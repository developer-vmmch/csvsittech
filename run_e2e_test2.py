import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import AutoTriggerHistory
history = AutoTriggerHistory.objects.order_by('-id').first()
print(history.error_message)
