import re

def remove_import(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove import button
    pattern = (
        r'<button type="button" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0\.35rem 0\.75rem;">\s*'
        r'<i class="bi bi-arrow-up"></i> Import\s*'
        r'</button>\s*'
    )
    content = re.sub(pattern, '', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

def remove_export(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove export button
    pattern = (
        r'<a href="\?export=excel" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0\.35rem 0\.75rem; text-decoration: none;">\s*'
        r'<i class="bi bi-arrow-down"></i> Export\s*'
        r'</a>\s*'
    )
    content = re.sub(pattern, '', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

# Lab Diagnosis (keep export, remove import)
remove_import('templates/lab/master/lab_diagnosis_list.html')

# Investigation Parameter Mapping (remove both)
remove_import('templates/lab/master/investigation_parameter_mapping.html')
remove_export('templates/lab/master/investigation_parameter_mapping.html')

# Diagnosis Department Mapping (remove both)
remove_import('templates/lab/master/diagnosis_department_mapping.html')
remove_export('templates/lab/master/diagnosis_department_mapping.html')

# Legacy Mapping (remove both)
remove_import('templates/lab/master/legacy_mapping.html')
remove_export('templates/lab/master/legacy_mapping.html')

# Diagnosis Investigation Mapping (keep import (it's an a tag now), remove export)
remove_export('templates/lab/master/diagnosis_investigation_mapping.html')

print("Fake buttons removed.")
