import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()
from apps.lab.auto_trigger_views import process_auto_trigger
from apps.lab.models import AutoTriggerHistory

import traceback
import sys

def patch_exception():
    original = AutoTriggerHistory.objects.get
    pass

history = AutoTriggerHistory.objects.order_by('-id').first()
# Let's run it directly here to see exactly where it fails
from apps.patients.models import Patient, PatientVisit
from django.db import transaction
from django.utils import timezone
import datetime

# Attempt to do exactly what the code does
scheduled_dt = timezone.now()
try:
    with transaction.atomic():
        new_patient = Patient(
            title='Mr',
            name='Test',
            department=history.department.name if history.department else "GENERAL",
            department_obj=history.department,
            guardian_relationship='C/O'
        )
        new_patient.op_number = Patient.generate_next_op_number()
        new_patient.save()
        print("Patient Saved")
        
        pv = PatientVisit.objects.create(
            patient=new_patient,
            visit_no=1,
            visit_date=scheduled_dt,
            department_obj=new_patient.department_obj,
            department=new_patient.department,
            unit_doctor="Test",
            visit_type="OP"
        )
        print("Visit Saved")
except Exception as e:
    traceback.print_exc()
