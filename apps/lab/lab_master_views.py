import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Count, Q
from apps.lab.models import LabWorkloadMapping, UnmappedLabInvestigation, LabDepartment, Investigation
from apps.patients.models import Department as HospitalDepartment

@login_required
def lab_master_dashboard(request):
    """
    Shows the validation dashboard for the Lab Master Mapping
    """
    total_mapped = LabWorkloadMapping.objects.count()
    unmapped_records = UnmappedLabInvestigation.objects.all()
    unmapped_count = unmapped_records.filter(resolved=False).count()
    
    # Grouped stats for hospital departments
    hosp_dept_filter = request.GET.get('hospital_department')
    
    if hosp_dept_filter:
        unmapped_records = unmapped_records.filter(hospital_department_name__icontains=hosp_dept_filter)
        mapped_qs = LabWorkloadMapping.objects.filter(hospital_department__name__icontains=hosp_dept_filter)
    else:
        mapped_qs = LabWorkloadMapping.objects.all()
        
    mapped_count = mapped_qs.count()

    context = {
        'total_mapped': total_mapped,
        'unmapped_count': unmapped_count,
        'unmapped_records': unmapped_records[:50],  # Show top 50 unmapped for performance
        'filtered_mapped': mapped_count,
        'hosp_dept_filter': hosp_dept_filter
    }
    return render(request, 'lab/master/lab_master_dashboard.html', context)

@login_required
def export_lab_workload_csv(request):
    """
    Export current mappings to CSV
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lab_workload_mappings.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Hospital Department', 'Lab Sub Department', 'Investigation', 'Monthly', 'Weekly', 'Daily'])
    
    mappings = LabWorkloadMapping.objects.select_related('hospital_department', 'lab_sub_department', 'investigation').all()
    for m in mappings:
        writer.writerow([
            m.hospital_department.name,
            m.lab_sub_department.name,
            m.investigation.name,
            m.monthly_benchmark,
            m.weekly_benchmark,
            m.daily_benchmark
        ])
        
    return response

@login_required
def import_lab_workload_csv(request):
    """
    Import mappings from CSV idempotently
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('lab:lab_master_dashboard')
            
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        mapped = 0
        unmapped = 0
        
        for row in reader:
            hosp_name = row.get('Hospital Department')
            lab_name = row.get('Lab Sub Department')
            inv_name = row.get('Investigation')
            
            if not all([hosp_name, lab_name, inv_name]):
                continue
                
            hosp, _ = HospitalDepartment.objects.get_or_create(name=hosp_name, defaults={'is_active': True})
            
            try:
                lab = LabDepartment.objects.get(name__iexact=lab_name)
            except LabDepartment.DoesNotExist:
                UnmappedLabInvestigation.objects.create(
                    hospital_department_name=hosp_name,
                    source_category=lab_name,
                    investigation_name=inv_name,
                    reason=f"Lab Sub Department '{lab_name}' not found."
                )
                unmapped += 1
                continue
                
            inv = Investigation.objects.filter(name__iexact=inv_name).first()
            if not inv:
                UnmappedLabInvestigation.objects.create(
                    hospital_department_name=hosp_name,
                    source_category=lab_name,
                    investigation_name=inv_name,
                    reason="Investigation not found in Master."
                )
                unmapped += 1
                continue
                
            if inv.department != lab:
                inv.department = lab
                inv.save()
                
            # Create mapping idempotently
            LabWorkloadMapping.objects.update_or_create(
                hospital_department=hosp,
                lab_sub_department=lab,
                investigation=inv,
                defaults={
                    'monthly_benchmark': row.get('Monthly') or 0,
                    'weekly_benchmark': row.get('Weekly') or 0,
                    'daily_benchmark': row.get('Daily') or 0,
                }
            )
            mapped += 1
            
        messages.success(request, f"Imported successfully. Mapped: {mapped}, Exceptions logged: {unmapped}.")
        return redirect('lab:lab_master_dashboard')
        
    return render(request, 'lab/master/lab_workload_import.html')
