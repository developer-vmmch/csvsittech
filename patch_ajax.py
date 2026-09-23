import os

VIEW_CODE = """
@csrf_exempt
def api_diagnosis_investigations(request):
    try:
        diag_id = request.GET.get('diag_id')
        patient_id = request.GET.get('patient_id')
        
        if not diag_id:
            return JsonResponse({'status': 'success', 'investigations': []})
            
        from apps.lab.models import DiagnosisInvestigationMap
        mappings = DiagnosisInvestigationMap.objects.filter(diagnosis_id=diag_id, is_active=True).select_related('investigation', 'age_group')
        
        patient_age_days = 0
        patient_gender = 'All'
        if patient_id:
            from apps.patients.models import Patient
            try:
                p = Patient.objects.get(id=patient_id)
                patient_age_days = (p.age_years or 0) * 365 + (p.age_months or 0) * 30 + (p.age_days or 0)
                patient_gender = p.gender
            except Patient.DoesNotExist:
                pass
                
        results = {}
        for m in mappings:
            inv = m.investigation
            if m.age_group:
                ag = m.age_group
                # Compare Gender
                if ag.gender != 'All' and ag.gender != patient_gender:
                    continue
                # Compare Age
                if patient_id:
                    multiplier = {'Days': 1, 'Months': 30, 'Years': 365, 'Weeks': 7}
                    min_days = (ag.min_age_value or 0) * multiplier.get(ag.min_age_unit, 365)
                    max_days = (ag.max_age_value or 150) * multiplier.get(ag.max_age_unit, 365)
                    if not (min_days <= patient_age_days <= max_days):
                        continue
                        
            results[inv.id] = {
                'id': inv.id,
                'name': inv.name,
                'short_name': getattr(inv, 'short_name', '')
            }
            
        return JsonResponse({'status': 'success', 'investigations': list(results.values())})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
"""

with open(r'C:\Users\Admin\Desktop\erp1\apps\lab\views.py', 'a') as f:
    f.write(VIEW_CODE)
print("View added")
