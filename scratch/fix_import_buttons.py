import re
import os

files_to_fix = {
    'investigation_list.html': 'investigation_import',
    'parameter_list.html': 'parameter_import',
    'agegroup_list.html': 'agegroup_import',
    'reference_range_grid.html': 'reference_range_import',
    'diagnosis_investigation_mapping.html': 'diagnosis_investigation_map_import'
}

base_path = 'templates/lab/master/'

for filename, url_name in files_to_fix.items():
    filepath = os.path.join(base_path, filename)
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    # Replace dummy button with a tag
    pattern = (
        r'<button type="button" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0\.35rem 0\.75rem;">\s*'
        r'<i class="bi bi-arrow-up"></i> Import\s*'
        r'</button>'
    )
    
    replacement = (
        f'<a href="{{% url \'lab:{url_name}\' %}}" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0.35rem 0.75rem; text-decoration: none;">\n'
        f'                    <i class="bi bi-arrow-up"></i> Import\n'
        f'                </a>'
    )
    
    content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w') as f:
        f.write(content)

print("Import buttons fixed for 5 files.")
