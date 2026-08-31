import json

code = """
from apps.lab.models import MonthlyTriggerExecutionLog
from django.db.models import Sum
from datetime import datetime

def api_get_monthly_history(request):
    dept_id = request.GET.get('department_id')
    plan_id = request.GET.get('plan_id')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    status = request.GET.get('status')
    
    targets = MonthlyTriggerDailyTarget.objects.all().select_related('plan', 'plan__department')
    logs = MonthlyTriggerExecutionLog.objects.all().select_related('plan', 'plan__department', 'stopped_by')
    
    if dept_id:
        targets = targets.filter(plan__department_id=dept_id)
        logs = logs.filter(plan__department_id=dept_id)
        
    if plan_id:
        targets = targets.filter(plan_id=plan_id)
        logs = logs.filter(plan_id=plan_id)
        
    if from_date:
        targets = targets.filter(target_date__gte=from_date)
        logs = logs.filter(target_date__gte=from_date)
        
    if to_date:
        targets = targets.filter(target_date__lte=to_date)
        logs = logs.filter(target_date__lte=to_date)
        
    if status and status != 'All':
        targets = targets.filter(status=status)
        logs = logs.filter(status=status)
        
    targets = targets.order_by('-target_date')
    logs = logs.order_by('-created_at')[:50] # Last 50 logs
    
    daily_targets_data = []
    for t in targets:
        progress = 0
        if t.max_entries > 0:
            progress = (t.created_count / t.max_entries) * 100
            
        rem_min = max(0, t.min_entries - t.created_count)
        rem_max = max(0, t.max_entries - t.created_count)
        
        daily_targets_data.append({
            'id': t.id,
            'date': t.target_date.strftime('%d-%b-%Y'),
            'day': t.target_date.strftime('%a'),
            'department': t.plan.department.name,
            'min': t.min_entries,
            'max': t.max_entries,
            'created': t.created_count,
            'duplicates': t.duplicates_count,
            'failed': t.failed_count,
            'remaining_min': rem_min,
            'remaining_max': rem_max,
            'progress': round(progress, 1),
            'status': t.status
        })
        
    logs_data = []
    for l in logs:
        logs_data.append({
            'datetime': timezone.localtime(l.created_at).strftime('%d-%b-%Y %I:%M %p'),
            'plan': f"{l.plan.department.name} {l.plan.month}/{l.plan.year}",
            'department': l.plan.department.name,
            'automation_date': l.target_date.strftime('%d-%b-%Y') if l.target_date else '—',
            'action': l.action,
            'status': l.status,
            'created': l.created_count if l.created_count else '—',
            'duplicates': l.duplicates_count if l.duplicates_count else '—',
            'failed': l.failed_count if l.failed_count else '—',
            'stopped_by': l.stopped_by.username if l.stopped_by else 'System',
            'reason': l.reason or '—'
        })
        
    # Plan Summary (only if 1 plan is filtered, or aggregate)
    summary = None
    if plan_id:
        plan = MonthlyTriggerPlan.objects.filter(id=plan_id).first()
        if plan:
            aggr = MonthlyTriggerDailyTarget.objects.filter(plan=plan).aggregate(
                total_created=Sum('created_count'),
                total_duplicates=Sum('duplicates_count'),
                total_failed=Sum('failed_count')
            )
            summary = {
                'department': plan.department.name,
                'source_from': plan.source_from_date.strftime('%d-%b-%Y'),
                'source_to': plan.source_to_date.strftime('%d-%b-%Y'),
                'start_date': f"01-{plan.month:02d}-{plan.year}",
                'end_date': f"28-{plan.month:02d}-{plan.year}", # rough estimate
                'start_time': plan.trigger_start_time.strftime('%I:%M %p'),
                'stop_time': plan.trigger_stop_time.strftime('%I:%M %p'),
                'interval': f"{plan.interval_mins} mins",
                'status': plan.status,
                'total_days': MonthlyTriggerDailyTarget.objects.filter(plan=plan).count(),
                'total_created': aggr['total_created'] or 0,
                'total_duplicates': aggr['total_duplicates'] or 0,
                'total_failed': aggr['total_failed'] or 0
            }
            
    return JsonResponse({
        'success': True, 
        'daily_targets': daily_targets_data,
        'logs': logs_data,
        'summary': summary
    })
"""
with open('apps/lab/auto_trigger_views.py', 'a') as f:
    f.write(code)
