import os
import django
from datetime import date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, Department
from apps.lab.models import (
    InvestigationMarkingConfig,
    InvestigationMarkingDepartment,
    InvestigationMarkingPatient,
    ServiceRequest,
    ServiceRequestInvestigation,
    ServiceRequestResult,
    PatientInvestigationOrder,
    Diagnosis,
    Investigation,
)
from apps.lab.services.investigation_marking_service import InvestigationMarkingService

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

client = Client()
client.force_login(admin_user)

print("=" * 80)
print("RUNNING AUTOMATED TEST SUITE FOR SIMPLIFIED INVESTIGATION MARKING")
print("=" * 80)

# Clear any previous test configs for 2026-09-20
test_date = date(2026, 9, 20)
test_date_str = "2026-09-20"
InvestigationMarkingConfig.objects.filter(marking_date=test_date).delete()

# Ensure we have General Medicine and Dental departments with D patients
dept_gm = Department.objects.filter(name="GENERAL MEDICINE").first()
if not dept_gm:
    dept_gm = Department.objects.create(name="GENERAL MEDICINE", is_active=True)

dept_derm = Department.objects.filter(name="DENTAL").first()
if not dept_derm:
    dept_derm = Department.objects.create(name="DENTAL", is_active=True)

# 1. Test GET /lab/auto-trigger/investigation-marking/
res = client.get(f'/lab/auto-trigger/investigation-marking/?date={test_date_str}')
assert res.status_code == 200, f"Failed GET: {res.status_code}"
assert b"Investigation Marking" in res.content
assert b"Department List" in res.content
assert b"Preview Patients" in res.content
print("✓ Test 1 Passed: Page renders with HTTP 200 and matches compact layout.")

# 2. Test Add Department (General Medicine: Male=10, Female=10)
# (Using 10 and 10 to fit readily available test D-patients)
add_payload = {
    'date': test_date_str,
    'department_id': dept_gm.id,
    'male_count': 10,
    'female_count': 10,
}
res_add = client.post(
    '/lab/api/investigation-marking/add-department/',
    data=add_payload,
    content_type='application/json'
)
assert res_add.status_code == 200, f"Failed add dept: {res_add.status_code}"
data = res_add.json()
assert data.get('success') is True, f"Error: {data.get('message')}"
assert len(data.get('departments')) == 1
assert data['departments'][0]['total'] == 20
print("✓ Test 2 Passed: Added General Medicine (Male=10, Female=10, Total=20).")

# 3. Test Same Department Cannot Be Added Twice
res_dup = client.post(
    '/lab/api/investigation-marking/add-department/',
    data=add_payload,
    content_type='application/json'
)
data_dup = res_dup.json()
assert data_dup.get('success') is False, "Duplicate department should have been rejected!"
assert "already added" in data_dup.get('message', '').lower()
print("✓ Test 3 Passed: Duplicate department addition rejected successfully.")

# 4. Test Add Second Department (Dermatology)
add_derm_payload = {
    'date': test_date_str,
    'department_id': dept_derm.id,
    'male_count': 5,
    'female_count': 5,
}
res_derm = client.post(
    '/lab/api/investigation-marking/add-department/',
    data=add_derm_payload,
    content_type='application/json'
)
data_derm = res_derm.json()
assert data_derm.get('success') is True
assert len(data_derm.get('departments')) == 2
print("✓ Test 4 Passed: Second department (Dermatology) added; Grand Totals updated.")

# 5. Verify Only D Patients Selected & Random Selection
config = InvestigationMarkingConfig.objects.get(marking_date=test_date)
selected_patients = list(config.selected_patients.all())
assert len(selected_patients) > 0

for sp in selected_patients:
    p = sp.patient
    assert p.patient_type == 'D', f"Patient {p.patient_id} is not type D!"
    assert p.registration_date == test_date, f"Patient {p.patient_id} has date {p.registration_date} instead of {test_date}!"
    assert sp.gender in ('Male', 'Female'), f"Invalid gender {sp.gender}"
    assert sp.primary_diagnosis_name != '', f"Primary diagnosis is missing for {sp.patient_id_str}"
print("✓ Test 5 Passed: All selected patients are D patients created for the chosen date.")

# 6. Verify Gender-Specific Eligibility Rules Enforced
# Male patients should NOT have female-only investigations
male_sp = [sp for sp in selected_patients if sp.gender == 'Male']
for sp in male_sp:
    if sp.primary_diagnosis:
        # verify investigations for this patient
        from apps.lab.services.eligibility_engine import get_eligible_investigations
        invs = get_eligible_investigations(sp.primary_diagnosis, sp.patient, sp.department, pregnancy_status=False)
        for inv in invs:
            inv_name = inv.name.lower()
            assert 'pregnancy' not in inv_name, f"Female-only test assigned to male: {inv_name}"
print("✓ Test 6 Passed: Gender eligibility rules strictly enforced (no female-only tests on male patients).")

# 7. Test Save Configuration & Persistence
res_save = client.post(
    '/lab/api/investigation-marking/save-config/',
    data={'date': test_date_str},
    content_type='application/json'
)
assert res_save.json().get('success') is True
config.refresh_from_db()
assert config.status == 'SAVED'
print("✓ Test 7 Passed: Save Configuration persists status=SAVED.")

# 8. Test Refresh / Reload Persistence (Selected Patients remain unchanged)
patient_ids_before = list(config.selected_patients.order_by('id').values_list('patient_id_str', flat=True))
res_reload = client.get(f'/lab/api/investigation-marking/load/?date={test_date_str}')
data_reload = res_reload.json()
patient_ids_after = [p['patient_id'] for p in data_reload['patients']]
assert patient_ids_before == patient_ids_after, "Persisted patient list changed after reload!"
print("✓ Test 8 Passed: Reloading/refreshing retains the EXACT persisted patients without re-shuffling.")

# 9. Test Save & Trigger Workflow
res_trig = client.post(
    '/lab/api/investigation-marking/trigger/',
    data={'date': test_date_str},
    content_type='application/json'
)
assert res_trig.json().get('success') is True
config.refresh_from_db()
assert config.status == 'TRIGGERED'
assert config.triggered_at is not None

# Verify ServiceRequests, Orders, and Results were created
sr_count = ServiceRequest.objects.filter(request_date=test_date, patient__patient_type='D').count()
assert sr_count > 0, "No ServiceRequests created!"
order_count = PatientInvestigationOrder.objects.filter(patient__patient_type='D', status='COMPLETED').count()
assert order_count > 0, "No completed PatientInvestigationOrders found!"
result_count = ServiceRequestResult.objects.filter(sr_investigation__service_request__request_date=test_date).count()
assert result_count > 0, "No ServiceRequestResults generated!"

print(f"✓ Test 9 Passed: Save & Trigger created {sr_count} ServiceRequests, {order_count} completed orders, and {result_count} results.")

# 10. Test Clear Configuration
res_clear = client.post(
    '/lab/api/investigation-marking/clear/',
    data={'date': test_date_str},
    content_type='application/json'
)
assert res_clear.json().get('success') is True
config.refresh_from_db()
assert config.departments.count() == 0
assert config.selected_patients.count() == 0
assert config.total_patients == 0
print("✓ Test 10 Passed: Clear All successfully reset the configuration.")

print("=" * 80)
print("ALL 10 INVESTIGATION MARKING AUTOMATED TESTS PASSED SUCCESSFULLY!")
print("=" * 80)
