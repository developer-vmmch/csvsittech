import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

import logging
l = logging.getLogger('django.db.backends')
l.setLevel(logging.DEBUG)
l.addHandler(logging.StreamHandler())

from apps.lab.auto_trigger_views import process_auto_trigger
from apps.lab.models import AutoTriggerHistory

history = AutoTriggerHistory.objects.order_by('-id').first()
history.status = 'Queued'
history.successful = 0
history.processed_entries = 0
history.failed = 0
history.save()

try:
    process_auto_trigger(history.id)
except Exception as e:
    import traceback
    traceback.print_exc()

