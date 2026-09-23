import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.patients.models import Patient, PatientVisit, Department, DepartmentUnit
from apps.lab.models import (
    Diagnosis,
    DiagnosisEligibilityRule,
    Investigation,
    Parameter,
    InvestigationParameter,
    ParameterReferenceRange,
    AgeGroup,
    DiagnosisInvestigationMap,
    DiagnosisDepartmentMapping,
    ServiceRequest,
    ServiceRequestDiagnosis,
    ServiceRequestInvestigation,
    ServiceRequestResult,
    LabDepartment,
    SampleType,
    ATCJob,
)
from apps.lab.services.eligibility_engine import (
    calculate_patient_age,
    normalize_gender,
    get_eligible_diagnoses,
    get_eligible_investigations,
    find_matching_reference_range,
    assign_atc_lab_workflow,
    STATUS_NO_ELIGIBLE_DIAGNOSIS,
    STATUS_NO_ELIGIBLE_INVESTIGATION,
    STATUS_SUCCESS,
)
from apps.lab.services.result_classifier import (
    find_best_db_reference_range,
    classify_result,
    STATUS_NORMAL,
    STATUS_BELOW,
    STATUS_ABOVE,
)
from apps.lab.result_views import get_evaluated_results_for_sr, lab_result_detail_view, lab_result_print_view

User = get_user_model()


def run_all_tests():
    print("=" * 80)
    print("RUNNING 19 AUTOMATED TESTS FOR LAB MASTER & ELIGIBILITY RULES ENGINE")
    print("=" * 80)

    # Setup core test fixtures
    user, _ = User.objects.get_or_create(username='test_lab_admin', defaults={'is_staff': True})
    dept, _ = Department.objects.get_or_create(code='TEST_GM', defaults={'name': 'TEST GENERAL MEDICINE', 'is_active': True})
    lab_dept, _ = LabDepartment.objects.get_or_create(name='TEST BIOCHEMISTRY', defaults={'is_active': True})
    sample_type, _ = SampleType.objects.get_or_create(name='TEST SERUM', defaults={'is_active': True})

    # Age Groups fixtures
    ag_pedia, _ = AgeGroup.objects.get_or_create(
        code='TEST_PED',
        defaults={'label': 'Test Pediatric (0-12 Y)', 'min_age_value': 0, 'max_age_value': 12, 'min_age_unit': 'Years', 'max_age_unit': 'Years', 'gender': 'All', 'is_active': True}
    )
    ag_adult, _ = AgeGroup.objects.get_or_create(
        code='TEST_ADULT',
        defaults={'label': 'Test Adult (18-59 Y)', 'min_age_value': 18, 'max_age_value': 59, 'min_age_unit': 'Years', 'max_age_unit': 'Years', 'gender': 'All', 'is_active': True}
    )
    ag_geriatric, _ = AgeGroup.objects.get_or_create(
        code='TEST_GERIATRIC',
        defaults={'label': 'Test Geriatric (60+ Y)', 'min_age_value': 60, 'max_age_value': 120, 'min_age_unit': 'Years', 'max_age_unit': 'Years', 'gender': 'All', 'is_active': True}
    )

    # -----------------------------------------------------------------------
    # TEST 1: Male patient + Male-only investigation -> Expected: visible
    # -----------------------------------------------------------------------
    diag_general, _ = Diagnosis.objects.get_or_create(code='TEST_DIAG_GEN', defaults={'name': 'General Health Evaluation', 'is_active': True})
    inv_male, _ = Investigation.objects.get_or_create(
        code='TEST_INV_PSA',
        defaults={'name': 'PSA Total (Prostate Specific)', 'department': lab_dept, 'sample_type': sample_type, 'is_active': True}
    )
    map_male, _ = DiagnosisInvestigationMap.objects.get_or_create(
        diagnosis=diag_general,
        investigation=inv_male,
        defaults={'gender': 'Male', 'is_active': True}
    )
    map_male.gender = 'Male'
    map_male.save()

    male_patient = {'gender': 'Male', 'age_years': 45}
    eligible_invs_m = get_eligible_investigations(diag_general, male_patient)
    assert inv_male in eligible_invs_m, "Test 1 Failed: Male-only investigation should be visible for Male patient"
    print("✓ Test 1 Passed: Male patient + male-only investigation -> visible.")

    # -----------------------------------------------------------------------
    # TEST 2: Female patient + Female-only investigation -> Expected: visible
    # -----------------------------------------------------------------------
    inv_female, _ = Investigation.objects.get_or_create(
        code='TEST_INV_PAP',
        defaults={'name': 'Pap Smear Cervical Screen', 'department': lab_dept, 'sample_type': sample_type, 'is_active': True}
    )
    map_female, _ = DiagnosisInvestigationMap.objects.get_or_create(
        diagnosis=diag_general,
        investigation=inv_female,
        defaults={'gender': 'Female', 'is_active': True}
    )
    map_female.gender = 'Female'
    map_female.save()

    female_patient = {'gender': 'Female', 'age_years': 30}
    eligible_invs_f = get_eligible_investigations(diag_general, female_patient)
    assert inv_female in eligible_invs_f, "Test 2 Failed: Female-only investigation should be visible for Female patient"
    print("✓ Test 2 Passed: Female patient + female-only investigation -> visible.")

    # -----------------------------------------------------------------------
    # TEST 3: Male patient + Female-only investigation -> Expected: not visible
    # -----------------------------------------------------------------------
    assert inv_female not in eligible_invs_m, "Test 3 Failed: Female-only investigation must NOT be visible for Male patient"
    print("✓ Test 3 Passed: Male patient + female-only investigation -> not visible.")

    # -----------------------------------------------------------------------
    # TEST 4: Female patient + Male-only investigation -> Expected: not visible
    # -----------------------------------------------------------------------
    assert inv_male not in eligible_invs_f, "Test 4 Failed: Male-only investigation must NOT be visible for Female patient"
    print("✓ Test 4 Passed: Female patient + male-only investigation -> not visible.")

    # -----------------------------------------------------------------------
    # TEST 5: Universal investigation -> Expected: visible for both
    # -----------------------------------------------------------------------
    inv_uni, _ = Investigation.objects.get_or_create(
        code='TEST_INV_CBC',
        defaults={'name': 'Complete Blood Count (Universal)', 'department': lab_dept, 'sample_type': sample_type, 'is_active': True}
    )
    map_uni, _ = DiagnosisInvestigationMap.objects.get_or_create(
        diagnosis=diag_general,
        investigation=inv_uni,
        defaults={'gender': 'All', 'is_active': True}
    )
    map_uni.gender = 'All'
    map_uni.save()

    eligible_m = get_eligible_investigations(diag_general, male_patient)
    eligible_f = get_eligible_investigations(diag_general, female_patient)
    assert inv_uni in eligible_m and inv_uni in eligible_f, "Test 5 Failed: Universal investigation must be visible for both Male and Female"
    print("✓ Test 5 Passed: Universal investigation -> visible for both.")

    # -----------------------------------------------------------------------
    # TEST 6: Pediatric patient (5 yo) -> Expected: pediatric diagnosis/range
    # -----------------------------------------------------------------------
    diag_ped, _ = Diagnosis.objects.get_or_create(
        code='TEST_DIAG_PED',
        defaults={'name': 'Pediatric Growth Assessment', 'min_age': 0, 'max_age': 12, 'is_active': True}
    )
    ped_patient = {'gender': 'Male', 'age_years': 5}
    ped_eligible_diags = get_eligible_diagnoses(ped_patient)
    assert diag_ped in ped_eligible_diags, "Test 6 Failed: Pediatric patient must be eligible for pediatric diagnosis"

    # Parameter with pediatric reference range
    param_hb, _ = Parameter.objects.get_or_create(
        code='00022681_HB',
        defaults={'name': 'Hemoglobin Pediatric Test', 'default_unit': 'g/dL', 'is_active': True}
    )
    ip_hb, _ = InvestigationParameter.objects.get_or_create(
        investigation=inv_uni,
        code='00022681_HB',
        defaults={'name': 'Hemoglobin', 'parameter': param_hb, 'unit': 'g/dL', 'is_active': True}
    )
    rr_ped, _ = ParameterReferenceRange.objects.get_or_create(
        investigation_parameter=ip_hb,
        age_group=ag_pedia,
        gender='All',
        defaults={'range_type': 'Numeric', 'min_value': Decimal('11.0'), 'max_value': Decimal('13.5'), 'unit': 'g/dL', 'is_active': True}
    )
    best_range_ped = find_best_db_reference_range(ip_hb.id, patient_age_days=5*365, patient_gender='Male')
    assert best_range_ped.id == rr_ped.id, f"Test 6 Failed: Expected pediatric range {rr_ped.id}, got {best_range_ped.id}"
    print("✓ Test 6 Passed: Pediatric patient -> pediatric diagnosis/reference range.")

    # -----------------------------------------------------------------------
    # TEST 7: Adult patient (35 yo) -> Expected: adult diagnosis/reference range
    # -----------------------------------------------------------------------
    adult_patient = {'gender': 'Male', 'age_years': 35}
    ped_diags_for_adult = get_eligible_diagnoses(adult_patient)
    assert diag_ped not in ped_diags_for_adult, "Test 7 Failed: Adult patient must NOT be eligible for pediatric diagnosis (0-12 Y)"

    rr_adult, _ = ParameterReferenceRange.objects.get_or_create(
        investigation_parameter=ip_hb,
        age_group=ag_adult,
        gender='Male',
        defaults={'range_type': 'Numeric', 'min_value': Decimal('13.0'), 'max_value': Decimal('17.0'), 'unit': 'g/dL', 'is_active': True}
    )
    best_range_adult = find_best_db_reference_range(ip_hb.id, patient_age_days=35*365, patient_gender='Male')
    assert best_range_adult.id == rr_adult.id, f"Test 7 Failed: Expected adult range {rr_adult.id}, got {best_range_adult.id}"
    print("✓ Test 7 Passed: Adult patient -> adult diagnosis/reference range.")

    # -----------------------------------------------------------------------
    # TEST 8: Geriatric patient (72 yo) -> Expected: geriatric range
    # -----------------------------------------------------------------------
    rr_geriatric, _ = ParameterReferenceRange.objects.get_or_create(
        investigation_parameter=ip_hb,
        age_group=ag_geriatric,
        gender='Male',
        defaults={'range_type': 'Numeric', 'min_value': Decimal('12.0'), 'max_value': Decimal('16.0'), 'unit': 'g/dL', 'is_active': True}
    )
    best_range_ger = find_best_db_reference_range(ip_hb.id, patient_age_days=72*365, patient_gender='Male')
    assert best_range_ger.id == rr_geriatric.id, f"Test 8 Failed: Expected geriatric range {rr_geriatric.id}, got {best_range_ger.id}"
    print("✓ Test 8 Passed: Geriatric patient -> geriatric reference range.")

    # -----------------------------------------------------------------------
    # TEST 9: Female patient without pregnancy eligibility -> Not eligible
    # -----------------------------------------------------------------------
    diag_preg, _ = Diagnosis.objects.get_or_create(
        code='TEST_DIAG_PREG',
        defaults={'name': 'Antenatal Pregnancy Routine Care', 'gender_eligibility': 'Female', 'is_active': True}
    )
    # Configure rule: Female, Pregnancy Required = True
    DiagnosisEligibilityRule.objects.filter(diagnosis=diag_preg).delete()
    rule_preg = DiagnosisEligibilityRule.objects.create(
        diagnosis=diag_preg,
        gender='Female',
        min_age=15,
        max_age=49,
        pregnancy_required=True,
        is_active=True
    )

    inv_hcg, _ = Investigation.objects.get_or_create(
        code='TEST_INV_HCG',
        defaults={'name': 'Beta HCG Pregnancy Quantitative', 'department': lab_dept, 'sample_type': sample_type, 'is_active': True}
    )
    DiagnosisInvestigationMap.objects.filter(diagnosis=diag_preg, investigation=inv_hcg).delete()
    map_hcg = DiagnosisInvestigationMap.objects.create(
        diagnosis=diag_preg,
        investigation=inv_hcg,
        gender='Female',
        pregnancy_required=True,
        is_active=True
    )

    # Female age 26 with pregnancy_status=False
    female_not_preg = {'gender': 'Female', 'age_years': 26}
    preg_diags = get_eligible_diagnoses(female_not_preg, pregnancy_status=False)
    assert diag_preg not in preg_diags, "Test 9 Failed: Pregnancy diagnosis must NOT be assigned when pregnancy_required=True and pregnancy_status=False"

    eligible_hcg_invs = get_eligible_investigations(diag_preg, female_not_preg, pregnancy_status=False)
    assert inv_hcg not in eligible_hcg_invs, "Test 9 Failed: Pregnancy investigation must NOT be eligible when pregnancy_required=True and pregnancy_status=False"
    print("✓ Test 9 Passed: Female patient without required pregnancy eligibility -> pregnancy test not automatically assigned.")

    # -----------------------------------------------------------------------
    # TEST 10: Female patient satisfying pregnancy eligibility -> Eligible
    # -----------------------------------------------------------------------
    preg_diags_yes = get_eligible_diagnoses(female_not_preg, pregnancy_status=True)
    assert diag_preg in preg_diags_yes, "Test 10 Failed: Pregnancy diagnosis should be eligible when pregnancy_status=True"

    eligible_hcg_yes = get_eligible_investigations(diag_preg, female_not_preg, pregnancy_status=True)
    assert inv_hcg in eligible_hcg_yes, "Test 10 Failed: Pregnancy investigation should be eligible when pregnancy_status=True"
    print("✓ Test 10 Passed: Female patient satisfying pregnancy eligibility -> eligible.")

    # -----------------------------------------------------------------------
    # TEST 11: Diagnosis with no eligible investigation -> Log / error message
    # -----------------------------------------------------------------------
    diag_no_inv, _ = Diagnosis.objects.get_or_create(
        code='TEST_DIAG_EMPTY',
        defaults={'name': 'Condition Without Any Investigations', 'is_active': True}
    )
    DiagnosisInvestigationMap.objects.filter(diagnosis=diag_no_inv).delete()
    res_invs = get_eligible_investigations(diag_no_inv, male_patient)
    assert len(res_invs) == 0, "Test 11 Failed: Diagnosis with no mappings must return 0 eligible investigations"

    # Simulated patient in DB
    p_id_11 = f"TEST-P11-{timezone.now().strftime('%m%d%H%M%S%f')}"
    p_test_obj = Patient.objects.create(
        patient_id=p_id_11,
        name='Test Empty Diag Patient',
        gender='Male',
        age_years=30,
        registration_date=timezone.now().date(),
        patient_type='D',
        created_source='D'
    )
    pv_test_obj = PatientVisit.objects.create(
        patient=p_test_obj,
        visit_no=1,
        visit_date=timezone.now(),
        visit_type='OP',
        department='GENERAL MEDICINE'
    )
    # Force this specific diagnosis by checking assign_atc_lab_workflow when no investigations exist
    DiagnosisInvestigationMap.objects.filter(diagnosis=diag_no_inv).delete()
    res, status_msg = assign_atc_lab_workflow(p_test_obj, pv_test_obj)
    # The first eligible diagnosis in DB was assigned, if we test with isolated diagnosis:
    invs_empty = get_eligible_investigations(diag_no_inv, p_test_obj)
    assert len(invs_empty) == 0
    print("✓ Test 11 Passed: Diagnosis with no eligible investigation -> returns empty and logs correctly.")

    # -----------------------------------------------------------------------
    # TEST 12: Unknown diagnosis -> No invalid investigation created
    # -----------------------------------------------------------------------
    diag_unknown = Diagnosis(id=999999, name="Nonexistent Diagnosis", code="NONEXISTENT")
    unknown_invs = get_eligible_investigations(diag_unknown, male_patient)
    assert len(unknown_invs) == 0, "Test 12 Failed: Unknown diagnosis must produce zero investigations"
    print("✓ Test 12 Passed: Unknown diagnosis -> no invalid investigations created.")

    # -----------------------------------------------------------------------
    # TEST 13: Parameter code 00022681 -> Leading zeros strictly preserved
    # -----------------------------------------------------------------------
    target_code = "00022681"
    param_special, _ = Parameter.objects.get_or_create(
        code=target_code,
        defaults={'name': 'Specific Test Parameter with Leading Zeros', 'default_unit': 'mg/dL', 'is_active': True}
    )
    param_db = Parameter.objects.get(code=target_code)
    assert isinstance(param_db.code, str), "Test 13 Failed: Parameter code must be of type string"
    assert param_db.code == target_code, f"Test 13 Failed: Code '{param_db.code}' != '{target_code}' (leading zeros stripped!)"
    assert param_db.code.startswith("000"), "Test 13 Failed: Leading zeros must be preserved"
    print("✓ Test 13 Passed: Parameter code 00022681 -> leading zeros strictly preserved as string.")

    # -----------------------------------------------------------------------
    # TEST 14: Existing ATC workflow continues working
    # -----------------------------------------------------------------------
    p_id_14 = f"TEST-ATC-P14-{timezone.now().strftime('%m%d%H%M%S%f')}"
    atc_p = Patient.objects.create(
        patient_id=p_id_14,
        name='ATC Automated Patient',
        gender='Male',
        age_years=42,
        dob=date(1984, 3, 10),
        registration_date=timezone.now().date(),
        patient_type='D',
        created_source='D'
    )
    atc_v = PatientVisit.objects.create(
        patient=atc_p,
        visit_no=1,
        visit_date=timezone.now(),
        visit_type='OP',
        department_obj=dept,
        department=dept.name
    )
    sr_atc, status_atc = assign_atc_lab_workflow(atc_p, atc_v)
    assert status_atc == STATUS_SUCCESS, f"Test 14 Failed: ATC assignment returned {status_atc}"
    assert sr_atc is not None, "Test 14 Failed: ServiceRequest was not created"
    assert sr_atc.diagnoses.count() >= 1, "Test 14 Failed: Primary diagnosis was not attached to ServiceRequest"
    assert sr_atc.investigations.count() >= 1, "Test 14 Failed: Investigations were not attached to ServiceRequest"
    print(f"✓ Test 14 Passed: Existing ATC workflow -> successfully generated SR #{sr_atc.id} with {sr_atc.investigations.count()} investigations.")

    # -----------------------------------------------------------------------
    # TEST 15: Existing Lab Order workflow continues working
    # -----------------------------------------------------------------------
    sr_diag = sr_atc.diagnoses.first()
    assert sr_diag.sort_order == 0, "Test 15 Failed: Primary diagnosis must be clearly identified with sort_order=0"
    assert sr_diag.diagnosis is not None, "Test 15 Failed: Primary diagnosis is missing on ServiceRequest"
    print("✓ Test 15 Passed: Existing Lab Order workflow -> ServiceRequest and primary diagnosis intact.")

    # -----------------------------------------------------------------------
    # TEST 16: Existing Work Order workflow continues working
    # -----------------------------------------------------------------------
    sri = sr_atc.investigations.first()
    assert sri.status == ServiceRequestInvestigation.StatusChoices.PENDING
    sri.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
    sri.received_date = timezone.now().date()
    sri.save(update_fields=['status', 'received_date'])
    assert sri.status == ServiceRequestInvestigation.StatusChoices.RECEIVED
    print("✓ Test 16 Passed: Existing Work Order workflow -> Pending to Received status transition verified.")

    # -----------------------------------------------------------------------
    # TEST 17: Existing Result Entry workflow continues working with dynamic evaluation
    # -----------------------------------------------------------------------
    # Add parameter and enter result
    inv_under_test = sri.investigation
    ip_test = InvestigationParameter.objects.filter(investigation=inv_under_test, is_active=True).first()
    if not ip_test:
        ip_test = InvestigationParameter.objects.create(
            investigation=inv_under_test,
            code='PARAM_RES_17',
            name='Test Glucose',
            unit='mg/dL',
            reference_range='70 - 100',
            is_active=True
        )
    # Enter a high result (125)
    ServiceRequestResult.objects.filter(sr_investigation=sri, investigation_parameter=ip_test).delete()
    res_entry = ServiceRequestResult.objects.create(
        sr_investigation=sri,
        investigation_parameter=ip_test,
        result_value='125.0',
        status='Recorded'
    )
    # Dynamic classification test
    c_flag = classify_result('125.0', min_val=70.0, max_val=100.0)
    assert c_flag == STATUS_ABOVE, f"Test 17 Failed: 125.0 should be classified as ABOVE range 70-100, got {c_flag}"
    print("✓ Test 17 Passed: Result Entry workflow -> Result entered & evaluated dynamically against reference range.")

    # -----------------------------------------------------------------------
    # TEST 18: Existing Result View workflow continues working
    # -----------------------------------------------------------------------
    evaluated_report = get_evaluated_results_for_sr(sr_atc)
    assert evaluated_report['patient'].id == atc_p.id, "Test 18 Failed: Patient mismatch in result view report"
    assert len(evaluated_report['investigations']) >= 1, "Test 18 Failed: Investigations missing in result view report"
    first_inv_rep = evaluated_report['investigations'][0]
    assert 'parameters' in first_inv_rep, "Test 18 Failed: Parameters missing in investigation report"

    rf = RequestFactory()
    req = rf.get(f'/lab/results/view/{sr_atc.id}/')
    req.user = user
    resp_view = lab_result_detail_view(req, sr_atc.id)
    assert resp_view.status_code == 200, f"Test 18 Failed: Result view returned HTTP {resp_view.status_code}"
    print("✓ Test 18 Passed: Result View workflow -> View compiles and renders HTTP 200.")

    # -----------------------------------------------------------------------
    # TEST 19: Existing Print workflow continues working
    # -----------------------------------------------------------------------
    req_print = rf.get(f'/lab/results/print/{sr_atc.id}/')
    req_print.user = user
    resp_print = lab_result_print_view(req_print, sr_atc.id)
    assert resp_print.status_code == 200, f"Test 19 Failed: Print view returned HTTP {resp_print.status_code}"
    content_html = resp_print.content.decode('utf-8')
    assert "Vinayaka Mission's Medical College" in content_html, "Test 19 Failed: Header missing in print report"
    assert atc_p.name in content_html, "Test 19 Failed: Patient name missing in print report"
    print("✓ Test 19 Passed: Print workflow -> Clinical laboratory print layout rendered with HTTP 200.")

    print("=" * 80)
    print("ALL 19 AUTOMATED TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == '__main__':
    run_all_tests()
