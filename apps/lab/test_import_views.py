from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import csv
import io
from apps.lab.models import Investigation, Parameter, InvestigationParameter, AgeGroup, ParameterReferenceRange

class ReferenceRangeImportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.preview_url = reverse('lab:api_referencerange_preview')
        self.import_url = reverse('lab:api_referencerange_import')
        
        self.inv = Investigation.objects.create(name="Test Inv", code="INV100")
        self.param = Parameter.objects.create(name="Test Param", code="PARAM1")
        self.ip = InvestigationParameter.objects.create(investigation=self.inv, parameter=self.param, code="PARAM1")
        
        self.ag = AgeGroup.objects.create(
            label="Adult", code="ADULT", 
            min_age_value=18, min_age_unit="YEARS", 
            max_age_value=100, max_age_unit="YEARS"
        )
        
        # We need a user to log in if the views require it. 
        # The views have LoginRequiredMixin. We need to bypass it or login.
        # Actually, let's create a superuser and log in.
        from django.contrib.auth import get_user_model
        import uuid
        User = get_user_model()
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
        return SimpleUploadedFile("test.csv", out.getvalue().encode('utf-8'), content_type="text/csv")

    def test_correct_investigation_code(self):
        file = self.generate_csv_file(
            ['investigation_code', 'parameter_code', 'age_group_code', 'gender', 'range_type', 'min_value', 'max_value'],
            [['INV100', 'PARAM1', 'ADULT', 'Male', 'NUMERIC', '10', '20']]
        )
        res = self.client.post(self.preview_url, {'file': file})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data'][0]['status'], 'Valid')

    def test_investigation_code_variants(self):
        variants = ['Investigation Code', 'investigation code', 'Investigation_Code', '  investigation_code  ']
        for var in variants:
            file = self.generate_csv_file(
                [var, 'parameter_code', 'age_group_code', 'gender', 'range_type'],
                [['INV100', 'PARAM1', 'ADULT', 'Male', 'NUMERIC']]
            )
            res = self.client.post(self.preview_url, {'file': file})
            data = res.json()
            self.assertEqual(data['status'], 'success', f"Failed for header: {var}")
            self.assertEqual(data['data'][0]['investigation_code'], 'INV100')
            self.assertEqual(data['data'][0]['status'], 'Valid')

    def test_missing_required_columns(self):
        file = self.generate_csv_file(['parameter_code', 'gender'], [['PARAM1', 'Male']])
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('investigation_code', data['message'])
        self.assertIn('age_group_code', data['message'])
        self.assertIn('range_type', data['message'])

    def test_invalid_investigation_code(self):
        file = self.generate_csv_file(
            ['investigation_code', 'parameter_code', 'age_group_code', 'gender', 'range_type'],
            [['INV999', 'PARAM1', 'ADULT', 'Male', 'NUMERIC']]
        )
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data'][0]['status'], 'Error')
        self.assertIn("code 'INV999' does not exist", data['data'][0]['error'])
        
    def test_empty_investigation_code(self):
        file = self.generate_csv_file(
            ['investigation_code', 'parameter_code', 'age_group_code', 'gender', 'range_type'],
            [['', 'PARAM1', 'ADULT', 'Male', 'NUMERIC']]
        )
        res = self.client.post(self.preview_url, {'file': file})
        data = res.json()
        self.assertEqual(data['data'][0]['status'], 'Error')
        self.assertEqual(data['data'][0]['error'], 'Investigation Code is required')

    def test_transaction_rollback_and_import(self):
        # First preview to stage the file
        file = self.generate_csv_file(
            ['investigation_code', 'parameter_code', 'age_group_code', 'gender', 'range_type', 'min_value', 'max_value'],
            [['INV100', 'PARAM1', 'ADULT', 'Female', 'NUMERIC', '5', '15']]
        )
        res_preview = self.client.post(self.preview_url, {'file': file})
        import_id = res_preview.json().get('import_id')
        
        self.assertIsNotNone(import_id)

        # Then run import with the import_id
        res = self.client.post(self.import_url, json.dumps({'import_id': import_id}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(ParameterReferenceRange.objects.filter(gender='Female').exists())
        
        # Test duplicate record update
        file2 = self.generate_csv_file(
            ['investigation_code', 'parameter_code', 'age_group_code', 'gender', 'range_type', 'min_value', 'max_value'],
            [['INV100', 'PARAM1', 'ADULT', 'Female', 'NUMERIC', '6', '15']]
        )
        res_preview2 = self.client.post(self.preview_url, {'file': file2})
        import_id2 = res_preview2.json().get('import_id')
        
        res2 = self.client.post(self.import_url, json.dumps({'import_id': import_id2}), content_type="application/json")
        self.assertEqual(res2.json()['updated'], 1)
        self.assertEqual(ParameterReferenceRange.objects.get(gender='Female').min_value, 6)
        
    def test_download_template_compatibility(self):
        res = self.client.get(reverse('lab:api_referencerange_import_template'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
