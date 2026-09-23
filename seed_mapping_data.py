import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import Diagnosis, AgeGroup, Investigation, DiagnosisInvestigationMap

data = [
    {"diag": "Atypical Chest Pain", "age_grp": "Adult", "age_range": [18, 59], "invs": ["COMPLETE BLOOD COUNT (CBC)", "ERYTHROCYTE SEDIMENTATION RATE (ESR)", "C-REACTIVE PROTEIN (CRP)", "ELECTROCARDIOGRAM (ECG)"]},
    {"diag": "Atypical Chest Pain", "age_grp": "Child", "age_range": [1, 17], "invs": ["COMPLETE BLOOD COUNT (CBC)", "C-REACTIVE PROTEIN (CRP)"]},
    {"diag": "Fever", "age_grp": "Infant", "age_range": [0, 1], "invs": ["COMPLETE BLOOD COUNT (CBC)", "C-REACTIVE PROTEIN (CRP)", "BLOOD CULTURE"]},
    {"diag": "Fever", "age_grp": "Child", "age_range": [2, 12], "invs": ["COMPLETE BLOOD COUNT (CBC)", "WIDAL TEST", "C-REACTIVE PROTEIN (CRP)"]},
    {"diag": "Diabetes Mellitus", "age_grp": "Adult", "age_range": [18, 59], "invs": ["FASTING BLOOD SUGAR (FBS)", "POST PRANDIAL BLOOD SUGAR (PPBS)", "HbA1c", "LIPID PROFILE"]}
]

for item in data:
    d, _ = Diagnosis.objects.get_or_create(name=item["diag"], defaults={"code": "TEST"})
    ag, _ = AgeGroup.objects.get_or_create(age_group_name=item["age_grp"], defaults={"min_age": item["age_range"][0], "max_age": item["age_range"][1], "min_age_unit": 3, "max_age_unit": 3})
    dm, created = DiagnosisInvestigationMap.objects.get_or_create(diagnosis=d, age_group=ag)
    for inv_name in item["invs"]:
        inv, _ = Investigation.objects.get_or_create(investigation_name=inv_name, defaults={"investigation_code": "TEST1234", "sample_type": "Blood"})
        dm.investigations.add(inv)
        
print("Sample data seeded successfully!")
