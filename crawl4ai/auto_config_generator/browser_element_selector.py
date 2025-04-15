import asyncio
import json
import tempfile
import webbrowser
import os
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from playwright.async_api import async_playwright, ElementHandle, Page
import yaml
from bs4 import BeautifulSoup


class BrowserElementSelector:
    """
    Browser-based element selector that allows users to visually select elements
    from a webpage to generate selectors for web scraping.
    """

    def __init__(self):
        """Initialize the element selector."""
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

            # Enable console logging if debug is enabled
            if debug:
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

            # Inject element selector tool
            print("Injecting element selector tools...")
            await self._inject_selector_tools()

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
                let isSelecting = false;
                let hoveredElement = null;
                let selectedElements = {};

                // Create toolbar
                function createToolbar() {
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
                    } else {
                        selectBtn.textContent = 'Select Element';
                        selectBtn.style.backgroundColor = '#2196f3';

                        if (hoveredElement) {
                            hoveredElement.classList.remove('crawl4ai-highlight');
                            hoveredElement = null;
                        }
                    }
                }

                // Show selection naming modal
                function showNamingModal(element, selector) {
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

                    // Add event listeners
                    document.getElementById('crawl4ai-modal-close').addEventListener('click', () => {
                        document.body.removeChild(modal);
                        element.classList.remove('crawl4ai-selected');
                    });

                    document.getElementById('crawl4ai-cancel-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                        element.classList.remove('crawl4ai-selected');
                    });

                    document.getElementById('crawl4ai-save-btn').addEventListener('click', () => {
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
                        document.body.removeChild(modal);
                        element.classList.remove('crawl4ai-selected');

                        // If it's a group, prompt to select fields
                        if (isGroup) {
                            showAddFieldPrompt(name);
                        }
                    });
                }

                // Show prompt to add fields to a group
                function showAddFieldPrompt(groupName) {
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
                    document.getElementById('crawl4ai-later-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                    });

                    document.getElementById('crawl4ai-add-fields-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                        addFieldToGroup(groupName);
                    });
                }

                // Add a field to a group
                function addFieldToGroup(groupName) {
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

                    // Add event listeners
                    document.getElementById('crawl4ai-field-modal-close').addEventListener('click', () => {
                        document.body.removeChild(modal);
                    });

                    document.getElementById('crawl4ai-field-cancel-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                    });

                    document.getElementById('crawl4ai-select-field-btn').addEventListener('click', () => {
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

                        // Store current state to know we're selecting a field
                        window.crawl4aiSelectingField = {
                            groupName: groupName,
                            fieldName: fieldName,
                            isMultiple: document.getElementById('crawl4ai-field-is-multiple').checked,
                            attribute: document.getElementById('crawl4ai-field-attribute').value.trim()
                        };
                    });
                }

                // Save selected field to a group
                function saveFieldToGroup(element, selector) {
                    const fieldInfo = window.crawl4aiSelectingField;
                    if (!fieldInfo) return;

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

                    // Reset field selection state
                    window.crawl4aiSelectingField = null;

                    // Show add another field prompt
                    showAddAnotherFieldPrompt(fieldInfo.groupName);
                }

                // Show prompt to add another field
                function showAddAnotherFieldPrompt(groupName) {
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
                    document.getElementById('crawl4ai-done-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                    });

                    document.getElementById('crawl4ai-another-field-btn').addEventListener('click', () => {
                        document.body.removeChild(modal);
                        addFieldToGroup(groupName);
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
                        // First create a backup file download in case the communication fails
                        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(selectedElements, null, 2));
                        const downloadAnchorNode = document.createElement('a');
                        downloadAnchorNode.setAttribute("href", dataStr);
                        downloadAnchorNode.setAttribute("download", "crawl4ai_selections.json");
                        document.body.appendChild(downloadAnchorNode);

                        // Notify parent window that config is ready
                        console.log('Attempting to save element selections...');
                        console.log('Selected elements:', selectedElements);

                        if (typeof window.saveElementSelections === 'function') {
                            try {
                                // Convert the object to a JSON string to avoid serialization issues
                                const selectionsJson = JSON.stringify(selectedElements);
                                console.log('Calling saveElementSelections with JSON string...');
                                window.saveElementSelections(selectionsJson);
                                console.log('Successfully sent selections to Python backend');

                                // Show confirmation
                                alert('Configuration generated successfully! You can close this window.');
                            } catch (err) {
                                console.error('Error sending selections to Python:', err);

                                // Trigger the backup file download
                                downloadAnchorNode.click();
                                downloadAnchorNode.remove();

                                alert('Error sending selections to Python. A backup JSON file has been downloaded.');
                            }
                        } else {
                            console.warn('saveElementSelections function not available, using fallback');

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
                        window.closeSelectorTool();
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
                    if (window.crawl4aiSelectingField) {
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
                    addFieldToGroup(groupName);
                };

                // Add event listeners
                document.addEventListener('mouseover', handleMouseOver, true);
                document.addEventListener('mouseout', handleMouseOut, true);
                document.addEventListener('click', handleClick, true);

                // Initialize
                createToolbar();

                // Send ready message to parent
                if (window.notifySelectorReady) {
                    window.notifySelectorReady();
                }
            })();
        """)

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

        # Create a promise that will be resolved when selections are made
        selections_future = asyncio.Future()
        self.selections_future = selections_future  # Store as instance variable

        # Expose function to receive selections from the page
        async def handle_selections(selections_str):
            try:
                # Parse the JSON string to get the selections object
                selections = json.loads(selections_str) if isinstance(selections_str, str) else selections_str
                print(f"Received {len(selections)} element selections")

                # Check if future is already done (to prevent invalid state error)
                if not selections_future.done():
                    selections_future.set_result(selections)
                else:
                    print("Warning: Future already resolved, ignoring duplicate selection")
            except Exception as e:
                print(f"Error processing selections: {e}")
                # Only set exception if future isn't done yet
                if not selections_future.done():
                    selections_future.set_exception(e)

        await self.page.expose_function("saveElementSelections", handle_selections)

        # Expose function to know when the tool is ready
        ready_future = asyncio.Future()

        async def handle_ready():
            ready_future.set_result(True)

        await self.page.expose_function("notifySelectorReady", handle_ready)

        # Expose function to handle closing
        close_future = asyncio.Future()

        async def handle_close():
            close_future.set_result(True)
            # If selections weren't received, set a default empty result
            if not selections_future.done():
                selections_future.set_result({})

        await self.page.expose_function("closeSelectorTool", handle_close)

        # Wait for the tool to be ready
        try:
            await asyncio.wait_for(ready_future, timeout=30)

            print("\n*******************************************")
            print("* Element selector is ready!")
            print("* - Use the toolbar in the top-right corner")
            print("* - Click 'Select Element' to start selecting")
            print("* - When finished, click 'Generate Config'")
            print("*******************************************\n")

            # Wait for either selections or close
            done, pending = await asyncio.wait(
                [selections_future, close_future],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=600  # 10 minute timeout
            )

            # Cancel any pending futures
            for future in pending:
                future.cancel()

            if selections_future in done and selections_future.done():
                try:
                    return selections_future.result()
                except Exception as e:
                    print(f"Error retrieving selections: {e}")
                    return {}
            else:
                print("Selection timed out or was cancelled")
                return {}

        except asyncio.TimeoutError:
            print("Timed out waiting for element selector to initialize")
            return {}
        except Exception as e:
            print(f"Error during element selection: {e}")
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