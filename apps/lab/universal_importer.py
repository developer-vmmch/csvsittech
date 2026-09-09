"""
Universal Import / Export engine for VMMC ERP Lab Master.

Handles a multi-sheet workbook with sheets:
  Departments, Diagnoses, Investigations, Parameters, Age Groups,
  Reference Ranges, Investigation Parameters, Diagnosis Investigations,
  Diagnosis Departments

Export produces exactly the same schema the importer expects (round-trip safe).
"""

import io
import logging
from decimal import Decimal, InvalidOperation

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from django.db import transaction

from apps.lab.models import (
    LabDepartment, Diagnosis, Investigation, Parameter, AgeGroup, SampleType,
    InvestigationParameter, ParameterReferenceRange, DiagnosisInvestigationMap,
    DiagnosisDepartmentMapping,
)
from apps.patients.models import Department

logger = logging.getLogger('apps.lab.universal_importer')

# ---------------------------------------------------------------------------
# Single source of truth: sheet names and their column definitions
# ---------------------------------------------------------------------------
SHEET_DEFS = {
    'Departments': {
        'required': True,
        'columns': ['Department Name', 'Department Code', 'Status'],
    },
    'Diagnoses': {
        'required': True,
        'columns': ['Diagnosis Name', 'Diagnosis Code', 'Status'],
    },
    'Investigations': {
        'required': True,
        'columns': ['Investigation Name', 'Investigation Code', 'Department',
                    'Sample Type', 'Is Panel', 'Status'],
    },
    'Parameters': {
        'required': True,
        'columns': ['Parameter Name', 'Parameter Code', 'Data Type',
                    'Default Unit', 'Status'],
    },
    'Age Groups': {
        'required': False,
        'columns': ['Age Group Code', 'Age Group Name', 'Age From',
                    'Age From Unit', 'Age To', 'Age To Unit', 'Gender', 'Status'],
    },
    'Reference Ranges': {
        'required': False,
        'columns': ['Investigation Code', 'Parameter Code', 'Age Group Code',
                    'Gender', 'Diagnosis Code', 'Min Value', 'Max Value',
                    'Normal Value', 'Unit', 'Method', 'Remarks', 'Status'],
    },
    'Investigation Parameters': {
        'required': False,
        'columns': ['Investigation Code', 'Parameter Code', 'Display Order', 'Status'],
    },
    'Diagnosis Investigations': {
        'required': False,
        'columns': ['Diagnosis Code', 'Investigation Code', 'Age Group Code', 'Status'],
    },
    'Diagnosis Departments': {
        'required': False,
        'columns': ['Diagnosis Code', 'Department Code', 'Age Group Code', 'Status'],
    },
}

SHEET_ORDER = [
    'Departments', 'Diagnoses', 'Investigations', 'Parameters',
    'Age Groups', 'Reference Ranges', 'Investigation Parameters',
    'Diagnosis Investigations', 'Diagnosis Departments',
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_val(v):
    if v is None:
        return ''
    return str(v).strip()


def get_decimal(v):
    if v is None or str(v).strip() == '':
        return None
    try:
        return Decimal(str(v).strip())
    except Exception:
        return None


def is_active_bool(v):
    if v is None:
        return True
    return str(v).strip().lower() in ['active', 'true', '1', 'yes']


def normalize_sheet_name(raw_name):
    """Strip whitespace; return canonical SHEET_DEFS key or the raw name."""
    name = str(raw_name).strip()
    if name in SHEET_DEFS:
        return name
    for k in SHEET_DEFS:
        if k.lower() == name.lower():
            return k
    return name


def get_workbook_sheet_map(wb):
    """Return {canonical_name: ws} with whitespace/case normalisation."""
    result = {}
    for raw in wb.sheetnames:
        result[normalize_sheet_name(raw)] = wb[raw]
    return result


def parse_sheet(ws):
    """Parse worksheet into list of row-dicts (lowercased keys, skips blanks)."""
    if ws is None:
        return []
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [
        str(h).strip().lower() if (h is not None and str(h).strip()) else '_col_%d' % i
        for i, h in enumerate(rows[0])
    ]
    data = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_data = {}
        is_empty = True
        for col_idx, value in enumerate(row):
            if col_idx < len(headers):
                if value is not None and str(value).strip():
                    is_empty = False
                row_data[headers[col_idx]] = value
        if not is_empty:
            row_data['_row_index'] = row_idx
            data.append(row_data)
    return data


def detect_format(wb, sheet_map):
    """Returns 'multi', 'legacy', or 'unknown'."""
    if len(set(SHEET_DEFS.keys()) & set(sheet_map.keys())) >= 3:
        return 'multi'
    if 'Universal Master' in wb.sheetnames:
        return 'legacy'
    return 'unknown'


def _style_header_row(ws):
    fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')
    font = Font(bold=True, color='FFFFFF', size=10)
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal='center', vertical='center')


# ---------------------------------------------------------------------------
# VALIDATION (read-only — no DB writes)
# ---------------------------------------------------------------------------

def validate_import(file_obj):
    """
    Validate a Universal Master workbook.

    Returns a dict with keys:
        format, detected_sheets, stats, errors, warnings, valid

    Every error dict has:
        {sheet, row, field, value, message}

    NO database writes occur here.
    """
    errors = []
    warnings = []
    stats = {
        'departments':        {'existing': 0, 'new': 0},
        'diagnoses':          {'existing': 0, 'new': 0},
        'investigations':     {'existing': 0, 'new': 0},
        'parameters':         {'existing': 0, 'new': 0},
        'age_groups':         {'existing': 0, 'new': 0},
        'reference_ranges':   {'new': 0, 'updates': 0},
        'inv_param_mappings': {'existing': 0, 'new': 0},
        'diag_inv_mappings':  {'existing': 0, 'new': 0},
        'diag_dept_mappings': {'existing': 0, 'new': 0},
    }

    def err(sheet, row, field, value, message):
        errors.append({'sheet': sheet, 'row': row, 'field': field,
                       'value': str(value), 'message': message})

    # -- Open workbook -------------------------------------------------------
    try:
        wb = load_workbook(filename=file_obj, data_only=True, read_only=False)
    except Exception as exc:
        logger.exception('universal_importer.validate_import: failed to open workbook')
        return {
            'format': 'unknown', 'detected_sheets': [],
            'stats': stats, 'warnings': [],
            'errors': [{'sheet': 'File', 'row': 0, 'field': 'File', 'value': '',
                        'message': 'Could not open Excel file: %s' % exc}],
            'valid': False,
        }

    detected_sheets = list(wb.sheetnames)
    sheet_map = get_workbook_sheet_map(wb)
    fmt = detect_format(wb, sheet_map)
    logger.info('universal_importer.validate_import: format=%s sheets=%s', fmt, detected_sheets)

    # -- Legacy format -------------------------------------------------------
    if fmt == 'legacy':
        warnings.append(
            "This workbook uses the older single-sheet 'Universal Master' format and does not "
            "contain complete mapping sheets. Please download the latest Universal Import Template "
            "or use Export Complete Master to get the current multi-sheet format."
        )
        return {'format': 'legacy', 'detected_sheets': detected_sheets,
                'stats': stats, 'errors': [], 'warnings': warnings, 'valid': False}

    if fmt == 'unknown':
        return {
            'format': 'unknown', 'detected_sheets': detected_sheets,
            'stats': stats, 'warnings': [],
            'errors': [{'sheet': 'File', 'row': 0, 'field': 'File', 'value': '',
                        'message': (
                            'Unrecognised workbook format. Detected sheets: %s. '
                            'Expected a multi-sheet Universal Master workbook. '
                            'Use Export Complete Master or Download Blank Template.' % detected_sheets
                        )}],
            'valid': False,
        }

    # -- Check required sheets exist ----------------------------------------
    for sheet_name, sdef in SHEET_DEFS.items():
        if sdef['required'] and sheet_name not in sheet_map:
            err(sheet_name, 0, 'Sheet', sheet_name,
                "Required sheet '%s' is missing from the workbook." % sheet_name)

    if errors:
        return {'format': fmt, 'detected_sheets': detected_sheets,
                'stats': stats, 'errors': errors, 'warnings': warnings, 'valid': False}

    # -- Parse all sheets ----------------------------------------------------
    def load(name):
        ws = sheet_map.get(name)
        if ws is None:
            return []
        try:
            return parse_sheet(ws)
        except Exception as exc:
            logger.exception('universal_importer: failed to parse sheet %s', name)
            err(name, 0, 'Sheet', name, "Could not read sheet '%s': %s" % (name, exc))
            return []

    depts      = load('Departments')
    diags      = load('Diagnoses')
    invs       = load('Investigations')
    params     = load('Parameters')
    ages       = load('Age Groups')
    refs       = load('Reference Ranges')
    inv_params = load('Investigation Parameters')
    diag_invs  = load('Diagnosis Investigations')
    diag_depts = load('Diagnosis Departments')

    if errors:
        return {'format': fmt, 'detected_sheets': detected_sheets,
                'stats': stats, 'errors': errors, 'warnings': warnings, 'valid': False}

    # -- DB lookup sets (read-only) ------------------------------------------
    try:
        db_dept_codes  = set(Department.objects.values_list('code', flat=True))
        db_diag_codes  = set(Diagnosis.objects.values_list('code', flat=True))
        db_inv_codes   = set(Investigation.objects.values_list('code', flat=True))
        db_param_codes = set(Parameter.objects.values_list('code', flat=True))
        db_age_codes   = set(AgeGroup.objects.values_list('code', flat=True))
    except Exception as exc:
        logger.exception('universal_importer: DB lookup failed during validation')
        return {
            'format': fmt, 'detected_sheets': detected_sheets, 'stats': stats, 'warnings': [],
            'errors': [{'sheet': 'Database', 'row': 0, 'field': '', 'value': '',
                        'message': 'Database lookup failed: %s' % exc}],
            'valid': False,
        }

    # Working sets include codes from this file (so forward-references work)
    file_dept_codes  = set(db_dept_codes)
    file_diag_codes  = set(db_diag_codes)
    file_inv_codes   = set(db_inv_codes)
    file_param_codes = set(db_param_codes)
    file_age_codes   = set(db_age_codes)

    # -- Departments ---------------------------------------------------------
    for r in depts:
        code = clean_val(r.get('department code'))
        if not code:
            err('Departments', r['_row_index'], 'Department Code', '', 'Department Code is required')
            continue
        stats['departments']['existing' if code in db_dept_codes else 'new'] += 1
        file_dept_codes.add(code)

    # -- Diagnoses -----------------------------------------------------------
    for r in diags:
        code = clean_val(r.get('diagnosis code'))
        if not code:
            err('Diagnoses', r['_row_index'], 'Diagnosis Code', '', 'Diagnosis Code is required')
            continue
        stats['diagnoses']['existing' if code in db_diag_codes else 'new'] += 1
        file_diag_codes.add(code)

    # -- Investigations ------------------------------------------------------
    for r in invs:
        code = clean_val(r.get('investigation code'))
        if not code:
            err('Investigations', r['_row_index'], 'Investigation Code', '',
                'Investigation Code is required')
            continue
        stats['investigations']['existing' if code in db_inv_codes else 'new'] += 1
        file_inv_codes.add(code)

    # -- Parameters ----------------------------------------------------------
    for r in params:
        code = clean_val(r.get('parameter code'))
        if not code:
            err('Parameters', r['_row_index'], 'Parameter Code', '', 'Parameter Code is required')
            continue
        stats['parameters']['existing' if code in db_param_codes else 'new'] += 1
        file_param_codes.add(code)

    # -- Age Groups ----------------------------------------------------------
    for r in ages:
        code = clean_val(r.get('age group code'))
        if not code:
            err('Age Groups', r['_row_index'], 'Age Group Code', '', 'Age Group Code is required')
            continue
        stats['age_groups']['existing' if code in db_age_codes else 'new'] += 1
        file_age_codes.add(code)

    # -- Reference Ranges ----------------------------------------------------
    for r in refs:
        inv_code   = clean_val(r.get('investigation code'))
        param_code = clean_val(r.get('parameter code'))
        age_code   = clean_val(r.get('age group code'))
        min_v      = clean_val(r.get('min value'))
        max_v      = clean_val(r.get('max value'))
        row        = r['_row_index']
        if not inv_code:
            err('Reference Ranges', row, 'Investigation Code', '', 'Investigation Code is required')
        elif inv_code not in file_inv_codes:
            err('Reference Ranges', row, 'Investigation Code', inv_code,
                "Investigation Code '%s' does not exist" % inv_code)
        if not param_code:
            err('Reference Ranges', row, 'Parameter Code', '', 'Parameter Code is required')
        elif param_code not in file_param_codes:
            err('Reference Ranges', row, 'Parameter Code', param_code,
                "Parameter Code '%s' does not exist" % param_code)
        if age_code and age_code not in file_age_codes:
            err('Reference Ranges', row, 'Age Group Code', age_code,
                "Age Group Code '%s' does not exist" % age_code)
        if min_v and max_v:
            try:
                if Decimal(min_v) > Decimal(max_v):
                    err('Reference Ranges', row, 'Min Value', min_v,
                        'Min (%s) cannot be greater than Max (%s)' % (min_v, max_v))
            except Exception:
                pass
        stats['reference_ranges']['new'] += 1

    # -- Investigation Parameters --------------------------------------------
    for r in inv_params:
        inv_code   = clean_val(r.get('investigation code'))
        param_code = clean_val(r.get('parameter code'))
        row = r['_row_index']
        if inv_code not in file_inv_codes:
            err('Investigation Parameters', row, 'Investigation Code', inv_code,
                "Investigation Code '%s' does not exist" % inv_code)
        if param_code not in file_param_codes:
            err('Investigation Parameters', row, 'Parameter Code', param_code,
                "Parameter Code '%s' does not exist" % param_code)
        stats['inv_param_mappings']['new'] += 1

    # -- Diagnosis Investigations --------------------------------------------
    for r in diag_invs:
        diag_code = clean_val(r.get('diagnosis code'))
        inv_code  = clean_val(r.get('investigation code'))
        age_code  = clean_val(r.get('age group code'))
        row = r['_row_index']
        if diag_code not in file_diag_codes:
            err('Diagnosis Investigations', row, 'Diagnosis Code', diag_code,
                "Diagnosis Code '%s' does not exist" % diag_code)
        if inv_code not in file_inv_codes:
            err('Diagnosis Investigations', row, 'Investigation Code', inv_code,
                "Investigation Code '%s' does not exist" % inv_code)
        if age_code and age_code not in file_age_codes:
            err('Diagnosis Investigations', row, 'Age Group Code', age_code,
                "Age Group Code '%s' does not exist" % age_code)
        stats['diag_inv_mappings']['new'] += 1

    # -- Diagnosis Departments -----------------------------------------------
    for r in diag_depts:
        diag_code = clean_val(r.get('diagnosis code'))
        dept_code = clean_val(r.get('department code'))
        age_code  = clean_val(r.get('age group code'))
        row = r['_row_index']
        if diag_code not in file_diag_codes:
            err('Diagnosis Departments', row, 'Diagnosis Code', diag_code,
                "Diagnosis Code '%s' does not exist" % diag_code)
        if dept_code not in file_dept_codes:
            err('Diagnosis Departments', row, 'Department Code', dept_code,
                "Department Code '%s' does not exist" % dept_code)
        if age_code and age_code not in file_age_codes:
            err('Diagnosis Departments', row, 'Age Group Code', age_code,
                "Age Group Code '%s' does not exist" % age_code)
        stats['diag_dept_mappings']['new'] += 1

    valid = len(errors) == 0
    logger.info('universal_importer: validation complete valid=%s errors=%d', valid, len(errors))
    return {
        'format': fmt,
        'detected_sheets': detected_sheets,
        'stats': stats,
        'errors': errors[:100],
        'warnings': warnings,
        'valid': valid,
    }


# ---------------------------------------------------------------------------
# IMPORT (DB writes inside transaction.atomic)
# ---------------------------------------------------------------------------

def import_universal_master(file_obj, admin_user=None):
    """
    Import a validated multi-sheet Universal Master workbook.
    Any error rolls back the entire transaction.
    """
    try:
        wb = load_workbook(filename=file_obj, data_only=True)
    except Exception as exc:
        logger.exception('universal_importer: failed to open workbook for import')
        raise ValueError('Could not open Excel file: %s' % exc)

    sheet_map = get_workbook_sheet_map(wb)

    def load(name):
        ws = sheet_map.get(name)
        if ws is None:
            return []
        return parse_sheet(ws)

    depts      = load('Departments')
    diags      = load('Diagnoses')
    invs       = load('Investigations')
    params     = load('Parameters')
    ages       = load('Age Groups')
    refs       = load('Reference Ranges')
    inv_params = load('Investigation Parameters')
    diag_invs  = load('Diagnosis Investigations')
    diag_depts = load('Diagnosis Departments')

    counts = {
        'departments_created': 0,    'departments_updated': 0,
        'diagnoses_created': 0,      'diagnoses_updated': 0,
        'investigations_created': 0, 'investigations_updated': 0,
        'parameters_created': 0,     'parameters_updated': 0,
        'age_groups_created': 0,     'age_groups_updated': 0,
        'ref_ranges_created': 0,     'ref_ranges_updated': 0,
        'mappings_created': 0,       'mappings_updated': 0,
    }

    with transaction.atomic():
        # 1. Departments
        for r in depts:
            code   = clean_val(r.get('department code'))
            name   = clean_val(r.get('department name'))
            status = is_active_bool(r.get('status'))
            if code and name:
                _, c = Department.objects.update_or_create(
                    code=code, defaults={'name': name, 'is_active': status})
                counts['departments_created' if c else 'departments_updated'] += 1

        # 2. Diagnoses
        for r in diags:
            code   = clean_val(r.get('diagnosis code'))
            name   = clean_val(r.get('diagnosis name'))
            status = is_active_bool(r.get('status'))
            if code and name:
                _, c = Diagnosis.objects.update_or_create(
                    code=code, defaults={'name': name, 'is_active': status})
                counts['diagnoses_created' if c else 'diagnoses_updated'] += 1

        # 3. Parameters (before Investigations — no dep but good order)
        for r in params:
            code   = clean_val(r.get('parameter code'))
            name   = clean_val(r.get('parameter name'))
            dtype  = clean_val(r.get('data type')) or 'NUMERIC'
            unit   = clean_val(r.get('default unit'))
            status = is_active_bool(r.get('status'))
            if code and name:
                _, c = Parameter.objects.update_or_create(
                    code=code,
                    defaults={'name': name, 'data_type': dtype,
                              'default_unit': unit, 'is_active': status})
                counts['parameters_created' if c else 'parameters_updated'] += 1

        # 4. Investigations
        for r in invs:
            code      = clean_val(r.get('investigation code'))
            name      = clean_val(r.get('investigation name'))
            dept_name = clean_val(r.get('department'))
            samp_name = clean_val(r.get('sample type'))
            is_panel  = clean_val(r.get('is panel')).lower() in ['yes', 'true', '1']
            status    = is_active_bool(r.get('status'))
            if code and name:
                ldept = LabDepartment.objects.get_or_create(name=dept_name)[0] if dept_name else None
                samp  = SampleType.objects.get_or_create(name=samp_name)[0] if samp_name else None
                _, c = Investigation.objects.update_or_create(
                    code=code,
                    defaults={'name': name, 'department': ldept, 'sample_type': samp,
                              'is_panel': is_panel, 'is_active': status})
                counts['investigations_created' if c else 'investigations_updated'] += 1

        # 5. Age Groups
        for r in ages:
            code    = clean_val(r.get('age group code'))
            ag_name = clean_val(r.get('age group name'))
            a_from  = clean_val(r.get('age from'))
            f_unit  = clean_val(r.get('age from unit')) or 'Years'
            a_to    = clean_val(r.get('age to'))
            t_unit  = clean_val(r.get('age to unit')) or 'Years'
            gender  = clean_val(r.get('gender')) or 'All'
            status  = is_active_bool(r.get('status'))
            if code and ag_name:
                _, c = AgeGroup.objects.update_or_create(
                    code=code,
                    defaults={
                        'label': ag_name,
                        'min_age_value': int(a_from) if a_from and a_from.isdigit() else None,
                        'min_age_unit':  f_unit,
                        'max_age_value': int(a_to) if a_to and a_to.isdigit() else None,
                        'max_age_unit':  t_unit,
                        'gender':        gender,
                        'is_active':     status,
                    })
                counts['age_groups_created' if c else 'age_groups_updated'] += 1

        # 6. Investigation Parameters
        for r in inv_params:
            inv_code   = clean_val(r.get('investigation code'))
            param_code = clean_val(r.get('parameter code'))
            order      = clean_val(r.get('display order'))
            status     = is_active_bool(r.get('status'))
            if inv_code and param_code:
                inv   = Investigation.objects.filter(code=inv_code).first()
                param = Parameter.objects.filter(code=param_code).first()
                if inv and param:
                    _, c = InvestigationParameter.objects.update_or_create(
                        investigation=inv, parameter=param,
                        defaults={
                            'name': param.name, 'code': param.code,
                            'display_order': int(order) if order and order.isdigit() else 0,
                            'is_active': status,
                        })
                    counts['mappings_created' if c else 'mappings_updated'] += 1

        # 7. Reference Ranges
        for r in refs:
            inv_code   = clean_val(r.get('investigation code'))
            param_code = clean_val(r.get('parameter code'))
            age_code   = clean_val(r.get('age group code'))
            gender     = clean_val(r.get('gender')) or 'All'
            diag_code  = clean_val(r.get('diagnosis code'))
            min_v  = get_decimal(r.get('min value'))
            max_v  = get_decimal(r.get('max value'))
            n_val  = clean_val(r.get('normal value'))
            unit   = clean_val(r.get('unit'))
            meth   = clean_val(r.get('method'))
            rem    = clean_val(r.get('remarks'))
            status = is_active_bool(r.get('status'))
            if inv_code and param_code:
                ip   = InvestigationParameter.objects.filter(
                    investigation__code=inv_code, parameter__code=param_code).first()
                ag   = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                diag = Diagnosis.objects.filter(code=diag_code).first() if diag_code else None
                if ip:
                    defaults = {
                        'min_value': min_v, 'max_value': max_v,
                        'reference_text': n_val,
                        'unit': unit, 'method': meth, 'remarks': rem,
                        'is_active': status,
                        'range_type': 'Text' if (n_val and not (min_v or max_v)) else 'Numeric',
                    }
                    existing = ParameterReferenceRange.objects.filter(
                        investigation_parameter=ip, age_group=ag,
                        gender=gender, diagnosis=diag)
                    if existing.exists():
                        first = existing.first()
                        for k, v in defaults.items():
                            setattr(first, k, v)
                        first.save()
                        if existing.count() > 1:
                            existing.exclude(id=first.id).delete()
                        counts['ref_ranges_updated'] += 1
                    else:
                        ParameterReferenceRange.objects.create(
                            investigation_parameter=ip, age_group=ag,
                            gender=gender, diagnosis=diag, **defaults)
                        counts['ref_ranges_created'] += 1

        # 8. Diagnosis Investigations
        for r in diag_invs:
            diag_code = clean_val(r.get('diagnosis code'))
            inv_code  = clean_val(r.get('investigation code'))
            age_code  = clean_val(r.get('age group code'))
            status    = is_active_bool(r.get('status'))
            if diag_code and inv_code:
                diag = Diagnosis.objects.filter(code=diag_code).first()
                inv  = Investigation.objects.filter(code=inv_code).first()
                ag   = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                if diag and inv:
                    _, c = DiagnosisInvestigationMap.objects.update_or_create(
                        diagnosis=diag, investigation=inv, age_group=ag,
                        defaults={'is_active': status})
                    counts['mappings_created' if c else 'mappings_updated'] += 1

        # 9. Diagnosis Departments
        for r in diag_depts:
            diag_code = clean_val(r.get('diagnosis code'))
            dept_code = clean_val(r.get('department code'))
            age_code  = clean_val(r.get('age group code'))
            if diag_code and dept_code:
                diag = Diagnosis.objects.filter(code=diag_code).first()
                dept = Department.objects.filter(code=dept_code).first()
                ag   = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                if diag and dept:
                    _, c = DiagnosisDepartmentMapping.objects.get_or_create(
                        diagnosis=diag, department=dept, age_group=ag)
                    counts['mappings_created' if c else 'mappings_updated'] += 1

    logger.info('universal_importer: import complete counts=%s', counts)
    return counts


# Alias — view code imports commit_import; this keeps it working
commit_import = import_universal_master


# ---------------------------------------------------------------------------
# EXPORT (produces exactly what the importer expects — round-trip safe)
# ---------------------------------------------------------------------------

def export_universal_master():
    """Export all Lab Master data as a multi-sheet workbook."""
    wb = Workbook(write_only=False)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])

    # Departments
    ws = wb.create_sheet('Departments')
    ws.append(SHEET_DEFS['Departments']['columns'])
    for d in Department.objects.order_by('name'):
        ws.append([d.name, d.code, 'Active' if d.is_active else 'Inactive'])
    _style_header_row(ws)

    # Diagnoses
    ws = wb.create_sheet('Diagnoses')
    ws.append(SHEET_DEFS['Diagnoses']['columns'])
    for d in Diagnosis.objects.order_by('name'):
        ws.append([d.name, d.code, 'Active' if d.is_active else 'Inactive'])
    _style_header_row(ws)

    # Investigations
    ws = wb.create_sheet('Investigations')
    ws.append(SHEET_DEFS['Investigations']['columns'])
    for i in Investigation.objects.select_related('department', 'sample_type').order_by('name'):
        ws.append([
            i.name, i.code,
            i.department.name if i.department else '',
            i.sample_type.name if i.sample_type else '',
            'Yes' if i.is_panel else 'No',
            'Active' if i.is_active else 'Inactive',
        ])
    _style_header_row(ws)

    # Parameters
    ws = wb.create_sheet('Parameters')
    ws.append(SHEET_DEFS['Parameters']['columns'])
    for p in Parameter.objects.order_by('name'):
        ws.append([p.name, p.code, p.data_type, p.default_unit or '',
                   'Active' if p.is_active else 'Inactive'])
    _style_header_row(ws)

    # Age Groups
    ws = wb.create_sheet('Age Groups')
    ws.append(SHEET_DEFS['Age Groups']['columns'])
    for a in AgeGroup.objects.order_by('code'):
        ws.append([
            a.code, a.label,
            a.min_age_value if a.min_age_value is not None else '',
            a.min_age_unit or 'Years',
            a.max_age_value if a.max_age_value is not None else '',
            a.max_age_unit or 'Years',
            a.gender,
            'Active' if a.is_active else 'Inactive',
        ])
    _style_header_row(ws)

    # Reference Ranges
    ws = wb.create_sheet('Reference Ranges')
    ws.append(SHEET_DEFS['Reference Ranges']['columns'])
    for r in ParameterReferenceRange.objects.select_related(
        'investigation_parameter__investigation',
        'investigation_parameter__parameter',
        'age_group', 'diagnosis',
    ).order_by('investigation_parameter__investigation__code'):
        ip = r.investigation_parameter
        ws.append([
            ip.investigation.code,
            ip.parameter.code if ip.parameter else '',
            r.age_group.code if r.age_group else '',   # code, not label
            r.gender,
            r.diagnosis.code if r.diagnosis else '',
            r.min_value, r.max_value,
            r.reference_text or '', r.unit or '',
            r.method or '', r.remarks or '',
            'Active' if r.is_active else 'Inactive',
        ])
    _style_header_row(ws)

    # Investigation Parameters
    ws = wb.create_sheet('Investigation Parameters')
    ws.append(SHEET_DEFS['Investigation Parameters']['columns'])
    for ip in InvestigationParameter.objects.select_related(
        'investigation', 'parameter'
    ).order_by('investigation__code', 'display_order'):
        if ip.parameter:
            ws.append([
                ip.investigation.code, ip.parameter.code,
                ip.display_order,
                'Active' if ip.is_active else 'Inactive',
            ])
    _style_header_row(ws)

    # Diagnosis Investigations
    ws = wb.create_sheet('Diagnosis Investigations')
    ws.append(SHEET_DEFS['Diagnosis Investigations']['columns'])
    for di in DiagnosisInvestigationMap.objects.select_related(
        'diagnosis', 'investigation', 'age_group'
    ).order_by('diagnosis__code'):
        ws.append([
            di.diagnosis.code, di.investigation.code,
            di.age_group.code if di.age_group else '',   # code, not label
            'Active' if di.is_active else 'Inactive',
        ])
    _style_header_row(ws)

    # Diagnosis Departments
    ws = wb.create_sheet('Diagnosis Departments')
    ws.append(SHEET_DEFS['Diagnosis Departments']['columns'])
    for dd in DiagnosisDepartmentMapping.objects.select_related(
        'diagnosis', 'department', 'age_group'
    ).order_by('diagnosis__code'):
        ws.append([
            dd.diagnosis.code, dd.department.code,
            dd.age_group.code if dd.age_group else '',   # code, not label
            'Active',
        ])
    _style_header_row(ws)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_blank_template():
    """Produce a blank multi-sheet template with headers only."""
    wb = Workbook(write_only=False)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    for sheet_name in SHEET_ORDER:
        ws = wb.create_sheet(sheet_name)
        ws.append(SHEET_DEFS[sheet_name]['columns'])
        _style_header_row(ws)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def clean_val(v):
    if v is None:
        return ""
    return str(v).strip()

def get_decimal(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return Decimal(str(v).strip())
    except Exception:
        raise ValueError(f"Invalid numeric value: {v}")

def is_active_bool(v):
    if v is None:
        return True
    return str(v).strip().lower() in ['active', 'true', '1', 'yes']

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

def validate_import(file_obj):
    errors = []
    warnings = []
    stats = {
        'departments': {'existing': 0, 'new': 0, 'updates': 0},
        'diagnoses': {'existing': 0, 'new': 0, 'updates': 0},
        'investigations': {'existing': 0, 'new': 0, 'updates': 0},
        'parameters': {'existing': 0, 'new': 0, 'updates': 0},
        'reference_ranges': {'new': 0, 'updates': 0},
        'inv_param_mappings': {'existing': 0, 'new': 0},
        'diag_inv_mappings': {'existing': 0, 'new': 0},
        'diag_dept_mappings': {'existing': 0, 'new': 0},
        'age_groups': {'existing': 0, 'new': 0, 'updates': 0},
    }
    
    try:
        wb = load_workbook(filename=file_obj, data_only=True)
    except Exception as e:
        return {'errors': [{'row': 0, 'field': 'File', 'value': '', 'error': f"Could not parse Excel: {str(e)}"}]}

    is_legacy = 'Universal Master' in wb.sheetnames and len(wb.sheetnames) == 1
    if is_legacy:
        warnings.append("Using legacy single-sheet format. Mapping data might be incomplete.")
        # Minimal legacy validation
        data = parse_excel_sheet(wb, 'Universal Master')
        if not data:
            errors.append({'row': 0, 'field': 'File', 'value': '', 'error': 'Legacy sheet is empty.'})
        return {'stats': stats, 'warnings': warnings, 'errors': errors}

    # Multisheet validation
    depts = parse_excel_sheet(wb, 'Departments')
    diags = parse_excel_sheet(wb, 'Diagnoses')
    invs = parse_excel_sheet(wb, 'Investigations')
    params = parse_excel_sheet(wb, 'Parameters')
    ages = parse_excel_sheet(wb, 'Age Groups')
    refs = parse_excel_sheet(wb, 'Reference Ranges')
    inv_params = parse_excel_sheet(wb, 'Investigation Parameters')
    diag_invs = parse_excel_sheet(wb, 'Diagnosis Investigations')
    diag_depts = parse_excel_sheet(wb, 'Diagnosis Departments')
    
    valid_dept_codes = set(Department.objects.values_list('code', flat=True))
    for r in depts:
        code = clean_val(r.get('department code'))
        if not code:
            errors.append({'row': r['_row_index'], 'field': 'Department Code', 'value': '', 'error': 'Missing Code'})
        else:
            if code in valid_dept_codes:
                stats['departments']['existing'] += 1
            else:
                stats['departments']['new'] += 1
                valid_dept_codes.add(code)

    valid_diag_codes = set(Diagnosis.objects.values_list('code', flat=True))
    for r in diags:
        code = clean_val(r.get('diagnosis code'))
        if not code:
            errors.append({'row': r['_row_index'], 'field': 'Diagnosis Code', 'value': '', 'error': 'Missing Code'})
        else:
            if code in valid_diag_codes:
                stats['diagnoses']['existing'] += 1
            else:
                stats['diagnoses']['new'] += 1
                valid_diag_codes.add(code)

    valid_inv_codes = set(Investigation.objects.values_list('code', flat=True))
    for r in invs:
        code = clean_val(r.get('investigation code'))
        if not code:
            errors.append({'row': r['_row_index'], 'field': 'Investigation Code', 'value': '', 'error': 'Missing Code'})
        else:
            if code in valid_inv_codes:
                stats['investigations']['existing'] += 1
            else:
                stats['investigations']['new'] += 1
                valid_inv_codes.add(code)

    valid_param_codes = set(Parameter.objects.values_list('code', flat=True))
    for r in params:
        code = clean_val(r.get('parameter code'))
        if not code:
            errors.append({'row': r['_row_index'], 'field': 'Parameter Code', 'value': '', 'error': 'Missing Code'})
        else:
            if code in valid_param_codes:
                stats['parameters']['existing'] += 1
            else:
                stats['parameters']['new'] += 1
                valid_param_codes.add(code)

    valid_age_codes = set(AgeGroup.objects.values_list('code', flat=True))
    for r in ages:
        code = clean_val(r.get('age group code'))
        if not code:
            errors.append({'row': r['_row_index'], 'field': 'Age Group Code', 'value': '', 'error': 'Missing Code'})
        else:
            if code in valid_age_codes:
                stats['age_groups']['existing'] += 1
            else:
                stats['age_groups']['new'] += 1
                valid_age_codes.add(code)
                
    for r in refs:
        inv_code = clean_val(r.get('investigation code'))
        if inv_code not in valid_inv_codes:
            errors.append({'row': r['_row_index'], 'field': 'Investigation Code', 'value': inv_code, 'error': 'Invalid Investigation Code'})
        stats['reference_ranges']['new'] += 1

    for r in inv_params:
        inv_code = clean_val(r.get('investigation code'))
        param_code = clean_val(r.get('parameter code'))
        if inv_code not in valid_inv_codes:
            errors.append({'row': r['_row_index'], 'field': 'Investigation Code', 'value': inv_code, 'error': 'Orphan Mapping: Invalid Investigation'})
        if param_code not in valid_param_codes:
            errors.append({'row': r['_row_index'], 'field': 'Parameter Code', 'value': param_code, 'error': 'Orphan Mapping: Invalid Parameter'})
        stats['inv_param_mappings']['new'] += 1

    for r in diag_invs:
        diag_code = clean_val(r.get('diagnosis code'))
        inv_code = clean_val(r.get('investigation code'))
        if diag_code not in valid_diag_codes:
            errors.append({'row': r['_row_index'], 'field': 'Diagnosis Code', 'value': diag_code, 'error': 'Orphan Mapping: Invalid Diagnosis'})
        if inv_code not in valid_inv_codes:
            errors.append({'row': r['_row_index'], 'field': 'Investigation Code', 'value': inv_code, 'error': 'Orphan Mapping: Invalid Investigation'})
        stats['diag_inv_mappings']['new'] += 1

    for r in diag_depts:
        diag_code = clean_val(r.get('diagnosis code'))
        dept_code = clean_val(r.get('department code'))
        if diag_code not in valid_diag_codes:
            errors.append({'row': r['_row_index'], 'field': 'Diagnosis Code', 'value': diag_code, 'error': 'Orphan Mapping: Invalid Diagnosis'})
        if dept_code not in valid_dept_codes:
            errors.append({'row': r['_row_index'], 'field': 'Department Code', 'value': dept_code, 'error': 'Orphan Mapping: Invalid Department'})
        stats['diag_dept_mappings']['new'] += 1

    return {'stats': stats, 'warnings': warnings, 'errors': errors[:50]}

def import_universal_master(file_obj, admin_user=None):
    wb = load_workbook(filename=file_obj, data_only=True)
    is_legacy = 'Universal Master' in wb.sheetnames and len(wb.sheetnames) == 1
    
    counts = {
        'departments_created': 0, 'departments_updated': 0,
        'diagnoses_created': 0, 'diagnoses_updated': 0,
        'investigations_created': 0, 'investigations_updated': 0,
        'parameters_created': 0, 'parameters_updated': 0,
        'age_groups_created': 0, 'age_groups_updated': 0,
        'ref_ranges_created': 0, 'ref_ranges_updated': 0,
        'mappings_created': 0, 'mappings_updated': 0,
    }

    if is_legacy:
        # Fallback to single sheet import
        ws = wb['Universal Master']
        # (Legacy implementation omitted for brevity, but would parse rows manually)
        return counts

    depts = parse_excel_sheet(wb, 'Departments')
    diags = parse_excel_sheet(wb, 'Diagnoses')
    invs = parse_excel_sheet(wb, 'Investigations')
    params = parse_excel_sheet(wb, 'Parameters')
    ages = parse_excel_sheet(wb, 'Age Groups')
    refs = parse_excel_sheet(wb, 'Reference Ranges')
    inv_params = parse_excel_sheet(wb, 'Investigation Parameters')
    diag_invs = parse_excel_sheet(wb, 'Diagnosis Investigations')
    diag_depts = parse_excel_sheet(wb, 'Diagnosis Departments')

    with transaction.atomic():
        # 1. Departments
        for r in depts:
            code = clean_val(r.get('department code'))
            name = clean_val(r.get('department name'))
            status = is_active_bool(r.get('status'))
            if code and name:
                obj, created = Department.objects.update_or_create(code=code, defaults={'name': name, 'is_active': status})
                if created: counts['departments_created'] += 1
                else: counts['departments_updated'] += 1

        # 2. Diagnoses
        for r in diags:
            code = clean_val(r.get('diagnosis code'))
            name = clean_val(r.get('diagnosis name'))
            status = is_active_bool(r.get('status'))
            if code and name:
                obj, created = Diagnosis.objects.update_or_create(code=code, defaults={'name': name, 'is_active': status})
                if created: counts['diagnoses_created'] += 1
                else: counts['diagnoses_updated'] += 1
                
        # 3. Parameters
        for r in params:
            code = clean_val(r.get('parameter code'))
            name = clean_val(r.get('parameter name'))
            dtype = clean_val(r.get('data type')) or 'NUMERIC'
            unit = clean_val(r.get('default unit'))
            status = is_active_bool(r.get('status'))
            if code and name:
                obj, created = Parameter.objects.update_or_create(code=code, defaults={'name': name, 'data_type': dtype, 'default_unit': unit, 'is_active': status})
                if created: counts['parameters_created'] += 1
                else: counts['parameters_updated'] += 1

        # 4. Investigations
        for r in invs:
            code = clean_val(r.get('investigation code'))
            name = clean_val(r.get('investigation name'))
            dept_name = clean_val(r.get('department'))
            samp_name = clean_val(r.get('sample type'))
            is_panel = clean_val(r.get('is panel')).lower() in ['yes', 'true', '1']
            status = is_active_bool(r.get('status'))
            if code and name:
                ldept, _ = LabDepartment.objects.get_or_create(name=dept_name) if dept_name else (None, False)
                samp, _ = SampleType.objects.get_or_create(name=samp_name) if samp_name else (None, False)
                obj, created = Investigation.objects.update_or_create(
                    code=code, 
                    defaults={'name': name, 'department': ldept, 'sample_type': samp, 'is_panel': is_panel, 'is_active': status}
                )
                if created: counts['investigations_created'] += 1
                else: counts['investigations_updated'] += 1
                
        # 5. Age Groups
        for r in ages:
            code = clean_val(r.get('age group code'))
            code = clean_val(r.get('age group code'))
            a_from = clean_val(r.get('age from'))
            f_unit = clean_val(r.get('age from unit')) or 'Years'
            a_to = clean_val(r.get('age to'))
            t_unit = clean_val(r.get('age to unit')) or 'Years'
            gender = clean_val(r.get('gender')) or 'All'
            status = is_active_bool(r.get('status'))
            if code and name:
                obj, created = AgeGroup.objects.update_or_create(
                    code=code,
                    defaults={
                        'label': name,
                        'min_age_value': int(a_from) if a_from.isdigit() else None,
                        'min_age_unit': f_unit,
                        'max_age_value': int(a_to) if a_to.isdigit() else None,
                        'max_age_unit': t_unit,
                        'gender': gender,
                        'is_active': status
                    }
                )
                if created: counts['age_groups_created'] += 1
                else: counts['age_groups_updated'] += 1

        # 6. Investigation Parameters
        for r in inv_params:
            inv_code = clean_val(r.get('investigation code'))
            param_code = clean_val(r.get('parameter code'))
            order = clean_val(r.get('display order'))
            status = is_active_bool(r.get('status'))
            if inv_code and param_code:
                inv = Investigation.objects.filter(code=inv_code).first()
                param = Parameter.objects.filter(code=param_code).first()
                if inv and param:
                    ip, created = InvestigationParameter.objects.update_or_create(
                        investigation=inv, parameter=param,
                        defaults={
                            'name': param.name, 'code': param.code,
                            'display_order': int(order) if order.isdigit() else 0,
                            'is_active': status
                        }
                    )
                    if created: counts['mappings_created'] += 1
                    else: counts['mappings_updated'] += 1

        # 7. Reference Ranges
        for r in refs:
            inv_code = clean_val(r.get('investigation code'))
            param_code = clean_val(r.get('parameter code'))
            age_code = clean_val(r.get('age group code'))
            gender = clean_val(r.get('gender')) or 'All'
            diag_code = clean_val(r.get('diagnosis code'))
            min_v = get_decimal(r.get('min value'))
            max_v = get_decimal(r.get('max value'))
            n_val = clean_val(r.get('normal value'))
            unit = clean_val(r.get('unit'))
            meth = clean_val(r.get('method'))
            rem = clean_val(r.get('remarks'))
            status = is_active_bool(r.get('status'))
            
            if inv_code and param_code:
                ip = InvestigationParameter.objects.filter(investigation__code=inv_code, parameter__code=param_code).first()
                ag = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                diag = Diagnosis.objects.filter(code=diag_code).first() if diag_code else None
                if ip:
                    existing = ParameterReferenceRange.objects.filter(
                        investigation_parameter=ip,
                        age_group=ag,
                        gender=gender,
                        diagnosis=diag
                    )
                    
                    defaults = {
                        'min_value': min_v, 'max_value': max_v, 'reference_text': n_val,
                        'unit': unit, 'method': meth, 'remarks': rem, 'is_active': status,
                        'range_type': 'Text' if n_val and not (min_v or max_v) else 'Numeric'
                    }
                    
                    if existing.exists():
                        # Update the first one and delete the rest to enforce uniqueness manually
                        first_obj = existing.first()
                        for k, v in defaults.items():
                            setattr(first_obj, k, v)
                        first_obj.save()
                        if existing.count() > 1:
                            existing.exclude(id=first_obj.id).delete()
                        counts['ref_ranges_updated'] += 1
                    else:
                        ParameterReferenceRange.objects.create(
                            investigation_parameter=ip,
                            age_group=ag,
                            gender=gender,
                            diagnosis=diag,
                            **defaults
                        )
                        counts['ref_ranges_created'] += 1

        # 8. Diagnosis Investigations
        for r in diag_invs:
            diag_code = clean_val(r.get('diagnosis code'))
            inv_code = clean_val(r.get('investigation code'))
            age_code = clean_val(r.get('age group code'))
            status = is_active_bool(r.get('status'))
            if diag_code and inv_code:
                diag = Diagnosis.objects.filter(code=diag_code).first()
                inv = Investigation.objects.filter(code=inv_code).first()
                ag = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                if diag and inv:
                    dim, created = DiagnosisInvestigationMap.objects.update_or_create(
                        diagnosis=diag, investigation=inv, age_group=ag,
                        defaults={'is_active': status}
                    )
                    if created: counts['mappings_created'] += 1
                    else: counts['mappings_updated'] += 1

        # 9. Diagnosis Departments
        for r in diag_depts:
            diag_code = clean_val(r.get('diagnosis code'))
            dept_code = clean_val(r.get('department code'))
            age_code = clean_val(r.get('age group code'))
            status = is_active_bool(r.get('status'))
            if diag_code and dept_code:
                diag = Diagnosis.objects.filter(code=diag_code).first()
                dept = Department.objects.filter(code=dept_code).first()
                ag = AgeGroup.objects.filter(code=age_code).first() if age_code else None
                if diag and dept:
                    # using the unique constraint fields: department, diagnosis, age_group
                    ddm, created = DiagnosisDepartmentMapping.objects.get_or_create(
                        diagnosis=diag, department=dept, age_group=ag
                    )
                    if created: counts['mappings_created'] += 1
                    else: counts['mappings_updated'] += 1

    return counts

def export_universal_master():
    wb = Workbook(write_only=False)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    
    ws_dept = wb.create_sheet('Departments')
    ws_dept.append(['Department Name', 'Department Code', 'Status'])
    for d in Department.objects.all():
        ws_dept.append([d.name, d.code, 'Active' if d.is_active else 'Inactive'])
        
    ws_diag = wb.create_sheet('Diagnoses')
    ws_diag.append(['Diagnosis Name', 'Diagnosis Code', 'Status'])
    for d in Diagnosis.objects.all():
        ws_diag.append([d.name, d.code, 'Active' if d.is_active else 'Inactive'])
        
    ws_inv = wb.create_sheet('Investigations')
    ws_inv.append(['Investigation Name', 'Investigation Code', 'Department', 'Sample Type', 'Is Panel', 'Status'])
    for i in Investigation.objects.select_related('department', 'sample_type').all():
        ws_inv.append([i.name, i.code, i.department.name if i.department else '', i.sample_type.name if i.sample_type else '', 'Yes' if i.is_panel else 'No', 'Active' if i.is_active else 'Inactive'])
        
    ws_param = wb.create_sheet('Parameters')
    ws_param.append(['Parameter Name', 'Parameter Code', 'Data Type', 'Default Unit', 'Status'])
    for p in Parameter.objects.all():
        ws_param.append([p.name, p.code, p.data_type, p.default_unit or '', 'Active' if p.is_active else 'Inactive'])
        
    ws_age = wb.create_sheet('Age Groups')
    ws_age.append(['Age Group Code', 'Age Group Name', 'Age From', 'Age From Unit', 'Age To', 'Age To Unit', 'Gender', 'Status'])
    for a in AgeGroup.objects.all():
        ws_age.append([a.code, a.label, a.min_age_value or '', a.min_age_unit or 'Years', a.max_age_value or '', a.max_age_unit or 'Years', a.gender, 'Active' if a.is_active else 'Inactive'])
        
    ws_ref = wb.create_sheet('Reference Ranges')
    ws_ref.append(['Investigation Code', 'Parameter Code', 'Age Group Code', 'Gender', 'Diagnosis Code', 'Min Value', 'Max Value', 'Normal Value', 'Unit', 'Method', 'Remarks', 'Status'])
    for r in ParameterReferenceRange.objects.select_related('investigation_parameter__investigation', 'investigation_parameter__parameter', 'age_group', 'diagnosis').all():
        ws_ref.append([
            r.investigation_parameter.investigation.code,
            r.investigation_parameter.parameter.code if r.investigation_parameter.parameter else '',
            r.age_group.code if r.age_group else '',
            r.gender,
            r.diagnosis.code if r.diagnosis else '',
            r.min_value,
            r.max_value,
            r.reference_text or '',
            r.unit or '',
            r.method or '',
            r.remarks or '',
            'Active' if r.is_active else 'Inactive'
        ])
        
    ws_ip = wb.create_sheet('Investigation Parameters')
    ws_ip.append(['Investigation Code', 'Parameter Code', 'Display Order', 'Status'])
    for ip in InvestigationParameter.objects.select_related('investigation', 'parameter').all():
        if ip.parameter:
            ws_ip.append([ip.investigation.code, ip.parameter.code, ip.display_order, 'Active' if ip.is_active else 'Inactive'])
        
    ws_di = wb.create_sheet('Diagnosis Investigations')
    ws_di.append(['Diagnosis Code', 'Investigation Code', 'Age Group', 'Status'])
    for di in DiagnosisInvestigationMap.objects.select_related('diagnosis', 'investigation', 'age_group').all():
        ws_di.append([di.diagnosis.code, di.investigation.code, di.age_group.label if di.age_group else '', 'Active' if di.is_active else 'Inactive'])
        
    ws_dd = wb.create_sheet('Diagnosis Departments')
    ws_dd.append(['Diagnosis Code', 'Department Code', 'Age Group', 'Status'])
    for dd in DiagnosisDepartmentMapping.objects.select_related('diagnosis', 'department', 'age_group').all():
        ws_dd.append([dd.diagnosis.code, dd.department.code, dd.age_group.label if dd.age_group else '', 'Active'])
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
