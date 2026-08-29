import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import (
    Investigation, Parameter, InvestigationParameter, 
    AgeGroup, ParameterReferenceRange, ServiceRequest, 
    ServiceRequestInvestigation
)
from apps.patients.models import Patient, Department
from django.contrib.auth import get_user_model

User = get_user_model()

def seed():
    # Age Groups
    adult_group, _ = AgeGroup.objects.update_or_create(
        code='ADULT',
        defaults={
            'label': 'Adult',
            'min_age_value': 18,
            'min_age_unit': 'Years',
            'max_age_value': 120,
            'max_age_unit': 'Years',
            'is_active': True
        }
    )

    # Patient & Orders
    hod, _ = User.objects.get_or_create(username="admin", defaults={'is_staff': True, 'is_superuser': True})
    
    patient, _ = Patient.objects.update_or_create(
        patient_id='PAT-TEST-001',
        defaults={
            'name': 'Test Patient Lakshmi',
            'age_years': 32,
            'gender': 'Female',
        }
    )

    # CBC Investigation
    cbc, _ = Investigation.objects.update_or_create(
        code='CBC',
        defaults={
            'name': 'CBC Complete Blood Count (26 Parameters)',
            'short_name': 'CBC',
            'legacy_code': 'CBC',
            'is_active': True
        }
    )

    parameters_data = [
        {"code": "HGB", "name": "Hemoglobin", "unit": "g/dL", "method": "Colorimetric", "ranges": [
            {"gender": "Male", "min": 13.0, "max": 17.0},
            {"gender": "Female", "min": 12.0, "max": 15.0}
        ]},
        {"code": "WBC", "name": "Total WBC Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 4.0, "max": 10.0}
        ]},
        {"code": "RBC", "name": "RBC Count", "unit": "x10^6/uL", "method": "Sheath Fluid", "ranges": [
            {"gender": "Male", "min": 4.5, "max": 5.9},
            {"gender": "Female", "min": 4.1, "max": 5.1}
        ]},
        {"code": "MCV", "name": "MCV", "unit": "fL", "method": "Calculated", "ranges": [
            {"gender": "All", "min": 80, "max": 100}
        ]},
        {"code": "MCH", "name": "MCH", "unit": "pg", "method": "Calculated", "ranges": [
            {"gender": "All", "min": 27, "max": 32}
        ]},
        {"code": "MCHC", "name": "MCHC", "unit": "g/dL", "method": "Calculated", "ranges": [
            {"gender": "All", "min": 32, "max": 36}
        ]},
        {"code": "RDW_CV", "name": "RDW (CV %)", "unit": "%", "method": "Calculated", "ranges": [
            {"gender": "All", "min": 11, "max": 16}
        ]},
        {"code": "RDW_SD", "name": "RDW (SD)", "unit": "fL", "method": "Calculated", "ranges": [
            {"gender": "All", "min": 35.0, "max": 56.0}
        ]},
        {"code": "PCV", "name": "PCV", "unit": "%", "method": "Calculated", "ranges": [
            {"gender": "Male", "min": 40, "max": 52},
            {"gender": "Female", "min": 36, "max": 46}
        ]},
        {"code": "DIFF", "name": "Differential Count", "unit": "-", "method": "Manual", "ranges": [
            {"gender": "All", "type": "Text"}
        ]},
        {"code": "NEUT", "name": "Neutrophils", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 50, "max": 70}
        ]},
        {"code": "LYMPH", "name": "Lymphocytes", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 20, "max": 40}
        ]},
        {"code": "MONO", "name": "Monocytes", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 2, "max": 8}
        ]},
        {"code": "EOS", "name": "Eosinophils", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 1, "max": 4}
        ]},
        {"code": "BASO", "name": "Basophils", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0, "max": 1}
        ]},
        {"code": "MID_CELLS", "name": "Mid Cells", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 3.0, "max": 15.0}
        ]},
        {"code": "ANC", "name": "Absolute Neutrophils Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 2, "max": 8}
        ]},
        {"code": "ALC", "name": "Absolute Lymphocyte Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 1, "max": 3}
        ]},
        {"code": "AMC", "name": "Absolute Monocyte Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.08, "max": 0.8}
        ]},
        {"code": "AEC", "name": "Absolute Eosinophil Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.1, "max": 0.5}
        ]},
        {"code": "ABC", "name": "Absolute Basophil Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.02, "max": 0.1}
        ]},
        {"code": "MID_COUNT", "name": "Mid cells Count", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.1, "max": 1.5}
        ]},
        {"code": "IMG_COUNT", "name": "IMG#", "unit": "x10^3/uL", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.00, "max": 999.99}
        ]},
        {"code": "IMG_PERC", "name": "IMG%", "unit": "%", "method": "Laser Flow", "ranges": [
            {"gender": "All", "min": 0.0, "max": 100.0}
        ]},
        {"code": "PLT", "name": "PLATELET COUNT", "unit": "x10^3/uL", "method": "Sheath fluid", "ranges": [
            {"gender": "All", "min": 100, "max": 300}
        ]},
        {"code": "ESR", "name": "ESR", "unit": "mm/first hour", "method": "Westergren", "ranges": [
            {"gender": "Male", "min": 0, "max": 15},
            {"gender": "Female", "min": 0, "max": 20}
        ]},
    ]

    for order_idx, p_data in enumerate(parameters_data):
        param, _ = Parameter.objects.update_or_create(
            code=p_data['code'],
            defaults={
                'name': p_data['name'],
                'default_unit': p_data['unit'],
            }
        )
        
        inv_param, _ = InvestigationParameter.objects.update_or_create(
            investigation=cbc,
            parameter=param,
            defaults={
                'display_order': order_idx + 1,
                'is_active': True,
                 
            }
        )
        
        # Create reference ranges
        for r in p_data['ranges']:
            rtype = 'Text' if 'type' in r and r['type'] == 'Text' else 'Numeric'
            ref_text = ''
            if rtype == 'Numeric':
                ref_text = f"{r['min']} - {r['max']}"
            else:
                ref_text = '-'
                
            ParameterReferenceRange.objects.update_or_create(
                investigation_parameter=inv_param,
                age_group=adult_group,
                gender=r['gender'],
                defaults={
                    'range_type': rtype,
                    'min_value': r.get('min'),
                    'max_value': r.get('max'),
                    'reference_text': ref_text,
                    'unit': p_data['unit'],
                }
            )

    # Create ServiceRequest with CBC for the patient
    dept, _ = Department.objects.get_or_create(name="OPD")
    sr, _ = ServiceRequest.objects.get_or_create(
        sample_id='2608260191',
        defaults={
            'patient': patient,
            'consultant': hod,
            'department': dept,
            'status': 'Saved'
        }
    )
    
    sri, _ = ServiceRequestInvestigation.objects.get_or_create(
        service_request=sr,
        investigation=cbc,
        defaults={
            'status': 'RECEIVED'
        }
    )
    print("Seed complete. Order ID:", sri.id)

if __name__ == '__main__':
    seed()
