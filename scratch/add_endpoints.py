import os
import re

VIEWS_FILE = "apps/lab/views.py"
URLS_FILE = "apps/lab/urls.py"

with open(VIEWS_FILE, "r") as f:
    views_content = f.read()

endpoints = """
@csrf_exempt
@login_required
def api_lab_diagnosis_save(request):
    if request.method == 'POST':
        try:
            import json
            from .models import LabDiagnosis
            data = json.loads(request.body)
            diag_id = data.get('id')
            name = data.get('name', '').strip()
            code = data.get('code', '').strip()
            if not name or not code:
                return JsonResponse({'status': 'error', 'message': 'Name and Code required'})
            
            duplicate_code = LabDiagnosis.objects.filter(code__iexact=code)
            duplicate_name = LabDiagnosis.objects.filter(name__iexact=name)
            if diag_id:
                duplicate_code = duplicate_code.exclude(id=diag_id)
                duplicate_name = duplicate_name.exclude(id=diag_id)
                
            if duplicate_name.exists(): return JsonResponse({'status': 'error', 'message': f'Name {name} exists.'})
            if duplicate_code.exists(): return JsonResponse({'status': 'error', 'message': f'Code {code} exists.'})
            
            if diag_id:
                d = LabDiagnosis.objects.get(id=diag_id)
                d.name = name; d.code = code; d.chapter = data.get('chapter', ''); d.synonyms = data.get('synonyms', ''); d.legacy_code = data.get('legacy_code', ''); d.is_active = data.get('is_active', True)
                d.save()
            else:
                d = LabDiagnosis.objects.create(name=name, code=code, chapter=data.get('chapter', ''), synonyms=data.get('synonyms', ''), legacy_code=data.get('legacy_code', ''), is_active=data.get('is_active', True))
                
            return JsonResponse({'status': 'success', 'message': 'Saved', 'data': {'id': d.id, 'name': d.name, 'code': d.code, 'chapter': d.chapter, 'synonyms': d.synonyms, 'legacy_code': d.legacy_code, 'is_active': d.is_active}})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})

@csrf_exempt
@login_required
def api_lab_diagnosis_delete(request, pk):
    if request.method == 'POST':
        try:
            from .models import LabDiagnosis
            LabDiagnosis.objects.get(id=pk).delete()
            return JsonResponse({'status': 'success', 'message': 'Deleted'})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})

@csrf_exempt
@login_required
def api_investigation_delete(request, pk):
    if request.method == 'POST':
        try:
            from .models import Investigation
            Investigation.objects.get(id=pk).delete()
            return JsonResponse({'status': 'success', 'message': 'Deleted'})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})

@csrf_exempt
@login_required
def api_parameter_delete(request, pk):
    if request.method == 'POST':
        try:
            from .models import Parameter
            Parameter.objects.get(id=pk).delete()
            return JsonResponse({'status': 'success', 'message': 'Deleted'})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})

@csrf_exempt
@login_required
def api_agegroup_save(request):
    if request.method == 'POST':
        try:
            import json
            from .models import AgeGroup
            data = json.loads(request.body)
            ag_id = data.get('id')
            name = data.get('name', '').strip()
            if not name: return JsonResponse({'status': 'error', 'message': 'Name required'})
            
            duplicate_name = AgeGroup.objects.filter(name__iexact=name)
            if ag_id: duplicate_name = duplicate_name.exclude(id=ag_id)
            if duplicate_name.exists(): return JsonResponse({'status': 'error', 'message': f'Name {name} exists.'})
            
            if ag_id:
                d = AgeGroup.objects.get(id=ag_id)
                d.name = name; d.min_age = data.get('min_age', 0); d.max_age = data.get('max_age', 0); d.age_unit = data.get('age_unit', 'Years'); d.gender = data.get('gender', 'All')
                d.save()
            else:
                d = AgeGroup.objects.create(name=name, min_age=data.get('min_age', 0), max_age=data.get('max_age', 0), age_unit=data.get('age_unit', 'Years'), gender=data.get('gender', 'All'))
                
            return JsonResponse({'status': 'success', 'message': 'Saved', 'data': {'id': d.id, 'name': d.name, 'min_age': d.min_age, 'max_age': d.max_age, 'age_unit': d.age_unit, 'gender': d.gender}})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})

@csrf_exempt
@login_required
def api_agegroup_delete(request, pk):
    if request.method == 'POST':
        try:
            from .models import AgeGroup
            AgeGroup.objects.get(id=pk).delete()
            return JsonResponse({'status': 'success', 'message': 'Deleted'})
        except Exception as e: return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid'})
"""

if "api_lab_diagnosis_save" not in views_content:
    with open(VIEWS_FILE, "a") as f:
        f.write("\n" + endpoints + "\n")

with open(URLS_FILE, "r") as f:
    urls_content = f.read()

if "api_lab_diagnosis_save" not in urls_content:
    urls_content = urls_content.replace(
        "from .views import (",
        "from .views import (\n    api_lab_diagnosis_save, api_lab_diagnosis_delete, api_investigation_delete, api_parameter_delete, api_agegroup_save, api_agegroup_delete,"
    )
    urls_content = urls_content.replace(
        "path('api/diagnosis/save/', api_diagnosis_save, name='api_diagnosis_save'),",
        "path('api/diagnosis/save/', api_diagnosis_save, name='api_diagnosis_save'),\n    path('api/lab-diagnosis/save/', api_lab_diagnosis_save, name='api_lab_diagnosis_save'),\n    path('api/lab-diagnosis/<int:pk>/delete/', api_lab_diagnosis_delete, name='api_lab_diagnosis_delete'),\n    path('api/investigation/<int:pk>/delete/', api_investigation_delete, name='api_investigation_delete'),\n    path('api/parameter/<int:pk>/delete/', api_parameter_delete, name='api_parameter_delete'),\n    path('api/age-group/save/', api_agegroup_save, name='api_agegroup_save'),\n    path('api/age-group/<int:pk>/delete/', api_agegroup_delete, name='api_agegroup_delete'),"
    )
    with open(URLS_FILE, "w") as f:
        f.write(urls_content)

print("Endpoints added.")
