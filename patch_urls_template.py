import os

URLS_PATH = r"C:\Users\Admin\Desktop\erp1\apps\lab\urls.py"
TEMPLATE_PATH = r"C:\Users\Admin\Desktop\erp1\templates\lab\orders\order_entry.html"

with open(URLS_PATH, 'r') as f:
    content = f.read()

# Add import
if 'api_diagnosis_investigations' not in content:
    content = content.replace("from .views import (", "from .views import (\n    api_diagnosis_investigations,")

# Add URL
if 'api/diagnosis-investigations/' not in content:
    content = content.replace(
        "path('api/diagnosis/<int:pk>/delete/', api_diagnosis_delete, name='api_diagnosis_delete'),",
        "path('api/diagnosis/<int:pk>/delete/', api_diagnosis_delete, name='api_diagnosis_delete'),\n    path('api/diagnosis-investigations/', api_diagnosis_investigations, name='api_diagnosis_investigations'),"
    )

with open(URLS_PATH, 'w') as f:
    f.write(content)

with open(TEMPLATE_PATH, 'r') as f:
    template_content = f.read()

# Replace JS logic in template
JS_LOGIC_START = "$('#diagnosisSelect').on('change', function() {"
JS_LOGIC_END = "});"

new_js = """
$('#diagnosisSelect').on('change', function() {
            const diagId = $(this).val();
            const patientId = $('#patientId').val() || '';
            
            // Clear current selection
            $('.inv-checkbox').prop('checked', false);
            $('#suggestedInvestigations').hide();
            $('#suggestedChecks').empty();
            
            if (diagId) {
                fetch(`/lab/api/diagnosis-investigations/?diag_id=${diagId}&patient_id=${patientId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success' && data.investigations.length > 0) {
                            let html = '';
                            data.investigations.forEach(s => {
                                $(`input[value="${s.id}"]`).prop('checked', true);
                                html += `<span class="badge badge-green" style="background:#86efac; color:#14532d; padding:0.2rem 0.5rem; border-radius:4px; font-size:0.85rem;">${s.name}</span>`;
                            });
                            $('#suggestedChecks').html(html);
                            $('#suggestedInvestigations').show();
                        }
                    })
                    .catch(error => console.error('Error fetching investigations:', error));
            }
"""

if "$('#diagnosisSelect').on('change'" in template_content:
    import re
    template_content = re.sub(
        r"\$\('#diagnosisSelect'\)\.on\('change', function\(\) \{.*?\n            \}\n        \}\);",
        new_js + "\n        });",
        template_content,
        flags=re.DOTALL
    )

with open(TEMPLATE_PATH, 'w') as f:
    f.write(template_content)

print("Patch complete")
