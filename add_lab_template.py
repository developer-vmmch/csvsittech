import re

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    content = f.read()

template_code = """
def api_lab_diagnosis_download_template(request):
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame({
        'icd_code': ['BA00', 'BA01'],
        'diagnosis_name': ['Essential hypertension', 'Secondary hypertension'],
        'category': ['Cardiovascular', 'Cardiovascular'],
        'synonyms': ['High BP, HTN', ''],
        'class_kind': ['', ''],
        'active': ['Yes', 'Yes']
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="lab_diagnosis_import_template.xlsx"'
    return response
"""

# Insert after api_diagnosis_download_template
target_str = "    return response"

match = re.search(r"def api_diagnosis_download_template.*?return response", content, flags=re.DOTALL)
if match:
    insert_pos = match.end()
    new_content = content[:insert_pos] + "\n\n" + template_code.strip() + content[insert_pos:]
    with open(file_path, 'w') as f:
        f.write(new_content)
