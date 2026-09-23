import os

content = """
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
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    if 'file' not in request.FILES: return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
        
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'): df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'): df = pd.read_excel(file, dtype=str)
        else: return JsonResponse({'status': 'error', 'message': 'Unsupported format'})
            
        required = ['age_group_code', 'age_group_name', 'minimum_age', 'maximum_age', 'age_unit', 'gender', 'pregnancy_applicable', 'active']
        df_columns = [c.lower().strip() for c in df.columns]
        for req in required:
            if req not in df_columns:
                return JsonResponse({'status': 'error', 'message': f'Missing {req}'})
                
        df.columns = df_columns
        preview_data = []
        file_codes = set()
        existing = set(AgeGroup.objects.values_list('code', flat=True))
        
        for index, row in df.iterrows():
            code = str(row.get('age_group_code', '')).strip()
            if code == 'nan': code = ''
            name = str(row.get('age_group_name', '')).strip()
            if name == 'nan': name = ''
            
            min_age = str(row.get('minimum_age', '0')).strip()
            max_age = str(row.get('maximum_age', '0')).strip()
            age_unit = str(row.get('age_unit', 'Years')).strip().capitalize()
            if age_unit not in ['Days', 'Months', 'Years']:
                age_unit = 'Years'
                
            gender = str(row.get('gender', 'All')).strip().capitalize()
            if gender not in ['All', 'Male', 'Female']: gender = 'All'
            
            preg = str(row.get('pregnancy_applicable', '')).strip().lower() in ['yes', 'y', '1', 'true']
            active = str(row.get('active', 'yes')).strip().lower() in ['yes', 'y', '1', 'true']
            
            status = 'Valid'
            error = ''
            
            if not code:
                status, error = 'Error', 'Code required'
            elif not name:
                status, error = 'Error', 'Name required'
            elif not min_age.isdigit() or not max_age.isdigit():
                status, error = 'Error', 'Age must be numeric'
            elif int(min_age) > int(max_age) and age_unit == 'Years':
                # Simplified check. Actual logic can be complex for units
                pass
            elif code in file_codes:
                status, error = 'Error', 'Duplicate in file'
            elif code in existing:
                status, error = 'Duplicate', 'Code exists'
                
            if code: file_codes.add(code)
            
            preview_data.append({
                'row_num': index + 2,
                'code': code,
                'name': name,
                'min_age': min_age,
                'max_age': max_age,
                'unit': age_unit,
                'gender': gender,
                'preg': preg,
                'active': active,
                'status': status,
                'error': error
            })
            
        return JsonResponse({'status': 'success', 'filename': filename, 'data': preview_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def api_agegroup_import(request):
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_duplicates = data.get('update_duplicates', False)
        
        imported = updated = skipped = failed = 0
        from django.db import transaction
        with transaction.atomic():
            for row in rows:
                if row['status'] == 'Error':
                    failed += 1; continue
                try:
                    ag = AgeGroup.objects.filter(code=row['code']).first()
                    if ag:
                        if update_duplicates:
                            ag.label = row['name']
                            ag.min_age_value = int(row['min_age'])
                            ag.min_age_unit = row['unit']
                            ag.max_age_value = int(row['max_age'])
                            ag.max_age_unit = row['unit']
                            ag.gender = row['gender']
                            ag.pregnancy_applicable = row['preg']
                            ag.is_active = row['active']
                            ag.save()
                            updated += 1
                        else:
                            skipped += 1
                    else:
                        AgeGroup.objects.create(
                            code=row['code'],
                            label=row['name'],
                            min_age_value=int(row['min_age']),
                            min_age_unit=row['unit'],
                            max_age_value=int(row['max_age']),
                            max_age_unit=row['unit'],
                            gender=row['gender'],
                            pregnancy_applicable=row['preg'],
                            is_active=row['active']
                        )
                        imported += 1
                except Exception as e:
                    failed += 1
                    
            history = AgeGroupImportHistory.objects.create(
                file_name=filename, uploaded_by=request.user if request.user.is_authenticated else None,
                total_records=len(rows), imported=imported, updated=updated, skipped=skipped, failed=failed
            )
        return JsonResponse({'status': 'success', 'summary': {
            'total': len(rows), 'imported': imported, 'updated': updated, 'skipped': skipped, 'failed': failed, 'history_id': history.id
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

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
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    if 'file' not in request.FILES: return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
    
    file = request.FILES['file']
    filename = file.name
    
    try:
        if filename.endswith('.csv'): df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'): df = pd.read_excel(file, dtype=str)
        else: return JsonResponse({'status': 'error', 'message': 'Unsupported format'})
        
        required = ['parameter_code', 'investigation_code', 'parameter_name', 'result_type']
        df_columns = [c.lower().strip() for c in df.columns]
        for req in required:
            if req not in df_columns: return JsonResponse({'status': 'error', 'message': f'Missing {req}'})
        df.columns = df_columns
        
        preview_data = []
        from .models import Investigation, AgeGroup
        invs = set(Investigation.objects.values_list('code', flat=True))
        
        for index, row in df.iterrows():
            pcode = str(row.get('parameter_code', '')).strip()
            icode = str(row.get('investigation_code', '')).strip()
            name = str(row.get('parameter_name', '')).strip()
            if pcode == 'nan': pcode = ''
            if icode == 'nan': icode = ''
            if name == 'nan': name = ''
            
            rtype = str(row.get('result_type', 'Numeric')).strip().capitalize()
            ag_code = str(row.get('age_group_code', '')).strip()
            if ag_code == 'nan': ag_code = ''
            
            status = 'Valid'
            error = ''
            if not pcode: status, error = 'Error', 'Parameter code missing'
            elif not icode: status, error = 'Error', 'Investigation code missing'
            elif icode not in invs: status, error = 'Error', f'Investigation {icode} not found'
            
            preview_data.append({
                'row_num': index + 2,
                'pcode': pcode,
                'icode': icode,
                'name': name,
                'short_name': str(row.get('short_name', '')).strip(),
                'rtype': rtype,
                'unit': str(row.get('unit', '')).strip(),
                'decimal_precision': str(row.get('decimal_precision', '')).strip(),
                'ag_code': ag_code,
                'gender': str(row.get('gender', 'All')).strip(),
                'min_age': str(row.get('min_age', '')).strip(),
                'max_age': str(row.get('max_age', '')).strip(),
                'age_unit': str(row.get('age_unit', 'Years')).strip(),
                'ref_min': str(row.get('reference_min', '')).strip(),
                'ref_max': str(row.get('reference_max', '')).strip(),
                'ref_text': str(row.get('reference_text', '')).strip(),
                'crit_low': str(row.get('critical_low', '')).strip(),
                'crit_high': str(row.get('critical_high', '')).strip(),
                'disp_order': str(row.get('display_order', '1')).strip(),
                'active': str(row.get('active', 'Yes')).strip().lower() in ['yes','y','1','true'],
                'status': status,
                'error': error
            })
        return JsonResponse({'status': 'success', 'filename': filename, 'data': preview_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def api_parameter_import(request):
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    try:
        data = json.loads(request.body)
        filename = data.get('filename', 'Unknown')
        rows = data.get('rows', [])
        update_dups = data.get('update_duplicates', False)
        
        imported = updated = skipped = failed = 0
        from django.db import transaction
        from .models import Investigation, InvestigationParameter
        
        with transaction.atomic():
            for row in rows:
                if row['status'] == 'Error':
                    failed += 1; continue
                try:
                    inv = Investigation.objects.get(code=row['icode'])
                    pcode = row['pcode']
                    
                    param = InvestigationParameter.objects.filter(investigation=inv, code=pcode).first()
                    
                    dec_prec = None
                    if row['decimal_precision'] and row['decimal_precision'] != 'nan':
                        try: dec_prec = int(float(row['decimal_precision']))
                        except: pass
                        
                    disp = 1
                    if row['disp_order'] and row['disp_order'] != 'nan':
                        try: disp = int(float(row['disp_order']))
                        except: pass
                        
                    s_name = row['short_name'] if row['short_name'] != 'nan' else ''
                    p_unit = row['unit'] if row['unit'] != 'nan' else ''
                    
                    if param:
                        if update_dups:
                            param.name = row['name']
                            param.short_name = s_name
                            param.result_type = row['rtype']
                            param.unit = p_unit
                            param.decimal_precision = dec_prec
                            param.display_order = disp
                            param.is_active = row['active']
                            param.save()
                            updated += 1
                        else:
                            skipped += 1
                    else:
                        param = InvestigationParameter.objects.create(
                            investigation=inv, code=pcode, name=row['name'],
                            short_name=s_name, result_type=row['rtype'], unit=p_unit,
                            decimal_precision=dec_prec, display_order=disp, is_active=row['active']
                        )
                        imported += 1
                        
                    # Reference Range mapping if ag_code is present
                    ag_code = row['ag_code']
                    if ag_code and ag_code != 'nan':
                        # Auto create age group if it doesnt exist
                        ag, _ = AgeGroup.objects.get_or_create(code=ag_code, defaults={
                            'label': ag_code,
                            'min_age_value': int(float(row['min_age'])) if row['min_age'] and row['min_age']!='nan' else 0,
                            'max_age_value': int(float(row['max_age'])) if row['max_age'] and row['max_age']!='nan' else 120,
                            'min_age_unit': row['age_unit'] if row['age_unit'] and row['age_unit']!='nan' else 'Years',
                            'max_age_unit': row['age_unit'] if row['age_unit'] and row['age_unit']!='nan' else 'Years',
                        })
                        
                        gen = row['gender'] if row['gender'] and row['gender']!='nan' else 'All'
                        
                        ref, ref_cr = ParameterReferenceRange.objects.get_or_create(
                            investigation_parameter=param, age_group=ag, gender=gen,
                            defaults={
                                'min_value': float(row['ref_min']) if row['ref_min'] and row['ref_min']!='nan' else None,
                                'max_value': float(row['ref_max']) if row['ref_max'] and row['ref_max']!='nan' else None,
                                'reference_text': row['ref_text'] if row['ref_text'] and row['ref_text']!='nan' else '',
                                'critical_low': float(row['crit_low']) if row['crit_low'] and row['crit_low']!='nan' else None,
                                'critical_high': float(row['crit_high']) if row['crit_high'] and row['crit_high']!='nan' else None,
                                'unit': p_unit
                            }
                        )
                        
                        if not ref_cr and update_dups:
                            ref.min_value = float(row['ref_min']) if row['ref_min'] and row['ref_min']!='nan' else None
                            ref.max_value = float(row['ref_max']) if row['ref_max'] and row['ref_max']!='nan' else None
                            ref.reference_text = row['ref_text'] if row['ref_text'] and row['ref_text']!='nan' else ''
                            ref.critical_low = float(row['crit_low']) if row['crit_low'] and row['crit_low']!='nan' else None
                            ref.critical_high = float(row['crit_high']) if row['crit_high'] and row['crit_high']!='nan' else None
                            ref.unit = p_unit
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

"""
with open('apps/lab/import_views.py', 'a') as f:
    f.write(content)
