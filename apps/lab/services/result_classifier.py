import re

STATUS_NORMAL = 'NORMAL'
STATUS_BELOW = 'BELOW'
STATUS_ABOVE = 'ABOVE'
STATUS_NON_NUMERIC = 'NON_NUMERIC'


def parse_reference_range(ref_str):
    if not ref_str or not str(ref_str).strip():
        return None, None
    s = str(ref_str).strip()
    s = re.sub(r'^-(F|M|Female|Male)\s*:\s*', '', s, flags=re.IGNORECASE).strip()
    m = re.match(r'^(?:UPTO|UP TO|UP-TO|MAX|MAXIMUM)\s*([-0-9.]+)', s, re.IGNORECASE)
    if m:
        try: return None, float(m.group(1))
        except ValueError: return None, None
    m = re.match(r'^<[=]?\s*([-0-9.]+)', s)
    if m:
        try: return None, float(m.group(1))
        except ValueError: return None, None
    m = re.match(r'^>[=]?\s*([-0-9.]+)', s)
    if m:
        try: return float(m.group(1)), None
        except ValueError: return None, None
    m = re.search(r'([-0-9.]+)\s*(?:-|to)\s*([-0-9.]+)', s, re.IGNORECASE)
    if m:
        try: return float(m.group(1)), float(m.group(2))
        except ValueError: return None, None
    m = re.match(r'^([-0-9.]+)\s*$', s)
    if m:
        try: return 0.0, float(m.group(1))
        except ValueError: return None, None
    return None, None


def classify_result(value_str, min_val, max_val, ref_text=None):
    if not value_str or not str(value_str).strip():
        return STATUS_NON_NUMERIC
    v_str = str(value_str).strip()
    try:
        val = float(v_str)
        is_num = True
    except (ValueError, TypeError):
        val = None
        is_num = False

    if is_num:
        if min_val is not None and max_val is not None:
            if val < min_val: return STATUS_BELOW
            elif val > max_val: return STATUS_ABOVE
            else: return STATUS_NORMAL
        elif min_val is not None:
            return STATUS_NORMAL if val >= min_val else STATUS_BELOW
        elif max_val is not None:
            return STATUS_NORMAL if val <= max_val else STATUS_ABOVE

    # Qualitative comparison if ref_text is provided
    if ref_text and str(ref_text).strip():
        r_str = str(ref_text).strip()
        # Direct case-insensitive equality
        if v_str.lower() == r_str.lower():
            return STATUS_NORMAL
        # Split multiple normal values like "2.0 / 2.3 / 2.5"
        allowed = [x.strip().lower() for x in re.split(r'[/,]', r_str) if x.strip()]
        if v_str.lower() in allowed:
            return STATUS_NORMAL
        # Common qualitative flags
        negatives = {'negative', 'nil', 'non-reactive', 'absent', 'not seen', 'normal', 'clear', 'straw yellow', 'straw'}
        positives = {'positive', 'reactive', 'present', 'seen', 'abnormal'}
        if r_str.lower() in negatives:
            if v_str.lower() in positives:
                return STATUS_ABOVE
            elif v_str.lower() in negatives:
                return STATUS_NORMAL

    return STATUS_NON_NUMERIC


def classify_from_range_string(value_str, ref_str):
    if not ref_str or not ref_str.strip(): return STATUS_NON_NUMERIC
    min_val, max_val = parse_reference_range(ref_str)
    return classify_result(value_str, min_val, max_val, ref_text=ref_str)


def age_to_days(value, unit):
    if value is None: return 0
    u = (unit or 'Years').strip().lower()
    if u in ('days', 'day'): return int(value)
    elif u in ('weeks', 'week'): return int(value) * 7
    elif u in ('months', 'month'): return int(value) * 30
    else: return int(value) * 365


def find_best_db_reference_range(investigation_parameter_id, patient_age_days, patient_gender, diagnosis_id=None):
    from apps.lab.models import ParameterReferenceRange
    ranges = list(
        ParameterReferenceRange.objects
        .filter(investigation_parameter_id=investigation_parameter_id, is_active=True)
        .select_related('age_group', 'diagnosis')
    )
    if not ranges: return None
    if len(ranges) == 1: return ranges[0]
    gender_norm = (patient_gender or 'All').strip().capitalize()
    if gender_norm not in ('Male', 'Female'): gender_norm = 'All'

    def age_ok(r):
        if r.age_group is None: return True
        ag = r.age_group
        mn = age_to_days(ag.min_age_value, ag.min_age_unit)
        mx = age_to_days(ag.max_age_value, ag.max_age_unit)
        return mn <= patient_age_days <= mx

    # 1. If diagnosis is specified, search diagnosis-specific ranges first
    if diagnosis_id:
        for r in ranges:
            if r.diagnosis_id == diagnosis_id and age_ok(r) and r.gender == gender_norm and r.age_group is not None:
                return r
        for r in ranges:
            if r.diagnosis_id == diagnosis_id and age_ok(r) and r.gender == 'All' and r.age_group is not None:
                return r
        for r in ranges:
            if r.diagnosis_id == diagnosis_id and r.age_group is None and r.gender == gender_norm:
                return r
        for r in ranges:
            if r.diagnosis_id == diagnosis_id and r.age_group is None and r.gender == 'All':
                return r

    # 2. Generic diagnosis ranges (diagnosis is None)
    for r in ranges:
        if r.diagnosis_id is None and age_ok(r) and r.gender == gender_norm and r.age_group is not None:
            return r
    for r in ranges:
        if r.diagnosis_id is None and age_ok(r) and r.gender == 'All' and r.age_group is not None:
            return r
    for r in ranges:
        if r.diagnosis_id is None and r.age_group is None and r.gender == gender_norm:
            return r
    for r in ranges:
        if r.diagnosis_id is None and r.age_group is None and r.gender == 'All':
            return r

    # 3. Fallback to any range matching age
    for r in ranges:
        if age_ok(r):
            return r

    return ranges[0]


def get_db_range_bounds(ref_range_obj):
    if ref_range_obj is None: return None, None
    if ref_range_obj.range_type == 'Numeric':
        mn = float(ref_range_obj.min_value) if ref_range_obj.min_value is not None else None
        mx = float(ref_range_obj.max_value) if ref_range_obj.max_value is not None else None
        return mn, mx
    elif ref_range_obj.range_type == 'Text':
        if ref_range_obj.reference_text: return parse_reference_range(ref_range_obj.reference_text)
    return None, None


def classify_dummy_parameter(dummy_param):
    result = dummy_param.dummy_result
    patient_gender = result.patient_gender or 'All'
    patient_age_days = 0
    if result.patient_dob:
        from django.utils import timezone
        patient_age_days = (timezone.now().date() - result.patient_dob).days
    min_val, max_val = None, None
    ref_text = None
    if dummy_param.parameter_id:
        from apps.lab.models import InvestigationParameter
        for ip_id in InvestigationParameter.objects.filter(
            investigation=result.investigation,
            parameter_id=dummy_param.parameter_id,
            is_active=True
        ).values_list('id', flat=True):
            rr = find_best_db_reference_range(ip_id, patient_age_days, patient_gender)
            if rr:
                min_val, max_val = get_db_range_bounds(rr)
                ref_text = rr.reference_text
                break
    if min_val is None and max_val is None and dummy_param.reference_range:
        min_val, max_val = parse_reference_range(dummy_param.reference_range)
        if not ref_text:
            ref_text = dummy_param.reference_range
    return classify_result(dummy_param.result_value, min_val, max_val, ref_text=ref_text), min_val, max_val


def get_overall_result_status(parameter_statuses):
    statuses = set(s for s in parameter_statuses if s != STATUS_NON_NUMERIC)
    if not statuses: return STATUS_NON_NUMERIC
    if STATUS_ABOVE in statuses and STATUS_BELOW in statuses: return 'MIXED'
    if STATUS_ABOVE in statuses: return STATUS_ABOVE
    if STATUS_BELOW in statuses: return STATUS_BELOW
    return STATUS_NORMAL


def classify_service_request_result(sr_result):
    from django.utils import timezone
    patient = sr_result.sr_investigation.service_request.patient
    patient_gender = patient.gender or 'All'
    patient_age_days = 0
    if patient.dob:
        patient_age_days = (timezone.now().date() - patient.dob).days

    # Retrieve primary diagnosis (sort_order=0)
    sr = sr_result.sr_investigation.service_request
    primary_sr_diag = sr.diagnoses.order_by('sort_order').filter(diagnosis__isnull=False).first()
    diagnosis_id = primary_sr_diag.diagnosis_id if primary_sr_diag else None

    rr = find_best_db_reference_range(
        sr_result.investigation_parameter_id,
        patient_age_days,
        patient_gender,
        diagnosis_id=diagnosis_id
    )
    min_val, max_val = get_db_range_bounds(rr)
    ref_text = rr.reference_text if rr else None

    if min_val is None and max_val is None and sr_result.investigation_parameter.reference_range:
        min_val, max_val = parse_reference_range(sr_result.investigation_parameter.reference_range)
        if not ref_text:
            ref_text = sr_result.investigation_parameter.reference_range

    status = classify_result(sr_result.result_value, min_val, max_val, ref_text=ref_text)
    sr_result.status = status
    sr_result.applied_reference_range = rr
    sr_result.save(update_fields=['status', 'applied_reference_range'])
    return status


def update_service_request_investigation_status(sr_investigation):
    results = sr_investigation.results.all()
    statuses = [r.status for r in results if r.status]
    
    if not statuses:
        for r in results:
            statuses.append(classify_service_request_result(r))
            
    overall = get_overall_result_status(statuses)
    
    if overall in (STATUS_ABOVE, STATUS_BELOW, 'MIXED'):
        sr_investigation.result_status = 'ABNORMAL'
    elif overall == STATUS_NORMAL:
        sr_investigation.result_status = 'NORMAL'
    else:
        sr_investigation.result_status = None
        
    sr_investigation.save(update_fields=['result_status'])
    return sr_investigation.result_status
