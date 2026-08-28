import json
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
        context['default_time_setting'] = AutoTriggerTimeSetting.objects.filter(is_active=True).first()
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
        history = AutoTriggerHistory.objects.get(id=history_id)
        if not is_retry:
            history.status = 'Processing'
            history.started_at = timezone.now()
            history.save()

        # Get eligible patients
        eligible_visits = PatientVisit.objects.filter(
            department_obj=history.department,
            visit_date__date__gte=history.from_date,
            visit_date__date__lte=history.to_date
        ).order_by('visit_date')
        
        # Exclude already processed visits (Success ones)
        processed_visit_ids = AutoTriggerLog.objects.filter(
            history=history, status='Success'
        ).values_list('visit_id', flat=True)
        
        eligible_visits = eligible_visits.exclude(id__in=processed_visit_ids)
        
        entries_to_process = history.max_entries - history.successful
        visits_to_process = list(eligible_visits[:entries_to_process])
        
        schedule = history.schedule_data if history.schedule_data else []
        
        # Adjust history processed_entries for retry
        if is_retry:
            history.processed_entries = history.successful
            history.failed = 0
            history.save()
            
            # Clear previous failed logs for this history
            AutoTriggerLog.objects.filter(history=history, status='Failed').delete()
        
        # Let's simulate processing interval by interval for UI updates
        idx = 0
        for block in schedule:
            target = block['target']
            
            for _ in range(target):
                if idx >= len(visits_to_process):
                    break
                    
                visit = visits_to_process[idx]
                patient = visit.patient
                
                # Check for duplicate ServiceRequest on this day
                if ServiceRequest.objects.filter(patient=patient, request_date=visit.visit_date.date()).exists():
                    AutoTriggerLog.objects.create(
                        history=history,
                        entry_no=history.processed_entries + 1,
                        entry_date=timezone.now().date(),
                        department=history.department.name,
                        visit=visit,
                        status='Failed',
                        message='ServiceRequest already exists for this date.'
                    )
                    history.failed += 1
                else:
                    mapping, err = assign_diagnosis(patient)
                    if err:
                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=timezone.now().date(),
                            department=history.department.name,
                            visit=visit,
                            status='Failed',
                            message=err
                        )
                        history.failed += 1
                    else:
                        # Process Success
                        sr = ServiceRequest.objects.create(
                            patient=patient,
                            visit_no=visit.visit_no,
                            department=visit.department_obj,
                            visit_type=visit.visit_type,
                            request_date=visit.visit_date.date(),
                            status='Saved',
                            created_by=history.triggered_by
                        )
                        ServiceRequestDiagnosis.objects.create(
                            service_request=sr,
                            diagnosis=mapping.diagnosis
                        )
                        ServiceRequestInvestigation.objects.create(
                            service_request=sr,
                            investigation=mapping.investigation,
                            source='AUTO_SUGGESTED',
                            status='PENDING'
                        )
                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=timezone.now().date(),
                            department=history.department.name,
                            visit=visit,
                            status='Success',
                            message=f'Assigned Diagnosis: {mapping.diagnosis.name}, Inv: {mapping.investigation.name}'
                        )
                        history.successful += 1
                
                history.processed_entries += 1
                history.last_processed_at = timezone.now()
                history.save()
                idx += 1
                
                time.sleep(0.2) # Small delay to allow UI polling to show progress bar moving
        
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
        data.append({
            'id': c.id,
            'department': c.department.name if c.department else '',
            'department_id': c.department_id,
            'time_setting_id': c.time_setting_id,
            'time_setting_name': c.time_setting.name if c.time_setting else 'N/A',
            'from_date': c.from_date.strftime('%Y-%m-%d') if c.from_date else '',
            'to_date': c.to_date.strftime('%Y-%m-%d') if c.to_date else '',
            'min_entries': c.min_entries,
            'max_entries': c.max_entries,
            'trigger_start_time': c.trigger_start_time.strftime('%H:%M:%S') if c.trigger_start_time else '10:00:00',
            'day_start_time': c.day_start_time.strftime('%H:%M:%S') if c.day_start_time else '04:00:00',
            'day_end_time': c.day_end_time.strftime('%H:%M:%S') if c.day_end_time else '03:59:00',
            'is_active': c.is_active,
            'created_by': c.created_by.username if c.created_by else 'System',
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
            'last_triggered': last_history.started_at.strftime('%Y-%m-%d %H:%M') if last_history and last_history.started_at else 'Never'
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
    history_list = AutoTriggerHistory.objects.all().select_related('department').order_by('-created_at')
    
    department_id = request.GET.get('department_id', '')
    if department_id:
        history_list = history_list.filter(department_id=department_id)
        
    status = request.GET.get('status', '')
    if status:
        history_list = history_list.filter(status=status)
        
    data = []
    for h in history_list:
        data.append({
            'id': h.id,
            'trigger_id': f"TRG-{h.id:04d}",
            'department': h.department.name if h.department else '',
            'from_date': h.from_date.strftime('%Y-%m-%d') if h.from_date else '',
            'to_date': h.to_date.strftime('%Y-%m-%d') if h.to_date else '',
            'min_entries': h.min_entries,
            'max_entries': h.max_entries,
            'day_start_time': h.day_start_time.strftime('%H:%M:%S') if h.day_start_time else '',
            'day_end_time': h.day_end_time.strftime('%H:%M:%S') if h.day_end_time else '',
            'trigger_start_time': h.trigger_start_time.strftime('%H:%M:%S') if h.trigger_start_time else '',
            'processed_entries': h.processed_entries,
            'successful': h.successful,
            'failed': h.failed,
            'status': h.status,
            'triggered_by': h.triggered_by.username if h.triggered_by else 'System',
            'started_at': h.started_at.strftime('%Y-%m-%d %I:%M %p') if h.started_at else '',
            'completed_at': h.completed_at.strftime('%Y-%m-%d %I:%M %p') if h.completed_at else ''
        })
    return JsonResponse({'success': True, 'data': data})

def api_get_auto_trigger_history_detail(request, pk):
    try:
        h = AutoTriggerHistory.objects.get(id=pk)
        details = {
            'id': h.id,
            'trigger_id': f"TRG-{h.id:04d}",
            'department': h.department.name if h.department else '',
            'date_range': f"{h.from_date.strftime('%Y-%m-%d')} to {h.to_date.strftime('%Y-%m-%d')}",
            'min_entries': h.min_entries,
            'max_entries': h.max_entries,
            'processed_entries': h.processed_entries,
            'successful': h.successful,
            'failed': h.failed,
            'status': h.status,
            'triggered_by': h.triggered_by.username if h.triggered_by else 'System',
            'started_at': h.started_at.strftime('%Y-%m-%d %I:%M %p') if h.started_at else '',
            'completed_at': h.completed_at.strftime('%Y-%m-%d %I:%M %p') if h.completed_at else '',
            'schedule_data': h.schedule_data
        }
        
        logs = h.logs.all().order_by('entry_no')
        log_data = []
        for l in logs:
            log_data.append({
                'entry_no': l.entry_no,
                'entry_date': l.entry_date.strftime('%Y-%m-%d') if l.entry_date else '',
                'department': l.department,
                'status': l.status,
                'message': l.message,
                'patient': l.visit.patient.name if l.visit else 'N/A'
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
            is_active = data.get('is_active', False)
            
            if is_active:
                AutoTriggerTimeSetting.objects.all().update(is_active=False)
                
            if ts_id:
                ts = AutoTriggerTimeSetting.objects.get(id=ts_id)
                ts.name = data['name']
                ts.lab_day_start = data['lab_day_start']
                ts.lab_day_end = data['lab_day_end']
                ts.rush_start = data['rush_start']
                ts.rush_end = data['rush_end']
                ts.rush_percentage = data['rush_percentage']
                ts.processing_interval = data['processing_interval']
                ts.is_active = is_active
                ts.save()
            else:
                ts = AutoTriggerTimeSetting.objects.create(
                    name=data['name'],
                    lab_day_start=data['lab_day_start'],
                    lab_day_end=data['lab_day_end'],
                    rush_start=data['rush_start'],
                    rush_end=data['rush_end'],
                    rush_percentage=data['rush_percentage'],
                    processing_interval=data['processing_interval'],
                    is_active=is_active
                )
            return JsonResponse({'success': True, 'message': 'Time Setting saved successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid method.'})

def api_get_time_settings(request):
    settings = AutoTriggerTimeSetting.objects.all().order_by('-created_at')
    data = []
    for s in settings:
        data.append({
            'id': s.id,
            'name': s.name,
            'lab_day_start': s.lab_day_start.strftime('%H:%M'),
            'lab_day_end': s.lab_day_end.strftime('%H:%M'),
            'rush_start': s.rush_start.strftime('%H:%M'),
            'rush_end': s.rush_end.strftime('%H:%M'),
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
