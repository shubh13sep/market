import asyncio
import json
import yaml
import os
import logging
import re
import argparse
import tempfile
import webbrowser
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

import aiohttp
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crawl4ai.auto_config_generator.hybrid_config_generator import ConfigGenerator
# Import our modules
from crawl4ai.auto_config_generator.llm_selector_generator import LLMSelectorGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('auto_config_generator')


class AutoConfigGenerator:
    """
    Enhanced configuration generator that captures headers automatically
    and provides UI-based element selection for generating selectors.
    """

    def __init__(self, llm_api_key: Optional[str] = None,
                 llm_provider: str = "anthropic",
                 llm_model: str = "claude-3-haiku-20240307"):
        """
        Initialize the automatic configuration generator.

        Args:
            llm_api_key: API key for the LLM service
            llm_provider: LLM provider to use ("anthropic" or "openai")
            llm_model: Model to use
        """
        self.llm_api_key = llm_api_key or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.config_generator = ConfigGenerator(llm_api_key, llm_provider, llm_model)
        self.captured_headers = {}
        self.ui_selections = {}
        self.page_html = ""
        self.current_url = ""

    async def capture_headers(self, url: str) -> Dict[str, str]:
        """
        Capture actual HTTP headers used when visiting a URL.

        Args:
            url: URL to visit and capture headers from

        Returns:
            Dict[str, str]: Dictionary of HTTP headers
        """
        logger.info(f"Capturing headers from {url}")
        self.current_url = url

        # Use Playwright to visit the URL and capture headers
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            # Setup header interception
            captured_headers = {}

            async def log_request_headers(request):
                # Store the request headers for later use
                headers = request.headers
                for key, value in headers.items():
                    # Skip internal headers
                    if not key.startswith(('_', ':')) and key.lower() not in ['host', 'connection', 'content-length']:
                        captured_headers[key] = value

            # Listen for requests
            context.on("request", log_request_headers)

            # Create page and navigate
            page = await context.new_page()

            try:
                response = await page.goto(url, wait_until="networkidle")

                # Get response headers as well
                response_headers = response.headers

                # Combine request and response headers, giving priority to request headers
                for key, value in response_headers.items():
                    if key.lower() not in ['set-cookie']:
                        if key not in captured_headers:
                            captured_headers[key] = value

                # Store HTML for later use
                self.page_html = await page.content()

                # Get essential headers for scraping
                essential_headers = {
                    'User-Agent': captured_headers.get('User-Agent', ''),
                    'Accept': captured_headers.get('Accept', '*/*'),
                    'Accept-Language': captured_headers.get('Accept-Language', 'en-US,en;q=0.9'),
                    'Referer': url
                }

                logger.info(f"Captured {len(essential_headers)} essential headers")
                self.captured_headers = essential_headers

                return essential_headers

            except Exception as e:
                logger.error(f"Error capturing headers: {e}")
                return {}
            finally:
                await browser.close()

    async def generate_selectors_from_ui_selections(self, selections: Dict[str, Dict[str, str]]) -> Dict[
        str, Dict[str, Any]]:
        """
        Generate selectors based on elements selected through the UI.

        Args:
            selections: Dictionary of element selections from UI

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of generated selectors
        """
        logger.info(f"Generating selectors from {len(selections)} UI selections")
        self.ui_selections = selections

        selectors = {}

        for name, selection in selections.items():
            selector_path = selection.get('selector', '')
            is_group = selection.get('isGroup', False)
            is_multiple = selection.get('isMultiple', False)
            attribute = selection.get('attribute', '')

            if is_group:
                # This is a group selector (like a product card)
                fields = selection.get('fields', {})
                group_config = {
                    "type": "group",
                    "multiple": True,
                    "container": selector_path,
                    "fields": {}
                }

                # Add fields within the group
                for field_name, field_data in fields.items():
                    field_selector = field_data.get('selector', '')
                    field_attribute = field_data.get('attribute', '')
                    field_is_multiple = field_data.get('isMultiple', False)

                    field_config = {
                        "type": "css",
                        "query": field_selector,
                        "multiple": field_is_multiple
                    }

                    if field_attribute:
                        field_config["attribute"] = field_attribute

                    group_config["fields"][field_name] = field_config

                selectors[name] = group_config
            else:
                # This is a simple selector
                selector_config = {
                    "type": "css",
                    "query": selector_path,
                    "multiple": is_multiple
                }

                if attribute:
                    selector_config["attribute"] = attribute

                selectors[name] = selector_config

        return selectors

    async def optimize_selectors_with_llm(self, selectors: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Optimize user-selected selectors using LLM for better robustness.

        Args:
            selectors: Dictionary of selectors from UI selection

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of optimized selectors
        """
        if not self.llm_api_key:
            logger.warning("No LLM API key provided, skipping selector optimization")
            return selectors

        try:
            # Initialize LLM selector generator
            llm_config = {
                "enabled": True,
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
                "llm_api_key": self.llm_api_key,
                "use_cache": True
            }
            selector_generator = LLMSelectorGenerator(llm_config)

            # Create extraction spec from our selectors
            extraction_spec = {}
            for key, value in selectors.items():
                if value.get("type") == "group":
                    # For group selectors, include fields
                    extraction_spec[key] = list(value.get("fields", {}).keys())
                else:
                    # For simple selectors, just add the key
                    extraction_spec[key] = None

            # Have LLM optimize our selectors
            logger.info(f"Optimizing selectors with LLM")
            optimized_selectors = await selector_generator.create_full_extraction_config(
                self.current_url, self.page_html, extraction_spec
            )

            # If LLM generated selectors, use them, otherwise keep the original ones
            if optimized_selectors:
                logger.info(f"Successfully optimized selectors with LLM")

                # For each original selector, check if we have an optimized version
                # If not, keep the original one
                for key, value in selectors.items():
                    if key not in optimized_selectors:
                        optimized_selectors[key] = value

                return optimized_selectors
            else:
                logger.warning("LLM failed to optimize selectors, keeping original ones")
                return selectors

        except Exception as e:
            logger.error(f"Error optimizing selectors with LLM: {e}")
            return selectors

    async def generate_complete_config(self, url: str, selectors: Dict[str, Dict[str, Any]],
                                       optimize: bool = True) -> Dict[str, Any]:
        """
        Generate a complete configuration including automatically captured headers and selectors.

        Args:
            url: URL to generate configuration for
            selectors: Dictionary of selectors (from UI or other source)
            optimize: Whether to optimize selectors with LLM

        Returns:
            Dict[str, Any]: Complete configuration
        """
        logger.info(f"Generating complete configuration for {url}")
        logger.info(f"Received selectors: {selectors.keys() if selectors else 'None'}")

        # Capture headers if not already done
        if not self.captured_headers:
            await self.capture_headers(url)

        # If selectors is empty or None, try to get them from ui_selections
        if not selectors and hasattr(self, 'ui_selections') and self.ui_selections:
            logger.info(f"Using cached UI selections: {self.ui_selections.keys()}")
            selectors = await self.generate_selectors_from_ui_selections(self.ui_selections)

        # If still no selectors, use a fallback selector
        if not selectors:
            logger.warning("No selectors available, using fallback selectors")
            selectors = {
                "content": {
                    "type": "css",
                    "query": "body",
                    "multiple": False
                }
            }

        # Optimize selectors if requested
        if optimize and self.llm_api_key and selectors:
            try:
                optimized = await self.optimize_selectors_with_llm(selectors)
                if optimized:
                    selectors = optimized
                    logger.info("Successfully optimized selectors with LLM")
            except Exception as e:
                logger.error(f"Error optimizing selectors: {e}")
                # Continue with original selectors

        # Detect site type
        site_type = await self.config_generator.detect_site_type(url)
        logger.info(f"Detected site type: {site_type}")

        # Load template based on site type
        config = await self.config_generator.load_template(site_type)

        # Update configuration with our captured data
        config["url"] = url
        config["headers"] = self.captured_headers
        config["extract"] = selectors

        # Determine if JavaScript rendering is needed
        js_indicators = [
            "Vue", "React", "Angular", "Svelte", "jQuery",
            "dynamically", "lazy loading", "infinite scroll"
        ]

        needs_js = False
        for indicator in js_indicators:
            if indicator.lower() in self.page_html.lower():
                needs_js = True
                break

        config["render_js"] = needs_js

        # Add stealth mode to avoid bot detection
        config["stealth_mode"] = True

        # Set default output format
        if "output_format" not in config:
            config["output_format"] = "json"

        # Set default output directory
        if "output_dir" not in config:
            config["output_dir"] = "output"

        logger.info(f"Generated complete configuration with {len(selectors)} selectors")
        return config


    async def validate_config(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Validate the generated configuration by testing selectors.

        Args:
            config: Generated configuration

        Returns:
            Dict[str, Dict[str, Any]]: Validation results
        """
        logger.info("Validating configuration")

        # Use the existing validation method from ConfigGenerator
        validation_results = await self.config_generator.validate_selectors(config["url"], config)
        return validation_results

    def save_config(self, config: Dict[str, Any], path: str) -> None:
        """
        Save the configuration to a file.

        Args:
            config: Configuration to save
            path: Path to save the configuration to
        """
        logger.info(f"Saving configuration to {path}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        # Save configuration
        with open(path, 'w') as f:
            if path.endswith('.json'):
                json.dump(config, f, indent=2)
            else:
                yaml.dump(config, f, default_flow_style=False)


# Web interface for UI-based element selection
class ElementSelectorUI:
    """
    Web-based UI for selecting elements to scrape and generating configurations.
    """

    def __init__(self):
        """Initialize the UI server."""
        self.app = FastAPI(title="Crawl4AI Element Selector")
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.static_dir = os.path.join(os.path.dirname(__file__), "static")

        # Create directories if they don't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs(os.path.join(self.static_dir, "css"), exist_ok=True)
        os.makedirs(os.path.join(self.static_dir, "js"), exist_ok=True)

        # Mount static files
        self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")

        # Setup templates
        self.templates = Jinja2Templates(directory=self.templates_dir)

        # Create required files
        self._create_ui_files()

        # Setup routes
        self._setup_routes()

        # Initialize generator
        self.config_generator = None
        self.current_url = ""
        self.current_config = {}
        self.validation_results = {}

    def _create_ui_files(self):
        """Create necessary UI files."""
        # Create index.html
        with open(os.path.join(self.templates_dir, "index.html"), "w") as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crawl4AI Element Selector</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/dracula.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container-fluid">
                    <a class="navbar-brand" href="#">Crawl4AI Element Selector</a>
                </div>
            </nav>
        </div>

        <div class="row mt-3">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>URL Configuration</h5>
                    </div>
                    <div class="card-body">
                        <form id="urlForm">
                            <div class="mb-3">
                                <label for="url" class="form-label">URL</label>
                                <input type="url" class="form-control" id="url" name="url" placeholder="https://example.com" required>
                            </div>
                            <div class="mb-3">
                                <label for="llmProvider" class="form-label">LLM Provider (Optional)</label>
                                <select class="form-select" id="llmProvider" name="llm_provider">
                                    <option value="anthropic">Anthropic Claude</option>
                                    <option value="openai">OpenAI GPT</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="llmModel" class="form-label">LLM Model (Optional)</label>
                                <input type="text" class="form-control" id="llmModel" name="llm_model" value="claude-3-haiku-20240307">
                            </div>
                            <div class="mb-3">
                                <label for="llmApiKey" class="form-label">API Key (Optional)</label>
                                <input type="password" class="form-control" id="llmApiKey" name="llm_api_key" placeholder="Your LLM API key">
                            </div>
                            <button type="submit" class="btn btn-primary" id="analyzeBtn">Analyze URL</button>
                        </form>
                        <div class="mt-3">
                            <div class="progress d-none" id="progressBar">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                            </div>
                            <div id="statusMessage" class="alert alert-info d-none"></div>
                        </div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h5>Element Selection</h5>
                    </div>
                    <div class="card-body">
                        <div id="selectionList" class="list-group">
                            <p class="text-muted" id="noSelectionMsg">No elements selected yet. Use the iframe to select elements.</p>
                        </div>
                        <div class="mt-3">
                            <button class="btn btn-primary" id="addSelectionBtn" disabled>Add New Selection</button>
                            <button class="btn btn-success" id="generateConfigBtn" disabled>Generate Config</button>
                        </div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h5>Validation Results</h5>
                    </div>
                    <div class="card-body" id="validationResults">
                        <p class="text-muted">Validation results will appear here after generating the config.</p>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5>Page Preview</h5>
                        <div>
                            <button class="btn btn-sm btn-info" id="inspectorToggle" disabled>Enable Inspector</button>
                            <button class="btn btn-sm btn-success" id="saveConfigBtn" disabled>Save Config</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="iframeContainer" class="d-none">
                            <iframe id="pageFrame" class="w-100 h-100" src="about:blank"></iframe>
                        </div>
                        <div id="configView" class="d-none">
                            <textarea id="configEditor"></textarea>
                        </div>
                        <div id="loadingMessage" class="text-center p-5">
                            <p>Enter a URL above and click "Analyze URL" to start.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Add New Selection Modal -->
    <div class="modal fade" id="addSelectionModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Add Element Selection</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="selectionForm">
                        <div class="mb-3">
                            <label for="selectionName" class="form-label">Name</label>
                            <input type="text" class="form-control" id="selectionName" required>
                        </div>
                        <div class="mb-3">
                            <label for="selectionSelector" class="form-label">Selected Element</label>
                            <input type="text" class="form-control" id="selectionSelector" readonly>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="selectionIsGroup">
                            <label class="form-check-label" for="selectionIsGroup">This is a group/container</label>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="selectionIsMultiple">
                            <label class="form-check-label" for="selectionIsMultiple">Extract multiple elements</label>
                        </div>
                        <div class="mb-3">
                            <label for="selectionAttribute" class="form-label">Attribute (optional)</label>
                            <input type="text" class="form-control" id="selectionAttribute" placeholder="e.g., href, src">
                        </div>
                        <div id="groupFieldsContainer" class="mb-3 d-none">
                            <label class="form-label">Group Fields</label>
                            <div id="groupFields"></div>
                            <button type="button" class="btn btn-sm btn-outline-primary mt-2" id="addFieldBtn">Add Field</button>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="saveSelectionBtn">Save</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Group Field Modal -->
    <div class="modal fade" id="addFieldModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Add Group Field</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="fieldForm">
                        <div class="mb-3">
                            <label for="fieldName" class="form-label">Field Name</label>
                            <input type="text" class="form-control" id="fieldName" required>
                        </div>
                        <div class="mb-3">
                            <label for="fieldSelector" class="form-label">Select an element in the page preview</label>
                            <input type="text" class="form-control" id="fieldSelector" placeholder="Click in the page to select element" readonly>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="fieldIsMultiple">
                            <label class="form-check-label" for="fieldIsMultiple">Extract multiple elements</label>
                        </div>
                        <div class="mb-3">
                            <label for="fieldAttribute" class="form-label">Attribute (optional)</label>
                            <input type="text" class="form-control" id="fieldAttribute" placeholder="e.g., href, src">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="saveFieldBtn">Save</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/yaml/yaml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/javascript/javascript.min.js"></script>
    <script src="/static/js/script.js"></script>
</body>
</html>
            """)

        # Create CSS file
        with open(os.path.join(self.static_dir, "css", "style.css"), "w") as f:
            f.write("""
body {
    background-color: #f7f9fc;
}

.navbar {
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.card {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    border: none;
}

.card-header {
    background-color: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
}

.CodeMirror {
    height: calc(100vh - 200px);
    border: 1px solid #ced4da;
    border-radius: 4px;
}

#pageFrame {
    height: calc(100vh - 200px);
    border: 1px solid #ced4da;
    border-radius: 4px;
}

#iframeContainer {
    height: calc(100vh - 200px);
}

.highlight-element {
    outline: 2px dashed #007bff !important;
    background-color: rgba(0, 123, 255, 0.1) !important;
}

.selection-item {
    border-left: 3px solid #007bff;
}

.field-item {
    border-left: 3px solid #28a745;
    margin-left: 15px;
}

.group-fields-container {
    margin-left: 15px;
    border-left: 1px dashed #ccc;
    padding-left: 10px;
}

.validation-success {
    color: #28a745;
}

.validation-failure {
    color: #dc3545;
}
            """)

        # Create JavaScript file
        with open(os.path.join(self.static_dir, "js", "script.js"), "w") as f:
            f.write("""
document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let editor;
    let selectedElement = null;
    let inspectorEnabled = false;
    let addingGroupField = false;
    let currentGroupField = null;
    let selections = {};
    let frameLoaded = false;

    // Initialize Bootstrap components
    const addSelectionModal = new bootstrap.Modal(document.getElementById('addSelectionModal'));
    const addFieldModal = new bootstrap.Modal(document.getElementById('addFieldModal'));

    // Setup CodeMirror
    const setupCodeMirror = () => {
        editor = CodeMirror.fromTextArea(document.getElementById('configEditor'), {
            mode: 'yaml',
            lineNumbers: true,
            theme: 'default',
            lineWrapping: true,
            readOnly: false
        });
    };

    // Toggle between iframe and config views
    const showIframe = () => {
        document.getElementById('iframeContainer').classList.remove('d-none');
        document.getElementById('configView').classList.add('d-none');
        document.getElementById('loadingMessage').classList.add('d-none');
    };

    const showConfig = () => {
        document.getElementById('iframeContainer').classList.add('d-none');
        document.getElementById('configView').classList.remove('d-none');
        document.getElementById('loadingMessage').classList.add('d-none');

        if (!editor) {
            setupCodeMirror();
        }
    };

    const showLoading = () => {
        document.getElementById('iframeContainer').classList.add('d-none');
        document.getElementById('configView').classList.add('d-none');
        document.getElementById('loadingMessage').classList.remove('d-none');
    };

    // URL Form Submission
    document.getElementById('urlForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const url = document.getElementById('url').value;
        const llmProvider = document.getElementById('llmProvider').value;
        const llmModel = document.getElementById('llmModel').value;
        const llmApiKey = document.getElementById('llmApiKey').value;

        // Reset UI
        showLoading();
        document.getElementById('inspectorToggle').disabled = true;
        document.getElementById('addSelectionBtn').disabled = true;
        document.getElementById('generateConfigBtn').disabled = true;
        document.getElementById('saveConfigBtn').disabled = true;
        document.getElementById('selectionList').innerHTML = '<p class="text-muted" id="noSelectionMsg">No elements selected yet. Use the iframe to select elements.</p>';
        selections = {};

        // Show progress
        const progressBar = document.getElementById('progressBar');
        const progressIndicator = progressBar.querySelector('.progress-bar');
        const statusMessage = document.getElementById('statusMessage');

        progressBar.classList.remove('d-none');
        statusMessage.classList.remove('d-none');
        statusMessage.innerHTML = 'Analyzing URL and capturing headers...';
        progressIndicator.style.width = '10%';

        try {
            // Step 1: Capture headers and prepare page
            const prepareResponse = await fetch('/api/prepare-page', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    llm_provider: llmProvider,
                    llm_model: llmModel,
                    llm_api_key: llmApiKey
                })
            });

            if (!prepareResponse.ok) {
                throw new Error('Failed to prepare page: ' + await prepareResponse.text());
            }

            statusMessage.innerHTML = 'Page prepared successfully! Loading preview...';
            progressIndicator.style.width = '50%';

            // Step 2: Load the iframe with the prepared URL
            const iframe = document.getElementById('pageFrame');
            iframe.src = '/preview?url=' + encodeURIComponent(url);

            iframe.onload = function() {
                try {
                    // Setup iframe inspection
                    setupIframeInspector(iframe);
                    frameLoaded = true;

                    // Update UI
                    showIframe();
                    document.getElementById('inspectorToggle').disabled = false;
                    document.getElementById('addSelectionBtn').disabled = false;

                    statusMessage.innerHTML = 'Page loaded! Use the inspector to select elements for scraping.';
                    statusMessage.classList.remove('alert-info');
                    statusMessage.classList.add('alert-success');
                    progressIndicator.style.width = '100%';

                    // Hide progress after a delay
                    setTimeout(() => {
                        progressBar.classList.add('d-none');
                    }, 2000);
                } catch (err) {
                    console.error('Error setting up iframe inspector:', err);
                    statusMessage.innerHTML = 'Error loading preview: ' + err.message;
                    statusMessage.classList.remove('alert-info');
                    statusMessage.classList.add('alert-danger');
                }
            };

            iframe.onerror = function() {
                statusMessage.innerHTML = 'Error loading preview. Please check the URL and try again.';
                statusMessage.classList.remove('alert-info');
                statusMessage.classList.add('alert-danger');
            };

        } catch (error) {
            console.error('Error:', error);
            statusMessage.innerHTML = error.message;
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-danger');
        }
    });

    // Setup iframe inspector
    function setupIframeInspector(iframe) {
        const frameContent = iframe.contentDocument || iframe.contentWindow.document;

        // Inject CSS for highlighting
        const style = frameContent.createElement('style');
        style.textContent = `
            .highlight-element {
                outline: 2px dashed #007bff !important;
                background-color: rgba(0, 123, 255, 0.1) !important;
            }

            .selected-element {
                outline: 2px solid #dc3545 !important;
                background-color: rgba(220, 53, 69, 0.1) !important;
            }
        `;
        frameContent.head.appendChild(style);

        // Inject custom script for element selection
        const script = frameContent.createElement('script');
        script.textContent = `
            let hoveredElement = null;
            let inspector = false;

            function toggleInspector(enable) {
                inspector = enable;
                if (!inspector && hoveredElement) {
                    hoveredElement.classList.remove('highlight-element');
                    hoveredElement = null;
                }
            }

            function getCssSelector(el) {
                if (!el) return '';

                let path = [];
                while (el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.nodeName.toLowerCase();

                    if (el.id) {
                        selector += '#' + el.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sib = el, nth = 1;
                        while (sib = sib.previousElementSibling) {
                            if (sib.nodeName.toLowerCase() === selector) nth++;
                        }

                        if (el.className) {
                            selector += '.' + Array.from(el.classList).join('.');
                        }

                        if (nth !== 1) selector += ":nth-of-type(" + nth + ")";
                    }

                    path.unshift(selector);
                    el = el.parentNode;
                }

                return path.join(' > ');
            }

            document.addEventListener('mouseover', function(e) {
                if (!inspector) return;

                if (hoveredElement) {
                    hoveredElement.classList.remove('highlight-element');
                }

                hoveredElement = e.target;
                hoveredElement.classList.add('highlight-element');

                // Prevent default to avoid any page interactions
                e.preventDefault();
                e.stopPropagation();
            }, true);

            document.addEventListener('click', function(e) {
                if (!inspector) return;

                // Get the element's selector
                const selector = getCssSelector(e.target);

                // Send message to parent window
                window.parent.postMessage({
                    type: 'elementSelected',
                    selector: selector,
                    text: e.target.textContent.trim(),
                    tagName: e.target.tagName.toLowerCase(),
                    attributes: Array.from(e.target.attributes).reduce((acc, attr) => {
                        acc[attr.name] = attr.value;
                        return acc;
                    }, {})
                }, '*');

                // Prevent default page interaction
                e.preventDefault();
                e.stopPropagation();
            }, true);
        `;
        frameContent.body.appendChild(script);
    }

    // Listen for messages from the iframe
    window.addEventListener('message', function(event) {
        if (event.data.type === 'elementSelected') {
            selectedElement = event.data;

            if (addingGroupField) {
                // We're adding a field to a group
                document.getElementById('fieldSelector').value = selectedElement.selector;
                addFieldModal.show();
            } else {
                // We're adding a top-level selection
                document.getElementById('selectionSelector').value = selectedElement.selector;
                addSelectionModal.show();
            }
        }
    });

    // Toggle inspector
    document.getElementById('inspectorToggle').addEventListener('click', function() {
        const iframe = document.getElementById('pageFrame');
        const frameContent = iframe.contentDocument || iframe.contentWindow.document;

        inspectorEnabled = !inspectorEnabled;

        if (inspectorEnabled) {
            this.textContent = 'Disable Inspector';
            this.classList.remove('btn-info');
            this.classList.add('btn-warning');

            // Enable inspector in iframe
            if (frameContent && frameContent.defaultView) {
                frameContent.defaultView.toggleInspector(true);
            }
        } else {
            this.textContent = 'Enable Inspector';
            this.classList.remove('btn-warning');
            this.classList.add('btn-info');

            // Disable inspector in iframe
            if (frameContent && frameContent.defaultView) {
                frameContent.defaultView.toggleInspector(false);
            }
        }
    });

    // Add selection button
    document.getElementById('addSelectionBtn').addEventListener('click', function() {
        if (!frameLoaded) {
            alert('Please wait for the page to load first.');
            return;
        }

        // Enable inspector
        const inspectorToggle = document.getElementById('inspectorToggle');
        if (!inspectorEnabled) {
            inspectorToggle.click();
        }

        // Reset form
        document.getElementById('selectionForm').reset();
        document.getElementById('groupFieldsContainer').classList.add('d-none');
        document.getElementById('groupFields').innerHTML = '';
    });

    // Selection form handling
    document.getElementById('selectionIsGroup').addEventListener('change', function() {
        if (this.checked) {
            document.getElementById('groupFieldsContainer').classList.remove('d-none');
        } else {
            document.getElementById('groupFieldsContainer').classList.add('d-none');
        }
    });

    // Add field button
    document.getElementById('addFieldBtn').addEventListener('click', function() {
        addingGroupField = true;
        currentGroupField = null;

        // Reset field form
        document.getElementById('fieldForm').reset();

        // Focus back on iframe - user needs to select an element
        const inspectorToggle = document.getElementById('inspectorToggle');
        if (!inspectorEnabled) {
            inspectorToggle.click();
        }
    });

    // Save field button
    document.getElementById('saveFieldBtn').addEventListener('click', function() {
        const fieldName = document.getElementById('fieldName').value;
        const fieldSelector = document.getElementById('fieldSelector').value;
        const fieldIsMultiple = document.getElementById('fieldIsMultiple').checked;
        const fieldAttribute = document.getElementById('fieldAttribute').value;

        if (!fieldName || !fieldSelector) {
            alert('Please fill in all required fields');
            return;
        }

        // Add field to the group fields container
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'card p-2 mb-2 field-item';
        fieldDiv.innerHTML = `
            <div class="d-flex justify-content-between">
                <span><strong>${fieldName}</strong>: ${fieldSelector}</span>
                <button type="button" class="btn btn-sm btn-outline-danger" data-field="${fieldName}">Remove</button>
            </div>
            <div class="small">
                ${fieldAttribute ? `Attribute: ${fieldAttribute} | ` : ''}
                ${fieldIsMultiple ? 'Multiple elements' : 'Single element'}
            </div>
        `;
        document.getElementById('groupFields').appendChild(fieldDiv);

        // Add event listener for remove button
        fieldDiv.querySelector('button').addEventListener('click', function() {
            const fieldName = this.getAttribute('data-field');
            this.closest('.field-item').remove();
        });

        // Hide modal
        addFieldModal.hide();
        addingGroupField = false;
    });

    // Save selection button
    document.getElementById('saveSelectionBtn').addEventListener('click', function() {
        const selectionName = document.getElementById('selectionName').value;
        const selectionSelector = document.getElementById('selectionSelector').value;
        const selectionIsGroup = document.getElementById('selectionIsGroup').checked;
        const selectionIsMultiple = document.getElementById('selectionIsMultiple').checked;
        const selectionAttribute = document.getElementById('selectionAttribute').value;

        if (!selectionName || !selectionSelector) {
            alert('Please fill in all required fields');
            return;
        }

        // Check if name already exists
        if (selections[selectionName]) {
            alert('A selection with this name already exists');
            return;
        }

        // Create selection object
        const selection = {
            selector: selectionSelector,
            isGroup: selectionIsGroup,
            isMultiple: selectionIsMultiple
        };

        if (selectionAttribute) {
            selection.attribute = selectionAttribute;
        }

        if (selectionIsGroup) {
            // Get fields
            selection.fields = {};
            const fieldElements = document.querySelectorAll('#groupFields .field-item');

            fieldElements.forEach(fieldElem => {
                const fieldName = fieldElem.querySelector('strong').textContent;
                const fieldSelector = fieldElem.querySelector('span').textContent.split(': ')[1];
                const fieldDetails = fieldElem.querySelector('.small').textContent;

                const fieldObj = {
                    selector: fieldSelector,
                    isMultiple: fieldDetails.includes('Multiple elements')
                };

                if (fieldDetails.includes('Attribute:')) {
                    fieldObj.attribute = fieldDetails.split('Attribute: ')[1].split(' |')[0];
                }

                selection.fields[fieldName] = fieldObj;
            });
        }

        // Add to selections object
        selections[selectionName] = selection;

        // Update selection list
        updateSelectionList();

        // Hide modal
        addSelectionModal.hide();

        // Enable generate config button if we have selections
        if (Object.keys(selections).length > 0) {
            document.getElementById('generateConfigBtn').disabled = false;
        }

        // Disable inspector
        const inspectorToggle = document.getElementById('inspectorToggle');
        if (inspectorEnabled) {
            inspectorToggle.click();
        }
    });

    // Update selection list
    function updateSelectionList() {
        const selectionList = document.getElementById('selectionList');
        selectionList.innerHTML = '';

        const noSelectionMsg = document.getElementById('noSelectionMsg');
        if (noSelectionMsg) {
            noSelectionMsg.remove();
        }

        for (const [name, selection] of Object.entries(selections)) {
            const item = document.createElement('div');
            item.className = 'card p-2 mb-2 selection-item';

            let itemContent = `
                <div class="d-flex justify-content-between">
                    <span><strong>${name}</strong>: ${selection.selector}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger" data-selection="${name}">Remove</button>
                </div>
                <div class="small">
                    ${selection.attribute ? `Attribute: ${selection.attribute} | ` : ''}
                    ${selection.isMultiple ? 'Multiple elements | ' : ''}
                    ${selection.isGroup ? 'Group container' : 'Simple selector'}
                </div>
            `;

            if (selection.isGroup && selection.fields) {
                itemContent += '<div class="group-fields-container mt-2">';

                for (const [fieldName, field] of Object.entries(selection.fields)) {
                    itemContent += `
                        <div class="mb-1">
                            <strong>${fieldName}:</strong> ${field.selector}
                            <div class="small">
                                ${field.attribute ? `Attribute: ${field.attribute} | ` : ''}
                                ${field.isMultiple ? 'Multiple elements' : 'Single element'}
                            </div>
                        </div>
                    `;
                }

                itemContent += '</div>';
            }

            item.innerHTML = itemContent;
            selectionList.appendChild(item);

            // Add event listener for remove button
            item.querySelector('button').addEventListener('click', function() {
                const selectionName = this.getAttribute('data-selection');
                delete selections[selectionName];
                updateSelectionList();

                // Disable generate button if no selections left
                if (Object.keys(selections).length === 0) {
                    document.getElementById('generateConfigBtn').disabled = true;
                }
            });
        }
    }

    // Generate config button
    document.getElementById('generateConfigBtn').addEventListener('click', async function() {
        const url = document.getElementById('url').value;

        if (Object.keys(selections).length === 0) {
            alert('Please select at least one element before generating the configuration');
            return;
        }

        // Show progress
        const progressBar = document.getElementById('progressBar');
        const progressIndicator = progressBar.querySelector('.progress-bar');
        const statusMessage = document.getElementById('statusMessage');

        progressBar.classList.remove('d-none');
        statusMessage.classList.remove('d-none');
        statusMessage.innerHTML = 'Generating configuration...';
        progressIndicator.style.width = '10%';

        try {
            // Call API to generate config
            const response = await fetch('/api/generate-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    selections: selections
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate configuration: ' + await response.text());
            }

            statusMessage.innerHTML = 'Testing configuration...';
            progressIndicator.style.width = '50%';

            const config = await response.json();

            // Show config in editor
            showConfig();
            editor.setValue(config.yaml_config);

            // Update validation results
            updateValidationResults(config.validation_results);

            // Enable save button
            document.getElementById('saveConfigBtn').disabled = false;

            statusMessage.innerHTML = 'Configuration generated successfully!';
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-success');
            progressIndicator.style.width = '100%';

            // Hide progress after a delay
            setTimeout(() => {
                progressBar.classList.add('d-none');
            }, 2000);

        } catch (error) {
            console.error('Error:', error);
            statusMessage.innerHTML = error.message;
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-danger');
        }
    });

    // Update validation results
    function updateValidationResults(results) {
        const validationDiv = document.getElementById('validationResults');

        if (!results || Object.keys(results).length === 0) {
            validationDiv.innerHTML = '<p class="text-muted">No validation results available.</p>';
            return;
        }

        let html = '<div class="list-group">';

        for (const [key, result] of Object.entries(results)) {
            if (result.container !== undefined) {
                // Group selector
                const containerSuccess = result.container;
                const containerClass = containerSuccess ? 'validation-success' : 'validation-failure';
                const containerIcon = containerSuccess ? '✅' : '❌';

                html += `<div class="list-group-item">`;
                html += `<div class="${containerClass}"><strong>${key}</strong> ${containerIcon}</div>`;
                html += `<div>Container: ${result.container_count} matches</div>`;

                if (result.fields && Object.keys(result.fields).length > 0) {
                    html += `<div class="ms-3 mt-1">Fields:</div>`;
                    html += `<ul class="list-unstyled ms-3">`;

                    for (const [fieldName, fieldResult] of Object.entries(result.fields)) {
                        const fieldSuccess = fieldResult.success;
                        const fieldClass = fieldSuccess ? 'validation-success' : 'validation-failure';
                        const fieldIcon = fieldSuccess ? '✅' : '❌';

                        html += `<li class="${fieldClass}">${fieldName} ${fieldIcon}`;
                        if (fieldResult.count) {
                            html += ` (${fieldResult.count} matches)`;
                        }
                        html += `</li>`;
                    }

                    html += `</ul>`;
                }

                html += `</div>`;
            } else if (result.success !== undefined) {
                // Simple selector
                const success = result.success;
                const className = success ? 'validation-success' : 'validation-failure';
                const icon = success ? '✅' : '❌';

                html += `<div class="list-group-item">`;
                html += `<div class="${className}"><strong>${key}</strong> ${icon}`;
                if (result.count) {
                    html += ` (${result.count} matches)`;
                }
                html += `</div>`;

                html += `</div>`;
            }
        }

        html += '</div>';
        validationDiv.innerHTML = html;
    }

    // Save config button
    document.getElementById('saveConfigBtn').addEventListener('click', async function() {
        const configYaml = editor.getValue();

        try {
            const response = await fetch('/api/save-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config: configYaml
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save configuration: ' + await response.text());
            }

            const result = await response.json();

            // Use the browser's download capability
            const a = document.createElement('a');
            a.href = result.download_url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            // Show success message
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-danger');
            statusMessage.classList.add('alert-success');
            statusMessage.innerHTML = 'Configuration saved successfully!';

            // Hide message after a delay
            setTimeout(() => {
                statusMessage.classList.add('d-none');
            }, 3000);

        } catch (error) {
            console.error('Error:', error);

            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-success');
            statusMessage.classList.add('alert-danger');
            statusMessage.innerHTML = error.message;
        }
    });

    // Initialize UI
    showLoading();
});
            """)

    def _setup_routes(self):
        """Setup API routes."""

        # Home page
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            return self.templates.TemplateResponse("index.html", {"request": request})

        # Page preview
        @self.app.get("/preview")
        async def preview(request: Request, url: str):
            # This route serves an iframe-friendly version of the target website
            # with injected scripts for element selection
            return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Page Preview</title>
                    <meta name="robots" content="noindex, nofollow">
                    <style>
                        body {{
                            margin: 0;
                            padding: 0;
                        }}
                    </style>
                </head>
                <body>
                    <iframe src="{url}" style="width:100%;height:100vh;border:none;"></iframe>
                </body>
                </html>
            """)

        # API: Prepare page
        @self.app.post("/api/prepare-page")
        async def prepare_page(request: Request):
            data = await request.json()
            url = data.get("url")
            llm_provider = data.get("llm_provider")
            llm_model = data.get("llm_model")
            llm_api_key = data.get("llm_api_key")

            if not url:
                return JSONResponse(status_code=400, content={"error": "URL is required"})

            # Initialize config generator
            self.config_generator = AutoConfigGenerator(
                llm_api_key=llm_api_key,
                llm_provider=llm_provider,
                llm_model=llm_model
            )

            # Capture headers
            self.current_url = url
            await self.config_generator.capture_headers(url)

            return JSONResponse(content={"success": True, "message": "Page prepared successfully"})

        # API: Generate config
        @self.app.post("/api/generate-config")
        async def generate_config(request: Request):
            data = await request.json()
            url = data.get("url")
            selections = data.get("selections", {})

            logger.info(f"Received API request to generate config for URL: {url}")
            logger.info(f"Received {len(selections)} selections")

            if not url:
                return JSONResponse(
                    status_code=400,
                    content={"error": "URL is required"}
                )

            if not selections:
                logger.warning("No selections provided in request")
                # Check if we have any cached selections
                if hasattr(self, 'ui_selections') and self.ui_selections:
                    logger.info(f"Using {len(self.ui_selections)} cached selections")
                    selections = self.ui_selections
                else:
                    # Create a minimal fallback selection
                    logger.warning("Using fallback selection for entire page content")
                    selections = {
                        "page_content": {
                            "selector": "body",
                            "isGroup": False,
                            "isMultiple": False
                        }
                    }

            if not self.config_generator:
                logger.info("Initializing config generator")
                self.config_generator = AutoConfigGenerator(
                    llm_api_key=None,  # Don't use LLM for fallback
                    llm_provider="anthropic",
                    llm_model="claude-3-haiku-20240307"
                )
                await self.config_generator.capture_headers(url)

            # Save selections for potential reuse
            self.ui_selections = selections

            try:
                # Generate selectors from UI selections
                logger.info("Generating selectors from UI selections")
                selectors = await self.config_generator.generate_selectors_from_ui_selections(selections)

                # Generate complete config
                logger.info("Generating complete config")
                config = await self.config_generator.generate_complete_config(url, selectors)

                # Validate config
                logger.info("Validating config")
                validation_results = await self.config_generator.validate_config(config)

                # Convert config to YAML
                yaml_config = yaml.dump(config, default_flow_style=False)

                # Save current config for later use
                self.current_config = config
                self.validation_results = validation_results

                logger.info("Config generation successful")
                return JSONResponse(content={
                    "config": config,
                    "yaml_config": yaml_config,
                    "validation_results": validation_results
                })
            except Exception as e:
                logger.error(f"Error generating config: {e}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Error generating configuration: {str(e)}"}
                )

        # API: Save config
        @self.app.post("/api/save-config")
        async def save_config(request: Request):
            data = await request.json()
            config_yaml = data.get("config")

            if not config_yaml:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Configuration is required"}
                )

            # Generate a filename based on the URL
            if self.current_url:
                parsed_url = urlparse(self.current_url)
                hostname = parsed_url.netloc.replace(".", "_")
                filename = f"crawl4ai_{hostname}_config.yaml"
            else:
                filename = "crawl4ai_config.yaml"

            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
            temp_file.write(config_yaml.encode())
            temp_file.close()

            # Return the download URL
            return JSONResponse(content={
                "success": True,
                "filename": filename,
                "download_url": f"/download/{os.path.basename(temp_file.name)}?filename={filename}"
            })

        # Download route
        @self.app.get("/download/{filename}")
        async def download(filename: str, request_filename: str = None):
            file_path = os.path.join(tempfile.gettempdir(), filename)
            return FileResponse(
                path=file_path,
                filename=request_filename or filename,
                media_type="application/x-yaml"
            )

    def run(self, host: str = "0.0.0.0", port: int = 8000, open_browser: bool = True):
        """
        Run the UI server.

        Args:
            host: Host to run on
            port: Port to run on
            open_browser: Whether to open a browser window automatically
        """
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")

        uvicorn.run(self.app, host=host, port=port)


# Main function to run the automatic config generator
async def main():
    parser = argparse.ArgumentParser(description="Automatic Crawl4AI Configuration Generator")
    parser.add_argument("--url", help="URL to generate configuration for")
    parser.add_argument("--output", help="Output file path for configuration")
    parser.add_argument("--key", help="API key for LLM service (Anthropic or OpenAI)")
    parser.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic", help="LLM provider")
    parser.add_argument("--model", default="claude-3-haiku-20240307", help="LLM model to use")
    parser.add_argument("--ui", action="store_true", help="Launch the UI server")
    parser.add_argument("--port", type=int, default=8000, help="Port for UI server")

    args = parser.parse_args()

    if args.ui:
        # Launch UI server
        ui = ElementSelectorUI()
        ui.run(port=args.port)
    elif args.url:
        # Generate config in command-line mode
        generator = AutoConfigGenerator(
            llm_api_key=args.key,
            llm_provider=args.provider,
            llm_model=args.model
        )

        # Capture headers
        headers = await generator.capture_headers(args.url)

        # Create a basic extraction spec - this would normally come from UI
        extraction_spec = {
            "title": None,
            "content": None,
            "images": None,
            "links": None
        }

        # Generate selectors using LLM
        selectors = await generator.generate_selectors_from_llm(args.url, extraction_spec)

        # Generate complete config
        config = await generator.generate_complete_config(args.url, selectors)

        # Save configuration if output path is specified
        if args.output:
            generator.save_config(config, args.output)
            print(f"Configuration saved to {args.output}")
        else:
            # Print configuration to console
            print("\nGenerated Configuration:")
            print(yaml.dump(config, default_flow_style=False))
    else:
        print("Please specify a URL or use --ui to launch the UI server")


if __name__ == "__main__":
    asyncio.run(main())