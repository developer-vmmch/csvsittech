import json
from django.http import JsonResponse
from django.db.models import Count, Q, Max
from django.views.decorators.csrf import csrf_exempt
from apps.core.mixins import granular_permission_required
from .models import ParameterReferenceRange, InvestigationParameter, AgeGroup, Diagnosis, Investigation

@granular_permission_required('lab_master.reference_range.view')
def api_reference_ranges_grid_list(request):
    inv_id = request.GET.get('inv_id')
    ag_id = request.GET.get('ag_id')
    diagnosis_id = request.GET.get('diagnosis_id')
    status = request.GET.get('status')

    qs = ParameterReferenceRange.objects.select_related(
        'investigation_parameter__investigation',
        'age_group',
        'diagnosis'
    )

    if inv_id:
        qs = qs.filter(investigation_parameter__investigation_id=inv_id)
    if ag_id:
        qs = qs.filter(age_group_id=ag_id)
    if diagnosis_id:
        if diagnosis_id == 'generic':
            qs = qs.filter(diagnosis__isnull=True)
        else:
            qs = qs.filter(diagnosis_id=diagnosis_id)

    # Group by (diagnosis, age_group, investigation, gender)
    # We will use python to group to handle relations easily
    groups = {}
    for r in qs:
        key = (
            r.diagnosis_id,
            r.age_group_id,
            r.investigation_parameter.investigation_id,
            r.gender
        )
        if key not in groups:
            groups[key] = {
                'diagnosis_id': r.diagnosis_id,
                'diagnosis_name': r.diagnosis.name if r.diagnosis else 'Generic (No Diagnosis)',
                'age_group_id': r.age_group_id,
                'age_group_label': r.age_group.label,
                'age_range': f"{r.age_group.min_age_value} {r.age_group.min_age_unit} - {r.age_group.max_age_value} {r.age_group.max_age_unit}",
                'investigation_id': r.investigation_parameter.investigation_id,
                'investigation_name': r.investigation_parameter.investigation.name,
                'gender': r.gender,
                'param_count': 0,
                'is_active': False
            }
        groups[key]['param_count'] += 1
        if r.is_active:
            groups[key]['is_active'] = True
            
    filtered_groups = []
    for g in groups.values():
        if status == '1' and not g['is_active']:
            continue
        if status == '0' and g['is_active']:
            continue
        filtered_groups.append(g)

    return JsonResponse({'status': 'success', 'ranges': filtered_groups})

@granular_permission_required('lab_master.reference_range.view')
def api_reference_ranges_grid_detail(request):
    inv_id = request.GET.get('inv_id')
    ag_id = request.GET.get('ag_id')
    diagnosis_id = request.GET.get('diagnosis_id')
    gender = request.GET.get('gender')
    
    qs = ParameterReferenceRange.objects.filter(
        investigation_parameter__investigation_id=inv_id,
        age_group_id=ag_id,
        gender=gender
    )
    if diagnosis_id and diagnosis_id != 'null':
        qs = qs.filter(diagnosis_id=diagnosis_id)
    else:
        qs = qs.filter(diagnosis__isnull=True)
        
    data = []
    for r in qs:
        data.append({
            'investigation_parameter_id': r.investigation_parameter_id,
            'min_value': r.min_value,
            'max_value': r.max_value,
            'critical_low': r.critical_low,
            'critical_high': r.critical_high,
            'unit': r.unit,
            'is_active': r.is_active
        })
    return JsonResponse({'status': 'success', 'data': data})

@csrf_exempt
@granular_permission_required('lab_master.reference_range.create')
def api_reference_ranges_grid_save(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis_id = data.get('diagnosis_id')
            age_group_id = data.get('age_group_id')
            investigation_id = data.get('investigation_id')
            gender = data.get('gender', 'All')
            parameters = data.get('parameters', [])
            
            if not age_group_id or not investigation_id or not parameters:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})
            
            # Save or Update each parameter
            for p in parameters:
                ip_id = p.get('investigation_parameter_id')
                if not ip_id:
                    continue
                    
                obj, created = ParameterReferenceRange.objects.get_or_create(
                    investigation_parameter_id=ip_id,
                    age_group_id=age_group_id,
                    diagnosis_id=diagnosis_id if diagnosis_id else None,
                    gender=gender,
                    defaults={'range_type': 'Numeric'}
                )
                
                min_val = p.get('min_value')
                max_val = p.get('max_value')
                cl_val = p.get('critical_low')
                ch_val = p.get('critical_high')
                
                if min_val == '': min_val = None
                if max_val == '': max_val = None
                if cl_val == '': cl_val = None
                if ch_val == '': ch_val = None
                
                obj.min_value = min_val
                obj.max_value = max_val
                obj.critical_low = cl_val
                obj.critical_high = ch_val
                obj.unit = p.get('unit', '')
                obj.is_active = p.get('is_active', True)
                obj.range_type = 'Numeric'
                obj.save()
                
            return JsonResponse({'status': 'success', 'message': 'Reference ranges saved successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method.'})

@csrf_exempt
@granular_permission_required('lab_master.reference_range.delete')
def api_reference_ranges_grid_delete(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis_id = data.get('diagnosis_id')
            age_group_id = data.get('age_group_id')
            investigation_id = data.get('investigation_id')
            gender = data.get('gender', 'All')
            
            qs = ParameterReferenceRange.objects.filter(
                investigation_parameter__investigation_id=investigation_id,
                age_group_id=age_group_id,
                gender=gender
            )
            if diagnosis_id and diagnosis_id != 'null':
                qs = qs.filter(diagnosis_id=diagnosis_id)
            else:
                qs = qs.filter(diagnosis__isnull=True)
                
            qs.delete()
            return JsonResponse({'status': 'success', 'message': 'Deleted successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method.'})

@granular_permission_required('lab_master.age_group.view')
def api_agegroup_search(request):
    query = request.GET.get('q', '').strip()
    qs = AgeGroup.objects.filter(is_active=True)
    if query:
        qs = qs.filter(label__icontains=query)
    
    results = []
    for ag in qs.order_by('sort_order'):
        results.append({
            'id': ag.id,
            'text': ag.label,
            'code': ag.code or '',
            'min_age': ag.min_age_value if ag.min_age_value is not None else '',
            'max_age': ag.max_age_value if ag.max_age_value is not None else '',
            'min_age_unit_display': ag.get_min_age_unit_display() or ag.min_age_unit or 'Years',
        })
    return JsonResponse({'results': results})
