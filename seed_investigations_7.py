import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from apps.lab.models import (
    Investigation, Parameter, AgeGroup, InvestigationParameter,
    ParameterReferenceRange, LabDepartment, SampleType
)
from decimal import Decimal

def seed():
    print("Starting seeding process for 7 investigations...")
    
    # Get or create department
    dept, _ = LabDepartment.objects.get_or_create(name='Biochemistry', defaults={'is_active': True})
    dept_haem, _ = LabDepartment.objects.get_or_create(name='Haematology', defaults={'is_active': True})
    dept_urine, _ = LabDepartment.objects.get_or_create(name='Clinical Pathology', defaults={'is_active': True})
    
    # Get or create sample types
    sample_serum, _ = SampleType.objects.get_or_create(name='Serum', defaults={'is_active': True})
    sample_blood, _ = SampleType.objects.get_or_create(name='BLOOD', defaults={'is_active': True})
    sample_urine, _ = SampleType.objects.get_or_create(name='Urine', defaults={'is_active': True})
    
    # Age Groups
    ag_newborn, _ = AgeGroup.objects.get_or_create(code='NEWBORN', defaults={'label': 'Newborn', 'min_age_value': 0, 'min_age_unit': 'Days', 'max_age_value': 28, 'max_age_unit': 'Days'})
    ag_infant, _ = AgeGroup.objects.get_or_create(code='INFANT', defaults={'label': 'Infant', 'min_age_value': 1, 'min_age_unit': 'Months', 'max_age_value': 11, 'max_age_unit': 'Months'})
    ag_adult_male, _ = AgeGroup.objects.get_or_create(code='ADULT_MALE', defaults={'label': 'Adult Male', 'min_age_value': 18, 'min_age_unit': 'Years', 'max_age_value': 150, 'max_age_unit': 'Years', 'gender': 'Male'})
    ag_adult_female, _ = AgeGroup.objects.get_or_create(code='ADULT_FEMALE', defaults={'label': 'Adult Female', 'min_age_value': 18, 'min_age_unit': 'Years', 'max_age_value': 150, 'max_age_unit': 'Years', 'gender': 'Female'})
    
    ag_phos_m1, _ = AgeGroup.objects.get_or_create(code='PHOS_M_1_4', defaults={'label': 'Male 1-4 yrs', 'min_age_value': 1, 'min_age_unit': 'Years', 'max_age_value': 4, 'max_age_unit': 'Years', 'gender': 'Male'})
    ag_phos_m2, _ = AgeGroup.objects.get_or_create(code='PHOS_M_5_13', defaults={'label': 'Male 5-13 yrs', 'min_age_value': 5, 'min_age_unit': 'Years', 'max_age_value': 13, 'max_age_unit': 'Years', 'gender': 'Male'})
    ag_phos_m3, _ = AgeGroup.objects.get_or_create(code='PHOS_M_14_15', defaults={'label': 'Male 14-15 yrs', 'min_age_value': 14, 'min_age_unit': 'Years', 'max_age_value': 15, 'max_age_unit': 'Years', 'gender': 'Male'})
    ag_phos_m4, _ = AgeGroup.objects.get_or_create(code='PHOS_M_16_17', defaults={'label': 'Male 16-17 yrs', 'min_age_value': 16, 'min_age_unit': 'Years', 'max_age_value': 17, 'max_age_unit': 'Years', 'gender': 'Male'})
    
    ag_phos_f1, _ = AgeGroup.objects.get_or_create(code='PHOS_F_1_7', defaults={'label': 'Female 1-7 yrs', 'min_age_value': 1, 'min_age_unit': 'Years', 'max_age_value': 7, 'max_age_unit': 'Years', 'gender': 'Female'})
    ag_phos_f2, _ = AgeGroup.objects.get_or_create(code='PHOS_F_8_13', defaults={'label': 'Female 8-13 yrs', 'min_age_value': 8, 'min_age_unit': 'Years', 'max_age_value': 13, 'max_age_unit': 'Years', 'gender': 'Female'})
    ag_phos_f3, _ = AgeGroup.objects.get_or_create(code='PHOS_F_14_15', defaults={'label': 'Female 14-15 yrs', 'min_age_value': 14, 'min_age_unit': 'Years', 'max_age_value': 15, 'max_age_unit': 'Years', 'gender': 'Female'})
    ag_phos_f4, _ = AgeGroup.objects.get_or_create(code='PHOS_F_16_17', defaults={'label': 'Female 16-17 yrs', 'min_age_value': 16, 'min_age_unit': 'Years', 'max_age_value': 17, 'max_age_unit': 'Years', 'gender': 'Female'})

    # Helper function to create Investigation, Parameter, Mapping, and Reference Ranges
    def create_lab_test(inv_name, inv_code, param_name, param_code, dept_obj, sample_obj, unit, data_type, ranges_info):
        print(f"Creating {inv_name}...")
        inv, _ = Investigation.objects.get_or_create(code=inv_code, defaults={
            'name': inv_name,
            'department': dept_obj,
            'sample_type': sample_obj,
            'is_active': True
        })
        param, _ = Parameter.objects.get_or_create(code=param_code, defaults={
            'name': param_name,
            'default_unit': unit,
            'data_type': data_type,
            'is_active': True
        })
        inv_param, _ = InvestigationParameter.objects.get_or_create(investigation=inv, code=param_code, defaults={
            'parameter': param,
            'name': param_name,
            'unit': unit,
            'is_active': True
        })
        
        for r_info in ranges_info:
            defaults = {
                'range_type': r_info['range_type'],
                'min_value': r_info.get('min_value'),
                'max_value': r_info.get('max_value'),
                'reference_text': r_info.get('reference_text'),
                'method': r_info.get('method'),
                'remarks': r_info.get('remarks'),
                'is_active': True,
                'unit': unit,
            }
            ag = r_info.get('age_group')
            gender = r_info.get('gender', 'All')
            ParameterReferenceRange.objects.get_or_create(
                investigation_parameter=inv_param,
                age_group=ag,
                gender=gender,
                defaults=defaults
            )

    # 1. RBS
    create_lab_test(
        inv_name='RBS', inv_code='00014149',
        param_name='RBS', param_code='00014149',
        dept_obj=dept, sample_obj=sample_serum,
        unit='mg/dl', data_type='NUMERIC',
        ranges_info=[{
            'range_type': 'Numeric', 'min_value': 80, 'max_value': 140, 'method': 'GOD/POD'
        }]
    )

    # 2. Hb
    create_lab_test(
        inv_name='Hb', inv_code='02904017',
        param_name='Hb', param_code='02904017',
        dept_obj=dept_haem, sample_obj=sample_blood,
        unit='g/dl', data_type='NUMERIC',
        ranges_info=[
            {'range_type': 'Numeric', 'min_value': 13.8, 'max_value': 17.2, 'age_group': ag_adult_male, 'gender': 'Male'},
            {'range_type': 'Numeric', 'min_value': 12.1, 'max_value': 15.1, 'age_group': ag_adult_female, 'gender': 'Female'},
            {'range_type': 'Numeric', 'min_value': 14, 'max_value': 24, 'age_group': ag_newborn, 'gender': 'All'},
            {'range_type': 'Numeric', 'min_value': 9.5, 'max_value': 14, 'age_group': ag_infant, 'gender': 'All'},
        ]
    )

    # 3. SR PHOSPHORUS
    create_lab_test(
        inv_name='SR PHOSPHORUS', inv_code='00012425',
        param_name='SR PHOSPHORUS', param_code='00012425',
        dept_obj=dept, sample_obj=sample_serum,
        unit='mg/dl', data_type='NUMERIC',
        ranges_info=[
            {'range_type': 'Numeric', 'min_value': 4.3, 'max_value': 5.4, 'age_group': ag_phos_m1, 'gender': 'Male', 'remarks': 'Reference value not established for patients <1 year'},
            {'range_type': 'Numeric', 'min_value': 3.7, 'max_value': 5.4, 'age_group': ag_phos_m2, 'gender': 'Male'},
            {'range_type': 'Numeric', 'min_value': 3.5, 'max_value': 5.3, 'age_group': ag_phos_m3, 'gender': 'Male'},
            {'range_type': 'Numeric', 'min_value': 3.1, 'max_value': 4.7, 'age_group': ag_phos_m4, 'gender': 'Male'},
            {'range_type': 'Numeric', 'min_value': 2.5, 'max_value': 4.5, 'age_group': ag_adult_male, 'gender': 'Male'},
            {'range_type': 'Numeric', 'min_value': 4.3, 'max_value': 5.4, 'age_group': ag_phos_f1, 'gender': 'Female', 'remarks': 'Reference value not established for patients <1 year'},
            {'range_type': 'Numeric', 'min_value': 4.0, 'max_value': 5.2, 'age_group': ag_phos_f2, 'gender': 'Female'},
            {'range_type': 'Numeric', 'min_value': 3.5, 'max_value': 4.9, 'age_group': ag_phos_f3, 'gender': 'Female'},
            {'range_type': 'Numeric', 'min_value': 3.1, 'max_value': 4.7, 'age_group': ag_phos_f4, 'gender': 'Female'},
            {'range_type': 'Numeric', 'min_value': 2.5, 'max_value': 4.5, 'age_group': ag_adult_female, 'gender': 'Female'},
        ]
    )

    # 4. URINE ACETONE
    create_lab_test(
        inv_name='URINE ACETONE', inv_code='00021115',
        param_name='URINE ACETONE', param_code='00021115',
        dept_obj=dept_urine, sample_obj=sample_urine,
        unit='-', data_type='TEXT',
        ranges_info=[{
            'range_type': 'Text', 'reference_text': 'Negative'
        }]
    )

    # 5. FBS
    create_lab_test(
        inv_name='FBS', inv_code='00025527',
        param_name='FBS', param_code='00025527',
        dept_obj=dept, sample_obj=sample_blood,
        unit='mg/dl', data_type='NUMERIC',
        ranges_info=[{
            'range_type': 'Numeric', 'min_value': 70, 'max_value': 110, 'method': 'GOD/POD'
        }]
    )

    # 6. BG (BLOOD GROUPING)
    # Using 'BG' as code since none is visible.
    create_lab_test(
        inv_name='BG (BLOOD GROUPING)', inv_code='BG',
        param_name='BG (BLOOD GROUPING)', param_code='BG',
        dept_obj=dept_haem, sample_obj=sample_blood,
        unit='-', data_type='TEXT', # Categorical / TEXT
        ranges_info=[{
            'range_type': 'Text', 'reference_text': 'A / B / AB / O with Rh +/-'
        }]
    )

    # 7. PPBS
    create_lab_test(
        inv_name='PPBS', inv_code='00025528',
        param_name='PPBS', param_code='00025528',
        dept_obj=dept, sample_obj=sample_blood,
        unit='mg/dl', data_type='NUMERIC',
        ranges_info=[{
            'range_type': 'Numeric', 'max_value': 145, 'reference_text': 'UPTO 145', 'method': 'GOD/POD'
        }] # Added min_value to handle "UPTO 145" in UI? Actually just reference_text and max_value.
    )

    print("Seeding completed successfully.")

if __name__ == '__main__':
    seed()
