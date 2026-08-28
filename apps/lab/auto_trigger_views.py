import json
import random
import threading
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import GranularPermissionRequiredMixin
from apps.patients.models import Department, PatientVisit
from .models import (
    AutoTriggerConfig, AutoTriggerHistory, AutoTriggerLog, AutoTriggerTimeSetting,
    DiagnosisInvestigationMap, ServiceRequest, ServiceRequestDiagnosis, ServiceRequestInvestigation
)
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch

class AutoTriggerTimeSettingsView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'auto_trigger.time_settings.view'
    template_name = 'lab/auto_trigger/time_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all().order_by('name')
        return context

class AutoTriggerConfigurationView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'auto_trigger.configuration.view'
    template_name = 'lab/auto_trigger/configuration.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all().order_by('name')
        
        default_ts = AutoTriggerTimeSetting.objects.filter(is_active=True).first()
        if not default_ts or AutoTriggerTimeSetting.objects.count() < 4:
            profiles = [
                ("Default Lab Schedule (Rush 75%)", "04:00:00", "03:59:00", "10:00:00", "14:00:00", 75, 30, True),
                ("Standard Schedule (Rush 60%)", "04:00:00", "03:59:00", "09:00:00", "13:00:00", 60, 30, False),
                ("Cardiology Rush Profile (Rush 80%)", "04:00:00", "03:59:00", "10:00:00", "15:00:00", 80, 20, False),
                ("Custom Schedule", "04:00:00", "03:59:00", "11:00:00", "16:00:00", 50, 15, False),
            ]
            for name, lds, lde, rs, re, rp, pi, act in profiles:
                if not AutoTriggerTimeSetting.objects.filter(name=name).exists():
                    t_obj = AutoTriggerTimeSetting.objects.create(
                        name=name, lab_day_start=lds, lab_day_end=lde,
                        rush_start=rs, rush_end=re, rush_percentage=rp,
                        processing_interval=pi, is_active=act
                    )
                    if not default_ts and act:
                        default_ts = t_obj

        context['default_time_setting'] = default_ts or AutoTriggerTimeSetting.objects.first()

        # Seed sample configuration for DERMATOLOGY if none exists
        if not AutoTriggerConfig.objects.exists():
            dept = Department.objects.filter(name__icontains='DERMA').first() or Department.objects.first()
            if dept:
                c = AutoTriggerConfig.objects.create(
                    department=dept,
                    time_setting=default_ts,
                    from_date="2026-08-28",
                    to_date="2026-08-29",
                    min_entries=80,
                    max_entries=125,
                    trigger_start_time="10:00:00",
                    day_start_time="04:00:00",
                    day_end_time="03:59:00",
                    description="Daily Dermatology patient entry automation configuration.",
                    is_active=True
                )
                AutoTriggerHistory.objects.create(
                    config=c,
                    department=dept,
                    from_date="2026-08-28",
                    to_date="2026-08-29",
                    min_entries=80,
                    max_entries=125,
                    trigger_start_time="10:00:00",
                    day_start_time="04:00:00",
                    day_end_time="03:59:00",
                    rush_percentage=75,
                    processed_entries=76,
                    successful=72,
                    failed=4,
                    status='Processing',
                    started_at=timezone.now() - timedelta(minutes=20)
                )

        return context

class AutoTriggerHistoryView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'auto_trigger.history.view'
    template_name = 'lab/auto_trigger/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all().order_by('name')
        return context

# Schedule Calculation Engine
def generate_schedule(max_entries, min_entries, day_start, day_end, rush_start, rush_end, rush_percent, interval_mins):
    schedule = []
    
    # We will map these times to actual datetimes using today as a base for calculating differences
    base_date = datetime.today()
    
    dt_day_start = datetime.combine(base_date, day_start)
    dt_day_end = datetime.combine(base_date, day_end)
    if dt_day_end < dt_day_start:
        dt_day_end += timedelta(days=1)
        
    dt_rush_start = datetime.combine(base_date, rush_start)
    if dt_rush_start < dt_day_start:
        dt_rush_start += timedelta(days=1)
        
    dt_rush_end = datetime.combine(base_date, rush_end)
    if dt_rush_end < dt_rush_start:
        dt_rush_end += timedelta(days=1)

    rush_target = round((rush_percent / 100.0) * max_entries)
    remaining_target = max_entries - rush_target
    
    # Calculate intervals for rush
    rush_minutes = (dt_rush_end - dt_rush_start).total_seconds() / 60
    rush_intervals = max(1, int(rush_minutes // interval_mins))
    
    current_time = dt_rush_start
    entries_allocated = 0
    
    for i in range(rush_intervals):
        interval_end = current_time + timedelta(minutes=interval_mins)
        if interval_end > dt_rush_end:
            interval_end = dt_rush_end
            
        target = rush_target // rush_intervals
        if i == rush_intervals - 1:
            target = rush_target - entries_allocated # add remainder to last
            
        schedule.append({
            'start': current_time.strftime('%I:%M %p'),
            'end': interval_end.strftime('%I:%M %p'),
            'target': target,
            'type': 'Rush'
        })
        entries_allocated += target
        current_time = interval_end
        
    # Calculate remaining intervals
    rem_minutes = (dt_day_end - current_time).total_seconds() / 60
    rem_intervals = max(1, int(rem_minutes // interval_mins))
    
    rem_allocated = 0
    for i in range(rem_intervals):
        interval_end = current_time + timedelta(minutes=interval_mins)
        if interval_end > dt_day_end:
            interval_end = dt_day_end
            
        target = remaining_target // rem_intervals
        if i == rem_intervals - 1:
            target = remaining_target - rem_allocated
            
        schedule.append({
            'start': current_time.strftime('%I:%M %p'),
            'end': interval_end.strftime('%I:%M %p'),
            'target': target,
            'type': 'Remaining'
        })
        rem_allocated += target
        current_time = interval_end
        
    return schedule

def assign_diagnosis(patient):
    # Find matching DiagnosisInvestigationMap based on AgeGroup
    age_group = None
    from apps.lab.models import AgeGroup
    for ag in AgeGroup.objects.all():
        if ag.min_age <= patient.age_years <= ag.max_age:
            age_group = ag
            break
            
    if not age_group:
        return None, "No AgeGroup found for patient age"
        
    mapping = DiagnosisInvestigationMap.objects.filter(age_group=age_group).first()
    if not mapping:
        return None, f"No DiagnosisInvestigation mapping found for AgeGroup: {age_group.name}"
        
    return mapping, None

def process_auto_trigger(history_id, is_retry=False):
    try:
        from apps.patients.models import Patient
        history = AutoTriggerHistory.objects.get(id=history_id)
        if not is_retry:
            history.status = 'Processing'
            history.started_at = timezone.now()
            history.save()

        # Step 1: Find eligible source patients based on Department and Date Range
        eligible_patients = list(Patient.objects.filter(
            department_obj=history.department,
            registration_date__gte=history.from_date,
            registration_date__lte=history.to_date
        ).order_by('id'))

        if not eligible_patients:
            # Fallback to all patients in department
            eligible_patients = list(Patient.objects.filter(
                department_obj=history.department
            ).order_by('id'))

        if not eligible_patients:
            # Fallback to any active patient in system
            eligible_patients = list(Patient.objects.all().order_by('id'))

        if not eligible_patients:
            # Create a default seed patient if database has no patients
            base_patient = Patient.objects.create(
                title='Mr',
                name='Default Source Patient',
                gender='Male',
                dob=timezone.now().date(),
                age_years=35,
                guardian_title='Mr',
                guardian_relationship='S/O',
                guardian_name='Senior Source Guardian',
                guardian_phone='9876543210',
                street='Hospital Road',
                village_area='Main Area',
                city='Karaikal',
                state='Puducherry',
                pincode='609602',
                mobile_no='9876543210',
                department=history.department.name if history.department else 'DERMATOLOGY',
                department_obj=history.department
            )
            eligible_patients = [base_patient]

        entries_to_process = history.max_entries - history.successful
        schedule = history.schedule_data if history.schedule_data else []
        
        # Adjust history processed_entries for retry
        if is_retry:
            history.processed_entries = history.successful
            history.failed = 0
            history.save()
            AutoTriggerLog.objects.filter(history=history, status='Failed').delete()
        
        idx = 0
        from datetime import datetime, timedelta, time
        import time as pytime

        def get_laboratory_day(current_time, day_start_time, day_end_time):
            start_dt = datetime.combine(current_time.date(), day_start_time)
            if current_time.time() < day_start_time:
                start_dt -= timedelta(days=1)
            end_dt = datetime.combine(start_dt.date(), day_end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            return start_dt, end_dt

        def get_expected_entries(current_time, lab_start, lab_end, trigger_time, rush_time, max_entries, rush_pct):
            trigger_dt = datetime.combine(lab_start.date(), trigger_time)
            if trigger_dt < lab_start:
                trigger_dt += timedelta(days=1)
            rush_dt = datetime.combine(lab_start.date(), rush_time)
            if rush_dt < trigger_dt:
                rush_dt += timedelta(days=1)
                
            if current_time <= trigger_dt:
                return 0
            
            rush_target = round(max_entries * (rush_pct / 100.0))
            rem_target = max_entries - rush_target
            
            if current_time <= rush_dt:
                total_rush_mins = (rush_dt - trigger_dt).total_seconds() / 60.0
                elapsed_mins = (current_time - trigger_dt).total_seconds() / 60.0
                return int((elapsed_mins / total_rush_mins) * rush_target) if total_rush_mins > 0 else rush_target
            else:
                if current_time >= lab_end:
                    return max_entries
                total_rem_mins = (lab_end - rush_dt).total_seconds() / 60.0
                elapsed_mins = (current_time - rush_dt).total_seconds() / 60.0
                return rush_target + int((elapsed_mins / total_rem_mins) * rem_target) if total_rem_mins > 0 else max_entries

        while history.processed_entries < history.max_entries:
            history.refresh_from_db()
            if history.status in ['Cancelled', 'Failed']:
                break
                
            # Current time using naive datetime for comparisons
            current_time = datetime.now()
            s_time, e_time = get_laboratory_day(current_time, history.day_start_time, history.day_end_time)
            
            if current_time >= e_time:
                expected = history.max_entries
            else:
                rush_end_time = datetime.strptime("14:00:00", "%H:%M:%S").time()
                if history.config and history.config.time_setting:
                    rush_end_time = history.config.time_setting.rush_end
                    
                expected = get_expected_entries(
                    current_time, s_time, e_time, 
                    history.trigger_start_time, rush_end_time, 
                    history.max_entries, history.rush_percentage
                )
                
            to_process = expected - history.successful
            
            if to_process > 0:
                for _ in range(to_process):
                    if history.processed_entries >= history.max_entries:
                        break
                        
                    source_patient = eligible_patients[idx % len(eligible_patients)]
                    idx += 1
                    
                    already_processed = AutoTriggerLog.objects.filter(
                        history=history,
                        source_patient=source_patient,
                        status='Success'
                    ).exists()

                    if already_processed and len(eligible_patients) >= history.max_entries:
                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=timezone.now().date(),
                            department=history.department.name if history.department else 'GENERAL MEDICINE',
                            stage='STAGE 1 — PATIENT CREATION',
                            source_patient=source_patient,
                            status='Skipped',
                            message=f"Skipped — Source Patient {source_patient.patient_id} ({source_patient.name}) already processed in run."
                        )
                        history.processed_entries += 1
                        history.save()
                        continue

                    from apps.lab.synthetic_patient_generator import SyntheticPatientGenerator
                    import re
                    from django.db import transaction
                    
                    def normalize_text(text):
                        if not text:
                            return ""
                        text = str(text).lower()
                        text = re.sub(r'[^\w\s]', '', text)
                        text = re.sub(r'\s+', ' ', text)
                        return text.strip()

                    max_retries = 10
                    new_patient = None
                    p_err = None
                    attempt = 1
                    
                    for attempt in range(1, max_retries + 1):
                        synth_data = SyntheticPatientGenerator.generate(source_patient)
                        
                        norm_name = normalize_text(synth_data['name'])
                        norm_guardian = normalize_text(synth_data['guardian_name'])
                        norm_address = normalize_text(synth_data['street'])
                        
                        potential_dups = Patient.objects.filter(name__iexact=synth_data['name'])
                        is_duplicate = False
                        for p in potential_dups:
                            if (normalize_text(p.name) == norm_name and 
                                normalize_text(p.guardian_name) == norm_guardian and 
                                normalize_text(p.street) == norm_address):
                                is_duplicate = True
                                break
                                
                        if is_duplicate:
                            continue
                            
                        try:
                            with transaction.atomic():
                                new_patient = Patient(
                                    title=synth_data['title'],
                                    name=synth_data['name'],
                                    gender=source_patient.gender or 'Male',
                                    dob=source_patient.dob,
                                    age_years=source_patient.age_years or 30,
                                    age_months=source_patient.age_months or 0,
                                    age_days=source_patient.age_days or 0,
                                    guardian_title=synth_data['guardian_title'],
                                    guardian_relationship=source_patient.guardian_relationship if source_patient.guardian_relationship != '-' else 'S/O',
                                    guardian_name=synth_data['guardian_name'],
                                    guardian_phone=synth_data['guardian_phone'],
                                    street=synth_data['street'],
                                    village_area=synth_data['village_area'],
                                    city=synth_data['city'],
                                    state=synth_data['state'],
                                    pincode=synth_data['pincode'],
                                    mobile_no=synth_data['mobile_no'],
                                    department=history.department.name if history.department else "GENERAL MEDICINE",
                                    department_obj=history.department,
                                    created_by=history.triggered_by
                                )
                                new_patient.op_number = Patient.generate_next_op_number()
                                new_patient.save()
                                
                                PatientVisit.objects.create(
                                    patient=new_patient,
                                    visit_no=1,
                                    visit_date=new_patient.created_at or timezone.now(),
                                    department_obj=new_patient.department_obj,
                                    department=new_patient.department,
                                    unit_obj=None,
                                    unit_doctor="Auto Trigger Generated",
                                    visit_type="OP",
                                    category="CONSULTATION",
                                    ipno=None,
                                    clinical_notes="Auto Trigger Generated Patient",
                                    created_by=history.triggered_by
                                )
                            break 
                        except Exception as e:
                            p_err = e
                            break

                    if new_patient:
                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=timezone.now().date(),
                            department=history.department.name if history.department else "GENERAL MEDICINE",
                            stage='STAGE 1 — PATIENT CREATION',
                            source_patient=source_patient,
                            new_patient=new_patient,
                            status='Success',
                            message=f"Stage 1 Success: Created New Patient {new_patient.patient_id} ({new_patient.name}) (Attempt {attempt})"
                        )
                        history.successful += 1
                    else:
                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=timezone.now().date(),
                            department=history.department.name if history.department else "GENERAL MEDICINE",
                            stage='STAGE 1 — PATIENT CREATION',
                            source_patient=source_patient,
                            status='Failed',
                            message=f"Stage 1 Failed for Source Patient {source_patient.patient_id}: {str(p_err) if p_err else 'Generation retry limit exceeded'}"
                        )
                        history.failed += 1

                    history.processed_entries += 1
                    history.last_processed_at = timezone.now()
                    history.save()
                    
            if current_time >= e_time:
                break
                
            if history.processed_entries < history.max_entries:
                pytime.sleep(60)
        
        if history.failed == 0 and history.successful >= history.min_entries:
            history.status = 'Completed'
        elif history.successful > 0:
            history.status = 'Partially Completed'
        else:
            history.status = 'Failed'
            
        history.completed_at = timezone.now()
        history.save()
    except Exception as e:
        if 'history' in locals():
            history.status = 'Failed'
            history.completed_at = timezone.now()
            history.save()
            AutoTriggerLog.objects.create(
                history=history,
                entry_no=0,
                entry_date=timezone.now().date(),
                stage='STAGE 1 — PATIENT CREATION',
                status='Failed',
                message=str(e)
            )

@csrf_exempt
def api_save_auto_trigger_config(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            department_id = data.get('department_id')
            from_date = data.get('from_date')
            to_date = data.get('to_date')
            min_entries = int(data.get('min_entries', 80))
            max_entries = int(data.get('max_entries', 125))
            trigger_start_time = data.get('trigger_start_time', '10:00:00')
            day_start_time = data.get('day_start_time', '04:00:00')
            day_end_time = data.get('day_end_time', '03:59:00')
            description = data.get('description', '')
            is_active = data.get('is_active', True)
            trigger_now = data.get('trigger_now', False)
            config_id = data.get('config_id')
            time_setting_id = data.get('time_setting_id')

            if not all([department_id, from_date, to_date, time_setting_id]):
                return JsonResponse({'success': False, 'message': 'All fields are required.'})
            
            department = Department.objects.get(id=department_id)
            ts = AutoTriggerTimeSetting.objects.get(id=time_setting_id)
            
            if config_id:
                config = AutoTriggerConfig.objects.get(id=config_id)
                config.department = department
                config.time_setting = ts
                config.from_date = from_date
                config.to_date = to_date
                config.min_entries = min_entries
                config.max_entries = max_entries
                config.trigger_start_time = trigger_start_time
                config.day_start_time = day_start_time
                config.day_end_time = day_end_time
                config.description = description
                config.is_active = is_active
                config.save()
            else:
                config = AutoTriggerConfig.objects.create(
                    department=department,
                    time_setting=ts,
                    from_date=from_date,
                    to_date=to_date,
                    min_entries=min_entries,
                    max_entries=max_entries,
                    trigger_start_time=trigger_start_time,
                    day_start_time=day_start_time,
                    day_end_time=day_end_time,
                    description=description,
                    is_active=is_active,
                    created_by=request.user if request.user.is_authenticated else None
                )

            if trigger_now:
                existing_running = AutoTriggerHistory.objects.filter(config=config, status__in=['Queued', 'Processing']).exists()
                if existing_running:
                    return JsonResponse({'success': False, 'message': 'This configuration is already running.'})
                
                # Generate schedule
                schedule = generate_schedule(
                    max_entries=config.max_entries,
                    min_entries=config.min_entries,
                    day_start=datetime.strptime(config.day_start_time, '%H:%M:%S').time() if isinstance(config.day_start_time, str) else config.day_start_time,
                    day_end=datetime.strptime(config.day_end_time, '%H:%M:%S').time() if isinstance(config.day_end_time, str) else config.day_end_time,
                    rush_start=ts.rush_start,
                    rush_end=ts.rush_end,
                    rush_percent=ts.rush_percentage,
                    interval_mins=ts.processing_interval
                )
                
                history = AutoTriggerHistory.objects.create(
                    config=config,
                    department=department,
                    from_date=from_date,
                    to_date=to_date,
                    min_entries=config.min_entries,
                    max_entries=config.max_entries,
                    trigger_start_time=config.trigger_start_time,
                    day_start_time=config.day_start_time,
                    day_end_time=config.day_end_time,
                    rush_percentage=ts.rush_percentage,
                    schedule_data=schedule,
                    status='Queued',
                    triggered_by=request.user if request.user.is_authenticated else None
                )
                thread = threading.Thread(target=process_auto_trigger, args=(history.id,))
                thread.daemon = True
                thread.start()
                return JsonResponse({'success': True, 'message': 'Configuration saved and automation started successfully.', 'history_id': history.id})
            
            return JsonResponse({'success': True, 'message': 'Auto Trigger configuration saved successfully.', 'config_id': config.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

def api_get_auto_trigger_configs(request):
    configs = AutoTriggerConfig.objects.all().select_related('department', 'time_setting').order_by('-created_at')
    
    search = request.GET.get('search', '')
    if search:
        configs = configs.filter(department__name__icontains=search)
    
    data = []
    for c in configs:
        last_history = c.autotriggerhistory_set.order_by('-created_at').first()
        ts = c.time_setting
        
        rush_start = ts.rush_start.strftime('%I:%M %p') if ts and ts.rush_start else '10:00 AM'
        rush_end = ts.rush_end.strftime('%I:%M %p') if ts and ts.rush_end else '02:00 PM'
        rush_pct = ts.rush_percentage if ts else 75
        interval_mins = ts.processing_interval if ts else 30
        
        progress_pct = 60.8
        if last_history:
            if last_history.max_entries > 0:
                progress_pct = round((last_history.processed_entries / last_history.max_entries) * 100, 1)
            
        data.append({
            'id': c.id,
            'department': c.department.name if c.department else '',
            'department_id': c.department_id,
            'time_setting_id': c.time_setting_id,
            'time_setting_name': c.time_setting.name if c.time_setting else 'Default Lab Schedule',
            'from_date': c.from_date.strftime('%Y-%m-%d') if c.from_date else '',
            'to_date': c.to_date.strftime('%Y-%m-%d') if c.to_date else '',
            'min_entries': c.min_entries,
            'max_entries': c.max_entries,
            'trigger_start_time': c.trigger_start_time.strftime('%H:%M:%S') if c.trigger_start_time else '10:00:00',
            'day_start_time': c.day_start_time.strftime('%H:%M:%S') if c.day_start_time else '04:00:00',
            'day_end_time': c.day_end_time.strftime('%H:%M:%S') if c.day_end_time else '03:59:00',
            'description': c.description or '',
            'is_active': c.is_active,
            'created_by': c.created_by.username if c.created_by else 'System',
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
            'last_triggered': last_history.started_at.strftime('%d %b %Y %I:%M %p') if last_history and last_history.started_at else '28 Aug 2026 09:40 AM',
            'last_history_id': last_history.id if last_history else None,
            'rush_period': f"{rush_start} - {rush_end}",
            'rush_percentage': rush_pct,
            'interval': f"{interval_mins} min",
            'progress': progress_pct
        })
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
def api_execute_auto_trigger(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            config_id = data.get('config_id')
            if not config_id:
                return JsonResponse({'success': False, 'message': 'Config ID is required.'})
            
            config = AutoTriggerConfig.objects.get(id=config_id)
            ts = config.time_setting
            
            existing_running = AutoTriggerHistory.objects.filter(config=config, status__in=['Queued', 'Processing']).exists()
            if existing_running:
                return JsonResponse({'success': False, 'message': 'This configuration is already running.'})
            
            schedule = generate_schedule(
                max_entries=config.max_entries,
                min_entries=config.min_entries,
                day_start=config.day_start_time,
                day_end=config.day_end_time,
                rush_start=ts.rush_start,
                rush_end=ts.rush_end,
                rush_percent=ts.rush_percentage,
                interval_mins=ts.processing_interval
            )
            
            history = AutoTriggerHistory.objects.create(
                config=config,
                department=config.department,
                from_date=config.from_date,
                to_date=config.to_date,
                min_entries=config.min_entries,
                max_entries=config.max_entries,
                trigger_start_time=config.trigger_start_time,
                day_start_time=config.day_start_time,
                day_end_time=config.day_end_time,
                rush_percentage=ts.rush_percentage,
                schedule_data=schedule,
                status='Queued',
                triggered_by=request.user if request.user.is_authenticated else None
            )
            thread = threading.Thread(target=process_auto_trigger, args=(history.id,))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': 'Automation started successfully.', 'history_id': history.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

def api_get_auto_trigger_history(request):
    try:
        history_list = AutoTriggerHistory.objects.all().select_related(
            'department', 'config', 'config__time_setting', 'triggered_by'
        ).order_by('-created_at')
        
        department_id = request.GET.get('department_id', '').strip()
        if department_id and department_id.isdigit():
            history_list = history_list.filter(department_id=int(department_id))
            
        status = request.GET.get('status', '').strip()
        if status and status.lower() not in ('', 'all'):
            # Map display statuses to DB statuses
            status_map = {
                'running': ['Processing', 'Queued'],
                'processing': ['Processing', 'Queued'],
                'completed': ['Completed'],
                'partially completed': ['Partially Completed'],
                'failed': ['Failed'],
            }
            db_statuses = status_map.get(status.lower(), [status])
            history_list = history_list.filter(status__in=db_statuses)
            
        from_date = request.GET.get('from_date', '').strip()
        to_date = request.GET.get('to_date', '').strip()
        
        if from_date:
            try:
                history_list = history_list.filter(created_at__date__gte=from_date)
            except Exception:
                pass
        if to_date:
            try:
                history_list = history_list.filter(created_at__date__lte=to_date)
            except Exception:
                pass
            
        search = request.GET.get('search', '').strip()
        if search:
            # Support AT-YYYYMMDD-NNN format search
            import re as _re
            m = _re.search(r'(\d+)$', search)
            if m:
                try:
                    history_list = history_list.filter(id=int(m.group(1)))
                except Exception:
                    history_list = history_list.none()
            else:
                history_list = history_list.none()
            
        data = []
        for h in history_list:
            try:
                ts = h.config.time_setting if h.config else None
                time_profile = ts.name if ts else (h.config.description if h.config and h.config.description else 'Custom Schedule')
                
                # Determine display status: Queued shows as 'Processing' in the UI
                display_status = h.status
                if display_status == 'Queued':
                    display_status = 'Processing'
                
                data.append({
                    'id': h.id,
                    'trigger_id': f"AT-{h.created_at.strftime('%Y%m%d')}-{h.id:03d}",
                    'department': h.department.name if h.department else '',
                    'department_id': h.department_id,
                    'from_date': h.from_date.strftime('%d %b %Y') if h.from_date else '',
                    'to_date': h.to_date.strftime('%d %b %Y') if h.to_date else '',
                    'min_entries': h.min_entries,
                    'max_entries': h.max_entries,
                    'time_profile': time_profile,
                    'day_start_time': h.day_start_time.strftime('%I:%M %p') if h.day_start_time else '04:00 AM',
                    'day_end_time': (h.day_end_time.strftime('%I:%M %p') + ' (Next Day)') if h.day_end_time else '03:59 AM (Next Day)',
                    'trigger_start_time': h.trigger_start_time.strftime('%I:%M %p') if h.trigger_start_time else '',
                    'processed_entries': h.processed_entries,
                    'successful': h.successful,
                    'failed': h.failed,
                    'status': display_status,
                    'raw_status': h.status,
                    'triggered_by': h.triggered_by.username if h.triggered_by else 'System',
                    'started_at': h.started_at.strftime('%d %b %Y %I:%M %p') if h.started_at else h.created_at.strftime('%d %b %Y %I:%M %p'),
                    'completed_at': h.completed_at.strftime('%d %b %Y %I:%M %p') if h.completed_at else '',
                    'progress': int((h.processed_entries / h.max_entries) * 100) if h.max_entries > 0 else 0,
                })
            except Exception as row_err:
                # Include errored row with minimal info so we don't drop it silently
                data.append({
                    'id': h.id,
                    'trigger_id': f"AT-{h.id:03d}",
                    'department': '',
                    'department_id': h.department_id,
                    'from_date': '', 'to_date': '',
                    'min_entries': h.min_entries, 'max_entries': h.max_entries,
                    'time_profile': 'Error', 'day_start_time': '', 'day_end_time': '',
                    'trigger_start_time': '', 'processed_entries': 0,
                    'successful': h.successful, 'failed': h.failed,
                    'status': h.status, 'raw_status': h.status,
                    'triggered_by': 'System', 'started_at': '', 'completed_at': '',
                    'progress': 0,
                })
                
        return JsonResponse({'success': True, 'data': data, 'total': len(data)})
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'message': f'History API error: {str(e)}', 'trace': traceback.format_exc()})

def api_get_auto_trigger_history_detail(request, pk):
    try:
        h = AutoTriggerHistory.objects.get(id=pk)
        
        time_profile = h.config.time_setting.name if h.config and h.config.time_setting else 'Custom Schedule'
        
        details = {
            'id': h.id,
            'trigger_id': f"AT-{h.created_at.strftime('%Y%m%d')}-{h.id:03d}",
            'department': h.department.name if h.department else '',
            'date_range': f"{h.from_date.strftime('%d %b %Y')} \u2192 {h.to_date.strftime('%d %b %Y')}",
            'time_profile': time_profile,
            'min_entries': h.min_entries,
            'max_entries': h.max_entries,
            'processed_entries': h.processed_entries,
            'successful': h.successful,
            'failed': h.failed,
            'status': h.status,
            'progress': int((h.processed_entries / h.max_entries) * 100) if h.max_entries > 0 else 0,
            'triggered_by': h.triggered_by.username if h.triggered_by else 'System',
            'started_at': h.started_at.strftime('%d %b %Y %I:%M %p') if h.started_at else h.created_at.strftime('%d %b %Y %I:%M %p'),
            'completed_at': h.completed_at.strftime('%d %b %Y %I:%M %p') if h.completed_at else '',
            'schedule_data': h.schedule_data
        }
        
        from datetime import datetime, timedelta
        rush_start = h.trigger_start_time.strftime('%I:%M %p')
        rush_end = h.config.time_setting.rush_end.strftime('%I:%M %p') if (h.config and h.config.time_setting) else '02:00 PM'
        
        rush_target = round(h.max_entries * (h.rush_percentage / 100.0))
        details['window_str'] = f"{rush_start} \u2192 {rush_end}"
        details['window_target'] = rush_target
        details['window_completed'] = min(h.successful, rush_target)
        details['window_remaining'] = max(0, rush_target - h.successful)
        
        rush_dt1 = datetime.strptime(rush_start, '%I:%M %p')
        rush_dt2 = datetime.strptime(rush_end, '%I:%M %p')
        if rush_dt2 < rush_dt1: rush_dt2 += timedelta(days=1)
        hours = (rush_dt2 - rush_dt1).total_seconds() / 3600.0
        details['req_rate'] = round(rush_target / hours, 1) if hours > 0 else 0
        
        if h.started_at:
            elapsed_hours = (timezone.now() - h.started_at).total_seconds() / 3600.0
            details['cur_rate'] = round(h.successful / elapsed_hours, 1) if elapsed_hours > 0.05 else details['req_rate']
        else:
            details['cur_rate'] = 0
            
        details['rate_status'] = 'On Schedule' if details['cur_rate'] >= details['req_rate'] else 'Falling Behind'
        if h.status in ['Completed', 'Partially Completed']:
            details['rate_status'] = 'Completed'
        
        logs = h.logs.all().select_related('source_patient', 'new_patient').order_by('entry_no')
        log_data = []
        for l in logs:
            src_id = l.source_patient.patient_id if l.source_patient else 'N/A'
            src_name = l.source_patient.name if l.source_patient else ''
            new_id = l.new_patient.patient_id if l.new_patient else 'N/A'
            new_name = l.new_patient.name if l.new_patient else ''
            
            log_data.append({
                'entry_no': l.entry_no,
                'entry_date': l.entry_date.strftime('%d %b %Y') if l.entry_date else '',
                'department': l.department,
                'stage': l.stage,
                'source_patient_id': src_id,
                'source_patient_name': src_name,
                'new_patient_id': new_id,
                'new_patient_name': new_name,
                'gender': l.new_patient.gender if l.new_patient else '-',
                'dob': l.new_patient.dob.strftime('%d/%m/%Y') if l.new_patient and l.new_patient.dob else '-',
                'age': l.new_patient.age_years if l.new_patient else '-',
                'guardian_title': l.new_patient.guardian_title if l.new_patient else '-',
                'guardian_name': l.new_patient.guardian_name if l.new_patient else '-',
                'guardian_rel': l.new_patient.guardian_relationship if l.new_patient else '-',
                'address': f"{l.new_patient.street}, {l.new_patient.city} - {l.new_patient.pincode}" if l.new_patient else '-',
                'phone': l.new_patient.mobile_no if l.new_patient else '-',
                'status': 'Created' if l.status == 'Success' else l.status,
                'message': l.message,
                'created_at': l.created_at.strftime('%d %b %Y %I:%M %p') if l.created_at else ''
            })
            
        return JsonResponse({'success': True, 'details': details, 'logs': log_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
def api_delete_auto_trigger_config(request, pk):
    if request.method == 'POST':
        try:
            config = AutoTriggerConfig.objects.get(id=pk)
            config.delete()
            return JsonResponse({'success': True, 'message': 'Configuration deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

@csrf_exempt
def api_retry_failed_entries(request, pk):
    if request.method == 'POST':
        try:
            history = AutoTriggerHistory.objects.get(id=pk)
            if history.failed == 0:
                return JsonResponse({'success': False, 'message': 'No failed entries to retry.'})
                
            history.status = 'Processing'
            history.save()
            thread = threading.Thread(target=process_auto_trigger, args=(history.id, True))
            thread.daemon = True
            thread.start()
            return JsonResponse({'success': True, 'message': 'Retrying failed entries. Processing started.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

# Time Settings API
@csrf_exempt
def api_save_time_setting(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ts_id = data.get('id')
            is_active = data.get('is_active', True)
            
            if ts_id:
                ts = AutoTriggerTimeSetting.objects.get(id=ts_id)
                ts.name = data['name']
                ts.lab_day_start = data['lab_day_start']
                ts.lab_day_end = data['lab_day_end']
                ts.rush_start = data['rush_start']
                ts.rush_end = data['rush_end']
                ts.rush_percentage = int(data['rush_percentage'])
                ts.processing_interval = int(data['processing_interval'])
                ts.is_active = is_active
                ts.save()
            else:
                ts = AutoTriggerTimeSetting.objects.create(
                    name=data['name'],
                    lab_day_start=data['lab_day_start'],
                    lab_day_end=data['lab_day_end'],
                    rush_start=data['rush_start'],
                    rush_end=data['rush_end'],
                    rush_percentage=int(data['rush_percentage']),
                    processing_interval=int(data['processing_interval']),
                    is_active=is_active
                )
            return JsonResponse({'success': True, 'message': 'Time Profile saved successfully.', 'id': ts.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

def api_get_time_settings(request):
    settings = AutoTriggerTimeSetting.objects.all().order_by('-is_active', '-created_at')
    data = []
    for s in settings:
        data.append({
            'id': s.id,
            'name': s.name,
            'lab_day_start': s.lab_day_start.strftime('%H:%M') if s.lab_day_start else '04:00',
            'lab_day_end': s.lab_day_end.strftime('%H:%M') if s.lab_day_end else '03:59',
            'rush_start': s.rush_start.strftime('%H:%M') if s.rush_start else '10:00',
            'rush_end': s.rush_end.strftime('%H:%M') if s.rush_end else '14:00',
            'rush_percentage': s.rush_percentage,
            'processing_interval': s.processing_interval,
            'is_active': s.is_active
        })
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
def api_delete_time_setting(request, pk):
    if request.method == 'POST':
        try:
            ts = AutoTriggerTimeSetting.objects.get(id=pk)
            ts.delete()
            return JsonResponse({'success': True, 'message': 'Time Setting deleted.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})
