import os
import re

source = '/tmp/import_views_index.py'
dest = 'apps/lab/import_views.py'

with open(source, 'r') as f:
    content = f.read()

# Make sure imports are clean (only replace the first occurrence)
if "import os" not in content[:500]:
    content = content.replace("import json", "import json\nimport os", 1)

if "import uuid" not in content[:500]:
    content = content.replace("import os", "import os\nimport uuid", 1)

if "from django.core.files.storage import FileSystemStorage" not in content[:500]:
    content = content.replace("import uuid", "import uuid\nfrom django.core.files.storage import FileSystemStorage", 1)

if "LabDiagnosis" not in content[:500]:
    content = content.replace("Diagnosis, AgeGroup", "Diagnosis, LabDiagnosis, AgeGroup", 1)
    content = content.replace("Diagnosis, DiagnosisImportHistory", "Diagnosis, LabDiagnosis, DiagnosisImportHistory", 1)

# Remove the old api_diagnosis_preview and api_diagnosis_import and replace with our new ones.
start_match = re.search(r"def api_diagnosis_download_template\(request\):", content)
# We will drop from api_diagnosis_download_template up to api_investigation_download_template
end_match = re.search(r"def api_investigation_download_template\(request\):", content)

if not start_match or not end_match:
    print("Could not find start or end matches in index!")
    exit(1)

start_idx = start_match.start()
end_idx = end_match.start()

new_logic = """
def api_diagnosis_download_template(request):
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame({
        'icd_code': ['BA00', 'BA01'],
        'diagnosis_name': ['Essential hypertension', 'Secondary hypertension'],
        'category': ['Cardiovascular', 'Cardiovascular'],
        'synonyms': ['High BP, HTN', ''],
        'active': ['Yes', 'Yes']
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="diagnosis_import_template.xlsx"'
    return response

def api_lab_diagnosis_download_template(request):
    import pandas as pd
    from io import BytesIO
    df = pd.DataFrame({
        'icd_code': ['BA00', 'BA01'],
        'diagnosis_name': ['Essential hypertension', 'Secondary hypertension'],
        'category': ['Cardiovascular', 'Cardiovascular'],
        'synonyms': ['High BP, HTN', ''],
        'class_kind': ['', ''],
        'active': ['Yes', 'Yes']
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="lab_diagnosis_import_template.xlsx"'
    return response

def get_diagnosis_rows(f, filename):
    import pandas as pd
    if filename.endswith('.csv'):
        df = pd.read_csv(f, dtype=str)
    else:
        df = pd.read_excel(f, dtype=str)
    
    df_columns = [str(c).lower().strip() for c in df.columns]
    df.columns = df_columns
    
    for index, row in df.iterrows():
        yield index + 2, row

def process_preview(request, is_lab_diagnosis=False):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        from django.conf import settings
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_imports'))
        file_ext = os.path.splitext(filename)[1]
        if file_ext.lower() not in ['.csv', '.xlsx', '.xls']:
            return JsonResponse({'status': 'error', 'message': 'Unsupported file format. Please upload .csv or .xlsx'})
            
        upload_id = str(uuid.uuid4())
        saved_name = fs.save(f"{upload_id}{file_ext}", file)
        file_path = fs.path(saved_name)
        
        preview_data = []
        file_codes = set()
        file_names = set()
        
        ModelClass = LabDiagnosis if is_lab_diagnosis else Diagnosis
        existing_codes = set(ModelClass.objects.exclude(code__isnull=True).exclude(code='').values_list('code', flat=True))
        existing_names = set(ModelClass.objects.values_list('name', flat=True))
        
        with open(file_path, 'rb') as f:
            for row_num, row in get_diagnosis_rows(f, filename):
                icd_code = str(row.get('icd_code', '')).strip()
                if icd_code == 'nan': icd_code = ''
                
                diag_name = str(row.get('diagnosis_name', '')).strip()
                if diag_name == 'nan': diag_name = ''
                
                category = str(row.get('category', '')).strip() or 'Hospital Legacy'
                if category == 'nan': category = 'Hospital Legacy'
                
                synonyms = str(row.get('synonyms', '')).strip()
                if synonyms == 'nan': synonyms = ''
                
                class_kind = str(row.get('class_kind', '')).strip()
                if class_kind == 'nan': class_kind = ''
                
                active_str = str(row.get('status', row.get('active', 'Yes'))).strip().lower()
                is_active = True if active_str in ['yes', 'y', 'true', '1', 'active'] else False
                
                status = 'Valid'
                error_msg = ''
                
                if not diag_name:
                    status = 'Error'
                    error_msg = 'Diagnosis Name is required'
                elif icd_code and len(icd_code) > 50:
                    status = 'Error'
                    error_msg = 'ICD Code is too long'
                elif icd_code and icd_code in file_codes:
                    status = 'Error'
                    error_msg = 'Duplicate ICD Code in file'
                elif not icd_code and diag_name in file_names:
                    status = 'Error'
                    error_msg = 'Duplicate Diagnosis Name in file'
                elif icd_code and icd_code in existing_codes:
                    status = 'Duplicate'
                    error_msg = 'ICD Code already exists in database'
                elif not icd_code and diag_name in existing_names:
                    status = 'Duplicate'
                    error_msg = 'Diagnosis Name already exists in database'
                
                if icd_code: file_codes.add(icd_code)
                if diag_name: file_names.add(diag_name)
                
                preview_data.append({
                    'row_num': row_num,
                    'icd_code': icd_code,
                    'diagnosis_name': diag_name,
                    'category': category,
                    'class_kind': class_kind,
                    'synonyms': synonyms,
                    'active': is_active,
                    'status': status,
                    'error': error_msg
                })
                
        return JsonResponse({
            'status': 'success',
            'filename': filename,
            'upload_id': upload_id,
            'data': preview_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error parsing file: {str(e)}'})

def process_import(request, is_lab_diagnosis=False):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
        
    upload_id = request.POST.get('upload_id')
    filename = request.POST.get('filename')
    update_duplicates = request.POST.get('update_duplicates') == 'true'
    
    if not upload_id or not filename:
        return JsonResponse({'status': 'error', 'message': 'File missing. Please start again.'})
        
    from django.conf import settings
    fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_imports'))
    file_ext = os.path.splitext(filename)[1]
    saved_name = f"{upload_id}{file_ext}"
    
    if not fs.exists(saved_name):
        return JsonResponse({'status': 'error', 'message': 'File missing. Please start again.'})
        
    file_path = fs.path(saved_name)
    
    ModelClass = LabDiagnosis if is_lab_diagnosis else Diagnosis
    
    imported = 0
    updated = 0
    duplicates = 0
    failed = 0
    
    from django.db import transaction
    try:
        existing_objs = ModelClass.objects.all()
        existing_by_code = {obj.code: obj for obj in existing_objs if obj.code}
        existing_by_name = {obj.name: obj for obj in existing_objs if obj.name}
        
        creates = []
        updates = []
        
        file_codes = set()
        file_names = set()
        
        with open(file_path, 'rb') as f:
            for row_num, row in get_diagnosis_rows(f, filename):
                icd_code = str(row.get('icd_code', '')).strip()
                if icd_code == 'nan': icd_code = ''
                
                diag_name = str(row.get('diagnosis_name', '')).strip()
                if diag_name == 'nan': diag_name = ''
                
                category = str(row.get('category', '')).strip() or 'Hospital Legacy'
                if category == 'nan': category = 'Hospital Legacy'
                
                synonyms = str(row.get('synonyms', '')).strip()
                if synonyms == 'nan': synonyms = ''
                
                class_kind = str(row.get('class_kind', '')).strip()
                if class_kind == 'nan': class_kind = ''
                
                active_str = str(row.get('status', row.get('active', 'Yes'))).strip().lower()
                is_active = True if active_str in ['yes', 'y', 'true', '1', 'active'] else False
                
                if not diag_name or (icd_code and len(icd_code) > 50):
                    failed += 1
                    continue
                    
                is_file_dup = False
                if icd_code:
                    if icd_code in file_codes: is_file_dup = True
                    file_codes.add(icd_code)
                else:
                    if diag_name in file_names: is_file_dup = True
                    file_names.add(diag_name)
                    
                if is_file_dup:
                    failed += 1
                    continue
                    
                obj = None
                if icd_code and icd_code in existing_by_code:
                    obj = existing_by_code[icd_code]
                elif not icd_code and diag_name in existing_by_name:
                    obj = existing_by_name[diag_name]
                    
                if obj:
                    if update_duplicates:
                        obj.name = diag_name
                        if not obj.chapter and category: obj.chapter = category
                        if not obj.synonyms and synonyms: obj.synonyms = synonyms
                        if not getattr(obj, 'class_kind', None) and class_kind:
                            if hasattr(obj, 'class_kind'): obj.class_kind = class_kind
                        if is_active: obj.is_active = True
                        updates.append(obj)
                    else:
                        duplicates += 1
                else:
                    save_code = icd_code
                    if not save_code:
                        slug = "".join(c for c in diag_name.upper().replace(" ", "_") if c.isalnum() or c == "_")[:20]
                        save_code = f"DX-{slug}-{uuid.uuid4().hex[:4].upper()}"
                        
                    creates.append(ModelClass(
                        code=save_code,
                        name=diag_name,
                        chapter=category,
                        synonyms=synonyms,
                        is_active=is_active,
                        source='Import',
                        **({'class_kind': class_kind} if hasattr(ModelClass, 'class_kind') else {})
                    ))
        
        with transaction.atomic():
            if updates:
                update_fields = ['name', 'chapter', 'synonyms', 'is_active']
                if hasattr(ModelClass, 'class_kind'):
                    update_fields.append('class_kind')
                ModelClass.objects.bulk_update(updates, update_fields, batch_size=1000)
                updated = len(updates)
            
            if creates:
                ModelClass.objects.bulk_create(creates, batch_size=1000)
                imported = len(creates)
                
            history = DiagnosisImportHistory.objects.create(
                file_name=filename,
                uploaded_by=request.user if request.user.is_authenticated else None,
                total_rows=imported + updated + duplicates + failed,
                imported=imported,
                updated=updated,
                duplicates=duplicates,
                failed=failed,
                status='Completed'
            )
            
        return JsonResponse({
            'status': 'success',
            'summary': {
                'total': imported + updated + duplicates + failed,
                'imported': imported,
                'updated': updated,
                'duplicates': duplicates,
                'failed': failed,
                'history_id': history.id
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})

def api_diagnosis_preview(request):
    return process_preview(request, is_lab_diagnosis=False)

def api_diagnosis_import(request):
    return process_import(request, is_lab_diagnosis=False)

def api_lab_diagnosis_preview(request):
    return process_preview(request, is_lab_diagnosis=True)

def api_lab_diagnosis_import(request):
    return process_import(request, is_lab_diagnosis=True)

"""

new_content = content[:start_idx] + new_logic + content[end_idx:]

with open(dest, 'w') as f:
    f.write(new_content)
