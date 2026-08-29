import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()
from apps.patients.models import Patient
from django.core.exceptions import ValidationError

p = Patient.objects.filter(patient_type='D').first()
if p:
    try:
        p.delete()
        print("FAIL: Patient was deleted!")
    except ValidationError as e:
        print("SUCCESS: Deletion blocked with ValidationError:", str(e))
else:
    print("No type D patients found.")
