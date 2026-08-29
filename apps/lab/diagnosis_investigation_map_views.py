import json
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from apps.core.mixins import granular_permission_required
from .models import DiagnosisInvestigationMap, Diagnosis, Investigation, AgeGroup

@granular_permission_required('lab_master.diagnosis_investigation_map.view')
def diagnosis_investigation_mapping_view(request):
    return render(request, 'lab/master/diagnosis_investigation_mapping.html')

@granular_permission_required('lab_master.diagnosis_investigation_map.view')
def api_diagnosis_investigation_map_list(request):
    diag_id = request.GET.get('diagnosis_id')
    age_group_id = request.GET.get('age_group_id')
    status = request.GET.get('status')
    q = request.GET.get('q', '').strip()
    
    qs = DiagnosisInvestigationMap.objects.select_related('diagnosis', 'investigation', 'age_group')
    
    if diag_id:
        qs = qs.filter(diagnosis_id=diag_id)
    if age_group_id:
        qs = qs.filter(age_group_id=age_group_id)
        
    # Group by diagnosis and age group
    groups = {}
    for r in qs:
        key = (r.diagnosis_id, r.age_group_id)
        if key not in groups:
            groups[key] = {
                'diagnosis_id': r.diagnosis_id,
                'diagnosis_name': r.diagnosis.name if r.diagnosis else 'Unknown',
                'age_group_id': r.age_group_id,
                'age_group_name': r.age_group.label if r.age_group else 'Unknown',
                'age_range': f"{r.age_group.min_age_value} - {r.age_group.max_age_value} {r.age_group.get_min_age_unit_display()}" if r.age_group else 'Unknown',
                'investigations': [],
                'is_active': False
            }
        
        groups[key]['investigations'].append(r.investigation.name)
        if r.is_active:
            groups[key]['is_active'] = True
            
    # Format investigations as comma-separated string and apply filters
    results = []
    q_lower = q.lower() if q else None
    
    for g in groups.values():
        if status == '1' and not g['is_active']:
            continue
        if status == '0' and g['is_active']:
            continue
            
        inv_names_str = ", ".join(g['investigations'])
        diag_name_lower = g['diagnosis_name'].lower()
        inv_names_lower = inv_names_str.lower()
        
        if q_lower:
            if q_lower not in diag_name_lower and q_lower not in inv_names_lower:
                continue
                
        g['investigation_names'] = inv_names_str
        g['investigation_count'] = len(g['investigations'])
        del g['investigations']
        results.append(g)
        
    return JsonResponse({'status': 'success', 'mappings': results})

@granular_permission_required('lab_master.diagnosis_investigation_map.view')
def api_diagnosis_investigation_map_detail(request):
    diag_id = request.GET.get('diagnosis_id')
    age_group_id = request.GET.get('age_group_id')
    if not diag_id or not age_group_id:
        return JsonResponse({'status': 'error', 'message': 'Missing diagnosis_id or age_group_id'})
        
    qs = DiagnosisInvestigationMap.objects.filter(diagnosis_id=diag_id, age_group_id=age_group_id).select_related('investigation')
    
    data = []
    for r in qs:
        data.append({
            'investigation_id': r.investigation_id,
            'investigation_name': r.investigation.name,
            'investigation_code': r.investigation.code,
            'sample_type': r.investigation.sample_type.name if hasattr(r.investigation, 'sample_type') and r.investigation.sample_type else 'Not Specified',
            'is_default': r.is_default,
            'is_active': r.is_active
        })
    return JsonResponse({'status': 'success', 'data': data})

@csrf_exempt
@granular_permission_required('lab_master.diagnosis_investigation_map.create')
def api_diagnosis_investigation_map_save(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis_id = data.get('diagnosis_id')
            age_group_id = data.get('age_group_id')
            investigations = data.get('investigations', [])
            
            if not diagnosis_id or not age_group_id:
                return JsonResponse({'status': 'error', 'message': 'Missing diagnosis_id or age_group_id'})
                
            # Keep track of updated/created
            existing_inv_ids = set()
            for inv in investigations:
                inv_id = inv.get('investigation_id')
                if not inv_id:
                    continue
                existing_inv_ids.add(inv_id)
                
                obj, created = DiagnosisInvestigationMap.objects.get_or_create(
                    diagnosis_id=diagnosis_id,
                    age_group_id=age_group_id,
                    investigation_id=inv_id
                )
                obj.is_default = inv.get('is_default', False)
                obj.is_active = inv.get('is_active', True)
                obj.save()
                
            # Remove omitted mappings
            DiagnosisInvestigationMap.objects.filter(
                diagnosis_id=diagnosis_id,
                age_group_id=age_group_id
            ).exclude(investigation_id__in=existing_inv_ids).delete()
            
            return JsonResponse({'status': 'success', 'message': 'Mapping saved successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method.'})

@csrf_exempt
@granular_permission_required('lab_master.diagnosis_investigation_map.delete')
def api_diagnosis_investigation_map_delete(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis_id = data.get('diagnosis_id')
            age_group_id = data.get('age_group_id')
            if diagnosis_id and age_group_id:
                DiagnosisInvestigationMap.objects.filter(diagnosis_id=diagnosis_id, age_group_id=age_group_id).delete()
                return JsonResponse({'status': 'success', 'message': 'Deleted successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method.'})
