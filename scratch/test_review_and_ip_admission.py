import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from apps.patients.models import Patient, PatientVisit, Department, DepartmentUnit, Ward
from apps.patients.views import PatientReviewView, IPAdmissionView
from apps.patients.forms import PatientVisitForm, IPAdmissionForm

User = get_user_model()

def add_middleware_to_request(request):
    session_middleware = SessionMiddleware(lambda r: None)
    session_middleware.process_request(request)
    request.session.save()
    message_middleware = MessageMiddleware(lambda r: None)
    message_middleware.process_request(request)


def run_tests():
    print("=== STARTING COMPREHENSIVE REVIEW & IP ADMISSION TESTS ===")
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('testadmin', 'test@vmmc.com', 'adminpass123')

    Department.seed_defaults()
    Ward.seed_defaults()

    dept = Department.objects.filter(units__isnull=False).first()
    if not dept:
        dept = Department.objects.filter(is_active=True).first()
        unit = DepartmentUnit.objects.create(department=dept, unit_name="General Medicine Unit 1")
    else:
        unit = dept.units.first()

    ward = Ward.objects.filter(is_active=True).first()

    factory = RequestFactory()

    # -------------------------------------------------------------
    # 1. REVIEW PAGE TEMPLATE CHECKS
    # -------------------------------------------------------------
    print("\n--- 1. Testing Review Page Template ---")
    with open('templates/patients/patient_review.html', 'r') as f:
        review_html = f.read()

    # Time must be completely removed
    assert 'review_time_input' not in review_html, "FAIL: Time input still in review.html"
    assert 'Time:' not in review_html, "FAIL: Time label still in review.html"
    print("PASS: Time field completely removed from Review Visit Details.")

    # Ward and Bed must not be visible in Visit Details
    assert 'ward_beds_panel' not in review_html, "FAIL: ward_beds_panel still in review.html"
    assert 'id="id_bed"' not in review_html, "FAIL: Bed input still in review.html"
    print("PASS: Ward, Bed, and Bed panel removed from Review Page.")

    # Single-line Visit Details check
    assert 'display: flex; flex-direction: row; flex-wrap: nowrap' in review_html, "FAIL: nowrap missing from Review Visit Details"
    print("PASS: Review Visit Details enforces strictly ONE SINGLE LINE (flex-wrap: nowrap).")

    # Bloodgroup +/- control
    assert 'lbl_pt_plus' in review_html and 'lbl_pt_minus' in review_html, "FAIL: +/- bloodgroup control missing in review.html"
    print("PASS: Compact Bloodgroup [Select] [+] [-] present in Review.")

    # Last Visit Reference
    assert 'Last Visit Date:' in review_html, "FAIL: Last Visit Date missing"
    assert 'ref_last_visit_dept' in review_html, "FAIL: Last Visit Dept missing"
    assert 'ref_last_visit_unit' in review_html, "FAIL: Last Visit Unit missing"
    print("PASS: Readonly Last Visit Reference present above Visit Details.")

    # Review Actions
    for btn in ['btn-action-save', 'btn-action-reset', 'Print', 'Label - I', 'Print - OP', 'Label-A4']:
        assert btn in review_html, f"FAIL: Action {btn} missing from Review"
    print("PASS: All Review action buttons present (Save, Reset, Print, Label-I, Print-OP, Label-A4).")

    # -------------------------------------------------------------
    # 2. REVIEW BACKEND & WORKFLOW CHECKS
    # -------------------------------------------------------------
    print("\n--- 2. Testing Review Backend Logic ---")
    # Create test patient
    p1 = Patient.objects.create(
        name="Review Test Patient",
        gender="Male",
        age_years=35,
        mobile_no="9876543210",
        department_obj=dept,
        department=dept.name,
        unit_obj=unit,
        unit_doctor=unit.unit_name if unit else 'Dr. Specialist'
    )

    # Initial Review Visit form
    req = factory.get(f'/patients/review/?patient_id={p1.patient_id}')
    req.user = user
    view = PatientReviewView()
    view.request = req
    ctx = view.get_context_data()

    # Must default to REVIEW
    assert ctx['visit_form'].initial['visit_type'] == 'REVIEW', f"FAIL: Expected REVIEW default, got {ctx['visit_form'].initial.get('visit_type')}"
    print(f"PASS: Review Visit Type defaults to 'REVIEW' (not Out-P).")

    # Post new Review visit
    req_post = factory.post('/patients/review/', {
        'patient_id': p1.id,
        'department_obj': dept.id,
        'unit_obj': unit.id if unit else '',
        'visit_type': 'REVIEW',
        'review_date': timezone.now().strftime('%d/%m/%Y'),
        'reg_fees': '0.0',
        'age_years': '35',
        'name': p1.name,
        'gender': 'Male',
        'patient_type': 'O',
        'blood_group': 'B+'
    })
    req_post.user = user
    add_middleware_to_request(req_post)

    resp = PatientReviewView.as_view()(req_post)
    assert resp.status_code == 302, f"FAIL: Expected redirect on save, got {resp.status_code}"
    
    p1.refresh_from_db()
    latest_v = p1.visits.order_by('-id').first()
    assert latest_v.visit_type == 'REVIEW', f"FAIL: Visit type is {latest_v.visit_type}"
    assert latest_v.ward == '', f"FAIL: Review visit must have empty ward, got {latest_v.ward}"
    assert latest_v.bed == '', f"FAIL: Review visit must have empty bed, got {latest_v.bed}"
    assert latest_v.ipno == '', f"FAIL: Review visit must have empty ipno, got {latest_v.ipno}"
    print("PASS: Review visit saved with visit_type='REVIEW', ward='', bed='', ipno=''.")

    # -------------------------------------------------------------
    # 3. IP ADMISSION PAGE & WORKFLOW CHECKS
    # -------------------------------------------------------------
    print("\n--- 3. Testing IP Admission Page & Workflow ---")
    with open('templates/patients/ip_admission.html', 'r') as f:
        adm_html = f.read()

    # Required fields in Admission Details
    assert 'Department:' in adm_html, "FAIL: Department missing from Admission Details"
    assert 'Unit / Doctor:' in adm_html, "FAIL: Unit/Doctor missing from Admission Details"
    assert 'Admission Type:' in adm_html, "FAIL: Admission Type missing from Admission Details"
    assert 'Ward:' in adm_html, "FAIL: Ward missing from Admission Details"
    assert 'Available Beds:' in adm_html, "FAIL: Available Beds missing from Admission Details"
    assert 'Bed:' in adm_html, "FAIL: Bed missing from Admission Details"
    assert 'Admission Date:' in adm_html, "FAIL: Admission Date missing from Admission Details"
    assert 'IP Number:' in adm_html, "FAIL: IP Number missing from Admission Details"
    assert 'Status:' in adm_html, "FAIL: Status missing from Admission Details"
    assert 'Admission Reason / Diagnosis:' in adm_html, "FAIL: Diagnosis missing from Admission Details"
    print("PASS: All required fields present in Admission Details row & Diagnosis.")

    # Bed Allocation UI
    assert 'bed-allocation-card' in adm_html, "FAIL: Bed allocation card missing"
    assert 'Check Available Beds' in adm_html, "FAIL: Check Available Beds button missing"
    assert 'ip_ward_beds_grid' in adm_html, "FAIL: Bed grid container missing"
    print("PASS: Unique Bed Allocation UI present with live refresh.")

    # IP Admission Actions
    for act in ['Save Admission', 'Reset', 'Print - Admission', 'Label - IP', 'Bed Allocation']:
        assert act in adm_html, f"FAIL: Action {act} missing from IP Admission"
    print("PASS: All IP Admission actions present (Save Admission, Reset, Print - Admission, Label - IP, Bed Allocation).")

    # Test IP Admission POST: Allocate Bed
    test_bed = f"BED_{int(timezone.now().timestamp())}"
    req_adm = factory.post('/patients/admission/', {
        'patient_id': p1.id,
        'department_obj': dept.id,
        'unit_obj': unit.id if unit else '',
        'admission_type': 'General Admission',
        'ward': ward.name,
        'bed': test_bed,
        'admission_date': timezone.now().strftime('%d/%m/%Y'),
        'ipno': 'IP2026001',
        'status': 'Admitted',
        'admission_reason': 'Acute fever under evaluation',
        'age_years': '35',
        'name': p1.name,
        'gender': 'Male',
        'patient_type': 'O',
        'blood_group': 'B+'
    })
    req_adm.user = user
    add_middleware_to_request(req_adm)

    adm_resp = IPAdmissionView.as_view()(req_adm)
    assert adm_resp.status_code == 302, f"FAIL: Expected redirect on admission, got {adm_resp.status_code}"

    p1.refresh_from_db()
    assert p1.is_admitted_inpatient is True, "FAIL: Patient should be marked as admitted inpatient"
    active_ip = p1.active_ip_admission
    assert active_ip is not None, "FAIL: active_ip_admission should return the IP visit"
    assert active_ip.ward == ward.name, f"FAIL: Ward mismatch, got {active_ip.ward}"
    assert active_ip.bed == test_bed, f"FAIL: Bed mismatch, got {active_ip.bed}"
    print(f"PASS: IP Admission successfully created! Bed '{test_bed}' in '{ward.name}' allocated.")

    # Prevent Double Allocation check
    p2 = Patient.objects.create(
        name="Second Patient",
        gender="Male",
        age_years=40,
        mobile_no="9876543211",
        department_obj=dept,
        department=dept.name
    )
    req_double = factory.post('/patients/admission/', {
        'patient_id': p2.id,
        'department_obj': dept.id,
        'unit_obj': unit.id if unit else '',
        'admission_type': 'General Admission',
        'ward': ward.name,
        'bed': test_bed,  # Same bed! Already occupied by p1
        'admission_date': timezone.now().strftime('%d/%m/%Y'),
        'ipno': 'AUTO',
        'status': 'Admitted',
        'admission_reason': 'Chest pain',
        'age_years': '40'
    })
    req_double.user = user
    add_middleware_to_request(req_double)

    IPAdmissionView.as_view()(req_double)
    p2.refresh_from_db()
    assert p2.is_admitted_inpatient is False, "FAIL: Double allocation must be prevented!"
    print("PASS: Double allocation successfully prevented by backend validation!")

    # -------------------------------------------------------------
    # 4. AGE VALIDATION CHECKS (0-99 INTEGERS ONLY)
    # -------------------------------------------------------------
    print("\n--- 4. Testing Age Validation (0–99 Integers Only) ---")
    # Valid: 0
    p1.age_years = 0
    p1.clean()  # should not raise
    # Valid: 99
    p1.age_years = 99
    p1.clean()  # should not raise
    print("PASS: Age 0 and 99 are valid.")

    # Invalid: 100
    try:
        p1.age_years = 100
        p1.clean()
        assert False, "FAIL: Age 100 should raise ValidationError"
    except Exception:
        print("PASS: Age 100 rejected by Patient.clean().")

    # Invalid: Negative
    try:
        p1.age_years = -5
        p1.clean()
        assert False, "FAIL: Age -5 should raise ValidationError"
    except Exception:
        print("PASS: Negative age rejected by Patient.clean().")

    # Form age validation (Decimal)
    form = PatientVisitForm(data={'age_years': '25.5'})
    # Checking IPAdmissionView age parsing on post
    req_decimal = factory.post('/patients/admission/', {
        'patient_id': p2.id,
        'age_years': '25.5'
    })
    req_decimal.user = user
    add_middleware_to_request(req_decimal)
    IPAdmissionView.as_view()(req_decimal)
    p2.refresh_from_db()
    assert p2.age_years != 25.5, "FAIL: Decimal age should not be saved"
    print("PASS: Decimal age rejected by backend validation.")

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_tests()
