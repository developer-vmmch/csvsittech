import os
import django
import sys
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import (
    Investigation, Parameter, InvestigationParameter, 
    ParameterReferenceRange, AgeGroup
)

def parse_range(r):
    r = r.strip()
    if not r or r == '-':
        return None, None
    m = re.match(r'^\s*([0-9\.]+)\s*-\s*([0-9\.]+)\s*$', r)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None

def get_or_create_age_group(label, min_val, min_unit, max_val, max_unit, gender='All'):
    ag = AgeGroup.objects.filter(label__iexact=label).first()
    if ag:
        return ag
    ag = AgeGroup.objects.create(
        code=label[:10].upper(),
        label=label,
        min_age_value=min_val,
        min_age_unit=min_unit,
        max_age_value=max_val,
        max_age_unit=max_unit,
        gender=gender,
        is_active=True
    )
    return ag

# Create Age Groups
ag_0_7d = get_or_create_age_group('0-7 days', 0, 'Days', 7, 'Days')
ag_8_30d = get_or_create_age_group('8-30 days', 8, 'Days', 30, 'Days')
ag_31d_11m = get_or_create_age_group('31 days-11 months', 31, 'Days', 11, 'Months')
ag_1_7y = get_or_create_age_group('1-7 years', 1, 'Years', 7, 'Years')
ag_gt_7y = get_or_create_age_group('>7 years', 7, 'Years', 150, 'Years')

ag_child = get_or_create_age_group('Child', 0, 'Years', 18, 'Years')
ag_adult_male = get_or_create_age_group('Adult Male', 18, 'Years', 150, 'Years', gender='Male')
ag_adult_female = get_or_create_age_group('Adult Female', 18, 'Years', 150, 'Years', gender='Female')

ag_1_4d = get_or_create_age_group('1 days-4 days', 1, 'Days', 4, 'Days')
ag_1_11m = get_or_create_age_group('1 month-11 month', 1, 'Months', 11, 'Months')
ag_1_5y = get_or_create_age_group('1 year-5 years', 1, 'Years', 5, 'Years')
ag_6_10y = get_or_create_age_group('6 years-10 years', 6, 'Years', 10, 'Years')
ag_11_15y = get_or_create_age_group('11 years-15 years', 11, 'Years', 15, 'Years')
ag_16_20y = get_or_create_age_group('16 years-20 years', 16, 'Years', 20, 'Years')
ag_21_50y = get_or_create_age_group('21 years-50 years', 21, 'Years', 50, 'Years')
ag_51_90y = get_or_create_age_group('51 years-90 years', 51, 'Years', 90, 'Years')

ag_1w_2w = get_or_create_age_group('1Week-2Weeks', 1, 'Weeks', 2, 'Weeks')
ag_1m_4m = get_or_create_age_group('1Month-4Months', 1, 'Months', 4, 'Months')
ag_4m_12m = get_or_create_age_group('4Months-12Months', 4, 'Months', 12, 'Months')
ag_16_60y_f = get_or_create_age_group('16Years-60Years', 16, 'Years', 60, 'Years', gender='Female')
ag_gt_60y = get_or_create_age_group('>60years', 60, 'Years', 150, 'Years')

stats = {
    'investigations_created': 0, 'investigations_reused': 0,
    'parameters_created': 0, 'parameters_reused': 0,
    'mappings_created': 0, 'mappings_reused': 0,
    'ranges_created': 0, 'ranges_reused': 0,
}

def seed_inv(inv_code, inv_name, params):
    inv, created = Investigation.objects.get_or_create(
        code=inv_code,
        defaults={'name': inv_name, 'is_active': True}
    )
    if created: stats['investigations_created'] += 1
    else: stats['investigations_reused'] += 1
    
    for p in params:
        param, p_created = Parameter.objects.get_or_create(
            code=p['code'],
            defaults={
                'name': p['name'], 
                'default_unit': p.get('unit', ''),
                'data_type': p.get('data_type', 'NUMERIC')
            }
        )
        if p_created: stats['parameters_created'] += 1
        else: stats['parameters_reused'] += 1
            
        ip_mapping, ip_created = InvestigationParameter.objects.get_or_create(
            investigation=inv,
            parameter=param,
            defaults={
                'name': p['name'],
                'display_order': p.get('order', 1),
                'unit': p.get('unit', ''),
                'is_active': True
            }
        )
        if not ip_created:
            updated = False
            if ip_mapping.display_order != p.get('order', 1):
                ip_mapping.display_order = p.get('order', 1)
                updated = True
            if ip_mapping.unit != p.get('unit', ''):
                ip_mapping.unit = p.get('unit', '')
                updated = True
            if updated:
                ip_mapping.save()
            stats['mappings_reused'] += 1
        else:
            stats['mappings_created'] += 1
            
        # Ranges
        for rr_data in p.get('ranges', []):
            min_val, max_val = parse_range(rr_data['range'])
            ref_text = rr_data['range'] if min_val is None else None
            if rr_data.get('exact_text'):
                ref_text = rr_data['exact_text']
                
            rr, rr_created = ParameterReferenceRange.objects.get_or_create(
                investigation_parameter=ip_mapping,
                age_group=rr_data.get('ag'),
                gender=rr_data.get('gender', 'All'),
                pregnancy=rr_data.get('pregnancy', False),
                defaults={
                    'min_value': min_val,
                    'max_value': max_val,
                    'reference_text': ref_text,
                    'unit': rr_data.get('unit', p.get('unit', '')),
                    'method': p.get('method', ''),
                    'remarks': rr_data.get('remarks', ''),
                    'is_active': True
                }
            )
            if not rr_created:
                rr.min_value = min_val
                rr.max_value = max_val
                rr.reference_text = ref_text
                rr.unit = rr_data.get('unit', p.get('unit', ''))
                rr.method = p.get('method', '')
                rr.remarks = rr_data.get('remarks', '')
                rr.save()
                stats['ranges_reused'] += 1
            else:
                stats['ranges_created'] += 1

# 1. GRBS
seed_inv("GRBS", "GRBS", [
    {
        "order": 1, "code": "00021494", "name": "GRBS", "unit": "mg/dL", "method": "Hexokinase",
        "ranges": [
            {"ag": None, "range": "80-140"}
        ]
    }
])

# 2. AEC
seed_inv("AEC", "AEC", [
    {
        "order": 1, "code": "00022476", "name": "AEC", "unit": "x10^3/uL", "method": "Laser flow",
        "ranges": [
            {"ag": ag_0_7d, "range": "0.0-0.6", "remarks": "Source: Labcorp Pediatric Testing Reference Ranges"},
            {"ag": ag_8_30d, "range": "0.0-0.7", "remarks": "Source: Labcorp Pediatric Testing Reference Ranges"},
            {"ag": ag_31d_11m, "range": "0.0-0.4", "remarks": "Source: Labcorp Pediatric Testing Reference Ranges"},
            {"ag": ag_1_7y, "range": "0.0-0.3", "remarks": "Source: Labcorp Pediatric Testing Reference Ranges"},
            {"ag": ag_gt_7y, "range": "0.0-0.4", "remarks": "Source: Labcorp Pediatric Testing Reference Ranges"},
        ]
    }
])

# 3. FERRITIN
seed_inv("FERRITIN", "FERRITIN", [
    {
        "order": 1, "code": "00012199", "name": "FERRITIN", "unit": "ng/dl", "method": "",
        "ranges": [
            {"ag": ag_child, "range": "7-140"},
            {"ag": ag_adult_male, "range": "20-250", "gender": "Male"},
            {"ag": ag_adult_female, "range": "10-120", "gender": "Female"},
        ]
    }
])

# 4. THYROID FUNCTION TEST
seed_inv("00023296", "THYROID FUNCTION TEST", [
    {
        "order": 1, "code": "00020059", "name": "Total T3", "unit": "ng/dl", "method": "CLIA",
        "ranges": [
            {"ag": ag_1_4d, "range": "100-740", "exact_text": "1 days-4 days:100-740\\nng/dl"},
            {"ag": ag_1_11m, "range": "108-245"},
            {"ag": ag_1_5y, "range": "94-269"},
            {"ag": ag_6_10y, "range": "94-241"},
            {"ag": ag_11_15y, "range": "82-213"},
            {"ag": ag_16_20y, "range": "80-210"},
            {"ag": ag_21_50y, "range": "70-204"},
            {"ag": ag_51_90y, "range": "40-181"},
            {"ag": None, "range": "81-190", "pregnancy": True, "exact_text": "First trimester: 81-190"},
            {"ag": None, "range": "100-260", "pregnancy": True, "exact_text": "Second and third trimester: 100-260"},
        ]
    },
    {
        "order": 2, "code": "00020060", "name": "Total T4", "unit": "µg/ml", "method": "CLIA",
        "ranges": [
            {"ag": ag_1_4d, "range": "11.8-22.6", "exact_text": "1Days-4 Days:11.8-22.6"},
            {"ag": ag_1w_2w, "range": "9.9-16.6"},
            {"ag": ag_1m_4m, "range": "7.2-14.4"},
            {"ag": ag_4m_12m, "range": "7.8-16.5"},
            {"ag": ag_1_5y, "range": "7.3-15.0"},
            {"ag": ag_6_10y, "range": "6.4-13.3"},
            {"ag": ag_11_15y, "range": "5.6-11.7"},
            {"ag": ag_16_60y_f, "range": "5.5-11.0", "gender": "Female"},
            {"ag": ag_gt_60y, "range": "5.5-11.0"},
        ]
    }
])

print(f"Investigations: {stats['investigations_created']} created, {stats['investigations_reused']} reused.")
print(f"Parameters: {stats['parameters_created']} created, {stats['parameters_reused']} reused.")
print(f"Mappings: {stats['mappings_created']} created, {stats['mappings_reused']} reused.")
print(f"Reference Ranges: {stats['ranges_created']} created, {stats['ranges_reused']} reused.")
