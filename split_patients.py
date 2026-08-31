import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VMMCerp.settings')
django.setup()

from apps.patients.models import Patient
from django.db.models import Count
from django.db import transaction

print("Updating patient types...")
# Get registration dates with ~500 patients
dates = Patient.objects.values('registration_date').annotate(c=Count('id')).filter(c__gte=450)

for d in dates:
    r_date = d['registration_date']
    patients = list(Patient.objects.filter(registration_date=r_date).order_by('id'))
    
    o_patients = patients[:400]
    d_patients = patients[400:500] # At most 100
    
    o_ids = [p.id for p in o_patients]
    d_ids = [p.id for p in d_patients]
    
    with transaction.atomic():
        Patient.objects.filter(id__in=o_ids).update(patient_type='O')
        Patient.objects.filter(id__in=d_ids).update(patient_type='D', created_source='D')

    print(f"Updated {r_date}: O={len(o_ids)}, D={len(d_ids)}")

print("Done")
