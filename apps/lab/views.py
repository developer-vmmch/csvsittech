from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from apps.core.mixins import MenuAccessRequiredMixin, GranularPermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
import json
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.patients.models import Patient, PatientVisit

from .models import (
    Diagnosis, Investigation, Parameter, AgeGroup,
    DiagnosisInvestigationMap, InvestigationParameter,
    ParameterReferenceRange, PatientInvestigationOrder, PatientInvestigationResult,
    LabDepartment, SampleType,
    ChiefComplaint, HospitalService, StagingDiagnosis, StagingInvestigation,
    ServiceRequest, ServiceRequestDiagnosis, ServiceRequestInvestigation,
    PatientVisitDiagnosis
)
from .forms import (
    DiagnosisForm, InvestigationForm, ParameterForm, AgeGroupForm,
    DiagnosisInvestigationMapForm, InvestigationParameterForm, ServiceRequestForm
)
from apps.patients.models import Patient

# --- Master Entities CRUD ---

class BaseLabMasterView(LoginRequiredMixin, MenuAccessRequiredMixin):
    menu_key = 'administration' # Fallback for now

class DiagnosisListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_master.diagnosis.view'
    model = Diagnosis
    template_name = 'lab/master/diagnosis_list.html'
    context_object_name = 'diagnoses'

class DiagnosisCreateView(LoginRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    permission_required = 'lab_master.diagnosis.create'
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'lab/master/diagnosis_form.html'
    success_url = reverse_lazy('lab:diagnosis_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Diagnosis created successfully!")
        return super().form_valid(form)

class DiagnosisUpdateView(LoginRequiredMixin, GranularPermissionRequiredMixin, UpdateView):
    permission_required = 'lab_master.diagnosis.update'
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'lab/master/diagnosis_form.html'
    success_url = reverse_lazy('lab:diagnosis_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Diagnosis updated successfully!")
        return super().form_valid(form)

class InvestigationListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_master.investigation.view'
    model = Investigation
    template_name = 'lab/master/investigation_list.html'
    context_object_name = 'investigations'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('parameters', 'department', 'sample_type')

from django.views.generic import DetailView
class InvestigationDetailView(LoginRequiredMixin, GranularPermissionRequiredMixin, DetailView):
    permission_required = 'lab_master.investigation.view'
    model = Investigation
    template_name = 'lab/master/investigation_detail.html'
    context_object_name = 'investigation'

class InvestigationCreateView(LoginRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    permission_required = 'lab_master.investigation.create'
    model = Investigation
    form_class = InvestigationForm
    template_name = 'lab/master/investigation_form.html'
    success_url = reverse_lazy('lab:investigation_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Investigation created successfully!")
        return super().form_valid(form)

class InvestigationUpdateView(LoginRequiredMixin, GranularPermissionRequiredMixin, UpdateView):
    permission_required = 'lab_master.investigation.update'
    model = Investigation
    form_class = InvestigationForm
    template_name = 'lab/master/investigation_form.html'
    success_url = reverse_lazy('lab:investigation_list')

    def form_valid(self, form):
        messages.success(self.request, "Investigation updated successfully!")
        return super().form_valid(form)

class ParameterListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_master.parameter.view'
    model = InvestigationParameter
    template_name = 'lab/master/parameter_list.html'
    context_object_name = 'parameters'

class ParameterCreateView(LoginRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    permission_required = 'lab_master.parameter.create'
    model = InvestigationParameter
    form_class = ParameterForm
    template_name = 'lab/master/parameter_form.html'
    success_url = reverse_lazy('lab:parameter_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Parameter created successfully!")
        return super().form_valid(form)

class ParameterUpdateView(LoginRequiredMixin, GranularPermissionRequiredMixin, UpdateView):
    permission_required = 'lab_master.parameter.update'
    model = InvestigationParameter
    form_class = ParameterForm
    template_name = 'lab/master/parameter_form.html'
    success_url = reverse_lazy('lab:parameter_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reference_ranges'] = self.object.reference_ranges.all()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Parameter updated successfully!")
        return super().form_valid(form)

class AgeGroupListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_master.age_group.view'
    model = AgeGroup
    template_name = 'lab/master/agegroup_list.html'
    context_object_name = 'age_groups'

class AgeGroupCreateView(LoginRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    permission_required = 'lab_master.age_group.create'
    model = AgeGroup
    form_class = AgeGroupForm
    template_name = 'lab/master/agegroup_form.html'
    success_url = reverse_lazy('lab:agegroup_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Age Group created successfully!")
        return super().form_valid(form)

class AgeGroupUpdateView(LoginRequiredMixin, GranularPermissionRequiredMixin, UpdateView):
    permission_required = 'lab_master.age_group.update'
    model = AgeGroup
    form_class = AgeGroupForm
    template_name = 'lab/master/agegroup_form.html'
    success_url = reverse_lazy('lab:agegroup_list')

    def form_valid(self, form):
        messages.success(self.request, "Age Group updated successfully!")
        return super().form_valid(form)


# --- Reference Range Grid ---
class ReferenceRangeGridView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_master.reference_range.view'
    template_name = 'lab/master/reference_range_grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigations'] = Investigation.objects.filter(is_active=True)
        context['age_groups'] = AgeGroup.objects.filter(is_active=True).order_by('sort_order')
        context['diagnoses'] = Diagnosis.objects.filter(is_active=True)
        return context

class InvestigationParameterMappingView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_master.mapping.view'
    template_name = 'lab/master/investigation_parameter_mapping.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigations'] = Investigation.objects.filter(is_active=True)
        
        # Build mapping summary for the table
        investigations_with_params = Investigation.objects.filter(parameters__is_active=True).distinct()
        mapping_data = []
        for inv in investigations_with_params:
            params = inv.parameters.filter(is_active=True)
            mapping_data.append({
                'id': inv.id,
                'name': inv.name,
                'code': inv.code,
                'status': inv.is_active,
                'param_count': params.count(),
                'param_names': ", ".join([p.name or p.parameter.name for p in params if p.name or (p.parameter and p.parameter.name)])
            })
        context['mappings'] = mapping_data
        
        return context

from apps.core.mixins import granular_permission_required

@granular_permission_required('lab_master.mapping.view')
def get_all_parameters(request):
    params = InvestigationParameter.objects.filter(is_active=True).values('code', 'name').distinct().order_by('name')
    param_list = [{'id': p['code'], 'code': p['code'], 'name': p['name']} for p in params if p['code']]
    return JsonResponse({'parameters': param_list})

@granular_permission_required('lab_master.mapping.update')
def save_investigation_parameters(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            inv_id = data.get('investigation_id')
            param_codes = data.get('parameter_ids', [])
            
            if not inv_id:
                return JsonResponse({'status': 'error', 'message': 'Investigation ID is required'})
                
            existing_mappings = InvestigationParameter.objects.filter(investigation_id=inv_id)
            existing_map_dict = {m.code: m for m in existing_mappings if m.code}
            
            target_codes = set(str(p) for p in param_codes)
            
            for code, mapping in existing_map_dict.items():
                if code not in target_codes and mapping.is_active:
                    mapping.is_active = False
                    mapping.save()
                    
            display_order = existing_mappings.count()
            for code in target_codes:
                if code in existing_map_dict:
                    mapping = existing_map_dict[code]
                    if not mapping.is_active:
                        mapping.is_active = True
                        mapping.save()
                else:
                    source = InvestigationParameter.objects.filter(code=code).first()
                    if source:
                        display_order += 1
                        InvestigationParameter.objects.create(
                            investigation_id=inv_id,
                            name=source.name,
                            code=source.code,
                            unit=source.unit,
                            result_type=source.result_type,
                            decimal_precision=source.decimal_precision,
                            display_order=display_order,
                            is_active=True
                        )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@granular_permission_required('lab_master.parameter.create')
def api_add_parameter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            code = data.get('code', '').strip()
            unit = data.get('unit', '').strip()
            is_active = data.get('is_active', True)
            
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Parameter Name is required.'})
                
            # Check for duplicate
            if Parameter.objects.filter(name__iexact=name).exists() or (code and Parameter.objects.filter(code__iexact=code).exists()):
                return JsonResponse({'status': 'error', 'message': 'A parameter with this name or code already exists.'})
                
            param = Parameter.objects.create(
                name=name,
                code=code,
                default_unit=unit,
                is_active=is_active
            )
            
            return JsonResponse({
                'status': 'success',
                'parameter': {
                    'id': param.id,
                    'name': param.name,
                    'code': param.code,
                    'unit': param.default_unit
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@granular_permission_required('lab_master.reference_range.view')
def get_investigation_parameters(request):
    investigation_id = request.GET.get('investigation_id')
    if not investigation_id:
        return JsonResponse({'parameters': []})
    
    params = InvestigationParameter.objects.filter(investigation_id=investigation_id, is_active=True).select_related('parameter')
    data = [{'id': p.id, 'parameter_id': p.code, 'name': p.name or (p.parameter.name if p.parameter else ''), 'unit': p.unit or (p.parameter.default_unit if p.parameter else '')} for p in params]
    return JsonResponse({'parameters': data})

@granular_permission_required('lab_master.reference_range.view')
def get_reference_ranges(request):
    inv_param_id = request.GET.get('inv_param_id')
    if not inv_param_id:
        return JsonResponse({'ranges': []})
    
    ranges = ParameterReferenceRange.objects.filter(investigation_parameter_id=inv_param_id).select_related('age_group')
    
    data = []
    for r in ranges:
        data.append({
            'id': r.id,
            'age_group_id': r.age_group.id,
            'age_group_name': r.age_group.label,
            'gender': r.gender,
            'pregnancy': r.pregnancy,
            'min_value': str(r.min_value) if r.min_value is not None else '',
            'max_value': str(r.max_value) if r.max_value is not None else '',
            'unit': r.unit or '',
            'reference_text': r.reference_text or '',
            'is_active': r.is_active
        })
    return JsonResponse({'ranges': data})

@granular_permission_required('lab_master.reference_range.view')
def get_reference_ranges_bulk(request):
    investigation_id = request.GET.get('investigation_id')
    age_group_id = request.GET.get('age_group_id')
    gender = request.GET.get('gender')
    
    if not all([investigation_id, age_group_id, gender]):
        return JsonResponse({'ranges': []})
        
    ranges = ParameterReferenceRange.objects.filter(
        investigation_parameter__investigation_id=investigation_id,
        age_group_id=age_group_id,
        gender=gender
    )
    
    data = []
    for r in ranges:
        data.append({
            'id': r.id,
            'investigation_parameter_id': r.investigation_parameter_id,
            'age_group_id': r.age_group_id,
            'gender': r.gender,
            'pregnancy': r.pregnancy,
            'range_type': r.range_type,
            'min_value': str(r.min_value) if r.min_value is not None else '',
            'max_value': str(r.max_value) if r.max_value is not None else '',
            'unit': r.unit or '',
            'reference_text': r.reference_text or '',
            'method': r.method or '',
            'remarks': r.remarks or '',
            'is_active': r.is_active
        })
    return JsonResponse({'ranges': data})

@granular_permission_required('lab_master.reference_range.view')
def get_reference_ranges_all(request):
    inv_id = request.GET.get('inv_id')
    ag_id = request.GET.get('ag_id')
    gender = request.GET.get('gender')
    
    ranges = ParameterReferenceRange.objects.select_related(
        'investigation_parameter__investigation',
        'investigation_parameter',
        'age_group'
    ).all()
    
    if inv_id:
        ranges = ranges.filter(investigation_parameter__investigation_id=inv_id)
    if ag_id:
        ranges = ranges.filter(age_group_id=ag_id)
    if gender:
        ranges = ranges.filter(gender=gender)
        
    data = []
    for r in ranges:
        val = ''
        if r.range_type == 'Numeric':
            val = f"{r.min_value} - {r.max_value}"
        elif r.range_type == 'Text':
            val = r.reference_text
        else:
            val = '-'
            
        data.append({
            'id': r.id,
            'investigation': r.investigation_parameter.investigation.name,
            'investigation_id': r.investigation_parameter.investigation_id,
            'parameter': r.investigation_parameter.name,
            'age_group': r.age_group.label,
            'age_group_id': r.age_group_id,
            'gender': r.gender,
            'range': val,
            'unit': r.unit or '-',
            'method': r.method or '-',
            'status': r.is_active
        })
    return JsonResponse({'ranges': data})

@granular_permission_required('lab_master.reference_range.update')
def save_reference_range(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            range_id = data.get('id')
            inv_param_id = data.get('investigation_parameter_id')
            age_group_id = data.get('age_group_id')
            gender = data.get('gender', 'All')
            pregnancy = data.get('pregnancy', 'No')
            
            if not inv_param_id or not age_group_id:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'})
            
            # Validate Min <= Max
            min_val_raw = data.get('min_value')
            max_val_raw = data.get('max_value')
            min_val = Decimal(min_val_raw) if min_val_raw and str(min_val_raw).strip() != '' else None
            max_val = Decimal(max_val_raw) if max_val_raw and str(max_val_raw).strip() != '' else None
            
            if min_val is not None and max_val is not None:
                if min_val > max_val:
                    return JsonResponse({'status': 'error', 'message': 'Minimum value cannot be greater than maximum value.'})
            
            created = False
            if range_id:
                try:
                    range_obj = ParameterReferenceRange.objects.get(id=range_id)
                    range_obj.gender = gender
                    range_obj.pregnancy = pregnancy
                except ParameterReferenceRange.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Record not found for update'})
            else:
                range_obj, created = ParameterReferenceRange.objects.get_or_create(
                    investigation_parameter_id=inv_param_id,
                    age_group_id=age_group_id,
                    gender=gender,
                    pregnancy=pregnancy
                )
            
            range_obj.range_type = data.get('range_type', 'Numeric')
            range_obj.min_value = min_val
            range_obj.max_value = max_val
            range_obj.reference_text = data.get('reference_text', '')
            range_obj.unit = data.get('unit', '')
            range_obj.method = data.get('method', '')
            range_obj.remarks = data.get('remarks', '')
            range_obj.is_active = data.get('is_active', True)
            
            range_obj.save()
            return JsonResponse({'status': 'success', 'id': range_obj.id, 'created': created})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@granular_permission_required('lab_master.reference_range.create')
def save_multiple_reference_ranges(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            param_ids = data.get('parameter_ids', [])
            age_group_ids = data.get('age_group_ids', [])
            gender = data.get('gender', 'All')
            
            # Additional fields
            range_type = data.get('range_type', 'Numeric')
            min_val_raw = data.get('min_value')
            max_val_raw = data.get('max_value')
            reference_text = data.get('reference_text', '')
            unit = data.get('unit', '')
            method = data.get('method', '')
            remarks = data.get('remarks', '')
            
            update_existing = data.get('update_existing', False)
            
            if not param_ids or not age_group_ids:
                return JsonResponse({'status': 'error', 'message': 'Missing parameters or age groups'})
                
            min_val = Decimal(min_val_raw) if min_val_raw and str(min_val_raw).strip() != '' else None
            max_val = Decimal(max_val_raw) if max_val_raw and str(max_val_raw).strip() != '' else None
            
            if range_type == 'Numeric' and min_val is not None and max_val is not None:
                if min_val > max_val:
                    return JsonResponse({'status': 'error', 'message': 'Minimum value cannot be greater than maximum value.'})
                    
            created_count = 0
            updated_count = 0
            
            # Check for existing
            if not update_existing:
                for p_id in param_ids:
                    for ag_id in age_group_ids:
                        if ParameterReferenceRange.objects.filter(
                            investigation_parameter_id=p_id,
                            age_group_id=ag_id,
                            gender=gender
                        ).exists():
                            return JsonResponse({'status': 'exists', 'message': 'Reference range already exists. Update existing?'})

            for p_id in param_ids:
                for ag_id in age_group_ids:
                    range_obj, created = ParameterReferenceRange.objects.get_or_create(
                        investigation_parameter_id=p_id,
                        age_group_id=ag_id,
                        gender=gender
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                    range_obj.range_type = range_type
                    range_obj.min_value = min_val
                    range_obj.max_value = max_val
                    range_obj.reference_text = reference_text
                    range_obj.unit = unit
                    range_obj.method = method
                    range_obj.remarks = remarks
                    range_obj.is_active = True
                    range_obj.save()
                    
            return JsonResponse({
                'status': 'success',
                'message': f"{created_count + updated_count} reference ranges saved successfully."
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@granular_permission_required('lab_master.reference_range.delete')
def delete_reference_range(request, pk):
    if request.method == 'POST':
        try:
            r = ParameterReferenceRange.objects.get(id=pk)
            r.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

def api_add_department(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            dept, created = LabDepartment.objects.get_or_create(name=name.strip())
            return JsonResponse({'status': 'success', 'id': dept.id, 'name': dept.name})
    return JsonResponse({'status': 'error'})

def api_add_sample_type(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            st, created = SampleType.objects.get_or_create(name=name.strip())
            return JsonResponse({'status': 'success', 'id': st.id, 'name': st.name})
    return JsonResponse({'status': 'error'})

class LegacyMappingView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_master.legacy_mapping.view'
    template_name = 'lab/master/legacy_mapping.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Diagnosis Tab Data
        unmapped_diag = StagingDiagnosis.objects.filter(migrated=False)
        context['staging_diagnosis'] = unmapped_diag
        context['diag_unmapped_count'] = unmapped_diag.count()
        context['diag_total_count'] = StagingDiagnosis.objects.count()
        
        # Investigation Tab Data
        unmapped_inv = StagingInvestigation.objects.filter(migrated=False)
        context['staging_investigation'] = unmapped_inv
        context['inv_unmapped_count'] = unmapped_inv.count()
        context['inv_total_count'] = StagingInvestigation.objects.count()
        
        # Lookups for mapping forms
        context['departments'] = LabDepartment.objects.filter(is_active=True)
        context['sample_types'] = SampleType.objects.filter(is_active=True)
        context['hospital_service_categories'] = HospitalService.CategoryChoices.choices
        
        return context

@granular_permission_required('lab_master.legacy_mapping.update')
def process_legacy_mapping(request):
    """
    API endpoint to handle legacy mapping operations from both tabs.
    Expected JSON payload: { "tab": "diagnosis"|"investigation", "action": "...", "ids": [1,2,3], ...other fields }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
        
    try:
        data = json.loads(request.body)
        tab = data.get('tab')
        action = data.get('action')
        item_ids = data.get('ids', [])
        
        if not item_ids:
            return JsonResponse({'status': 'error', 'message': 'No items selected'})

        if tab == 'diagnosis':
            staging_qs = StagingDiagnosis.objects.filter(id__in=item_ids)
            if action == 'chief_complaint':
                for st in staging_qs:
                    # Save as Chief Complaint
                    cc, created = ChiefComplaint.objects.get_or_create(
                        legacy_code=st.legacy_id,
                        defaults={'name': st.legacy_text}
                    )
                    st.migrated = True
                    st.migrated_to_type = 'ChiefComplaint'
                    st.migrated_to_id = cc.id
                    st.save()
                    
            elif action == 'true_diagnosis':
                # Single item mapping
                st = staging_qs.first()
                icd_code = data.get('icd_code')
                icd_title = data.get('icd_title')
                if st and icd_code:
                    diag, created = Diagnosis.objects.get_or_create(
                        code=icd_code,
                        defaults={
                            'name': icd_title or st.legacy_text,
                            'icd11_title': icd_title,
                            'legacy_code': st.legacy_id
                        }
                    )
                    st.migrated = True
                    st.migrated_to_type = 'Diagnosis'
                    st.migrated_to_id = diag.id
                    st.save()
                    
            elif action == 'skip':
                staging_qs.update(migrated=True, migrated_to_type='Skipped')

        elif tab == 'investigation':
            staging_qs = StagingInvestigation.objects.filter(id__in=item_ids)
            
            if action == 'hospital_service':
                category = data.get('category', HospitalService.CategoryChoices.OTHER)
                for st in staging_qs:
                    hs, created = HospitalService.objects.get_or_create(
                        code=st.legacy_code,
                        defaults={'name': st.legacy_text, 'category': category}
                    )
                    st.migrated = True
                    st.migrated_to_type = 'HospitalService'
                    st.migrated_to_id = hs.id
                    st.save()
                    
            elif action == 'true_investigation':
                # Single item mapping
                st = staging_qs.first()
                name = data.get('name')
                short_name = data.get('short_name')
                dept_id = data.get('department_id')
                sample_type_id = data.get('sample_type_id')
                is_panel = data.get('is_panel', False)
                
                if st and name:
                    inv, created = Investigation.objects.get_or_create(
                        code=f"INV-{st.legacy_code}", # ensure unique code format or just use legacy code
                        defaults={
                            'name': name,
                            'short_name': short_name,
                            'department_id': dept_id if dept_id else None,
                            'sample_type_id': sample_type_id if sample_type_id else None,
                            'is_panel': is_panel,
                            'legacy_code': st.legacy_code
                        }
                    )
                    st.migrated = True
                    st.migrated_to_type = 'Investigation'
                    st.migrated_to_id = inv.id
                    st.save()
            
            elif action == 'skip':
                staging_qs.update(migrated=True, migrated_to_type='Skipped')

        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})

# --- Transaction Screens ---
class OrderEntryView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_orders.create_lab_order.view'
    template_name = 'lab/orders/order_entry.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient_id = self.request.GET.get('patient_id')
        if patient_id:
            context['patient'] = Patient.objects.filter(id=patient_id).first()
        context['diagnoses'] = Diagnosis.objects.filter(is_active=True)
        # Mapping mapping for JS
        maps = DiagnosisInvestigationMap.objects.filter(is_active=True).select_related('investigation')
        diag_map = {}
        for m in maps:
            if m.diagnosis_id not in diag_map:
                diag_map[m.diagnosis_id] = []
            diag_map[m.diagnosis_id].append({'id': m.investigation.id, 'name': m.investigation.name})
        context['diagnosis_investigation_map_json'] = json.dumps(diag_map)
        context['all_investigations'] = Investigation.objects.filter(is_active=True)
        return context

    def post(self, request, *args, **kwargs):
        patient_id = request.POST.get('patient_id')
        diagnosis_id = request.POST.get('diagnosis_id')
        investigation_ids = request.POST.getlist('investigations')

        if not patient_id or not investigation_ids:
            messages.error(request, "Patient and at least one Investigation are required.")
            return redirect('lab:order_entry')

        patient = get_object_or_404(Patient, id=patient_id)
        diagnosis = Diagnosis.objects.filter(id=diagnosis_id).first() if diagnosis_id else None
        
        for inv_id in investigation_ids:
            inv = get_object_or_404(Investigation, id=inv_id)
            PatientInvestigationOrder.objects.create(
                patient=patient,
                diagnosis=diagnosis,
                investigation=inv,
                ordered_by=request.user,
                status=PatientInvestigationOrder.StatusChoices.PENDING
            )
            
        messages.success(request, f"Successfully created {len(investigation_ids)} order(s) for patient {patient.name}.")
        return redirect('lab:order_entry')

class ResultEntryListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_orders.lab_order_list.view'
    model = PatientInvestigationOrder
    template_name = 'lab/orders/result_entry_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return PatientInvestigationOrder.objects.filter(status=PatientInvestigationOrder.StatusChoices.PENDING).select_related('patient', 'investigation')

class ResultEntryDetailView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_orders.lab_order_list.view'
    template_name = 'lab/orders/result_entry.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(PatientInvestigationOrder, id=kwargs.get('pk'))
        context['order'] = order
        context['parameters'] = InvestigationParameter.objects.filter(investigation=order.investigation, is_active=True).select_related('parameter')
        return context

    def post(self, request, *args, **kwargs):
        order = get_object_or_404(PatientInvestigationOrder, id=kwargs.get('pk'))
        params = InvestigationParameter.objects.filter(investigation=order.investigation, is_active=True)
        
        # Simplified resolve logic: just save for now
        from .services import resolveReferenceRange
        
        for p in params:
            val = request.POST.get(f'param_{p.id}')
            if val:
                # We would normally calculate patient age here, but just mock it
                age_group_id = None # need real logic for patient age
                
                # Mock resolving logic
                # result_range = resolveReferenceRange(age_group_id, order.diagnosis_id, p.id, order.patient.gender)
                
                PatientInvestigationResult.objects.update_or_create(
                    order=order,
                    investigation_parameter=p,
                    defaults={
                        'result_value': val,
                        'flag': PatientInvestigationResult.FlagChoices.NORMAL, # would use resolved logic
                        'entered_by': request.user
                    }
                )
                
        order.status = PatientInvestigationOrder.StatusChoices.COMPLETED
        order.save()
        messages.success(request, "Results saved successfully.")
        return redirect('lab:result_entry_list')


# --- Counts APIs ---
from django.http import JsonResponse
from .models import InvestigationParameter

def api_diagnosis_count(request):
    total = Diagnosis.objects.count()
    active = Diagnosis.objects.filter(is_active=True).count()
    return JsonResponse({
        'total': total,
        'active': active,
        'inactive': total - active
    })

# --- Service Request (Doctor Window) ---
from django.db import transaction
from django.db.models import Q
from apps.users.models import User

class ServiceRequestListView(LoginRequiredMixin, GranularPermissionRequiredMixin, ListView):
    permission_required = 'lab_orders.service_request.view'
    model = ServiceRequest
    template_name = 'lab/orders/service_request_list.html'
    context_object_name = 'service_requests'

    def get_queryset(self):
        return super().get_queryset().select_related('patient', 'consultant', 'department')

class ServiceRequestCreateView(LoginRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    permission_required = 'lab_orders.service_request.create'
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'lab/orders/service_request_form.html'
    success_url = reverse_lazy('lab:service_request_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.patients.models import Department
        context['departments'] = Department.objects.filter(is_active=True)
        # Assuming we can get consultants from User model (is_staff or something), filtering all for now
        context['consultants'] = User.objects.all()
        return context

    def form_valid(self, form):
        # We handle this mainly via AJAX, but if form submits normally:
        return super().form_valid(form)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # We will handle AJAX POST here
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                patient_id = data.get('patient_id')
                consultant_id = data.get('consultant_id')
                department_id = data.get('department_id')
                visit_type = data.get('visit_type', 'OP')
                request_date = data.get('request_date')
                diagnoses_data = data.get('diagnoses', [])
                investigations_data = data.get('investigations', [])
                from apps.patients.models import Department
                patient = Patient.objects.get(id=patient_id)
                department = Department.objects.filter(id=department_id).first()
                consultant = User.objects.filter(id=consultant_id).first()

                sr = ServiceRequest.objects.create(
                    patient=patient,
                    consultant=consultant,
                    department=department,
                    visit_type=visit_type,
                    request_date=request_date or timezone.now().date(),
                    status=ServiceRequest.StatusChoices.SAVED,
                    created_by=request.user
                )

                for idx, diag in enumerate(diagnoses_data):
                    item_type = diag.get('type')
                    item_id = diag.get('id')
                    if item_type == 'Diagnosis':
                        ServiceRequestDiagnosis.objects.create(
                            service_request=sr,
                            diagnosis_id=item_id,
                            sort_order=idx
                        )
                    elif item_type == 'ChiefComplaint':
                        ServiceRequestDiagnosis.objects.create(
                            service_request=sr,
                            chief_complaint_id=item_id,
                            sort_order=idx
                        )

                for inv in investigations_data:
                    ServiceRequestInvestigation.objects.create(
                        service_request=sr,
                        investigation_id=inv.get('id'),
                        qty=inv.get('qty', 1),
                        source=inv.get('source', 'MANUAL'),
                        is_removed=inv.get('is_removed', False)
                    )

                return JsonResponse({'status': 'success', 'service_request_id': sr.id})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        else:
            return super().post(request, *args, **kwargs)

@login_required
def api_get_patients_for_request(request):
    department_id = request.GET.get('department_id')
    visit_type = request.GET.get('visit_type')
    date_str = request.GET.get('date')
    
    # We combine logic to find Patient records (visit 1) and PatientVisit records (visit > 1)
    patients_qs = Patient.objects.all().select_related('department_obj').order_by('-id')
    if date_str:
        patients_qs = patients_qs.filter(registration_date=date_str)
    if department_id:
        patients_qs = patients_qs.filter(department_obj_id=department_id)
    if visit_type:
        patients_qs = patients_qs.filter(visit_through=visit_type)
        
    visits_qs = PatientVisit.objects.all().select_related('patient', 'department_obj').order_by('-id')
    if date_str:
        visits_qs = visits_qs.filter(visit_date__date=date_str)
    if department_id:
        visits_qs = visits_qs.filter(department_obj_id=department_id)
    if visit_type:
        visits_qs = visits_qs.filter(visit_type=visit_type)
        
    data = []
    
    # 1. Process Patient (Visit 1)
    for p in patients_qs[:50]:
        visit1 = PatientVisit.objects.filter(patient=p, visit_no=1).first()
        diagnosis_texts = []
        if visit1:
            for d in visit1.diagnoses.all():
                if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
                elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
                
        req_count = ServiceRequest.objects.filter(patient=p, request_date=p.registration_date).count()
        data.append({
            'visit_id': f"patient_{p.id}",
            'patient_id': p.patient_id,
            'patient_pk': p.id,
            'name': p.name,
            'gender': p.gender,
            'age': p.age_years,
            'department': p.department_obj.name if p.department_obj else (p.department or '-'),
            'dept_code': p.department_obj.code if p.department_obj else (p.department[:4].upper() if p.department else '-'),
            'visit_type': p.visit_through,
            'visit_no': 1,
            'diagnosis': ", ".join(diagnosis_texts) if diagnosis_texts else "Not Added",
            'request_count': req_count
        })
        
    # 2. Process PatientVisit (Visit > 1)
    for v in visits_qs[:50]:
        if v.visit_no == 1:
            continue
            
        diagnosis_texts = []
        for d in v.diagnoses.all():
            if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
            elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
            
        req_count = ServiceRequest.objects.filter(patient=v.patient, request_date=v.visit_date.date()).count()
        data.append({
            'visit_id': v.id,
            'patient_id': v.patient.patient_id,
            'patient_pk': v.patient.id,
            'name': v.patient.name,
            'gender': v.patient.gender,
            'age': v.patient.age_years,
            'department': v.department_obj.name if v.department_obj else (v.department or '-'),
            'dept_code': v.department_obj.code if v.department_obj else (v.department[:4].upper() if v.department else '-'),
            'visit_type': v.visit_type,
            'visit_no': v.visit_no,
            'diagnosis': ", ".join(diagnosis_texts) if diagnosis_texts else "Not Added",
            'request_count': req_count
        })
        
    return JsonResponse({'patients': data[:100]})

@login_required
def api_search_diagnosis(request):
    q = request.GET.get('q', '').strip()
    diag_type = request.GET.get('type', 'ALL')
    
    if not q:
        diags = Diagnosis.objects.filter(is_active=True)
        chiefs = ChiefComplaint.objects.filter(is_active=True)
    else:
        diags = Diagnosis.objects.filter(
            Q(name__icontains=q) | Q(code__icontains=q) | Q(icd11_title__icontains=q) | Q(synonyms__icontains=q),
            is_active=True
        )
        chiefs = ChiefComplaint.objects.filter(name__icontains=q, is_active=True)
    
    results = []
    if diag_type in ['ALL', 'Diagnosis']:
        for d in diags:
            results.append({
                'id': d.id,
                'text': d.name,
                'code': d.code,
                'category': d.chapter or 'General',
                'type': 'Diagnosis'
            })
            
    if diag_type in ['ALL', 'ChiefComplaint']:
        for c in chiefs:
            results.append({
                'id': c.id,
                'text': c.name,
                'type': 'ChiefComplaint'
            })
            
    return JsonResponse({'results': results})

@login_required
@csrf_exempt
def api_suggest_investigations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis_ids = data.get('diagnosis_ids', [])
            patient_id = data.get('patient_id')
            
            # Map diagnosis directly
            maps_qs = DiagnosisInvestigationMap.objects.filter(
                diagnosis_id__in=diagnosis_ids, 
                is_active=True
            ).select_related('investigation', 'age_group')
            
            if patient_id:
                p = get_object_or_404(Patient, id=patient_id)
                age_days = p.age_years * 365 # Approx, enough for basic matching
                
                # Match Age Groups
                valid_age_groups = []
                for ag in AgeGroup.objects.filter(is_active=True):
                    if ag.gender not in ['All', p.gender]:
                        continue
                    
                    min_days = 0
                    if ag.min_age_value:
                        if ag.min_age_unit == 'Days': min_days = ag.min_age_value
                        elif ag.min_age_unit == 'Months': min_days = ag.min_age_value * 30
                        else: min_days = ag.min_age_value * 365
                        
                    max_days = 99999
                    if ag.max_age_value:
                        if ag.max_age_unit == 'Days': max_days = ag.max_age_value
                        elif ag.max_age_unit == 'Months': max_days = ag.max_age_value * 30
                        else: max_days = ag.max_age_value * 365
                        
                    if min_days <= age_days <= max_days:
                        valid_age_groups.append(ag.id)
                
                maps_qs = maps_qs.filter(Q(age_group__isnull=True) | Q(age_group_id__in=valid_age_groups))
            
            investigations = {}
            for m in maps_qs:
                if m.investigation.id not in investigations:
                    investigations[m.investigation.id] = {
                        'id': m.investigation.id,
                        'name': m.investigation.name,
                        'code': m.investigation.legacy_code or m.investigation.code
                    }
                
            return JsonResponse({'status': 'success', 'investigations': list(investigations.values())})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})


def api_investigation_count(request):
    total = Investigation.objects.count()
    active = Investigation.objects.filter(is_active=True).count()
    return JsonResponse({
        'total': total,
        'active': active,
        'inactive': total - active
    })

def api_parameter_count(request):
    total = InvestigationParameter.objects.count()
    active = InvestigationParameter.objects.filter(is_active=True).count()
    return JsonResponse({
        'total': total,
        'active': active,
        'inactive': total - active
    })

def api_search_investigation(request):
    query = request.GET.get('q', '').strip()
        
    investigations = Investigation.objects.filter(is_active=True)
    if query:
        investigations = investigations.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(short_name__icontains=query)
        )
    
    results = []
    for inv in investigations:
        results.append({
            'id': inv.id,
            'text': inv.name,
            'code': inv.code
        })
        
    return JsonResponse({'results': results})

# --- Doctor Window ---

class DoctorWindowView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    template_name = 'lab/orders/doctor_window.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.patients.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        return context

@login_required
def api_doctor_window_patients(request):
    department_id = request.GET.get('department_id')
    visit_type = request.GET.get('visit_type')
    date_str = request.GET.get('date')
    
    # We will combine Patient (Visit 1) and PatientVisit (Visit > 1)
    # 1. Query Patient (Visit 1)
    patients_qs = Patient.objects.all().order_by('-id')
    if date_str:
        patients_qs = patients_qs.filter(registration_date=date_str)
    if department_id:
        patients_qs = patients_qs.filter(department_obj_id=department_id)
    if visit_type:
        patients_qs = patients_qs.filter(visit_through=visit_type)
        
    # 2. Query PatientVisit (Visit > 1)
    visits_qs = PatientVisit.objects.select_related('patient', 'department_obj').all().order_by('-id')
    if date_str:
        visits_qs = visits_qs.filter(visit_date__date=date_str)
    if department_id:
        visits_qs = visits_qs.filter(department_obj_id=department_id)
    if visit_type:
        visits_qs = visits_qs.filter(visit_type=visit_type)
        
    data = []
    
    # Process Patient (Visit 1)
    for p in patients_qs[:100]:
        # Check if Visit 1 record exists in PatientVisit for diagnosis
        visit1 = PatientVisit.objects.filter(patient=p, visit_no=1).first()
        diagnosis_texts = []
        if visit1:
            for d in visit1.diagnoses.all():
                if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
                elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
                
        req_count = ServiceRequest.objects.filter(patient=p, request_date=p.registration_date).count()
        data.append({
            'visit_id': f"patient_{p.id}",
            'patient_id': p.patient_id,
            'patient_name': p.name,
            'gender': p.gender,
            'age': p.age_years,
            'department': p.department_obj.name if p.department_obj else (p.department or '-'),
            'dept_code': p.department_obj.code if p.department_obj else (p.department[:4].upper() if p.department else '-'),
            'visit_type': p.visit_through,
            'visit_no': 1,
            'diagnosis': ", ".join(diagnosis_texts) if diagnosis_texts else "Select",
            'request_count': req_count
        })
        
    # Process PatientVisit (Visit > 1)
    for v in visits_qs[:100]:
        if v.visit_no == 1:
            continue # Already handled in Patient queries typically
            
        diagnosis_texts = []
        for d in v.diagnoses.all():
            if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
            elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
            
        req_count = ServiceRequest.objects.filter(patient=v.patient, request_date=v.visit_date.date()).count()
        data.append({
            'visit_id': v.id,
            'patient_id': v.patient.patient_id,
            'patient_name': v.patient.name,
            'gender': v.patient.gender,
            'age': v.patient.age_years,
            'department': v.department_obj.name if v.department_obj else (v.department or '-'),
            'dept_code': v.department_obj.code if v.department_obj else (v.department[:4].upper() if v.department else '-'),
            'visit_type': v.visit_type,
            'visit_no': v.visit_no,
            'diagnosis': ", ".join(diagnosis_texts) if diagnosis_texts else "Select",
            'request_count': req_count
        })
        
    return JsonResponse({'patients': data[:150]})

@login_required
def api_doctor_window_get_diagnosis(request):
    visit_id = request.GET.get('visit_id')
    diagnoses = []
    
    if str(visit_id).startswith('patient_'):
        patient_id = visit_id.split('_')[1]
        visit = PatientVisit.objects.filter(patient_id=patient_id, visit_no=1).first()
    else:
        visit = get_object_or_404(PatientVisit, id=visit_id)
        
    if visit:
        for d in visit.diagnoses.all():
            if d.diagnosis:
                diagnoses.append({'id': d.diagnosis.id, 'text': d.diagnosis.name, 'type': 'Diagnosis'})
            elif d.chief_complaint:
                diagnoses.append({'id': d.chief_complaint.id, 'text': d.chief_complaint.name, 'type': 'Complaint'})
            
    return JsonResponse({'diagnoses': diagnoses})

@login_required
@require_POST
def api_doctor_window_save_diagnosis(request):
    data = json.loads(request.body)
    visit_id = data.get('visit_id')
    diagnoses = data.get('diagnoses', [])
    
    if str(visit_id).startswith('patient_'):
        patient_id = visit_id.split('_')[1]
        p = get_object_or_404(Patient, id=patient_id)
        
        from django.utils import timezone
        from datetime import datetime
        
        # Create or get Visit 1 for this Patient to attach diagnosis
        v_date = timezone.make_aware(datetime.combine(p.registration_date, datetime.min.time())) if p.registration_date else timezone.now()
        
        visit, _ = PatientVisit.objects.get_or_create(
            patient=p,
            visit_no=1,
            defaults={
                'visit_date': v_date,
                'department_obj': p.department_obj,
                'department': p.department,
                'visit_type': p.visit_through,
                'category': p.category
            }
        )
    else:
        visit = get_object_or_404(PatientVisit, id=visit_id)
    
    with transaction.atomic():
        visit.diagnoses.all().delete()
        for d in diagnoses:
            if d['type'] == 'Diagnosis':
                PatientVisitDiagnosis.objects.create(visit=visit, diagnosis_id=d['id'])
            elif d['type'] == 'Complaint':
                PatientVisitDiagnosis.objects.create(visit=visit, chief_complaint_id=d['id'])
                
    return JsonResponse({'status': 'success'})

# --- Work Orders ---
class WorkOrdersView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    permission_required = 'lab_orders.work_orders.view'
    template_name = 'lab/orders/work_orders.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.patients.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        from apps.lab.models import ServiceRequestInvestigation
        context['statuses'] = ServiceRequestInvestigation.StatusChoices.choices
        return context

@login_required
def api_work_orders_list(request):
    date_str = request.GET.get('date')
    department_id = request.GET.get('department_id')
    visit_type = request.GET.get('visit_type')
    status = request.GET.get('status')
    search = request.GET.get('search', '').strip()

    from apps.lab.models import ServiceRequest
    from django.db.models import Prefetch, Q
    
    qs = ServiceRequest.objects.filter(investigations__is_removed=False).distinct().select_related(
        'patient', 'department'
    ).prefetch_related(
        'investigations'
    ).order_by('-request_date', '-id')

    if date_str:
        qs = qs.filter(request_date=date_str)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if visit_type and visit_type != 'ALL':
        qs = qs.filter(visit_type=visit_type)
        
    if search:
        qs = qs.filter(
            Q(patient__patient_id__icontains=search) |
            Q(patient__name__icontains=search) |
            Q(sample_id__icontains=search) |
            Q(receipt_no__icontains=search)
        )

    data = []
    for sr in qs[:200]: # Reasonable limit for UI
        invs = [inv for inv in sr.investigations.all() if not inv.is_removed]
        if not invs:
            continue
            
        statuses = [inv.status for inv in invs]
        
        if all(s == 'COMPLETED' for s in statuses):
            sr_status = 'COMPLETED'
        elif all(s in ['RECEIVED', 'COMPLETED'] for s in statuses):
            sr_status = 'RECEIVED'
        else:
            sr_status = 'PENDING'
            
        if status and status != 'ALL' and sr_status != status:
            continue
            
        data.append({
            's_no': len(data) + 1,
            'id': sr.id,
            'sample_id': sr.sample_id or '-',
            'patient_id': sr.patient.patient_id,
            'patient_name': sr.patient.name,
            'age_gender': f"{sr.patient.age_years} / {sr.patient.gender}",
            'department': sr.department.name if sr.department else '-',
            'visit_type': sr.get_visit_type_display(),
            'request_date': sr.request_date.strftime('%d/%m/%Y') if sr.request_date else '-',
            'amount': '-',
            'voucher_no': sr.receipt_no or '-',
            'status': sr_status,
        })
        
    return JsonResponse({'work_orders': data})

class WorkOrderDetailView(LoginRequiredMixin, GranularPermissionRequiredMixin, DetailView):
    permission_required = 'lab_orders.work_orders.view'
    template_name = 'lab/orders/work_order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        from apps.lab.models import ServiceRequest
        return ServiceRequest.objects.select_related('patient', 'department', 'consultant')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.lab.models import ServiceRequestInvestigation
        context['investigations'] = self.object.investigations.filter(is_removed=False).select_related(
            'investigation', 'investigation__department', 'investigation__sample_type', 'received_by'
        )
        return context

@login_required
@require_POST
def api_work_order_receive_multiple(request):
    try:
        data = json.loads(request.body)
        test_ids = data.get('test_ids', [])
        
        from apps.lab.models import ServiceRequestInvestigation
        tests = ServiceRequestInvestigation.objects.filter(id__in=test_ids, status=ServiceRequestInvestigation.StatusChoices.PENDING)
        
        for t in tests:
            t.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
            t.received_date = timezone.now().date()
            t.received_time = timezone.now().time()
            t.received_by = request.user
            t.save()
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def api_work_order_receive(request, pk):
    from apps.lab.models import ServiceRequestInvestigation
    wo = get_object_or_404(ServiceRequestInvestigation, id=pk)
    if wo.status != ServiceRequestInvestigation.StatusChoices.PENDING:
        return JsonResponse({'status': 'error', 'message': 'Work order is not pending'})
    
    wo.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
    wo.received_date = timezone.now().date()
    wo.received_time = timezone.now().time()
    wo.received_by = request.user
    wo.save()
    
    return JsonResponse({'status': 'success'})

class WorkOrderResultEntryView(LoginRequiredMixin, GranularPermissionRequiredMixin, DetailView):
    permission_required = 'lab_orders.work_orders.view'
    template_name = 'lab/orders/work_order_result_entry.html'
    context_object_name = 'wo'
    
    def get_queryset(self):
        from apps.lab.models import ServiceRequestInvestigation
        return ServiceRequestInvestigation.objects.select_related(
            'service_request',
            'service_request__patient',
            'service_request__department',
            'investigation',
            'investigation__sample_type'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wo = self.object
        
        from apps.lab.models import InvestigationParameter
        parameters = InvestigationParameter.objects.filter(
            investigation=wo.investigation,
            is_active=True
        ).select_related('parameter').order_by('display_order')
        
        # Get diagnosis from service request
        diagnosis_texts = []
        for d in wo.service_request.diagnoses.all():
            if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
            elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
            
        context['diagnosis_text'] = ", ".join(diagnosis_texts) if diagnosis_texts else "Not Added"
        context['parameters'] = parameters
        return context

@login_required
@require_POST
def api_work_order_save_result(request, pk):
    from apps.lab.models import ServiceRequestInvestigation, ServiceRequestResult, InvestigationParameter
    wo = get_object_or_404(ServiceRequestInvestigation, id=pk)
    
    if wo.status == ServiceRequestInvestigation.StatusChoices.COMPLETED:
        return JsonResponse({'status': 'error', 'message': 'Work order already completed'})
        
    try:
        data = json.loads(request.body)
        results = data.get('results', [])
        
        with transaction.atomic():
            for res in results:
                param_id = res.get('parameter_id')
                val = res.get('value')
                remarks = res.get('remarks', '')
                if not val:
                    continue
                    
                ip = InvestigationParameter.objects.get(id=param_id, investigation=wo.investigation)
                
                ServiceRequestResult.objects.update_or_create(
                    sr_investigation=wo,
                    investigation_parameter=ip,
                    defaults={
                        'result_value': val,
                        'remarks': remarks,
                        'entered_by': request.user
                    }
                )
            
            wo.status = ServiceRequestInvestigation.StatusChoices.COMPLETED
            wo.completed_date = timezone.now()
            wo.completed_by = request.user
            wo.save()
            
        return JsonResponse({'status': 'success', 'order_id': wo.service_request.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
