import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()
from apps.patients.models import Patient
from apps.lab.models import AutoTriggerHistory

h = AutoTriggerHistory.objects.order_by('-id').first()
print(f"History Run ID: {h.run_id}, Status: {h.status}, Success: {h.successful}, Failed: {h.failed}")

pts = Patient.objects.filter(auto_trigger_run=h).order_by('id')
print(f"Generated {pts.count()} patients.")
for p in pts:
    print(f"ID: {p.patient_id} OP: {p.op_number} Type: {p.patient_type} CreatedAt: {p.automation_scheduled_at} Dept: {p.department_obj.name}")

