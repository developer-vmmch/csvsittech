import re

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    content = f.read()

view_classes = """
class LabDiagnosisImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_lab_diagnosis.html'
    menu_key = 'administration'

class LabDiagnosisImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = DiagnosisImportHistory
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

class DiagnosisImportView"""

content = content.replace("class DiagnosisImportView", view_classes, 1)

with open(file_path, 'w') as f:
    f.write(content)
