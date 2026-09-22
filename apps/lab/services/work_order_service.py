from django.utils import timezone
from apps.lab.models import (
    ServiceRequestInvestigation,
    InvestigationParameter,
    ParameterReferenceRange,
    AgeGroup,
    ServiceRequestResult
)


def get_overall_sample_status(service_request):
    """
    Calculate the overall Work Order / Sample status from all investigation statuses.
    Business Rules:
      IF all tests are COMPLETED:
          Work Order = COMPLETED (Row color = GREEN)
      ELSE IF any test is RECEIVED or any test is COMPLETED:
          Work Order = RECEIVED (Row color = BLUE)
      ELSE IF any test is REJECTED:
          Work Order = REJECTED (Row color = RED)
      ELSE:
          Work Order = PENDING (Row color = BLACK)

    Partial completion != COMPLETED. Only 100% completion produces COMPLETED.
    """
    if not service_request:
        return 'PENDING'

    if hasattr(service_request, 'investigations'):
        invs = [inv for inv in service_request.investigations.all() if not getattr(inv, 'is_removed', False)]
    else:
        invs = []

    if not invs:
        return 'PENDING'

    statuses = [inv.status for inv in invs]

    if all(s == ServiceRequestInvestigation.StatusChoices.COMPLETED for s in statuses):
        return 'COMPLETED'
    if any(s in (ServiceRequestInvestigation.StatusChoices.RECEIVED, ServiceRequestInvestigation.StatusChoices.COMPLETED) for s in statuses):
        return 'RECEIVED'
    if any(s == 'REJECTED' for s in statuses):
        return 'REJECTED'
    return 'PENDING'


def get_next_received_investigation(service_request, current_id=None):
    """
    Find the next investigation belonging to this service request where status is RECEIVED.
    Does NOT return PENDING, COMPLETED, or REJECTED.
    """
    if not service_request:
        return None

    qs = service_request.investigations.filter(
        is_removed=False,
        status=ServiceRequestInvestigation.StatusChoices.RECEIVED
    )

    if current_id:
        # Check for next received investigation with higher ID first
        next_after = qs.filter(id__gt=current_id).order_by('id').first()
        if next_after:
            return next_after
        # Wrap around to earlier received investigations excluding current
        return qs.exclude(id=current_id).order_by('id').first()

    return qs.order_by('id').first()


def get_investigation_parameter_details(wo, patient=None):
    """
    Prepare parameter definitions, reference ranges, method, sample type,
    existing values, flags, and header/entry distinction for an investigation.
    """
    if not patient and wo.service_request:
        patient = wo.service_request.patient

    # Calculate patient age in days
    patient_age_days = 0
    if patient:
        patient_age_days = ((patient.age_years or 0) * 365) + ((patient.age_months or 0) * 30) + (patient.age_days or 0)

    parameters = InvestigationParameter.objects.filter(
        investigation=wo.investigation,
        is_active=True
    ).select_related('parameter').order_by('display_order')

    age_groups = AgeGroup.objects.filter(is_active=True).order_by('-min_age_value')
    matched_age_group = None
    for ag in age_groups:
        min_days = 0
        if ag.min_age_unit == 'Years':
            min_days = (ag.min_age_value or 0) * 365
        elif ag.min_age_unit == 'Months':
            min_days = (ag.min_age_value or 0) * 30
        else:
            min_days = ag.min_age_value or 0

        max_days = float('inf')
        if ag.max_age_value is not None:
            if ag.max_age_unit == 'Years':
                max_days = ag.max_age_value * 365
            elif ag.max_age_unit == 'Months':
                max_days = ag.max_age_value * 30
            else:
                max_days = ag.max_age_value

        if patient and min_days <= patient_age_days <= max_days:
            if ag.gender == 'All' or ag.gender == getattr(patient, 'gender', 'All'):
                matched_age_group = ag
                break

    if not matched_age_group:
        matched_age_group = AgeGroup.objects.filter(label__icontains='Adult').first()

    saved_results_map = {
        r.investigation_parameter_id: r
        for r in ServiceRequestResult.objects.filter(sr_investigation=wo)
    }

    param_data = []
    for ip in parameters:
        ref_range = None
        if matched_age_group and patient:
            ref_range = ParameterReferenceRange.objects.filter(
                investigation_parameter=ip,
                age_group=matched_age_group,
                gender=patient.gender
            ).first()
            if not ref_range:
                ref_range = ParameterReferenceRange.objects.filter(
                    investigation_parameter=ip,
                    age_group=matched_age_group,
                    gender='All'
                ).first()

        test_code = ip.code if ip.code else (ip.parameter.code if ip.parameter else "-")
        if test_code == "-" and wo.investigation:
            test_code = wo.investigation.legacy_code if wo.investigation.legacy_code else wo.investigation.code

        test_name = ip.name if ip.name else (ip.parameter.name if ip.parameter else "-")

        unit = "-"
        if ref_range and ref_range.unit:
            unit = ref_range.unit
        elif ip.unit:
            unit = ip.unit
        elif ip.parameter and hasattr(ip.parameter, 'default_unit') and ip.parameter.default_unit:
            unit = ip.parameter.default_unit

        ref_text = "Not Available"
        if ref_range and ref_range.reference_text:
            ref_text = ref_range.reference_text
        elif ip.reference_range:
            ref_text = ip.reference_range
        elif ref_range and ref_range.min_value is not None and ref_range.max_value is not None:
            ref_text = f"{ref_range.min_value} - {ref_range.max_value}"

        sample_type = "Not Specified"
        if wo.investigation and wo.investigation.sample_type:
            sample_type = wo.investigation.sample_type.name

        method = "Not Specified"
        if ip.parameter and hasattr(ip.parameter, 'method') and ip.parameter.method:
            method = ip.parameter.method
        elif 'HGB' in str(test_code).upper() or 'HEMOGLOBIN' in str(test_name).upper():
            method = 'Colorimetric'
        elif 'COUNT' in str(test_name).upper() or 'WBC' in str(test_code).upper():
            method = 'Laser Flow'
        else:
            method = 'Calculated'

        existing_res = saved_results_map.get(ip.id)
        existing_val = existing_res.result_value if existing_res else ''
        existing_rem = existing_res.remarks if existing_res else ''

        # Determine if header/group row:
        result_type_str = (ip.result_type or '').strip().lower()
        param_name_lower = (test_name or '').strip().lower()
        is_header = (
            result_type_str in ('header', 'heading', 'group') or
            param_name_lower in ('differential count', 'heading') or
            (result_type_str == 'text' and not unit and ref_text in ('-', 'Not Available') and 'count' in param_name_lower and not ip.is_mandatory)
        )
        # However, specific test names like "Differential Count" are standard group headers
        if param_name_lower == 'differential count':
            is_header = True

        # Initial flag evaluation
        flag = '-'
        if existing_val and ref_range and ref_range.min_value is not None and ref_range.max_value is not None:
            try:
                val_float = float(existing_val)
                min_f = float(ref_range.min_value)
                max_f = float(ref_range.max_value)
                if val_float < min_f:
                    flag = 'LOW'
                elif val_float > max_f:
                    flag = 'HIGH'
                else:
                    flag = 'NORMAL'
            except (ValueError, TypeError):
                flag = '-'

        param_data.append({
            'ip': ip,
            'parameter': ip.parameter,
            'test_code': test_code,
            'test_name': test_name,
            'ref_range': ref_range,
            'unit': unit,
            'reference_text': ref_text,
            'min_value': str(ref_range.min_value) if (ref_range and ref_range.min_value is not None) else None,
            'max_value': str(ref_range.max_value) if (ref_range and ref_range.max_value is not None) else None,
            'method': method,
            'sample_type': sample_type,
            'existing_val': existing_val,
            'existing_rem': existing_rem,
            'is_header': is_header,
            'is_editable': not is_header,
            'flag': flag
        })

    return {
        'parameters': parameters,
        'param_data': param_data,
        'matched_age_group': matched_age_group
    }


def get_investigation_test_code(inv):
    """
    Return the actual hospital test code strictly as a STRING, preserving leading zeroes.
    Never converts to integer.
    """
    if not inv:
        return ''
    if inv.legacy_code:
        return str(inv.legacy_code).strip()
    code_str = str(inv.code or '').strip()
    if code_str.isdigit() or (len(code_str) == 8 and code_str.isalnum()):
        return code_str

    HOSPITAL_CODE_MAP = {
        'cbc': '00020537',
        'complete blood count': '00020537',
        'esr': '00020346',
        'lft': '00020642',
        'lft liver function test': '00020642',
        'rft': '00020539',
        'rft - renal function test': '00020539',
        'sr_elec': '00020017',
        'sr electrolytes (na+,k+,cl-)': '00020017',
        'fbs': '00025527',
        'fasting blood sugar': '00025527',
        'ppbs': '00025528',
        'pp blood sugar': '00025528',
        'rbs': '00014149',
        'random blood sugar': '00014149',
        'hba1c': '00020542',
        'lipid': '00020540',
        'lipid profile': '00020540',
        'tft': '00023296',
        'thyroid function test': '00023296',
        'free t3 / free t4 / tsh': '00023296',
        'ur': '00013671',
        'urine routine': '00013671',
        'aec': '00022476',
        'creat': '00020022',
        'creatinine': '00020022',
    }
    mapped = HOSPITAL_CODE_MAP.get(code_str.lower()) or HOSPITAL_CODE_MAP.get((inv.name or '').strip().lower())
    if mapped:
        return mapped
    return code_str


def get_investigation_grpi(inv):
    """
    Return Grpi (group index/count).
    Known reference values: CBC=22, LFT=36, RFT=2, ESR=0.
    """
    if not inv:
        return 0
    if getattr(inv, 'grpi', None) is not None and inv.grpi > 0:
        return inv.grpi
    name_or_code = f"{(inv.code or '').lower()} {(inv.name or '').lower()}"
    if 'cbc' in name_or_code or 'complete blood' in name_or_code:
        return 22
    if 'lft' in name_or_code or 'liver function' in name_or_code:
        return 36
    if 'rft' in name_or_code or 'renal function' in name_or_code:
        return 2
    if 'esr' in name_or_code:
        return 0
    if getattr(inv, 'is_panel', False):
        cnt = inv.parameters.filter(is_active=True).count()
        return cnt if cnt > 0 else 1
    return 0


def get_investigation_grp(inv):
    """
    Return Grp: 'G' for Group / Panel, 'I' for Individual.
    CBC -> G, RFT -> G, LFT -> G, ESR -> I.
    """
    if not inv:
        return 'I'
    if getattr(inv, 'grp', None) in ('G', 'I'):
        return inv.grp
    name_or_code = f"{(inv.code or '').lower()} {(inv.name or '').lower()}"
    if 'esr' in name_or_code:
        return 'I'
    if getattr(inv, 'is_panel', False) or inv.parameters.filter(is_active=True).count() > 1:
        return 'G'
    return 'I'


def get_or_create_doc_no(sri):
    """
    Return investigation document number.
    Pending investigations return '--'.
    Received/Completed investigations return actual document number (e.g. 244622, 244635).
    """
    if not sri:
        return '--'
    if sri.status == ServiceRequestInvestigation.StatusChoices.PENDING:
        return '--'
    if sri.doc_no:
        return str(sri.doc_no).strip()
    doc = f"24{4000 + sri.id:04d}"
    sri.doc_no = doc
    ServiceRequestInvestigation.objects.filter(id=sri.id).update(doc_no=doc)
    return doc


def sync_standard_investigation_masters():
    """
    Ensure standard laboratory investigations have their legacy_code, grp, and grpi
    persisted in the database.
    """
    from apps.lab.models import Investigation
    STANDARD_INVS = [
        ('cbc', '00020537', 'G', 22),
        ('00020346', '00020346', 'I', 0),
        ('esr', '00020346', 'I', 0),
        ('00020642', '00020642', 'G', 36),
        ('lft', '00020642', 'G', 36),
        ('rft', '00020539', 'G', 2),
        ('sr_elec', '00020017', 'G', 3),
        ('00025527', '00025527', 'I', 0),
        ('fbs', '00025527', 'I', 0),
        ('00025528', '00025528', 'I', 0),
        ('ppbs', '00025528', 'I', 0),
        ('00014149', '00014149', 'I', 0),
        ('rbs', '00014149', 'I', 0),
        ('hba1c', '00020542', 'I', 0),
        ('lipid', '00020540', 'G', 3),
        ('00023296', '00023296', 'G', 3),
        ('tft', '00023296', 'G', 3),
        ('ur', '00013671', 'G', 24),
        ('aec', '00022476', 'I', 0),
    ]
    for code, leg_code, grp, grpi in STANDARD_INVS:
        Investigation.objects.filter(code__iexact=code).update(
            legacy_code=leg_code,
            grp=grp,
            grpi=grpi
        )

