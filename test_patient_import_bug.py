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

# Create an excel file
df = pd.DataFrame({
    'patient_id': ['2601019999'],
    'op_number': ['26109999'],
    'patient_title': ['Mr'],
    'first_name': ['John'],
    'last_name': ['Doe'],
    'full_name': ['John Doe'],
    'gender': ['Male'],
    'date_of_birth': ['1990-01-01'],
    'age': ['36'],
    'age_display': ['36'],
    'mobile_number': ['9876543210'],
    'alternate_phone': [''],
    'email': [''],
    'address_line1': ['123 Main St'],
    'address_line2': [''],
    'city': ['Karaikal'],
    'state': ['Puducherry'],
    'country': ['India'],
    'pincode': ['609602'],
    'blood_group': ['O+'],
    'marital_status': ['Single'],
    'guardian_title': ['Mr'],
    'guardian_name': ['Jack Doe'],
    'guardian_relation': ['F/O'],
    'guardian_phone': ['9876543214'],
    'emergency_contact_name': ['Jim Doe'],
    'emergency_contact_phone': ['9876543212'],
    'registration_date': ['2026-05-01']
})
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
output.seek(0)
file = SimpleUploadedFile("test.xlsx", output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

history = PatientImportHistory.objects.create(
    file_name="test.xlsx",
    total_records=1,
    status='Staged',
    upload_file=file
)

from django.test import RequestFactory
factory = RequestFactory()
request = factory.post('/api/import_process', data=json.dumps({'import_id': history.id}), content_type='application/json')
request.user = user

from apps.patients.import_views import api_patient_import
response = api_patient_import(request)
print(response.content)
