from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

import os
import json
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.lab.models import (
    ServiceRequest,
    ServiceRequestInvestigation,
    Investigation,
    Diagnosis,
    ServiceRequestDiagnosis
)
from apps.lab.services.work_order_service import sync_standard_investigation_masters

# Ensure masters are synced
sync_standard_investigation_masters()

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin_test', 'admin@test.com', 'pass123')

client = Client()
client.force_login(admin_user)

# Pick an existing ServiceRequest or ServiceRequestInvestigation
sri = ServiceRequestInvestigation.objects.filter(id=61).first()
if not sri:
    sri = ServiceRequestInvestigation.objects.first()

assert sri is not None, "Need at least one ServiceRequestInvestigation in DB"
print(f"Testing with ServiceRequestInvestigation ID={sri.id}, Test={sri.investigation.name}, Status={sri.status}")

# 1. Test GET /lab/work-orders/result/<id>/
resp = client.get(f'/lab/work-orders/result/{sri.id}/')
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
content = resp.content.decode('utf-8')

# Verify 9 columns exist in exact order
expected_headers = [
    'S.No', 'Req Status', 'Test Name', 'Doctor', 'Doc No', 'Test Code', 'Grpi', 'Grp', 'Select'
]
for h in expected_headers:
    assert h in content, f"Header '{h}' missing from table in result entry page"
print("✓ All 9 column headers present in result entry page")

# Verify Diagnosis and Clinical Remarks inputs exist
assert 'id="diagnosisInput"' in content, "diagnosisInput field missing from page"
assert 'id="clinicalRemarksInput"' in content, "clinicalRemarksInput field missing from page"
assert 'id="btnQuickSaveDiag"' in content, "btnQuickSaveDiag missing"
assert 'id="btnQuickSaveRemarks"' in content, "btnQuickSaveRemarks missing"
print("✓ Editable Diagnosis and Clinical Remarks inputs exist")

# 2. Test saving Diagnosis and Clinical Remarks via API
test_diag_name = "Type 2 Diabetes Mellitus with Neuropathy"
test_remarks = "Fasting blood sugar sample collected at 8:00 AM"

from django.urls import reverse

save_resp = client.post(
    reverse('lab:api_work_order_save_result', args=[sri.id]),
    data=json.dumps({
        'only_metadata': True,
        'diagnosis': test_diag_name,
        'clinical_remarks': test_remarks
    }),
    content_type='application/json'
)
assert save_resp.status_code == 200, f"Metadata save failed: {save_resp.content}"
save_data = save_resp.json()
assert save_data.get('status') == 'success'
print("✓ API only_metadata save returned success")

# Reload ServiceRequest from DB
sr = ServiceRequest.objects.get(id=sri.service_request.id)
assert sr.clinical_remarks == test_remarks, f"Clinical remarks not updated: {sr.clinical_remarks}"
srd = sr.diagnoses.first()
assert srd is not None and srd.diagnosis.name == test_diag_name, f"Diagnosis not updated: {srd}"
print(f"✓ DB verified: clinical_remarks='{sr.clinical_remarks}', diagnosis='{srd.diagnosis.name}'")

# 3. Reload GET page and check values are present in inputs
resp2 = client.get(f'/lab/work-orders/result/{sri.id}/')
content2 = resp2.content.decode('utf-8')
assert test_diag_name in content2, "Updated diagnosis not rendered in HTML"
assert test_remarks in content2, "Updated clinical remarks not rendered in HTML"
print("✓ Reloaded page contains updated Diagnosis and Clinical Remarks in HTML inputs")

# 4. Verify Work Orders table compact styles and patient id width
wo_resp = client.get('/lab/work-orders/')
assert wo_resp.status_code == 200
wo_content = wo_resp.content.decode('utf-8')
assert 'padding: 5px 7px;' in wo_content, "Work orders table padding 5px 7px missing"
assert 'PATIENT ID' in wo_content, "PATIENT ID column missing"
assert 'patient-id-link' in wo_content, "patient-id-link missing"
print("✓ Work orders page compact padding and PATIENT ID verified")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
