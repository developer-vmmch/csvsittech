import re

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    content = f.read()

# Add view classes
view_logic = """
class DiagnosisImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_diagnosis.html'
    menu_key = 'administration'

class DiagnosisImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = DiagnosisImportHistory
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'
"""
new_view_logic = """
class DiagnosisImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_diagnosis.html'
    menu_key = 'administration'

class DiagnosisImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = DiagnosisImportHistory
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

class LabDiagnosisImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_lab_diagnosis.html'
    menu_key = 'administration'

class LabDiagnosisImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = DiagnosisImportHistory
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'
"""
content = content.replace(view_logic.strip(), new_view_logic.strip())

# Extract functions dynamically using regex
template_match = re.search(r"def api_diagnosis_download_template.*?return response\n", content, flags=re.DOTALL)
preview_match = re.search(r"def api_diagnosis_preview.*?return JsonResponse\(\{'success': False.*?'\}\)\n", content, flags=re.DOTALL)
import_match = re.search(r"def api_diagnosis_import.*?return JsonResponse\(\{'success': False.*?'\}\)\n", content, flags=re.DOTALL)

if template_match and preview_match and import_match:
    lab_template = template_match.group(0).replace("api_diagnosis_download", "api_lab_diagnosis_download").replace("primary_diagnosis", "lab_diagnosis")
    
    lab_preview = preview_match.group(0).replace("api_diagnosis_preview", "api_lab_diagnosis_preview").replace("Diagnosis.objects", "LabDiagnosis.objects").replace("Diagnosis(", "LabDiagnosis(")
    
    lab_import = import_match.group(0).replace("api_diagnosis_import", "api_lab_diagnosis_import").replace("Diagnosis.objects", "LabDiagnosis.objects").replace("Diagnosis(", "LabDiagnosis(")

    # Insert before api_investigation_download_template
    insert_str = lab_template + "\n" + lab_preview + "\n" + lab_import + "\n"
    content = content.replace("def api_investigation_download_template", insert_str + "def api_investigation_download_template")
    
    # Add imports
    content = content.replace("from apps.lab.models import Diagnosis,", "from apps.lab.models import Diagnosis, LabDiagnosis,")
    
    with open(file_path, 'w') as f:
        f.write(content)
else:
    print("Failed to find api functions using regex")
