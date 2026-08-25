import pandas as pd
df = pd.read_excel("/home/Loosifer/Documents/VMMCerp/VMMCerp/VMMC_ERP_Patient_Import_May01_to_Aug25_2026.xlsx", dtype=str)
print("Columns:", [str(c).strip().lower().replace(' ', '_') for c in df.columns])
