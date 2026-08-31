import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.patients.models import Patient, Department
from apps.lab.models import AutoTriggerConfig, AutoTriggerHistory, AutoTriggerTimeSetting
from django.utils import timezone
from datetime import timedelta
import random

# Get a department and time setting
dept = Department.objects.first()
ts = AutoTriggerTimeSetting.objects.first()

# Determine dates
from_date = (timezone.now() - timedelta(days=5)).date()
to_date = (timezone.now() - timedelta(days=2)).date()

# Make sure we have some source patients for those dates
Patient.objects.create(
    name="Start Patient Test", department_obj=dept, registration_date=from_date,
    title='Mr', gender='Male', guardian_name='Start Guardian', guardian_title='Mr', guardian_relationship='S/O'
)
Patient.objects.create(
    name="End Patient Test", department_obj=dept, registration_date=to_date,
    street='End Address Street', city='End City', pincode='999999'
)

# Create config
config = AutoTriggerConfig.objects.create(
    department=dept,
    time_setting=ts,
    from_date=from_date,
    to_date=to_date,
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
    from_date=from_date,
    to_date=to_date,
    min_entries=2,
    max_entries=2,
    trigger_start_time="09:00:00",
    day_start_time="09:00:00",
    day_end_time="17:00:00",
    status='Processing',
    current_stage='STAGE 1 - PATIENT CREATION'
)

from apps.lab.auto_trigger_views import process_auto_trigger
process_auto_trigger(history.id)

history.refresh_from_db()
print(f"Status: {history.status}, Success: {history.successful}, Failed: {history.failed}")

pts = Patient.objects.filter(auto_trigger_run=history).order_by('id')
print(f"Generated {pts.count()} patients.")

for p in pts:
    print(f"Patient Name: {p.name}")
    print(f"First Name Source (Start): {p.title} {p.gender}")
    print(f"Address Source (End): {p.street} {p.city}")
    print(f"Guardian: {p.guardian_name} ({p.guardian_relationship})")
    print(f"Phone: '{p.mobile_no}'")
    print(f"Reg Date: {p.registration_date}")
    print(f"Created At: {p.created_at}")

# Also test PatientSearchView
from apps.patients.views import PatientSearchView
from django.test import RequestFactory
req = RequestFactory().get(f'/patients/search/?from_date={timezone.now().date()}')
view = PatientSearchView()
view.request = req
qs = view.get_queryset()
print(f"Found in PatientSearchView for today: {qs.filter(auto_trigger_run=history).exists()}")

