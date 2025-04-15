<select class="form-select" id="llmProvider" name="llm_provider">
  <option value="google">Google Gemini</option>
  <option value="anthropic">Anthropic Claude</option>
  <option value="openai">OpenAI GPT</option>
</select>

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
    