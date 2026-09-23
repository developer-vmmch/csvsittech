import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from apps.patients.models import Patient, PatientImportHistory
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import pandas as pd
import io
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()

from apps.patients.import_views import api_patient_import
from django.test import RequestFactory

history = PatientImportHistory.objects.create(
    file_name="VMMC_ERP_Patient_Import_Corrected.xlsx",
    total_records=35100,
    status='Staged'
)

# Attach the real file from the user's workspace
with open("/home/Loosifer/Documents/VMMCerp/VMMCerp/VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx", "rb") as f:
    history.upload_file.save("VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx", f)
history.save()

factory = RequestFactory()
request = factory.post('/api/import_process', data=json.dumps({'import_id': history.id}), content_type='application/json')
request.user = user

response = api_patient_import(request)
print(response.content)
