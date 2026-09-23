import re
import os

file_path = 'apps/lab/urls.py'
with open(file_path, 'r') as f:
    content = f.read()

# Add imports
imports = """
    LabDiagnosisImportView, LabDiagnosisImportHistoryView,
    api_lab_diagnosis_download_template, api_lab_diagnosis_preview, api_lab_diagnosis_import,
"""
if "LabDiagnosisImportView" not in content:
    content = content.replace(
        "api_diagnosis_download_template, api_diagnosis_preview, api_diagnosis_import,",
        "api_diagnosis_download_template, api_diagnosis_preview, api_diagnosis_import,\n    " + imports.strip()
    )
    content = content.replace(
        "DiagnosisImportView, DiagnosisImportHistoryView,",
        "DiagnosisImportView, DiagnosisImportHistoryView,\n    LabDiagnosisImportView, LabDiagnosisImportHistoryView,"
    )

# Add URL paths
urls = """
    path('lab-diagnosis/import/', LabDiagnosisImportView.as_view(), name='lab_diagnosis_import'),
    path('lab-diagnosis/import/history/', LabDiagnosisImportHistoryView.as_view(), name='lab_diagnosis_import_history'),
    path('api/lab-diagnosis/import/template/', api_lab_diagnosis_download_template, name='api_lab_diagnosis_import_template'),
    path('api/lab-diagnosis/import/preview/', api_lab_diagnosis_preview, name='api_lab_diagnosis_import_preview'),
    path('api/lab-diagnosis/import/process/', api_lab_diagnosis_import, name='api_lab_diagnosis_import_process'),
"""
if "lab-diagnosis/import/" not in content:
    content = content.replace(
        "path('lab-diagnosis/<int:pk>/edit/', LabDiagnosisUpdateView.as_view(), name='lab_diagnosis_edit'),",
        "path('lab-diagnosis/<int:pk>/edit/', LabDiagnosisUpdateView.as_view(), name='lab_diagnosis_edit'),\n" + urls
    )

with open(file_path, 'w') as f:
    f.write(content)
