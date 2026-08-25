import re

with open('apps/lab/import_views.py', 'r') as f:
    content = f.read()

new_content = """def api_parameter_preview(request):
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    if 'file' not in request.FILES: return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
    
    file = request.FILES['file']
    filename = file.name
    
    try:
        import pandas as pd
        if filename.endswith('.csv'): 
            df = pd.read_csv(file, dtype=str)
        elif filename.endswith('.xlsx'):
            xls = pd.ExcelFile(file)
            if 'Template' in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name='Template', dtype=str)
            else:
                return JsonResponse({'status': 'error', 'message': "Validation Error: Import worksheet 'Template' not found."})
        else: 
            return JsonResponse({'status': 'error', 'message': 'Unsupported format'})
        
        df = df.dropna(how='all')
        
        required = [
            'parameter_code', 'investigation_code', 'parameter_name', 'short_name', 
            'result_type', 'unit', 'decimal_precision', 'age_group_code', 'gender', 
            'min_age', 'max_age', 'age_unit', 'reference_min', 'reference_max', 
            'reference_text', 'critical_low', 'critical_high', 'display_order', 'active'
        ]
        
        df_columns = [str(c).lower().strip() for c in df.columns]
        df.columns = df_columns
        
        for req in required:
            if req not in df_columns:
                return JsonResponse({'status': 'error', 'message': f'Validation Error: Missing required column: {req}'})
        
        preview_data = []
        from .models import Investigation, AgeGroup, InvestigationParameter
        
        invs = set(Investigation.objects.values_list('code', flat=True))
        ags = set(AgeGroup.objects.values_list('code', flat=True))
        
        existing_params = set(InvestigationParameter.objects.values_list('investigation__code', 'code'))
        
        valid_result_types = [
            'Numeric', 'Text', 'Boolean', 'Positive/Negative', 
            'Reactive/Non-Reactive', 'Detected/Not Detected', 'Select', 'Date', 'Time'
        ]
        valid_result_types_lower = [v.lower() for v in valid_result_types]
        
        def safe_str(val):
            if pd.isna(val) or val is None or str(val).strip().lower() == 'nan': return ""
            return str(val).strip()
            
        def safe_float(val):
            s = safe_str(val)
            if not s: return None
            try: return float(s)
            except: return 'INVALID'
            
        def safe_int(val):
            s = safe_str(val)
            if not s: return None
            try: return int(float(s))
            except: return 'INVALID'

        for index, row in df.iterrows():
            pcode = safe_str(row.get('parameter_code'))
            icode = safe_str(row.get('investigation_code'))
            name = safe_str(row.get('parameter_name'))
            
            if not pcode and not icode and not name:
                continue
                
            status = 'Valid'
            error = ''
            
            short_name = safe_str(row.get('short_name'))
            rtype_input = safe_str(row.get('result_type'))
            unit = safe_str(row.get('unit'))
            dec_prec = safe_int(row.get('decimal_precision'))
            ag_code = safe_str(row.get('age_group_code'))
            gender = safe_str(row.get('gender')).capitalize()
            if gender not in ['Male', 'Female', 'All']: gender = 'All'
            
            min_age = safe_float(row.get('min_age'))
            max_age = safe_float(row.get('max_age'))
            age_unit = safe_str(row.get('age_unit')).capitalize()
            if age_unit not in ['Days', 'Months', 'Years']: age_unit = 'Years'
            
            ref_min = safe_float(row.get('reference_min'))
            ref_max = safe_float(row.get('reference_max'))
            ref_text = safe_str(row.get('reference_text'))
            crit_low = safe_float(row.get('critical_low'))
            crit_high = safe_float(row.get('critical_high'))
            disp_order = safe_int(row.get('display_order'))
            
            active_str = safe_str(row.get('active')).lower()
            active = active_str in ['yes', 'y', '1', 'true', '']
            
            if not pcode:
                status, error = 'Error', 'Parameter code missing'
            elif not icode:
                status, error = 'Error', 'Investigation code missing'
            elif icode not in invs:
                status, error = 'Error', 'INVESTIGATION_NOT_FOUND'
            elif not name:
                status, error = 'Error', 'Parameter name missing'
            elif not rtype_input:
                status, error = 'Error', 'Missing result type'
            elif rtype_input.lower() not in valid_result_types_lower:
                status, error = 'Error', f'Invalid result type: {rtype_input}'
            elif ag_code and ag_code not in ags and ag_code != 'GENERAL':
                status, error = 'Error', 'AGE_GROUP_NOT_FOUND'
            elif dec_prec == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: decimal_precision'
            elif disp_order == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: display_order'
            elif min_age == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: min_age'
            elif max_age == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: max_age'
            elif ref_min == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: reference_min'
            elif ref_max == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: reference_max'
            elif crit_low == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: critical_low'
            elif crit_high == 'INVALID':
                status, error = 'Error', 'INVALID_NUMERIC_VALUE: critical_high'
            elif min_age is not None and max_age is not None and min_age > max_age:
                status, error = 'Error', 'INVALID_AGE_RANGE'
            elif ref_min is not None and ref_max is not None and ref_min > ref_max:
                status, error = 'Error', 'INVALID_REFERENCE_RANGE'
            elif (icode, pcode) in existing_params:
                status, error = 'Duplicate', 'DUPLICATE_PARAMETER'

            rtype = ""
            for v in valid_result_types:
                if v.lower() == rtype_input.lower():
                    rtype = v
                    break
                    
            preview_data.append({
                'row_num': index + 2,
                'pcode': pcode,
                'icode': icode,
                'name': name,
                'short_name': short_name,
                'rtype': rtype,
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
                'error': error
            })
        return JsonResponse({'status': 'success', 'filename': filename, 'data': preview_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})

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
"""

start_idx = content.find('def api_parameter_preview(request):')
if start_idx == -1:
    print("Could not find api_parameter_preview")
else:
    # Construct the new content
    final_content = content[:start_idx] + new_content + "\n"
    with open('apps/lab/import_views.py', 'w') as f:
        f.write(final_content)
    print("File successfully modified.")
