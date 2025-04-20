
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
    // Make sure we can access the iframe content
    const frameContent = iframe.contentDocument || iframe.contentWindow.document;
    
    inspectorEnabled = !inspectorEnabled;

    console.log("Inspector toggled:", inspectorEnabled); // Add debugging log
    
    if (inspectorEnabled) {
        this.textContent = 'Disable Inspector';
        this.classList.remove('btn-info');
        this.classList.add('btn-warning');

        // Enable inspector in iframe - THIS MIGHT BE THE ISSUE
        if (frameContent && frameContent.defaultView) {
            console.log("Attempting to enable inspector in iframe");
            try {
                frameContent.defaultView.toggleInspector(true);
            } catch (e) {
                console.error("Error toggling inspector:", e);
                // Fallback method to inject function if not available
                const script = frameContent.createElement('script');
                script.textContent = `
                    function toggleInspector(enable) {
                        console.log("Inspector enabled:", enable);
                        window.inspector = enable;
                    }
                    toggleInspector(true);
                `;
                frameContent.body.appendChild(script);
            }
        } else {
            console.error("Cannot access iframe content");
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

    try {
        const frameContent = iframe.contentDocument || iframe.contentWindow.document;
        console.log("Successfully accessed iframe document");
    } catch (e) {
        console.error("Cross-origin error:", e);
        alert("a. Try using the URL proxy option.");
    }
    // Initialize UI
    showLoading();
});
            