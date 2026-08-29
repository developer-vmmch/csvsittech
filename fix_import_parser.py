import re
import os

with open('apps/lab/import_views.py', 'r') as f:
    content = f.read()

new_preview = """def api_parameter_preview(request):
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
        return JsonResponse({'success': False, 'message': str(e)})"""

start_idx = content.find('def api_parameter_preview(request):')
end_idx = content.find('def api_parameter_import(request):')
final_content = content[:start_idx] + new_preview + "\n\n" + content[end_idx:]

with open('apps/lab/import_views.py', 'w') as f:
    f.write(final_content)
