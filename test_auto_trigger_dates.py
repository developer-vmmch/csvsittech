import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import AutoTriggerConfig, AutoTriggerHistory, AutoTriggerTimeSetting
from apps.patients.models import Patient, Department, PatientVisit
from apps.lab.auto_trigger_views import process_auto_trigger
from django.utils import timezone
from datetime import timedelta

dept = Department.objects.get(name="DERMATOLOGY")
ts = AutoTriggerTimeSetting.objects.first()

# Create source patients on a specific old date
source_date = (timezone.now() - timedelta(days=10)).date()
# Find a valid numeric patient ID for our mock
last_p = Patient.objects.exclude(patient_id__contains='SRC').order_by('-id').first()
next_id = str(int(last_p.patient_id) + 1) if last_p and last_p.patient_id.isdigit() else "9999999999"

p1 = Patient.objects.create(
    title='Mr', name='Source Patient One', gender='Male', dob=source_date,
    registration_date=source_date, department_obj=dept, department=dept.name,
    patient_id=next_id, op_number='OP-001', mobile_no='9999999999',
    street='Old Address 1'
)

config = AutoTriggerConfig.objects.create(
    department=dept,
    time_setting=ts,
    from_date=source_date,
    to_date=source_date,
    min_entries=2,
    max_entries=2,
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
    min_entries=2,
    max_entries=2,
    trigger_start_time="09:00:00",
    day_start_time="09:00:00",
    day_end_time="17:00:00",
    status='Queued',
    current_stage='STAGE 1 - PATIENT CREATION'
)

process_auto_trigger(history.id)

history.refresh_from_db()
print(f"Run ID: {history.run_id}, Status: {history.status}, Success: {history.successful}")
pts = Patient.objects.filter(auto_trigger_run=history).order_by('id')
print(f"Generated {pts.count()} patients.")
for p in pts:
    print(f"NEW ID: {p.patient_id} RegDate: {p.registration_date} Phone: '{p.mobile_no}'")
    for visit in p.visits.all():
        print(f"  VISIT: {visit.visit_date} Dept: {visit.department} Diag: {visit.clinical_notes}")
    
p1.refresh_from_db()
print(f"SOURCE ID: {p1.patient_id} RegDate: {p1.registration_date} Phone: '{p1.mobile_no}'")

for l in history.logs.all():
    print("LOG:", l.message)
