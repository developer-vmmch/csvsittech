from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import io

from apps.patients.models import Patient, PatientVisit, Department
from apps.printing.models import PublicPrintToken, PrintJob
from apps.printing.services.sticker_renderer import StickerRenderer
from apps.printing.services.printer_service import StickerPrintService
from apps.printing.services.pdf_generator import PatientPdfGenerator
from apps.printing.adapters.mock_printer import MockPrinterAdapter


class PrintingSystemTests(TestCase):
    def setUp(self):
        # Create test department
        self.dept = Department.objects.create(
            name="GENERAL MEDICINE",
            code="GM",
            is_active=True
        )

        # Create test patient matching reference specs
        self.patient = Patient.objects.create(
            patient_id="26148635",
            op_number="26000001",
            title="Mr",
            name="MARTIN LOURDURAJ",
            gender="Male",
            age_years=15,
            guardian_name="MARTIN",
            department="GENERAL MEDICINE",
            department_obj=self.dept,
            created_source="O",
            patient_type="O"
        )

        # Create test review visit
        self.visit = PatientVisit.objects.create(
            patient=self.patient,
            visit_no=2,
            visit_type="OP",
            category="RE_CONSULTATION",
            department="GENERAL MEDICINE",
            department_obj=self.dept
        )

        self.client = Client()

    def test_01_token_generation_security(self):
        """Tokens must be cryptographically random and not expose sequential database IDs"""
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        self.assertIsNotNone(token.token)
        self.assertGreaterEqual(len(token.token), 32)
        # Verify database PK is NOT in the token string
        self.assertNotIn(f"id={self.patient.id}", token.token)
        self.assertNotIn(str(self.patient.id), token.token[:4])
        self.assertTrue(token.is_valid)

    def test_02_separate_op_and_review_tokens(self):
        """OP and Review prints must generate distinct tokens with their respective print types"""
        op_token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        review_token = PublicPrintToken.get_or_create_token(self.patient, visit=self.visit, print_type='REVIEW')

        self.assertNotEqual(op_token.token, review_token.token)
        self.assertEqual(op_token.print_type, 'OP')
        self.assertEqual(review_token.print_type, 'REVIEW')

    def test_03_public_print_view_mobile_html_response(self):
        """
        Unauthenticated mobile patients scanning QR receive clean HTML preview (NOT raw PDF).
        Must include all required hospital & patient fields, sticker preview, action buttons.
        """
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        url = reverse('printing:public_print', kwargs={'token': token.token})

        # Test with Android / Mobile User Agent
        response = self.client.get(url, HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari/537.36")
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])

        content = response.content.decode('utf-8')

        # 1. Hospital Header
        self.assertIn("Vinayaka Missions Medical College &amp; Hospital", content)
        self.assertIn("vmmc_logo.png", content)
        self.assertIn("nabh_logo.png", content)
        self.assertIn("HFRID: IN3410000736", content)

        # 2. Visit Banner
        self.assertIn("OUT PATIENT - NEW", content)

        # 3. Patient Details
        self.assertIn("MARTIN LOURDURAJ", content)
        self.assertIn("26148635", content)
        self.assertIn("26000001", content)
        self.assertIn("GENERAL MEDICINE", content)
        self.assertIn("15 Years", content)
        self.assertIn("Male", content)
        self.assertIn("MARTIN", content)

        # 4. Sticker Preview
        self.assertIn("Sticker Preview", content)
        self.assertIn("VMMC KARAIKAL", content)
        self.assertIn("60mm &times; 30mm", content)

        # 5. Action Buttons
        self.assertIn("PRINT STICKER", content)
        self.assertIn("DOWNLOAD PDF", content)
        pdf_url = reverse('printing:public_pdf', kwargs={'token': token.token})
        self.assertIn(pdf_url, content)

        # 6. Ensure NO internal HMS UI or dashboard elements leak
        self.assertNotIn("sidebar-wrapper", content)
        self.assertNotIn("navbar-nav", content)
        self.assertNotIn("Register Another Patient", content)
        self.assertNotIn("Patient Directory", content)
        self.assertNotIn("dashboard", content.lower())

    def test_04_review_public_view_displays_review(self):
        """Review tokens must render the review document representation"""
        review_token = PublicPrintToken.get_or_create_token(self.patient, visit=self.visit, print_type='REVIEW')
        url = reverse('printing:public_print', kwargs={'token': review_token.token})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("OUT PATIENT - REVIEW", content)
        self.assertIn("REVIEW", content)

    def test_05_direct_pdf_download_endpoint(self):
        """Public PDF endpoint returns valid application/pdf binary"""
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        url = reverse('printing:public_pdf', kwargs={'token': token.token})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        # PDF binary starts with %PDF-
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreater(len(response.content), 1000)

    def test_06_invalid_and_expired_tokens(self):
        """Invalid or expired tokens must safely return 404 without leaking internal info"""
        # Invalid token
        url_fake = reverse('printing:public_print', kwargs={'token': 'non_existent_random_token_12345'})
        res_fake = self.client.get(url_fake)
        self.assertEqual(res_fake.status_code, 404)
        self.assertIn("Document Unavailable", res_fake.content.decode('utf-8'))

        # Expired token
        expired_token = PublicPrintToken.objects.create(
            token="expired_token_test_1234567890abcdef",
            patient=self.patient,
            print_type='OP',
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True
        )
        url_exp = reverse('printing:public_print', kwargs={'token': expired_token.token})
        res_exp = self.client.get(url_exp)
        self.assertEqual(res_exp.status_code, 404)

        # Deactivated token
        deactivated_token = PublicPrintToken.objects.create(
            token="deactivated_token_test_1234567890abc",
            patient=self.patient,
            print_type='OP',
            is_active=False
        )
        url_deact = reverse('printing:public_print', kwargs={'token': deactivated_token.token})
        res_deact = self.client.get(url_deact)
        self.assertEqual(res_deact.status_code, 404)

    def test_07_sticker_renderer_op_and_review(self):
        """StickerRenderer generates HTML and TSPL PRN payloads for both OP and REVIEW"""
        renderer = StickerRenderer(width="60mm", height="30mm")
        op_token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        rev_token = PublicPrintToken.get_or_create_token(self.patient, visit=self.visit, print_type='REVIEW')

        op_data = renderer.extract_sticker_data(op_token)
        op_html = renderer.render_html(op_data)
        op_prn = renderer.render_prn(op_data)

        self.assertIn("VMMC KARAIKAL", op_html)
        self.assertIn("OP", op_html)
        self.assertIn("MARTIN LOURDURAJ", op_html)
        self.assertIn("SIZE 60 mm, 30 mm", op_prn)
        self.assertIn("VMMC KARAIKAL  OP", op_prn)
        self.assertIn("PRINT 1", op_prn)

        rev_data = renderer.extract_sticker_data(rev_token)
        rev_html = renderer.render_html(rev_data)
        rev_prn = renderer.render_prn(rev_data)

        self.assertIn("REVIEW", rev_html)
        self.assertIn("VMMC KARAIKAL  REVIEW", rev_prn)

    def test_08_sticker_print_service_mock_adapter(self):
        """StickerPrintService creates PrintJob and dispatches to configured adapter"""
        MockPrinterAdapter.clear()
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        
        service = StickerPrintService(printer_type='mock')
        res = service.print_sticker(token)

        self.assertTrue(res['success'])
        self.assertEqual(res['status'], 'PRINTED')
        self.assertEqual(len(MockPrinterAdapter.printed_jobs), 1)

        # Check PrintJob database record
        job = PrintJob.objects.filter(job_id=res['job_id']).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.status, PrintJob.StatusChoices.PRINTED)
        self.assertEqual(job.patient, self.patient)

    def test_09_workstation_print_trigger_api(self):
        """Dedicated scanner API triggers sticker print without requiring login"""
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        url = reverse('printing:public_print_trigger', kwargs={'token': token.token})

        response = self.client.post(url, content_type='application/json', data={})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn(data['status'], ['PRINTED', 'SENT'])
        self.assertEqual(data['uhid'], '26148635')
        self.assertEqual(data['patient_name'], 'MARTIN LOURDURAJ')

    def test_10_pdf_generator_creates_valid_pdf_with_nabh(self):
        """PatientPdfGenerator generates PDF including patient details and NABH logo"""
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        generator = PatientPdfGenerator(token)
        pdf_bytes = generator.generate_pdf()

        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_11_patient_print_view_integrates_secure_qr(self):
        """Internal PatientPrintView creates token and renders public QR reference with caption"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_superuser(
            username='admin_print_test',
            password='Password123!',
            email='admin@vmmckl.edu.in'
        )
        self.client.force_login(user)

        # 1. OP Print
        op_url = reverse('patients:print', kwargs={'pk': self.patient.pk})
        response = self.client.get(op_url)
        self.assertEqual(response.status_code, 200)

        # Token created and passed to context
        self.assertIn('print_token', response.context)
        self.assertEqual(response.context['print_type'], 'OP')
        self.assertIn('public_print_url', response.context)

        content = response.content.decode('utf-8')
        self.assertIn("SCAN FOR STICKER / PRINT VIEW", content)
        self.assertIn(response.context['print_token'].token, content)

        # 2. Review Print via ?type=review
        rev_url = f"{op_url}?type=review"
        rev_response = self.client.get(rev_url)
        self.assertEqual(rev_response.status_code, 200)
        self.assertEqual(rev_response.context['print_type'], 'REVIEW')
        self.assertEqual(rev_response.context['print_token'].print_type, 'REVIEW')

    @override_settings(PUBLIC_BASE_URL='https://csvsittech.in')
    def test_12_qr_url_never_contains_localhost_or_loopback(self):
        """
        CRITICAL TEST:
        Production QR URLs MUST ALWAYS use https://csvsittech.in/public/print/<token>/
        and MUST NEVER contain 127.0.0.1, localhost, or 0.0.0.0 even when viewed on dev server.
        """
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')

        # 1. Without request
        url_no_req = token.get_public_url()
        self.assertTrue(url_no_req.startswith("https://csvsittech.in/public/print/"))
        self.assertNotIn("127.0.0.1", url_no_req)
        self.assertNotIn("localhost", url_no_req)
        self.assertNotIn("0.0.0.0", url_no_req)

        # 2. Even when a simulated request with 127.0.0.1 is passed
        from django.test.client import RequestFactory
        factory = RequestFactory()
        req_local = factory.get('/patients/1/print/', HTTP_HOST='127.0.0.1:8000')

        url_with_req = token.get_public_url(req_local)
        self.assertTrue(url_with_req.startswith("https://csvsittech.in/public/print/"))
        self.assertNotIn("127.0.0.1", url_with_req)
        self.assertNotIn("localhost", url_with_req)
        self.assertNotIn("0.0.0.0", url_with_req)

        # 3. Check inside rendered sticker payload
        renderer = StickerRenderer()
        sticker_data = renderer.extract_sticker_data(token)
        self.assertTrue(sticker_data['qr_url'].startswith("https://csvsittech.in/public/print/"))
        self.assertNotIn("127.0.0.1", sticker_data['qr_url'])
        self.assertNotIn("localhost", sticker_data['qr_url'])

        prn_content = renderer.render_prn(sticker_data)
        self.assertIn("https://csvsittech.in/public/print/", prn_content)
        self.assertNotIn("127.0.0.1", prn_content)

    @override_settings(PUBLIC_BASE_URL='http://192.168.1.100:8000')
    def test_13_lan_ip_configurable_for_local_mobile_testing(self):
        """Allows LAN IP (e.g. 192.168.1.100:8000) for testing phone against dev PC on Wi-Fi"""
        token = PublicPrintToken.get_or_create_token(self.patient, print_type='OP')
        url_lan = token.get_public_url()
        self.assertTrue(url_lan.startswith("http://192.168.1.100:8000/public/print/"))
        self.assertNotIn("127.0.0.1", url_lan)
        self.assertNotIn("localhost", url_lan)
