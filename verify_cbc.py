import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import Investigation, Parameter, ParameterReferenceRange, InvestigationParameter

cbc = Investigation.objects.get(code='CBC')

print(f"Investigation records:\n{Investigation.objects.count()}\n")
print(f"Parameter records:\n{Parameter.objects.count()}\n")
print(f"CBC parameters:\n{InvestigationParameter.objects.filter(investigation=cbc).count()}\n")
print(f"Reference range records:\n{ParameterReferenceRange.objects.count()}\n")
print(f"CBC mappings:\n{InvestigationParameter.objects.filter(investigation=cbc).count()}\n")

print("Actual CBC parameter codes found in the database:")
for ip in InvestigationParameter.objects.filter(investigation=cbc).order_by('display_order'):
    print(f"{ip.code}")
