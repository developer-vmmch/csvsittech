import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import Parameter, Investigation

print(f"Total Investigations: {Investigation.objects.count()}")
print(f"Total Parameters: {Parameter.objects.count()}")

