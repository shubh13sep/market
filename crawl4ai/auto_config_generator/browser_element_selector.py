import json
import tempfile
import webbrowser
import os
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import asyncio
from playwright.async_api import async_playwright, ElementHandle, Page
import yaml
from bs4 import BeautifulSoup


async def open_element_selector(self) -> Dict[str, Dict[str, Any]]:
    """
    Open the interactive element selector and wait for user selections.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of selected elements
    """
    if not self.page:
        raise ValueError("Page not loaded. Call load_page() first.")
    import asyncio
    # Create a promise that will be resolved when selections are made
    selections_future = asyncio.Future()
    ready_future = asyncio.Future()
    close_future = asyncio.Future()

    self.selections_future = selections_future  # Store as instance variable
    self.ready_future = ready_future  # Store as instance variable
    self.close_future = close_future  # Store as instance variable

    # Expose function to receive selections from the page
    async def handle_selections(selections_str):
        try:
            print(f"Received selections from browser: {selections_str[:100]}...")

            # Parse the JSON string to get the selections object
            selections = {}
            if isinstance(selections_str, str):
                selections = json.loads(selections_str)
            elif isinstance(selections_str, dict):
                selections = selections_str

            print(f"Parsed {len(selections)} element selections")

            # Check if future is already done (to prevent invalid state error)
            if not selections_future.done():
                selections_future.set_result(selections)
            else:
                print("Warning: Future already resolved, ignoring duplicate selection")
        except Exception as e:
            print(f"Error processing selections: {e}")
            import traceback
            traceback.print_exc()

            # Only set exception if future isn't done yet
            if not selections_future.done():
                selections_future.set_exception(e)

    # # Expose function to know when the tool is ready
    # async def handle_ready():
    #     print("Element selector tool is ready!")
    #
    #     if not ready_future.done():
    #         ready_future.set_result(True)
    #
    # # Expose function to handle closing
    # async def handle_close():
    #     print("Element selector is being closed")
    #
    #     if not close_future.done():
    #         close_future.set_result(True)
    #
    #     # If selections weren't received, set a default empty result
    #     if not selections_future.done():
    #         selections_future.set_result({})
    #
    # # Expose functions to the page
    # await self.page.expose_function("saveElementSelections", handle_selections)
    # await self.page.expose_function("notifySelectorReady", handle_ready)
    # await self.page.expose_function("closeSelectorTool", handle_close)
    import asyncio
    # Wait for the tool to be ready
    try:
        # Add a timeout to the ready future
        print("Waiting for element selector to initialize...")
        ready_timeout = 30  # 30 seconds

        # Add periodic checking with console logs to detect ready state
        for i in range(ready_timeout * 2):  # Check every 0.5 seconds
            if ready_future.done():
                break

            # Check if ready via JavaScript evaluation
            if i % 4 == 0:  # Every 2 seconds
                try:
                    toolbar_exists = await self.page.evaluate("!!document.getElementById('crawl4ai-toolbar')")
                    if toolbar_exists:
                        print("Detected toolbar element - selector appears to be ready")
                        if not ready_future.done():
                            ready_future.set_result(True)
                        break
                except Exception as e:
                    print(f"Error checking ready state: {e}")

            await asyncio.sleep(0.5)

        if not ready_future.done():
            print("Ready state not detected within timeout")
            ready_future.set_result(False)

        # Only proceed if ready state was detected
        if await ready_future:
            print("\n*******************************************")
            print("* Element selector is ready!")
            print("* - Use the toolbar in the top-right corner")
            print("* - Click 'Select Element' to start selecting")
            print("* - When finished, click 'Generate Config'")
            print("*******************************************\n")

            # Wait for either selections or close
            max_wait_time = 1800  # 30 minutes timeout
            print(f"Waiting for selections (timeout: {max_wait_time}s)...")

            try:
                # Wait for either selections or close with timeout
                done, pending = await asyncio.wait(
                    [selections_future, close_future],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=max_wait_time
                )

                # Cancel any pending futures
                for future in pending:
                    future.cancel()

                if selections_future in done and selections_future.done():
                    try:
                        selections = selections_future.result()
                        print(f"Received selections: {selections.keys()}")
                        return selections
                    except Exception as e:
                        print(f"Error retrieving selections: {e}")
                        return {}
                elif close_future in done:
                    print("Selector was closed without making selections")
                    return {}
                else:
                    print("No selections received within timeout")
                    return {}

            except asyncio.TimeoutError:
                print(f"Selection process timed out after {max_wait_time} seconds")
                return {}
        else:
            print("Element selector failed to initialize properly")
            return {}

    except Exception as e:
        print(f"Error during element selection: {e}")
        import traceback
        traceback.print_exc()
        return {}


class BrowserElementSelector:
    """
    Browser-based element selector that allows users to visually select elements
    from a webpage to generate selectors for web scraping.
    """

    def __init__(self):
        """Initialize the element selector."""
        self.close_future = None
        self.ready_future = None
        self.selections_future = None
        self.page = None
        self.browser = None
        self.context = None
        self.selected_elements = {}
        self.target_url = None
        self.captured_headers = {}
        self.html_content = ""
        self.temp_html_file = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the browser."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )

    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None

        # Clean up temporary files
        if self.temp_html_file and os.path.exists(self.temp_html_file):
            os.unlink(self.temp_html_file)
            self.temp_html_file = None

    async def load_page(self, url: str, debug: bool = False) -> bool:
        """
        Load a webpage for element selection.

        Args:
            url: URL to load
            debug: Enable debugging console in browser

        Returns:
            bool: True if successful, False otherwise
        """
        self.target_url = url
        self.debug = debug

        try:
            # Create a new page
            self.page = await self.context.new_page()

            # Enable console logging for debugging
            self.page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
            print("Browser console logging enabled for debugging")

            # Setup header capture
            await self._setup_header_capture()

            # Navigate to the URL
            print(f"Navigating to {url}...")
            response = await self.page.goto(url, wait_until='networkidle')

            if not response:
                print(f"Failed to get response from {url}")
                return False

            print(f"Page loaded with status: {response.status}")

            # Get the HTML content
            self.html_content = await self.page.content()

            # Explicitly expose functions BEFORE injecting the selector tools
            # This ensures the functions are available when the script runs
            async def handle_ready():
                print("Element selector ready notification received!")
                if hasattr(self, 'ready_future') and self.ready_future and not self.ready_future.done():
                    self.ready_future.set_result(True)

            async def handle_selections(data):
                print(f"Received selections data: {str(data)[:100]}...")
                if hasattr(self, 'selections_future') and self.selections_future and not self.selections_future.done():
                    if isinstance(data, str):
                        data = json.loads(data)
                    self.selections_future.set_result(data)

            async def handle_close():
                print("Close notification received")
                if hasattr(self, 'close_future') and self.close_future and not self.close_future.done():
                    self.close_future.set_result(True)

                # If selections weren't received, set a default empty result
                if hasattr(self, 'selections_future') and self.selections_future and not self.selections_future.done():
                    self.selections_future.set_result({})

            # Expose functions to the page
            await self.page.expose_function("notifySelectorReady", handle_ready)
            await self.page.expose_function("saveElementSelections", handle_selections)
            await self.page.expose_function("closeSelectorTool", handle_close)

            # Add a simple test function to verify exposure works
            await self.page.expose_function("testFunction", lambda: print("Test function called"))

            # Wait a moment to ensure functions are properly exposed
            await asyncio.sleep(1)

            # Now inject the selector tools
            print("Injecting element selector tools...")
            await self._inject_selector_tools()

            # Verify functions are exposed
            is_ready_fn_available = await self.page.evaluate("typeof window.notifySelectorReady === 'function'")
            is_save_fn_available = await self.page.evaluate("typeof window.saveElementSelections === 'function'")
            is_close_fn_available = await self.page.evaluate("typeof window.closeSelectorTool === 'function'")

            print(f"Function availability: notifySelectorReady={is_ready_fn_available}, "
                  f"saveElementSelections={is_save_fn_available}, closeSelectorTool={is_close_fn_available}")

            # Call test function to verify
            await self.page.evaluate("window.testFunction()")

            print("Page ready for element selection")
            return True
        except Exception as e:
            print(f"Error loading page: {e}")
            return False

    async def _setup_header_capture(self):
        """Setup header capture for the page."""
        if not self.page:
            return

        # Track captured headers
        self.captured_headers = {}

        # Intercept all requests
        async def capture_headers(request):
            # Store request headers
            headers = request.headers
            for key, value in headers.items():
                # Skip internal headers
                if not key.startswith(('_', ':')) and key.lower() not in ['host', 'connection', 'content-length']:
                    self.captured_headers[key] = value

        # Listen for requests
        self.page.on("request", capture_headers)

    async def _inject_selector_tools(self):
        """Inject selection tools into the page."""
        if not self.page:
            return

        # Inject CSS for highlighting
        await self.page.add_style_tag(content="""
            .crawl4ai-highlight {
                outline: 2px dashed #ff5722 !important;
                background-color: rgba(255, 87, 34, 0.1) !important;
                cursor: pointer !important;
            }

            .crawl4ai-selected {
                outline: 2px solid #4caf50 !important;
                background-color: rgba(76, 175, 80, 0.1) !important;
            }

            #crawl4ai-toolbar {
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 9999;
                background-color: #ffffff;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                padding: 10px;
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            #crawl4ai-toolbar button {
                padding: 5px 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
            }

            .crawl4ai-primary-btn {
                background-color: #2196f3;
                color: white;
            }

            .crawl4ai-success-btn {
                background-color: #4caf50;
                color: white;
            }

            .crawl4ai-danger-btn {
                background-color: #f44336;
                color: white;
            }

            #crawl4ai-selection-list {
                position: fixed;
                bottom: 10px;
                right: 10px;
                z-index: 9999;
                background-color: #ffffff;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                padding: 10px;
                font-family: Arial, sans-serif;
                max-width: 300px;
                max-height: 300px;
                overflow-y: auto;
            }

            .crawl4ai-selection-item {
                margin-bottom: 5px;
                padding: 5px;
                border-left: 3px solid #2196f3;
                background-color: #f5f5f5;
            }

            .crawl4ai-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
            }

            .crawl4ai-modal-content {
                background-color: #ffffff;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                padding: 20px;
                width: 400px;
                max-width: 90%;
            }

            .crawl4ai-modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }

            .crawl4ai-modal-body {
                margin-bottom: 15px;
            }

            .crawl4ai-modal-footer {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }

            .crawl4ai-form-group {
                margin-bottom: 10px;
            }

            .crawl4ai-form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }

            .crawl4ai-form-group input, .crawl4ai-form-group select {
                width: 100%;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }

            .crawl4ai-checkbox {
                display: flex;
                align-items: center;
                gap: 5px;
            }

            .crawl4ai-checkbox input {
                width: auto;
            }
        """)

        # Inject JavaScript for element selection
        await self.page.add_script_tag(content="""
            // Crawl4AI element selector tool
(function() {
    console.log("Initializing Crawl4AI element selector...");
    let isSelecting = false;
    let hoveredElement = null;
    let selectedElements = {};
    let inFieldSelectionMode = false; // Track if we're selecting a field explicitly

    // Create toolbar
    function createToolbar() {
        console.log("Creating toolbar...");
        const toolbar = document.createElement('div');
        toolbar.id = 'crawl4ai-toolbar';
        toolbar.innerHTML = `
            <button id="crawl4ai-select-btn" class="crawl4ai-primary-btn">Select Element</button>
            <button id="crawl4ai-config-btn" class="crawl4ai-success-btn">Generate Config</button>
            <button id="crawl4ai-close-btn" class="crawl4ai-danger-btn">Close Selector</button>
        `;
        document.body.appendChild(toolbar);

        // Selection list container
        const selectionList = document.createElement('div');
        selectionList.id = 'crawl4ai-selection-list';
        selectionList.style.display = 'none';
        document.body.appendChild(selectionList);

        // Add event listeners
        document.getElementById('crawl4ai-select-btn').addEventListener('click', toggleSelector);
        document.getElementById('crawl4ai-config-btn').addEventListener('click', generateConfig);
        document.getElementById('crawl4ai-close-btn').addEventListener('click', closeTool);

        // Signal that we're ready
        if (typeof window.notifySelectorReady === 'function') {
            console.log("Notifying Python that selector is ready");
            try {
                window.notifySelectorReady();
            } catch (e) {
                console.error("Error notifying ready state:", e);
            }
        } else {
            console.warn("notifySelectorReady function not available");
            // Fallback: try to make window.notifySelectorReady available
            let checkReadyFunctionInterval = setInterval(() => {
                if (typeof window.notifySelectorReady === 'function') {
                    console.log("Found notifySelectorReady, notifying ready state");
                    try {
                        window.notifySelectorReady();
                        clearInterval(checkReadyFunctionInterval);
                    } catch (e) {
                        console.error("Error in interval notifying ready state:", e);
                    }
                }
            }, 500);

            // Stop checking after 10 seconds
            setTimeout(() => {
                clearInterval(checkReadyFunctionInterval);
            }, 10000);
        }
    }

    // Generate unique CSS selector for an element
    function getCssSelector(el) {
        if (!el) return '';

        // Check if element has an ID
        if (el.id) {
            return `#${el.id}`;
        }

        // Build a path to the element
        let path = [];
        let element = el;

        while (element.nodeType === Node.ELEMENT_NODE) {
            let selector = element.nodeName.toLowerCase();

            // Add classes (up to 2 for specificity but not too much brittleness)
            if (element.className) {
                const classes = Array.from(element.classList)
                    .filter(c => !c.startsWith('crawl4ai-'))
                    .slice(0, 2);

                if (classes.length > 0) {
                    selector += '.' + classes.join('.');
                }
            }

            // Add :nth-child only if needed for disambiguation
            let siblings = Array.from(element.parentNode.children)
                .filter(e => e.nodeName.toLowerCase() === selector.split('.')[0]);

            if (siblings.length > 1) {
                const index = siblings.indexOf(element) + 1;
                selector += `:nth-child(${index})`;
            }

            path.unshift(selector);

            // Stop at body
            if (element.parentNode === document.body || 
                element.parentNode.nodeName.toLowerCase() === 'body') {
                path.unshift('body');
                break;
            }

            element = element.parentNode;
        }

        return path.join(' > ');
    }

    // Toggle element selector
    function toggleSelector() {
        isSelecting = !isSelecting;

        const selectBtn = document.getElementById('crawl4ai-select-btn');

        if (isSelecting) {
            selectBtn.textContent = 'Cancel Selection';
            selectBtn.style.backgroundColor = '#f44336';
            
            // Create floating prompt for field selection if in field selection mode
            if (inFieldSelectionMode) {
                showFloatingPrompt('Click on an element to select as a field');
            }
        } else {
            selectBtn.textContent = 'Select Element';
            selectBtn.style.backgroundColor = '#2196f3';
            
            // Remove floating prompt if it exists
            removeFloatingPrompt();

            if (hoveredElement) {
                hoveredElement.classList.remove('crawl4ai-highlight');
                hoveredElement = null;
            }
        }
    }
    
    // Creates a floating prompt to guide users
    function showFloatingPrompt(message) {
        removeFloatingPrompt(); // Remove any existing prompt
        
        const prompt = document.createElement('div');
        prompt.id = 'crawl4ai-floating-prompt';
        prompt.style.cssText = `
            position: fixed;
            top: 70px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            font-family: Arial, sans-serif;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        `;
        prompt.textContent = message;
        document.body.appendChild(prompt);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            removeFloatingPrompt();
        }, 10000);
    }
    
    // Remove floating prompt
    function removeFloatingPrompt() {
        const prompt = document.getElementById('crawl4ai-floating-prompt');
        if (prompt) {
            prompt.remove();
        }
    }

    // Show selection naming modal
    function showNamingModal(element, selector) {
        // Remove any existing modals
        document.querySelectorAll('.crawl4ai-modal').forEach(modal => modal.remove());
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'crawl4ai-modal';
        modal.innerHTML = `
            <div class="crawl4ai-modal-content">
                <div class="crawl4ai-modal-header">
                    <h3>Name this selection</h3>
                    <button class="crawl4ai-danger-btn" id="crawl4ai-modal-close">×</button>
                </div>
                <div class="crawl4ai-modal-body">
                    <div class="crawl4ai-form-group">
                        <label for="crawl4ai-selection-name">Selection Name:</label>
                        <input type="text" id="crawl4ai-selection-name" placeholder="e.g., title, price, product_card">
                    </div>
                    <div class="crawl4ai-form-group">
                        <label>Selected Element:</label>
                        <input type="text" value="${selector}" readonly>
                    </div>
                    <div class="crawl4ai-form-group">
                        <label>Sample Content:</label>
                        <input type="text" value="${element.textContent.trim().substring(0, 50)}${element.textContent.trim().length > 50 ? '...' : ''}" readonly>
                    </div>
                    <div class="crawl4ai-form-group">
                        <div class="crawl4ai-checkbox">
                            <input type="checkbox" id="crawl4ai-is-group" />
                            <label for="crawl4ai-is-group">This is a group/container</label>
                        </div>
                    </div>
                    <div class="crawl4ai-form-group">
                        <div class="crawl4ai-checkbox">
                            <input type="checkbox" id="crawl4ai-is-multiple" />
                            <label for="crawl4ai-is-multiple">Extract multiple elements</label>
                        </div>
                    </div>
                    <div class="crawl4ai-form-group">
                        <label for="crawl4ai-attribute">Attribute (optional):</label>
                        <input type="text" id="crawl4ai-attribute" placeholder="e.g., href, src, alt">
                    </div>
                </div>
                <div class="crawl4ai-modal-footer">
                    <button class="crawl4ai-danger-btn" id="crawl4ai-cancel-btn">Cancel</button>
                    <button class="crawl4ai-success-btn" id="crawl4ai-save-btn">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Function to clean up
        function cleanup() {
            element.classList.remove('crawl4ai-selected');
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
        }

        // Add event listeners
        const closeBtn = document.getElementById('crawl4ai-modal-close');
        const cancelBtn = document.getElementById('crawl4ai-cancel-btn');
        const saveBtn = document.getElementById('crawl4ai-save-btn');
        
        closeBtn.addEventListener('click', function() {
            cleanup();
        });

        cancelBtn.addEventListener('click', function() {
            cleanup();
        });

        saveBtn.addEventListener('click', function() {
            const name = document.getElementById('crawl4ai-selection-name').value.trim();
            if (!name) {
                alert('Please enter a name for this selection');
                return;
            }

            // Check if name already exists
            if (selectedElements[name]) {
                alert('This name is already in use');
                return;
            }

            const isGroup = document.getElementById('crawl4ai-is-group').checked;
            const isMultiple = document.getElementById('crawl4ai-is-multiple').checked;
            const attribute = document.getElementById('crawl4ai-attribute').value.trim();

            // Store the selection
            selectedElements[name] = {
                selector: selector,
                isGroup: isGroup,
                isMultiple: isMultiple,
                sampleText: element.textContent.trim().substring(0, 50)
            };

            if (attribute) {
                selectedElements[name].attribute = attribute;
            }

            // If it's a group, we'll need to select fields later
            if (isGroup) {
                selectedElements[name].fields = {};
            }

            // Update the selection list
            updateSelectionList();

            // Close the modal
            cleanup();

            // If it's a group, prompt to select fields
            if (isGroup) {
                showAddFieldPrompt(name);
            }
        });
    }

    // Show prompt to add fields to a group
    function showAddFieldPrompt(groupName) {
        // Remove any existing modals
        document.querySelectorAll('.crawl4ai-modal').forEach(modal => modal.remove());
        
        const modal = document.createElement('div');
        modal.className = 'crawl4ai-modal';
        modal.innerHTML = `
            <div class="crawl4ai-modal-content">
                <div class="crawl4ai-modal-header">
                    <h3>Add Fields to Group</h3>
                </div>
                <div class="crawl4ai-modal-body">
                    <p>Would you like to add fields to the "${groupName}" group?</p>
                    <p>Fields are elements within the group container that you want to extract.</p>
                </div>
                <div class="crawl4ai-modal-footer">
                    <button class="crawl4ai-danger-btn" id="crawl4ai-later-btn">Later</button>
                    <button class="crawl4ai-success-btn" id="crawl4ai-add-fields-btn">Add Fields Now</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add event listeners
        document.getElementById('crawl4ai-later-btn').addEventListener('click', function() {
            document.body.removeChild(modal);
        });

        document.getElementById('crawl4ai-add-fields-btn').addEventListener('click', function() {
            document.body.removeChild(modal);
            addFieldToGroup(groupName);
        });
    }

    // Add a field to a group
    function addFieldToGroup(groupName) {
        // Remove any existing modals
        document.querySelectorAll('.crawl4ai-modal').forEach(modal => modal.remove());
        
        // Show instruction modal
        const modal = document.createElement('div');
        modal.className = 'crawl4ai-modal';
        modal.id = 'crawl4ai-field-modal';
        modal.innerHTML = `
            <div class="crawl4ai-modal-content">
                <div class="crawl4ai-modal-header">
                    <h3>Add Field to ${groupName}</h3>
                    <button class="crawl4ai-danger-btn" id="crawl4ai-field-modal-close">×</button>
                </div>
                <div class="crawl4ai-modal-body">
                    <p>Click on an element <strong>within</strong> the ${groupName} container to add it as a field.</p>
                    <div class="crawl4ai-form-group">
                        <label for="crawl4ai-field-name">Field Name:</label>
                        <input type="text" id="crawl4ai-field-name" placeholder="e.g., title, price, image">
                    </div>
                    <div class="crawl4ai-form-group">
                        <div class="crawl4ai-checkbox">
                            <input type="checkbox" id="crawl4ai-field-is-multiple" />
                            <label for="crawl4ai-field-is-multiple">Extract multiple elements</label>
                        </div>
                    </div>
                    <div class="crawl4ai-form-group">
                        <label for="crawl4ai-field-attribute">Attribute (optional):</label>
                        <input type="text" id="crawl4ai-field-attribute" placeholder="e.g., href, src, alt">
                    </div>
                </div>
                <div class="crawl4ai-modal-footer">
                    <button class="crawl4ai-danger-btn" id="crawl4ai-field-cancel-btn">Cancel</button>
                    <button class="crawl4ai-primary-btn" id="crawl4ai-select-field-btn">Select Field</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add event listeners with proper cleanup
        const closeBtn = document.getElementById('crawl4ai-field-modal-close');
        const cancelBtn = document.getElementById('crawl4ai-field-cancel-btn');
        const selectFieldBtn = document.getElementById('crawl4ai-select-field-btn');
        
        // Function to clean up modal and state
        function cleanup() {
            // Remove modal
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
            
            // Reset state
            inFieldSelectionMode = false;
            removeFloatingPrompt();
        }
        
        // Close button handler
        closeBtn.addEventListener('click', function() {
            cleanup();
        });
        
        // Cancel button handler
        cancelBtn.addEventListener('click', function() {
            cleanup();
        });
        
        // Select field button handler
        selectFieldBtn.addEventListener('click', function() {
            const fieldName = document.getElementById('crawl4ai-field-name').value.trim();
            if (!fieldName) {
                alert('Please enter a name for this field');
                return;
            }

            // Check if field name already exists in the group
            if (selectedElements[groupName].fields[fieldName]) {
                alert('This field name is already in use in this group');
                return;
            }

            // Hide the modal temporarily and enable selector
            modal.style.display = 'none';
            isSelecting = true;
            inFieldSelectionMode = true;

            // Show floating prompt to guide the user
            showFloatingPrompt('Click on an element to select as a field');

            // Store current state to know we're selecting a field
            window.crawl4aiSelectingField = {
                groupName: groupName,
                fieldName: fieldName,
                isMultiple: document.getElementById('crawl4ai-field-is-multiple').checked,
                attribute: document.getElementById('crawl4ai-field-attribute').value.trim()
            };
            
            // Update the select button to reflect we're in field selection mode
            const selectBtn = document.getElementById('crawl4ai-select-btn');
            if (selectBtn) {
                selectBtn.textContent = 'Cancel Field Selection';
                selectBtn.style.backgroundColor = '#f44336';
            }
            
            console.log("Starting field selection for:", window.crawl4aiSelectingField);
        });
    }

    // Save selected field to a group
    function saveFieldToGroup(element, selector) {
        const fieldInfo = window.crawl4aiSelectingField;
        if (!fieldInfo) {
            console.error("No field selection in progress");
            return;
        }
        
        console.log("Saving field to group:", fieldInfo);

        // Store the field
        selectedElements[fieldInfo.groupName].fields[fieldInfo.fieldName] = {
            selector: selector,
            isMultiple: fieldInfo.isMultiple,
            sampleText: element.textContent.trim().substring(0, 30)
        };

        if (fieldInfo.attribute) {
            selectedElements[fieldInfo.groupName].fields[fieldInfo.fieldName].attribute = fieldInfo.attribute;
        }

        // Update the selection list
        updateSelectionList();

        // Close the field modal if it's still open
        const fieldModal = document.getElementById('crawl4ai-field-modal');
        if (fieldModal) {
            fieldModal.remove();
        }

        // Reset field selection state
        const oldFieldInfo = {...fieldInfo}; // Save for showing prompt
        window.crawl4aiSelectingField = null;
        inFieldSelectionMode = false;
        isSelecting = false;
        removeFloatingPrompt();

        // Show add another field prompt
        showAddAnotherFieldPrompt(oldFieldInfo.groupName);
    }

    // Show prompt to add another field
    function showAddAnotherFieldPrompt(groupName) {
        // Remove any existing modals
        document.querySelectorAll('.crawl4ai-modal').forEach(modal => modal.remove());
        
        const modal = document.createElement('div');
        modal.className = 'crawl4ai-modal';
        modal.innerHTML = `
            <div class="crawl4ai-modal-content">
                <div class="crawl4ai-modal-header">
                    <h3>Field Added Successfully</h3>
                </div>
                <div class="crawl4ai-modal-body">
                    <p>Would you like to add another field to the "${groupName}" group?</p>
                </div>
                <div class="crawl4ai-modal-footer">
                    <button class="crawl4ai-primary-btn" id="crawl4ai-done-btn">Done</button>
                    <button class="crawl4ai-success-btn" id="crawl4ai-another-field-btn">Add Another Field</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add event listeners
        const doneBtn = document.getElementById('crawl4ai-done-btn');
        const anotherFieldBtn = document.getElementById('crawl4ai-another-field-btn');
        
        // Done button - properly cleanup state and close the modal
        doneBtn.addEventListener('click', function() {
            // Remove the modal
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
            
            // Ensure we've completely reset the state
            window.crawl4aiSelectingField = null;
            inFieldSelectionMode = false;
            isSelecting = false;
            
            // Update UI to reflect state
            const selectBtn = document.getElementById('crawl4ai-select-btn');
            if (selectBtn) {
                selectBtn.textContent = 'Select Element';
                selectBtn.style.backgroundColor = '#2196f3';
            }
            
            // Remove any floating prompts
            removeFloatingPrompt();
            
            console.log("Field selection completed, state reset");
        });
        
        // Add another field button - close this modal and start new field selection
        anotherFieldBtn.addEventListener('click', function() {
            // Remove the modal
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
            
            // Small delay before starting the new field selection to ensure clean state
            setTimeout(() => {
                // Ensure we're in a clean state before starting new field selection
                window.crawl4aiSelectingField = null;
                inFieldSelectionMode = false;
                isSelecting = false;
                
                addFieldToGroup(groupName);
            }, 100);
        });
    }

    // Update the selection list display
    function updateSelectionList() {
        const container = document.getElementById('crawl4ai-selection-list');
        container.style.display = 'block';
        container.innerHTML = '<h4>Selected Elements</h4>';

        for (const [name, details] of Object.entries(selectedElements)) {
            const item = document.createElement('div');
            item.className = 'crawl4ai-selection-item';

            let content = `
                <div><strong>${name}</strong> ${details.isGroup ? '(Group)' : ''}</div>
                <div class="small">${details.selector}</div>
            `;

            if (details.isGroup && details.fields) {
                content += '<div style="margin-left: 10px; margin-top: 5px; border-left: 2px solid #ccc; padding-left: 5px;">';

                if (Object.keys(details.fields).length === 0) {
                    content += '<div class="small">No fields added yet</div>';
                } else {
                    for (const [fieldName, fieldDetails] of Object.entries(details.fields)) {
                        content += `
                            <div class="small"><strong>${fieldName}</strong></div>
                            <div class="small">${fieldDetails.selector}</div>
                        `;
                    }
                }

                content += `<button class="crawl4ai-primary-btn" style="margin-top: 5px; font-size: 12px;" onclick="window.crawl4aiAddField('${name}')">Add Field</button>`;
                content += '</div>';
            }

            item.innerHTML = content;
            container.appendChild(item);
        }
    }

    // Generate configuration
    function generateConfig() {
        if (Object.keys(selectedElements).length === 0) {
            alert('Please select at least one element before generating a configuration.');
            return;
        }

        try {
            console.log("Generating configuration from selections:", selectedElements);

            // First create a backup file download in case the communication fails
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(selectedElements, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", "crawl4ai_selections.json");
            document.body.appendChild(downloadAnchorNode);

            // Notify parent window that config is ready
            if (typeof window.saveElementSelections === 'function') {
                try {
                    console.log('Sending JSON with selections to Python backend');
                    // Convert the object to a JSON string to avoid serialization issues
                    const selectionsJson = JSON.stringify(selectedElements);
                    window.saveElementSelections(selectionsJson);
                    console.log('Sent selections to Python backend:', selectionsJson.substring(0, 100) + '...');

                    // Trigger the download as backup
                    downloadAnchorNode.click();
                    downloadAnchorNode.remove();

                    // Show confirmation
                    alert('Configuration generated successfully! A backup JSON file has also been downloaded.');
                } catch (err) {
                    console.error('Error sending selections to Python:', err);

                    // Trigger the backup file download
                    downloadAnchorNode.click();
                    downloadAnchorNode.remove();

                    alert('Error sending selections to Python. A backup JSON file has been downloaded.');
                }
            } else {
                console.warn('saveElementSelections function not available, using fallback');
                console.log('Functions available on window:', Object.keys(window).filter(k => typeof window[k] === 'function'));

                // Try using a more direct approach with postMessage
                try {
                    window.parent.postMessage({
                        type: 'saveElementSelections',
                        selections: selectedElements
                    }, '*');
                    console.log('Sent selections via postMessage');
                } catch (e) {
                    console.error('Error sending via postMessage:', e);
                }

                // Trigger the backup file download
                downloadAnchorNode.click();
                downloadAnchorNode.remove();

                alert('Configuration generated! A JSON file with your selections has been downloaded.');
            }
        } catch (error) {
            console.error('Error generating configuration:', error);
            alert('Error generating configuration: ' + error.message);
        }
    }

    // Close the selector tool
    function closeTool() {
        // Remove all crawl4ai elements
        document.querySelectorAll('[id^="crawl4ai-"]').forEach(el => el.remove());

        // Remove event listeners
        document.removeEventListener('mouseover', handleMouseOver, true);
        document.removeEventListener('mouseout', handleMouseOut, true);
        document.removeEventListener('click', handleClick, true);

        // Notify parent window
        if (window.closeSelectorTool) {
            try {
                window.closeSelectorTool();
                console.log("Notified Python that selector tool is closing");
            } catch (e) {
                console.error("Error notifying selector tool close:", e);
            }
        } else {
            console.warn("closeSelectorTool function not available");
        }
    }

    // Mouse over event handler
    function handleMouseOver(e) {
        if (!isSelecting) return;

        if (hoveredElement) {
            hoveredElement.classList.remove('crawl4ai-highlight');
        }

        hoveredElement = e.target;
        hoveredElement.classList.add('crawl4ai-highlight');

        // Prevent default to avoid any page interactions
        e.preventDefault();
        e.stopPropagation();
    }

    // Mouse out event handler
    function handleMouseOut(e) {
        if (!isSelecting) return;

        if (hoveredElement) {
            hoveredElement.classList.remove('crawl4ai-highlight');
            hoveredElement = null;
        }
    }

    // Click event handler
    function handleClick(e) {
        if (!isSelecting) return;

        const element = e.target;
        const selector = getCssSelector(element);

        // Add selection class
        element.classList.add('crawl4ai-selected');

        // Disable selecting temporarily
        isSelecting = false;

        // Check if we're selecting a field for a group
        if (inFieldSelectionMode && window.crawl4aiSelectingField) {
            console.log("Handling click for field selection");
            saveFieldToGroup(element, selector);
        } else {
            // Regular element selection
            showNamingModal(element, selector);

            // Update select button
            const selectBtn = document.getElementById('crawl4ai-select-btn');
            selectBtn.textContent = 'Select Element';
            selectBtn.style.backgroundColor = '#2196f3';
        }

        // Prevent default actions
        e.preventDefault();
        e.stopPropagation();
    }

    // Expose functions to window
    window.crawl4aiAddField = function(groupName) {
        console.log("Adding field to group:", groupName);
        // Reset state completely before adding a field
        window.crawl4aiSelectingField = null;
        inFieldSelectionMode = false;
        isSelecting = false;
        
        if (hoveredElement) {
            hoveredElement.classList.remove('crawl4ai-highlight');
            hoveredElement = null;
        }
        
        // Now start the field addition process
        addFieldToGroup(groupName);
    };

    // Debug helper function 
    window.logCrawl4AIState = function() {
        console.log("Current Crawl4AI state:", {
            isSelecting,
            inFieldSelectionMode,
            hoveredElement: hoveredElement ? hoveredElement.tagName : null,
            selectingField: window.crawl4aiSelectingField,
            selectedElements
        });
    };

    // Add event listeners
    document.addEventListener('mouseover', handleMouseOver, true);
    document.addEventListener('mouseout', handleMouseOut, true);
    document.addEventListener('click', handleClick, true);

    // Initialize
    createToolbar();

    // Set a timeout to ensure we notify that we're ready
    setTimeout(function() {
        if (typeof window.notifySelectorReady === 'function') {
            console.log("Sending delayed ready notification");
            try {
                window.notifySelectorReady();
            } catch (e) {
                console.error("Error sending delayed ready notification:", e);
            }
        } else {
            console.warn("notifySelectorReady function not available after timeout");
        }
        
        // Set up a global debug interval to help diagnose issues
        setInterval(() => {
            console.debug("Crawl4AI state:", {
                isSelecting,
                inFieldSelectionMode,
                selectingField: window.crawl4aiSelectingField ? true : false,
                selectedCount: Object.keys(selectedElements).length
                });
            }, 5000);
        }, 1000);
    })();
        """)

        # Wait a moment to ensure the script is properly initialized
        await asyncio.sleep(1)

        return True

    async def capture_headers(self) -> Dict[str, str]:
        """
        Get the captured headers from the page visit.

        Returns:
            Dict[str, str]: Captured headers
        """
        # Filter and clean headers
        essential_headers = {
            'User-Agent': self.captured_headers.get('User-Agent', ''),
            'Accept': self.captured_headers.get('Accept', '*/*'),
            'Accept-Language': self.captured_headers.get('Accept-Language', 'en-US,en;q=0.9'),
            'Referer': self.target_url
        }

        # Add other potentially useful headers
        for key, value in self.captured_headers.items():
            if key.lower() not in ['user-agent', 'accept', 'accept-language', 'referer',
                                   'host', 'connection', 'content-length', 'sec-']:
                essential_headers[key] = value

        return essential_headers

    async def open_element_selector(self) -> Dict[str, Dict[str, Any]]:
        """
        Open the interactive element selector and wait for user selections.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of selected elements
        """
        if not self.page:
            raise ValueError("Page not loaded. Call load_page() first.")

        # Create futures for communication
        self.selections_future = asyncio.Future()
        self.ready_future = asyncio.Future()
        self.close_future = asyncio.Future()

        # Inject a script to test if our functions are working correctly
        await self.page.evaluate("""
            console.log("Testing function exposure:");
            console.log("notifySelectorReady available:", typeof window.notifySelectorReady === 'function');
            console.log("saveElementSelections available:", typeof window.saveElementSelections === 'function');
            console.log("closeSelectorTool available:", typeof window.closeSelectorTool === 'function');

            if (typeof window.notifySelectorReady === 'function') {
                try {
                    window.notifySelectorReady();
                    console.log("Successfully called notifySelectorReady");
                } catch (e) {
                    console.error("Error calling notifySelectorReady:", e);
                }
            } else {
                console.error("notifySelectorReady function is not available!");
            }
        """)

        # Wait for the ready future with a timeout
        try:
            await asyncio.wait_for(self.ready_future, timeout=10)
            print("Element selector tool is ready")
        except asyncio.TimeoutError:
            print("Timed out waiting for element selector to be ready")
            # Try to force ready state
            self.ready_future.set_result(True)

        print("\n*******************************************")
        print("* Element selector is ready!")
        print("* - Use the toolbar in the top-right corner")
        print("* - Click 'Select Element' to start selecting")
        print("* - When finished, click 'Generate Config'")
        print("*******************************************\n")

        # Wait for selections with a timeout
        try:
            # Wait for either selections or close
            done, pending = await asyncio.wait(
                [self.selections_future, self.close_future],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=600  # 10 minute timeout
            )

            # Cancel any pending futures
            for future in pending:
                future.cancel()

            if self.selections_future in done and self.selections_future.done():
                result = self.selections_future.result()
                print(f"Received selections: {type(result)}")
                return result
            else:
                print("Selection process completed without selections")
                return {}
        except asyncio.TimeoutError:
            print("Selection process timed out")
            return {}
        except Exception as e:
            print(f"Error during element selection: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def create_config_from_selections(self, selections: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a configuration from user selections.

        Args:
            selections: Dictionary of selected elements

        Returns:
            Dict[str, Any]: Crawl4AI configuration
        """
        # Extract headers
        headers = await self.capture_headers()

        # Convert selections to Crawl4AI selectors
        extract_config = {}

        for name, details in selections.items():
            if details.get('isGroup', False):
                # Group selector
                group_config = {
                    "type": "group",
                    "multiple": details.get('isMultiple', True),
                    "container": details['selector'],
                    "fields": {}
                }

                # Add fields
                for field_name, field_details in details.get('fields', {}).items():
                    field_config = {
                        "type": "css",
                        "query": field_details['selector'],
                        "multiple": field_details.get('isMultiple', False)
                    }

                    if field_details.get('attribute'):
                        field_config["attribute"] = field_details['attribute']

                    group_config["fields"][field_name] = field_config

                extract_config[name] = group_config
            else:
                # Simple selector
                selector_config = {
                    "type": "css",
                    "query": details['selector'],
                    "multiple": details.get('isMultiple', False)
                }

                if details.get('attribute'):
                    selector_config["attribute"] = details['attribute']

                extract_config[name] = selector_config

        # Determine if JavaScript is needed
        js_needed = False

        # Check for common JS frameworks in the HTML
        js_indicators = [
            "Vue", "React", "Angular", "jQuery", "lazy", "dynamically",
            "infinite scroll", "ajax", "axios", "fetch("
        ]

        for indicator in js_indicators:
            if indicator.lower() in self.html_content.lower():
                js_needed = True
                break

        # Create the configuration
        config = {
            "url": self.target_url,
            "headers": headers,
            "render_js": js_needed,
            "stealth_mode": True,
            "extract": extract_config,
            "output_format": "json",
            "output_dir": "output"
        }

        return config

    async def save_config_to_file(self, config: Dict[str, Any], path: str) -> None:
        """
        Save configuration to a file.

        Args:
            config: Configuration to save
            path: Path to save the configuration
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        # Save configuration
        with open(path, 'w') as f:
            if path.endswith('.json'):
                json.dump(config, f, indent=2)
            else:
                yaml.dump(config, f, default_flow_style=False)

        print(f"Configuration saved to {path}")

    async def open_selector_in_browser(self) -> Dict[str, Dict[str, Any]]:
        """
        Save the current page to a temporary file and open it in the browser with the selector tool.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of selected elements
        """
        if not self.html_content:
            raise ValueError("No HTML content. Load a page first.")

        # Create a temporary HTML file
        fd, html_path = tempfile.mkstemp(suffix=".html")
        self.temp_html_file = html_path

        with os.fdopen(fd, 'w') as f:
            # Add selector scripts and styles
            soup = BeautifulSoup(self.html_content, 'html.parser')

            # Add selector styles
            style_tag = soup.new_tag('style')
            style_tag.string = """
                .crawl4ai-highlight {
                    outline: 2px dashed #ff5722 !important;
                    background-color: rgba(255, 87, 34, 0.1) !important;
                    cursor: pointer !important;
                }

                .crawl4ai-selected {
                    outline: 2px solid #4caf50 !important;
                    background-color: rgba(76, 175, 80, 0.1) !important;
                }

                #crawl4ai-toolbar {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    z-index: 9999;
                    background-color: #ffffff;
                    border-radius: 4px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                    padding: 10px;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                /* ... rest of CSS ... */
            """
            soup.head.append(style_tag)

            # Add selector script
            script_tag = soup.new_tag('script')
            script_tag.string = """
                // Crawl4AI element selector tool
                document.addEventListener('DOMContentLoaded', function() {
                    // ... JavaScript code ... 
                });
            """
            soup.body.append(script_tag)

            # Save the modified HTML
            f.write(str(soup))

        # Open the file in the browser
        webbrowser.open('file://' + html_path)

        print("\n*******************************************")
        print("* Element selector opened in your browser!")
        print("* - Use the toolbar in the top-right corner")
        print("* - Click 'Select Element' to start selecting")
        print("* - When finished, click 'Generate Config'")
        print("*******************************************\n")

        # This is just a placeholder - in a real implementation,
        # you would need a way to receive the selections from the browser
        # Perhaps using a small local server or a custom protocol

        # For now, we'll simulate waiting for user input
        print("Waiting for selections... (this is a simulation)")
        await asyncio.sleep(5)

        # Return dummy selections
        return {
            "title": {
                "selector": "h1.product-title",
                "isGroup": False,
                "isMultiple": False
            },
            "price": {
                "selector": "span.price",
                "isGroup": False,
                "isMultiple": False
            }
        }