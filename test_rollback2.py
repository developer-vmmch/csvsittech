import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.auto_trigger_views import process_auto_trigger
from apps.lab.models import AutoTriggerHistory

history = AutoTriggerHistory.objects.order_by('-id').first()
history.status = 'Queued'
history.successful = 0
history.processed_entries = 0
history.failed = 0
history.save()

process_auto_trigger(history.id)

