from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from .models import Diagnosis, DiagnosisImportHistory, InvestigationImportHistory, ParameterImportHistory, AgeGroupImportHistory, ReferenceRangeImportHistory
import pandas as pd
import io
import csv
import json

class DiagnosisImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_diagnosis.html'
    menu_key = 'administration'

class DiagnosisImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = DiagnosisImportHistory
    template_name = 'lab/master/import_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

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

def api_diagnosis_preview(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unsupported file format. Please upload .csv or .xlsx'})
            
        required_columns = ['icd_code', 'diagnosis_name', 'category', 'synonyms', 'active']
        
        # Check if empty
        if df.empty:
            return JsonResponse({'status': 'error', 'message': 'Uploaded file is empty.'})
            
        # Check columns
        df_columns = [c.lower().strip() for c in df.columns]
        for req in required_columns:
            if req not in df_columns:
                return JsonResponse({'status': 'error', 'message': f'Missing required column: {req}'})
                
        # Rename columns to standard
        df.columns = df_columns
        
        preview_data = []
        file_codes = set()
        
        # Fetch existing codes for faster checking
        existing_codes = set(Diagnosis.objects.values_list('code', flat=True))
        
        for index, row in df.iterrows():
            row_num = index + 2 # Excel row number (header is 1, data starts at 2)
            
            icd_code = str(row.get('icd_code', '')).strip()
            if icd_code == 'nan' or not icd_code:
                icd_code = ''
            
            diag_name = str(row.get('diagnosis_name', '')).strip()
            if diag_name == 'nan':
                diag_name = ''
                
            category = str(row.get('category', '')).strip()
            if category == 'nan':
                category = ''
                
            synonyms = str(row.get('synonyms', '')).strip()
            if synonyms == 'nan':
                synonyms = ''
                
            active_str = str(row.get('active', '')).strip().lower()
            is_active = True if active_str in ['yes', 'y', 'true', '1'] else False
            
            status = 'Valid'
            error_msg = ''
            
            if not icd_code:
                status = 'Error'
                error_msg = 'ICD Code is required'
            elif not diag_name:
                status = 'Error'
                error_msg = 'Diagnosis Name is required'
            elif len(icd_code) > 50:
                status = 'Error'
                error_msg = 'ICD Code is too long'
            elif icd_code in file_codes:
                status = 'Error'
                error_msg = 'Duplicate ICD Code in file'
            elif icd_code in existing_codes:
                status = 'Duplicate'
                error_msg = 'ICD Code already exists in database'
            
            if icd_code:
                file_codes.add(icd_code)
                
            preview_data.append({
                'row_num': row_num,
                'icd_code': icd_code,
                'diagnosis_name': diag_name,
                'category': category,
                'synonyms': synonyms,
                'active': is_active,
                'status': status,
                'error': error_msg
            })
            
        return JsonResponse({
            'status': 'success', 
            'filename': filename,
            'data': preview_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error parsing file: {str(e)}'})

def api_diagnosis_import(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
        
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_duplicates = data.get('update_duplicates', False)
        
        imported = 0
        updated = 0
        duplicates = 0
        failed = 0
        
        from django.db import transaction
        
        with transaction.atomic():
            for row in rows:
                if row['status'] == 'Error':
                    failed += 1
                    continue
                    
                code = row['icd_code']
                
                try:
                    obj = Diagnosis.objects.filter(code=code).first()
                    
                    if obj:
                        if update_duplicates:
                            obj.name = row['diagnosis_name']
                            obj.chapter = row['category']
                            obj.synonyms = row['synonyms']
                            obj.is_active = row['active']
                            obj.source = 'Import'
                            obj.save()
                            updated += 1
                        else:
                            duplicates += 1
                    else:
                        Diagnosis.objects.create(
                            code=code,
                            name=row['diagnosis_name'],
                            chapter=row['category'],
                            synonyms=row['synonyms'],
                            is_active=row['active'],
                            source='Import'
                        )
                        imported += 1
                except Exception as e:
                    print(f"Error importing row {row['row_num']}: {str(e)}")
                    failed += 1
                    
            history = DiagnosisImportHistory.objects.create(
                file_name=filename,
                uploaded_by=request.user if request.user.is_authenticated else None,
                total_rows=len(rows),
                imported=imported,
                updated=updated,
                duplicates=duplicates,
                failed=failed,
                status='Completed'
            )
            
        return JsonResponse({
            'status': 'success',
            'summary': {
                'total': len(rows),
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

# --- Investigation Import ---

class InvestigationImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_investigation.html'
    menu_key = 'administration'

class InvestigationImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = InvestigationImportHistory
    template_name = 'lab/master/import_investigation_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_investigation_download_template(request):
    df = pd.DataFrame({
        'investigation_code': ['INV-001', 'INV-002'],
        'investigation_name': ['Complete Blood Count (CBC)', 'Liver Function Test'],
        'category': ['Hematology', 'Biochemistry'],
        'specimen_or_sample': ['Whole Blood', 'Serum'],
        'parameters': ['Hemoglobin; RBC Count; WBC Count; Platelet Count', 'SGPT; SGOT; Bilirubin'],
        'active': ['Yes', 'Yes']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="investigation_import_template.xlsx"'
    return response

def api_investigation_preview(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unsupported file format. Please upload .csv or .xlsx'})
            
        required_columns = ['investigation_code', 'investigation_name', 'category', 'specimen_or_sample', 'parameters', 'active']
        
        if df.empty:
            return JsonResponse({'status': 'error', 'message': 'Uploaded file is empty.'})
            
        df_columns = [c.lower().strip() for c in df.columns]
        for req in required_columns:
            if req not in df_columns:
                return JsonResponse({'status': 'error', 'message': f'Missing required column: {req}'})
                
        df.columns = df_columns
        
        preview_data = []
        file_inv_codes = set()
        
        from .models import Investigation, InvestigationParameter
        existing_inv_codes = set(Investigation.objects.values_list('code', flat=True))
        
        for index, row in df.iterrows():
            row_num = index + 2
            
            inv_code = str(row.get('investigation_code', '')).strip()
            if inv_code == 'nan' or not inv_code: inv_code = ''
            
            inv_name = str(row.get('investigation_name', '')).strip()
            if inv_name == 'nan': inv_name = ''
                
            category = str(row.get('category', '')).strip()
            if category == 'nan': category = ''
                
            specimen = str(row.get('specimen_or_sample', '')).strip()
            if specimen == 'nan': specimen = ''
                
            active_str = str(row.get('active', '')).strip().lower()
            is_active = True if active_str in ['yes', 'y', 'true', '1'] else False
            
            params_raw = str(row.get('parameters', '')).strip()
            if params_raw == 'nan': params_raw = ''
            
            parameters_list = [p.strip() for p in params_raw.split(';') if p.strip()]
            
            status = 'Valid'
            error_msg = ''
            
            if not inv_code:
                status = 'Error'
                error_msg = 'Investigation Code is required'
            elif not inv_name:
                status = 'Error'
                error_msg = 'Investigation Name is required'
            elif inv_code in file_inv_codes:
                status = 'Error'
                error_msg = 'Duplicate Investigation Code in file'
            elif inv_code in existing_inv_codes:
                status = 'Duplicate'
                error_msg = 'Investigation Code already exists in database'
            
            if inv_code:
                file_inv_codes.add(inv_code)
                
            preview_data.append({
                'row_num': row_num,
                'investigation_code': inv_code,
                'investigation_name': inv_name,
                'category': category,
                'specimen_or_sample': specimen,
                'parameters': parameters_list,
                'active': is_active,
                'status': status,
                'error': error_msg
            })
            
        return JsonResponse({
            'status': 'success', 
            'filename': filename,
            'data': preview_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error parsing file: {str(e)}'})

def api_investigation_import(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
        
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_duplicates = data.get('update_duplicates', False)
        
        inv_imported = 0
        inv_updated = 0
        inv_skipped = 0
        param_imported = 0
        param_updated = 0
        param_skipped = 0
        failed = 0
        
        from django.db import transaction
        from .models import Investigation, InvestigationParameter, LabDepartment, SampleType
        
        with transaction.atomic():
            for row in rows:
                if row['status'] == 'Error':
                    failed += 1
                    continue
                    
                inv_code = row['investigation_code']
                
                try:
                    dept = None
                    if row['category']:
                        dept, _ = LabDepartment.objects.get_or_create(name=row['category'])
                        
                    samp = None
                    if row['specimen_or_sample']:
                        samp, _ = SampleType.objects.get_or_create(name=row['specimen_or_sample'])
                
                    inv = Investigation.objects.filter(code=inv_code).first()
                    
                    if inv:
                        if update_duplicates:
                            inv.name = row['investigation_name']
                            inv.department = dept
                            inv.sample_type = samp
                            inv.is_active = row['active']
                            inv.save()
                            inv_updated += 1
                        else:
                            inv_skipped += 1
                            continue # skip parameters too if skipping investigation
                    else:
                        inv = Investigation.objects.create(
                            code=inv_code,
                            name=row['investigation_name'],
                            department=dept,
                            sample_type=samp,
                            is_active=row['active'],
                            is_panel=len(row['parameters']) > 1
                        )
                        inv_imported += 1
                        
                    # Process parameters
                    for idx, p_name in enumerate(row['parameters']):
                        # Auto-generate a simple code if not provided
                        p_code = f"{inv_code}-P{idx+1}"
                        
                        param = InvestigationParameter.objects.filter(investigation=inv, code=p_code).first()
                        if param:
                            if update_duplicates:
                                param.name = p_name
                                param.display_order = idx + 1
                                param.save()
                                param_updated += 1
                            else:
                                param_skipped += 1
                        else:
                            InvestigationParameter.objects.create(
                                investigation=inv,
                                code=p_code,
                                name=p_name,
                                display_order=idx + 1,
                                result_type='Numeric', # default
                                is_active=True
                            )
                            param_imported += 1
                            
                except Exception as e:
                    print(f"Error importing row {row['row_num']}: {str(e)}")
                    failed += 1
                    
            history = InvestigationImportHistory.objects.create(
                file_name=filename,
                uploaded_by=request.user if request.user.is_authenticated else None,
                total_investigations=len(rows),
                total_parameters=sum(len(r['parameters']) for r in rows),
                investigations_imported=inv_imported,
                investigations_updated=inv_updated,
                investigations_skipped=inv_skipped,
                parameters_imported=param_imported,
                parameters_updated=param_updated,
                parameters_skipped=param_skipped,
                failed_records=failed,
                status='Completed'
            )
            
        return JsonResponse({
            'status': 'success',
            'summary': {
                'total_investigations': len(rows),
                'total_parameters': sum(len(r['parameters']) for r in rows),
                'inv_imported': inv_imported,
                'inv_updated': inv_updated,
                'inv_skipped': inv_skipped,
                'param_imported': param_imported,
                'param_updated': param_updated,
                'param_skipped': param_skipped,
                'failed': failed,
                'history_id': history.id
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})

# --- Age Group Import ---

from .models import AgeGroupImportHistory, ParameterImportHistory, AgeGroup, ParameterReferenceRange

class AgeGroupImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_agegroup.html'
    menu_key = 'administration'

class AgeGroupImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = AgeGroupImportHistory
    template_name = 'lab/master/import_agegroup_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_agegroup_download_template(request):
    df = pd.DataFrame({
        'age_group_code': ['NEWBORN', 'INFANT'],
        'age_group_name': ['Newborn', 'Infant'],
        'minimum_age': [0, 29],
        'maximum_age': [28, 12],
        'age_unit': ['Days', 'Months'],
        'gender': ['All', 'All'],
        'pregnancy_applicable': ['No', 'No'],
        'display_order': [1, 2],
        'active': ['Yes', 'Yes']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="agegroup_import_template.xlsx"'
    return response

def api_agegroup_preview(request):
    if request.method != 'POST': return JsonResponse({'success': False, 'message': 'Invalid method'})
    if 'file' not in request.FILES: return JsonResponse({'success': False, 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        import pandas as pd
        if filename.endswith('.csv'): 
            import csv
            import io
            decoded_file = file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file))
            raw_headers = next(reader, [])
            rows_data = list(reader)
        elif filename.endswith('.xlsx'): 
            from openpyxl import load_workbook
            try:
                workbook = load_workbook(file, read_only=True, data_only=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("AGE GROUP IMPORT ERROR:", repr(e))
                return JsonResponse({'success': False, 'error_type': 'VALIDATION_ERROR', 'errors': [{'row': 0, 'field': 'File', 'value': '', 'message': 'Could not read Excel file'}]})
            if 'Template' not in workbook.sheetnames:
                return JsonResponse({'success': False, 'error_type': 'VALIDATION_ERROR', 'errors': [{'row': 0, 'field': 'Worksheet', 'value': '', 'message': "Import worksheet 'Template' not found."}]})
            worksheet = workbook['Template']
            raw_headers = []
            rows_data = []
            for i, row in enumerate(worksheet.iter_rows(values_only=True)):
                if i == 0:
                    raw_headers = list(row)
                else:
                    if any(cell is not None and str(cell).strip() != '' for cell in row):
                        rows_data.append(list(row))
        else: 
            return JsonResponse({'success': False, 'message': 'Unsupported format'})
            
        required = ['age_group_code', 'age_group_name', 'minimum_age', 'maximum_age', 'age_unit', 'gender', 'pregnancy_applicable', 'display_order', 'active']
        headers = [str(h).strip().lower() if h else "" for h in raw_headers]
        
        for req in required:
            if req not in headers:
                return JsonResponse({'success': False, 'error_type': 'VALIDATION_ERROR', 'errors': [{'row': 1, 'field': 'Header', 'value': '', 'message': f'Missing required column: {req}'}]})
                
        col_idx = {req: headers.index(req) for req in required}
        
        preview_data = []
        validation_errors = []
        file_codes = set()
        
        from .models import AgeGroup
        existing = set(AgeGroup.objects.values_list('code', flat=True))
        
        valid_rows = 0
        invalid_rows = 0
        duplicate_rows = 0
        
        def parse_optional_number(value):
            if value is None: return None
            val_str = str(value).strip()
            if val_str == "": return None
            try:
                f = float(val_str)
                if f.is_integer(): return int(f)
                return f
            except Exception:
                return "INVALID"
                
        def safe_str(val):
            if val is None: return ""
            return str(val).strip()
        
        for i, row in enumerate(rows_data):
            row_num = i + 2
            while len(row) < len(headers): row.append(None)
            
            code = safe_str(row[col_idx['age_group_code']])
            name = safe_str(row[col_idx['age_group_name']])
            min_age = parse_optional_number(row[col_idx['minimum_age']])
            max_age = parse_optional_number(row[col_idx['maximum_age']])
            disp_order = parse_optional_number(row[col_idx['display_order']])
            
            age_unit = safe_str(row[col_idx['age_unit']]).capitalize()
            gender = safe_str(row[col_idx['gender']]).capitalize()
            preg_str = safe_str(row[col_idx['pregnancy_applicable']]).lower()
            active_str = safe_str(row[col_idx['active']]).lower()
            
            row_errors = []
            
            if not code: row_errors.append({'row': row_num, 'field': 'age_group_code', 'value': '', 'message': 'Age group code required'})
            if not name: row_errors.append({'row': row_num, 'field': 'age_group_name', 'value': '', 'message': 'Age group name required'})
            
            if min_age == 'INVALID': row_errors.append({'row': row_num, 'field': 'minimum_age', 'value': row[col_idx['minimum_age']], 'message': 'INVALID_NUMERIC_VALUE'})
            if max_age == 'INVALID': row_errors.append({'row': row_num, 'field': 'maximum_age', 'value': row[col_idx['maximum_age']], 'message': 'INVALID_NUMERIC_VALUE'})
            if disp_order == 'INVALID': row_errors.append({'row': row_num, 'field': 'display_order', 'value': row[col_idx['display_order']], 'message': 'INVALID_NUMERIC_VALUE'})
            
            if min_age != 'INVALID' and max_age != 'INVALID' and min_age is not None and max_age is not None and min_age > max_age:
                row_errors.append({'row': row_num, 'field': 'age_range', 'value': f'{min_age}-{max_age}', 'message': 'INVALID_AGE_RANGE: minimum_age > maximum_age'})
                
            if age_unit not in ['Days', 'Months', 'Years']:
                row_errors.append({'row': row_num, 'field': 'age_unit', 'value': row[col_idx['age_unit']], 'message': 'INVALID_AGE_UNIT: Allowed values: Days, Months, Years.'})
            if gender not in ['All', 'Male', 'Female']:
                row_errors.append({'row': row_num, 'field': 'gender', 'value': row[col_idx['gender']], 'message': 'INVALID_GENDER: Allowed values: All, Male, Female.'})
            
            preg = preg_str in ['yes', 'y', '1', 'true']
            if preg_str not in ['yes', 'no', 'y', 'n', '1', '0', 'true', 'false', '']:
                row_errors.append({'row': row_num, 'field': 'pregnancy_applicable', 'value': row[col_idx['pregnancy_applicable']], 'message': 'INVALID_PREGNANCY_VALUE'})
                
            active = active_str in ['yes', 'y', '1', 'true', '']
            if active_str not in ['yes', 'no', 'y', 'n', '1', '0', 'true', 'false', '']:
                row_errors.append({'row': row_num, 'field': 'active', 'value': row[col_idx['active']], 'message': 'INVALID_ACTIVE_VALUE'})
            
            is_duplicate = False
            if code in existing:
                is_duplicate = True
            elif code in file_codes:
                row_errors.append({'row': row_num, 'field': 'age_group_code', 'value': code, 'message': 'DUPLICATE_AGE_GROUP_CODE_IN_FILE'})
                
            if code: file_codes.add(code)
            
            if row_errors:
                status = 'Error'
                invalid_rows += 1
                validation_errors.extend(row_errors)
                error_msg = row_errors[0]['message']
            elif is_duplicate:
                status = 'Duplicate'
                duplicate_rows += 1
                error_msg = 'EXISTING_AGE_GROUP'
            else:
                status = 'Valid'
                valid_rows += 1
                error_msg = ''
                
            preview_data.append({
                'row_num': row_num,
                'code': code,
                'name': name,
                'min_age': min_age if min_age != 'INVALID' and min_age is not None else '',
                'max_age': max_age if max_age != 'INVALID' and max_age is not None else '',
                'unit': age_unit,
                'gender': gender,
                'preg': preg,
                'disp_order': disp_order if disp_order != 'INVALID' and disp_order is not None else '',
                'active': active,
                'status': status,
                'error': error_msg
            })
            
        if validation_errors:
            return JsonResponse({
                'success': False,
                'error_type': 'VALIDATION_ERROR',
                'errors': validation_errors,
                'data': preview_data,
                'filename': filename
            })
            
        return JsonResponse({
            'success': True,
            'total_rows': len(rows_data),
            'valid_rows': valid_rows,
            'invalid_rows': invalid_rows,
            'duplicates': duplicate_rows,
            'errors': [],
            'data': preview_data,
            'filename': filename
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("AGE GROUP IMPORT ERROR:", repr(e))
        return JsonResponse({'success': False, 'message': str(e)})

def api_agegroup_import(request):
    import json
    from django.http import JsonResponse
    if request.method != 'POST': return JsonResponse({'success': False, 'message': 'Invalid method'})
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_duplicates = data.get('update_duplicates', False)
        
        imported = updated = skipped = failed = 0
        from django.db import transaction, IntegrityError
        from .models import AgeGroup, AgeGroupImportHistory
        
        # Pre-fetch existing codes to avoid querying per row
        valid_codes = [r['code'] for r in rows if r['status'] != 'Error']
        existing_age_groups = {ag.code: ag for ag in AgeGroup.objects.filter(code__in=valid_codes)}
        
        try:
            with transaction.atomic():
                for row in rows:
                    if row['status'] == 'Error':
                        failed += 1
                        continue
                    
                    ag = existing_age_groups.get(row['code'])
                    min_age = row['min_age'] if row['min_age'] != '' else 0
                    max_age = row['max_age'] if row['max_age'] != '' else None
                    disp = row['disp_order'] if row['disp_order'] != '' else 1
                    
                    if ag:
                        if update_duplicates or row['status'] == 'Duplicate':
                            if update_duplicates:
                                ag.label = row['name']
                                ag.min_age_value = min_age
                                ag.min_age_unit = row['unit']
                                ag.max_age_value = max_age
                                ag.max_age_unit = row['unit']
                                ag.gender = row['gender']
                                ag.pregnancy_applicable = row['preg']
                                ag.sort_order = disp
                                ag.is_active = row['active']
                                ag.save()
                                updated += 1
                            else:
                                skipped += 1
                        else:
                            skipped += 1
                    else:
                        new_ag = AgeGroup.objects.create(
                            code=row['code'],
                            label=row['name'],
                            min_age_value=min_age,
                            min_age_unit=row['unit'],
                            max_age_value=max_age,
                            max_age_unit=row['unit'],
                            gender=row['gender'],
                            pregnancy_applicable=row['preg'],
                            sort_order=disp,
                            is_active=row['active']
                        )
                        existing_age_groups[new_ag.code] = new_ag
                        imported += 1
                        
                history = AgeGroupImportHistory.objects.create(
                    file_name=filename, uploaded_by=request.user if request.user.is_authenticated else None,
                    total_records=len(rows), imported=imported, updated=updated, skipped=skipped, failed=failed
                )
                
            return JsonResponse({'success': True, 'summary': {
                'total': len(rows), 'imported': imported, 'updated': updated, 'skipped': skipped, 'failed': failed, 'history_id': history.id
            }})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("AGE GROUP IMPORT DATABASE ERROR:", repr(e))
            return JsonResponse({
                'success': False, 
                'error_type': 'DATABASE_ERROR',
                'message': 'Age Group import failed. No records were imported.'
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("AGE GROUP IMPORT ERROR:", repr(e))
        return JsonResponse({'success': False, 'message': str(e)})

# --- Parameter Import ---

class ParameterImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_parameter.html'
    menu_key = 'administration'

class ParameterImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = ParameterImportHistory
    template_name = 'lab/master/import_parameter_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_parameter_download_template(request):
    df = pd.DataFrame({
        'parameter_code': ['CBC-HB', 'CBC-WBC'],
        'investigation_code': ['00020537', '00020537'],
        'parameter_name': ['Hemoglobin', 'WBC Count'],
        'short_name': ['Hb', 'WBC'],
        'result_type': ['Numeric', 'Numeric'],
        'unit': ['g/dL', '10^3/uL'],
        'decimal_precision': [1, 1],
        'age_group_code': ['ADULT-MALE', 'ADULT-MALE'],
        'gender': ['Male', 'Male'],
        'min_age': [18, 18],
        'max_age': [120, 120],
        'age_unit': ['Years', 'Years'],
        'reference_min': ['12.0', '4.0'],
        'reference_max': ['17.5', '11.0'],
        'reference_text': ['', ''],
        'critical_low': ['7.0', '2.0'],
        'critical_high': ['20.0', '30.0'],
        'display_order': [1, 2],
        'active': ['Yes', 'Yes']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="parameter_import_template.xlsx"'
    return response

def api_parameter_preview(request):
    if request.method != 'POST': return JsonResponse({'success': False, 'message': 'Invalid method'})
    if 'file' not in request.FILES: return JsonResponse({'success': False, 'message': 'No file uploaded'})
    
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'):
            import csv
            import io
            decoded_file = file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(decoded_file))
            raw_headers = next(reader, [])
            rows_data = list(reader)
        elif filename.endswith('.xlsx'):
            from openpyxl import load_workbook
            try:
                workbook = load_workbook(file, read_only=True, data_only=True)
            except Exception as e:
                print("PARAMETER IMPORT ERROR:", repr(e))
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'success': False, 
                    'error_type': 'VALIDATION_ERROR',
                    'errors': [{'row': 0, 'field': 'File', 'value': '', 'message': 'Could not read Excel file'}]
                })
                
            if 'Template' not in workbook.sheetnames:
                return JsonResponse({
                    'success': False, 
                    'error_type': 'VALIDATION_ERROR',
                    'errors': [{'row': 0, 'field': 'Worksheet', 'value': '', 'message': "Import worksheet 'Template' not found."}]
                })
                
            worksheet = workbook['Template']
            
            raw_headers = []
            rows_data = []
            for i, row in enumerate(worksheet.iter_rows(values_only=True)):
                if i == 0:
                    raw_headers = list(row)
                else:
                    # Ignore completely empty rows
                    if any(cell is not None and str(cell).strip() != '' for cell in row):
                        rows_data.append(list(row))
        else:
            return JsonResponse({'success': False, 'message': 'Unsupported format'})
            
        required_cols = [
            'parameter_code', 'investigation_code', 'parameter_name', 'short_name', 
            'result_type', 'unit', 'decimal_precision', 'age_group_code', 'gender', 
            'min_age', 'max_age', 'age_unit', 'reference_min', 'reference_max', 
            'reference_text', 'critical_low', 'critical_high', 'display_order', 'active'
        ]
        
        headers = [str(h).strip().lower() if h else "" for h in raw_headers]
        
        for req in required_cols:
            if req not in headers:
                return JsonResponse({
                    'success': False, 
                    'error_type': 'VALIDATION_ERROR',
                    'errors': [{'row': 1, 'field': 'Header', 'value': '', 'message': f'Missing required column: {req}'}]
                })
                
        # Get column indices
        col_idx = {req: headers.index(req) for req in required_cols}
        
        from .models import Investigation, AgeGroup, InvestigationParameter
        invs = set(Investigation.objects.values_list('code', flat=True))
        ags = set(AgeGroup.objects.values_list('code', flat=True))
        existing_params = set(InvestigationParameter.objects.values_list('investigation__code', 'code'))
        
        valid_result_types = [
            'numeric', 'text', 'boolean', 'positive/negative', 
            'reactive/non-reactive', 'detected/not detected', 'select', 'date', 'time'
        ]
        
        def parse_optional_number(value):
            if value is None: return None
            val_str = str(value).strip()
            if val_str == "": return None
            try:
                # Try parsing as float, if it's an integer, return int, else float
                f = float(val_str)
                if f.is_integer(): return int(f)
                return f
            except Exception:
                return "INVALID"
                
        def safe_str(val):
            if val is None: return ""
            return str(val).strip()
            
        preview_data = []
        validation_errors = []
        
        valid_rows = 0
        invalid_rows = 0
        duplicate_rows = 0
        
        for i, row in enumerate(rows_data):
            row_num = i + 2
            
            # ensure row has enough elements
            while len(row) < len(headers): row.append(None)
            
            pcode = safe_str(row[col_idx['parameter_code']])
            icode = safe_str(row[col_idx['investigation_code']])
            name = safe_str(row[col_idx['parameter_name']])
            short_name = safe_str(row[col_idx['short_name']])
            rtype_input = safe_str(row[col_idx['result_type']])
            unit = safe_str(row[col_idx['unit']])
            dec_prec = parse_optional_number(row[col_idx['decimal_precision']])
            ag_code = safe_str(row[col_idx['age_group_code']])
            gender = safe_str(row[col_idx['gender']]).capitalize()
            if gender not in ['Male', 'Female', 'All']: gender = 'All'
            
            min_age = parse_optional_number(row[col_idx['min_age']])
            max_age = parse_optional_number(row[col_idx['max_age']])
            age_unit = safe_str(row[col_idx['age_unit']]).capitalize()
            if age_unit not in ['Days', 'Months', 'Years']: age_unit = 'Years'
            
            ref_min = parse_optional_number(row[col_idx['reference_min']])
            ref_max = parse_optional_number(row[col_idx['reference_max']])
            ref_text = safe_str(row[col_idx['reference_text']])
            crit_low = parse_optional_number(row[col_idx['critical_low']])
            crit_high = parse_optional_number(row[col_idx['critical_high']])
            disp_order = parse_optional_number(row[col_idx['display_order']])
            active_str = safe_str(row[col_idx['active']]).lower()
            active = active_str in ['yes', 'y', '1', 'true', '']
            
            row_errors = []
            
            if not pcode: row_errors.append({'row': row_num, 'field': 'parameter_code', 'value': '', 'message': 'Parameter code is required'})
            
            if not icode: 
                row_errors.append({'row': row_num, 'field': 'investigation_code', 'value': '', 'message': 'Investigation code is required'})
            elif icode not in invs:
                row_errors.append({'row': row_num, 'field': 'investigation_code', 'value': icode, 'message': 'INVESTIGATION_NOT_FOUND'})
                
            if not name: row_errors.append({'row': row_num, 'field': 'parameter_name', 'value': '', 'message': 'Parameter name is required'})
            
            if not rtype_input:
                row_errors.append({'row': row_num, 'field': 'result_type', 'value': '', 'message': 'RESULT_TYPE_REQUIRED'})
            elif rtype_input.lower() not in valid_result_types:
                row_errors.append({'row': row_num, 'field': 'result_type', 'value': rtype_input, 'message': 'Invalid result type'})
                
            if ag_code and ag_code not in ags and ag_code != 'GENERAL':
                row_errors.append({'row': row_num, 'field': 'age_group_code', 'value': ag_code, 'message': 'AGE_GROUP_NOT_FOUND'})
                
            if dec_prec == 'INVALID': row_errors.append({'row': row_num, 'field': 'decimal_precision', 'value': row[col_idx['decimal_precision']], 'message': 'INVALID_NUMERIC_VALUE'})
            if disp_order == 'INVALID': row_errors.append({'row': row_num, 'field': 'display_order', 'value': row[col_idx['display_order']], 'message': 'INVALID_NUMERIC_VALUE'})
            
            if min_age == 'INVALID': row_errors.append({'row': row_num, 'field': 'min_age', 'value': row[col_idx['min_age']], 'message': 'INVALID_NUMERIC_VALUE'})
            if max_age == 'INVALID': row_errors.append({'row': row_num, 'field': 'max_age', 'value': row[col_idx['max_age']], 'message': 'INVALID_NUMERIC_VALUE'})
            
            if ref_min == 'INVALID': row_errors.append({'row': row_num, 'field': 'reference_min', 'value': row[col_idx['reference_min']], 'message': 'INVALID_NUMERIC_VALUE'})
            if ref_max == 'INVALID': row_errors.append({'row': row_num, 'field': 'reference_max', 'value': row[col_idx['reference_max']], 'message': 'INVALID_NUMERIC_VALUE'})
            
            if crit_low == 'INVALID': row_errors.append({'row': row_num, 'field': 'critical_low', 'value': row[col_idx['critical_low']], 'message': 'INVALID_NUMERIC_VALUE'})
            if crit_high == 'INVALID': row_errors.append({'row': row_num, 'field': 'critical_high', 'value': row[col_idx['critical_high']], 'message': 'INVALID_NUMERIC_VALUE'})
            
            if min_age != 'INVALID' and max_age != 'INVALID' and min_age is not None and max_age is not None and min_age > max_age:
                row_errors.append({'row': row_num, 'field': 'age_range', 'value': f'{min_age}-{max_age}', 'message': 'INVALID_AGE_RANGE'})
                
            if ref_min != 'INVALID' and ref_max != 'INVALID' and ref_min is not None and ref_max is not None and ref_min > ref_max:
                row_errors.append({'row': row_num, 'field': 'reference_range', 'value': f'{ref_min}-{ref_max}', 'message': 'INVALID_REFERENCE_RANGE'})
                
            # If there are duplicate parameter, just warn in row_errors
            is_duplicate = False
            if icode and pcode and (icode, pcode) in existing_params:
                is_duplicate = True
                
            if row_errors:
                status = 'Error'
                invalid_rows += 1
                validation_errors.extend(row_errors)
                error_msg = row_errors[0]['message']
            elif is_duplicate:
                status = 'Duplicate'
                duplicate_rows += 1
                error_msg = 'DUPLICATE_PARAMETER'
            else:
                status = 'Valid'
                valid_rows += 1
                error_msg = ''
                
            rtype_final = rtype_input.capitalize()
            for v in valid_result_types:
                if v == rtype_input.lower(): rtype_final = v.title(); break
                
            preview_data.append({
                'row_num': row_num,
                'pcode': pcode,
                'icode': icode,
                'name': name,
                'short_name': short_name,
                'rtype': rtype_final,
                'unit': unit,
                'decimal_precision': dec_prec if dec_prec != 'INVALID' else '',
                'ag_code': ag_code,
                'gender': gender,
                'min_age': min_age if min_age != 'INVALID' else '',
                'max_age': max_age if max_age != 'INVALID' else '',
                'age_unit': age_unit,
                'ref_min': ref_min if ref_min != 'INVALID' else '',
                'ref_max': ref_max if ref_max != 'INVALID' else '',
                'ref_text': ref_text,
                'crit_low': crit_low if crit_low != 'INVALID' else '',
                'crit_high': crit_high if crit_high != 'INVALID' else '',
                'disp_order': disp_order if disp_order != 'INVALID' else '',
                'active': active,
                'status': status,
                'error': error_msg
            })
            
        if validation_errors:
            # We return success True but errors array!
            # Wait, the user said: "If parsing/validation fails: { success: false, error_type: VALIDATION_ERROR, errors: [...] }"
            # And: "After parsing successfully return: { success: true, total_rows: 97... }"
            # If there are validation errors on rows, do we return success: true with the preview, or success: false?
            # "The generic message... must no longer be shown. Change to: Exception caused by bad row -> validation result -> show row error."
            # "The frontend should then display the Import Preview."
            # Let's return success: False with VALIDATION_ERROR to trigger the error modal, OR success: True so they can see the preview?
            # The prompt says: "If parsing/validation fails: { success: false, error_type: "VALIDATION_ERROR", errors: [ ... ] }" 
            # So I will return success: False if there are errors, and the frontend will display them in a table.
            return JsonResponse({
                'success': False,
                'error_type': 'VALIDATION_ERROR',
                'errors': validation_errors,
                'data': preview_data, # Include data anyway so frontend has it if needed
                'filename': filename
            })
            
        return JsonResponse({
            'success': True,
            'total_rows': len(rows_data),
            'valid_rows': valid_rows,
            'invalid_rows': invalid_rows,
            'duplicates': duplicate_rows,
            'errors': [],
            'data': preview_data,
            'filename': filename
        })
        
    except Exception as e:
        print("PARAMETER IMPORT ERROR:", repr(e))
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)})

def api_parameter_import(request):
    import json
    from django.http import JsonResponse
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_dups = data.get('update_duplicates', False)
        
        imported = updated = skipped = failed = 0
        from django.db import transaction
        from .models import Investigation, InvestigationParameter, AgeGroup, ParameterReferenceRange, ParameterImportHistory
        
        with transaction.atomic():
            for row in rows:
                if row['status'] == 'Error':
                    failed += 1
                    continue
                try:
                    inv = Investigation.objects.filter(code=row['icode']).first()
                    if not inv:
                        failed += 1
                        continue
                        
                    pcode = row['pcode']
                    param = InvestigationParameter.objects.filter(investigation=inv, code=pcode).first()
                    
                    dec_prec = None
                    if row.get('decimal_precision') not in [None, '']:
                        try: dec_prec = int(float(row['decimal_precision']))
                        except: pass
                        
                    disp = 1
                    if row.get('disp_order') not in [None, '']:
                        try: disp = int(float(row['disp_order']))
                        except: pass
                        
                    if param:
                        if update_dups or row['status'] == 'Duplicate':
                            if update_dups:
                                param.name = row['name']
                                param.short_name = row['short_name']
                                param.result_type = row['rtype']
                                param.unit = row['unit']
                                param.decimal_precision = dec_prec
                                param.display_order = disp
                                param.is_active = row['active']
                                param.save()
                                updated += 1
                            else:
                                skipped += 1
                                continue
                        else:
                            skipped += 1
                            continue
                    else:
                        param = InvestigationParameter.objects.create(
                            investigation=inv, code=pcode, name=row['name'],
                            short_name=row['short_name'], result_type=row['rtype'], 
                            unit=row['unit'], decimal_precision=dec_prec, 
                            display_order=disp, is_active=row['active']
                        )
                        imported += 1
                        
                    ag_code = row['ag_code']
                    if ag_code:
                        ag = AgeGroup.objects.filter(code=ag_code).first()
                        if ag:
                            gen = row.get('gender', 'All')
                            
                            def s_float(val):
                                if val in [None, '']: return None
                                return float(val)
                                
                            r_min = s_float(row.get('ref_min'))
                            r_max = s_float(row.get('ref_max'))
                            c_low = s_float(row.get('crit_low'))
                            c_high = s_float(row.get('crit_high'))
                            
                            ref, ref_cr = ParameterReferenceRange.objects.get_or_create(
                                investigation_parameter=param, age_group=ag, gender=gen,
                                defaults={
                                    'min_value': r_min,
                                    'max_value': r_max,
                                    'reference_text': row.get('ref_text', ''),
                                    'critical_low': c_low,
                                    'critical_high': c_high,
                                    'unit': row.get('unit', '')
                                }
                            )
                            
                            if not ref_cr and update_dups:
                                ref.min_value = r_min
                                ref.max_value = r_max
                                ref.reference_text = row.get('ref_text', '')
                                ref.critical_low = c_low
                                ref.critical_high = c_high
                                ref.unit = row.get('unit', '')
                                ref.save()
                                
                except Exception as e:
                    print(e)
                    failed += 1
                    
            history = ParameterImportHistory.objects.create(
                file_name=filename, uploaded_by=request.user if request.user.is_authenticated else None,
                total_records=len(rows), imported=imported, updated=updated, skipped=skipped, failed=failed
            )
        return JsonResponse({'status': 'success', 'summary': {
            'total': len(rows), 'imported': imported, 'updated': updated, 'skipped': skipped, 'failed': failed, 'history_id': history.id
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})

class ReferenceRangeImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'lab/master/import_reference_range.html'
    menu_key = 'administration'

class ReferenceRangeImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = ReferenceRangeImportHistory
    template_name = 'lab/master/import_reference_range_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_referencerange_download_template(request):
    df = pd.DataFrame({
        'investigation_code': ['00020537', '00020537'],
        'investigation_name': ['CBC Complete Blood Count', 'CBC Complete Blood Count'],
        'parameter_code': ['00020350', '00020350'],
        'parameter_name': ['Hemoglobin', 'Hemoglobin'],
        'age_group_code': ['ADOLESCENT', 'ADULT'],
        'age_group_name': ['Younger Adolescent', 'Adult'],
        'gender': ['Male', 'Female'],
        'range_type': ['NUMERIC', 'NUMERIC'],
        'min_value': ['11.0', '12.0'],
        'max_value': ['15.0', '16.0'],
        'reference_range_text': ['', ''],
        'unit': ['g/dL', 'g/dL'],
        'method': ['Colorimetric', 'Colorimetric'],
        'remarks': ['', ''],
        'status': ['Active', 'Active']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reference_range_import_template.xlsx"'
    return response

def api_referencerange_preview(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unsupported file format.'})
            
        required_columns = [
            'investigation_code', 'parameter_code', 'age_group_code', 'range_type'
        ]
        
        # Normalize headers to handle spaces, case, etc.
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        
        missing_columns = [req for req in required_columns if req not in df.columns]
        if missing_columns:
            msg = 'Missing required columns:\n- ' + '\n- '.join(missing_columns)
            return JsonResponse({'status': 'error', 'message': msg})
                
        from .models import InvestigationParameter, AgeGroup, ParameterReferenceRange, Investigation, ReferenceRangeImportHistory
        
        # Create staging history record and save file
        history = ReferenceRangeImportHistory.objects.create(
            file_name=filename,
            uploaded_by=request.user if request.user.is_authenticated else None,
            total_records=len(df),
            status='Staged',
            upload_file=file
        )
        
        valid_investigations = set(Investigation.objects.values_list('code', flat=True))
        inv_params_cache = list(InvestigationParameter.objects.select_related('investigation', 'parameter').all())
        ag_cache = {ag.code: ag for ag in AgeGroup.objects.all()}
        
        existing_ranges = set()
        for r in ParameterReferenceRange.objects.all():
            existing_ranges.add((r.investigation_parameter_id, r.age_group_id, r.gender))
        
        preview_data = []
        file_keys = set()
        
        valid_rows = 0
        invalid_rows = 0
        duplicate_rows = 0
        
        for index, row in df.iterrows():
            row_num = index + 2
            
            inv_code = str(row.get('investigation_code', '')).strip()
            param_code = str(row.get('parameter_code', '')).strip()
            ag_code = str(row.get('age_group_code', '')).strip()
            gender = str(row.get('gender', '')).strip().capitalize()
            range_type = str(row.get('range_type', '')).strip().upper()
            
            if inv_code == 'nan': inv_code = ''
            if param_code == 'nan': param_code = ''
            if ag_code == 'nan': ag_code = ''
            if gender == 'nan' or not gender: gender = 'All'
            if range_type == 'nan' or not range_type: range_type = 'NUMERIC'
            
            if range_type in ['NUMERIC RANGE', 'NUMERIC']: range_type = 'Numeric'
            elif range_type in ['TEXT', 'TEXT / QUALITATIVE', 'QUALITATIVE']: range_type = 'Text'
            elif range_type in ['NONE', 'NO REFERENCE RANGE']: range_type = 'None'
            
            min_val = str(row.get('min_value', '')).strip()
            max_val = str(row.get('max_value', '')).strip()
            if min_val == 'nan': min_val = ''
            if max_val == 'nan': max_val = ''
            
            ref_text = str(row.get('reference_range_text', '')).strip()
            if ref_text == 'nan': ref_text = ''
            
            status = 'Valid'
            error_msg = ''
            
            ip_id = None
            ag_id = None
            
            if not inv_code:
                status = 'Error'
                error_msg = 'Investigation Code is required'
            elif not param_code:
                status = 'Error'
                error_msg = 'Parameter Code is required'
            elif not ag_code:
                status = 'Error'
                error_msg = 'Age Group Code is required'
            elif gender not in ['All', 'Male', 'Female']:
                status = 'Error'
                error_msg = 'Invalid Gender'
            elif inv_code not in valid_investigations:
                status = 'Error'
                error_msg = f"Investigation code '{inv_code}' does not exist."
            else:
                ip = next((ip for ip in inv_params_cache if ip.investigation.code == inv_code and (ip.code == param_code or (ip.parameter and ip.parameter.code == param_code))), None)
                if not ip:
                    status = 'Error'
                    error_msg = f"Parameter code '{param_code}' not found for investigation '{inv_code}'"
                else:
                    ip_id = ip.id
                    ag = ag_cache.get(ag_code)
                    if not ag:
                        status = 'Error'
                        error_msg = f"Age Group code '{ag_code}' does not exist."
                    else:
                        ag_id = ag.id
                        
            if status == 'Valid':
                if range_type == 'Numeric':
                    if min_val and max_val:
                        try:
                            if float(min_val) > float(max_val):
                                status = 'Error'
                                error_msg = 'Min > Max'
                        except:
                            status = 'Error'
                            error_msg = 'Invalid numeric min/max'
                            
                key = f"{inv_code}-{param_code}-{ag_code}-{gender}"
                if key in file_keys:
                    status = 'Error'
                    error_msg = 'Duplicate in file'
                else:
                    file_keys.add(key)
                    
                if status == 'Valid':
                    if (ip_id, ag_id, gender) in existing_ranges:
                        status = 'Duplicate'
                        error_msg = 'Mapping already exists'
            
            if status == 'Valid':
                valid_rows += 1
            elif status == 'Duplicate':
                duplicate_rows += 1
            else:
                invalid_rows += 1
                
            if index < 100:
                preview_data.append({
                    'row_num': row_num,
                    'investigation_code': inv_code,
                    'parameter_code': param_code,
                    'age_group_code': ag_code,
                    'gender': gender,
                    'range_type': range_type.upper(),
                    'min_value': min_val,
                    'max_value': max_val,
                    'reference_range_text': ref_text,
                    'unit': str(row.get('unit', '')).strip(),
                    'method': str(row.get('method', '')).strip(),
                    'remarks': str(row.get('remarks', '')).strip(),
                    'status': status,
                    'error': error_msg
                })
            
        return JsonResponse({
            'status': 'success',
            'filename': filename,
            'import_id': history.id,
            'total_rows': len(df),
            'valid_rows': valid_rows,
            'invalid_rows': invalid_rows,
            'duplicate_rows': duplicate_rows,
            'data': preview_data
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error parsing file: {str(e)}'})

def api_referencerange_import(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})
        
    try:
        data = json.loads(request.body)
        import_id = data.get('import_id')
        update_existing = data.get('update_existing', False)
        
        if not import_id:
            return JsonResponse({'status': 'error', 'message': 'Missing import_id'})
            
        from .models import InvestigationParameter, AgeGroup, ParameterReferenceRange, ReferenceRangeImportHistory, Investigation
        from decimal import Decimal
        from django.db import transaction, models
        import pandas as pd
        
        history = ReferenceRangeImportHistory.objects.get(id=import_id)
        if history.status != 'Staged':
            return JsonResponse({'status': 'error', 'message': 'This import is already processed.'})
            
        history.status = 'In Progress'
        history.save()
        
        file_path = history.upload_file.path
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
            
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        
        imported = 0
        updated = 0
        failed = 0
        
        # Pre-cache to speed up import
        inv_params_cache = list(InvestigationParameter.objects.select_related('investigation', 'parameter').all())
        ag_cache = {ag.code: ag for ag in AgeGroup.objects.all()}
        valid_investigations = set(Investigation.objects.values_list('code', flat=True))
        
        try:
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        inv_code = str(row.get('investigation_code', '')).strip()
                        param_code = str(row.get('parameter_code', '')).strip()
                        ag_code = str(row.get('age_group_code', '')).strip()
                        gender = str(row.get('gender', '')).strip().capitalize()
                        
                        if inv_code == 'nan': inv_code = ''
                        if param_code == 'nan': param_code = ''
                        if ag_code == 'nan': ag_code = ''
                        if gender == 'nan' or not gender: gender = 'All'
                        if gender not in ['All', 'Male', 'Female']:
                            failed += 1
                            continue
                            
                        if not inv_code or not param_code or not ag_code:
                            failed += 1
                            continue
                            
                        if inv_code not in valid_investigations:
                            failed += 1
                            continue
                            
                        range_type = str(row.get('range_type', '')).strip().upper()
                        if range_type in ['NUMERIC RANGE', 'NUMERIC']: range_type = 'Numeric'
                        elif range_type in ['TEXT', 'TEXT / QUALITATIVE', 'QUALITATIVE']: range_type = 'Text'
                        else: range_type = 'None'
                        
                        min_val = str(row.get('min_value', '')).strip()
                        max_val = str(row.get('max_value', '')).strip()
                        ref_text = str(row.get('reference_range_text', '')).strip()
                        unit = str(row.get('unit', '')).strip()
                        method = str(row.get('method', '')).strip()
                        remarks = str(row.get('remarks', '')).strip()
                        
                        min_d = Decimal(min_val) if min_val and min_val != 'nan' else None
                        max_d = Decimal(max_val) if max_val and max_val != 'nan' else None
                        
                        if unit == 'nan': unit = ''
                        if method == 'nan': method = ''
                        if remarks == 'nan': remarks = ''
                        if ref_text == 'nan': ref_text = ''
                        
                        ip = next((ip for ip in inv_params_cache if ip.investigation.code == inv_code and (ip.code == param_code or (ip.parameter and ip.parameter.code == param_code))), None)
                        ag = ag_cache.get(ag_code)
                        
                        if ip and ag:
                            obj, created = ParameterReferenceRange.objects.get_or_create(
                                investigation_parameter=ip,
                                age_group=ag,
                                gender=gender
                            )
                            
                            if created:
                                imported += 1
                            else:
                                updated += 1
                                
                            obj.range_type = range_type
                            obj.min_value = min_d
                            obj.max_value = max_d
                            obj.reference_text = ref_text
                            obj.unit = unit
                            obj.method = method
                            obj.remarks = remarks
                            obj.is_active = True
                            obj.save()
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                        
                history.imported = imported
                history.updated = updated
                history.failed = failed
                history.status = 'Completed'
                history.save()
                
        except Exception as e:
            history.status = 'Failed'
            history.save()
            return JsonResponse({'status': 'error', 'message': str(e)})
        
        return JsonResponse({
            'status': 'success',
            'imported': imported,
            'updated': updated,
            'failed': failed,
            'skipped': 0
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

