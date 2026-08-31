import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.auto_trigger_views import process_auto_trigger
from apps.lab.models import AutoTriggerHistory, AutoTriggerLog

history = AutoTriggerHistory.objects.order_by('-id').first()
# Reset it
history.status = 'Queued'
history.successful = 0
history.processed_entries = 0
history.failed = 0
history.save()

process_auto_trigger(history.id)

for log in history.logs.all():
    print(f"Log: {log.status} - {log.message}")
