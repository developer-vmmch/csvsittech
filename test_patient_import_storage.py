import os
import sys
import io
import time
import django
import pandas as pd
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.patients.models import Patient, PatientImportHistory
from django.core.files.storage import default_storage

def run_tests():
    print("==================================================")
    print("TESTING PATIENT IMPORT STORAGE CONFIGURATION")
    print("==================================================")

    # 1. Verify default_storage backend configuration
    print("\n--- Test 1: settings.STORAGES['default'] and default_storage ---")
    from django.conf import settings
    assert 'default' in settings.STORAGES, "settings.STORAGES missing 'default'!"
    assert settings.STORAGES['default']['BACKEND'] == 'django.core.files.storage.FileSystemStorage'
    print(f"settings.STORAGES['default']: {settings.STORAGES['default']}")
    print(f"default_storage: {default_storage}")
    print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print("Test 1 PASSED: default_storage is properly configured as FileSystemStorage.")

    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    client = Client()
    client.force_login(admin)

    # 2. Test GET /patients/import/ page
    print("\n--- Test 2: GET /patients/import/ page ---")
    resp = client.get('/patients/import/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("Test 2 PASSED: /patients/import/ loaded with HTTP 200.")

    # 3. Test Upload & Preview with .xlsx
    print("\n--- Test 3: Upload and Preview with Excel (.xlsx) ---")
    df_xlsx = pd.DataFrame({
        'patient_id': ['9901010001', '9901010002'],
        'op_number': ['99100001', '99100002'],
        'patient_title': ['Mr', 'Mrs'],
        'first_name': ['John', 'Jane'],
        'last_name': ['Doe', 'Smith'],
        'full_name': ['John Doe', 'Jane Smith'],
        'gender': ['Male', 'Female'],
        'date_of_birth': ['1990-01-01', '1985-01-15'],
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
    buf_xlsx = io.BytesIO()
    with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
        df_xlsx.to_excel(writer, index=False, sheet_name='Patients')
    buf_xlsx.seek(0)

    upload_xlsx = SimpleUploadedFile(
        'test_patients.xlsx',
        buf_xlsx.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    resp_preview_xlsx = client.post('/patients/api/import/preview/', {'file': upload_xlsx})
    assert resp_preview_xlsx.status_code == 200, f"Preview returned {resp_preview_xlsx.status_code}"
    data_xlsx = resp_preview_xlsx.json()
    print("Preview XLSX response:", data_xlsx)
    assert data_xlsx['status'] == 'success', f"Preview failed: {data_xlsx.get('message')}"
    assert data_xlsx['total_rows'] == 2
    assert data_xlsx['valid_rows'] == 2
    import_id_xlsx = data_xlsx['import_id']
    
    # Verify file saved to storage
    history_xlsx = PatientImportHistory.objects.get(id=import_id_xlsx)
    assert history_xlsx.upload_file, "upload_file is empty on history!"
    assert default_storage.exists(history_xlsx.upload_file.name), f"File does not exist in storage: {history_xlsx.upload_file.name}"
    print(f"File stored at: {history_xlsx.upload_file.name} (exists={default_storage.exists(history_xlsx.upload_file.name)})")
    print("Test 3 PASSED: Excel upload and preview staged successfully in storage.")

    # 4. Test Import Execution for the .xlsx file
    print("\n--- Test 4: Execute Import for Excel (.xlsx) ---")
    resp_imp_xlsx = client.post(
        '/patients/api/import/process/',
        data={'import_id': import_id_xlsx},
        content_type='application/json'
    )
    assert resp_imp_xlsx.status_code == 200
    print("Import XLSX API response:", resp_imp_xlsx.json())
    
    # Wait for thread to complete
    for _ in range(30):
        history_xlsx.refresh_from_db()
        if history_xlsx.status in ['Completed', 'Failed']:
            break
        time.sleep(0.2)
    
    print(f"History status: {history_xlsx.status}, imported={history_xlsx.imported}, failed={history_xlsx.failed}")
    assert history_xlsx.status == 'Completed', f"Import failed with status {history_xlsx.status}"
    assert history_xlsx.imported == 2, f"Expected 2 imported, got {history_xlsx.imported}"
    
    p1 = Patient.objects.filter(patient_id='9901010001').first()
    p2 = Patient.objects.filter(patient_id='9901010002').first()
    assert p1 is not None and p2 is not None, "Patients were not created in DB!"
    print(f"Created patients verified in DB: {p1.patient_id} ({p1.name}), {p2.patient_id} ({p2.name})")
    print("Test 4 PASSED: Patient records imported successfully into database.")

    # 5. Test Upload & Preview with .csv
    print("\n--- Test 5: Upload and Preview with CSV (.csv) ---")
    df_csv = pd.DataFrame({
        'patient_id': ['9901010003', '9901010004'],
        'op_number': ['99100003', '99100004'],
        'patient_title': ['Mr', 'Mrs'],
        'first_name': ['Robert', 'Emily'],
        'last_name': ['Taylor', 'Brown'],
        'full_name': ['Robert Taylor', 'Emily Brown'],
        'gender': ['Male', 'Female'],
        'date_of_birth': ['1992-03-10', '1988-01-22'],
        'age': [34, 38],
        'age_display': ['34', '38'],
        'mobile_number': ['9876543220', '9876543221'],
        'alternate_phone': ['', ''],
        'email': ['robert@example.com', 'emily@example.com'],
        'address_line1': ['789 Pine St', '101 Maple St'],
        'address_line2': ['', ''],
        'city': ['Karaikal', 'Karaikal'],
        'state': ['Puducherry', 'Puducherry'],
        'country': ['India', 'India'],
        'pincode': ['609602', '609602'],
        'blood_group': ['B+', 'AB+'],
        'marital_status': ['Married', 'Single'],
        'guardian_title': ['Mr', 'Mr'],
        'guardian_name': ['George Taylor', 'David Brown'],
        'guardian_relation': ['F/O', 'F/O'],
        'guardian_phone': ['9876543224', '9876543225'],
        'emergency_contact_name': ['George Taylor', 'David Brown'],
        'emergency_contact_phone': ['9876543222', '9876543223'],
        'registration_date': ['2026-05-02', '2026-05-02']
    })
    csv_bytes = df_csv.to_csv(index=False).encode('utf-8')
    upload_csv = SimpleUploadedFile(
        'test_patients.csv',
        csv_bytes,
        content_type='text/csv'
    )

    resp_preview_csv = client.post('/patients/api/import/preview/', {'file': upload_csv})
    assert resp_preview_csv.status_code == 200, f"Preview CSV returned {resp_preview_csv.status_code}"
    data_csv = resp_preview_csv.json()
    print("Preview CSV response:", data_csv)
    assert data_csv['status'] == 'success', f"Preview failed: {data_csv.get('message')}"
    assert data_csv['total_rows'] == 2
    assert data_csv['valid_rows'] == 2
    import_id_csv = data_csv['import_id']

    # Execute CSV import
    resp_imp_csv = client.post(
        '/patients/api/import/process/',
        data={'import_id': import_id_csv},
        content_type='application/json'
    )
    assert resp_imp_csv.status_code == 200
    
    history_csv = PatientImportHistory.objects.get(id=import_id_csv)
    for _ in range(30):
        history_csv.refresh_from_db()
        if history_csv.status in ['Completed', 'Failed']:
            break
        time.sleep(0.2)
        
    print(f"History status: {history_csv.status}, imported={history_csv.imported}, failed={history_csv.failed}")
    assert history_csv.status == 'Completed'
    assert history_csv.imported == 2
    print("Test 5 PASSED: CSV upload, preview, and import all succeeded.")

    # 6. Test with large actual patient dataset
    print("\n--- Test 6: Preview with existing large patient dataset ---")
    large_file = '/home/Loosifer/Documents/VMMCHErp/VMMCerp/media/patient_imports/patients.csv'
    if os.path.exists(large_file):
        with open(large_file, 'rb') as f:
            upload_large = SimpleUploadedFile('patients.csv', f.read(), content_type='text/csv')
        resp_large = client.post('/patients/api/import/preview/', {'file': upload_large})
        data_large = resp_large.json()
        print(f"Large file preview status: {data_large.get('status')}, total_rows: {data_large.get('total_rows')}, valid: {data_large.get('valid_rows')}")
        assert data_large.get('status') == 'success'
        print("Test 6 PASSED: Large actual patient file uploaded and validated successfully.")

    # Clean up test patients
    Patient.objects.filter(patient_id__in=['9901010001', '9901010002', '9901010003', '9901010004']).delete()
    print("\nCleanup completed.")
    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
