from apps.lab.models import Investigation, InvestigationParameter, AgeGroup, ParameterReferenceRange

# Age Groups
ags = [
    {'code': 'NEWBORN', 'label': 'Newborn', 'min': 0, 'max': 28, 'unit': 'Days', 'gender': 'All', 'preg': False, 'order': 1},
    {'code': 'INFANT', 'label': 'Infant', 'min': 29, 'unit_min': 'Days', 'max': 12, 'unit_max': 'Months', 'gender': 'All', 'preg': False, 'order': 2},
    {'code': 'CHILD', 'label': 'Child', 'min': 1, 'unit_min': 'Years', 'max': 12, 'unit_max': 'Years', 'gender': 'All', 'preg': False, 'order': 3},
    {'code': 'ADULT-MALE', 'label': 'Adult Male', 'min': 13, 'unit_min': 'Years', 'max': 120, 'unit_max': 'Years', 'gender': 'Male', 'preg': False, 'order': 4},
    {'code': 'ADULT-FEMALE', 'label': 'Adult Female', 'min': 13, 'unit_min': 'Years', 'max': 120, 'unit_max': 'Years', 'gender': 'Female', 'preg': False, 'order': 5},
    {'code': 'PREGNANT-FEMALE', 'label': 'Pregnant Female', 'min': 13, 'unit_min': 'Years', 'max': 120, 'unit_max': 'Years', 'gender': 'Female', 'preg': True, 'order': 6}
]

created_ags = []
for ag in ags:
    obj, _ = AgeGroup.objects.get_or_create(code=ag['code'], defaults={
        'label': ag['label'],
        'min_age_value': ag['min'],
        'min_age_unit': ag.get('unit_min', ag.get('unit', 'Days')),
        'max_age_value': ag['max'],
        'max_age_unit': ag.get('unit_max', ag.get('unit', 'Days')),
        'gender': ag['gender'],
        'pregnancy_applicable': ag['preg'],
        'sort_order': ag['order']
    })
    created_ags.append(obj)

# Investigation
inv, _ = Investigation.objects.get_or_create(code='CBC', defaults={
    'name': 'Complete Blood Count',
    'is_active': True
})

# Parameter
param, _ = InvestigationParameter.objects.get_or_create(investigation=inv, code='CBC-HB', defaults={
    'name': 'Hemoglobin',
    'short_name': 'Hb',
    'result_type': 'Numeric',
    'unit': 'g/dL',
    'decimal_precision': 1,
    'display_order': 1,
    'is_active': True
})

print("Sample data created successfully!")
