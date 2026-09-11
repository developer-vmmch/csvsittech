from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from apps.lab.models import ServiceRequestInvestigation, LabDepartment

@login_required
def lab_workload_dashboard(request):
    """
    Shows actual transactional workload split by Lab Sub Department
    Pending / In Progress / Completed
    """
    departments = LabDepartment.objects.filter(is_active=True).order_by('name')
    
    # Base queryset for actual transactions
    qs = ServiceRequestInvestigation.objects.all()
    
    report_data = []
    
    for dept in departments:
        # We assume `investigation__department` points to LabDepartment
        dept_qs = qs.filter(investigation__department=dept)
        
        pending = dept_qs.filter(status='Pending').count()
        in_progress = dept_qs.filter(status='In Progress').count()
        completed = dept_qs.filter(status='Completed').count()
        total = pending + in_progress + completed
        
        if total > 0:
            report_data.append({
                'department': dept.name,
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'total': total
            })
            
    context = {
        'report_data': report_data,
        'overall_total': sum(item['total'] for item in report_data)
    }
    return render(request, 'lab/reports/workload_dashboard.html', context)
