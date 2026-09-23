import json

code = """
import json
import datetime
from django.utils import timezone
from apps.lab.models import MonthlyTriggerPlan, MonthlyTriggerDailyTarget

def api_get_monthly_trigger(request):
    dept_id = request.GET.get('department_id')
    month = request.GET.get('month')
    year = request.GET.get('year')
    if not all([dept_id, month, year]):
        return JsonResponse({'success': False, 'message': 'Missing parameters'})
    
    plan = MonthlyTriggerPlan.objects.filter(department_id=dept_id, month=month, year=year).first()
    if not plan:
        return JsonResponse({'success': True, 'exists': False})
        
    targets = MonthlyTriggerDailyTarget.objects.filter(plan=plan).order_by('target_date')
    daily_targets = []
    for t in targets:
        daily_targets.append({
            'date': t.target_date.strftime('%Y-%m-%d'),
            'min': t.min_entries,
            'max': t.max_entries,
            'status': t.status
        })
        
    data = {
        'source_from_date': plan.source_from_date.strftime('%Y-%m-%d'),
        'source_to_date': plan.source_to_date.strftime('%Y-%m-%d'),
        'trigger_start_time': plan.trigger_start_time.strftime('%H:%M'),
        'trigger_stop_time': plan.trigger_stop_time.strftime('%H:%M'),
        'interval_mins': plan.interval_mins,
        'status': plan.status,
        'is_saved': plan.is_saved,
        'daily_targets': daily_targets
    }
    return JsonResponse({'success': True, 'exists': True, 'data': data})

def api_save_monthly_trigger(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    try:
        data = json.loads(request.body)
        dept_id = data.get('department_id')
        month = data.get('month')
        year = data.get('year')
        
        plan, created = MonthlyTriggerPlan.objects.update_or_create(
            department_id=dept_id, month=month, year=year,
            defaults={
                'source_from_date': data.get('source_from_date'),
                'source_to_date': data.get('source_to_date'),
                'trigger_start_time': data.get('trigger_start_time'),
                'trigger_stop_time': data.get('trigger_stop_time'),
                'interval_mins': data.get('interval_mins'),
                'status': data.get('status', 'Active'),
                'is_saved': True,
                'created_by': request.user if request.user.is_authenticated else None
            }
        )
        
        daily_targets = data.get('daily_targets', [])
        for target in daily_targets:
            MonthlyTriggerDailyTarget.objects.update_or_create(
                plan=plan,
                target_date=target.get('date'),
                defaults={
                    'min_entries': target.get('min'),
                    'max_entries': target.get('max'),
                    'status': target.get('status', 'Active')
                }
            )
            
        return JsonResponse({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)})

def api_stop_monthly_automation(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Developer')):
        return JsonResponse({'success': False, 'message': 'Permission denied. Developer only.'})
    try:
        data = json.loads(request.body)
        dept_id = data.get('department_id')
        month = data.get('month')
        year = data.get('year')
        plan = MonthlyTriggerPlan.objects.get(department_id=dept_id, month=month, year=year)
        plan.status = 'Stopped'
        plan.save()
        MonthlyTriggerDailyTarget.objects.filter(plan=plan, target_date__gte=datetime.date.today()).update(status='Stopped')
        return JsonResponse({'success': True, 'message': 'Monthly automation stopped successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def api_stop_daily_target(request):
    if request.method != 'POST': return JsonResponse({'success': False})
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'Developer')):
        return JsonResponse({'success': False, 'message': 'Developer only.'})
    try:
        data = json.loads(request.body)
        dept_id = data.get('department_id')
        month = data.get('month')
        year = data.get('year')
        target_date = data.get('target_date')
        plan = MonthlyTriggerPlan.objects.get(department_id=dept_id, month=month, year=year)
        target = MonthlyTriggerDailyTarget.objects.get(plan=plan, target_date=target_date)
        target.status = 'Stopped'
        target.stopped_by = request.user
        target.stopped_at = timezone.now()
        target.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
"""

with open('apps/lab/auto_trigger_views.py', 'a') as f:
    f.write(code)
