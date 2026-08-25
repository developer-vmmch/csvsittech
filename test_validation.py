import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

import pandas as pd
from apps.patients.import_views import validate_patient_row

df = pd.read_excel("/home/Loosifer/Documents/VMMCerp/VMMCerp/VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx", dtype=str)
df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

file_patient_ids = set()
file_op_numbers = set()

parsed, status, errors = validate_patient_row(df.iloc[0], set(), set(), file_patient_ids, file_op_numbers)
print("Row 1 status:", status)
print("Row 1 errors:", errors)

parsed, status, errors = validate_patient_row(df.iloc[1], set(), set(), file_patient_ids, file_op_numbers)
print("Row 2 status:", status)
print("Row 2 errors:", errors)
