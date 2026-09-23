from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from apps.lab.models import ServiceRequestInvestigation, LabDepartment, PatientInvestigationResult, Investigation

@login_required
def lab_workload_dashboard(request):
    """Shows actual transactional workload split by Lab Sub Department"""
    departments = LabDepartment.objects.filter(is_active=True).order_by('name')
    qs = ServiceRequestInvestigation.objects.all()
    report_data = []
    
    for dept in departments:
        dept_qs = qs.filter(investigation__department=dept)
        pending = dept_qs.filter(status='PENDING').count()
        in_progress = dept_qs.filter(status='RECEIVED').count()
        completed = dept_qs.filter(status='COMPLETED').count()
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

@login_required
def report_dashboard(request):
    # A generic dashboard summarizing lab reports
    return render(request, 'lab/reports/report_dashboard.html', {})

@login_required
def report_daily(request):
    return render(request, 'lab/reports/report_daily.html', {})

@login_required
def report_monthly(request):
    return render(request, 'lab/reports/report_monthly.html', {})

@login_required
def report_sub_department(request):
    return render(request, 'lab/reports/report_sub_department.html', {})

@login_required
def report_investigation(request):
    return render(request, 'lab/reports/report_investigation.html', {})

@login_required
def report_hospital_department(request):
    return render(request, 'lab/reports/report_hospital_department.html', {})

@login_required
def report_benchmark(request):
    return render(request, 'lab/reports/report_benchmark.html', {})

@login_required
def report_abnormal(request):
    return render(request, 'lab/reports/report_abnormal.html', {})

