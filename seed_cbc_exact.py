import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import (
    Investigation, Parameter, InvestigationParameter, 
    AgeGroup, ParameterReferenceRange, LabDepartment, SampleType
)

def seed():
    # 1. Ensure minimal age group exists to satisfy FK constraint safely without "designing" new age groups
    default_age_group, _ = AgeGroup.objects.get_or_create(
        code="DEFAULT_CBC",
        defaults={
            "label": "Default (For CBC)",
            "min_age_value": 0,
            "min_age_unit": "Years",
            "max_age_value": 120,
            "max_age_unit": "Years",
            "gender": "All",
            "is_active": True
        }
    )

    # 2. Ensure minimal department/sample type if required (SampleType and Department are optional on Investigation)
    # Investigation model: department (FK, null=True), sample_type (FK, null=True)
    # So we don't strictly need them, but we'll try to use existing if they exist, else leave blank.
    
    # 3. Create or Update CBC Investigation
    cbc, _ = Investigation.objects.update_or_create(
        code='CBC',
        defaults={
            'name': 'Complete Blood Count',
            'short_name': 'CBC',
            'is_panel': True,
            'is_active': True
        }
    )

    parameters_data = [
        {"order": 1, "code": "00020350", "name": "Hemoglobin", "range": "11.5-15.5", "unit": "g/dl", "sample": "Whole Blood", "method": "Colorimetric"},
        {"order": 2, "code": "00020175", "name": "Total WBC Count", "range": "5.0-13.0", "unit": "X10^3/uL", "method": "Laser Flow"},
        {"order": 3, "code": "00020685", "name": "RBC Count", "range": "3.5-4.8", "unit": "10^6/uL", "method": "Sheath Fluid"},
        {"order": 4, "code": "00020375", "name": "MCV", "range": "80-100", "unit": "fl", "method": "Calculated"},
        {"order": 5, "code": "00020376", "name": "MCH", "range": "25-33", "unit": "pg", "method": "Calculated"},
        {"order": 6, "code": "00020377", "name": "MCHC", "range": "32-36", "unit": "g/dL", "method": "Calculated"},
        {"order": 7, "code": "00020378", "name": "RDW (CV %)", "range": "11-16", "unit": "%", "method": "Calculated"},
        {"order": 8, "code": "00303646", "name": "RDW (SD)", "range": "35.0-56.0", "unit": "fl", "method": "Calculated"},
        {"order": 9, "code": "00020669", "name": "PCV", "range": "35-45", "unit": "%", "method": "Calculated"},
        {"order": 10, "code": "00020553", "name": "Differential Count", "range": "-", "unit": "", "type": "TEXT"},
        {"order": 11, "code": "00020177", "name": "Neutrophils", "range": "50-70", "unit": "%", "method": "Laser Flow"},
        {"order": 12, "code": "00020178", "name": "Lymphocytes", "range": "20-40", "unit": "%", "method": "Laser Flow"},
        {"order": 13, "code": "00020343", "name": "Monocytes", "range": "2-8", "unit": "%", "method": "Laser Flow"},
        {"order": 14, "code": "00020342", "name": "Eosinophils", "range": "1-4", "unit": "%", "method": "Laser Flow"},
        {"order": 15, "code": "00020355", "name": "Basophils", "range": "0-1", "unit": "%", "method": "Laser Flow"},
        {"order": 16, "code": "00025556", "name": "Mid Cells", "range": "3.0-15.0", "unit": "%", "sample": "EDTA Whole Blood", "method": "Colorimetric"},
        {"order": 17, "code": "00020359", "name": "Absolute Neutrophils Count", "range": "2-8", "unit": "X 10^3/uL", "method": "Calculated"},
        {"order": 18, "code": "00020358", "name": "Absolute Lymphocyte Count", "range": "1-5", "unit": "X 10^3/uL", "method": "Calculated"},
        {"order": 19, "code": "00303644", "name": "Absolute Monocyte count", "range": "0.2-1.0", "unit": "10^3/uL", "method": "Calculated"},
        {"order": 20, "code": "00020357", "name": "Absolute Eosinophil Count", "range": "0.1-0.5", "unit": "X10^3/uL", "method": "Laser Flow"},
        {"order": 21, "code": "00303645", "name": "Absolute Basophil Count", "range": "0.02-0.1", "unit": "X10^3/uL", "method": "Calculated"},
        {"order": 22, "code": "00025557", "name": "Mid cells Count", "range": "0.1-1.5", "unit": "", "sample": "EDTA Whole Blood", "method": "Colorimetric"},
        {"order": 23, "code": "00025549", "name": "IMG#", "range": "0.00-999.99", "unit": "10^3/uL"},
        {"order": 24, "code": "00020426", "name": "IMG%", "range": "0.0-100.0", "unit": "%"},
        {"order": 25, "code": "00020347", "name": "PLATELET COUNT", "range": "100-300", "unit": "10^3/uL", "method": "Sheath fluid"},
        {"order": 26, "code": "00022681", "name": "ESR", "range": "F : 0-20", "unit": "mm/first hour", "method": "Westergren"},
    ]

    for p in parameters_data:
        # Create or Get the base parameter
        data_type = 'TEXT' if p.get('type') == 'TEXT' else 'NUMERIC'
        param, _ = Parameter.objects.update_or_create(
            code=p['code'],
            defaults={
                'name': p['name'],
                'default_unit': p.get('unit', ''),
                'data_type': data_type,
                'is_active': True
            }
        )

        # Map to Investigation
        inv_param, _ = InvestigationParameter.objects.update_or_create(
            investigation=cbc,
            parameter=param,
            defaults={
                'code': p['code'],
                'name': p['name'],
                'unit': p.get('unit', ''),
                'result_type': data_type.capitalize(),
                'reference_range': p['range'],
                'display_order': p['order'],
                'is_active': True
            }
        )

        # Parse reference ranges
        range_text = p['range']
        min_v = None
        max_v = None
        if '-' in range_text and 'F :' not in range_text:
            parts = range_text.split('-')
            if len(parts) == 2:
                try:
                    min_v = float(parts[0].strip())
                    max_v = float(parts[1].strip())
                except ValueError:
                    pass

        # Create Reference Range
        range_type = 'Text' if data_type == 'TEXT' else 'Numeric'
        ParameterReferenceRange.objects.update_or_create(
            investigation_parameter=inv_param,
            age_group=None,
            gender='All',
            defaults={
                'range_type': range_type,
                'min_value': min_v,
                'max_value': max_v,
                'reference_text': range_text,
                'unit': p.get('unit', ''),
                'method': p.get('method', ''),
                'is_active': True
            }
        )
        
    print(f"Investigation count: {Investigation.objects.count()}")
    print(f"Parameter count: {Parameter.objects.count()}")
    print(f"CBC mapped parameters: {InvestigationParameter.objects.filter(investigation=cbc).count()}")
    print(f"Reference ranges created for CBC: {ParameterReferenceRange.objects.filter(investigation_parameter__investigation=cbc).count()}")
    print("CBC Parameter Codes:")
    for ip in InvestigationParameter.objects.filter(investigation=cbc).order_by('display_order'):
        print(f"  {ip.display_order}. {ip.code} - {ip.name}")

if __name__ == '__main__':
    seed()
