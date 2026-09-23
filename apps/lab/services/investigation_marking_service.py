import random
from datetime import date, datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum

from apps.patients.models import Patient, PatientVisit, Department
from apps.lab.models import (
    Diagnosis,
    Investigation,
    InvestigationParameter,
    PatientInvestigationOrder,
    ServiceRequest,
    ServiceRequestDiagnosis,
    ServiceRequestInvestigation,
    ServiceRequestResult,
    InvestigationMarkingConfig,
    InvestigationMarkingDepartment,
    InvestigationMarkingPatient,
    AutomationDummyResult,
)
from apps.lab.services.eligibility_engine import (
    calculate_patient_age,
    normalize_gender,
    get_eligible_diagnoses,
    get_eligible_investigations,
)
from apps.lab.services.automation_test_service import AutomationTestService
from apps.lab.services.result_classifier import classify_from_range_string


class InvestigationMarkingService:
    @staticmethod
    def get_or_create_config(marking_date, user=None):
        """Returns or creates the single InvestigationMarkingConfig for a date."""
        config, created = InvestigationMarkingConfig.objects.get_or_create(
            marking_date=marking_date,
            defaults={'status': InvestigationMarkingConfig.StatusChoices.DRAFT, 'created_by': user}
        )
        return config

    @staticmethod
    def get_available_counts(marking_date, department_id=None):
        """
        Returns count of unallocated D-patients for a given date and department.
        """
        qs = Patient.objects.filter(
            patient_type='D',
            registration_date=marking_date
        )
        if department_id:
            dept = Department.objects.filter(id=department_id).first()
            if dept:
                qs = qs.filter(Q(department_obj=dept) | Q(department__iexact=dept.name))

        # Exclude patients already selected in any existing config for this date
        selected_ids = InvestigationMarkingPatient.objects.filter(
            config__marking_date=marking_date
        ).values_list('patient_id', flat=True)

        qs = qs.exclude(id__in=selected_ids)

        male_count = qs.filter(gender__iexact='Male').count()
        female_count = qs.filter(gender__iexact='Female').count()
        return {
            'male': male_count,
            'female': female_count,
            'total': male_count + female_count
        }

    @staticmethod
    @transaction.atomic
    def add_department(config, department_id, male_count, female_count, user=None):
        """
        Validates, samples random D patients, determines primary diagnoses and eligible
        investigations, and persists to the database so that refreshing never alters the selection.
        """
        dept = Department.objects.get(id=department_id)

        # 1. Verify not already added in this config
        if InvestigationMarkingDepartment.objects.filter(config=config, department=dept).exists():
            raise ValueError(f"Department '{dept.name}' is already added to this configuration.")

        total_requested = int(male_count or 0) + int(female_count or 0)
        if total_requested <= 0:
            raise ValueError("Total count must be greater than 0.")

        # 2. Query candidate D patients on this date for this department
        candidate_qs = Patient.objects.filter(
            patient_type='D',
            registration_date=config.marking_date
        ).filter(
            Q(department_obj=dept) | Q(department__iexact=dept.name)
        )

        # Exclude already selected in this config
        already_selected = InvestigationMarkingPatient.objects.filter(config=config).values_list('patient_id', flat=True)
        candidate_qs = candidate_qs.exclude(id__in=already_selected)

        # 3. Random sample for males (shuffle ID pool)
        male_candidates = list(candidate_qs.filter(gender__iexact='Male').values_list('id', flat=True))
        random.shuffle(male_candidates)
        selected_male_ids = male_candidates[:int(male_count or 0)]

        # 4. Random sample for females (shuffle ID pool)
        female_candidates = list(candidate_qs.filter(gender__iexact='Female').values_list('id', flat=True))
        random.shuffle(female_candidates)
        selected_female_ids = female_candidates[:int(female_count or 0)]

        selected_patient_ids = selected_male_ids + selected_female_ids
        selected_patients = list(Patient.objects.filter(id__in=selected_patient_ids))

        # 5. Resolve Primary Diagnosis & Eligible Investigations for each selected patient
        for p in selected_patients:
            age_info = calculate_patient_age(
                dob=p.dob,
                ref_date=config.marking_date,
                age_years=p.age_years,
                age_months=p.age_months,
                age_days=p.age_days
            )

            # Determine Primary Diagnosis
            primary_diag = None
            # Check existing visit diagnosis
            visit_diag = PatientVisit.objects.filter(patient=p).exclude(diagnoses=None).first()
            if visit_diag and visit_diag.diagnoses.exists():
                primary_diag = visit_diag.diagnoses.first().diagnosis

            if not primary_diag:
                # Resolve via eligibility engine
                eligible_diagnoses = get_eligible_diagnoses(
                    patient_or_data=p,
                    department=dept,
                    pregnancy_status=False
                )
                if eligible_diagnoses:
                    primary_diag = eligible_diagnoses[0]

            # Determine Eligible Investigations
            eligible_invs = []
            if primary_diag:
                eligible_invs = get_eligible_investigations(
                    diagnosis=primary_diag,
                    patient_or_data=p,
                    department=dept,
                    pregnancy_status=False
                )

            inv_count = len(eligible_invs)
            inv_summary = f"{inv_count}" if inv_count > 0 else "0"

            InvestigationMarkingPatient.objects.create(
                config=config,
                department=dept,
                department_name=dept.name,
                patient=p,
                patient_id_str=p.patient_id,
                patient_name=p.name,
                age_display=age_info['display'],
                gender=p.gender or 'Male',
                primary_diagnosis=primary_diag,
                primary_diagnosis_name=primary_diag.name if primary_diag else "Clinical Evaluation",
                investigations_count=inv_count,
                investigations_summary=inv_summary
            )

        # 6. Create Department Record
        actual_male = len(selected_male_ids)
        actual_female = len(selected_female_ids)
        actual_total = actual_male + actual_female

        dept_record = InvestigationMarkingDepartment.objects.create(
            config=config,
            department=dept,
            department_name=dept.name,
            male_count=actual_male,
            female_count=actual_female,
            total_count=actual_total
        )

        # 7. Update Config Aggregates
        InvestigationMarkingService.recalculate_totals(config)
        return dept_record

    @staticmethod
    @transaction.atomic
    def remove_department(config, department_id):
        """Removes a department and all its selected patients from the config."""
        dept = Department.objects.get(id=department_id)
        InvestigationMarkingPatient.objects.filter(config=config, department=dept).delete()
        InvestigationMarkingDepartment.objects.filter(config=config, department=dept).delete()
        InvestigationMarkingService.recalculate_totals(config)

    @staticmethod
    def recalculate_totals(config):
        """Recalculates summary counts on the config."""
        agg = config.departments.aggregate(
            m=Sum('male_count'),
            f=Sum('female_count'),
            t=Sum('total_count')
        )
        config.total_male = agg['m'] or 0
        config.total_female = agg['f'] or 0
        config.total_patients = agg['t'] or 0
        config.save(update_fields=['total_male', 'total_female', 'total_patients', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def save_configuration(config, user=None):
        """Marks the current configuration as SAVED."""
        config.status = InvestigationMarkingConfig.StatusChoices.SAVED
        if user:
            config.created_by = user
        config.save(update_fields=['status', 'created_by', 'updated_at'])
        return config

    @staticmethod
    @transaction.atomic
    def trigger_investigations(config, user=None):
        """
        Executes Save & Trigger:
        1. Persists configuration.
        2. Creates ServiceRequest, ServiceRequestDiagnosis, ServiceRequestInvestigation.
        3. Creates PatientInvestigationOrder.
        4. Applies each investigation's turnaround interval.
        5. Generates result values and completes investigations.
        6. Integrates into Lab Orders, Work Orders, and Result View.
        """
        config.status = InvestigationMarkingConfig.StatusChoices.TRIGGERED
        config.triggered_at = timezone.now()
        if user:
            config.created_by = user
        config.save(update_fields=['status', 'triggered_at', 'created_by', 'updated_at'])

        patients_records = config.selected_patients.select_related('patient', 'department', 'primary_diagnosis').all()
        now = timezone.now()
        today = config.marking_date or now.date()

        for rec in patients_records:
            if rec.is_triggered and rec.service_request:
                continue

            p = rec.patient
            dept = rec.department
            primary_diag = rec.primary_diagnosis

            # Ensure PatientVisit exists
            visit = PatientVisit.objects.filter(patient=p).first()
            if not visit:
                visit_dt = timezone.make_aware(datetime.combine(today, datetime.min.time())) if timezone.is_aware(now) else datetime.combine(today, datetime.min.time())
                visit = PatientVisit.objects.create(
                    patient=p,
                    visit_no=1,
                    department=dept.name if dept else p.department,
                    department_obj=dept,
                    visit_type='OP',
                    category='CONSULTATION',
                    visit_date=visit_dt
                )

            # 1. Create ServiceRequest
            sr = ServiceRequest.objects.create(
                patient=p,
                visit_no=visit.visit_no,
                department=dept,
                visit_type=ServiceRequest.VisitTypeChoices.OP,
                request_date=today,
                status=ServiceRequest.StatusChoices.SAVED,
                consultant_name=visit.unit_doctor or 'HOD-GENERAL MEDICINE-V',
                created_by=user
            )

            # 2. Attach Primary Diagnosis
            if primary_diag:
                ServiceRequestDiagnosis.objects.create(
                    service_request=sr,
                    diagnosis=primary_diag,
                    sort_order=0
                )

            # 3. Determine eligible investigations
            eligible_invs = []
            if primary_diag:
                eligible_invs = get_eligible_investigations(
                    diagnosis=primary_diag,
                    patient_or_data=p,
                    department=dept,
                    pregnancy_status=False
                )

            # If no diagnosis or no mapped invs, fallback to common routine investigations
            if not eligible_invs:
                dept_name = dept.name if dept else ''
                eligible_invs = list(Investigation.objects.filter(
                    department__name__iexact=dept_name,
                    is_active=True
                )[:3])
                if not eligible_invs:
                    eligible_invs = list(Investigation.objects.filter(is_active=True)[:2])

            max_interval_hours = 1
            for inv in eligible_invs:
                # Interval handling: use configured turnaround time hours
                inv_interval = inv.turnaround_time_hours if (inv.turnaround_time_hours and inv.turnaround_time_hours > 0) else 1
                if inv_interval > max_interval_hours:
                    max_interval_hours = inv_interval

                # Create ServiceRequestInvestigation
                sri = ServiceRequestInvestigation.objects.create(
                    service_request=sr,
                    investigation=inv,
                    qty=1,
                    source=ServiceRequestInvestigation.SourceChoices.AUTO_SUGGESTED,
                    status=ServiceRequestInvestigation.StatusChoices.RECEIVED,
                    received_date=today,
                    received_time=now.time(),
                    received_by=user
                )

                # Create PatientInvestigationOrder
                order, _ = PatientInvestigationOrder.objects.get_or_create(
                    patient=p,
                    diagnosis=primary_diag,
                    investigation=inv,
                    defaults={
                        'ordered_by': user,
                        'status': PatientInvestigationOrder.StatusChoices.PENDING
                    }
                )

                # Auto-generate results via dummy values or result classifier
                patient_age_days = (p.age_years or 30) * 365
                dummy_result = AutomationTestService.generate_dummy_values_for_investigation(
                    inv,
                    age_days=patient_age_days,
                    gender=p.gender
                )
                if isinstance(dummy_result, dict):
                    params_list = dummy_result.get('parameters', [])
                elif isinstance(dummy_result, list):
                    params_list = dummy_result
                else:
                    params_list = []

                for dp in params_list:
                    ip = InvestigationParameter.objects.filter(
                        investigation=inv,
                        parameter_id=dp.get('parameter_id'),
                        is_active=True
                    ).first()
                    if not ip and dp.get('parameter_id'):
                        ip = InvestigationParameter.objects.filter(
                            investigation=inv,
                            id=dp.get('parameter_id'),
                            is_active=True
                        ).first()
                    if ip:
                        val = str(dp.get('result_value', '0'))
                        ref_str = dp.get('reference_range', '')
                        status = classify_from_range_string(val, ref_str)
                        ServiceRequestResult.objects.create(
                            sr_investigation=sri,
                            investigation_parameter=ip,
                            result_value=val,
                            status=status,
                            remarks="Auto-triggered via Investigation Marking",
                            entered_by=user
                        )

                # Complete investigation & order
                sri.status = ServiceRequestInvestigation.StatusChoices.COMPLETED
                sri.completed_date = now
                sri.completed_by = user
                sri.save(update_fields=['status', 'completed_date', 'completed_by'])

                order.status = PatientInvestigationOrder.StatusChoices.COMPLETED
                order.save(update_fields=['status'])

            comp_due = now + timedelta(hours=max_interval_hours)
            rec.service_request = sr
            rec.is_triggered = True
            rec.triggered_at = now
            rec.completion_due_at = comp_due
            rec.save(update_fields=['service_request', 'is_triggered', 'triggered_at', 'completion_due_at', 'updated_at'])

        return config

    @staticmethod
    @transaction.atomic
    def clear_configuration(config):
        """Clears all departments and selected patients for a config."""
        config.selected_patients.all().delete()
        config.departments.all().delete()
        config.total_male = 0
        config.total_female = 0
        config.total_patients = 0
        config.status = InvestigationMarkingConfig.StatusChoices.DRAFT
        config.save()
        return config
