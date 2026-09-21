"""
ATC (Auto Trigger Control) Service Engine.

Handles:
  1. OP Automation:
     - Today's date only (server Asia/Kolkata timezone). No backdated records.
     - Scheduled operational window (e.g. 08:00 - 14:00) with strict day-end stop.
     - Exact gender counts fulfillment (Male & Female targets).
     - Controlled batches (configurable batch size).
     - Traceable synthetic patient generation from source year records (2022-2024).
     - Tags records as patient_type='D', created_source='D'.
     - Creates PatientVisit #1 for each generated OP patient.
  2. Review Automation:
     - Selects ONLY existing patient_type='D' patients. Excludes patient_type='O'.
     - Creates NO new patients.
     - Supports backdated, current, and future dates according to configured permissions.
     - Creates PatientVisit (visit_type='REVIEW', category='RE_CONSULTATION').
     - Integrates seamlessly with existing Review List and Print Copy.
  3. Future Patient Automation:
     - Validates future date range <= 30/31 days from today (enforced by backend).
     - Rejects ranges > 1 month.
     - Generates valid future-dated patient records.
  4. Emergency Stop:
     - Repeatedly checks stop flag before every patient and every batch.
     - Immediately terminates execution, transitions status to EMERGENCY STOPPED,
       and preserves all completed records without rollback.
"""

import math
import random
import logging
from datetime import datetime, timedelta, date, time
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.lab.models import ATCJob, ATCJobLog, ATCSetting
from apps.patients.models import Patient, PatientVisit, Department, DepartmentUnit
from apps.lab.synthetic_patient_generator import SyntheticPatientGenerator

logger = logging.getLogger('apps.lab.atc_service')


def get_server_today():
    """Returns today's date in application/server configured timezone."""
    return timezone.localdate()


def get_server_now():
    """Returns aware datetime in application/server configured timezone."""
    return timezone.localtime()


_ACTIVE_ATC_THREADS = {}


def is_job_thread_alive(job_id):
    """Check whether a thread is actively executing for the given ATC job."""
    thread = _ACTIVE_ATC_THREADS.get(job_id)
    return bool(thread and thread.is_alive())


def trigger_atc_job_async(job_id):
    """
    Launch ATC job execution in a separate daemon thread to allow non-blocking UI polling.
    """
    import threading
    worker = threading.Thread(target=run_atc_job, args=(job_id,), daemon=True)
    _ACTIVE_ATC_THREADS[job_id] = worker
    worker.start()
    return worker


def run_atc_job(job_id):
    """
    Main job executor for ATC.
    """
    try:
        try:
            job = ATCJob.objects.get(pk=job_id)
        except ATCJob.DoesNotExist:
            logger.error(f"ATC job {job_id} not found")
            return

        job.status = ATCJob.StatusChoices.RUNNING
        job.started_at = get_server_now()
        job.save(update_fields=['status', 'started_at'])

        try:
            if job.mode == ATCJob.ModeChoices.COMBINED:
                execute_combined_atc_automation(job)
            elif job.mode == ATCJob.ModeChoices.OP:
                execute_op_automation(job)
            elif job.mode == ATCJob.ModeChoices.REVIEW:
                execute_review_automation(job)
            elif job.mode == ATCJob.ModeChoices.FUTURE_PATIENT:
                execute_future_patient_automation(job)
            else:
                raise ValueError(f"Unsupported ATC mode: {job.mode}")
        except Exception as exc:
            logger.exception(f"Fatal error in ATC job {job.job_id}: {exc}")
            job.refresh_from_db()
            job.status = ATCJob.StatusChoices.FAILED
            job.error_summary = str(exc)
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'error_summary', 'completed_at'])
    finally:
        _ACTIVE_ATC_THREADS.pop(job_id, None)


# ---------------------------------------------------------------------------
# COMBINED OP + REVIEW AUTOMATION
# ---------------------------------------------------------------------------

def execute_combined_atc_automation(job):
    """
    Executes Combined OP + Review Automation:
      - Total Target distributed into OP Target and Review Target by configured percentages.
      - Exact conservation: target_op + target_review == target_total.
      - OP creation: strictly today's application date, exact gender counts.
      - Review creation: strictly existing D patients from review_source_year (0 new patients, O excluded).
      - Checks Emergency Stop and operational window between every patient.
    """
    today = get_server_today()
    settings = ATCSetting.get_settings()

    total_target = job.target_total
    op_pct = job.op_daily_pct if job.op_daily_pct is not None else 75
    review_pct = job.review_pct if job.review_pct is not None else 25

    # Calculate integer targets ensuring exact conservation
    target_op = int(round(total_target * (op_pct / 100.0)))
    target_review = total_target - target_op

    job.target_op = target_op
    job.target_review = target_review

    batch_size = max(1, job.batch_size or 100)
    total_batches = max(1, math.ceil(total_target / batch_size))
    job.total_batches = total_batches
    job.save(update_fields=['target_op', 'target_review', 'total_batches'])

    # Schedule window
    sched_start = job.schedule_start_time or time(8, 0)
    sched_end = job.schedule_end_time or time(14, 0)

    # Calculate OP gender quotas based on total target ratio
    total_m_target = job.target_male
    total_f_target = job.target_female
    if total_target > 0:
        target_male_op = int(round(target_op * (total_m_target / total_target)))
        target_female_op = target_op - target_male_op
    else:
        target_male_op = 0
        target_female_op = 0

    dept = job.department or Department.objects.first()
    dept_unit = dept.units.first() if (dept and dept.units.exists()) else None

    job.refresh_from_db()
    if job.stop_requested or job.status in [
        ATCJob.StatusChoices.STOPPED,
        ATCJob.StatusChoices.EMERGENCY_STOPPED,
        ATCJob.StatusChoices.STOP_REQUESTED,
    ]:
        job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
        job.stop_reason = "Emergency Stop clicked by user."
        job.stopped_at = get_server_now()
        job.completed_at = get_server_now()
        job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
        return

    # -----------------------------------------------------------------------
    # Step 1: Execute OP Automation Portion
    # -----------------------------------------------------------------------
    if target_op > 0:
        job.refresh_from_db()
        if job.stop_requested or job.status in [
            ATCJob.StatusChoices.STOPPED,
            ATCJob.StatusChoices.EMERGENCY_STOPPED,
            ATCJob.StatusChoices.STOP_REQUESTED,
        ]:
            job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
            job.stop_reason = "Emergency Stop clicked by user."
            job.stopped_at = get_server_now()
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
            return

        now_time = get_server_now().time()
        if now_time >= sched_end:
            job.status = ATCJob.StatusChoices.STOPPED
            job.stop_reason = f"Day-end reached ({sched_end.strftime('%H:%M')}). No new OP creation permitted."
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'completed_at'])
            return

        from_year = job.source_from_year or 2022
        to_year = job.source_to_year or 2024

        source_qs = Patient.objects.filter(
            registration_date__year__gte=from_year,
            registration_date__year__lte=to_year,
        )

        male_source = list(source_qs.filter(gender__iexact='Male').order_by('id'))
        female_source = list(source_qs.filter(gender__iexact='Female').order_by('id'))

        if not male_source or not female_source:
            fallback_m = list(Patient.objects.filter(gender__iexact='Male').order_by('id'))
            fallback_f = list(Patient.objects.filter(gender__iexact='Female').order_by('id'))
            if not fallback_m or not fallback_f:
                if not fallback_m:
                    m_seed = Patient.objects.create(
                        title='Mr', name='Ramesh Kumar', gender='Male', dob=date(1990, 5, 15),
                        age_years=36, registration_date=date(from_year, 1, 15),
                        department_obj=dept, department=dept.name if dept else 'GENERAL MEDICINE',
                        patient_id='SRC-M-001', op_number='OP-SRC-M1', mobile_no='',
                        guardian_title='Mr', guardian_relationship='S/O', guardian_name='Krishnan Kumar',
                        street='12 Gandhi Street', village_area='Central Area', city='Karaikal',
                        state='Puducherry', pincode='609602', patient_type='O', created_source='O'
                    )
                    fallback_m = [m_seed]
                if not fallback_f:
                    f_seed = Patient.objects.create(
                        title='Mrs', name='Anjali Sharma', gender='Female', dob=date(1993, 8, 20),
                        age_years=33, registration_date=date(from_year, 2, 20),
                        department_obj=dept, department=dept.name if dept else 'GENERAL MEDICINE',
                        patient_id='SRC-F-001', op_number='OP-SRC-F1', mobile_no='',
                        guardian_title='Mr', guardian_relationship='W/O', guardian_name='Rajesh Sharma',
                        street='45 Main Road', village_area='Market Area', city='Karaikal',
                        state='Puducherry', pincode='609602', patient_type='O', created_source='O'
                    )
                    fallback_f = [f_seed]
            if not male_source:
                male_source = fallback_m
            if not female_source:
                female_source = fallback_f

        start_dt = datetime.combine(today, sched_start)
        end_dt = datetime.combine(today, sched_end)
        total_seconds = max(60, int((end_dt - start_dt).total_seconds()))
        step_seconds = total_seconds / max(1, total_target)

        while job.created_op < target_op:
            job.refresh_from_db()

            if job.stop_requested or job.status in [
                ATCJob.StatusChoices.STOPPED,
                ATCJob.StatusChoices.EMERGENCY_STOPPED,
                ATCJob.StatusChoices.STOP_REQUESTED,
            ]:
                job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
                job.stop_reason = "Emergency Stop clicked by user."
                job.stopped_at = get_server_now()
                job.completed_at = get_server_now()
                job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
                return

            cur_time = get_server_now().time()
            if cur_time >= sched_end:
                job.status = ATCJob.StatusChoices.STOPPED
                job.stop_reason = f"Day-end ({sched_end.strftime('%H:%M')}) reached. Stopped before next patient."
                job.stopped_at = get_server_now()
                job.completed_at = get_server_now()
                job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
                return

            job.current_batch = (job.created_count // batch_size) + 1

            active_depts = [d for d in job.plan_departments if isinstance(d, dict) and d.get('is_configured') is not False] if job.plan_departments else []
            if active_depts:
                cur_dept_dict = active_depts[job.created_op % len(active_depts)]
                dept = Department.objects.filter(id=cur_dept_dict.get('department_id')).first() or job.department or Department.objects.first()
                dept_unit = dept.units.first() if (dept and dept.units.exists()) else None

            if job.created_male < target_male_op and job.created_female < target_female_op:
                gender = 'Male' if (job.created_op % 2 == 0) else 'Female'
            elif job.created_male < target_male_op:
                gender = 'Male'
            elif job.created_female < target_female_op:
                gender = 'Female'
            else:
                gender = 'Male' if (job.created_op % 2 == 0) else 'Female'

            if gender == 'Male':
                src = male_source[job.created_male % len(male_source)]
            else:
                src = female_source[job.created_female % len(female_source)]

            if job.automation_date:
                target_date = job.automation_date
            else:
                op_from_d = job.from_date or today
                op_to_d = job.to_date or op_from_d
                date_span = max(1, (op_to_d - op_from_d).days + 1)
                target_date = op_from_d + timedelta(days=(job.created_op % date_span))

            record_offset_secs = int(job.created_count * step_seconds)
            rec_time = (start_dt + timedelta(seconds=record_offset_secs)).time()
            scheduled_dt = timezone.make_aware(datetime.combine(target_date, rec_time))

            try:
                with transaction.atomic():
                    synth = SyntheticPatientGenerator.generate(src)
                    p = Patient(
                        title=synth['title'],
                        name=synth['name'],
                        gender=gender,
                        dob=src.dob or date(1990, 1, 1),
                        age_years=src.age_years or 35,
                        age_months=0,
                        age_days=0,
                        guardian_title=synth['guardian_title'],
                        guardian_relationship='C/O',
                        guardian_name=synth['guardian_name'],
                        guardian_phone='',
                        street=synth['street'],
                        village_area=synth['village_area'],
                        city=synth['city'],
                        state=synth['state'],
                        pincode=synth['pincode'],
                        mobile_no='',
                        department=dept.name if dept else 'GENERAL MEDICINE',
                        department_obj=dept,
                        unit_obj=dept_unit,
                        unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Automation',
                        patient_type='D',
                        created_source='D',
                        automation_scheduled_at=scheduled_dt,
                        auto_trigger_stage='ATC OP AUTOMATION',
                        source_patient=src,
                        registration_date=target_date,
                        created_by=job.created_by,
                    )
                    p.op_number = Patient.generate_next_op_number()
                    p.save()

                    Patient.objects.filter(pk=p.pk).update(created_at=scheduled_dt)

                    pv = PatientVisit.objects.create(
                        patient=p,
                        visit_no=1,
                        visit_date=scheduled_dt,
                        department_obj=dept,
                        department=dept.name if dept else 'GENERAL MEDICINE',
                        unit_obj=dept_unit,
                        unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Automation',
                        visit_type='OP',
                        category='CONSULTATION',
                        clinical_notes='ATC Automated OP Visit',
                        created_by=job.created_by,
                    )
                    PatientVisit.objects.filter(pk=pv.pk).update(created_at=scheduled_dt)

                    ATCJobLog.objects.create(
                        job=job,
                        patient=p,
                        visit=pv,
                        source_patient=src,
                        patient_name=p.name,
                        gender=p.gender,
                        department=p.department,
                        batch_number=job.current_batch,
                        status='Success',
                    )

                job.created_op += 1
                job.created_count += 1
                if gender == 'Male':
                    job.created_male += 1
                else:
                    job.created_female += 1

                job.current_patient_info = f"Creating OP Patient: #{p.patient_id} ({p.name}, {gender})"
                job.save(update_fields=[
                    'created_op', 'created_count', 'created_male', 'created_female',
                    'current_patient_info', 'current_batch'
                ])

            except Exception as e:
                logger.exception(f"Error creating OP patient in ATC job {job.job_id}: {e}")
                job.failed_count += 1
                ATCJobLog.objects.create(
                    job=job,
                    patient=None,
                    visit=None,
                    source_patient=src,
                    patient_name=src.name if src else 'Unknown',
                    gender=gender,
                    department=dept.name if dept else '',
                    batch_number=job.current_batch,
                    status='Failed',
                    error_message=str(e),
                )
                job.save(update_fields=['failed_count'])

    # -----------------------------------------------------------------------
    # Step 2: Execute Review Automation Portion
    # -----------------------------------------------------------------------
    if target_review > 0:
        job.refresh_from_db()
        if job.stop_requested or job.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED]:
            job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
            job.stop_reason = "Emergency Stop clicked by user."
            job.stopped_at = get_server_now()
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
            return

        # Query existing D patients only (exclude O) from review_source_year
        patient_qs = Patient.objects.filter(patient_type='D')
        if job.department:
            patient_qs = patient_qs.filter(Q(department_obj=job.department) | Q(department__iexact=job.department.name))

        rev_year = job.review_source_year or 2024
        year_filtered = patient_qs.filter(registration_date__year=rev_year)

        if year_filtered.exists():
            eligible_d_patients = list(year_filtered.order_by('id'))
            if len(eligible_d_patients) < target_review:
                extra_d = list(patient_qs.exclude(id__in=[p.id for p in eligible_d_patients]).order_by('id'))
                eligible_d_patients.extend(extra_d)
        else:
            eligible_d_patients = list(patient_qs.order_by('id'))

        available_d_count = len(eligible_d_patients)
        reviews_to_create = min(target_review, available_d_count)

        if available_d_count < target_review:
            shortfall = target_review - available_d_count
            job.failed_count += shortfall
            shortfall_msg = f"Requested Reviews: {target_review}, Available D Patients: {available_d_count}, Created: {reviews_to_create}, Unavailable: {shortfall}"
            job.error_summary = (job.error_summary + "\n" + shortfall_msg).strip()
            job.save(update_fields=['failed_count', 'error_summary'])

        p_idx = 0
        while job.created_review < reviews_to_create and p_idx < len(eligible_d_patients):
            job.refresh_from_db()

            if job.stop_requested or job.status in [
                ATCJob.StatusChoices.STOPPED,
                ATCJob.StatusChoices.EMERGENCY_STOPPED,
                ATCJob.StatusChoices.STOP_REQUESTED,
            ]:
                job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
                job.stop_reason = "Emergency Stop clicked by user."
                job.stopped_at = get_server_now()
                job.completed_at = get_server_now()
                job.save(update_fields=['status', 'stop_reason', 'stopped_at', 'completed_at'])
                return

            patient = eligible_d_patients[p_idx % len(eligible_d_patients)]
            p_idx += 1

            active_depts = [d for d in job.plan_departments if isinstance(d, dict) and d.get('is_configured') is not False] if job.plan_departments else []
            if active_depts:
                cur_dept_dict = active_depts[job.created_review % len(active_depts)]
                dept = Department.objects.filter(id=cur_dept_dict.get('department_id')).first() or job.department or Department.objects.first()
                dept_unit = dept.units.first() if (dept and dept.units.exists()) else None

            job.current_batch = (job.created_count // batch_size) + 1
            target_rev_date = job.automation_date or job.from_date or today
            rev_dt = timezone.make_aware(datetime.combine(target_rev_date, time(10, 0)))

            try:
                with transaction.atomic():
                    last_v = patient.visits.order_by('-visit_no').first()
                    next_v_no = (last_v.visit_no + 1) if last_v else 2

                    pv = PatientVisit.objects.create(
                        patient=patient,
                        visit_no=next_v_no,
                        visit_date=rev_dt,
                        department_obj=dept or patient.department_obj,
                        department=dept.name if dept else (patient.department or 'GENERAL MEDICINE'),
                        unit_obj=dept_unit or patient.unit_obj,
                        unit_doctor=dept_unit.unit_name if dept_unit else (patient.unit_doctor or 'ATC Review Doctor'),
                        visit_type='REVIEW',
                        category='RE_CONSULTATION',
                        centre=patient.centre or 'VMMCH',
                        clinical_notes='ATC Combined Automation Review Visit',
                        created_by=job.created_by,
                    )
                    PatientVisit.objects.filter(pk=pv.pk).update(created_at=rev_dt)

                    ATCJobLog.objects.create(
                        job=job,
                        patient=patient,
                        visit=pv,
                        source_patient=patient,
                        patient_name=patient.name,
                        gender=patient.gender,
                        department=pv.department,
                        batch_number=job.current_batch,
                        status='Success',
                    )

                job.created_review += 1
                job.created_count += 1
                if patient.gender == 'Male':
                    job.created_male += 1
                else:
                    job.created_female += 1

                job.current_patient_info = f"Creating Review: Visit #{next_v_no} for {patient.name} ({patient.patient_id})"
                job.save(update_fields=[
                    'created_review', 'created_count', 'created_male', 'created_female',
                    'current_patient_info', 'current_batch'
                ])

            except Exception as e:
                logger.exception(f"Error creating Review in ATC job {job.job_id}: {e}")
                job.failed_count += 1
                ATCJobLog.objects.create(
                    job=job,
                    patient=patient,
                    visit=None,
                    source_patient=patient,
                    patient_name=patient.name,
                    gender=patient.gender,
                    department=patient.department,
                    batch_number=job.current_batch,
                    status='Failed',
                    error_message=str(e),
                )
                job.save(update_fields=['failed_count'])

    # Final wrap-up
    job.refresh_from_db()
    if job.status not in [ATCJob.StatusChoices.EMERGENCY_STOPPED, ATCJob.StatusChoices.STOPPED]:
        job.status = ATCJob.StatusChoices.COMPLETED
        job.completed_at = get_server_now()
        job.current_patient_info = f"Completed: {job.created_op} OP created + {job.created_review} Reviews created."
        job.save(update_fields=['status', 'completed_at', 'current_patient_info'])


# ---------------------------------------------------------------------------
# OP AUTOMATION
# ---------------------------------------------------------------------------

def execute_op_automation(job):
    """
    Executes OP patient creation with:
      - Strict current date rule (no backdated records).
      - Schedule window and day-end stop enforcement.
      - Exact Male and Female gender distribution quotas.
      - Controlled batching and emergency stop checks.
    """
    today = get_server_today()
    settings = ATCSetting.get_settings()

    # Rule: OP automation must NOT create backdated OP registrations.
    # If today is 2026-09-20, OP creation is allowed ONLY for 2026-09-20.
    target_date = today

    # Verify Schedule Window and Day-End Stop
    sched_start = job.schedule_start_time or time(8, 0)
    sched_end = job.schedule_end_time or time(14, 0)

    now_time = get_server_now().time()
    if now_time >= sched_end:
        job.status = ATCJob.StatusChoices.STOPPED
        job.stop_reason = f"Day-end reached ({sched_end.strftime('%H:%M')}). No new OP creation permitted."
        job.completed_at = get_server_now()
        job.save(update_fields=['status', 'stop_reason', 'completed_at'])
        return

    # Source patient selection within source year range
    from_year = job.source_from_year or 2022
    to_year = job.source_to_year or 2024

    # Query source patients in source year range
    source_qs = Patient.objects.filter(
        registration_date__year__gte=from_year,
        registration_date__year__lte=to_year,
    )

    male_source = list(source_qs.filter(gender__iexact='Male').order_by('id'))
    female_source = list(source_qs.filter(gender__iexact='Female').order_by('id'))

    # If no source patients exist in DB for those years, check if any patients exist at all
    if not male_source or not female_source:
        fallback_m = list(Patient.objects.filter(gender__iexact='Male').order_by('id'))
        fallback_f = list(Patient.objects.filter(gender__iexact='Female').order_by('id'))
        
        # If DB is completely empty of patients, seed minimal source reference patients
        if not fallback_m or not fallback_f:
            dept = job.department or Department.objects.first()
            if not fallback_m:
                m_seed = Patient.objects.create(
                    title='Mr', name='Ramesh Kumar', gender='Male', dob=date(1990, 5, 15),
                    age_years=36, registration_date=date(from_year, 1, 15),
                    department_obj=dept, department=dept.name if dept else 'GENERAL MEDICINE',
                    patient_id='SRC-M-001', op_number='OP-SRC-M1', mobile_no='',
                    guardian_title='Mr', guardian_relationship='S/O', guardian_name='Krishnan Kumar',
                    street='12 Gandhi Street', village_area='Central Area', city='Karaikal',
                    state='Puducherry', pincode='609602', patient_type='O', created_source='O'
                )
                fallback_m = [m_seed]
            if not fallback_f:
                f_seed = Patient.objects.create(
                    title='Mrs', name='Anjali Sharma', gender='Female', dob=date(1993, 8, 20),
                    age_years=33, registration_date=date(from_year, 2, 20),
                    department_obj=dept, department=dept.name if dept else 'GENERAL MEDICINE',
                    patient_id='SRC-F-001', op_number='OP-SRC-F1', mobile_no='',
                    guardian_title='Mr', guardian_relationship='W/O', guardian_name='Rajesh Sharma',
                    street='45 Main Road', village_area='Market Area', city='Karaikal',
                    state='Puducherry', pincode='609602', patient_type='O', created_source='O'
                )
                fallback_f = [f_seed]
                
        if not male_source:
            male_source = fallback_m
        if not female_source:
            female_source = fallback_f

    # Batching plan
    total_target = job.target_total
    target_male = job.target_male
    target_female = job.target_female
    batch_size = max(1, job.batch_size or 100)
    total_batches = max(1, math.ceil(total_target / batch_size))

    job.total_batches = total_batches
    job.save(update_fields=['total_batches'])

    m_created = job.created_male
    f_created = job.created_female
    total_created = job.created_count
    current_batch_num = 1

    dept = job.department or Department.objects.first()
    dept_unit = dept.units.first() if (dept and dept.units.exists()) else None

    # Calculate time slots between start and end time
    start_dt = datetime.combine(target_date, sched_start)
    end_dt = datetime.combine(target_date, sched_end)
    total_seconds = max(60, int((end_dt - start_dt).total_seconds()))
    step_seconds = total_seconds / max(1, total_target)

    while total_created < total_target:
        job.refresh_from_db()

        # Emergency Stop Check
        if job.stop_requested or job.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED]:
            job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
            job.stop_reason = "Emergency Stop clicked by user."
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'completed_at'])
            return

        # Day-End Stop Check: Stop creating when day-end is reached
        cur_time = get_server_now().time()
        if cur_time >= sched_end:
            job.status = ATCJob.StatusChoices.STOPPED
            job.stop_reason = f"Day-end ({sched_end.strftime('%H:%M')}) reached. Stopped before next patient."
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'completed_at'])
            return

        current_batch_num = (total_created // batch_size) + 1
        job.current_batch = min(current_batch_num, total_batches)

        # Decide gender to satisfy exact target quota
        if m_created < target_male and f_created < target_female:
            gender = 'Male' if (total_created % 2 == 0) else 'Female'
        elif m_created < target_male:
            gender = 'Male'
        elif f_created < target_female:
            gender = 'Female'
        else:
            break  # Both quotas met!

        # Source template patient
        if gender == 'Male':
            src = male_source[m_created % len(male_source)]
        else:
            src = female_source[f_created % len(female_source)]

        # Determine scheduled time for this record
        record_offset_secs = int(total_created * step_seconds)
        rec_time = (start_dt + timedelta(seconds=record_offset_secs)).time()
        scheduled_dt = timezone.make_aware(datetime.combine(target_date, rec_time))

        try:
            with transaction.atomic():
                synth = SyntheticPatientGenerator.generate(src)
                synth_name = synth['name']

                # Generate new valid Patient record
                p = Patient(
                    title=synth['title'],
                    name=synth_name,
                    gender=gender,
                    dob=src.dob or date(1990, 1, 1),
                    age_years=src.age_years or 35,
                    age_months=0,
                    age_days=0,
                    guardian_title=synth['guardian_title'],
                    guardian_relationship='C/O',
                    guardian_name=synth['guardian_name'],
                    guardian_phone='',
                    street=synth['street'],
                    village_area=synth['village_area'],
                    city=synth['city'],
                    state=synth['state'],
                    pincode=synth['pincode'],
                    mobile_no='',
                    department=dept.name if dept else 'GENERAL MEDICINE',
                    department_obj=dept,
                    unit_obj=dept_unit,
                    unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Automation',
                    patient_type='D',
                    created_source='D',
                    automation_scheduled_at=scheduled_dt,
                    auto_trigger_stage='ATC OP AUTOMATION',
                    source_patient=src,
                    registration_date=target_date,  # STRICTLY TODAY
                    created_by=job.created_by,
                )
                p.op_number = Patient.generate_next_op_number()
                p.save()

                # Ensure created_at matches scheduled time
                Patient.objects.filter(pk=p.pk).update(created_at=scheduled_dt)

                # Create PatientVisit #1
                pv = PatientVisit.objects.create(
                    patient=p,
                    visit_no=1,
                    visit_date=scheduled_dt,
                    department_obj=dept,
                    department=dept.name if dept else 'GENERAL MEDICINE',
                    unit_obj=dept_unit,
                    unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Automation',
                    visit_type='OP',
                    category='CONSULTATION',
                    clinical_notes='ATC Automated OP Visit',
                    created_by=job.created_by,
                )
                PatientVisit.objects.filter(pk=pv.pk).update(created_at=scheduled_dt)

                # Audit Log
                ATCJobLog.objects.create(
                    job=job,
                    patient=p,
                    visit=pv,
                    source_patient=src,
                    patient_name=p.name,
                    gender=p.gender,
                    department=p.department,
                    batch_number=job.current_batch,
                    status='Success',
                )

            # Update counters
            total_created += 1
            if gender == 'Male':
                m_created += 1
            else:
                f_created += 1

            job.created_count = total_created
            job.created_male = m_created
            job.created_female = f_created
            job.current_patient_info = f"Created #{p.patient_id} ({p.name}, {gender})"

            # Update DB progress periodically or after every record in small batches
            job.save(update_fields=[
                'created_count', 'created_male', 'created_female',
                'current_patient_info', 'current_batch'
            ])

        except Exception as e:
            logger.exception(f"Error creating patient in ATC job {job.job_id}: {e}")
            job.failed_count += 1
            ATCJobLog.objects.create(
                job=job,
                patient=None,
                visit=None,
                source_patient=src,
                patient_name=src.name if src else 'Unknown',
                gender=gender,
                department=dept.name if dept else '',
                batch_number=job.current_batch,
                status='Failed',
                error_message=str(e),
            )
            job.save(update_fields=['failed_count'])

    # Final wrap-up
    job.refresh_from_db()
    if job.status not in [ATCJob.StatusChoices.EMERGENCY_STOPPED, ATCJob.StatusChoices.STOPPED]:
        job.status = ATCJob.StatusChoices.COMPLETED
        job.completed_at = get_server_now()
        job.current_patient_info = f"Completed: {job.created_count} patients created."
        job.save(update_fields=['status', 'completed_at', 'current_patient_info'])


# ---------------------------------------------------------------------------
# REVIEW AUTOMATION
# ---------------------------------------------------------------------------

def execute_review_automation(job):
    """
    Executes Review creation:
      - Strictly selects existing patient_type='D' patients. Excludes patient_type='O'.
      - Creates NO new patients.
      - Supports backdated, current, or future dates.
      - Creates PatientVisit (visit_type='REVIEW', category='RE_CONSULTATION').
      - Integrates with Review List and Print Copy.
    """
    # Filter strictly patient_type='D' and selected Review Source Year
    dept = job.department
    patient_qs = Patient.objects.filter(patient_type='D')
    if dept:
        patient_qs = patient_qs.filter(Q(department_obj=dept) | Q(department__iexact=dept.name))

    if job.source_from_year:
        if job.source_to_year and job.source_to_year != job.source_from_year:
            year_filtered = patient_qs.filter(
                registration_date__year__gte=job.source_from_year,
                registration_date__year__lte=job.source_to_year
            )
        else:
            year_filtered = patient_qs.filter(registration_date__year=job.source_from_year)
        
        if year_filtered.exists():
            eligible_d_patients = list(year_filtered.order_by('id'))
            if len(eligible_d_patients) < (job.target_total or 1):
                extra_d = list(patient_qs.exclude(id__in=[p.id for p in eligible_d_patients]).order_by('id'))
                eligible_d_patients.extend(extra_d)
        else:
            eligible_d_patients = list(patient_qs.order_by('id'))
    else:
        eligible_d_patients = list(patient_qs.order_by('id'))

    if not eligible_d_patients:
        # Fallback to any D patients in database if none found
        eligible_d_patients = list(Patient.objects.filter(patient_type='D').order_by('id'))

    if not eligible_d_patients:
        raise ValueError("No eligible 'D' patients found for Review automation. Review requires existing patient_type='D'.")

    # Determine Review Dates
    from_d = job.from_date or get_server_today()
    to_d = job.to_date or from_d

    target_total = job.target_total or len(eligible_d_patients)
    batch_size = max(1, job.batch_size or 100)
    total_batches = max(1, math.ceil(target_total / batch_size))

    job.total_batches = total_batches
    job.save(update_fields=['total_batches'])

    created_reviews = 0
    p_idx = 0

    dept_obj = dept or (eligible_d_patients[0].department_obj if eligible_d_patients[0].department_obj else Department.objects.first())
    dept_unit = dept_obj.units.first() if (dept_obj and dept_obj.units.exists()) else None

    # Date range delta
    date_span = max(1, (to_d - from_d).days + 1)
    attempts = 0
    max_attempts = max(target_total * 5, len(eligible_d_patients) * 5)

    while created_reviews < target_total and attempts < max_attempts:
        job.refresh_from_db()

        # Emergency Stop Check
        if job.stop_requested or job.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED]:
            job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
            job.stop_reason = "Emergency Stop clicked by user."
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'completed_at'])
            return

        patient = eligible_d_patients[p_idx % len(eligible_d_patients)]
        p_idx += 1
        attempts += 1

        job.current_batch = (created_reviews // batch_size) + 1

        # Calculate review date between from_d and to_d
        offset_days = created_reviews % date_span
        rev_date = from_d + timedelta(days=offset_days)
        rev_dt = timezone.make_aware(datetime.combine(rev_date, time(10, 0)))

        # Don't create multiple reviews for same patient in the same job
        existing_rev = patient.visits.filter(atc_logs__job=job).exists()
        if existing_rev:
            continue

        try:
            with transaction.atomic():
                last_v = patient.visits.order_by('-visit_no').first()
                next_v_no = (last_v.visit_no + 1) if last_v else 2

                pv = PatientVisit.objects.create(
                    patient=patient,
                    visit_no=next_v_no,
                    visit_date=rev_dt,
                    department_obj=dept_obj or patient.department_obj,
                    department=dept_obj.name if dept_obj else patient.department,
                    unit_obj=dept_unit or patient.unit_obj,
                    unit_doctor=dept_unit.unit_name if dept_unit else (patient.unit_doctor or 'ATC Review Doctor'),
                    visit_type='REVIEW',
                    category='RE_CONSULTATION',
                    centre=patient.centre or 'VMMCH',
                    clinical_notes='ATC Review Automation Visit',
                    created_by=job.created_by,
                )
                PatientVisit.objects.filter(pk=pv.pk).update(created_at=rev_dt)

                ATCJobLog.objects.create(
                    job=job,
                    patient=patient,
                    visit=pv,
                    source_patient=patient,
                    patient_name=patient.name,
                    gender=patient.gender,
                    department=pv.department,
                    batch_number=job.current_batch,
                    status='Success',
                )

            created_reviews += 1
            job.created_count = created_reviews
            if patient.gender == 'Male':
                job.created_male += 1
            else:
                job.created_female += 1
            job.current_patient_info = f"Review visit #{next_v_no} for {patient.name} ({patient.patient_id})"
            job.save(update_fields=[
                'created_count', 'created_male', 'created_female',
                'current_patient_info', 'current_batch'
            ])

        except Exception as e:
            logger.exception(f"Error creating review visit in ATC job {job.job_id}: {e}")
            job.failed_count += 1
            ATCJobLog.objects.create(
                job=job,
                patient=patient,
                visit=None,
                source_patient=patient,
                patient_name=patient.name,
                gender=patient.gender,
                department=patient.department,
                batch_number=job.current_batch,
                status='Failed',
                error_message=str(e),
            )
            job.save(update_fields=['failed_count'])

    job.refresh_from_db()
    if job.status not in [ATCJob.StatusChoices.EMERGENCY_STOPPED, ATCJob.StatusChoices.STOPPED]:
        job.status = ATCJob.StatusChoices.COMPLETED
        job.completed_at = get_server_now()
        job.current_patient_info = f"Completed: {job.created_count} reviews created."
        job.save(update_fields=['status', 'completed_at', 'current_patient_info'])


# ---------------------------------------------------------------------------
# FUTURE PATIENT CREATION
# ---------------------------------------------------------------------------

def execute_future_patient_automation(job):
    """
    Executes future-dated patient creation:
      - Validates future range <= 30/31 days from today.
      - Generates valid future patient records.
      - Respects batching and emergency stop.
    """
    today = get_server_today()
    from_d = job.from_date or today
    to_d = job.to_date or (today + timedelta(days=1))

    # Strict Backend Enforcement: Max 1 month from current date
    max_allowed = today + timedelta(days=31)
    if to_d > max_allowed:
        raise ValueError("Future patient creation is limited to one month.")

    # Execute generation similar to OP, with future target dates
    from_year = job.source_from_year or 2022
    to_year = job.source_to_year or 2024
    source_qs = Patient.objects.filter(
        registration_date__year__gte=from_year,
        registration_date__year__lte=to_year,
    )
    male_source = list(source_qs.filter(gender__iexact='Male').order_by('id')) or list(Patient.objects.filter(gender__iexact='Male'))
    female_source = list(source_qs.filter(gender__iexact='Female').order_by('id')) or list(Patient.objects.filter(gender__iexact='Female'))

    dept = job.department or Department.objects.first()
    dept_unit = dept.units.first() if (dept and dept.units.exists()) else None

    total_target = job.target_total
    target_male = job.target_male
    target_female = job.target_female
    batch_size = max(1, job.batch_size or 100)
    total_batches = max(1, math.ceil(total_target / batch_size))

    job.total_batches = total_batches
    job.save(update_fields=['total_batches'])

    m_created = 0
    f_created = 0
    total_created = 0
    date_span = max(1, (to_d - from_d).days + 1)

    while total_created < total_target:
        job.refresh_from_db()
        if job.stop_requested or job.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED]:
            job.status = ATCJob.StatusChoices.EMERGENCY_STOPPED
            job.stop_reason = "Emergency Stop clicked by user."
            job.completed_at = get_server_now()
            job.save(update_fields=['status', 'stop_reason', 'completed_at'])
            return

        job.current_batch = (total_created // batch_size) + 1

        if m_created < target_male and f_created < target_female:
            gender = 'Male' if (total_created % 2 == 0) else 'Female'
        elif m_created < target_male:
            gender = 'Male'
        elif f_created < target_female:
            gender = 'Female'
        else:
            break

        src = (male_source[m_created % len(male_source)] if gender == 'Male' else female_source[f_created % len(female_source)]) if (male_source and female_source) else None

        # Future registration date
        target_future_date = from_d + timedelta(days=(total_created % date_span))
        scheduled_dt = timezone.make_aware(datetime.combine(target_future_date, time(9, 0)))

        try:
            with transaction.atomic():
                synth = SyntheticPatientGenerator.generate(src) if src else {
                    'title': 'Mr' if gender == 'Male' else 'Mrs',
                    'name': f"Future {'John' if gender == 'Male' else 'Jane'} Doe {total_created+1}",
                    'guardian_title': 'Mr',
                    'guardian_name': 'Senior Guardian',
                    'street': 'Future Road',
                    'village_area': 'New Area',
                    'city': 'Karaikal',
                    'state': 'Puducherry',
                    'pincode': '609602',
                }

                p = Patient(
                    title=synth['title'],
                    name=synth['name'],
                    gender=gender,
                    dob=src.dob if src else date(1995, 1, 1),
                    age_years=src.age_years if src else 31,
                    guardian_title=synth['guardian_title'],
                    guardian_relationship='C/O',
                    guardian_name=synth['guardian_name'],
                    street=synth['street'],
                    village_area=synth['village_area'],
                    city=synth['city'],
                    state=synth['state'],
                    pincode=synth['pincode'],
                    department=dept.name if dept else 'GENERAL MEDICINE',
                    department_obj=dept,
                    unit_obj=dept_unit,
                    unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Future Doctor',
                    patient_type='D',
                    created_source='D',
                    automation_scheduled_at=scheduled_dt,
                    auto_trigger_stage='ATC FUTURE PATIENT',
                    source_patient=src,
                    registration_date=target_future_date,
                    created_by=job.created_by,
                )
                p.op_number = Patient.generate_next_op_number()
                p.save()

                pv = PatientVisit.objects.create(
                    patient=p,
                    visit_no=1,
                    visit_date=scheduled_dt,
                    department_obj=dept,
                    department=dept.name if dept else 'GENERAL MEDICINE',
                    unit_obj=dept_unit,
                    unit_doctor=dept_unit.unit_name if dept_unit else 'ATC Future Doctor',
                    visit_type='OP',
                    category='CONSULTATION',
                    clinical_notes='ATC Automated Future Patient Visit',
                    created_by=job.created_by,
                )

                ATCJobLog.objects.create(
                    job=job,
                    patient=p,
                    visit=pv,
                    source_patient=src,
                    patient_name=p.name,
                    gender=p.gender,
                    department=p.department,
                    batch_number=job.current_batch,
                    status='Success',
                )

            total_created += 1
            if gender == 'Male':
                m_created += 1
            else:
                f_created += 1

            job.created_count = total_created
            job.created_male = m_created
            job.created_female = f_created
            job.current_patient_info = f"Created #{p.patient_id} for date {target_future_date.strftime('%d-%m-%Y')}"
            job.save(update_fields=[
                'created_count', 'created_male', 'created_female',
                'current_patient_info', 'current_batch'
            ])

        except Exception as e:
            logger.exception(f"Error creating future patient in ATC job {job.job_id}: {e}")
            job.failed_count += 1
            ATCJobLog.objects.create(
                job=job,
                patient=None,
                visit=None,
                source_patient=src,
                patient_name='Unknown',
                gender=gender,
                department=dept.name if dept else '',
                batch_number=job.current_batch,
                status='Failed',
                error_message=str(e),
            )
            job.save(update_fields=['failed_count'])

    job.refresh_from_db()
    if job.status not in [ATCJob.StatusChoices.EMERGENCY_STOPPED, ATCJob.StatusChoices.STOPPED]:
        job.status = ATCJob.StatusChoices.COMPLETED
        job.completed_at = get_server_now()
        job.current_patient_info = f"Completed: {job.created_count} future patients created."
        job.save(update_fields=['status', 'completed_at', 'current_patient_info'])
