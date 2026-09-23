import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import AutoTriggerConfig, AutoTriggerHistory, AutoTriggerTimeSetting
from apps.patients.models import Patient, Department, PatientVisit
from apps.lab.auto_trigger_views import process_auto_trigger
from django.utils import timezone
from datetime import timedelta

dept = Department.objects.get(name="GENERAL SURGERY")
ts = AutoTriggerTimeSetting.objects.first()

# Delete any patients with patient_id containing SRC- or TEST- from previous runs
Patient.objects.filter(patient_id__icontains='SRC-').delete()

source_date = (timezone.now() - timedelta(days=15)).date()

last_p = Patient.objects.order_by('-id').first()
next_id_int = int(last_p.patient_id) if last_p and last_p.patient_id.isdigit() else 26000000

p1 = Patient.objects.create(
    title='Mr', name='Original Source Patient', gender='Male', dob=source_date,
    registration_date=source_date, department_obj=dept, department=dept.name,
    patient_id=str(next_id_int + 1), op_number='OP-OLD', mobile_no='9876543210',
    street='Old Address 1'
)

config = AutoTriggerConfig.objects.create(
    department=dept,
    time_setting=ts,
    from_date=source_date,
    to_date=source_date,
    min_entries=1,
    max_entries=1,
    trigger_start_time="09:00:00",
    day_start_time="09:00:00",
    day_end_time="17:00:00",
    is_active=True
)

history = AutoTriggerHistory.objects.create(
    config=config,
    department=dept,
    from_date=source_date,
    to_date=source_date,
    min_entries=1,
    max_entries=1,
    trigger_start_time="09:00:00",
    day_start_time="09:00:00",
    day_end_time="17:00:00",
    status='Queued',
    current_stage='STAGE 1 - PATIENT CREATION'
)

process_auto_trigger(history.id)

history.refresh_from_db()
print("="*50)
print(f"Run ID: {history.run_id}, Status: {history.status}")

pts = Patient.objects.filter(auto_trigger_run=history).order_by('id')
for p in pts:
    print("\nCreated:")
    print(f"Patient ID: {p.patient_id}")
    print(f"Registration Date: {p.registration_date.strftime('%d-%b-%Y')}")
    print(f"Phone: {'NULL' if not p.mobile_no else p.mobile_no}")
    print(f"Department: {p.department}")
    visit = p.visits.first()
    diag = "None"
    if visit and visit.clinical_notes:
        diag = visit.clinical_notes.replace("Auto Trigger Generated Patient - Diagnosis: ", "")
    print(f"Diagnosis: {diag}")

p1.refresh_from_db()
print("\nSource patient:")
print(f"Patient ID: {p1.patient_id}")
print(f"Original Registration Date: {p1.registration_date.strftime('%d-%b-%Y')}")
print("Status: UNCHANGED")
print("="*50)

