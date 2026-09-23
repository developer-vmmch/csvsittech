import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404

from apps.lab.models import (
    ServiceRequest,
    ServiceRequestInvestigation,
    ServiceRequestResult,
    InvestigationParameter,
    ParameterReferenceRange,
    PatientInvestigationOrder,
    PatientInvestigationResult,
)
from apps.lab.services.eligibility_engine import calculate_patient_age
from apps.lab.services.result_classifier import (
    find_best_db_reference_range,
    classify_result,
    get_db_range_bounds,
    STATUS_NORMAL,
    STATUS_BELOW,
    STATUS_ABOVE,
)

logger = logging.getLogger(__name__)


def get_evaluated_results_for_sr(sr):
    """
    Evaluates and compiles results for a ServiceRequest across all its investigations.
    Dynamically resolves reference ranges based on patient gender, age, and primary diagnosis.
    """
    patient = sr.patient
    p_gender = patient.gender or 'All'
    age_info = calculate_patient_age(
        dob=patient.dob,
        ref_date=sr.request_date,
        age_years=patient.age_years,
        age_months=patient.age_months,
        age_days=patient.age_days
    )
    p_age_days = age_info['total_days']

    # Get Primary Diagnosis
    primary_diag = None
    sr_diag = sr.diagnoses.order_by('sort_order').first()
    if sr_diag and sr_diag.diagnosis:
        primary_diag = sr_diag.diagnosis
    elif hasattr(patient, 'visits') and patient.visits.exists():
        v = patient.visits.filter(visit_no=sr.visit_no).first() or patient.visits.first()
        vd = v.diagnoses.first()
        if vd and vd.diagnosis:
            primary_diag = vd.diagnosis

    investigation_reports = []

    for sri in sr.investigations.filter(is_removed=False).select_related('investigation'):
        inv = sri.investigation
        inv_params = InvestigationParameter.objects.filter(
            investigation=inv,
            is_active=True
        ).select_related('parameter').order_by('display_order', 'id')

        # Existing saved results for this investigation
        existing_results = {
            r.investigation_parameter_id: r
            for r in sri.results.all().select_related('applied_reference_range')
        }

        parameter_rows = []

        for ip in inv_params:
            res_obj = existing_results.get(ip.id)
            val = res_obj.result_value if res_obj else ''

            # Dynamic Reference Range Selection from DB
            db_range = find_best_db_reference_range(
                investigation_parameter_id=ip.id,
                patient_age_days=p_age_days,
                patient_gender=p_gender,
                diagnosis_id=primary_diag.id if primary_diag else None
            )

            # Determine range display and bounds
            min_val, max_val = None, None
            ref_display = '-'
            unit = ip.unit or ''

            if db_range:
                unit = db_range.unit or unit
                if db_range.range_type == 'Numeric':
                    min_val = float(db_range.min_value) if db_range.min_value is not None else None
                    max_val = float(db_range.max_value) if db_range.max_value is not None else None
                    if min_val is not None and max_val is not None:
                        ref_display = f"{min_val} – {max_val}"
                    elif min_val is not None:
                        ref_display = f">= {min_val}"
                    elif max_val is not None:
                        ref_display = f"<= {max_val}"
                elif db_range.reference_text:
                    ref_display = db_range.reference_text
            elif ip.reference_range:
                ref_display = ip.reference_range
                min_val = float(ip.critical_low) if ip.critical_low else None
                max_val = float(ip.critical_high) if ip.critical_high else None

            # Evaluate Flag
            flag = 'Normal'
            if val and str(val).strip():
                c_status = classify_result(
                    str(val).strip(),
                    min_val=min_val,
                    max_val=max_val,
                    ref_text=ref_display
                )
                if c_status == STATUS_BELOW:
                    flag = 'Low'
                elif c_status == STATUS_ABOVE:
                    flag = 'High'
                else:
                    flag = 'Normal'

            parameter_rows.append({
                'parameter_id': ip.id,
                'parameter_name': ip.name or (ip.parameter.name if ip.parameter else f"Param {ip.code}"),
                'code': ip.code,
                'result_value': val or '—',
                'unit': unit,
                'reference_range': ref_display,
                'flag': flag,
                'remarks': res_obj.remarks if res_obj else '',
            })

        investigation_reports.append({
            'investigation': inv,
            'status': sri.status,
            'result_status': sri.result_status or 'Pending',
            'parameters': parameter_rows
        })

    return {
        'patient': patient,
        'age_display': age_info['display'],
        'service_request': sr,
        'primary_diagnosis': primary_diag,
        'department': sr.department,
        'investigations': investigation_reports
    }


@login_required
def lab_result_detail_view(request, pk):
    """
    Renders the clinical lab result view for a ServiceRequest.
    """
    sr = get_object_or_404(ServiceRequest.objects.select_related('patient', 'department'), pk=pk)
    report_data = get_evaluated_results_for_sr(sr)
    return render(request, 'lab/orders/result_view.html', report_data)


@login_required
def lab_result_print_view(request, pk):
    """
    Renders a clean printable laboratory result report.
    """
    sr = get_object_or_404(ServiceRequest.objects.select_related('patient', 'department'), pk=pk)
    report_data = get_evaluated_results_for_sr(sr)
    return render(request, 'lab/orders/result_print.html', report_data)
