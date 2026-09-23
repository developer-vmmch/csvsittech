import os

source_file = 'templates/lab/master/import_diagnosis.html'
dest_file = 'templates/lab/master/import_lab_diagnosis.html'

with open(source_file, 'r') as f:
    content = f.read()

content = content.replace("api_diagnosis_import_template", "api_lab_diagnosis_import_template")
content = content.replace("api_diagnosis_import_preview", "api_lab_diagnosis_import_preview")
content = content.replace("api_diagnosis_import_process", "api_lab_diagnosis_import_process")
content = content.replace("lab:diagnosis_list", "lab:lab_diagnosis_list")
content = content.replace("lab:diagnosis_import_history", "lab:lab_diagnosis_import_history")
content = content.replace("Primary Diagnosis", "Diagnosis Master")
content = content.replace("lab_diagnosis_list_history", "lab_diagnosis_import_history")

with open(dest_file, 'w') as f:
    f.write(content)
