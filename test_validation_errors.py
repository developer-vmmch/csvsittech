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

errors_tally = {}
for i, row in df.iterrows():
    parsed, status, errors = validate_patient_row(row, set(), set(), file_patient_ids, file_op_numbers)
    if status != 'Valid':
        err_str = " | ".join(errors)
        errors_tally[err_str] = errors_tally.get(err_str, 0) + 1

print("Errors tally:")
for k, v in errors_tally.items():
    print(f"{v}: {k}")
