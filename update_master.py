import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VMMCerp.settings')
django.setup()

from apps.patients.models import Department, DepartmentUnit

data = {
    "CHEST & TB": {
        "code": "CTB",
        "units": {
            "HOD-CTB -I": "CTB-I",
            "HOD-CTB -II": "CTB-II"
        }
    },
    "DENTAL": {
        "code": "DENTAL",
        "units": {
            "HOD-DENTAL": "DENTAL-HOD"
        }
    },
    "DERMATOLOGY": {
        "code": "DERM",
        "units": {
            "HOD-DENTAL": "DERM-HOD"
        }
    },
    "EMERGENCY MEDICINE": {
        "code": "EMR",
        "units": {
            "HOD-EMR": "EMR-HOD"
        }
    },
    "ENT": {
        "code": "ENT",
        "units": {
            "HOD-ENT": "ENT-HOD"
        }
    },
    "GENERAL MEDICINE": {
        "code": "GM",
        "units": {
            "HOD-GENERAL MEDICINE-I": "GM-I",
            "HOD-GENERAL MEDICINE-II": "GM-II",
            "HOD-GENERAL MEDICINE-III": "GM-III",
            "HOD-GENERAL MEDICINE-IV": "GM-IV",
            "HOD-GENERAL MEDICINE-V": "GM-V",
            "HOD-GENERAL MEDICINE-VI": "GM-VI",
            "HOD-GENERAL MEDICINE-VII": "GM-VII",
            "HOD-GENERAL MEDICINE-VIII": "GM-VIII",
        }
    },
    "GENERAL SURGERY": {
        "code": "GS",
        "units": {
            "HOD-GENERAL SURGERY -I": "GS-I",
            "HOD-GENERAL SURGERY -II": "GS-II",
            "HOD-GENERAL SURGERY -III": "GS-III",
            "HOD-GENERAL SURGERY -IV": "GS-IV",
            "HOD-GENERAL SURGERY -V": "GS-V",
            "HOD-GENERAL SURGERY -VI": "GS-VI",
            "HOD-GENERAL SURGERY -VII": "GS-VII",
            "HOD-GENERAL SURGERY -VIII": "GS-VIII",
        }
    },
    "GYNAECOLOGY": {
        "code": "GYN",
        "units": {
            "HOD-GYNAECOLOGY -I": "GYN-I",
            "HOD-GYNAECOLOGY -II": "GYN-II",
            "HOD-GYNAECOLOGY -III": "GYN-III",
            "HOD-GYNAECOLOGY -IV": "GYN-IV",
            "HOD-GYNAECOLOGY -V": "GYN-V",
        }
    },
    "OBSTETRICS": {
        "code": "OBS",
        "units": {
            "HOD-OBSTETRICS -I": "OBS-I",
            "HOD-OBSTETRICS -II": "OBS-II",
            "HOD-OBSTETRICS -III": "OBS-III",
            "HOD-OBSTETRICS -IV": "OBS-IV",
            "HOD-OBSTETRICS -V": "OBS-V",
        }
    },
    "PSYCHIATRY": {
        "code": "PSY",
        "units": {
            "HOD-PSY": "PSY-HOD"
        }
    },
    "PAEDIATRICS": {
        "code": "PED",
        "units": {
            "HOD-PAEDIATRICS -I": "PED-I",
            "HOD-PAEDIATRICS -II": "PED-II",
            "HOD-PAEDIATRICS -III": "PED-III",
            "HOD-PAEDIATRICS -IV": "PED-IV",
        }
    },
    "ORTHOPAEDICS": {
        "code": "ORTHO",
        "units": {
            "HOD-ORTHOPAEDICS -I": "ORTHO-I",
            "HOD-ORTHOPAEDICS -II": "ORTHO-II",
            "HOD-ORTHOPAEDICS -III": "ORTHO-III",
            "HOD-ORTHOPAEDICS -IV": "ORTHO-IV",
            "HOD-ORTHOPAEDICS -V": "ORTHO-V",
        }
    },
    "OPHTHALMOLOGY": {
        "code": "OPH",
        "units": {
            "HOD-OPHTHALMOLOGY -I": "OPH-I",
            "HOD-OPHTHALMOLOGY -II": "OPH-II",
        }
    }
}

for dept_name, info in data.items():
    # Find department or create it
    dept = Department.objects.filter(name__iexact=dept_name).first()
    if not dept:
        # Check if code is already taken by another department
        req_code = info['code']
        if Department.objects.filter(code__iexact=req_code).exists():
            print(f"Warning: Code {req_code} for {dept_name} is taken. Appending X.")
            req_code += 'X'
        dept = Department.objects.create(name=dept_name, code=req_code, is_active=True)
        print(f"Created Department: {dept_name}")
    else:
        # User said: "If a department already exists with a code: KEEP THE EXISTING CODE."
        # Meaning do NOT update the code if it already exists!
        pass
        
    order = 1
    for unit_name, unit_code in info['units'].items():
        # Clean unit code, maybe append suffix if not unique globally
        while DepartmentUnit.objects.filter(code__iexact=unit_code).exclude(department=dept, unit_name__iexact=unit_name).exists():
            unit_code += 'X'
        
        # Check if unit exists
        unit = DepartmentUnit.objects.filter(department=dept, unit_name__iexact=unit_name).first()
        if unit:
            if not unit.code:
                unit.code = unit_code
                unit.display_order = order
                unit.unit_type = 'HOD' if 'HOD' in unit_name.upper() else 'Unit'
                unit.save()
        else:
            DepartmentUnit.objects.create(
                department=dept,
                unit_name=unit_name,
                code=unit_code,
                unit_type='HOD' if 'HOD' in unit_name.upper() else 'Unit',
                display_order=order,
                is_active=True
            )
        order += 1

print("Completed department and unit setup.")
