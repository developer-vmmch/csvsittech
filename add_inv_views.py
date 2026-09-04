import re

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    content = f.read()

view_classes = """
class InvestigationImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_investigation.html'
    menu_key = 'administration'

class InvestigationImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = InvestigationImportHistory
    template_name = 'lab/master/import_investigation_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_investigation_download_template"""

content = content.replace("def api_investigation_download_template", view_classes, 1)

with open(file_path, 'w') as f:
    f.write(content)
