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


def calculate_age(date_of_birth, registration_date):
    """
    Calculate age safely:
    age = registration_year - dob_year
    subtract 1 when the birthday has not occurred yet.
    """
    if isinstance(date_of_birth, str):
        try:
            dob = datetime.datetime.strptime(date_of_birth.strip(), '%Y-%m-%d').date()
        except Exception:
            dob = pd.to_datetime(date_of_birth).date()
    else:
        dob = date_of_birth
        
    if isinstance(registration_date, str):
        try:
            reg = datetime.datetime.strptime(registration_date.strip(), '%Y-%m-%d').date()
        except Exception:
            reg = pd.to_datetime(registration_date).date()
    else:
        reg = registration_date

    age = reg.year - dob.year
    if (reg.month, reg.day) < (dob.month, dob.day):
        age -= 1
    return age


def validate_patient_row(row, existing_patient_ids, existing_op_numbers, file_patient_ids, file_op_numbers):
    def safe_str(val):
        if pd.isna(val) or str(val).strip().lower() == 'nan': return ''
        s = str(val).strip()
        if s.endswith('.0'): s = s[:-2]
        return s
        
    pat_id = safe_str(row.get('patient_id', ''))
    op_num = safe_str(row.get('op_number', ''))
    pat_type = safe_str(row.get('patient_type', '')).upper()
    if not pat_type:
        pat_type = 'O' if op_num else 'D'
    if pat_type not in ['O', 'D']:
        pat_type = 'O'
        
    reg_date_str = safe_str(row.get('registration_date', ''))
    dob_str = safe_str(row.get('date_of_birth', ''))
    fname = safe_str(row.get('first_name', ''))
    lname = safe_str(row.get('last_name', ''))
    fullname = safe_str(row.get('full_name', ''))
    if not fullname: fullname = f"{fname} {lname}".strip()
    
    gender = safe_str(row.get('gender', '')).capitalize()
    if gender not in ['Male', 'Female', 'Other']: gender = 'Male'
    
    pat_title = safe_str(row.get('patient_title', ''))
    title_map = {
        'mr': 'Mr', 'mrs': 'Mrs', 'ms': 'Ms', 'miss': 'Miss',
        'master': 'Master', 'dr': 'Dr', 'baby': 'Baby', '-': '-'
    }
    pat_title = title_map.get(pat_title.lower(), pat_title)
    
    age_raw = safe_str(row.get('age', ''))
    age_display = safe_str(row.get('age_display', ''))
    
    mobile = safe_str(row.get('mobile_number', ''))
    address = safe_str(row.get('address_line1', ''))
    city = safe_str(row.get('city', ''))
    state = safe_str(row.get('state', ''))
    country = safe_str(row.get('country', ''))
    
    g_title = safe_str(row.get('guardian_title', ''))
    g_title = title_map.get(g_title.lower(), g_title) if g_title else '-'
    g_name = safe_str(row.get('guardian_name', ''))
    g_relation = safe_str(row.get('guardian_relation', ''))
    g_phone = safe_str(row.get('guardian_phone', ''))
    
    status = 'Valid'
    errors = []
    
    if not pat_id:
        errors.append('Patient ID is required')
    elif not pat_id.isdigit():
        errors.append('Patient ID must be numeric')
    
    if pat_type == 'O':
        if not op_num:
            errors.append('OP Number is required for OP patient')
        elif not op_num.isdigit():
            errors.append('OP Number must be numeric')
    else:
        # D patient
        if op_num and not op_num.isdigit():
            errors.append('OP Number must be numeric')
    
    if not fname:
        errors.append('First name is required')
        
    reg_date = None
    dob = None
    if not reg_date_str:
        errors.append('Registration Date is required')
    else:
        try:
            reg_date = datetime.datetime.strptime(reg_date_str, '%Y-%m-%d').date()
        except Exception:
            try:
                reg_date = pd.to_datetime(reg_date_str).date()
            except Exception:
                errors.append(f'Invalid Registration Date format: {reg_date_str}')
        
    if not dob_str:
        errors.append('Date of Birth is required')
    else:
        try:
            dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d').date()
        except Exception:
            try:
                dob = pd.to_datetime(dob_str).date()
            except Exception:
                errors.append(f'Invalid DOB format: {dob_str}')
        
    calculated_age = 0
    if reg_date and dob:
        if dob > reg_date:
            errors.append('Date of Birth cannot be after Registration Date')
        else:
            calculated_age = calculate_age(dob, reg_date)
            
            # Compare with uploaded age if supplied
            if age_raw != '':
                try:
                    uploaded_age = int(float(age_raw))
                    if uploaded_age != calculated_age:
                        errors.append('Age does not match Date of Birth.')
                except ValueError:
                    errors.append('Invalid age value')
            
            # Child validation (< 18)
            if calculated_age < 18:
                if gender == 'Male' and pat_title not in ['Master', 'Baby', '-']:
                    errors.append(f'Child male title must be Master or Baby, got {pat_title}')
                elif gender == 'Female' and pat_title not in ['Miss', 'Baby', '-']:
                    errors.append(f'Child female title must be Miss or Baby, got {pat_title}')
                if not g_name:
                    errors.append('Guardian name is required for child')
                if g_relation and g_relation not in ['F/O', 'M/O', 'G/O', 'S/O', 'D/O', 'C/O', 'H/O', 'W/O', '-']:
                    errors.append(f'Invalid guardian relation: {g_relation}')
            else:
                # Adult validation (>= 18)
                if gender == 'Male' and pat_title not in ['Mr', 'Dr', '-']:
                    errors.append(f'Adult male title should be Mr or Dr, got {pat_title}')
                elif gender == 'Female' and pat_title not in ['Mrs', 'Ms', 'Miss', 'Dr', '-']:
                    errors.append(f'Adult female title should be Mrs, Ms, or Miss, got {pat_title}')
                if g_relation and g_relation not in ['H/O', 'W/O', 'F/O', 'M/O', 'S/O', 'D/O', 'C/O', 'G/O', '-']:
                    errors.append(f'Invalid guardian relation: {g_relation}')

    if not mobile:
        errors.append('Mobile Number is required')
    elif not mobile.isdigit() or len(mobile) != 10:
        errors.append('Mobile number must be exactly 10 digits.')
        
    if not address: errors.append('Address Line 1 is required')
    if not city: errors.append('City is required')
    if not state: errors.append('State is required')
    if not country: errors.append('Country is required')
    
    if pat_id in existing_patient_ids:
        status = 'Duplicate'
        errors.append(f'Patient ID {pat_id} already exists.')
    if op_num and op_num in existing_op_numbers:
        status = 'Duplicate'
        errors.append(f'OP Number {op_num} already exists.')
        
    if pat_id in file_patient_ids:
        status = 'Error'
        errors.append(f'Duplicate Patient ID in file: {pat_id}')
    if op_num and op_num in file_op_numbers:
        status = 'Error'
        errors.append(f'Duplicate OP Number in file: {op_num}')
        
    if status != 'Duplicate' and errors:
        status = 'Error'
        
    if pat_id: file_patient_ids.add(pat_id)
    if op_num: file_op_numbers.add(op_num)
    
    # Safe derived age strings for display and database
    final_age_str = str(calculated_age) if (reg_date and dob and dob <= reg_date) else (age_raw or '0')
    final_age_display = age_display if age_display else final_age_str
    
    parsed_data = {
        'patient_id': pat_id,
        'op_number': op_num,
        'patient_title': pat_title,
        'patient_type': pat_type,
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
        'age': final_age_str,
        'age_display': final_age_display,
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
            
        required_columns = ['patient_id', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'registration_date']
        
        # Normalize headers (and strip BOM)
        df.columns = [str(c).strip().lower().replace(' ', '_').lstrip('\ufeff') for c in df.columns]
        
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
        msg = str(e)
        if 'settings.STORAGES' in msg or 'storage' in msg.lower():
            user_msg = "File upload storage is not configured. Please contact the administrator."
        else:
            user_msg = f"Error parsing file: {msg}"
        return JsonResponse({'status': 'error', 'message': user_msg})


import threading

def _process_import_job(history_id, user_id):
    history = PatientImportHistory.objects.get(id=history_id)
    try:
        try:
            file_path = history.upload_file.path
        except (NotImplementedError, AttributeError, ValueError):
            file_path = None

        if file_path:
            if file_path.endswith('.csv') or (history.file_name and history.file_name.endswith('.csv')):
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
        else:
            with history.upload_file.open('rb') as f:
                if history.file_name and history.file_name.endswith('.csv'):
                    df = pd.read_csv(f, dtype=str)
                else:
                    df = pd.read_excel(f, dtype=str)
            
        df.columns = [str(c).strip().lower().replace(' ', '_').lstrip('\ufeff') for c in df.columns]
        
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
                    op_number=parsed['op_number'] if parsed['op_number'] else None,
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
                    patient_type=parsed.get('patient_type', 'O'),
                    created_source=parsed.get('patient_type', 'O')
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
