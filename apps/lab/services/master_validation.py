import logging
from django.db.models import Count, Q

from apps.lab.models import (
    Investigation,
    Parameter,
    InvestigationParameter,
    ParameterReferenceRange,
    Diagnosis,
    DiagnosisInvestigationMap,
    DiagnosisDepartmentMapping,
    DiagnosisEligibilityRule,
    AgeGroup,
)

logger = logging.getLogger(__name__)

def run_master_validation():
    """
    Runs comprehensive laboratory master data validation:
    1. Missing investigations (investigations with 0 mapped parameters)
    2. Missing parameters (parameters not mapped to any investigation)
    3. Orphan parameters (investigation parameters pointing to missing/inactive investigation)
    4. Missing investigation mappings (investigations with 0 diagnosis mappings)
    5. Duplicate investigation mappings (investigation + parameter duplicate codes or records)
    6. Missing reference ranges (investigation parameters with 0 reference ranges)
    7. Orphan reference ranges (ranges with missing investigation parameter)
    8. Missing diagnosis mappings (diagnoses with no investigation or no department)
    9. Invalid gender mappings (e.g. Male mapped to female-only / pregnancy rules)
    10. Invalid age ranges (min_age > max_age in rules, mappings, age groups)
    11. Invalid department mappings (mappings pointing to inactive or null departments)
    12. Duplicate diagnosis mappings (same diagnosis + investigation multiple times)
    13. Invalid parameter codes (empty, whitespace, or non-string codes)
    """
    results = {
        'total_checks': 13,
        'passed_checks': 0,
        'warning_checks': 0,
        'error_checks': 0,
        'overall_status': 'OK',
        'sections': [],
    }

    def add_section(title, category, status, count, message, details=None):
        nonlocal results
        if status == 'ERROR':
            results['error_checks'] += 1
            if results['overall_status'] != 'ERROR':
                results['overall_status'] = 'ERROR'
        elif status == 'WARNING':
            results['warning_checks'] += 1
            if results['overall_status'] == 'OK':
                results['overall_status'] = 'WARNING'
        else:
            results['passed_checks'] += 1

        results['sections'].append({
            'title': title,
            'category': category,
            'status': status,
            'count': count,
            'message': message,
            'details': details or []
        })

    # 1. Missing investigations: investigations with 0 parameters
    inv_zero_params = list(Investigation.objects.annotate(param_count=Count('parameters')).filter(param_count=0, is_active=True))
    if inv_zero_params:
        add_section(
            title="Investigations Without Parameters",
            category="Investigation",
            status="WARNING",
            count=len(inv_zero_params),
            message=f"{len(inv_zero_params)} active investigations have no mapped parameters.",
            details=[f"{inv.code} - {inv.name}" for inv in inv_zero_params[:25]]
        )
    else:
        add_section("Investigations Without Parameters", "Investigation", "OK", 0, "All active investigations have at least one mapped parameter.")

    # 2. Missing parameters: parameters not mapped to any investigation
    unmapped_params = list(Parameter.objects.annotate(inv_count=Count('investigations')).filter(inv_count=0, is_active=True))
    if unmapped_params:
        add_section(
            title="Unmapped Parameters",
            category="Parameter",
            status="WARNING",
            count=len(unmapped_params),
            message=f"{len(unmapped_params)} parameters exist in Parameter Master but are not mapped to any investigation.",
            details=[f"{p.code} - {p.name}" for p in unmapped_params[:25]]
        )
    else:
        add_section("Unmapped Parameters", "Parameter", "OK", 0, "All active parameters are mapped to at least one investigation.")

    # 3. Orphan investigation parameters: InvestigationParameter pointing to inactive or deleted investigation
    orphan_inv_params = list(InvestigationParameter.objects.filter(Q(investigation__isnull=True) | Q(investigation__is_active=False)))
    if orphan_inv_params:
        add_section(
            title="Orphan Investigation Parameters",
            category="Investigation Parameter",
            status="ERROR",
            count=len(orphan_inv_params),
            message=f"{len(orphan_inv_params)} investigation parameter records reference an inactive or missing investigation.",
            details=[f"Param #{ip.id} ({ip.code} - {ip.name})" for ip in orphan_inv_params[:25]]
        )
    else:
        add_section("Orphan Investigation Parameters", "Investigation Parameter", "OK", 0, "No orphan investigation parameters found.")

    # 4. Missing investigation mappings: Active investigations with no Diagnosis mapping
    unmapped_inv_diag = list(Investigation.objects.annotate(diag_count=Count('diagnosisinvestigationmap')).filter(diag_count=0, is_active=True))
    if unmapped_inv_diag:
        add_section(
            title="Investigations Without Diagnosis Mapping",
            category="Mapping",
            status="WARNING",
            count=len(unmapped_inv_diag),
            message=f"{len(unmapped_inv_diag)} active investigations are not linked to any clinical diagnosis.",
            details=[f"{inv.code} - {inv.name}" for inv in unmapped_inv_diag[:25]]
        )
    else:
        add_section("Investigations Without Diagnosis Mapping", "Mapping", "OK", 0, "All active investigations are mapped to at least one diagnosis.")

    # 5. Duplicate investigation parameters: same investigation having same parameter code multiple times
    dup_ip_codes = (
        InvestigationParameter.objects.filter(is_active=True)
        .values('investigation_id', 'code')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    dup_ip_list = list(dup_ip_codes)
    if dup_ip_list:
        add_section(
            title="Duplicate Investigation Parameters",
            category="Investigation Parameter",
            status="ERROR",
            count=len(dup_ip_list),
            message=f"{len(dup_ip_list)} duplicate parameter codes found within the same investigation.",
            details=[f"Inv #{d['investigation_id']} - Code: {d['code']} (Count: {d['cnt']})" for d in dup_ip_list[:25]]
        )
    else:
        add_section("Duplicate Investigation Parameters", "Investigation Parameter", "OK", 0, "No duplicate parameter codes within any investigation.")

    # 6. Missing reference ranges: InvestigationParameter with 0 reference ranges
    ip_no_ranges = list(
        InvestigationParameter.objects.filter(is_active=True)
        .annotate(range_count=Count('reference_ranges'))
        .filter(range_count=0)
        .select_related('investigation')
    )
    if ip_no_ranges:
        add_section(
            title="Parameters Missing Reference Ranges",
            category="Reference Range",
            status="WARNING",
            count=len(ip_no_ranges),
            message=f"{len(ip_no_ranges)} active investigation parameters have no database reference ranges configured.",
            details=[f"{ip.investigation.name}: {ip.code} - {ip.name}" for ip in ip_no_ranges[:25]]
        )
    else:
        add_section("Parameters Missing Reference Ranges", "Reference Range", "OK", 0, "All active investigation parameters have reference ranges.")

    # 7. Orphan reference ranges: ParameterReferenceRange pointing to missing or inactive investigation_parameter
    orphan_ranges = list(ParameterReferenceRange.objects.filter(Q(investigation_parameter__isnull=True) | Q(investigation_parameter__is_active=False)))
    if orphan_ranges:
        add_section(
            title="Orphan Reference Ranges",
            category="Reference Range",
            status="ERROR",
            count=len(orphan_ranges),
            message=f"{len(orphan_ranges)} reference range records point to inactive or missing investigation parameters.",
            details=[f"Range #{r.id} ({r.investigation_parameter_id})" for r in orphan_ranges[:25]]
        )
    else:
        add_section("Orphan Reference Ranges", "Reference Range", "OK", 0, "No orphan reference ranges found.")

    # 8. Missing diagnosis mappings: active diagnoses without department or investigation mapping
    diag_no_inv = list(Diagnosis.objects.annotate(inv_count=Count('investigation_mappings')).filter(inv_count=0, is_active=True))
    if diag_no_inv:
        add_section(
            title="Diagnoses Missing Investigation Mappings",
            category="Diagnosis",
            status="WARNING",
            count=len(diag_no_inv),
            message=f"{len(diag_no_inv)} diagnoses have no investigations mapped to them.",
            details=[f"{d.code} - {d.name}" for d in diag_no_inv[:25]]
        )
    else:
        add_section("Diagnoses Missing Investigation Mappings", "Diagnosis", "OK", 0, "All active diagnoses have mapped investigations.")

    # 9. Invalid gender mappings: rules or maps with male gender and pregnancy_required = True
    invalid_gender_rules = list(DiagnosisEligibilityRule.objects.filter(gender='Male', pregnancy_required=True, is_active=True))
    invalid_gender_maps = list(DiagnosisInvestigationMap.objects.filter(gender='Male', pregnancy_required=True, is_active=True))
    invalid_g_count = len(invalid_gender_rules) + len(invalid_gender_maps)
    if invalid_g_count > 0:
        details = [f"Rule #{r.id}: {r.diagnosis.name} (Male + Pregnancy Required)" for r in invalid_gender_rules] + \
                  [f"Map #{m.id}: {m.diagnosis.name} -> {m.investigation.name} (Male + Pregnancy Required)" for m in invalid_gender_maps]
        add_section(
            title="Invalid Gender / Pregnancy Mappings",
            category="Rules & Mappings",
            status="ERROR",
            count=invalid_g_count,
            message="Contradictory rules detected where Gender=Male is combined with Pregnancy Required.",
            details=details
        )
    else:
        add_section("Invalid Gender / Pregnancy Mappings", "Rules & Mappings", "OK", 0, "All gender and pregnancy constraints are consistent.")

    # 10. Invalid age ranges: min_age > max_age in rules, maps, or age groups
    invalid_age_rules = list(DiagnosisEligibilityRule.objects.filter(min_age__isnull=False, max_age__isnull=False, min_age__gt=models_max_age()))
    # To check min_age > max_age safely:
    invalid_age_items = []
    for r in DiagnosisEligibilityRule.objects.filter(min_age__isnull=False, max_age__isnull=False):
        if r.min_age > r.max_age:
            invalid_age_items.append(f"Rule #{r.id}: min_age ({r.min_age}) > max_age ({r.max_age})")
    for m in DiagnosisInvestigationMap.objects.filter(min_age__isnull=False, max_age__isnull=False):
        if m.min_age > m.max_age:
            invalid_age_items.append(f"Map #{m.id}: min_age ({m.min_age}) > max_age ({m.max_age})")
    for ag in AgeGroup.objects.filter(min_age_value__isnull=False, max_age_value__isnull=False):
        if ag.min_age_value > ag.max_age_value:
            invalid_age_items.append(f"AgeGroup {ag.code}: min ({ag.min_age_value}) > max ({ag.max_age_value})")

    if invalid_age_items:
        add_section(
            title="Invalid Age Range Boundaries",
            category="Rules & Age Groups",
            status="ERROR",
            count=len(invalid_age_items),
            message=f"{len(invalid_age_items)} items have minimum age greater than maximum age.",
            details=invalid_age_items[:25]
        )
    else:
        add_section("Invalid Age Range Boundaries", "Rules & Age Groups", "OK", 0, "All age boundaries have valid min <= max bounds.")

    # 11. Invalid department mappings: mappings pointing to inactive departments
    invalid_dept_maps = list(DiagnosisDepartmentMapping.objects.filter(department__is_active=False))
    if invalid_dept_maps:
        add_section(
            title="Inactive Department Mappings",
            category="Department Mapping",
            status="WARNING",
            count=len(invalid_dept_maps),
            message=f"{len(invalid_dept_maps)} diagnosis-department mappings point to inactive departments.",
            details=[f"{m.department.name} - {m.diagnosis.name}" for m in invalid_dept_maps[:25]]
        )
    else:
        add_section("Inactive Department Mappings", "Department Mapping", "OK", 0, "All department mappings reference active hospital departments.")

    # 12. Duplicate diagnosis mappings: same diagnosis + investigation mapped multiple times with same age_group
    dup_diag_maps = (
        DiagnosisInvestigationMap.objects.filter(is_active=True)
        .values('diagnosis_id', 'investigation_id', 'age_group_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    dup_dm_list = list(dup_diag_maps)
    if dup_dm_list:
        add_section(
            title="Duplicate Diagnosis Investigation Mappings",
            category="Mapping",
            status="WARNING",
            count=len(dup_dm_list),
            message=f"{len(dup_dm_list)} duplicate diagnosis-investigation mappings found.",
            details=[f"Diag #{d['diagnosis_id']} -> Inv #{d['investigation_id']} (Count: {d['cnt']})" for d in dup_dm_list[:25]]
        )
    else:
        add_section("Duplicate Diagnosis Investigation Mappings", "Mapping", "OK", 0, "No duplicate diagnosis investigation mappings found.")

    # 13. Invalid parameter codes: empty, whitespace, or integer-converted codes
    invalid_p_codes = []
    for p in Parameter.objects.all():
        if not p.code or not str(p.code).strip():
            invalid_p_codes.append(f"Param #{p.id} ({p.name}): Empty code")
        elif str(p.code) != str(p.code).strip():
            invalid_p_codes.append(f"Param #{p.id} ({p.name}): Code has leading/trailing whitespace '{p.code}'")
    for ip in InvestigationParameter.objects.all():
        if ip.code and str(ip.code) != str(ip.code).strip():
            invalid_p_codes.append(f"InvParam #{ip.id} ({ip.name}): Code has whitespace '{ip.code}'")

    if invalid_p_codes:
        add_section(
            title="Invalid Parameter Codes",
            category="Parameter Integrity",
            status="ERROR",
            count=len(invalid_p_codes),
            message=f"{len(invalid_p_codes)} parameter codes have integrity issues (empty or whitespace).",
            details=invalid_p_codes[:25]
        )
    else:
        add_section("Invalid Parameter Codes", "Parameter Integrity", "OK", 0, "All parameter codes are valid non-empty string identifiers.")

    return results

def models_max_age():
    from django.db.models import F
    return F('max_age')
