import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.contrib import messages

from apps.lab.models import (
    Investigation,
    Parameter,
    InvestigationParameter,
    ParameterReferenceRange,
    Diagnosis,
    DiagnosisEligibilityRule,
    DiagnosisInvestigationMap,
    DiagnosisDepartmentMapping,
    AgeGroup,
    LabDepartment,
    SampleType,
)
from apps.patients.models import Department as HospitalDepartment
from apps.lab.services.master_validation import run_master_validation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. LAB MASTER HUB
# ---------------------------------------------------------------------------

@login_required
def lab_master_hub(request):
    """
    Central hub for Lab Master with real-time statistics and quick navigation.
    """
    inv_count = Investigation.objects.filter(is_active=True).count()
    param_count = Parameter.objects.filter(is_active=True).count()
    inv_param_count = InvestigationParameter.objects.filter(is_active=True).count()
    range_count = ParameterReferenceRange.objects.filter(is_active=True).count()
    diag_count = Diagnosis.objects.filter(is_active=True).count()
    diag_inv_map_count = DiagnosisInvestigationMap.objects.filter(is_active=True).count()
    diag_dept_map_count = DiagnosisDepartmentMapping.objects.filter(status='Active').count()
    age_group_count = AgeGroup.objects.filter(is_active=True).count()
    rules_count = DiagnosisEligibilityRule.objects.filter(is_active=True).count()

    validation_summary = run_master_validation()

    context = {
        'inv_count': inv_count,
        'param_count': param_count,
        'inv_param_count': inv_param_count,
        'range_count': range_count,
        'diag_count': diag_count,
        'diag_inv_map_count': diag_inv_map_count,
        'diag_dept_map_count': diag_dept_map_count,
        'age_group_count': age_group_count,
        'rules_count': rules_count,
        'validation_summary': validation_summary,
    }
    return render(request, 'lab/master/lab_master_hub.html', context)


# ---------------------------------------------------------------------------
# 2. INVESTIGATIONS MASTER
# ---------------------------------------------------------------------------

class MasterInvestigationListView(LoginRequiredMixin, ListView):
    model = Investigation
    template_name = 'lab/master/master_investigation_list.html'
    context_object_name = 'investigations'
    paginate_by = 25

    def get_queryset(self):
        qs = Investigation.objects.all().select_related('department', 'sample_type').annotate(
            param_count=Count('parameters')
        ).order_by('display_order', 'name')

        search = self.request.GET.get('search', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        status = self.request.GET.get('status', '').strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(category__icontains=search) |
                Q(specimen__icontains=search)
            )
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = LabDepartment.objects.filter(is_active=True).order_by('name')
        ctx['sample_types'] = SampleType.objects.filter(is_active=True).order_by('name')
        ctx['total_count'] = self.get_queryset().count()
        return ctx


class MasterInvestigationDetailView(LoginRequiredMixin, DetailView):
    model = Investigation
    template_name = 'lab/master/master_investigation_detail.html'
    context_object_name = 'investigation'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['parameters'] = (
            InvestigationParameter.objects
            .filter(investigation=self.object)
            .select_related('parameter')
            .order_by('display_order', 'id')
        )
        ctx['reference_ranges'] = (
            ParameterReferenceRange.objects
            .filter(investigation_parameter__investigation=self.object)
            .select_related('investigation_parameter', 'age_group', 'diagnosis')
            .order_by('investigation_parameter', 'id')
        )
        ctx['diagnosis_mappings'] = (
            DiagnosisInvestigationMap.objects
            .filter(investigation=self.object)
            .select_related('diagnosis', 'age_group', 'department')
            .order_by('diagnosis__name')
        )
        return ctx


@login_required
@require_POST
def api_master_investigation_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    code = str(data.get('code', '')).strip()
    name = str(data.get('name', '')).strip()

    if not code or not name:
        return JsonResponse({'success': False, 'message': 'Code and Name are required.'}, status=400)

    dept_id = data.get('department_id') or None
    sample_type_id = data.get('sample_type_id') or None
    category = str(data.get('category', '')).strip() or None
    specimen = str(data.get('specimen', '')).strip() or None
    method = str(data.get('method', '')).strip() or None
    display_order = int(data.get('display_order') or 0)
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        inv = get_object_or_404(Investigation, pk=rec_id)
        if Investigation.objects.filter(code=code).exclude(pk=rec_id).exists():
            return JsonResponse({'success': False, 'message': f"Investigation with code '{code}' already exists."}, status=400)
        inv.code = code
        inv.name = name
    else:
        if Investigation.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f"Investigation with code '{code}' already exists."}, status=400)
        inv = Investigation(code=code, name=name)

    inv.department_id = dept_id
    inv.sample_type_id = sample_type_id
    inv.category = category
    inv.specimen = specimen
    inv.method = method
    inv.display_order = display_order
    inv.is_active = is_active
    inv.save()

    return JsonResponse({
        'success': True,
        'message': 'Investigation saved successfully.',
        'data': {
            'id': inv.id,
            'code': inv.code,
            'name': inv.name,
            'is_active': inv.is_active
        }
    })


@login_required
@require_POST
def api_master_investigation_toggle_status(request, pk):
    inv = get_object_or_404(Investigation, pk=pk)
    inv.is_active = not inv.is_active
    inv.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': inv.is_active})


# ---------------------------------------------------------------------------
# 3. PARAMETERS MASTER (PRESERVES STRING CODES e.g. "00022681")
# ---------------------------------------------------------------------------

class MasterParameterListView(LoginRequiredMixin, ListView):
    model = Parameter
    template_name = 'lab/master/master_parameter_list.html'
    context_object_name = 'parameters'
    paginate_by = 30

    def get_queryset(self):
        qs = Parameter.objects.all().order_by('code', 'name')
        search = self.request.GET.get('search', '').strip()
        data_type = self.request.GET.get('data_type', '').strip()
        status = self.request.GET.get('status', '').strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(default_unit__icontains=search)
            )
        if data_type:
            qs = qs.filter(data_type=data_type)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_count'] = self.get_queryset().count()
        return ctx


@login_required
@require_POST
def api_master_parameter_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    # Strictly preserve code as a string!
    raw_code = data.get('code')
    if raw_code is None or str(raw_code).strip() == '':
        return JsonResponse({'success': False, 'message': 'Parameter code is required.'}, status=400)
    code = str(raw_code).strip()

    name = str(data.get('name', '')).strip()
    if not name:
        return JsonResponse({'success': False, 'message': 'Parameter name is required.'}, status=400)

    data_type = data.get('data_type') or 'NUMERIC'
    default_unit = str(data.get('default_unit', '')).strip() or None
    result_type = str(data.get('result_type', 'Numeric')).strip()
    default_decimal_places = int(data.get('default_decimal_places') or 2)
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        param = get_object_or_404(Parameter, pk=rec_id)
        if Parameter.objects.filter(code=code).exclude(pk=rec_id).exists():
            return JsonResponse({'success': False, 'message': f"Parameter code '{code}' already exists."}, status=400)
        param.code = code
        param.name = name
    else:
        if Parameter.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f"Parameter code '{code}' already exists."}, status=400)
        param = Parameter(code=code, name=name)

    param.data_type = data_type
    param.default_unit = default_unit
    param.result_type = result_type
    param.default_decimal_places = default_decimal_places
    param.is_active = is_active
    param.save()

    return JsonResponse({
        'success': True,
        'message': 'Parameter saved successfully.',
        'data': {
            'id': param.id,
            'code': param.code,
            'name': param.name,
            'unit': param.default_unit,
            'is_active': param.is_active
        }
    })


# ---------------------------------------------------------------------------
# 4. INVESTIGATION PARAMETER MAPPING
# ---------------------------------------------------------------------------

class MasterInvestigationParameterMappingView(LoginRequiredMixin, ListView):
    model = InvestigationParameter
    template_name = 'lab/master/master_investigation_parameter_mapping.html'
    context_object_name = 'mappings'
    paginate_by = 30

    def get_queryset(self):
        qs = InvestigationParameter.objects.all().select_related('investigation', 'parameter').order_by(
            'investigation__name', 'display_order', 'id'
        )
        inv_id = self.request.GET.get('investigation')
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '').strip()

        if inv_id:
            qs = qs.filter(investigation_id=inv_id)
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(investigation__name__icontains=search) |
                Q(investigation__code__icontains=search)
            )
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['investigations'] = Investigation.objects.filter(is_active=True).order_by('name')
        ctx['parameters'] = Parameter.objects.filter(is_active=True).order_by('name')
        ctx['selected_inv'] = self.request.GET.get('investigation', '')
        return ctx


@login_required
@require_POST
def api_master_inv_param_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    inv_id = data.get('investigation_id')
    param_id = data.get('parameter_id')

    if not inv_id or not param_id:
        return JsonResponse({'success': False, 'message': 'Investigation and Parameter are required.'}, status=400)

    inv = get_object_or_404(Investigation, pk=inv_id)
    param = get_object_or_404(Parameter, pk=param_id)

    # String code preserved
    code = str(data.get('code') or param.code).strip()
    name = str(data.get('name') or param.name).strip()
    unit = str(data.get('unit') or param.default_unit or '').strip() or None
    result_type = str(data.get('result_type') or param.result_type or 'Numeric').strip()
    display_order = int(data.get('display_order') or 0)
    is_mandatory = str(data.get('is_mandatory', 'false')).lower() in ('true', '1')
    is_calculated = str(data.get('is_calculated', 'false')).lower() in ('true', '1')
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    # Prevent duplicate Investigation + Parameter
    qs = InvestigationParameter.objects.filter(investigation=inv, parameter=param)
    if rec_id:
        qs = qs.exclude(pk=rec_id)
    if qs.exists():
        return JsonResponse({
            'success': False,
            'message': f"Parameter '{param.name}' is already mapped to Investigation '{inv.name}'."
        }, status=400)

    # Prevent duplicate Investigation + Code
    code_qs = InvestigationParameter.objects.filter(investigation=inv, code=code)
    if rec_id:
        code_qs = code_qs.exclude(pk=rec_id)
    if code_qs.exists():
        return JsonResponse({
            'success': False,
            'message': f"Parameter code '{code}' is already used in Investigation '{inv.name}'."
        }, status=400)

    if rec_id:
        ip = get_object_or_404(InvestigationParameter, pk=rec_id)
    else:
        ip = InvestigationParameter(investigation=inv, parameter=param)

    ip.investigation = inv
    ip.parameter = param
    ip.code = code
    ip.name = name
    ip.unit = unit
    ip.result_type = result_type
    ip.display_order = display_order
    ip.is_mandatory = is_mandatory
    ip.is_calculated = is_calculated
    ip.is_active = is_active
    ip.save()

    return JsonResponse({
        'success': True,
        'message': 'Investigation parameter mapping saved.',
        'data': {'id': ip.id, 'code': ip.code, 'name': ip.name}
    })


@login_required
@require_POST
def api_master_inv_param_delete(request, pk):
    ip = get_object_or_404(InvestigationParameter, pk=pk)
    ip.delete()
    return JsonResponse({'success': True, 'message': 'Mapping removed successfully.'})


# ---------------------------------------------------------------------------
# 5. REFERENCE RANGES MASTER
# ---------------------------------------------------------------------------

class MasterReferenceRangeView(LoginRequiredMixin, ListView):
    model = ParameterReferenceRange
    template_name = 'lab/master/master_reference_ranges.html'
    context_object_name = 'reference_ranges'
    paginate_by = 30

    def get_queryset(self):
        qs = (
            ParameterReferenceRange.objects.all()
            .select_related('investigation_parameter__investigation', 'age_group', 'diagnosis')
            .order_by('investigation_parameter__investigation__name', 'investigation_parameter__name', 'id')
        )
        inv_id = self.request.GET.get('investigation')
        gender = self.request.GET.get('gender')
        age_group_id = self.request.GET.get('age_group')
        search = self.request.GET.get('search', '').strip()

        if inv_id:
            qs = qs.filter(investigation_parameter__investigation_id=inv_id)
        if gender and gender in ('All', 'Male', 'Female'):
            qs = qs.filter(gender=gender)
        if age_group_id:
            qs = qs.filter(age_group_id=age_group_id)
        if search:
            qs = qs.filter(
                Q(investigation_parameter__name__icontains=search) |
                Q(investigation_parameter__investigation__name__icontains=search) |
                Q(diagnosis__name__icontains=search) |
                Q(reference_text__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['investigations'] = Investigation.objects.filter(is_active=True).order_by('name')
        ctx['age_groups'] = AgeGroup.objects.filter(is_active=True).order_by('sort_order')
        ctx['diagnoses'] = Diagnosis.objects.filter(is_active=True).order_by('name')
        return ctx


@login_required
@require_POST
def api_master_reference_range_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    ip_id = data.get('investigation_parameter_id')
    if not ip_id:
        return JsonResponse({'success': False, 'message': 'Investigation parameter is required.'}, status=400)

    ip = get_object_or_404(InvestigationParameter, pk=ip_id)
    age_group_id = data.get('age_group_id') or None
    diag_id = data.get('diagnosis_id') or None
    gender = data.get('gender') or 'All'
    range_type = data.get('range_type') or 'Numeric'
    min_val = data.get('min_value')
    max_val = data.get('max_value')
    ref_text = str(data.get('reference_text', '')).strip() or None
    unit = str(data.get('unit', '')).strip() or ip.unit
    method = str(data.get('method', '')).strip() or None
    remarks = str(data.get('remarks', '')).strip() or None
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        rr = get_object_or_404(ParameterReferenceRange, pk=rec_id)
    else:
        # Check duplicate
        dup = ParameterReferenceRange.objects.filter(
            investigation_parameter=ip,
            age_group_id=age_group_id,
            diagnosis_id=diag_id,
            gender=gender
        )
        if dup.exists():
            return JsonResponse({'success': False, 'message': 'A reference range with these exact criteria already exists.'}, status=400)
        rr = ParameterReferenceRange(investigation_parameter=ip)

    rr.age_group_id = age_group_id
    rr.diagnosis_id = diag_id
    rr.gender = gender
    rr.range_type = range_type
    rr.min_value = min_val if min_val not in (None, '') else None
    rr.max_value = max_val if max_val not in (None, '') else None
    rr.reference_text = ref_text
    rr.unit = unit
    rr.method = method
    rr.remarks = remarks
    rr.is_active = is_active
    rr.save()

    return JsonResponse({'success': True, 'message': 'Reference range saved successfully.'})


# ---------------------------------------------------------------------------
# 6. DIAGNOSIS MASTER & ELIGIBILITY RULES
# ---------------------------------------------------------------------------

class MasterDiagnosisListView(LoginRequiredMixin, ListView):
    model = Diagnosis
    template_name = 'lab/master/master_diagnosis_list.html'
    context_object_name = 'diagnoses'
    paginate_by = 30

    def get_queryset(self):
        qs = Diagnosis.objects.all().select_related('department').prefetch_related(
            'eligibility_rules', 'investigation_mappings'
        ).annotate(
            rule_count=Count('eligibility_rules'),
            inv_map_count=Count('investigation_mappings')
        ).order_by('name')

        search = self.request.GET.get('search', '').strip()
        dept_id = self.request.GET.get('department', '').strip()
        gender = self.request.GET.get('gender', '').strip()
        status = self.request.GET.get('status', '').strip()

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(chapter__icontains=search)
            )
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if gender:
            qs = qs.filter(gender_eligibility=gender)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = HospitalDepartment.objects.filter(is_active=True).order_by('name')
        return ctx


@login_required
@require_POST
def api_master_diagnosis_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    code = str(data.get('code', '')).strip()
    name = str(data.get('name', '')).strip()

    if not name:
        return JsonResponse({'success': False, 'message': 'Diagnosis name is required.'}, status=400)

    dept_id = data.get('department_id') or None
    gender_eligibility = data.get('gender_eligibility') or 'All'
    min_age = data.get('min_age') or None
    max_age = data.get('max_age') or None
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        diag = get_object_or_404(Diagnosis, pk=rec_id)
        if code and Diagnosis.objects.filter(code=code).exclude(pk=rec_id).exists():
            return JsonResponse({'success': False, 'message': f"Diagnosis code '{code}' already exists."}, status=400)
    else:
        if code and Diagnosis.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f"Diagnosis code '{code}' already exists."}, status=400)
        diag = Diagnosis()

    diag.code = code or None
    diag.name = name
    diag.department_id = dept_id
    diag.gender_eligibility = gender_eligibility
    diag.min_age = int(min_age) if min_age not in (None, '') else None
    diag.max_age = int(max_age) if max_age not in (None, '') else None
    diag.is_active = is_active
    diag.save()

    return JsonResponse({'success': True, 'message': 'Diagnosis saved successfully.'})


@login_required
def api_master_diagnosis_get_rules(request, pk):
    diag = get_object_or_404(Diagnosis, pk=pk)
    rules = list(diag.eligibility_rules.all().select_related('department').values(
        'id', 'gender', 'min_age', 'max_age', 'department__name', 'department_id',
        'pregnancy_required', 'priority', 'is_active'
    ))
    return JsonResponse({'success': True, 'diagnosis': {'id': diag.id, 'name': diag.name}, 'rules': rules})


@login_required
@require_POST
def api_master_diagnosis_save_rule(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    diag_id = data.get('diagnosis_id')
    diag = get_object_or_404(Diagnosis, pk=diag_id)

    rule_id = data.get('rule_id')
    gender = data.get('gender') or 'All'
    min_age = data.get('min_age')
    max_age = data.get('max_age')
    dept_id = data.get('department_id') or None
    pregnancy_required = str(data.get('pregnancy_required', 'false')).lower() in ('true', '1')
    priority = int(data.get('priority') or 100)
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rule_id:
        rule = get_object_or_404(DiagnosisEligibilityRule, pk=rule_id, diagnosis=diag)
    else:
        rule = DiagnosisEligibilityRule(diagnosis=diag)

    rule.gender = gender
    rule.min_age = int(min_age) if min_age not in (None, '') else None
    rule.max_age = int(max_age) if max_age not in (None, '') else None
    rule.department_id = dept_id
    rule.pregnancy_required = pregnancy_required
    rule.priority = priority
    rule.is_active = is_active
    rule.save()

    return JsonResponse({'success': True, 'message': 'Eligibility rule saved successfully.'})


@login_required
@require_POST
def api_master_diagnosis_delete_rule(request, pk):
    rule = get_object_or_404(DiagnosisEligibilityRule, pk=pk)
    rule.delete()
    return JsonResponse({'success': True, 'message': 'Rule deleted successfully.'})


# ---------------------------------------------------------------------------
# 7. DIAGNOSIS -> INVESTIGATION MAPPING
# ---------------------------------------------------------------------------

class MasterDiagnosisInvestigationMappingView(LoginRequiredMixin, ListView):
    model = DiagnosisInvestigationMap
    template_name = 'lab/master/master_diagnosis_investigation_mapping.html'
    context_object_name = 'mappings'
    paginate_by = 30

    def get_queryset(self):
        qs = (
            DiagnosisInvestigationMap.objects.all()
            .select_related('diagnosis', 'investigation', 'age_group', 'department')
            .order_by('priority', 'diagnosis__name', 'investigation__name')
        )
        diag_id = self.request.GET.get('diagnosis')
        inv_id = self.request.GET.get('investigation')
        gender = self.request.GET.get('gender')
        search = self.request.GET.get('search', '').strip()

        if diag_id:
            qs = qs.filter(diagnosis_id=diag_id)
        if inv_id:
            qs = qs.filter(investigation_id=inv_id)
        if gender in ('All', 'Male', 'Female'):
            qs = qs.filter(gender=gender)
        if search:
            qs = qs.filter(
                Q(diagnosis__name__icontains=search) |
                Q(investigation__name__icontains=search) |
                Q(investigation__code__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['diagnoses'] = Diagnosis.objects.filter(is_active=True).order_by('name')
        ctx['investigations'] = Investigation.objects.filter(is_active=True).order_by('name')
        ctx['age_groups'] = AgeGroup.objects.filter(is_active=True).order_by('sort_order')
        ctx['departments'] = HospitalDepartment.objects.filter(is_active=True).order_by('name')
        return ctx


@login_required
@require_POST
def api_master_diag_inv_map_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    diag_id = data.get('diagnosis_id')
    inv_id = data.get('investigation_id')

    if not diag_id or not inv_id:
        return JsonResponse({'success': False, 'message': 'Diagnosis and Investigation are required.'}, status=400)

    diag = get_object_or_404(Diagnosis, pk=diag_id)
    inv = get_object_or_404(Investigation, pk=inv_id)

    age_group_id = data.get('age_group_id') or None
    dept_id = data.get('department_id') or None
    gender = data.get('gender') or 'All'
    min_age = data.get('min_age') or None
    max_age = data.get('max_age') or None
    pregnancy_required = str(data.get('pregnancy_required', 'false')).lower() in ('true', '1')
    priority = int(data.get('priority') or 100)
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        mapping = get_object_or_404(DiagnosisInvestigationMap, pk=rec_id)
    else:
        # Check duplicate
        dup = DiagnosisInvestigationMap.objects.filter(
            diagnosis=diag,
            investigation=inv,
            age_group_id=age_group_id
        )
        if dup.exists():
            return JsonResponse({'success': False, 'message': f"Mapping for '{diag.name}' -> '{inv.name}' already exists for this age group."}, status=400)
        mapping = DiagnosisInvestigationMap(diagnosis=diag, investigation=inv)

    mapping.age_group_id = age_group_id
    mapping.department_id = dept_id
    mapping.gender = gender
    mapping.min_age = int(min_age) if min_age not in (None, '') else None
    mapping.max_age = int(max_age) if max_age not in (None, '') else None
    mapping.pregnancy_required = pregnancy_required
    mapping.priority = priority
    mapping.is_active = is_active
    mapping.save()

    return JsonResponse({'success': True, 'message': 'Diagnosis to Investigation mapping saved.'})


@login_required
@require_POST
def api_master_diag_inv_map_delete(request, pk):
    mapping = get_object_or_404(DiagnosisInvestigationMap, pk=pk)
    mapping.delete()
    return JsonResponse({'success': True, 'message': 'Mapping deleted successfully.'})


# ---------------------------------------------------------------------------
# 8. DIAGNOSIS -> DEPARTMENT MAPPING
# ---------------------------------------------------------------------------

class MasterDiagnosisDepartmentMappingView(LoginRequiredMixin, ListView):
    model = DiagnosisDepartmentMapping
    template_name = 'lab/master/master_diagnosis_department_mapping.html'
    context_object_name = 'mappings'
    paginate_by = 30

    def get_queryset(self):
        qs = DiagnosisDepartmentMapping.objects.all().select_related('department', 'diagnosis', 'age_group').order_by(
            'department__name', 'diagnosis__name'
        )
        dept_id = self.request.GET.get('department')
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '').strip()

        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if search:
            qs = qs.filter(
                Q(diagnosis__name__icontains=search) |
                Q(diagnosis__code__icontains=search) |
                Q(department__name__icontains=search)
            )
        if status in ('Active', 'Inactive'):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = HospitalDepartment.objects.filter(is_active=True).order_by('name')
        ctx['diagnoses'] = Diagnosis.objects.filter(is_active=True).order_by('name')
        ctx['age_groups'] = AgeGroup.objects.filter(is_active=True).order_by('sort_order')
        return ctx


@login_required
@require_POST
def api_master_diag_dept_map_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    dept_id = data.get('department_id')
    diag_id = data.get('diagnosis_id')
    age_group_id = data.get('age_group_id') or None
    status = data.get('status') or 'Active'

    if not dept_id or not diag_id:
        return JsonResponse({'success': False, 'message': 'Department and Diagnosis are required.'}, status=400)

    dept = get_object_or_404(HospitalDepartment, pk=dept_id)
    diag = get_object_or_404(Diagnosis, pk=diag_id)

    mapping, created = DiagnosisDepartmentMapping.objects.get_or_create(
        department=dept,
        diagnosis=diag,
        age_group_id=age_group_id,
        defaults={'status': status}
    )
    if not created:
        mapping.status = status
        mapping.save(update_fields=['status'])

    return JsonResponse({'success': True, 'message': 'Department mapping saved successfully.'})


# ---------------------------------------------------------------------------
# 9. AGE GROUPS MASTER
# ---------------------------------------------------------------------------

class MasterAgeGroupListView(LoginRequiredMixin, ListView):
    model = AgeGroup
    template_name = 'lab/master/master_age_groups.html'
    context_object_name = 'age_groups'

    def get_queryset(self):
        return AgeGroup.objects.all().order_by('sort_order', 'id')


@login_required
@require_POST
def api_master_age_group_save(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    rec_id = data.get('id')
    code = str(data.get('code', '')).strip()
    label = str(data.get('label', '')).strip()

    if not code or not label:
        return JsonResponse({'success': False, 'message': 'Code and Name are required.'}, status=400)

    min_val = data.get('min_age_value')
    max_val = data.get('max_age_value')
    min_unit = data.get('min_age_unit') or 'Years'
    max_unit = data.get('max_age_unit') or 'Years'
    gender = data.get('gender') or 'All'
    sort_order = int(data.get('sort_order') or 0)
    is_active = str(data.get('is_active', 'true')).lower() in ('true', '1')

    if rec_id:
        ag = get_object_or_404(AgeGroup, pk=rec_id)
        if AgeGroup.objects.filter(code=code).exclude(pk=rec_id).exists():
            return JsonResponse({'success': False, 'message': f"Age group code '{code}' already exists."}, status=400)
    else:
        if AgeGroup.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f"Age group code '{code}' already exists."}, status=400)
        ag = AgeGroup()

    ag.code = code
    ag.label = label
    ag.min_age_value = int(min_val) if min_val not in (None, '') else None
    ag.max_age_value = int(max_val) if max_val not in (None, '') else None
    ag.min_age_unit = min_unit
    ag.max_age_unit = max_unit
    ag.gender = gender
    ag.sort_order = sort_order
    ag.is_active = is_active
    ag.save()

    return JsonResponse({'success': True, 'message': 'Age group saved successfully.'})


# ---------------------------------------------------------------------------
# 10. MASTER VALIDATION VIEW
# ---------------------------------------------------------------------------

@login_required
def master_validation_view(request):
    """
    Displays the automated laboratory master health and integrity report.
    """
    results = run_master_validation()
    return render(request, 'lab/master/master_validation.html', {'results': results})
