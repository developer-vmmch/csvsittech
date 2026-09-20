import os
import sys
import io
import django
from openpyxl import Workbook

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import (
    Parameter, Investigation, InvestigationParameter,
    AutomationDummyResult, AutomationDummyResultParameter
)
from apps.lab.result_importer import (
    normalize_parameter_code,
    ResultImportValidationService,
    validate_result_import,
    import_dummy_results_batch
)

def create_test_result_workbook(rows_data):
    """
    Helper to generate an in-memory Results workbook.
    rows_data: list of dicts with keys:
      rid, inv_name, inv_code, param_name, param_code, val, unit, ref, remarks, status
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'Results'
    headers = [
        'Result ID', 'Investigation', 'Investigation Code',
        'Parameter', 'Parameter Code', 'Result Value',
        'Unit', 'Reference Range', 'Remarks', 'Status', 'Created On'
    ]
    ws.append(headers)
    for r in rows_data:
        ws.append([
            r.get('rid', 'RES-TEST-001'),
            r.get('inv_name', 'Complete Blood Count'),
            r.get('inv_code', 'CBC'),
            r.get('param_name', 'ESR'),
            r.get('param_code', '00022681'),
            r.get('val', '12'),
            r.get('unit', 'mm/first hour'),
            r.get('ref', '0-20'),
            r.get('remarks', 'Test remarks'),
            r.get('status', 'Saved'),
            '2026-09-20 12:00'
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

def test_case_1():
    print("--- CASE 1: Master ESR -> 00022681, Result ESR -> 00022681 (String with leading zeroes) ---")
    validator = ResultImportValidationService()
    row = {
        '_row_index': 2,
        'result id': 'RES-C1',
        'investigation code': 'CBC',
        'investigation': 'Complete Blood Count',
        'parameter code': '00022681',
        'parameter': 'ESR',
        'result value': '15',
        'unit': 'mm/first hour',
        'reference range': '0-20',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row)
    assert is_valid, f"Expected CASE 1 to be valid, got errors: {errors}"
    assert info['norm_param_code'] == '00022681', f"Expected '00022681', got {info['norm_param_code']}"
    assert len(errors) == 0
    print("CASE 1 PASSED: Code resolved to '00022681' and marked VALID.")

def test_case_2():
    print("--- CASE 2: Excel returns numeric 22681 (integer / float / unpadded string) ---")
    validator = ResultImportValidationService()
    
    # 2a: Integer cell value 22681
    row_int = {
        '_row_index': 3,
        'result id': 'RES-C2A',
        'investigation code': 'CBC',
        'investigation': 'Complete Blood Count',
        'parameter code': 22681,
        'parameter': 'ESR',
        'result value': '15',
        'unit': 'mm/first hour',
        'reference range': '0-20',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row_int)
    assert is_valid, f"Expected numeric int 22681 to be valid, got errors: {errors}"
    assert info['norm_param_code'] == '00022681', f"Expected '00022681', got {info['norm_param_code']}"
    print("  CASE 2a (int 22681) PASSED: safely resolved to '00022681' -> VALID.")

    # 2b: Float cell value 22681.0
    row_flt = {
        '_row_index': 4,
        'result id': 'RES-C2B',
        'investigation code': 'CBC',
        'investigation': 'Complete Blood Count',
        'parameter code': 22681.0,
        'parameter': 'ESR',
        'result value': '15',
        'unit': 'mm/first hour',
        'reference range': '0-20',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row_flt)
    assert is_valid, f"Expected float 22681.0 to be valid, got errors: {errors}"
    assert info['norm_param_code'] == '00022681', f"Expected '00022681', got {info['norm_param_code']}"
    print("  CASE 2b (float 22681.0) PASSED: safely resolved to '00022681' -> VALID.")

    # 2c: String cell value "22681"
    row_str = {
        '_row_index': 5,
        'result id': 'RES-C2C',
        'investigation code': 'CBC',
        'investigation': 'Complete Blood Count',
        'parameter code': '22681',
        'parameter': 'ESR',
        'result value': '15',
        'unit': 'mm/first hour',
        'reference range': '0-20',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row_str)
    assert is_valid, f"Expected string '22681' to be valid, got errors: {errors}"
    assert info['norm_param_code'] == '00022681', f"Expected '00022681', got {info['norm_param_code']}"
    print("  CASE 2c (str '22681') PASSED: safely resolved to '00022681' -> VALID.")

def test_case_3():
    print("--- CASE 3: Result code 00099999 (Non-existent in Master) ---")
    validator = ResultImportValidationService()
    row = {
        '_row_index': 6,
        'result id': 'RES-C3',
        'investigation code': 'CBC',
        'investigation': 'Complete Blood Count',
        'parameter code': '00099999',
        'parameter': 'Unknown Test',
        'result value': '5',
        'unit': '',
        'reference range': '',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row)
    assert not is_valid, "Expected CASE 3 to be INVALID"
    assert len(errors) == 1
    err_text = errors[0]['error']
    print(f"  Got error message: '{err_text}'")
    assert "Parameter code does not exist in Parameter Master" in err_text, f"Unexpected error: {err_text}"
    print("CASE 3 PASSED: Non-existent parameter code reported with exact error message.")

def test_case_4():
    print("--- CASE 4: Parameter exists globally but is NOT mapped to selected investigation ---")
    # Parameter 00022681 (ESR) exists, but investigation 'UR' (Urine Routine) does not include ESR.
    validator = ResultImportValidationService()
    row = {
        '_row_index': 7,
        'result id': 'RES-C4',
        'investigation code': 'UR',
        'investigation': 'URINE ROUTINE',
        'parameter code': '00022681',
        'parameter': 'ESR',
        'result value': '10',
        'unit': 'mm/first hour',
        'reference range': '0-20',
        'status': 'Saved'
    }
    is_valid, errors, info = validator.validate_row(row)
    assert not is_valid, "Expected CASE 4 to be INVALID"
    assert len(errors) == 1
    err_text = errors[0]['error']
    print(f"  Got error message: '{err_text}'")
    assert "Parameter exists but is not mapped to this investigation" in err_text or "Parameter is not mapped to investigation UR" in err_text, f"Unexpected error: {err_text}"
    print("CASE 4 PASSED: Unmapped investigation-parameter correctly rejected with informative error.")

def test_case_5():
    print("--- CASE 5: Idempotent import (running twice creates zero duplicate parameters or results) ---")
    import uuid
    from django.core.files.storage import FileSystemStorage
    from django.conf import settings
    
    unique_rid = f"RES-IDEMP-{uuid.uuid4().hex[:8]}"
    test_rows = [
        {
            'rid': unique_rid,
            'inv_name': 'Complete Blood Count',
            'inv_code': 'CBC',
            'param_name': 'ESR',
            'param_code': '00022681',
            'val': '14',
            'unit': 'mm/first hour',
            'ref': '0-20',
            'remarks': 'Idempotency test',
            'status': 'Saved'
        }
    ]
    buf = create_test_result_workbook(test_rows)
    fs = FileSystemStorage(location=os.path.join(settings.BASE_DIR, 'tmp_imports'))
    tmp_name = f'test_idemp_{uuid.uuid4().hex}.xlsx'
    saved_key = fs.save(tmp_name, buf)

    try:
        # First import
        counts1 = import_dummy_results_batch(saved_key, 0, 10)
        assert counts1['results_created'] == 1, f"Expected 1 created, got {counts1}"
        assert counts1['parameters_created'] == 1, f"Expected 1 param created, got {counts1}"
        
        res1 = AutomationDummyResult.objects.get(result_id=unique_rid)
        params1 = list(res1.parameters.all())
        assert len(params1) == 1
        assert params1[0].parameter.code == '00022681'
        assert params1[0].result_value == '14'

        # Second import (same file)
        counts2 = import_dummy_results_batch(saved_key, 0, 10)
        assert counts2['results_created'] == 0, f"Expected 0 created, got {counts2}"
        assert counts2['results_updated'] == 1, f"Expected 1 updated, got {counts2}"
        assert counts2['parameters_created'] == 1, f"Expected 1 param recreated, got {counts2}"

        # Verify no duplicate results or parameters exist
        total_matching_results = AutomationDummyResult.objects.filter(result_id=unique_rid).count()
        assert total_matching_results == 1, f"Duplicate results found: {total_matching_results}"

        res2 = AutomationDummyResult.objects.get(result_id=unique_rid)
        params2 = list(res2.parameters.all())
        assert len(params2) == 1, f"Duplicate parameters found: {len(params2)}"
        assert params2[0].parameter.code == '00022681'
        print("CASE 5 PASSED: Second import updated existing record without duplication.")
    finally:
        AutomationDummyResult.objects.filter(result_id=unique_rid).delete()
        if fs.exists(saved_key):
            fs.delete(saved_key)

def test_actual_file_validation():
    print("\n--- Validating actual result file: result_export_validated_hospital_ranges.xlsx ---")
    file_path = '/home/Loosifer/Downloads/result_export_validated_hospital_ranges.xlsx'
    with open(file_path, 'rb') as f:
        res = validate_result_import(f)
    
    errors = res.get('errors', [])
    stats = res.get('stats', {})
    print(f"Total results: {stats.get('total_results')}")
    print(f"Total parameters: {stats.get('parameters')}")
    print(f"Errors detected: {len(errors)}")
    assert len(errors) == 0, f"Expected 0 errors on actual file, got {len(errors)}: {errors[:5]}"
    print("ACTUAL FILE VALIDATION PASSED: 0 errors detected on result_export_validated_hospital_ranges.xlsx!")

if __name__ == '__main__':
    test_case_1()
    test_case_2()
    test_case_3()
    test_case_4()
    test_case_5()
    test_actual_file_validation()
    print("\n==============================================")
    print("ALL 5 TEST CASES AND ACTUAL FILE VALIDATION PASSED!")
    print("==============================================")
