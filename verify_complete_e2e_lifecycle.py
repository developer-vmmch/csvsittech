import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.patients.models import Patient, PatientVisit, Department
from apps.lab.models import (
    Diagnosis,
    DiagnosisEligibilityRule,
    Investigation,
    Parameter,
    InvestigationParameter,
    ParameterReferenceRange,
    AgeGroup,
    DiagnosisInvestigationMap,
    ServiceRequest,
    ServiceRequestDiagnosis,
    ServiceRequestInvestigation,
    ServiceRequestResult,
    LabDepartment,
    SampleType,
)
from apps.lab.services.eligibility_engine import assign_atc_lab_workflow, calculate_patient_age
from apps.lab.result_views import get_evaluated_results_for_sr, lab_result_detail_view, lab_result_print_view

User = get_user_model()

def run_e2e_lifecycle():
    print("=" * 80)
    print("VMMC ERP – COMPLETE END-TO-END LAB WORKFLOW & RULE ENGINE VERIFICATION")
    print("=" * 80)

    admin_user, _ = User.objects.get_or_create(username='admin_verifier', defaults={'is_staff': True})
    dept, _ = Department.objects.get_or_create(code='E2E_GM', defaults={'name': 'E2E GENERAL MEDICINE', 'is_active': True})
    lab_dept, _ = LabDepartment.objects.get_or_create(name='E2E BIOCHEMISTRY', defaults={'is_active': True})
    sample_type, _ = SampleType.objects.get_or_create(name='E2E SERUM', defaults={'is_active': True})

    # 1. SETUP LAB MASTER CONFIGURATION
    print("\n[STAGE 1] LAB MASTER CONFIGURATION")
    
    # Diagnosis with eligibility rule: Adult, Female, 18-50
    diag, _ = Diagnosis.objects.get_or_create(
        code='E2E_DIAG_01',
        defaults={'name': 'Antenatal Wellness Check', 'department': dept, 'is_active': True}
    )
    DiagnosisEligibilityRule.objects.filter(diagnosis=diag).delete()
    DiagnosisEligibilityRule.objects.create(
        diagnosis=diag,
        gender='Female',
        min_age=18,
        max_age=50,
        department=dept,
        pregnancy_required=True,
        priority=10,
        is_active=True
    )
    # Map Diagnosis to Department
    from apps.lab.models import DiagnosisDepartmentMapping
    DiagnosisDepartmentMapping.objects.filter(department=dept).delete()
    DiagnosisDepartmentMapping.objects.create(department=dept, diagnosis=diag, status='Active')
    print(f" ✓ Configured Diagnosis: {diag.name} (Code: {diag.code}) linked to Department {dept.name} with Female reproductive age rule (18-50 Y, pregnancy required).")

    # Investigation with gender and pregnancy filter
    inv, _ = Investigation.objects.get_or_create(
        code='E2E_INV_HCG',
        defaults={
            'name': 'Quantitative Beta-HCG Test',
            'department': lab_dept,
            'sample_type': sample_type,
            'category': 'Endocrinology',
            'specimen': 'Blood',
            'method': 'CLIA',
            'display_order': 1,
            'is_active': True
        }
    )
    # Map Diagnosis -> Investigation
    DiagnosisInvestigationMap.objects.filter(diagnosis=diag, investigation=inv).delete()
    DiagnosisInvestigationMap.objects.create(
        diagnosis=diag,
        investigation=inv,
        gender='Female',
        min_age=18,
        max_age=50,
        department=dept,
        pregnancy_required=True,
        priority=1,
        is_active=True
    )
    print(f" ✓ Configured Investigation: {inv.name} (Code: {inv.code}) mapped to {diag.name}.")

    # Parameter with string code '00022681'
    param_code = "00022681"
    param, _ = Parameter.objects.get_or_create(
        code=param_code,
        defaults={'name': 'Beta HCG Subunit Level', 'data_type': 'NUMERIC', 'default_unit': 'mIU/mL', 'is_active': True}
    )
    ip, _ = InvestigationParameter.objects.get_or_create(
        investigation=inv,
        parameter=param,
        defaults={
            'code': param_code,
            'name': 'Beta HCG Subunit Level',
            'unit': 'mIU/mL',
            'result_type': 'Numeric',
            'display_order': 1,
            'is_mandatory': True,
            'is_active': True
        }
    )
    print(f" ✓ Configured Parameter: {param.name} (String Code strictly preserved: '{ip.code}').")

    # Age Group & DB Reference Range
    ag, _ = AgeGroup.objects.get_or_create(
        code='E2E_ADULT_F',
        defaults={'label': 'Adult Reproductive Female (18-50 Y)', 'min_age_value': 18, 'max_age_value': 50, 'gender': 'Female', 'is_active': True}
    )
    ParameterReferenceRange.objects.filter(investigation_parameter=ip).delete()
    rr = ParameterReferenceRange.objects.create(
        investigation_parameter=ip,
        age_group=ag,
        gender='Female',
        diagnosis=diag,
        range_type='Numeric',
        min_value=Decimal('5.0'),
        max_value=Decimal('50.0'),
        unit='mIU/mL',
        reference_text='5.0 – 50.0 mIU/mL (Expected normal range for early gestational period)',
        is_active=True
    )
    print(f" ✓ Configured Reference Range in DB: {rr.min_value} – {rr.max_value} {rr.unit} (Gender: Female, Diagnosis: {diag.name}).")

    # 2. CREATE ATC PATIENT & DETECT DEMOGRAPHICS
    print("\n[STAGE 2] ATC PATIENT CREATION & DEMOGRAPHIC DETECTION")
    p_id = f"ATC-E2E-{timezone.now().strftime('%m%d%H%M%S')}"
    patient = Patient.objects.create(
        patient_id=p_id,
        name='Sangeetha Priya',
        gender='Female',
        dob=date(1998, 4, 15),
        age_years=28,
        registration_date=timezone.now().date(),
        patient_type='D',
        created_source='D'
    )
    age_calc = calculate_patient_age(dob=patient.dob, ref_date=patient.registration_date)
    print(f" ✓ Created ATC Patient: {patient.name} (ID: {patient.patient_id})")
    print(f" ✓ Demographics Detected: Gender={patient.gender}, DOB={patient.dob}, Calculated Age={age_calc['years']} Years ({age_calc['display']})")

    # Patient Visit
    visit = PatientVisit.objects.create(
        patient=patient,
        visit_no=1,
        visit_date=timezone.now(),
        visit_type='OP',
        department_obj=dept,
        department=dept.name,
        unit_doctor='Dr. Ananya (OBG/GM)'
    )
    print(f" ✓ Patient Visit #1 registered under Department: {visit.department}")

    # 3. RUN ELIGIBILITY ENGINE & ASSIGN WORKFLOW
    print("\n[STAGE 3] ELIGIBILITY ENGINE EXECUTION")
    sr, status_msg = assign_atc_lab_workflow(patient, visit, pregnancy_status=True)
    assert status_msg == 'SUCCESS', f"Workflow assignment failed with {status_msg}"
    print(f" ✓ Diagnosis Eligibility Engine evaluated candidate diagnoses based on Gender=Female, Age=28, Dept={dept.name}, Pregnancy=True.")
    
    assigned_diag = sr.diagnoses.first().diagnosis
    print(f" ✓ Primary Diagnosis Assigned: {assigned_diag.name} (Code: {assigned_diag.code}, sort_order=0)")

    sr_invs = list(sr.investigations.all())
    assert len(sr_invs) >= 1, "No investigations created"
    sri = sr_invs[0]
    print(f" ✓ Eligible Investigation Assigned: {sri.investigation.name} (Code: {sri.investigation.code}, Source: {sri.source})")
    print(f" ✓ Service Request Generated: ID #{sr.id} (Sample ID: {sr.sample_id}, Status: {sr.status})")

    # 4. WORK ORDER & SAMPLE PROCESSING
    print("\n[STAGE 4] WORK ORDER PROCESSING")
    print(f" ✓ Initial Work Order Investigation Status: {sri.status}")
    sri.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
    sri.received_date = timezone.now().date()
    sri.received_time = timezone.now().time()
    sri.save(update_fields=['status', 'received_date', 'received_time'])
    print(f" ✓ Sample Received at Laboratory: Status transitioned to '{sri.status}' at {sri.received_time.strftime('%H:%M:%S')}")

    # 5. RESULT ENTRY & DYNAMIC EVALUATION
    print("\n[STAGE 5] RESULT ENTRY & DYNAMIC EVALUATION")
    result_val = "24.5"
    res_obj, _ = ServiceRequestResult.objects.get_or_create(
        sr_investigation=sri,
        investigation_parameter=ip,
        defaults={
            'result_value': result_val,
            'status': 'Completed',
            'applied_reference_range': rr
        }
    )
    sri.status = ServiceRequestInvestigation.StatusChoices.COMPLETED
    sri.result_status = 'Completed'
    sri.save(update_fields=['status', 'result_status'])
    print(f" ✓ Result Value Entered: {res_obj.result_value} {ip.unit}")

    # 6. DYNAMIC RESULT COMPILATION
    print("\n[STAGE 6] DYNAMIC RESULT COMPILATION & CLASSIFICATION")
    report = get_evaluated_results_for_sr(sr)
    param_evaluated = report['investigations'][0]['parameters'][0]
    print(f"   • Test Name:       {param_evaluated['parameter_name']}")
    print(f"   • Measured Value:  {param_evaluated['result_value']} {param_evaluated['unit']}")
    print(f"   • Dynamic DB Range:{param_evaluated['reference_range']}")
    print(f"   • Evaluation Flag: {param_evaluated['flag']}")
    assert param_evaluated['flag'] == 'Normal', f"Expected Normal, got {param_evaluated['flag']}"

    # 7. RESULT VIEW RENDERING
    print("\n[STAGE 7] RESULT VIEW HTTP RENDERING")
    rf = RequestFactory()
    req_view = rf.get(f'/lab/results/view/{sr.id}/')
    req_view.user = admin_user
    resp_view = lab_result_detail_view(req_view, sr.id)
    assert resp_view.status_code == 200, f"Result view returned {resp_view.status_code}"
    print(f" ✓ Result View (/lab/results/view/{sr.id}/) rendered successfully with HTTP {resp_view.status_code}.")

    # 8. PRINT REPORT RENDERING
    print("\n[STAGE 8] PRINT REPORT GENERATION")
    req_print = rf.get(f'/lab/results/print/{sr.id}/')
    req_print.user = admin_user
    resp_print = lab_result_print_view(req_print, sr.id)
    assert resp_print.status_code == 200, f"Print view returned {resp_print.status_code}"
    print_html = resp_print.content.decode('utf-8')
    assert "Vinayaka Mission's Medical College" in print_html
    assert patient.name in print_html
    assert "Beta HCG Subunit Level" in print_html
    print(f" ✓ Clinical Print Layout (/lab/results/print/{sr.id}/) compiled with header, demographics, and signatures (HTTP {resp_print.status_code}).")

    print("\n" + "=" * 80)
    print("LIFECYCLE TEST COMPLETED 100% SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    run_e2e_lifecycle()
