import os
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
class DummyMessageStorage:
    def __init__(self, request=None):
        self.messages = []
    def add(self, level, message, extra_tags=''):
        self.messages.append(message)
    def __iter__(self):
        return iter(self.messages)
    def __len__(self):
        return len(self.messages)
    def __getitem__(self, idx):
        return self.messages[idx]
from apps.patients.models import Patient, PatientVisit, Department, DepartmentUnit
from apps.patients.views import PatientReviewView
from apps.patients.forms import PatientVisitForm

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.create_superuser('testadmin', 'test@vmmch.com', 'admin123')

# Setup sample department & unit
dept_ent = Department.objects.filter(name__iexact='ENT').first()
if not dept_ent:
    dept_ent = Department.objects.create(name='ENT', code='ENT', is_active=True)
unit_ent = dept_ent.units.first()
if not unit_ent:
    unit_ent = DepartmentUnit.objects.create(department=dept_ent, unit_name='UNIT 1 (ENT)', code='ENT-U1', is_active=True)

dept_gm = Department.objects.filter(name__iexact='GENERAL MEDICINE').first()
if not dept_gm:
    dept_gm = Department.objects.create(name='GENERAL MEDICINE', code='GENMED', is_active=True)
unit_gm = dept_gm.units.first()
if not unit_gm:
    unit_gm = DepartmentUnit.objects.create(department=dept_gm, unit_name='UNIT 2 (GENERAL MEDICINE)', code='GM-U2', is_active=True)

# Create or get test patient with known last visit
test_pid = '26148636'
patient, _ = Patient.objects.update_or_create(
    patient_id=test_pid,
    defaults={
        'name': 'GAYATHIRI S',
        'title': 'Miss',
        'gender': 'Female',
        'age_years': 25,
        'dob': date(2001, 6, 15),
        'op_number': 'OP26148636',
        'ipno': 'IP99881',
        'guardian_name': 'SUBRAMANIAN',
        'guardian_relationship': 'S/O',
        'mobile_no': '9876543210',
        'aadhar_card': '123456789012',
        'abha_id': '98765432101234',
        'street': 'Main Street',
        'village_area': 'Karaikal Town',
        'city': 'Karaikal',
        'state': 'Puducherry',
        'pincode': '609602',
        'blood_group': 'B+',
        'department_obj': dept_ent,
        'department': dept_ent.name,
        'unit_obj': unit_ent,
        'unit_doctor': unit_ent.unit_name,
        'created_by': user,
    }
)

# Create previous visit under ENT
from django.utils import timezone
from datetime import datetime

patient.visits.all().delete()
prev_visit = PatientVisit.objects.create(
    patient=patient,
    visit_no=1,
    visit_date=timezone.make_aware(datetime(2026, 6, 15, 10, 0)),
    department_obj=dept_ent,
    department=dept_ent.name,
    unit_obj=unit_ent,
    unit_doctor=unit_ent.unit_name,
    visit_type='OP',
    category='CONSULTATION',
    ipno='',
    reg_fees=0.0,
    created_by=user,
)

factory = RequestFactory()

def run_tests():
    print("=== STARTING PATIENT REVIEW VERIFICATION TESTS ===")
    
    # A. Patient Id search
    req_pid = factory.get(f'/patients/review/?search_type=patient_id&search_query={test_pid}')
    req_pid.user = user
    setattr(req_pid, '_messages', DummyMessageStorage(req_pid))
    resp_pid = PatientReviewView.as_view()(req_pid)
    assert resp_pid.status_code == 200
    ctx_pid = resp_pid.context_data
    assert ctx_pid['patient'] == patient, "Test A Failed: Patient not found by Patient ID"
    print("Test A PASSED: Patient Id search works correctly.")

    # B. OP No search
    req_op = factory.get(f'/patients/review/?search_type=op_no&search_query={patient.op_number}')
    req_op.user = user
    setattr(req_op, '_messages', DummyMessageStorage(req_op))
    resp_op = PatientReviewView.as_view()(req_op)
    assert resp_op.status_code == 200
    ctx_op = resp_op.context_data
    assert ctx_op['patient'] == patient, "Test B Failed: Patient not found by OP No"
    assert ctx_op['search_type'] == 'op_no'
    print("Test B PASSED: OP No search works correctly.")

    print("Debug last_visit:", ctx_pid['last_visit'], ctx_pid['last_visit'].visit_date if ctx_pid['last_visit'] else None)
    assert ctx_pid['last_visit'].visit_date.date() == date(2026, 6, 15), "Test C Failed: Last visit date mismatch"
    print("Test C PASSED: Last Visit Date populated correctly.")

    # D. Last Visit Department population
    assert ctx_pid['last_visit'].department == 'ENT', "Test D Failed: Last visit department mismatch"
    print("Test D PASSED: Last Visit Department populated correctly.")

    # E. Last Visit Unit population
    assert ctx_pid['last_visit'].unit_doctor == 'UNIT 1 (ENT)', "Test E Failed: Last visit unit mismatch"
    print("Test E PASSED: Last Visit Unit populated correctly.")

    # F. Last Visit fields in template rendered as readonly / disabled
    rendered_content = resp_pid.rendered_content
    assert 'id="ref_last_visit_date"' in rendered_content
    assert 'id="ref_last_visit_dept" class="form-select-compact" disabled' in rendered_content
    assert 'id="ref_last_visit_unit" class="form-select-compact" disabled' in rendered_content
    print("Test F PASSED: Last Visit reference fields are readonly / disabled.")

    # G. New Visit Department can differ from Last Visit Department
    # Check that initial visit_form department_obj is empty (not auto-copied to ENT)
    visit_form = ctx_pid['visit_form']
    assert visit_form.initial.get('department_obj') is None, f"Test G Failed: Department was auto-copied into initial! {visit_form.initial}"
    print("Test G PASSED: New Visit Department is NOT auto-copied from Last Visit.")

    # Post a new review visit under GENERAL MEDICINE (differs from ENT)
    post_data_valid = {
        'patient_id_hidden': patient.id,
        'department_obj': dept_gm.id,
        'unit_obj': unit_gm.id,
        'visit_type': 'OP',
        'reg_fees': '0.0',
        'age_years': '25',
    }
    req_post = factory.post('/patients/review/', post_data_valid)
    req_post.user = user
    setattr(req_post, '_messages', DummyMessageStorage(req_post))
    resp_post = PatientReviewView.as_view()(req_post)
    print("Post messages:", req_post._messages.messages)
    print("Visits:", list(patient.visits.values('id', 'visit_no', 'department')))
    new_visit = patient.visits.order_by('-visit_no').first()
    assert new_visit.visit_no == 2
    assert new_visit.department == 'GENERAL MEDICINE'
    assert new_visit.unit_doctor == unit_gm.unit_name
    print(f"Test G2 PASSED: New visit created under {new_visit.department} ({new_visit.unit_doctor}) successfully while last visit was ENT.")

    # H. Age 99 accepted
    post_age_99 = {
        'patient_id_hidden': patient.id,
        'department_obj': dept_gm.id,
        'unit_obj': unit_gm.id,
        'visit_type': 'OP',
        'reg_fees': '0.0',
        'age_years': '99',
    }
    req_post_99 = factory.post('/patients/review/', post_age_99)
    req_post_99.user = user
    storage_99 = DummyMessageStorage(req_post_99)
    setattr(req_post_99, '_messages', storage_99)
    resp_99 = PatientReviewView.as_view()(req_post_99)
    assert resp_99.status_code == 302
    patient.refresh_from_db()
    assert patient.age_years == 99, f"Age 99 should be accepted, got {patient.age_years}"
    print("Test H PASSED: Age 99 accepted.")

    # I. Age 100 rejected
    post_age_100 = {
        'patient_id_hidden': patient.id,
        'department_obj': dept_gm.id,
        'unit_obj': unit_gm.id,
        'visit_type': 'OP',
        'reg_fees': '0.0',
        'age_years': '100',
    }
    req_post_100 = factory.post('/patients/review/', post_age_100)
    req_post_100.user = user
    storage_100 = DummyMessageStorage(req_post_100)
    setattr(req_post_100, '_messages', storage_100)
    resp_100 = PatientReviewView.as_view()(req_post_100)
    messages_100 = [str(m) for m in storage_100]
    assert any("Age must be between 0 and 99" in m for m in messages_100), f"Age 100 was not rejected with proper message! Messages: {messages_100}"
    print("Test I PASSED: Age 100 rejected with error message.")

    # J. Negative age rejected
    post_age_neg = {
        'patient_id_hidden': patient.id,
        'department_obj': dept_gm.id,
        'unit_obj': unit_gm.id,
        'visit_type': 'OP',
        'reg_fees': '0.0',
        'age_years': '-1',
    }
    req_post_neg = factory.post('/patients/review/', post_age_neg)
    req_post_neg.user = user
    storage_neg = DummyMessageStorage(req_post_neg)
    setattr(req_post_neg, '_messages', storage_neg)
    resp_neg = PatientReviewView.as_view()(req_post_neg)
    messages_neg = [str(m) for m in storage_neg]
    assert any("Age must be between 0 and 99" in m for m in messages_neg), f"Negative age not rejected! Messages: {messages_neg}"
    print("Test J PASSED: Negative age (-1) rejected.")

    # K. Decimal age rejected
    post_age_dec = {
        'patient_id_hidden': patient.id,
        'department_obj': dept_gm.id,
        'unit_obj': unit_gm.id,
        'visit_type': 'OP',
        'reg_fees': '0.0',
        'age_years': '1.5',
    }
    req_post_dec = factory.post('/patients/review/', post_age_dec)
    req_post_dec.user = user
    storage_dec = DummyMessageStorage(req_post_dec)
    setattr(req_post_dec, '_messages', storage_dec)
    resp_dec = PatientReviewView.as_view()(req_post_dec)
    messages_dec = [str(m) for m in storage_dec]
    assert any("Age must be between 0 and 99" in m for m in messages_dec), f"Decimal age not rejected! Messages: {messages_dec}"
    print("Test K PASSED: Decimal age (1.5) rejected.")

    # Template structure checks
    # N. Guardian relationship displays compact values such as S/O only (no expanded "Son of")
    assert 'Son of' not in rendered_content, "Found 'Son of' in rendered template!"
    assert 'Daughter of' not in rendered_content, "Found 'Daughter of' in rendered template!"
    assert '<option value="S/O"' in rendered_content
    print("Test N PASSED: Guardian relationship shows compact values like S/O only.")

    # O. Name title and name appear as one combined row
    assert 'for="title_select">Name:<span class="text-danger">*</span></label>' in rendered_content
    assert 'id="display_name"' in rendered_content
    print("Test O PASSED: Name title and name appear together.")

    # P. No "Search By" heading
    assert 'Search By' not in rendered_content, "Found 'Search By' heading in template!"
    print("Test P PASSED: No 'Search By' heading.")

    # Q. No large "Last Visit Details" heading
    assert 'Last Visit Details' not in rendered_content, "Found 'Last Visit Details' heading in template!"
    print("Test Q PASSED: No large 'Last Visit Details' heading.")

    # R. No duplicate Last Visit Date
    assert rendered_content.count('Last Visit Date:') == 1, f"Expected exactly 1 Last Visit Date, found {rendered_content.count('Last Visit Date:')}"
    assert 'Last visit Dt:' not in rendered_content, "Found old duplicate 'Last visit Dt:'"
    print("Test R PASSED: Exactly one Last Visit Date on the page.")

    # S. Existing Visit Details functionality remains intact
    assert 'id_visit_department' in rendered_content
    assert 'id_visit_unit' in rendered_content
    assert 'id_visit_ward' in rendered_content
    assert 'id_reg_fees' in rendered_content
    assert 'View All visit details' in rendered_content
    assert 'Save' in rendered_content
    assert 'Reset' in rendered_content
    assert 'Print' in rendered_content
    assert 'Label - I' in rendered_content
    assert 'Print - OP' in rendered_content
    assert 'Label-A4' in rendered_content
    print("Test S PASSED: All visit details and action buttons intact.")

    print("\nALL 19 VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
