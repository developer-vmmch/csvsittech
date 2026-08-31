import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.patients.models import Patient, PatientVisit
from django.utils import timezone
import traceback

p = Patient.objects.last()
print("Patient:", p.id)

try:
    pv = PatientVisit.objects.create(
        patient=p,
        visit_no=1,
        visit_date=timezone.now(),
        department_obj=p.department_obj,
        department=p.department,
        unit_obj=None,
        unit_doctor="Auto Trigger Generated",
        visit_type="OP",
        category="CONSULTATION",
        ipno=None,
        clinical_notes="Auto Trigger Generated Patient",
        created_by=None
    )
    print("Created PV:", pv.id)
except Exception as e:
    traceback.print_exc()

