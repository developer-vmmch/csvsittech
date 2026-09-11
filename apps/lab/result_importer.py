import io
from decimal import Decimal
from openpyxl import load_workbook, Workbook
from django.db import transaction
from django.utils import timezone
from collections import defaultdict
import datetime

from apps.lab.models import (
    AutomationDummyResult, 
    AutomationDummyResultParameter, 
    Investigation, 
    Parameter
)

def clean_val(v):
    if v is None:
        return ""
    return str(v).strip()

def is_active_bool(v):
    if v is None:
        return True
    return str(v).strip().lower() in ['saved', 'active', 'true', '1', 'yes']

def export_dummy_results(filters=None):
    wb = Workbook(write_only=False)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
        
    ws = wb.create_sheet('Results')
    headers = [
        'Result ID', 'Investigation', 'Investigation Code', 
        'Parameter', 'Parameter Code', 'Result Value', 'Unit', 'Reference Range', 
        'Remarks', 'Status', 'Created On'
    ]
    ws.append(headers)
    
    qs = AutomationDummyResult.objects.all().select_related('investigation').prefetch_related('parameters')
    
    if filters:
        if filters.get('investigation_id') and filters['investigation_id'] != 'all':
            qs = qs.filter(investigation_id=filters['investigation_id'])
        if filters.get('date_from'):
            qs = qs.filter(created_at__date__gte=filters['date_from'])
        if filters.get('date_to'):
            qs = qs.filter(created_at__date__lte=filters['date_to'])
            
    qs = qs.order_by('-created_at')
    
    for r in qs:
        # If no parameters, just export one row with empty parameter fields
        params = list(r.parameters.all())
        inv_name = r.investigation.name if r.investigation else ''
        inv_code = r.investigation.code if r.investigation else r.investigation_code
        
        if not params:
            ws.append([
                r.result_id,
                inv_name,
                inv_code,
                '', '', '', '', '',
                r.remarks or '',
                r.status or 'Saved',
                timezone.localtime(r.created_at).strftime('%Y-%m-%d %H:%M')
            ])
            continue
            
        for p in params:
            ws.append([
                r.result_id,
                inv_name,
                inv_code,
                p.parameter_name or '',
                p.parameter.code if p.parameter else '',
                p.result_value or '',
                p.unit or '',
                p.reference_range or '',
                r.remarks or '',
                r.status or 'Saved',
                timezone.localtime(r.created_at).strftime('%Y-%m-%d %H:%M')
            ])
            
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def parse_excel_sheet(wb, sheet_name):
    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() if h else f"col_{i}" for i, h in enumerate(rows[0])]
    data = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_data = {}
        is_empty = True
        for col_idx, value in enumerate(row):
            if col_idx < len(headers):
                if value is not None and str(value).strip() != "":
                    is_empty = False
                row_data[headers[col_idx]] = value
        if not is_empty:
            row_data['_row_index'] = row_idx
            data.append(row_data)
    return data

def validate_result_import(file_obj):
    errors = []
    warnings = []
    stats = {
        'results': {'existing': 0, 'new': 0, 'updates': 0},
        'parameters': {'existing': 0, 'new': 0, 'updates': 0},
    }
    
    try:
        wb = load_workbook(filename=file_obj, data_only=True)
    except Exception as e:
        return {'errors': [{'row': 0, 'field': 'File', 'value': '', 'error': f"Could not parse Excel: {str(e)}"}]}

    rows = parse_excel_sheet(wb, 'Results')
    if not rows:
        return {'errors': [{'row': 0, 'field': 'Sheet', 'value': 'Results', 'error': 'Missing or empty Results sheet.'}]}
        
    valid_inv_codes = set(Investigation.objects.values_list('code', flat=True))
    valid_param_codes = set(Parameter.objects.values_list('code', flat=True))
    existing_result_ids = set(AutomationDummyResult.objects.values_list('result_id', flat=True))
    
    seen_result_ids = set()
    valid_rows = []
    
    for r in rows:
        rid = clean_val(r.get('result id'))
        inv_code = clean_val(r.get('investigation code'))
        param_code = clean_val(r.get('parameter code'))
        inv_name = clean_val(r.get('investigation'))
        param_name = clean_val(r.get('parameter'))
        row_errors = []
        
        if not rid:
            row_errors.append({'row': r['_row_index'], 'field': 'Result ID', 'value': '', 'error': 'Missing Result ID'})
        else:
            if rid not in seen_result_ids:
                seen_result_ids.add(rid)
                if rid in existing_result_ids:
                    stats['results']['updates'] += 1
                else:
                    stats['results']['new'] += 1
                    
        if inv_code and inv_code not in valid_inv_codes:
            row_errors.append({'row': r['_row_index'], 'field': 'Investigation Code', 'value': inv_code, 'error': 'Invalid Investigation Code'})
            
        if param_code and param_code not in valid_param_codes:
            row_errors.append({'row': r['_row_index'], 'field': 'Parameter Code', 'value': param_code, 'error': 'Invalid Parameter Code'})
            
        stats['parameters']['new'] += 1
        
        if row_errors:
            errors.extend(row_errors)
        else:
            # Only add to valid_rows preview (up to 50)
            if len(valid_rows) < 50:
                valid_rows.append({
                    'row': r['_row_index'],
                    'investigation': inv_name or inv_code or '',
                    'parameter': param_name or param_code or '',
                })
                
    stats['total_results'] = len(seen_result_ids)
        
    return {'stats': stats, 'warnings': warnings, 'errors': errors[:50], 'valid_rows': valid_rows}

def import_dummy_results_batch(file_path, batch_index, batch_size, user=None):
    from django.core.files.storage import FileSystemStorage
    from django.conf import settings
    import os
    from apps.lab.services.result_classifier import classify_from_range_string, get_overall_result_status
    from openpyxl import load_workbook
    from collections import defaultdict
    from apps.lab.models import AutomationDummyResult, AutomationDummyResultParameter, Investigation, Parameter
    from django.db import transaction
    
    fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR, 'tmp_imports'))
    with fs.open(file_path, 'rb') as f:
        wb = load_workbook(filename=f, data_only=True)
        
    rows = parse_excel_sheet(wb, 'Results')
    
    # Group by Result ID while maintaining order
    grouped = defaultdict(list)
    result_ids_ordered = []
    for r in rows:
        rid = clean_val(r.get('result id'))
        if rid:
            if rid not in grouped:
                result_ids_ordered.append(rid)
            grouped[rid].append(r)
            
    # Slicing by Result ID
    start_idx = batch_index * batch_size
    end_idx = start_idx + batch_size
    batch_rids = result_ids_ordered[start_idx:end_idx]
    
    counts = {'results_created': 0, 'results_updated': 0, 'parameters_created': 0}
    if not batch_rids:
        return counts
        
    with transaction.atomic():
        # Bulk fetch existing AutomationDummyResult
        existing_results = AutomationDummyResult.objects.filter(result_id__in=batch_rids)
        existing_map = {r.result_id: r for r in existing_results}
        
        # Bulk fetch investigations and parameters used in this batch
        inv_codes_needed = set()
        param_codes_needed = set()
        param_names_needed = set()
        
        for rid in batch_rids:
            first = grouped[rid][0]
            inv_code = clean_val(first.get('investigation code'))
            if inv_code: inv_codes_needed.add(inv_code)
            for r in grouped[rid]:
                pc = clean_val(r.get('parameter code'))
                pn = clean_val(r.get('parameter')) # Note: the header is "Parameter"
                if not pn:
                    pn = clean_val(r.get('parameter name'))
                if pc: param_codes_needed.add(pc)
                if pn: param_names_needed.add(pn.lower())
                
        inv_map = {i.code: i for i in Investigation.objects.filter(code__in=inv_codes_needed)}
        param_code_map = {p.code: p for p in Parameter.objects.filter(code__in=param_codes_needed)}
        
        from django.db.models import Q
        import operator
        from functools import reduce
        if param_names_needed:
            q_objects = reduce(operator.or_, [Q(name__iexact=n) for n in param_names_needed])
            param_name_map = {p.name.lower(): p for p in Parameter.objects.filter(q_objects)}
        else:
            param_name_map = {}
        
        results_to_create = []
        results_to_update = []
        
        for rid in batch_rids:
            items = grouped[rid]
            first = items[0]
            inv_code = clean_val(first.get('investigation code'))
            remarks = clean_val(first.get('remarks'))
            status = clean_val(first.get('status')) or 'Saved'
            
            inv = inv_map.get(inv_code)
            
            # calculate statuses
            param_statuses = []
            for r in items:
                val = clean_val(r.get('result value'))
                ref = clean_val(r.get('reference range'))
                p_status = classify_from_range_string(val, ref)
                param_statuses.append(p_status)
            overall_status = get_overall_result_status(param_statuses)
            
            if rid in existing_map:
                res_obj = existing_map[rid]
                res_obj.investigation = inv
                res_obj.investigation_code = inv_code
                res_obj.remarks = remarks
                res_obj.status = status
                res_obj.result_status = overall_status
                results_to_update.append(res_obj)
                counts['results_updated'] += 1
            else:
                res_obj = AutomationDummyResult(
                    result_id=rid,
                    investigation=inv,
                    investigation_code=inv_code,
                    remarks=remarks,
                    status=status,
                    created_by=user,
                    result_status=overall_status
                )
                results_to_create.append(res_obj)
                existing_map[rid] = res_obj # so we can use it below
                counts['results_created'] += 1
                
        if results_to_create:
            AutomationDummyResult.objects.bulk_create(results_to_create)
            
        if results_to_update:
            AutomationDummyResult.objects.bulk_update(results_to_update, ['investigation', 'investigation_code', 'remarks', 'status', 'result_status'])
            
        # Delete existing parameters for the updated results
        if results_to_update:
            AutomationDummyResultParameter.objects.filter(dummy_result__in=results_to_update).delete()
            
        # Refetch all results for this batch to get their PKs for foreign keys
        all_res_objs = {r.result_id: r for r in AutomationDummyResult.objects.filter(result_id__in=batch_rids)}
        
        params_to_create = []
        for rid in batch_rids:
            res_obj = all_res_objs[rid]
            items = grouped[rid]
            for idx, r in enumerate(items):
                param_code = clean_val(r.get('parameter code'))
                param_name = clean_val(r.get('parameter'))
                if not param_name:
                    param_name = clean_val(r.get('parameter name'))
                res_val = clean_val(r.get('result value'))
                unit = clean_val(r.get('unit'))
                ref = clean_val(r.get('reference range'))
                
                param = param_code_map.get(param_code)
                if not param and param_name:
                    param = param_name_map.get(param_name.lower())
                    
                p_status = classify_from_range_string(res_val, ref)
                
                params_to_create.append(AutomationDummyResultParameter(
                    dummy_result=res_obj,
                    parameter=param,
                    parameter_name=param_name or (param.name if param else ''),
                    result_value=res_val,
                    unit=unit,
                    reference_range=ref,
                    display_order=idx,
                    result_status=p_status
                ))
                counts['parameters_created'] += 1
                
        if params_to_create:
            AutomationDummyResultParameter.objects.bulk_create(params_to_create)
            
    return counts
