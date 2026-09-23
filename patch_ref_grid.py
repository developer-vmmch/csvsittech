import os

file_path = r'c:\Users\Admin\Desktop\erp1\apps\lab\reference_range_grid_views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update list view
target_list = """    if inv_id:
        qs = qs.filter(investigation_parameter__investigation_id=inv_id)
    if ag_id:
        qs = qs.filter(age_group_id=ag_id)"""

new_list = """    if inv_id:
        qs = qs.filter(investigation_parameter__investigation_id=inv_id)
    if ag_id:
        qs = qs.filter(age_group_id=ag_id)
    else:
        # Also include ranges with no age group if no filter is applied, or maybe don't filter at all if not provided.
        pass
"""
if target_list in content:
    content = content.replace(target_list, new_list)

# Fix group by
target_group = """        key = (
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
                'investigation_name': r.investigation_parameter.investigation.name,"""

new_group = """        key = (
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
                'age_group_label': r.age_group.label if r.age_group else 'No Age Group',
                'age_range': f"{r.age_group.min_age_value} {r.age_group.min_age_unit} - {r.age_group.max_age_value} {r.age_group.max_age_unit}" if r.age_group else 'N/A',
                'investigation_id': r.investigation_parameter.investigation_id,
                'investigation_name': r.investigation_parameter.investigation.name,"""
if target_group in content:
    content = content.replace(target_group, new_group)

# Update save view
target_save = """            if not age_group_id or not investigation_id or not parameters:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})"""

new_save = """            if not investigation_id or not parameters:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields.'})"""
if target_save in content:
    content = content.replace(target_save, new_save)

# Update save create
target_create = """                obj, created = ParameterReferenceRange.objects.get_or_create(
                    investigation_parameter_id=ip_id,
                    age_group_id=age_group_id,
                    diagnosis_id=diagnosis_id if diagnosis_id else None,
                    gender=gender,
                    defaults={'range_type': 'Numeric'}
                )"""

new_create = """                obj, created = ParameterReferenceRange.objects.get_or_create(
                    investigation_parameter_id=ip_id,
                    age_group_id=age_group_id if age_group_id else None,
                    diagnosis_id=diagnosis_id if diagnosis_id else None,
                    gender=gender,
                    defaults={'range_type': 'Numeric'}
                )"""
if target_create in content:
    content = content.replace(target_create, new_create)

# Update detail view
target_detail = """    qs = ParameterReferenceRange.objects.filter(
        investigation_parameter__investigation_id=inv_id,
        age_group_id=ag_id,
        gender=gender
    )"""

new_detail = """    qs = ParameterReferenceRange.objects.filter(
        investigation_parameter__investigation_id=inv_id,
        gender=gender
    )
    if ag_id and ag_id != 'null':
        qs = qs.filter(age_group_id=ag_id)
    else:
        qs = qs.filter(age_group__isnull=True)"""
if target_detail in content:
    content = content.replace(target_detail, new_detail)

# Update delete view
target_delete = """            qs = ParameterReferenceRange.objects.filter(
                investigation_parameter__investigation_id=investigation_id,
                age_group_id=age_group_id,
                gender=gender
            )"""

new_delete = """            qs = ParameterReferenceRange.objects.filter(
                investigation_parameter__investigation_id=investigation_id,
                gender=gender
            )
            if age_group_id and age_group_id != 'null':
                qs = qs.filter(age_group_id=age_group_id)
            else:
                qs = qs.filter(age_group__isnull=True)"""
if target_delete in content:
    content = content.replace(target_delete, new_delete)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated reference_range_grid_views.py")
