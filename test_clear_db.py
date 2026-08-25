import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from apps.patients.models import Patient, PatientImportHistory
Patient.objects.all().delete()
PatientImportHistory.objects.all().delete()
print("DB cleared.")
