import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import Diagnosis, DiagnosisInvestigationMap

# The 20 ICD-11 codes provided in the prompt
icd11_codes = [
    "BA00", "5A11", "3A00", "5A00", "CA40.Z", "CA23", "CA07.0", "DA22",
    "DA42", "DB10.0", "GC08", "GB61", "EA80", "AB00", "FA01", "9B10",
    "6A70", "GA10", "JA01", "DA08.0"
]

diagnoses = Diagnosis.objects.filter(code__in=icd11_codes)

deleted_count = 0
for diag in diagnoses:
    # Delete mappings that HAVE an age group attached (fake default CBC ones)
    bad_mappings = DiagnosisInvestigationMap.objects.filter(diagnosis=diag, age_group__isnull=False)
    count, _ = bad_mappings.delete()
    if count > 0:
        print(f"Deleted {count} bad mappings for {diag.name}")
        deleted_count += count

print(f"Total bad mappings deleted: {deleted_count}")

# Verify Asthma mappings
asthma = Diagnosis.objects.filter(code='CA23').first()
if asthma:
    mappings = DiagnosisInvestigationMap.objects.filter(diagnosis=asthma)
    print(f"Asthma mappings count: {mappings.count()}")
    for m in mappings:
        print(f" - {m.investigation.name}")
