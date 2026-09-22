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
from django.urls import reverse
from apps.patients.models import Patient
from apps.lab.models import (
    ServiceRequest,
    ServiceRequestInvestigation,
    Investigation,
    InvestigationParameter,
    Parameter,
    ServiceRequestResult,
    Diagnosis,
    ServiceRequestDiagnosis
)
from apps.lab.services.work_order_service import (
    sync_standard_investigation_masters,
    get_investigation_test_code,
    get_investigation_grpi,
    get_investigation_grp,
    get_or_create_doc_no
)

sync_standard_investigation_masters()

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
client = Client()
client.force_login(admin)

print("--- 1. Testing Investigation Masters & Helper Functions ---")
cbc = Investigation.objects.filter(code__iexact='cbc').first()
esr = Investigation.objects.filter(code__iexact='esr').first()
lft = Investigation.objects.filter(code__iexact='lft').first()

if cbc:
    cbc_code = get_investigation_test_code(cbc)
    cbc_grpi = get_investigation_grpi(cbc)
    cbc_grp = get_investigation_grp(cbc)
    print(f"CBC: Code={cbc_code}, Grpi={cbc_grpi}, Grp={cbc_grp}")
    assert cbc_code == '00020537', f"Expected 00020537, got {cbc_code}"
    assert cbc_grpi == 22, f"Expected 22, got {cbc_grpi}"
    assert cbc_grp == 'G', f"Expected G, got {cbc_grp}"

if esr:
    esr_code = get_investigation_test_code(esr)
    esr_grpi = get_investigation_grpi(esr)
    esr_grp = get_investigation_grp(esr)
    print(f"ESR: Code={esr_code}, Grpi={esr_grpi}, Grp={esr_grp}")
    assert esr_code == '00020346', f"Expected 00020346, got {esr_code}"
    assert esr_grpi == 0, f"Expected 0, got {esr_grpi}"
    assert esr_grp == 'I', f"Expected I, got {esr_grp}"

if lft:
    lft_code = get_investigation_test_code(lft)
    lft_grpi = get_investigation_grpi(lft)
    lft_grp = get_investigation_grp(lft)
    print(f"LFT: Code={lft_code}, Grpi={lft_grpi}, Grp={lft_grp}")
    assert lft_code == '00020642', f"Expected 00020642, got {lft_code}"
    assert lft_grpi == 36, f"Expected 36, got {lft_grpi}"
    assert lft_grp == 'G', f"Expected G, got {lft_grp}"

print("✓ Master helper functions verified successfully!")

print("\n--- 2. Testing Result Entry View with Multi-Test Sample ---")
# Create a test patient & service request with 2 investigations: 1 RECEIVED, 1 PENDING
patient, _ = Patient.objects.get_or_create(
    patient_id='TEST_P_9999',
    defaults={'name': 'Test Comprehensive Patient', 'age_years': 45, 'gender': 'Male'}
)
sr = ServiceRequest.objects.create(
    patient=patient,
    status='RECEIVED',
    clinical_remarks='Initial clinical note'
)
inv_cbc = cbc or Investigation.objects.first()
inv_esr = esr or Investigation.objects.last()

sri_1 = ServiceRequestInvestigation.objects.create(
    service_request=sr,
    investigation=inv_cbc,
    status=ServiceRequestInvestigation.StatusChoices.RECEIVED
)
sri_2 = ServiceRequestInvestigation.objects.create(
    service_request=sr,
    investigation=inv_esr,
    status=ServiceRequestInvestigation.StatusChoices.PENDING
)

# Test Doc No behavior
doc_no_1 = get_or_create_doc_no(sri_1)
doc_no_2 = get_or_create_doc_no(sri_2)
print(f"sri_1 (RECEIVED) Doc No: {doc_no_1}")
print(f"sri_2 (PENDING) Doc No: {doc_no_2}")
assert doc_no_1 != '--' and doc_no_1.startswith('24'), f"Expected generated Doc No, got {doc_no_1}"
assert doc_no_2 == '--', f"Pending test should have '--', got {doc_no_2}"

# Render page for sri_1
resp = client.get(f'/lab/work-orders/result/{sri_1.id}/')
assert resp.status_code == 200
html = resp.content.decode('utf-8')

# Verify the 9 columns
for col in ['S.No', 'Req Status', 'Test Name', 'Doctor', 'Doc No', 'Test Code', 'Grpi', 'Grp', 'Select']:
    assert col in html, f"Missing column {col}"

# Verify doc_no_1 is in the HTML and '--' is in the HTML
assert doc_no_1 in html, f"Doc No {doc_no_1} not found in HTML"
assert '--' in html, "'--' for pending test not found in HTML"

# Verify CBC test code is in the HTML with leading zeroes
assert get_investigation_test_code(inv_cbc) in html, f"Test code {get_investigation_test_code(inv_cbc)} not in HTML"

print("✓ HTML renders 9 columns, correct Doc No (including '--' for pending), and exact Test Code with leading zeroes!")

print("\n--- 3. Testing Result Entry Save with Diagnosis & Parameter Validation ---")
# Attempt to save without parameters
param = inv_cbc.parameters.filter(is_active=True).first()
if param:
    bad_resp = client.post(
        reverse('lab:api_work_order_save_result', args=[sri_1.id]),
        data=json.dumps({
            'results': [],
            'diagnosis': 'Severe Anemia',
            'clinical_remarks': 'Fatigue and pallor'
        }),
        content_type='application/json'
    )
    assert bad_resp.status_code == 400, "Validation should have failed for missing parameters"
    print("✓ Validation correctly prevents saving missing required parameters")

    # Fill all active editable parameters
    from apps.lab.services.work_order_service import get_investigation_parameter_details
    details = get_investigation_parameter_details(sri_1)
    results_payload = [
        {'parameter_id': p['ip'].id, 'value': '10', 'remarks': 'OK'}
        for p in details['param_data'] if p['is_editable']
    ]

    good_resp = client.post(
        reverse('lab:api_work_order_save_result', args=[sri_1.id]),
        data=json.dumps({
            'results': results_payload,
            'diagnosis': 'Severe Anemia',
            'clinical_remarks': 'Fatigue and pallor'
        }),
        content_type='application/json'
    )
    assert good_resp.status_code == 200, f"Expected 200, got {good_resp.status_code}: {good_resp.content}"
    save_result = good_resp.json()
    assert save_result['status'] == 'success'
    print(f"✓ Save succeeded with all {len(results_payload)} parameters: {save_result}")

    # Check that Diagnosis & Clinical remarks persisted
    sr.refresh_from_db()
    assert sr.clinical_remarks == 'Fatigue and pallor'
    diag = sr.diagnoses.first()
    assert diag and diag.diagnosis.name == 'Severe Anemia'
    print(f"✓ Saved values verified: Diagnosis='{diag.diagnosis.name}', Remarks='{sr.clinical_remarks}'")

# Clean up test records
sr.delete()
patient.delete()
print("\n✓ Comprehensive tests finished successfully!")
