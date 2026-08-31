import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import AutoTriggerConfig, AutoTriggerHistory, AutoTriggerTimeSetting
from apps.patients.models import Patient, Department
from django.utils import timezone
from datetime import timedelta

dept = Department.objects.get(name="DERMATOLOGY")
ts = AutoTriggerTimeSetting.objects.first()

from_date = (timezone.now() - timedelta(days=5)).date()
to_date = (timezone.now() - timedelta(days=2)).date()

config = AutoTriggerConfig.objects.create(
    department=dept,
    time_setting=ts,
    from_date=from_date,
    to_date=to_date,
    min_entries=5,
    max_entries=5,
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
    min_entries=5,
    max_entries=5,
    trigger_start_time="09:00:00",
    day_start_time="09:00:00",
    day_end_time="17:00:00",
    status='Queued',
    current_stage='STAGE 1 - PATIENT CREATION'
)

from apps.lab.auto_trigger_views import process_auto_trigger
process_auto_trigger(history.id)

history.refresh_from_db()
print(f"History Run ID: {history.run_id}, Status: {history.status}, Success: {history.successful}, Failed: {history.failed}")
pts = Patient.objects.filter(auto_trigger_run=history).order_by('id')
print(f"Generated {pts.count()} patients.")
for p in pts:
    print(f"ID: {p.patient_id} OP: {p.op_number} Type: {p.patient_type} CreatedAt: {p.created_at} Dept: {p.department} Phone: '{p.mobile_no}'")
