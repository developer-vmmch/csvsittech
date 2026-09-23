import sys

file_path = 'apps/lab/import_views.py'
with open(file_path, 'r') as f:
    lines = f.readlines()

# Extract lines 32 to 358 (0-indexed: 31 to 357)
target_lines = lines[31:358]
target_str = "".join(target_lines)

# Perform replacements for LabDiagnosis
lab_str = target_str.replace("def api_diagnosis_", "def api_lab_diagnosis_")
lab_str = lab_str.replace("Diagnosis.objects", "LabDiagnosis.objects")
lab_str = lab_str.replace("creates.append(Diagnosis(", "creates.append(LabDiagnosis(")
lab_str = lab_str.replace("primary_diagnosis_import_template", "diagnosis_master_import_template")

# We also need to make sure we use LabDiagnosis
# Add import if missing
for i, line in enumerate(lines):
    if "from apps.lab.models import" in line and "Diagnosis," in line and "LabDiagnosis," not in line:
        lines[i] = line.replace("Diagnosis,", "Diagnosis, LabDiagnosis,")
        break
    elif "from apps.lab.models import" in line and "Diagnosis " in line and "LabDiagnosis" not in line:
        lines[i] = line.replace("Diagnosis ", "Diagnosis, LabDiagnosis ")
        break

# We need to insert lab_str before `def api_investigation_download_template` (line 359, index 358)
lines.insert(358, lab_str + "\n\n")

with open(file_path, 'w') as f:
    f.writelines(lines)
