from django.test import TransactionTestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import csv
import io
import time
from apps.patients.models import Patient, PatientImportHistory
from django.contrib.auth import get_user_model

class PatientImportTests(TransactionTestCase):
    def setUp(self):
        self.client = Client()
        self.preview_url = reverse('patients:api_import_preview')
        self.import_url = reverse('patients:api_import_process')
        
        User = get_user_model()
        import uuid
        username = str(uuid.uuid4())
        self.user = User.objects.create_user(username=username, email=f"{username}@example.com", password='pass')
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.login(username=username, password='pass')

    def generate_csv_file(self, headers, rows):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return SimpleUploadedFile("patients.csv", out.getvalue().encode('utf-8'), content_type="text/csv")

    def test_preview_valid_patient(self):
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age']
        row = ['2601010001', '26100000', 'Mr', '2026-05-01', 'John', 'Male', '1990-01-01', '9876543210', '123 St', 'Karaikal', 'Puducherry', 'India', '36', '36']
        file = self.generate_csv_file(headers, [row])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['valid_rows'], 1)
        self.assertEqual(data['data'][0]['status'], 'Valid')

    def test_missing_required_columns(self):
        file = self.generate_csv_file(
            ['first_name', 'gender'],
            [['John', 'Male']]
        )
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('patient_id', data['message'])

    def test_duplicate_patient_in_db(self):
        Patient.objects.create(patient_id='2601010001', name='Existing')
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age']
        row = ['2601010001', '26100000', 'Mr', '2026-05-01', 'John', 'Male', '1990-01-01', '9876543210', '123 St', 'Karaikal', 'Puducherry', 'India', '36', '36']
        file = self.generate_csv_file(headers, [row])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['data'][0]['status'], 'Duplicate')
        self.assertIn('Patient ID 2601010001 already exists', data['data'][0]['error'])

    def test_duplicate_in_file(self):
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age']
        row1 = ['2601010001', '26100000', 'Mr', '2026-05-01', 'John', 'Male', '1990-01-01', '9876543210', '123 St', 'Karaikal', 'Puducherry', 'India', '36', '36']
        row2 = ['2601010001', '26100000', 'Mr', '2026-05-01', 'John2', 'Male', '1990-01-01', '9876543211', '123 St', 'Karaikal', 'Puducherry', 'India', '36', '36']
        file = self.generate_csv_file(headers, [row1, row2])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['data'][1]['status'], 'Error')
        self.assertIn('Duplicate Patient ID in file: 2601010001', data['data'][1]['error'])

    def test_transaction_rollback_and_import(self):
        # First preview to stage the file
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age']
        row = ['2601010005', '26100005', 'Mr', '2026-05-01', 'John', 'Male', '1990-01-01', '9876543210', '123 St', 'Karaikal', 'Puducherry', 'India', '36', '36']
        file = self.generate_csv_file(headers, [row])
        res_preview = self.client.post(self.preview_url, {'file': file})
        import_id = res_preview.json().get('import_id')
        
        self.assertIsNotNone(import_id)

        # Then run import with the import_id
        res = self.client.post(self.import_url, json.dumps({'import_id': import_id}), content_type="application/json")
        
        self.assertEqual(res.status_code, 200)
        
        # Wait for thread to complete
        for _ in range(30):
            history = PatientImportHistory.objects.get(id=import_id)
            if history.status in ['Completed', 'Failed']:
                break
            time.sleep(0.1)
            
        self.assertTrue(Patient.objects.filter(patient_id='2601010005').exists())
        self.assertEqual(history.status, 'Completed')

    def test_d_patient_without_op_number(self):
        headers = ['patient_id', 'op_number', 'patient_title', 'patient_type', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age', 'guardian_name', 'guardian_relation']
        row = ['200101151', '', 'Mr', 'D', '2020-01-01', 'Prakash', 'Male', '1963-07-28', '6000005587', '737 West St', 'Nagapattinam', 'Tamil Nadu', 'India', '56', '56', 'Anjali', 'W/O']
        file = self.generate_csv_file(headers, [row])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['valid_rows'], 1)
        self.assertEqual(data['data'][0]['status'], 'Valid')
        self.assertEqual(data['data'][0]['age'], '56')
        self.assertEqual(data['data'][0]['patient_type'], 'D')

    def test_age_mismatch_error(self):
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age']
        row = ['2601010008', '26100008', 'Mr', '2026-05-01', 'John', 'Male', '1990-01-01', '9876543210', '123 St', 'Karaikal', 'Puducherry', 'India', '40', '40']
        file = self.generate_csv_file(headers, [row])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['invalid_rows'], 1)
        self.assertEqual(data['data'][0]['status'], 'Error')
        self.assertIn('Age does not match Date of Birth.', data['data'][0]['error'])

    def test_child_validation_rules(self):
        headers = ['patient_id', 'op_number', 'patient_title', 'registration_date', 'first_name', 'gender', 'date_of_birth', 'mobile_number', 'address_line1', 'city', 'state', 'country', 'age_display', 'age', 'guardian_name', 'guardian_relation']
        # Valid child
        row1 = ['200101021', '200101021', 'Master', '2020-01-01', 'Rithvik', 'Male', '2019-11-05', '6000000777', '929 East St', 'Mayiladuthurai', 'Tamil Nadu', 'India', '0', '0', 'Mohan', 'F/O']
        # Invalid child title (Mr for a 5-year-old)
        row2 = ['200101022', '200101022', 'Mr', '2020-01-01', 'ChildMr', 'Male', '2015-01-01', '6000000778', '929 East St', 'Mayiladuthurai', 'Tamil Nadu', 'India', '5', '5', 'Mohan', 'F/O']
        file = self.generate_csv_file(headers, [row1, row2])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data'][0]['status'], 'Valid')
        self.assertEqual(data['data'][0]['age'], '0')
        self.assertEqual(data['data'][1]['status'], 'Error')
        self.assertIn('Child male title must be Master or Baby', data['data'][1]['error'])

