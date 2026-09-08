import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.patients.models import Department
from apps.lab.models import Diagnosis, DiagnosisInvestigationMap, Investigation, AgeGroup

def seed_data():
    print("--- SEEDING DEPARTMENTS ---")
    departments_data = [
        ("DENTAL", "DENT"),
        ("DERMATOLOGY", "DERM"),
        ("EMERGENCY MEDICINE", "EM"),
        ("ENT", "ENT"),
        ("GENERAL MEDICINE", "GM"),
        ("GENERAL SURGERY", "GS"),
        ("GYNAECOLOGY", "GYN"),
        ("OBSTETRICS", "OBS"),
        ("OPHTHALMOLOGY", "OPH"),
        ("ORTHOPAEDICS", "ORTH"),
        ("PAEDIATRICS", "PED"),
        ("PSYCHIATRY", "PSY"),
    ]
    
    dept_map = {}
    for name, code in departments_data:
        dept, created = Department.objects.get_or_create(name=name, defaults={'code': code, 'is_active': True})
        if not created and not dept.code:
            dept.code = code
            dept.save()
        dept_map[name] = dept
        print(f"{'Created' if created else 'Found'} Department: {dept.name} ({dept.code})")

    print("\n--- SEEDING DIAGNOSES ---")
    diagnoses_data = [
        {"name": "Essential hypertension", "code": "BA00", "dept": "GENERAL MEDICINE"},
        {"name": "Type 2 diabetes mellitus", "code": "5A11", "dept": "GENERAL MEDICINE"},
        {"name": "Iron deficiency anaemia", "code": "3A00", "dept": "GENERAL MEDICINE"},
        {"name": "Hypothyroidism", "code": "5A00", "dept": "GENERAL MEDICINE"},
        {"name": "Pneumonia, organism unspecified", "code": "CA40.Z", "dept": "GENERAL MEDICINE"},
        {"name": "Asthma", "code": "CA23", "dept": "GENERAL MEDICINE"},
        {"name": "Acute upper respiratory infection, site unspecified", "code": "CA07.0", "dept": "ENT"},
        {"name": "Gastro-oesophageal reflux disease", "code": "DA22", "dept": "GENERAL MEDICINE"},
        {"name": "Gastritis", "code": "DA42", "dept": "GENERAL MEDICINE"},
        {"name": "Acute appendicitis", "code": "DB10.0", "dept": "GENERAL SURGERY"},
        {"name": "Urinary tract infection, site not specified", "code": "GC08", "dept": "GENERAL MEDICINE"},
        {"name": "Chronic kidney disease", "code": "GB61", "dept": "GENERAL MEDICINE"},
        {"name": "Atopic eczema", "code": "EA80", "dept": "DERMATOLOGY"},
        {"name": "Acute otitis media", "code": "AB00", "dept": "ENT"},
        {"name": "Osteoarthritis of knee", "code": "FA01", "dept": "ORTHOPAEDICS"},
        {"name": "Cataract", "code": "9B10", "dept": "OPHTHALMOLOGY"},
        {"name": "Single episode depressive disorder", "code": "6A70", "dept": "PSYCHIATRY"},
        {"name": "Endometriosis", "code": "GA10", "dept": "GYNAECOLOGY"},
        {"name": "Ectopic pregnancy", "code": "JA01", "dept": "OBSTETRICS"},
        {"name": "Dental caries", "code": "DA08.0", "dept": "DENTAL"},
    ]
    
    diag_obj_map = {}
    for d_data in diagnoses_data:
        diag, created = Diagnosis.objects.get_or_create(
            code=d_data['code'],
            defaults={
                'name': d_data['name'],
                'icd11_title': d_data['name'],
                'source': 'WHO ICD-11 MMS',
                'icd_version': '2026-01',
                'is_active': True
            }
        )
        if not created:
            diag.name = d_data['name']
            diag.icd11_title = d_data['name']
            diag.save()
        diag_obj_map[d_data['code']] = diag
        print(f"{'Created' if created else 'Found'} Diagnosis: {diag.name} [{diag.code}]")

        # Map to Department using DiagnosisDepartmentMapping if it exists
        try:
            from apps.lab.models import DiagnosisDepartmentMapping
            if d_data['dept'] in dept_map:
                DiagnosisDepartmentMapping.objects.get_or_create(
                    diagnosis=diag,
                    department=dept_map[d_data['dept']]
                )
        except ImportError:
            pass

    print("\n--- RESOLVING INVESTIGATIONS ---")
    investigations = Investigation.objects.all()
    inv_map = {}
    for i in investigations:
        name_upper = i.name.upper()
        if "CBC" in name_upper or "COMPLETE BLOOD COUNT" in name_upper: inv_map["CBC"] = i
        elif "URINE ROUTINE" in name_upper or "UR" == name_upper: inv_map["UR / URINE ROUTINE"] = i
        elif "ESR" in name_upper: inv_map["ESR"] = i
        elif "ELECTROLYTE" in name_upper: inv_map["SR ELECTROLYTES"] = i
        elif "RENAL FUNCTION" in name_upper or "RFT" in name_upper: inv_map["RFT"] = i
        elif "LIVER FUNCTION" in name_upper or "LFT" in name_upper: inv_map["LFT"] = i
        elif "THYROID" in name_upper or "TFT" in name_upper: inv_map["THYROID FUNCTION TEST"] = i
        elif "GRBS" in name_upper: inv_map["GRBS"] = i
        elif "AEC" in name_upper: inv_map["AEC"] = i
        elif "FERRITIN" in name_upper: inv_map["FERRITIN"] = i
    
    for key, val in inv_map.items():
        print(f"Matched {key} to ID: {val.id} - {val.name}")

    print("\n--- SEEDING MAPPINGS ---")
    mappings = {
        "BA00": ["RFT", "SR ELECTROLYTES", "UR / URINE ROUTINE", "CBC"],
        "5A11": ["GRBS", "RFT", "UR / URINE ROUTINE", "LFT"],
        "3A00": ["CBC", "FERRITIN", "ESR"],
        "5A00": ["THYROID FUNCTION TEST", "CBC"],
        "CA40.Z": ["CBC", "ESR", "GRBS"],
        "CA23": ["CBC", "AEC"],
        "CA07.0": ["CBC", "ESR"],
        "DA22": ["CBC", "LFT"],
        "DA42": ["CBC", "LFT"],
        "DB10.0": ["CBC", "UR / URINE ROUTINE", "GRBS"],
        "GC08": ["UR / URINE ROUTINE", "CBC", "RFT"],
        "GB61": ["RFT", "SR ELECTROLYTES", "UR / URINE ROUTINE", "CBC"],
        "EA80": ["CBC", "AEC"],
        "AB00": ["CBC", "ESR"],
        "FA01": ["CBC", "ESR"],
        "9B10": ["CBC", "GRBS"],
        "6A70": ["CBC", "THYROID FUNCTION TEST"],
        "GA10": ["CBC", "ESR"],
        "JA01": ["CBC", "GRBS", "RFT"],
        "DA08.0": [],
    }

    created_count = 0
    for diag_code, inv_list in mappings.items():
        diag = diag_obj_map.get(diag_code)
        if not diag: continue
        
        for inv_key in inv_list:
            inv = inv_map.get(inv_key)
            if not inv: 
                print(f"WARNING: Could not find investigation {inv_key} for mapping.")
                continue
            
            m, created = DiagnosisInvestigationMap.objects.get_or_create(
                diagnosis=diag,
                investigation=inv,
                age_group=None
            )
            if created:
                created_count += 1
    
    print(f"Created {created_count} new diagnosis-investigation mappings.")
    print("Done!")

if __name__ == "__main__":
    seed_data()
