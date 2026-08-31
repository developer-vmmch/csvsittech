import re

UTIL_CODE = """
from django.utils import timezone
from datetime import timedelta

def get_default_date_range(request, from_param='from_date', to_param='to_param'):
    from_raw = request.GET.get(from_param)
    to_raw = request.GET.get(to_param)
    
    if from_raw is None:
        from_date = (timezone.localdate() - timedelta(days=6)).strftime('%Y-%m-%d')
    else:
        from_date = from_raw.strip()
        
    if to_raw is None:
        to_date = timezone.localdate().strftime('%Y-%m-%d')
    else:
        to_date = to_raw.strip()
        
    return from_date, to_date
"""

def add_util(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    if 'get_default_date_range' not in content:
        # Find imports and add it after
        content = content.replace("from django.shortcuts", UTIL_CODE + "\nfrom django.shortcuts")
        with open(file_path, 'w') as f:
            f.write(content)

# 1. Update apps/patients/views.py
with open('apps/patients/views.py', 'r') as f:
    content = f.read()
if 'get_default_date_range' not in content:
    content = UTIL_CODE + "\n" + content

# Replace in export_patients_excel
content = re.sub(
    r"from_date = request\.GET\.get\('from_date'\)\s*to_date = request\.GET\.get\('to_date'\)",
    "from_date, to_date = get_default_date_range(request, 'from_date', 'to_date')",
    content
)

# Replace in PatientListView.get_queryset
content = re.sub(
    r"from_date = self\.request\.GET\.get\('from_date', ''\)\.strip\(\)\s*to_date = self\.request\.GET\.get\('to_date', ''\)\.strip\(\)",
    "from_date, to_date = get_default_date_range(self.request, 'from_date', 'to_date')",
    content
)
# Replace in PatientListView.get_context_data
content = re.sub(
    r"context\['from_date'\] = self\.request\.GET\.get\('from_date', ''\)\s*context\['to_date'\] = self\.request\.GET\.get\('to_date', ''\)",
    "context['from_date'], context['to_date'] = get_default_date_range(self.request, 'from_date', 'to_date')",
    content
)

# Replace in PatientSearchView.get_queryset
content = re.sub(
    r"q_from_date = self\.request\.GET\.get\('q_from_date', ''\)\.strip\(\)\s*q_to_date = self\.request\.GET\.get\('q_to_date', ''\)\.strip\(\)",
    "q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')",
    content
)
# Replace in PatientSearchView.get_context_data
content = re.sub(
    r"context\['q_from_date'\] = self\.request\.GET\.get\('q_from_date', ''\)\s*context\['q_to_date'\] = self\.request\.GET\.get\('q_to_date', ''\)",
    "context['q_from_date'], context['q_to_date'] = get_default_date_range(self.request, 'q_from_date', 'q_to_date')",
    content
)

# Replace in PatientReviewReportView.get_queryset
content = re.sub(
    r"q_from_date = self\.request\.GET\.get\('q_from_date', ''\)\.strip\(\)\s*q_to_date = self\.request\.GET\.get\('q_to_date', ''\)\.strip\(\)",
    "q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')",
    content
)
# Replace in PatientReviewReportView.get_context_data
content = re.sub(
    r"context\['q_from_date'\] = self\.request\.GET\.get\('q_from_date', ''\)\s*context\['q_to_date'\] = self\.request\.GET\.get\('q_to_date', ''\)",
    "context['q_from_date'], context['q_to_date'] = get_default_date_range(self.request, 'q_from_date', 'q_to_date')",
    content
)
with open('apps/patients/views.py', 'w') as f:
    f.write(content)


# 2. Update apps/lab/auto_trigger_views.py
with open('apps/lab/auto_trigger_views.py', 'r') as f:
    content = f.read()
if 'get_default_date_range' not in content:
    content = UTIL_CODE + "\n" + content
content = re.sub(
    r"from_date = request\.GET\.get\('from_date', ''\)\.strip\(\)\s*to_date = request\.GET\.get\('to_date', ''\)\.strip\(\)",
    "from_date, to_date = get_default_date_range(request, 'from_date', 'to_date')",
    content
)
with open('apps/lab/auto_trigger_views.py', 'w') as f:
    f.write(content)

# 3. Update apps/lab/views.py
with open('apps/lab/views.py', 'r') as f:
    content = f.read()
if 'get_default_date_range' not in content:
    content = UTIL_CODE + "\n" + content
content = re.sub(
    r"from_date = request\.GET\.get\('from_date'\)\s*to_date = request\.GET\.get\('to_date'\)",
    "from_date, to_date = get_default_date_range(request, 'from_date', 'to_date')",
    content
)
with open('apps/lab/views.py', 'w') as f:
    f.write(content)

