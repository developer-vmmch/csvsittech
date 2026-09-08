import os
import django
import sys
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import (
    Investigation, Parameter, InvestigationParameter, 
    ParameterReferenceRange
)

data = [
    {
        "inv_code": "UR",
        "inv_name": "URINE ROUTINE",
        "parameters": [
            {"order": 1, "code": "00013671", "name": "Macroscopy", "range": "-", "unit": "", "sample": "", "method": ""},
            {"order": 2, "code": "00021366", "name": "Colour", "range": "Straw Yellow", "unit": "", "sample": "", "method": ""},
            {"order": 3, "code": "01592782", "name": "Appearance", "range": "Clear", "unit": "", "sample": "Urine", "method": "Macroscopy"},
            {"order": 4, "code": "01593672", "name": "Odour", "range": "-", "unit": "", "sample": "", "method": ""},
            {"order": 5, "code": "01593673", "name": "Volume", "range": "-", "unit": "", "sample": "", "method": ""},
            {"order": 6, "code": "01593721", "name": "Chemical Examination", "range": "-", "unit": "", "sample": "", "method": ""},
            {"order": 7, "code": "00020673", "name": "PH", "range": "5-7", "unit": "", "sample": "", "method": ""},
            {"order": 8, "code": "00020694", "name": "Specific gravity - urine", "range": "1.010 - 1.025", "unit": "", "sample": "Urine", "method": "Photoelectric"},
            {"order": 9, "code": "00021030", "name": "Urine Albumin", "range": "Nil", "unit": "", "sample": "URINE", "method": "Protein error"},
            {"order": 10, "code": "00020007", "name": "Urine sugar", "range": "NEGATIVE", "unit": "-", "sample": "Urine", "method": "Reagent Strip"},
            {"order": 11, "code": "00020436", "name": "Bile Salt", "range": "Negative", "unit": "-", "sample": "Urine", "method": ""},
            {"order": 12, "code": "00020437", "name": "Bile Pigments", "range": "Negative", "unit": "-", "sample": "Urine", "method": ""},
            {"order": 13, "code": "00020450", "name": "Urobilinogen", "range": "Present", "unit": "", "sample": "", "method": "REAGENT"},
            {"order": 14, "code": "00020417", "name": "Urine ketones", "range": "Negative", "unit": "-", "sample": "", "method": "REAGENT"},
            {"order": 15, "code": "00020760", "name": "Nitrate(Urine)", "range": "Negative", "unit": "", "sample": "urine", "method": ""},
            {"order": 16, "code": "01592784", "name": "Blood", "range": "Negative", "unit": "", "sample": "Urine", "method": "Reagent Strip"},
            {"order": 17, "code": "00021361", "name": "Microscopy", "range": "-", "unit": "", "sample": "", "method": ""},
            {"order": 18, "code": "00021358", "name": "RBCs", "range": "0 - 1/HPF", "unit": "", "sample": "", "method": ""},
            {"order": 19, "code": "00020353", "name": "Pus cells", "range": "1 - 2/HPF", "unit": "", "sample": "", "method": ""},
            {"order": 20, "code": "00021359", "name": "Epithelial Cells", "range": "2 - 3/HPF", "unit": "", "sample": "", "method": ""},
            {"order": 21, "code": "00021360", "name": "Cast", "range": "/ HPF", "unit": "", "sample": "", "method": ""},
            {"order": 22, "code": "00020352", "name": "Crystals", "range": "Nil", "unit": "", "sample": "", "method": ""},
            {"order": 23, "code": "00021362", "name": "Others(Drivers/staff/Technician)", "range": "Nil", "unit": "-", "sample": "", "method": ""},
            {"order": 24, "code": "00021036", "name": "Urine Casts", "range": "-", "unit": "", "sample": "", "method": ""},
        ]
    },
    {
        "inv_code": "00020346",
        "inv_name": "ESR",
        "parameters": [
            {"order": 1, "code": "00020346", "name": "ESR", "range": "0-13", "unit": "mm/hr", "sample": "EDTA", "method": ""},
        ]
    },
    {
        "inv_code": "SR_ELEC",
        "inv_name": "SR ELECTROLYTES (NA+,K+,CL-)",
        "parameters": [
            {"order": 1, "code": "00020017", "name": "Serum Sodium", "range": "136 - 144", "unit": "mmol/L", "sample": "Serum", "method": "ISE"},
            {"order": 2, "code": "00020018", "name": "Serum Potassium", "range": "3.7 - 5.1", "unit": "mmol/L", "sample": "Serum", "method": "ISE"},
            {"order": 3, "code": "00020019", "name": "Chloride", "range": "97 - 105", "unit": "mmol/L", "sample": "Serum", "method": "ISE"},
        ]
    },
    {
        "inv_code": "RFT",
        "inv_name": "RFT - Renal Function Test",
        "parameters": [
            {"order": 1, "code": "00020020", "name": "UREA", "range": "15-45", "unit": "mg/dL", "sample": "Serum", "method": "GLDH-Urea"},
            {"order": 2, "code": "00020022", "name": "CREATININE", "range": "0.5-1.5", "unit": "mg/dL", "sample": "Serum", "method": "Enzymatic"},
        ]
    },
    {
        "inv_code": "00020642",
        "inv_name": "LFT Liver Function Test",
        "parameters": [
            {"order": 1, "code": "00020076", "name": "Blood Bilirubin(Total)", "range": "0.2-1", "unit": "mg%", "sample": "Serum", "method": "DCA Method"},
            {"order": 2, "code": "00020077", "name": "Blood Bilirubin(Direct)", "range": "<0.4", "unit": "mg%", "sample": "Serum", "method": "DIAZO Method"},
            {"order": 3, "code": "00020078", "name": "Blood Bilirubin(Indirect)", "range": "<0.6", "unit": "mg%", "sample": "Serum", "method": "Calculated"},
            {"order": 4, "code": "00020083", "name": "Blood SGOT (AST)", "range": "5-45", "unit": "IU/L", "sample": "Serum", "method": "UV Kinetic"},
            {"order": 5, "code": "00020084", "name": "Blood SGPT (ALT)", "range": "5-40", "unit": "IU/L", "sample": "Serum", "method": "UV Kinetic"},
            {"order": 6, "code": "00020039", "name": "ALP", "range": "64 - 306", "unit": "IU/L", "sample": "Serum", "method": "pNPP/AMP"},
            {"order": 7, "code": "00020085", "name": "GGT", "range": "5-32", "unit": "IU/L", "sample": "Serum", "method": "Szasz method"},
            {"order": 8, "code": "00021010", "name": "Blood Total Protein", "range": "6-8", "unit": "g%", "sample": "Serum", "method": "Biuret Method"},
            {"order": 9, "code": "00020080", "name": "Serum Albumin", "range": "3.5 - 5", "unit": "g/dL", "sample": "Serum", "method": "Bromocresol"},
        ]
    },
    {
        "inv_code": "00023296",
        "inv_name": "THYROID FUNCTION TEST",
        "parameters": [
            {"order": 1, "code": "00020059", "name": "Total T3", "range": "1 days-4 days:100-740\\nng/dl", "unit": "ng/dl", "sample": "Serum", "method": "CLIA"},
            {"order": 2, "code": "00020060", "name": "Total T4", "range": "1Days-4 Days:11.8-22.6", "unit": "µg/ml", "sample": "Serum", "method": "CLIA"},
            {"order": 3, "code": "00021630", "name": "THYROID STIMULATING HORMONE - TSH", "range": "0.3-4.5", "unit": "micro IU/mL", "sample": "", "method": "CLIA"},
        ]
    }
]

def parse_range(r):
    r = r.strip()
    if not r or r == '-':
        return None, None
    # e.g. "11.5-15.5", "136 - 144", "0-13", "0.5-1.5"
    m = re.match(r'^\s*([0-9\.]+)\s*-\s*([0-9\.]+)\s*$', r)
    if m:
        return float(m.group(1)), float(m.group(2))
    # e.g. "0 - 1/HPF" might not parse well, let's keep it textual if it has letters
    return None, None

stats = {
    'investigations_created': 0,
    'investigations_reused': 0,
    'parameters_created': 0,
    'parameters_reused': 0,
    'mappings_created': 0,
    'mappings_reused': 0,
    'ranges_created': 0,
    'ranges_reused': 0,
}

for group in data:
    inv, created = Investigation.objects.get_or_create(
        code=group['inv_code'],
        defaults={'name': group['inv_name'], 'is_active': True}
    )
    if created:
        stats['investigations_created'] += 1
    else:
        stats['investigations_reused'] += 1

    for p in group['parameters']:
        param, p_created = Parameter.objects.get_or_create(
            code=p['code'],
            defaults={
                'name': p['name'], 
                'default_unit': p['unit'],
                'data_type': 'NUMERIC' if parse_range(p['range'])[0] is not None else 'TEXT'
            }
        )
        if p_created:
            stats['parameters_created'] += 1
        else:
            stats['parameters_reused'] += 1
            
        ip_mapping, ip_created = InvestigationParameter.objects.get_or_create(
            investigation=inv,
            parameter=param,
            defaults={
                'name': p['name'],
                'display_order': p['order'],
                'unit': p['unit'],
                'is_active': True
            }
        )
        # Force sort_order update if reused
        if not ip_created:
            updated = False
            if ip_mapping.display_order != p['order']:
                ip_mapping.display_order = p['order']
                updated = True
            if ip_mapping.unit != p['unit']:
                ip_mapping.unit = p['unit']
                updated = True
            if updated:
                ip_mapping.save()
            stats['mappings_reused'] += 1
        else:
            stats['mappings_created'] += 1
            
        # Parse Reference Range
        min_val, max_val = parse_range(p['range'])
        
        # We need to see if range already exists for this mapping without age group
        rr, rr_created = ParameterReferenceRange.objects.get_or_create(
            investigation_parameter=ip_mapping,
            age_group__isnull=True,
            gender='All',
            defaults={
                'min_value': min_val,
                'max_value': max_val,
                'reference_text': p['range'] if min_val is None else None,
                'unit': p['unit'],
                'method': p['method'],
                'is_active': True
            }
        )
        
        if not rr_created:
            # Update it
            rr.min_value = min_val
            rr.max_value = max_val
            rr.reference_text = p['range'] if min_val is None else None
            rr.unit = p['unit']
            rr.method = p['method']
            rr.save()
            stats['ranges_reused'] += 1
        else:
            stats['ranges_created'] += 1

print(f"Investigations: {stats['investigations_created']} created, {stats['investigations_reused']} reused.")
print(f"Parameters: {stats['parameters_created']} created, {stats['parameters_reused']} reused.")
print(f"Mappings: {stats['mappings_created']} created, {stats['mappings_reused']} reused.")
print(f"Reference Ranges: {stats['ranges_created']} created, {stats['ranges_reused']} reused.")
