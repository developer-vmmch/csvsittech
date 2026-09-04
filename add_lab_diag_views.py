import re
import os

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    content = f.read()

# Copy DiagnosisImportView -> LabDiagnosisImportView
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
    model = DiagnosisImportHistory  # Reusing history model for simplicity, or create LabDiagnosisImportHistory if it exists
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'
"""
content = content.replace(view_logic.strip(), new_view_logic.strip())

# Extract api_diagnosis functions
def_preview = re.search(r"def api_diagnosis_preview.*?return JsonResponse.*?\}\)\n", content, flags=re.DOTALL)
def_import = re.search(r"def api_diagnosis_import.*?return JsonResponse\(\{'status': 'success', 'message': f'Import completed: \{imported\} added.*?\}\)\n", content, flags=re.DOTALL)
def_template = re.search(r"def api_diagnosis_download_template.*?return response\n", content, flags=re.DOTALL)

if def_preview and def_import and def_template:
    lab_preview = def_preview.group(0).replace("api_diagnosis_preview", "api_lab_diagnosis_preview").replace("Diagnosis.objects", "LabDiagnosis.objects").replace("Diagnosis(", "LabDiagnosis(")
    lab_import = def_import.group(0).replace("api_diagnosis_import", "api_lab_diagnosis_import").replace("Diagnosis.objects", "LabDiagnosis.objects").replace("Diagnosis(", "LabDiagnosis(")
    lab_template = def_template.group(0).replace("api_diagnosis_download_template", "api_lab_diagnosis_download_template").replace("primary_diagnosis_import_template", "diagnosis_master_import_template")
    
    # ensure it uses LabDiagnosis model import
    if "from apps.lab.models import Diagnosis," in content:
        content = content.replace("from apps.lab.models import Diagnosis,", "from apps.lab.models import Diagnosis, LabDiagnosis,")
    elif "from .models import Diagnosis" in content:
        content = content.replace("from .models import Diagnosis", "from .models import Diagnosis, LabDiagnosis")
    else:
        content = content.replace("import Diagnosis", "import Diagnosis, LabDiagnosis")
    
    content += "\n\n" + lab_template + "\n\n" + lab_preview + "\n\n" + lab_import
else:
    print("Failed to find api functions!")

with open(file_path, 'w') as f:
    f.write(content)
