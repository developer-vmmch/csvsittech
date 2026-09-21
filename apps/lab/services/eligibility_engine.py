import logging
from datetime import date, datetime
from django.utils import timezone
from django.db import transaction

from apps.lab.models import (
    Diagnosis,
    DiagnosisEligibilityRule,
    DiagnosisInvestigationMap,
    DiagnosisDepartmentMapping,
    Investigation,
    InvestigationParameter,
    ParameterReferenceRange,
    AgeGroup,
    ServiceRequest,
    ServiceRequestDiagnosis,
    ServiceRequestInvestigation,
    PatientVisitDiagnosis,
)
from apps.patients.models import Department, Patient, PatientVisit

logger = logging.getLogger(__name__)

STATUS_NO_ELIGIBLE_DIAGNOSIS = "NO_ELIGIBLE_DIAGNOSIS"
STATUS_NO_ELIGIBLE_INVESTIGATION = "NO_ELIGIBLE_INVESTIGATION"
STATUS_SUCCESS = "SUCCESS"


def calculate_patient_age(dob=None, ref_date=None, age_years=None, age_months=None, age_days=None):
    """
    Computes patient age accurately in years, months, days, and total days.
    """
    if ref_date is None:
        ref_date = timezone.now().date()
    elif isinstance(ref_date, str):
        try:
            ref_date = datetime.strptime(ref_date, '%Y-%m-%d').date()
        except Exception:
            ref_date = timezone.now().date()
    elif hasattr(ref_date, 'date'):
        ref_date = ref_date.date()

    if dob:
        if isinstance(dob, str):
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date()
            except Exception:
                dob = None
        elif hasattr(dob, 'date'):
            dob = dob.date()

    if dob:
        total_days = max(0, (ref_date - dob).days)
        years = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
        # rough month diff
        months = max(0, (total_days % 365) // 30)
        days = max(0, (total_days % 365) % 30)
        return {
            'years': max(0, years),
            'months': months,
            'days': days,
            'total_days': total_days,
            'display': f"{years} Y" if years > 0 else (f"{months} M" if months > 0 else f"{days} D")
        }

    years = int(age_years or 0)
    months = int(age_months or 0)
    days = int(age_days or 0)
    total_days = (years * 365) + (months * 30) + days
    return {
        'years': years,
        'months': months,
        'days': days,
        'total_days': total_days,
        'display': f"{years} Y" if years > 0 else (f"{months} M" if months > 0 else f"{days} D")
    }


def normalize_gender(gender_val):
    if not gender_val:
        return 'All'
    g = str(gender_val).strip().capitalize()
    if g in ('Male', 'M'):
        return 'Male'
    elif g in ('Female', 'F'):
        return 'Female'
    return 'All'


def find_matching_age_group(age_years, gender='All'):
    """
    Finds the best matching active AgeGroup for an age in years and gender.
    """
    norm_gender = normalize_gender(gender)
    groups = AgeGroup.objects.filter(is_active=True).order_by('sort_order', 'id')
    for ag in groups:
        min_y = ag.min_age_value if ag.min_age_value is not None else 0
        max_y = ag.max_age_value if ag.max_age_value is not None else 150
        if ag.min_age_unit == AgeGroup.AgeUnitChoices.MONTH:
            min_y = min_y / 12.0
        elif ag.min_age_unit == AgeGroup.AgeUnitChoices.DAY:
            min_y = min_y / 365.0
        if ag.max_age_unit == AgeGroup.AgeUnitChoices.MONTH:
            max_y = max_y / 12.0
        elif ag.max_age_unit == AgeGroup.AgeUnitChoices.DAY:
            max_y = max_y / 365.0

        if min_y <= age_years <= max_y:
            if ag.gender == 'All' or ag.gender == norm_gender:
                return ag
    return None


def get_eligible_diagnoses(patient_or_data, department=None, pregnancy_status=False, visit_type='OP'):
    """
    Determines list of eligible Diagnosis records for a patient based on:
    - Gender (All, Male, Female)
    - Age (min_age / max_age bounds from rules & age groups)
    - Department (matching DiagnosisDepartmentMapping or rule department)
    - Pregnancy requirements (Female only, pregnancy_status == True)
    """
    if isinstance(patient_or_data, Patient):
        p_gender = normalize_gender(patient_or_data.gender)
        age_info = calculate_patient_age(
            dob=patient_or_data.dob,
            ref_date=patient_or_data.registration_date,
            age_years=patient_or_data.age_years,
            age_months=patient_or_data.age_months,
            age_days=patient_or_data.age_days,
        )
    elif isinstance(patient_or_data, dict):
        p_gender = normalize_gender(patient_or_data.get('gender'))
        age_info = calculate_patient_age(
            dob=patient_or_data.get('dob'),
            ref_date=patient_or_data.get('registration_date'),
            age_years=patient_or_data.get('age_years'),
            age_months=patient_or_data.get('age_months'),
            age_days=patient_or_data.get('age_days'),
        )
    else:
        p_gender = 'All'
        age_info = {'years': 30, 'months': 0, 'days': 0, 'total_days': 10950, 'display': '30 Y'}

    p_years = age_info['years']

    # Resolve department object if possible
    dept_obj = None
    if isinstance(department, Department):
        dept_obj = department
    elif isinstance(department, str) and department.strip():
        dept_obj = Department.objects.filter(name__iexact=department.strip()).first()
    elif department and hasattr(department, 'id'):
        dept_obj = department

    # 1. Look for diagnoses associated with the department if given
    dept_diagnosis_ids = set()
    if dept_obj:
        dept_mappings = DiagnosisDepartmentMapping.objects.filter(
            department=dept_obj,
            status='Active',
            diagnosis__is_active=True
        ).select_related('diagnosis')
        dept_diagnosis_ids = set(dept_mappings.values_list('diagnosis_id', flat=True))

    # Query active diagnoses
    diagnoses_qs = Diagnosis.objects.filter(is_active=True).prefetch_related('eligibility_rules')
    if dept_diagnosis_ids:
        # Prioritize department-mapped diagnoses, but if none match we check all active
        candidate_diagnoses = [d for d in diagnoses_qs if d.id in dept_diagnosis_ids]
        if not candidate_diagnoses:
            candidate_diagnoses = list(diagnoses_qs)
    else:
        candidate_diagnoses = list(diagnoses_qs)

    eligible_diagnoses = []

    for diag in candidate_diagnoses:
        rules = list(diag.eligibility_rules.filter(is_active=True))
        if rules:
            # If explicit eligibility rules exist, at least one must match
            rule_matched = False
            for rule in rules:
                # Gender check
                if rule.gender != 'All' and rule.gender != p_gender:
                    continue
                # Min age check
                if rule.min_age is not None and p_years < rule.min_age:
                    continue
                # Max age check
                if rule.max_age is not None and p_years > rule.max_age:
                    continue
                # Department check
                if rule.department and dept_obj and rule.department_id != dept_obj.id:
                    continue
                # Pregnancy requirement
                if rule.pregnancy_required:
                    if p_gender != 'Female' or not pregnancy_status:
                        continue
                rule_matched = True
                break
            if rule_matched:
                eligible_diagnoses.append(diag)
        else:
            # Evaluate direct fields on Diagnosis
            # Gender check
            if diag.gender_eligibility and diag.gender_eligibility != 'All' and diag.gender_eligibility != p_gender:
                continue
            # Min age check
            if diag.min_age is not None and p_years < diag.min_age:
                continue
            # Max age check
            if diag.max_age is not None and p_years > diag.max_age:
                continue
            # Department check
            if diag.department and dept_obj and diag.department_id != dept_obj.id:
                continue
            # Implicit pregnancy heuristic check for clinical safety
            name_lower = (diag.name or '').lower()
            if any(term in name_lower for term in ('pregnancy', 'antenatal', 'gravid', 'obstetric', 'labour', 'postpartum')):
                if p_gender != 'Female':
                    continue
                if not pregnancy_status:
                    # Pregnancy requires confirmation; female patients without pregnancy status are not auto-assigned
                    continue
            eligible_diagnoses.append(diag)

    return eligible_diagnoses


def get_eligible_investigations(diagnosis, patient_or_data, department=None, pregnancy_status=False):
    """
    Determines list of eligible Investigation records mapped to a Diagnosis based on:
    - Gender (All, Male, Female)
    - Age bounds (min_age / max_age or AgeGroup bounds)
    - Department
    - Pregnancy requirement
    """
    if isinstance(patient_or_data, Patient):
        p_gender = normalize_gender(patient_or_data.gender)
        age_info = calculate_patient_age(
            dob=patient_or_data.dob,
            ref_date=patient_or_data.registration_date,
            age_years=patient_or_data.age_years,
            age_months=patient_or_data.age_months,
            age_days=patient_or_data.age_days,
        )
    elif isinstance(patient_or_data, dict):
        p_gender = normalize_gender(patient_or_data.get('gender'))
        age_info = calculate_patient_age(
            dob=patient_or_data.get('dob'),
            ref_date=patient_or_data.get('registration_date'),
            age_years=patient_or_data.get('age_years'),
            age_months=patient_or_data.get('age_months'),
            age_days=patient_or_data.get('age_days'),
        )
    else:
        p_gender = 'All'
        age_info = {'years': 30, 'months': 0, 'days': 0, 'total_days': 10950, 'display': '30 Y'}

    p_years = age_info['years']

    dept_obj = None
    if isinstance(department, Department):
        dept_obj = department
    elif isinstance(department, str) and department.strip():
        dept_obj = Department.objects.filter(name__iexact=department.strip()).first()
    elif department and hasattr(department, 'id'):
        dept_obj = department

    mappings = DiagnosisInvestigationMap.objects.filter(
        diagnosis=diagnosis,
        is_active=True,
        investigation__is_active=True
    ).select_related('investigation', 'age_group', 'department').order_by('priority', 'id')

    eligible_investigations = []
    seen_inv_ids = set()

    for m in mappings:
        inv = m.investigation
        if inv.id in seen_inv_ids:
            continue

        # 1. Gender filter
        if m.gender != 'All' and m.gender != p_gender:
            continue

        # 2. Age bounds on map
        if m.min_age is not None and p_years < m.min_age:
            continue
        if m.max_age is not None and p_years > m.max_age:
            continue

        # 3. Age Group filter on map if specified
        if m.age_group:
            ag = m.age_group
            min_y = ag.min_age_value if ag.min_age_value is not None else 0
            max_y = ag.max_age_value if ag.max_age_value is not None else 150
            if ag.min_age_unit == AgeGroup.AgeUnitChoices.MONTH:
                min_y = min_y / 12.0
            elif ag.min_age_unit == AgeGroup.AgeUnitChoices.DAY:
                min_y = min_y / 365.0
            if ag.max_age_unit == AgeGroup.AgeUnitChoices.MONTH:
                max_y = max_y / 12.0
            elif ag.max_age_unit == AgeGroup.AgeUnitChoices.DAY:
                max_y = max_y / 365.0
            if not (min_y <= p_years <= max_y):
                continue
            if ag.gender != 'All' and ag.gender != p_gender:
                continue

        # 4. Department filter on map
        if m.department and dept_obj and m.department_id != dept_obj.id:
            continue

        # 5. Pregnancy filter
        if m.pregnancy_required:
            if p_gender != 'Female' or not pregnancy_status:
                continue

        # Clinical heuristic safety for pregnancy tests
        inv_name_lower = (inv.name or '').lower()
        if any(term in inv_name_lower for term in ('pregnancy test', 'hcg', 'dual marker', 'triple marker', 'quadruple marker')):
            if p_gender != 'Female':
                continue
            if m.pregnancy_required and not pregnancy_status:
                continue

        eligible_investigations.append(inv)
        seen_inv_ids.add(inv.id)

    return eligible_investigations


def find_matching_reference_range(investigation_parameter, patient_gender, patient_age_years, diagnosis=None, pregnancy_status=False):
    """
    Dynamic DB lookup for ParameterReferenceRange matching patient demographics.
    """
    from apps.lab.services.result_classifier import find_best_db_reference_range
    patient_age_days = int(patient_age_years * 365)
    diag_id = diagnosis.id if diagnosis else None
    return find_best_db_reference_range(
        investigation_parameter_id=investigation_parameter.id,
        patient_age_days=patient_age_days,
        patient_gender=patient_gender,
        diagnosis_id=diag_id
    )


def assign_atc_lab_workflow(patient, visit, job=None, pregnancy_status=False):
    """
    Coordinates end-to-end lab workflow for ATC-generated patients:
    1. Read Gender, DOB, Age, Department.
    2. Run Diagnosis Eligibility Engine.
    3. If NO_ELIGIBLE_DIAGNOSIS -> logs and returns None.
    4. Selects Primary Diagnosis.
    5. Runs Diagnosis -> Investigation Eligibility Engine.
    6. If NO_ELIGIBLE_INVESTIGATION -> logs and returns (primary_diagnosis, NO_ELIGIBLE_INVESTIGATION).
    7. Creates ServiceRequest, ServiceRequestDiagnosis (primary), ServiceRequestInvestigation.
    """
    dept_obj = visit.department_obj if hasattr(visit, 'department_obj') and visit.department_obj else None
    if not dept_obj and visit.department:
        dept_obj = Department.objects.filter(name__iexact=visit.department.strip()).first()

    eligible_diagnoses = get_eligible_diagnoses(
        patient_or_data=patient,
        department=dept_obj,
        pregnancy_status=pregnancy_status,
        visit_type=visit.visit_type or 'OP'
    )

    if not eligible_diagnoses:
        msg = f"NO_ELIGIBLE_DIAGNOSIS for Patient {patient.patient_id} ({patient.gender}, age {patient.age_years}, dept {dept_obj})"
        logger.warning(msg)
        if job and hasattr(job, 'logs'):
            from apps.lab.models import ATCJobLog
            ATCJobLog.objects.create(
                job=job,
                patient=patient,
                visit=visit,
                patient_name=patient.name,
                gender=patient.gender,
                department=dept_obj.name if dept_obj else str(visit.department),
                status='Skipped',
                error_message=STATUS_NO_ELIGIBLE_DIAGNOSIS
            )
        return None, STATUS_NO_ELIGIBLE_DIAGNOSIS

    # Select Primary Diagnosis
    primary_diagnosis = eligible_diagnoses[0]

    # Save to visit diagnosis
    PatientVisitDiagnosis.objects.get_or_create(
        visit=visit,
        diagnosis=primary_diagnosis
    )

    # Determine eligible investigations
    eligible_investigations = get_eligible_investigations(
        diagnosis=primary_diagnosis,
        patient_or_data=patient,
        department=dept_obj,
        pregnancy_status=pregnancy_status
    )

    if not eligible_investigations:
        msg = f"NO_ELIGIBLE_INVESTIGATION for Patient {patient.patient_id} with Diagnosis {primary_diagnosis.name}"
        logger.warning(msg)
        if job and hasattr(job, 'logs'):
            from apps.lab.models import ATCJobLog
            ATCJobLog.objects.create(
                job=job,
                patient=patient,
                visit=visit,
                patient_name=patient.name,
                gender=patient.gender,
                department=dept_obj.name if dept_obj else str(visit.department),
                status='Skipped',
                error_message=STATUS_NO_ELIGIBLE_INVESTIGATION
            )
        return primary_diagnosis, STATUS_NO_ELIGIBLE_INVESTIGATION

    with transaction.atomic():
        # Create ServiceRequest
        sr, created = ServiceRequest.objects.get_or_create(
            patient=patient,
            visit_no=visit.visit_no,
            defaults={
                'department': dept_obj,
                'visit_type': ServiceRequest.VisitTypeChoices.OP if visit.visit_type == 'OP' else ServiceRequest.VisitTypeChoices.INPATIENT,
                'status': ServiceRequest.StatusChoices.SAVED,
                'consultant_name': visit.unit_doctor or 'Consultant',
            }
        )

        # Create Primary Diagnosis on ServiceRequest
        ServiceRequestDiagnosis.objects.get_or_create(
            service_request=sr,
            diagnosis=primary_diagnosis,
            defaults={'sort_order': 0}
        )

        # Create ServiceRequestInvestigation for each eligible investigation
        for inv in eligible_investigations:
            ServiceRequestInvestigation.objects.get_or_create(
                service_request=sr,
                investigation=inv,
                defaults={
                    'qty': 1,
                    'source': ServiceRequestInvestigation.SourceChoices.AUTO_SUGGESTED,
                    'status': ServiceRequestInvestigation.StatusChoices.PENDING,
                }
            )

    logger.info(f"ATC Lab Workflow successfully created for Patient {patient.patient_id}: SR #{sr.id} with {len(eligible_investigations)} investigations.")
    return sr, STATUS_SUCCESS
