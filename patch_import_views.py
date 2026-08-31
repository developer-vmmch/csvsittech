import re

with open('apps/patients/import_views.py', 'r') as f:
    content = f.read()

# Replace everything from `def api_patient_import(request):` to the end of the file.
start_idx = content.find("def api_patient_import(request):")
if start_idx != -1:
    content = content[:start_idx]
else:
    print("Could not find api_patient_import")

new_code = """
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
"""
with open('apps/patients/import_views.py', 'w') as f:
    f.write(content + new_code)
