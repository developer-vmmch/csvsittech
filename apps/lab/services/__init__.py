from django.db.models import Q
from apps.lab.models import ParameterReferenceRange

def resolveReferenceRange(patient_age_group, diagnosis_id, investigation_parameter_id, gender=None):
    """
    Resolves the applicable reference range based on:
    1. Specific override: matching investigation_parameter, age_group, diagnosis, and (optionally) gender.
    2. Generic age-based range: matching investigation_parameter, age_group, diagnosis=None, and (optionally) gender.
    
    Returns the resolved ParameterReferenceRange object, or None if no match.
    """
    qs = ParameterReferenceRange.objects.filter(
        investigation_parameter_id=investigation_parameter_id,
        age_group=patient_age_group,
        is_active=True
    )
    
    if gender:
        gender_val = gender.capitalize() if isinstance(gender, str) else gender
        gender_qs = qs.filter(Q(gender=gender_val) | Q(gender__iexact='all'))
    else:
        gender_qs = qs.filter(gender__iexact='all')

    # 1. Try to find specific diagnosis override
    if diagnosis_id:
        specific_range = gender_qs.filter(diagnosis_id=diagnosis_id).order_by('-gender').first()
        if specific_range:
            return specific_range
            
    # 2. Fallback to generic age-based range (diagnosis=None)
    generic_range = gender_qs.filter(diagnosis__isnull=True).order_by('-gender').first()
    if generic_range:
        return generic_range
        
    return None
