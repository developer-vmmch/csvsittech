import pandas as pd
import io
import json
import traceback
import math
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from .models import Patient, PatientImportHistory
from django.db import transaction
import datetime
from dateutil.relativedelta import relativedelta

class PatientImportView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    template_name = 'patients/import_patient.html'
    menu_key = 'administration'

class PatientImportHistoryView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    model = PatientImportHistory
    template_name = 'patients/import_patient_history.html'
    context_object_name = 'histories'
    menu_key = 'administration'

def api_patient_download_template(request):
    df = pd.DataFrame({
        'patient_id': ['2601010001', '2601010002'],
        'op_number': ['26100000', '26100001'],
        'patient_title': ['Mr', 'Mrs'],
        'first_name': ['John', 'Jane'],
        'last_name': ['Doe', 'Smith'],
        'full_name': ['John Doe', 'Jane Smith'],
        'gender': ['Male', 'Female'],
        'date_of_birth': ['1990-01-01', '1985-05-15'],
        'age': [36, 41],
        'age_display': ['36', '41'],
        'mobile_number': ['9876543210', '9876543211'],
        'alternate_phone': ['', ''],
        'email': ['john@example.com', 'jane@example.com'],
        'address_line1': ['123 Main St', '456 Oak St'],
        'address_line2': ['Apt 1', ''],
        'city': ['Karaikal', 'Karaikal'],
        'state': ['Puducherry', 'Puducherry'],
        'country': ['India', 'India'],
        'pincode': ['609602', '609602'],
        'blood_group': ['O+', 'A+'],
        'marital_status': ['Single', 'Married'],
        'guardian_title': ['Mr', 'Mr'],
        'guardian_name': ['Jack Doe', 'Jim Smith'],
        'guardian_relation': ['F/O', 'H/O'],
        'guardian_phone': ['9876543214', '9876543215'],
        'emergency_contact_name': ['Jim Doe', 'John Smith'],
        'emergency_contact_phone': ['9876543212', '9876543213'],
        'registration_date': ['2026-05-01', '2026-05-01']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="patient_import_template.xlsx"'
    return response


def validate_patient_row(row, existing_patient_ids, existing_op_numbers, file_patient_ids, file_op_numbers):
    def safe_str(val):
        if pd.isna(val) or str(val).strip().lower() == 'nan': return ''
        s = str(val).strip()
        if s.endswith('.0'): s = s[:-2]
        return s
        
    pat_id = safe_str(row.get('patient_id', ''))
    op_num = safe_str(row.get('op_number', ''))
    reg_date_str = safe_str(row.get('registration_date', ''))
    dob_str = safe_str(row.get('date_of_birth', ''))
    fname = safe_str(row.get('first_name', ''))
    lname = safe_str(row.get('last_name', ''))
    fullname = safe_str(row.get('full_name', ''))
    if not fullname: fullname = f"{fname} {lname}".strip()
    
    gender = safe_str(row.get('gender', '')).capitalize()
    if gender not in ['Male', 'Female', 'Other']: gender = 'Male'
    
    pat_title = safe_str(row.get('patient_title', '')).capitalize()
    
    age_raw = safe_str(row.get('age', ''))
    age_display = safe_str(row.get('age_display', ''))
    
    mobile = safe_str(row.get('mobile_number', ''))
    address = safe_str(row.get('address_line1', ''))
    city = safe_str(row.get('city', ''))
    state = safe_str(row.get('state', ''))
    country = safe_str(row.get('country', ''))
    
    g_title = safe_str(row.get('guardian_title', '')).capitalize()
    g_name = safe_str(row.get('guardian_name', ''))
    g_relation = safe_str(row.get('guardian_relation', ''))
    g_phone = safe_str(row.get('guardian_phone', ''))
    
    status = 'Valid'
    errors = []
    
    if not pat_id: errors.append('Patient ID is required')
    elif not pat_id.isdigit(): errors.append('Patient ID must be numeric')
    
    if not op_num: errors.append('OP Number is required')
    elif not op_num.isdigit(): errors.append('OP Number must be numeric')
    
    if not fname: errors.append('First name is required')
    if pat_title not in ['Mr', 'Mrs', 'Miss', 'Master', 'Dr', 'Baby']:
        pat_title = '-'
    
    reg_date = None
    dob = None
    if not reg_date_str: errors.append('Registration Date is required')
    else:
        try: reg_date = pd.to_datetime(reg_date_str).date()
        except: errors.append(f'Invalid Registration Date format: {reg_date_str}')
        
    if not dob_str: errors.append('Date of Birth is required')
    else:
        try: dob = pd.to_datetime(dob_str).date()
        except: errors.append(f'Invalid DOB format: {dob_str}')
        
    calculated_age = 0
    if reg_date and dob:
        calculated_age = relativedelta(reg_date, dob).years
    
    if calculated_age == 0:
        if age_display and age_display != 'Baby':
            errors.append('age_display must be Baby for age 0')
    else:
        if age_display and age_display != str(calculated_age):
            errors.append('age_display does not match calculated age')
            
    if g_title and g_title not in ['Mr', 'Mrs', 'Miss', '-']:
        g_title = '-'
    elif not g_title:
        g_title = '-'
        
    if not mobile: errors.append('Mobile Number is required')
    if not address: errors.append('Address Line 1 is required')
    if not city: errors.append('City is required')
    if not state: errors.append('State is required')
    if not country: errors.append('Country is required')
    
    if pat_id in existing_patient_ids:
        status = 'Duplicate'
        errors.append(f'Patient ID {pat_id} already exists.')
    if op_num in existing_op_numbers:
        status = 'Duplicate'
        errors.append(f'OP Number {op_num} already exists.')
        
    if pat_id in file_patient_ids:
        status = 'Error'
        errors.append(f'Duplicate Patient ID in file: {pat_id}')
    if op_num in file_op_numbers:
        status = 'Error'
        errors.append(f'Duplicate OP Number in file: {op_num}')
        
    if status != 'Duplicate' and errors:
        status = 'Error'
        
    if pat_id: file_patient_ids.add(pat_id)
    if op_num: file_op_numbers.add(op_num)
    
    parsed_data = {
        'patient_id': pat_id,
        'op_number': op_num,
        'patient_title': pat_title,
        'full_name': fullname,
        'first_name': fname,
        'last_name': lname,
        'registration_date': reg_date_str,
        'gender': gender,
        'mobile_number': mobile,
        'city': city,
        'state': state,
        'country': country,
        'dob': dob_str,
        'age': age_raw,
        'age_display': age_display,
        'email': safe_str(row.get('email', '')),
        'alternate_phone': safe_str(row.get('alternate_phone', '')),
        'address_line1': address,
        'address_line2': safe_str(row.get('address_line2', '')),
        'pincode': safe_str(row.get('pincode', '')),
        'blood_group': safe_str(row.get('blood_group', '')),
        'marital_status': safe_str(row.get('marital_status', '')),
        'guardian_title': g_title,
        'guardian_name': g_name,
        'guardian_relation': g_relation,
        'guardian_phone': g_phone,
        'emergency_contact_name': safe_str(row.get('emergency_contact_name', '')),
        'emergency_contact_phone': safe_str(row.get('emergency_contact_phone', '')),
        'status': status,
        'error': " | ".join(errors)
    }
    return parsed_data, status, errors

def api_patient_preview(request):
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
            
        required_columns = ['patient_id', 'op_number', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'registration_date']
        
        # Normalize headers
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        
        missing_columns = [req for req in required_columns if req not in df.columns]
        if missing_columns:
            msg = 'Missing required columns:\n- ' + '\n- '.join(missing_columns)
            return JsonResponse({'status': 'error', 'message': msg})
            
        # Create staging history record and save file
        history = PatientImportHistory.objects.create(
            file_name=filename,
            uploaded_by=request.user if request.user.is_authenticated else None,
            total_records=len(df),
            status='Staged',
            upload_file=file
        )
            
        preview_data = []
        file_patient_ids = set()
        file_op_numbers = set()
        
        existing_patient_ids = set(Patient.objects.values_list('patient_id', flat=True))
        existing_op_numbers = set(Patient.objects.values_list('op_number', flat=True))
        
        valid_rows = 0
        invalid_rows = 0
        duplicate_rows = 0
        
        for index, row in df.iterrows():
            row_num = index + 2
            parsed, status, errors = validate_patient_row(row, existing_patient_ids, existing_op_numbers, file_patient_ids, file_op_numbers)
            
            if status == 'Valid': valid_rows += 1
            elif status == 'Duplicate': duplicate_rows += 1
            else: invalid_rows += 1
            
            # Return only first 100 rows to the frontend for preview to save memory
            if index < 100:
                parsed['row_num'] = row_num
                preview_data.append(parsed)
            
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
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error parsing file: {str(e)}'})


import threading

def _process_import_job(history_id, user_id):
    history = PatientImportHistory.objects.get(id=history_id)
    try:
        file_path = history.upload_file.path
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
            
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        
        imported = 0
        failed = 0
        skipped = 0
        batch_size = 500
        batch_patients = []
        
        file_patient_ids = set()
        file_op_numbers = set()
        
        # Preload to avoid row-by-row queries
        existing_patient_ids = set(Patient.objects.values_list('patient_id', flat=True))
        existing_op_numbers = set(Patient.objects.values_list('op_number', flat=True))
        
        history.status = 'Importing'
        history.total_records = len(df)
        history.save()
        
        def save_batch(batch):
            nonlocal imported
            if not batch: return
            with transaction.atomic():
                Patient.objects.bulk_create(batch)
            imported += len(batch)
            history.imported = imported
            history.failed = failed
            history.skipped = skipped
            # Close db connection for this thread if necessary, but Django manages it mostly well if we don't leak it.
            history.save()

        for index, row in df.iterrows():
            parsed, status, errors = validate_patient_row(row, existing_patient_ids, existing_op_numbers, file_patient_ids, file_op_numbers)
            
            if status == 'Error':
                failed += 1
            elif status == 'Duplicate':
                skipped += 1
            else:
                reg_date_str = parsed.get('registration_date')
                reg_date = pd.to_datetime(reg_date_str).date() if reg_date_str else None
                dob_str = parsed.get('dob')
                dob = pd.to_datetime(dob_str).date() if dob_str else None
                
                age_years = 0
                if parsed.get('age') and str(parsed.get('age')).isdigit():
                    age_years = int(parsed.get('age'))
                
                patient = Patient(
                    patient_id=parsed['patient_id'],
                    op_number=parsed['op_number'],
                    registration_date=reg_date,
                    title=parsed.get('patient_title', '-'),
                    name=parsed['full_name'],
                    gender=parsed['gender'],
                    dob=dob,
                    age_years=age_years,
                    mobile_no=parsed['mobile_number'],
                    alternate_phone=parsed.get('alternate_phone', ''),
                    email=parsed.get('email', ''),
                    street=parsed.get('address_line1', ''),
                    village_area=parsed.get('address_line2', ''),
                    city=parsed.get('city', ''),
                    state=parsed.get('state', ''),
                    country=parsed.get('country', ''),
                    pincode=parsed.get('pincode', ''),
                    blood_group=parsed.get('blood_group', ''),
                    marital_status=parsed.get('marital_status', ''),
                    guardian_title=parsed.get('guardian_title', '-'),
                    guardian_name=parsed.get('guardian_name', ''),
                    guardian_relationship=parsed.get('guardian_relation', '-'),
                    guardian_phone=parsed.get('guardian_phone', ''),
                    emergency_contact_phone=parsed.get('emergency_contact_phone', ''),
                    created_by_id=user_id,
                    patient_type='O',
                    created_source='O'
                )
                batch_patients.append(patient)
            
            # Periodically commit and update progress
            if len(batch_patients) >= batch_size:
                save_batch(batch_patients)
                batch_patients = []
                
        # Final batch
        if batch_patients:
            save_batch(batch_patients)
            
        # Final sync
        history.imported = imported
        history.failed = failed
        history.skipped = skipped
        history.status = 'Completed'
        history.save()
        
    except Exception as e:
        traceback.print_exc()
        history.status = 'Failed'
        history.save()
    finally:
        from django.db import connection
        connection.close()


def api_patient_import(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
        
    try:
        data = json.loads(request.body)
        import_id = data.get('import_id')
        
        if not import_id:
            return JsonResponse({'status': 'error', 'message': 'Missing import_id'})
            
        history = PatientImportHistory.objects.get(id=import_id)
        if history.status != 'Staged':
            return JsonResponse({'status': 'error', 'message': 'This import is already processed.'})
            
        # Start async processing
        t = threading.Thread(target=_process_import_job, args=(import_id, request.user.id if request.user.is_authenticated else None))
        t.daemon = True
        t.start()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Import job started in background'
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)})


def api_patient_import_status(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    try:
        import_id = request.GET.get('import_id')
        history = PatientImportHistory.objects.get(id=import_id)
        return JsonResponse({
            'status': 'success',
            'job_status': history.status,
            'total_records': history.total_records,
            'imported': history.imported,
            'failed': history.failed,
            'skipped': history.skipped
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
