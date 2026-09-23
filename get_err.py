import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()
from apps.lab.models import AutoTriggerHistory
print(AutoTriggerHistory.objects.last().error_message)
