import os
import re

views_file = 'apps/lab/views.py'
with open(views_file, 'r') as f:
    content = f.read()

# Add models import if not there
if 'from django.db import models' not in content:
    content = content.replace('from django.db import transaction', 'from django.db import transaction, models')

def add_pagination(class_name, search_fields):
    q_filter = " | ".join([f"models.Q({f}__icontains=search)" for f in search_fields])
    
    # We replace the context_object_name line or template_name line with the pagination logic
    # Find the class block
    pattern = r"(class " + class_name + r".*?context_object_name = '[^']+')\n"
    
    def repl(m):
        base = m.group(1)
        if "paginate_by =" in base:
            return base + "\n"
            
        logic = f"""
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter({q_filter})
        return qs
"""
        return base + logic
        
    return re.sub(pattern, repl, content, flags=re.DOTALL)

content = add_pagination('DiagnosisListView', ['name', 'code', 'chapter'])
content = add_pagination('LabDiagnosisListView', ['name', 'code'])
content = add_pagination('InvestigationListView', ['name', 'code'])
content = add_pagination('ParameterListView', ['name', 'code'])
content = add_pagination('AgeGroupListView', ['name'])
content = add_pagination('InvestigationParameterMappingView', ['investigation__name', 'parameter__name'])

with open(views_file, 'w') as f:
    f.write(content)
