with open('templates/patients/import_patient.html', 'r') as f:
    content = f.read()

# Add step-progress div
progress_html = """
    <!-- Step 2.5: Progress -->
    <div id="step-progress" class="hidden">
        <div style="background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 2rem; max-width: 600px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; color: var(--accent-blue);">Patient Import</h3>
            <p id="prog-filename" style="color: #64748b; margin-bottom: 1.5rem; font-weight: bold;"></p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 0.5rem; margin-bottom: 1.5rem;">
                <div>Total Records</div><div style="font-weight: bold; text-align: right;" id="prog-total">0</div>
                <div>Processed</div><div style="font-weight: bold; text-align: right;" id="prog-processed">0</div>
                <div>Successfully Imported</div><div style="font-weight: bold; text-align: right; color: #166534;" id="prog-imported">0</div>
                <div>Skipped / Duplicate</div><div style="font-weight: bold; text-align: right; color: #854d0e;" id="prog-skipped">0</div>
                <div>Failed</div><div style="font-weight: bold; text-align: right; color: #991b1b;" id="prog-failed">0</div>
            </div>
            
            <div style="background: #e2e8f0; border-radius: 999px; height: 1.5rem; width: 100%; overflow: hidden; position: relative;">
                <div id="prog-bar" style="background: var(--accent-blue); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                <div id="prog-percent" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; text-align: center; font-size: 0.85rem; font-weight: bold; color: #334155; line-height: 1.5rem;">0.00%</div>
            </div>
            
            <div style="margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>Status: <strong id="prog-status" style="color: #f59e0b;">Starting...</strong></div>
            </div>
        </div>
    </div>
"""

# Inject before step-summary
content = content.replace('    <!-- Step 3: Summary -->', progress_html + '\n    <!-- Step 3: Summary -->')

js_old = """    function confirmImport() {
        if (!currentImportId) {
            alert("No valid import ID found.");
            return;
        }
        
        const btn = document.getElementById('btn-import');
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Importing (This may take a moment)...';
        btn.disabled = true;
        
        fetch('{% url "patients:api_import_process" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                import_id: currentImportId
            })
        })
        .then(response => {
            if (!response.ok) {
                // If it's a 413, that should technically not happen anymore since the body is just JSON with an ID
                if (response.status === 413) {
                    throw new Error("Payload Too Large");
                }
                return response.text().then(text => { throw new Error(text) });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                showSummary(data);
            } else {
                alert(data.message || 'Import failed');
                btn.innerHTML = '<i class="bi bi-upload"></i> Import Valid Data';
                btn.disabled = false;
            }
        })
        .catch(error => {
            alert(error.message || 'Error connecting to server');
            btn.innerHTML = '<i class="bi bi-upload"></i> Import Valid Data';
            btn.disabled = false;
        });
    }"""

js_new = """
    let pollInterval = null;
    
    function startPolling() {
        document.getElementById('step-preview').classList.add('hidden');
        document.getElementById('step-progress').classList.remove('hidden');
        document.getElementById('prog-filename').textContent = `File: ${currentFilename}`;
        
        const total = parseInt(document.getElementById('count-total').textContent) || 0;
        document.getElementById('prog-total').textContent = total;
        
        pollInterval = setInterval(() => {
            fetch(`{% url "patients:api_import_status" %}?import_id=${currentImportId}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    const imported = parseInt(data.imported) || 0;
                    const failed = parseInt(data.failed) || 0;
                    const skipped = parseInt(data.skipped) || 0;
                    const processed = imported + failed + skipped;
                    
                    document.getElementById('prog-processed').textContent = processed;
                    document.getElementById('prog-imported').textContent = imported;
                    document.getElementById('prog-failed').textContent = failed;
                    document.getElementById('prog-skipped').textContent = skipped;
                    
                    let pct = 0;
                    if (total > 0) {
                        pct = (processed / total) * 100;
                        if (pct > 100) pct = 100;
                    }
                    
                    document.getElementById('prog-bar').style.width = `${pct}%`;
                    document.getElementById('prog-percent').textContent = `${pct.toFixed(2)}%`;
                    document.getElementById('prog-status').textContent = data.job_status;
                    
                    if (data.job_status === 'Completed' || data.job_status === 'Failed') {
                        clearInterval(pollInterval);
                        if (data.job_status === 'Completed') {
                            setTimeout(() => { showSummary({imported: imported, failed: failed, duplicates: skipped}) }, 1000);
                        } else {
                            document.getElementById('prog-status').style.color = '#991b1b';
                            alert("Import encountered a critical failure. See history for details.");
                        }
                    }
                }
            })
            .catch(err => console.error('Error polling status:', err));
        }, 1500);
    }

    function confirmImport() {
        if (!currentImportId) {
            alert("No valid import ID found.");
            return;
        }
        
        fetch('{% url "patients:api_import_process" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                import_id: currentImportId
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                startPolling();
            } else {
                alert(data.message || 'Failed to start import');
            }
        })
        .catch(err => alert('Error connecting to server.'));
    }
"""

content = content.replace(js_old, js_new)

with open('templates/patients/import_patient.html', 'w') as f:
    f.write(content)

