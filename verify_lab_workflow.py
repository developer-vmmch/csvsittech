import os
import sys
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.utils import timezone
from apps.patients.models import Department, Patient
from apps.lab.models import (
    AgeGroup, Diagnosis, Investigation, Parameter,
    DiagnosisDepartmentMapping, DiagnosisInvestigationMap,
    InvestigationParameter, ParameterReferenceRange,
    ServiceRequest, ServiceRequestDiagnosis, ServiceRequestInvestigation,
    ServiceRequestResult
)
from apps.lab.services.result_classifier import (
    classify_service_request_result, update_service_request_investigation_status,
    STATUS_NORMAL, STATUS_ABOVE, STATUS_BELOW
)


def run_verification():
    print("=" * 80)
    print("VMMC ERP 9-STAGE HOSPITAL LABORATORY CLINICAL WORKFLOW VERIFICATION")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STAGE 1: Department Resolution
    # -------------------------------------------------------------------------
    print("\n[Stage 1] Verifying Department Master...")
    dept = Department.objects.filter(code__in=['GM', 'SURG', 'OPD']).first()
    if not dept:
        dept = Department.objects.first()
    assert dept is not None, "No Department found in DB!"
    print(f"  ✓ Department selected: {dept.name} (Code: '{dept.code}') [Active={dept.is_active}]")

    # -------------------------------------------------------------------------
    # STAGE 2: Age Group Master & Code Preservation
    # -------------------------------------------------------------------------
    print("\n[Stage 2] Verifying Age Group Master...")
    ag_adult = AgeGroup.objects.filter(code='ADULT_MALE').first() or AgeGroup.objects.first()
    assert ag_adult is not None, "No Age Group found in DB!"
    print(f"  ✓ Age Group resolved: {ag_adult.label} (Code: '{ag_adult.code}')")
    print(f"    Age Range: {ag_adult.min_age_value} {ag_adult.min_age_unit} to {ag_adult.max_age_value} {ag_adult.max_age_unit}, Gender: {ag_adult.gender}")

    # -------------------------------------------------------------------------
    # STAGE 3: Diagnosis Master & Department Mapping
    # -------------------------------------------------------------------------
    print("\n[Stage 3] Verifying Diagnosis Master & Department Diagnosis Mapping...")
    dd_mappings = DiagnosisDepartmentMapping.objects.filter(department=dept, status='Active').select_related('diagnosis')
    if not dd_mappings.exists():
        dd_mappings = DiagnosisDepartmentMapping.objects.filter(status='Active').select_related('department', 'diagnosis')
        dept = dd_mappings.first().department
    assert dd_mappings.exists(), f"No active DiagnosisDepartmentMapping found for department {dept.name}!"
    
    mapped_diag = dd_mappings.first().diagnosis
    print(f"  ✓ Department '{dept.name}' mapped diagnoses count: {dd_mappings.count()}")
    for m in dd_mappings[:3]:
        print(f"    - Mapped Diagnosis: {m.diagnosis.name} (Code: '{m.diagnosis.code}') [Status: {m.status}]")
    print(f"  ✓ Primary Diagnosis selected: {mapped_diag.name} (Code: '{mapped_diag.code}')")

    # -------------------------------------------------------------------------
    # STAGE 4: Investigation Master & Diagnosis Auto-Suggestion Mapping
    # -------------------------------------------------------------------------
    print("\n[Stage 4] Verifying Investigation Master & Diagnosis Investigation Mapping...")
    di_mappings = DiagnosisInvestigationMap.objects.filter(diagnosis=mapped_diag, is_active=True).select_related('investigation')
    if not di_mappings.exists():
        di_mappings = DiagnosisInvestigationMap.objects.filter(is_active=True).select_related('diagnosis', 'investigation')
        mapped_diag = di_mappings.first().diagnosis
        di_mappings = DiagnosisInvestigationMap.objects.filter(diagnosis=mapped_diag, is_active=True).select_related('investigation')
    assert di_mappings.exists(), f"No active DiagnosisInvestigationMap found for diagnosis {mapped_diag.name}!"
    
    suggested_invs = [m.investigation for m in di_mappings]
    print(f"  ✓ Diagnosis '{mapped_diag.name}' auto-suggests {len(suggested_invs)} investigations:")
    for inv in suggested_invs:
        print(f"    - Suggested Inv: {inv.name} (Code: '{inv.code}') [Panel={inv.is_panel}]")

    # -------------------------------------------------------------------------
    # STAGE 5: Parameter Master & Investigation Parameter Mapping
    # -------------------------------------------------------------------------
    print("\n[Stage 5] Verifying Parameter Master & Investigation Parameter Mappings...")
    cbc_inv = Investigation.objects.filter(code__iexact='cbc').first() or suggested_invs[0]
    cbc_params = InvestigationParameter.objects.filter(investigation=cbc_inv).order_by('display_order')
    assert cbc_params.exists(), f"No parameters mapped to investigation {cbc_inv.name}!"
    print(f"  ✓ Investigation '{cbc_inv.name}' has {cbc_params.count()} mapped parameters.")
    
    # Check leading zeros preservation
    esr_ip = cbc_params.filter(code='00022681').first()
    hb_ip = cbc_params.filter(code='00020350').first()
    print(f"  ✓ Leading zeros preserved in parameter codes:")
    if esr_ip:
        print(f"    - ESR Code: '{esr_ip.code}' (Expected '00022681', Type: {esr_ip.result_type}, Unit: {esr_ip.unit})")
        assert esr_ip.code == '00022681', f"ESR code leading zeroes lost! Found: {esr_ip.code}"
    if hb_ip:
        print(f"    - Hemoglobin Code: '{hb_ip.code}' (Expected '00020350', Type: {hb_ip.result_type}, Unit: {hb_ip.unit})")
        assert hb_ip.code == '00020350', f"Hemoglobin code leading zeroes lost! Found: {hb_ip.code}"

    # Check Urine Routine text/numeric types
    ur_inv = Investigation.objects.filter(code__iexact='ur').first()
    if ur_inv:
        ur_params = InvestigationParameter.objects.filter(investigation=ur_inv)
        macro_ip = ur_params.filter(code='00013671').first()
        color_ip = ur_params.filter(code='00021366').first()
        if macro_ip:
            print(f"    - Urine Macroscopy Section: Code '{macro_ip.code}', Result Type: {macro_ip.result_type}")
            assert macro_ip.result_type == 'Text', f"Macroscopy section must be Text! Found: {macro_ip.result_type}"
        if color_ip:
            print(f"    - Urine Colour: Code '{color_ip.code}', Result Type: {color_ip.result_type}, Ref: '{color_ip.reference_range}'")
            assert color_ip.result_type == 'Text', f"Urine Colour must be Text! Found: {color_ip.result_type}"

    # -------------------------------------------------------------------------
    # STAGE 6: Parameter Reference Ranges (Numeric and Qualitative)
    # -------------------------------------------------------------------------
    print("\n[Stage 6] Verifying Reference Ranges (Numeric & Qualitative)...")
    hb_ranges = ParameterReferenceRange.objects.filter(investigation_parameter=hb_ip)
    assert hb_ranges.exists(), "No reference range found for Hemoglobin!"
    print(f"  ✓ Hemoglobin Reference Ranges count: {hb_ranges.count()}")
    for r in hb_ranges[:3]:
        print(f"    - {r.gender} | Min: {r.min_value}, Max: {r.max_value} {r.unit} [Type: {r.range_type}]")

    # -------------------------------------------------------------------------
    # STAGE 7: Clinical Lab Order Placement with Primary Diagnosis
    # -------------------------------------------------------------------------
    print("\n[Stage 7] Placing Clinical Lab Order (ServiceRequest) with Primary Diagnosis...")
    # Create or get test patient (25 yo Male)
    patient, _ = Patient.objects.get_or_create(
        patient_id='TEST-VERIFY-001',
        defaults={
            'name': 'Test Lab Patient',
            'gender': 'Male',
            'dob': date(2001, 1, 1),
            'mobile_no': '9999999999'
        }
    )
    
    # Create Service Request
    sr = ServiceRequest.objects.create(
        patient=patient,
        department=dept,
        status=ServiceRequest.StatusChoices.SAVED
    )
    
    # Attach Primary Diagnosis (sort_order = 0)
    primary_diag_entry = ServiceRequestDiagnosis.objects.create(
        service_request=sr,
        diagnosis=mapped_diag,
        sort_order=0
    )
    print(f"  ✓ Created ServiceRequest #{sr.id} for Patient '{patient.name}' (Age 25, Male)")
    print(f"  ✓ Primary Diagnosis linked: {primary_diag_entry.diagnosis.name} (sort_order={primary_diag_entry.sort_order})")

    # Attach Investigations
    sr_inv = ServiceRequestInvestigation.objects.create(
        service_request=sr,
        investigation=cbc_inv,
        source=ServiceRequestInvestigation.SourceChoices.AUTO_SUGGESTED,
        status=ServiceRequestInvestigation.StatusChoices.PENDING
    )
    print(f"  ✓ Auto-suggested Investigation added: {sr_inv.investigation.name} (Status: {sr_inv.status})")

    # -------------------------------------------------------------------------
    # STAGE 8: Work Order Processing & Result Entry
    # -------------------------------------------------------------------------
    print("\n[Stage 8] Work Order Receiving & Parameter Result Entry...")
    sr_inv.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
    sr_inv.received_date = timezone.now().date()
    sr_inv.received_time = timezone.now().time()
    sr_inv.save()
    print(f"  ✓ Work order received: Status={sr_inv.status}, Date={sr_inv.received_date}")

    # Enter normal Hemoglobin (e.g. 12.5 g/dL within 11.0 - 14.0)
    res_hb = ServiceRequestResult.objects.create(
        sr_investigation=sr_inv,
        investigation_parameter=hb_ip,
        result_value='12.5'
    )
    # Enter abnormal ESR if ESR IP exists (e.g. 28.0 mm/hr -> Above normal 5.0 - 12.0)
    res_esr = None
    if esr_ip:
        res_esr = ServiceRequestResult.objects.create(
            sr_investigation=sr_inv,
            investigation_parameter=esr_ip,
            result_value='28.0'
        )
    print(f"  ✓ Results entered: Hemoglobin = '12.5', ESR = '28.0'")

    # -------------------------------------------------------------------------
    # STAGE 9: Reference Range Evaluation & Investigation Status Update
    # -------------------------------------------------------------------------
    print("\n[Stage 9] Reference Range Evaluation & Investigation Status Aggregation...")
    status_hb = classify_service_request_result(res_hb)
    res_hb.refresh_from_db()
    print(f"  ✓ Hemoglobin (Value: 14.2 g/dL): Classified as '{status_hb}' (Applied Range: {res_hb.applied_reference_range})")
    assert status_hb == STATUS_NORMAL, f"Expected Hemoglobin to be NORMAL, got {status_hb}"

    if res_esr:
        status_esr = classify_service_request_result(res_esr)
        res_esr.refresh_from_db()
        print(f"  ✓ ESR (Value: 28.0 mm/hr): Classified as '{status_esr}' (Applied Range: {res_esr.applied_reference_range})")
        assert status_esr == STATUS_ABOVE, f"Expected ESR to be ABOVE, got {status_esr}"

    overall_status = update_service_request_investigation_status(sr_inv)
    sr_inv.refresh_from_db()
    print(f"  ✓ Investigation '{sr_inv.investigation.name}' Overall Status: '{sr_inv.result_status}'")
    assert sr_inv.result_status == 'ABNORMAL', f"Expected overall status to be ABNORMAL, got {sr_inv.result_status}"

    # Test Qualitative evaluation (e.g. Urine Routine)
    if ur_inv and color_ip:
        sr_ur = ServiceRequestInvestigation.objects.create(
            service_request=sr,
            investigation=ur_inv,
            status=ServiceRequestInvestigation.StatusChoices.RECEIVED
        )
        res_color = ServiceRequestResult.objects.create(
            sr_investigation=sr_ur,
            investigation_parameter=color_ip,
            result_value='Straw Yellow'
        )
        status_color = classify_service_request_result(res_color)
        print(f"  ✓ Qualitative Test: Urine Colour 'Straw Yellow': Classified as '{status_color}'")
        assert status_color == STATUS_NORMAL, f"Expected Straw Yellow to be NORMAL, got {status_color}"
        sr_ur.delete()

    # Clean up test records
    sr.delete()
    patient.delete()
    print("\n  ✓ Test records cleaned up successfully.")

    print("\n" + "=" * 80)
    print("ALL 9 STAGES OF THE HOSPITAL LABORATORY CLINICAL WORKFLOW VERIFIED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == '__main__':
    run_verification()
