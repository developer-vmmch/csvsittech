import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.auto_trigger_views import process_auto_trigger
from apps.lab.models import AutoTriggerHistory

# Override transaction to not swallow
import apps.lab.auto_trigger_views

original_atomic = apps.lab.auto_trigger_views.transaction.atomic

history = AutoTriggerHistory.objects.order_by('-id').first()
history.status = 'Queued'
history.successful = 0
history.processed_entries = 0
history.failed = 0
history.save()

# Let's inject a print into the except block of process_auto_trigger directly
import re
with open('apps/lab/auto_trigger_views.py', 'r') as f:
    content = f.read()
if "print('ERROR IN ATOMIC:', e)" not in content:
    content = content.replace("except Exception as e:", "except Exception as e:\n                            print('ERROR IN ATOMIC:', e)\n                            import traceback\n                            traceback.print_exc()")
    with open('apps/lab/auto_trigger_views.py', 'w') as f:
        f.write(content)

process_auto_trigger(history.id)

