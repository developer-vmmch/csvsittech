import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from apps.patients.models import Patient
from django.db.models import Count

print(f"Total Patients: {Patient.objects.count()}")

distribution = Patient.objects.values('registration_date').annotate(count=Count('id')).order_by('registration_date')
for row in distribution[:5]:
    print(row)
for row in distribution[len(distribution)-5:]:
    print(row)
