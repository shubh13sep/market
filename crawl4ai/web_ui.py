import asyncio
import json
import yaml
import os
import tempfile
import webbrowser
from typing import Dict, Any, List, Optional
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import aiofiles
from starlette.middleware.cors import CORSMiddleware

# Import our hybrid config generator
from crawl4ai.auto_config_generator.hybrid_config_generator import ConfigGenerator

# Create FastAPI app
app = FastAPI(title="Crawl4AI Config Generator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)

# Create static directory for CSS and JS
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=templates_dir)

# Create the HTML template file
with open(os.path.join(templates_dir, "index.html"), "w") as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crawl4AI Config Generator</title>
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
                    <a class="navbar-brand" href="#">Crawl4AI Config Generator</a>
                </div>
            </nav>
        </div>

        <div class="row mt-3">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>Generate Configuration</h5>
                    </div>
                    <div class="card-body">
                        <form id="urlForm">
                            <div class="mb-3">
                                <label for="url" class="form-label">URL</label>
                                <input type="url" class="form-control" id="url" name="url" placeholder="https://example.com" required>
                            </div>
                            <div class="mb-3">
                                <label for="llmProvider" class="form-label">LLM Provider</label>
                                <select class="form-select" id="llmProvider" name="llm_provider">
                                    <option value="google">Google Gemini</option>
                                    <option value="anthropic">Anthropic Claude</option>
                                    <option value="openai">OpenAI GPT</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="llmModel" class="form-label">LLM Model</label>
                                <select class="form-select" id="llmModel" name="llm_model">
                                    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                                    <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                                    <option value="google/gemini-2.5-pro-exp-03-25:free">Gemini 2.5 Pro</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="llmApiKey" class="form-label">API Key</label>
                                <input type="password" class="form-control" id="llmApiKey" name="llm_api_key" placeholder="Your LLM API key">
                            </div>
                            <button type="submit" class="btn btn-primary" id="generateBtn">Generate Config</button>
                            <button type="button" class="btn btn-secondary" id="uploadBtn">Upload Existing</button>
                            <input type="file" id="configUpload" style="display: none;" accept=".yaml,.yml,.json">
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
                        <h5>Site Information</h5>
                    </div>
                    <div class="card-body" id="siteInfo">
                        <p class="text-muted">Site information will appear here after analysis.</p>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h5>Validation Results</h5>
                    </div>
                    <div class="card-body" id="validationResults">
                        <p class="text-muted">Validation results will appear here after testing selectors.</p>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5>Configuration Editor</h5>
                        <div>
                            <button class="btn btn-sm btn-success" id="saveBtn">Save Config</button>
                            <button class="btn btn-sm btn-info" id="validateBtn">Test Selectors</button>
                            <button class="btn btn-sm btn-primary" id="runBtn">Run Scraper</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <textarea id="configEditor"></textarea>
                    </div>
                </div>
            </div>
        </div>

        <div class="modal fade" id="selectorTestModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Selector Test Results</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div id="testResults"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
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

# Create the CSS file
with open(os.path.join(static_dir, "css", "style.css"), "w") as f:
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

.validation-success {
    color: #28a745;
}

.validation-failure {
    color: #dc3545;
}

.selector-sample {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-style: italic;
    color: #6c757d;
}

#siteInfo, #validationResults {
    max-height: 300px;
    overflow-y: auto;
}
    """)

# Create the JavaScript file
with open(os.path.join(static_dir, "js", "script.js"), "w") as f:
    f.write("""
    
// Add this to script.js
document.getElementById('llmProvider').addEventListener('change', function() {
    const provider = this.value;
    const modelSelect = document.getElementById('llmModel');
    
    // Clear current options
    modelSelect.innerHTML = '';
    
    // Add appropriate options based on provider
    if (provider === 'anthropic') {
        addOption(modelSelect, 'claude-3-haiku-20240307', 'Claude 3 Haiku');
        addOption(modelSelect, 'claude-3-sonnet-20240229', 'Claude 3 Sonnet');
        addOption(modelSelect, 'claude-3-opus-20240229', 'Claude 3 Opus');
    } else if (provider === 'openai') {
        addOption(modelSelect, 'gpt-4-turbo', 'GPT-4 Turbo');
        addOption(modelSelect, 'gpt-4', 'GPT-4');
        addOption(modelSelect, 'gpt-3.5-turbo', 'GPT-3.5 Turbo');
    } else if (provider === 'google') {
        addOption(modelSelect, 'google/gemini-2.5-pro-exp-03-25:free', 'Gemini 2.5 Pro');
        addOption(modelSelect, 'google/gemini-1.5-pro', 'Gemini 1.5 Pro');
    }
});

// Helper function to add options
function addOption(select, value, text) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = text;
    select.appendChild(option);
}

// Initialize model options on page load
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('llmProvider').dispatchEvent(new Event('change'));
});

document.addEventListener('DOMContentLoaded', function() {
    // Initialize CodeMirror
    const editor = CodeMirror.fromTextArea(document.getElementById('configEditor'), {
        mode: 'yaml',
        theme: 'default',
        lineNumbers: true,
        indentUnit: 2,
        tabSize: 2,
        lineWrapping: true,
        extraKeys: {"Tab": function(cm) { cm.replaceSelection("  ", "end"); }}
    });

    // Initialize Bootstrap components
    const selectorTestModal = new bootstrap.Modal(document.getElementById('selectorTestModal'));

    // Form submission
    document.getElementById('urlForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const url = document.getElementById('url').value;
        const llmProvider = document.getElementById('llmProvider').value;
        const llmModel = document.getElementById('llmModel').value;
        const llmApiKey = document.getElementById('llmApiKey').value;

        // Show progress and status
        const progressBar = document.getElementById('progressBar');
        const progressIndicator = progressBar.querySelector('.progress-bar');
        const statusMessage = document.getElementById('statusMessage');

        progressBar.classList.remove('d-none');
        statusMessage.classList.remove('d-none');
        statusMessage.textContent = 'Analyzing URL and detecting site type...';
        progressIndicator.style.width = '10%';

        try {
            // Step 1: Generate config
            const generateResponse = await fetch('/api/generate-config', {
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

            if (!generateResponse.ok) {
                throw new Error('Failed to generate configuration. ' + await generateResponse.text());
            }

            progressIndicator.style.width = '70%';
            statusMessage.textContent = 'Testing selectors...';

            const config = await generateResponse.json();

            // Update editor with config
            editor.setValue(config.yaml_config);

            // Display site info
            displaySiteInfo(config);

            // Step 2: Validate selectors
            const validateResponse = await fetch('/api/validate-selectors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    config: config.config
                })
            });

            if (!validateResponse.ok) {
                throw new Error('Failed to validate selectors. ' + await validateResponse.text());
            }

            const validationResults = await validateResponse.json();

            // Display validation results
            displayValidationResults(validationResults);

            progressIndicator.style.width = '100%';
            statusMessage.textContent = 'Configuration generated successfully!';
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-success');

            // Hide progress after a delay
            setTimeout(() => {
                progressBar.classList.add('d-none');
            }, 2000);

        } catch (error) {
            console.error('Error:', error);
            statusMessage.textContent = error.message;
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-danger');
            progressIndicator.style.width = '100%';
            progressBar.classList.remove('progress-bar-animated');
        }
    });

    // Save configuration
    document.getElementById('saveBtn').addEventListener('click', function() {
        const configYaml = editor.getValue();

        // Create a blob and download link
        const blob = new Blob([configYaml], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'crawl4ai_config.yaml';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // Validate selectors
    document.getElementById('validateBtn').addEventListener('click', async function() {
        try {
            const configYaml = editor.getValue();
            const config = jsyaml.load(configYaml);

            if (!config.url) {
                throw new Error('URL is missing in the configuration');
            }

            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-success', 'alert-danger');
            statusMessage.classList.add('alert-info');
            statusMessage.textContent = 'Testing selectors...';

            const response = await fetch('/api/validate-selectors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: config.url,
                    config: config
                })
            });

            if (!response.ok) {
                throw new Error('Failed to validate selectors. ' + await response.text());
            }

            const validationResults = await response.json();

            // Display validation results
            displayValidationResults(validationResults);
            displayTestResultsModal(validationResults);

            statusMessage.textContent = 'Selectors tested successfully!';
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-success');

        } catch (error) {
            console.error('Error:', error);
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-info', 'alert-success');
            statusMessage.classList.add('alert-danger');
            statusMessage.textContent = error.message;
        }
    });

    // Run scraper
    document.getElementById('runBtn').addEventListener('click', async function() {
        try {
            const configYaml = editor.getValue();

            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-success', 'alert-danger');
            statusMessage.classList.add('alert-info');
            statusMessage.textContent = 'Running scraper...';

            const response = await fetch('/api/run-scraper', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config_yaml: configYaml
                })
            });

            if (!response.ok) {
                throw new Error('Failed to run scraper. ' + await response.text());
            }

            const result = await response.json();

            statusMessage.textContent = `Scraper completed! Output saved to: ${result.output_path}`;
            statusMessage.classList.remove('alert-info');
            statusMessage.classList.add('alert-success');

        } catch (error) {
            console.error('Error:', error);
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.classList.remove('d-none', 'alert-info', 'alert-success');
            statusMessage.classList.add('alert-danger');
            statusMessage.textContent = error.message;
        }
    });

    // Upload existing config
    document.getElementById('uploadBtn').addEventListener('click', function() {
        document.getElementById('configUpload').click();
    });

    document.getElementById('configUpload').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            editor.setValue(content);
        };
        reader.readAsText(file);
    });

    // Helper function to display site info
    function displaySiteInfo(config) {
        const siteInfoDiv = document.getElementById('siteInfo');
        siteInfoDiv.innerHTML = `
            <p><strong>URL:</strong> ${config.config.url}</p>
            <p><strong>Site Type:</strong> ${config.site_type}</p>
            <p><strong>Navigation Type:</strong> ${config.config.navigation_type || 'single'}</p>
            <p><strong>JavaScript Required:</strong> ${config.config.render_js ? 'Yes' : 'No'}</p>
        `;
    }

    // Helper function to display validation results
    function displayValidationResults(results) {
        const validationDiv = document.getElementById('validationResults');
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
                        if (fieldResult.sample) {
                            html += ` <span class="selector-sample">"${fieldResult.sample}"</span>`;
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

                if (result.sample) {
                    html += `<div class="selector-sample">"${result.sample}"</div>`;
                }

                if (result.attribute_present !== undefined) {
                    const attrSuccess = result.attribute_present;
                    const attrClass = attrSuccess ? 'validation-success' : 'validation-failure';
                    const attrIcon = attrSuccess ? '✅' : '❌';

                    html += `<div class="${attrClass}">Attribute ${attrIcon}</div>`;
                    if (result.attribute_sample) {
                        html += `<div class="selector-sample">"${result.attribute_sample}"</div>`;
                    }
                }

                html += `</div>`;
            }
        }

        html += '</div>';
        validationDiv.innerHTML = html;
    }

    // Helper function to display test results modal
    function displayTestResultsModal(results) {
        const resultsDiv = document.getElementById('testResults');
        let html = '<div class="table-responsive"><table class="table table-bordered">';
        html += '<thead><tr><th>Selector</th><th>Status</th><th>Matches</th><th>Sample</th></tr></thead>';
        html += '<tbody>';

        for (const [key, result] of Object.entries(results)) {
            if (result.container !== undefined) {
                // Group selector
                const containerSuccess = result.container;
                const containerClass = containerSuccess ? 'table-success' : 'table-danger';
                const containerStatus = containerSuccess ? 'Success' : 'Failed';

                html += `<tr class="${containerClass}">`;
                html += `<td><strong>${key}</strong> (Container)</td>`;
                html += `<td>${containerStatus}</td>`;
                html += `<td>${result.container_count}</td>`;
                html += `<td>-</td>`;
                html += `</tr>`;

                if (result.fields && Object.keys(result.fields).length > 0) {
                    for (const [fieldName, fieldResult] of Object.entries(result.fields)) {
                        const fieldSuccess = fieldResult.success;
                        const fieldClass = fieldSuccess ? 'table-success' : 'table-danger';
                        const fieldStatus = fieldSuccess ? 'Success' : 'Failed';

                        html += `<tr class="${fieldClass}">`;
                        html += `<td class="ps-4">${key}.${fieldName}</td>`;
                        html += `<td>${fieldStatus}</td>`;
                        html += `<td>${fieldResult.count || 0}</td>`;
                        html += `<td>${fieldResult.sample || '-'}</td>`;
                        html += `</tr>`;
                    }
                }
            } else if (result.success !== undefined) {
                // Simple selector
                const success = result.success;
                const className = success ? 'table-success' : 'table-danger';
                const status = success ? 'Success' : 'Failed';

                html += `<tr class="${className}">`;
                html += `<td>${key}</td>`;
                html += `<td>${status}</td>`;
                html += `<td>${result.count || 0}</td>`;
                html += `<td>${result.sample || '-'}</td>`;
                html += `</tr>`;

                if (result.attribute_present !== undefined) {
                    const attrSuccess = result.attribute_present;
                    const attrClass = attrSuccess ? 'table-success' : 'table-danger';
                    const attrStatus = attrSuccess ? 'Success' : 'Failed';

                    html += `<tr class="${attrClass}">`;
                    html += `<td>${key} (Attribute)</td>`;
                    html += `<td>${attrStatus}</td>`;
                    html += `<td>-</td>`;
                    html += `<td>${result.attribute_sample || '-'}</td>`;
                    html += `</tr>`;
                }
            }
        }

        html += '</tbody></table></div>';
        resultsDiv.innerHTML = html;

        // Show the modal
        selectorTestModal.show();
    }
});
    """)



# Data models
class GenerateConfigRequest(BaseModel):
    url: str
    llm_provider: str = "anthropic"
    llm_model: str = "claude-3-haiku-20240307"
    llm_api_key: str = None


class ValidateSelectorsRequest(BaseModel):
    url: str
    config: Dict[str, Any]


class RunScraperRequest(BaseModel):
    config_yaml: str

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/generate-config")
async def generate_config(request: GenerateConfigRequest):
    """Generate configuration for a URL."""
    try:
        # Initialize the generator
        generator = ConfigGenerator(
            llm_api_key=request.llm_api_key,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model
        )

        # Generate the configuration
        config = await generator.generate_config(request.url)

        # Determine site type
        site_type = await generator.detect_site_type(request.url)

        # Convert config to YAML
        yaml_config = yaml.dump(config, default_flow_style=False)

        return {
            "config": config,
            "yaml_config": yaml_config,
            "site_type": site_type
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/validate-selectors")
async def validate_selectors(request: ValidateSelectorsRequest):
    """Validate selectors against a URL."""
    try:
        # Initialize the generator
        generator = ConfigGenerator()

        # Validate the selectors
        validation_results = await generator.validate_selectors(request.url, request.config)

        return validation_results
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/run-scraper")
async def run_scraper(request: RunScraperRequest):
    """Run the scraper with the provided configuration."""
    try:
        # Parse YAML config
        config = yaml.safe_load(request.config_yaml)

        # Create a temporary file for the config
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp_path = tmp.name
            yaml.dump(config, tmp)

        # Create output directory
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"scraped_data_{timestamp}.json")

        # Run the scraper using the config file
        process = await asyncio.create_subprocess_exec(
            "python", "crawl4ai_main.py",
            "-c", tmp_path,
            "-o", output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Scraper failed: {stderr.decode()}")

        return {
            "output_path": output_path,
            "status": "success",
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    finally:
        # Clean up the temporary config file
        if 'tmp_path' in locals():
            os.unlink(tmp_path)

# Start the server if run directly
if __name__ == "__main__":
    # Open the browser to the web UI
    webbrowser.open("http://localhost:8000")

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
