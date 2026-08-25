import pandas as pd
df = pd.read_excel("/home/Loosifer/Documents/VMMCerp/VMMCerp/VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx", dtype=str)
df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
print("Patient Title:", repr(df.iloc[0].get('patient_title')))
print("Age display:", repr(df.iloc[0].get('age_display')))
print("Reg Date:", repr(df.iloc[0].get('registration_date')))
print("DOB:", repr(df.iloc[0].get('date_of_birth')))
