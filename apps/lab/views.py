from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
import json
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Diagnosis, Investigation, Parameter, AgeGroup,
    DiagnosisInvestigationMap, InvestigationParameter,
    ParameterReferenceRange, PatientInvestigationOrder, PatientInvestigationResult,
    LabDepartment, SampleType,
    ChiefComplaint, HospitalService, StagingDiagnosis, StagingInvestigation
)
from .forms import (
    DiagnosisForm, InvestigationForm, ParameterForm, AgeGroupForm,
    DiagnosisInvestigationMapForm, InvestigationParameterForm
)
from apps.patients.models import Patient

# --- Master Entities CRUD ---

class BaseLabMasterView(LoginRequiredMixin, MenuAccessRequiredMixin):
    menu_key = 'administration' # Placeholder, since it should be 'lab_master' but need to check existing menus

class DiagnosisListView(BaseLabMasterView, ListView):
    model = Diagnosis
    template_name = 'lab/master/diagnosis_list.html'
    context_object_name = 'diagnoses'

class DiagnosisCreateView(BaseLabMasterView, CreateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'lab/master/diagnosis_form.html'
    success_url = reverse_lazy('lab:diagnosis_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Diagnosis created successfully!")
        return super().form_valid(form)

class DiagnosisUpdateView(BaseLabMasterView, UpdateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'lab/master/diagnosis_form.html'
    success_url = reverse_lazy('lab:diagnosis_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Diagnosis updated successfully!")
        return super().form_valid(form)

class InvestigationListView(BaseLabMasterView, ListView):
    model = Investigation
    template_name = 'lab/master/investigation_list.html'
    context_object_name = 'investigations'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('parameters', 'department', 'sample_type')

from django.views.generic import DetailView
class InvestigationDetailView(BaseLabMasterView, DetailView):
    model = Investigation
    template_name = 'lab/master/investigation_detail.html'
    context_object_name = 'investigation'

class InvestigationCreateView(BaseLabMasterView, CreateView):
    model = Investigation
    form_class = InvestigationForm
    template_name = 'lab/master/investigation_form.html'
    success_url = reverse_lazy('lab:investigation_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Investigation created successfully!")
        return super().form_valid(form)

class InvestigationUpdateView(BaseLabMasterView, UpdateView):
    model = Investigation
    form_class = InvestigationForm
    template_name = 'lab/master/investigation_form.html'
    success_url = reverse_lazy('lab:investigation_list')

    def form_valid(self, form):
        messages.success(self.request, "Investigation updated successfully!")
        return super().form_valid(form)

class ParameterListView(BaseLabMasterView, ListView):
    model = InvestigationParameter
    template_name = 'lab/master/parameter_list.html'
    context_object_name = 'parameters'

class ParameterCreateView(BaseLabMasterView, CreateView):
    model = InvestigationParameter
    form_class = ParameterForm
    template_name = 'lab/master/parameter_form.html'
    success_url = reverse_lazy('lab:parameter_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Parameter created successfully!")
        return super().form_valid(form)

class ParameterUpdateView(BaseLabMasterView, UpdateView):
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

class AgeGroupListView(BaseLabMasterView, ListView):
    model = AgeGroup
    template_name = 'lab/master/agegroup_list.html'
    context_object_name = 'age_groups'

class AgeGroupCreateView(BaseLabMasterView, CreateView):
    model = AgeGroup
    form_class = AgeGroupForm
    template_name = 'lab/master/agegroup_form.html'
    success_url = reverse_lazy('lab:agegroup_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Age Group created successfully!")
        return super().form_valid(form)

class AgeGroupUpdateView(BaseLabMasterView, UpdateView):
    model = AgeGroup
    form_class = AgeGroupForm
    template_name = 'lab/master/agegroup_form.html'
    success_url = reverse_lazy('lab:agegroup_list')

    def form_valid(self, form):
        messages.success(self.request, "Age Group updated successfully!")
        return super().form_valid(form)


# --- Reference Range Grid ---
class ReferenceRangeGridView(BaseLabMasterView, TemplateView):
    template_name = 'lab/master/reference_range_grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigations'] = Investigation.objects.filter(is_active=True)
        context['age_groups'] = AgeGroup.objects.filter(is_active=True).order_by('sort_order')
        context['diagnoses'] = Diagnosis.objects.filter(is_active=True)
        return context

class InvestigationParameterMappingView(BaseLabMasterView, TemplateView):
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

def get_all_parameters(request):
    params = InvestigationParameter.objects.filter(is_active=True).values('code', 'name').distinct().order_by('name')
    param_list = [{'id': p['code'], 'code': p['code'], 'name': p['name']} for p in params if p['code']]
    return JsonResponse({'parameters': param_list})

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

def get_investigation_parameters(request):
    investigation_id = request.GET.get('investigation_id')
    if not investigation_id:
        return JsonResponse({'parameters': []})
    
    params = InvestigationParameter.objects.filter(investigation_id=investigation_id, is_active=True).select_related('parameter')
    data = [{'id': p.id, 'parameter_id': p.code, 'name': p.name or (p.parameter.name if p.parameter else ''), 'unit': p.unit or (p.parameter.default_unit if p.parameter else '')} for p in params]
    return JsonResponse({'parameters': data})

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

class LegacyMappingView(BaseLabMasterView, TemplateView):
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
class OrderEntryView(BaseLabMasterView, TemplateView):
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

class ResultEntryListView(BaseLabMasterView, ListView):
    model = PatientInvestigationOrder
    template_name = 'lab/orders/result_entry_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return PatientInvestigationOrder.objects.filter(status=PatientInvestigationOrder.StatusChoices.PENDING).select_related('patient', 'investigation')

class ResultEntryDetailView(BaseLabMasterView, TemplateView):
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
