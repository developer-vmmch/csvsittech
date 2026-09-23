import os
import re

file_path = 'apps/lab/diagnosis_department_mapping_views.py'
with open(file_path, 'r') as f:
    content = f.read()

# Add pagination
search_logic = """
    qs = DiagnosisDepartmentMapping.objects.select_related('department', 'diagnosis').order_by('-id')
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(diagnosis__name__icontains=search)
        
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'departments': Department.objects.filter(is_active=True).order_by('name'),
        'diagnoses': Diagnosis.objects.filter(is_active=True).order_by('name'),
        'records': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': True
    }
"""

content = re.sub(
    r"    context = \{\n.*?    \}",
    search_logic.strip(),
    content,
    flags=re.DOTALL
)

with open(file_path, 'w') as f:
    f.write(content)
