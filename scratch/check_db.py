import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import Parameter, Investigation, LabDepartment, SampleType, InvestigationParameter, ParameterReferenceRange

print("Investigations:")
for inv in Investigation.objects.filter(name__icontains="CBC") | Investigation.objects.filter(code="CBC"):
    print(inv.id, inv.name, inv.code)

print("\nParameters:")
for p in Parameter.objects.filter(name__icontains="Hemoglobin"):
    print(p.id, p.name, p.code)

print("\nDepartments:")
for d in LabDepartment.objects.all():
    print(d.id, d.name)

print("\nSample Types:")
for s in SampleType.objects.all():
    print(s.id, s.name)

