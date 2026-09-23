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
from apps.lab.models import ServiceRequest, ServiceRequestInvestigation, Investigation

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
client = Client()
client.force_login(admin)

print("--- 1. Testing Work Orders HTML Page Elements & Styles ---")
resp = client.get('/lab/work-orders/')
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
content = resp.content.decode('utf-8')

# Verify Dedicated Patient ID search in filter row 1
assert 'id="f_patient_id"' in content, "Missing f_patient_id in filter row 1"
assert 'id="btn-search-pid"' in content, "Missing btn-search-pid search button"
assert 'Patient ID' in content, "Missing 'Patient ID' label"
assert 'id="btn-view-all"' in content, "Missing btn-view-all button"

# Verify Row 2 filters exist
assert 'id="f_service_type"' in content, "Missing f_service_type"
assert 'id="f_sample"' in content, "Missing f_sample"
assert 'id="f_sample_id"' in content, "Missing f_sample_id"
assert 'id="f_search_name"' in content, "Missing f_search_name"
assert 'id="f_doctor"' in content, "Missing f_doctor"
assert 'id="f_sort_by"' in content, "Missing f_sort_by"

# Verify Table Headers & Alignments
assert 'text-align: center;">S NO</th>' in content
assert 'text-align: center; white-space: nowrap;">PATIENT ID</th>' in content
assert 'text-align: left;">PATIENT NAME</th>' in content
assert 'text-align: center;">VNO</th>' in content
assert 'text-align: center;">AGE</th>' in content
assert 'text-align: center;">VTYPE</th>' in content
assert 'text-align: center;">SAMPLE ID</th>' in content
assert 'text-align: center;">VOUCHER NO</th>' in content
assert 'text-align: right;">AMOUNT</th>' in content
assert 'text-align: center;">BILL TIME</th>' in content
assert 'text-align: center;">SAMPLE DT</th>' in content
assert 'text-align: center;">IPNO</th>' in content

# Verify compact table padding and font size
assert 'padding: 5px 7px;' in content, "Missing compact padding: 5px 7px;"
assert 'font-size: 14px;' in content, "Missing font-size: 14px;"
assert 'table-layout: fixed;' in content, "Missing table-layout: fixed;"

# Verify Patient ID Link remains blue and underlined regardless of status
assert '.patient-id-link' in content
assert 'color: #0000ee !important;' in content
assert 'text-decoration: underline !important;' in content

# Verify JS rendering alignments
assert 'text-align: center; white-space: nowrap;' in content
assert 'text-align: left; font-weight: 500;' in content

print("✓ Work orders page HTML, CSS alignment, and typography verified successfully!")

print("\n--- 2. Testing API Search by Patient ID ---")
test_pid = "9999888877"
test_pname = "UniqueTestRahul123"
patient, _ = Patient.objects.get_or_create(
    patient_id=test_pid,
    defaults={'name': test_pname, 'age_years': 32, 'gender': 'Male'}
)
sr = ServiceRequest.objects.create(patient=patient, status='RECEIVED')
inv = Investigation.objects.first()
ServiceRequestInvestigation.objects.create(service_request=sr, investigation=inv, status='RECEIVED')

# Exact search
url = reverse('lab:api_work_orders_list')
api_resp = client.get(url, {'patient_id': test_pid})
assert api_resp.status_code == 200, f"Expected 200, got {api_resp.status_code}: {api_resp.content}"
data = api_resp.json()
wos = data.get('work_orders', [])
assert len(wos) > 0, "Expected at least 1 work order for patient_id"
assert any(w['patient_id'] == test_pid for w in wos), "Searched patient_id not found in results"
print(f"✓ Exact Patient ID search found {len(wos)} result(s)")

# Partial search
partial_pid = test_pid[:5]  # "99998"
api_resp_partial = client.get(url, {'patient_id': partial_pid})
assert api_resp_partial.status_code == 200
data_partial = api_resp_partial.json()
wos_partial = data_partial.get('work_orders', [])
assert any(w['patient_id'] == test_pid for w in wos_partial), "Partial search did not match"
print(f"✓ Partial Patient ID search ('{partial_pid}') found {len(wos_partial)} result(s)")

# Negative search: searching patient_id with patient name must not match
api_resp_neg = client.get(url, {'patient_id': 'UniqueTestRahul'})
data_neg = api_resp_neg.json()
wos_neg = data_neg.get('work_orders', [])
assert not any(w['patient_id'] == test_pid for w in wos_neg), "Patient ID search should NOT match on Patient Name"
print("✓ Patient ID search strictly searches Patient ID, not Patient Name!")

# Search Name filters by patient name
api_resp_name = client.get(url, {'search_name': 'UniqueTestRahul'})
data_name = api_resp_name.json()
wos_name = data_name.get('work_orders', [])
assert any(w['patient_id'] == test_pid for w in wos_name), "Search Name should match on Patient Name"
print(f"✓ Search Name ('UniqueTestRahul') correctly found {len(wos_name)} result(s)")

# Clean up test record
sr.delete()
patient.delete()

print("\nALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!")
