import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class PublicPrintToken(models.Model):
    """
    Secure, cryptographically random public token mapping external QR scans
    to a specific patient visit/print record without exposing sequential IDs
    or sensitive internal hospital information.
    """
    class PrintTypeChoices(models.TextChoices):
        OP = 'OP', 'Out-Patient (OP) Slip'
        REVIEW = 'REVIEW', 'Review Visit Slip'

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Secure Token"
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='public_print_tokens',
        verbose_name="Patient"
    )
    visit = models.ForeignKey(
        'patients.PatientVisit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='public_print_tokens',
        verbose_name="Specific Visit"
    )
    print_type = models.CharField(
        max_length=20,
        choices=PrintTypeChoices.choices,
        default=PrintTypeChoices.OP,
        db_index=True,
        verbose_name="Print Slip Type"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expires At")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    access_count = models.PositiveIntegerField(default=0, verbose_name="Access Count")
    last_accessed_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Accessed At")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Additional Metadata")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Public Print Token"
        verbose_name_plural = "Public Print Tokens"
        indexes = [
            models.Index(fields=['token', 'is_active']),
            models.Index(fields=['patient', 'print_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.print_type} Token for {self.patient.patient_id} ({self.token[:8]}...)"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def get_public_url(self, request=None):
        """
        Returns the canonical, patient-accessible public URL for the QR code.
        Guarantees that 127.0.0.1, localhost, or 0.0.0.0 are NEVER produced for patient QR codes.

        Priority:
        1. settings.PUBLIC_BASE_URL (e.g. 'https://csvsittech.in' or LAN IP 'http://192.168.x.x:8000')
           Loopback addresses (127.0.0.1, localhost, 0.0.0.0) are strictly rejected.
        2. If PUBLIC_BASE_URL is not set and request is provided:
           Only use request.build_absolute_uri() if request host is NOT loopback.
        3. Default production fallback: 'https://csvsittech.in'
        """
        relative_path = reverse('printing:public_print', kwargs={'token': self.token})

        configured_base = getattr(settings, 'PUBLIC_BASE_URL', '').strip().rstrip('/')
        if configured_base:
            is_loopback = any(
                bad in configured_base.lower()
                for bad in ['127.0.0.1', 'localhost', '0.0.0.0']
            )
            if not is_loopback:
                return f"{configured_base}{relative_path}"

        if request:
            try:
                host = request.get_host().lower()
                if not any(bad in host for bad in ['127.0.0.1', 'localhost', '0.0.0.0']):
                    return request.build_absolute_uri(relative_path)
            except Exception:
                pass

        return f"https://csvsittech.in{relative_path}"

    def record_access(self):
        self.access_count += 1
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed_at'])

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(32)

    @classmethod
    def get_or_create_token(cls, patient, visit=None, print_type='OP', auto_create=True):
        """
        Retrieves an existing active valid token for the patient and visit/type,
        or creates a new secure token.
        """
        qs = cls.objects.filter(
            patient=patient,
            print_type=print_type,
            is_active=True
        )
        if visit:
            qs = qs.filter(visit=visit)
        
        for existing in qs.order_by('-created_at'):
            if existing.is_valid:
                return existing

        if not auto_create:
            return None

        # Create new cryptographically secure token
        token_str = cls.generate_token()
        while cls.objects.filter(token=token_str).exists():
            token_str = cls.generate_token()

        new_token = cls.objects.create(
            token=token_str,
            patient=patient,
            visit=visit,
            print_type=print_type,
            is_active=True
        )
        return new_token


class PrintJob(models.Model):
    """
    Tracks thermal sticker print jobs sent to the configured printer abstraction layer
    (generic, PRN, TVS, network, mock).
    """
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent to Printer Spooler'
        PRINTED = 'PRINTED', 'Successfully Printed'
        FAILED = 'FAILED', 'Failed'

    job_id = models.CharField(max_length=64, unique=True, db_index=True)
    token = models.ForeignKey(
        PublicPrintToken,
        on_delete=models.CASCADE,
        related_name='print_jobs',
        null=True,
        blank=True
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='print_jobs',
        null=True,
        blank=True
    )
    print_type = models.CharField(max_length=20, default='OP')
    printer_name = models.CharField(max_length=100, default='')
    printer_type = models.CharField(max_length=50, default='generic')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    raw_payload = models.TextField(blank=True, verbose_name="PRN / Raw Payload")
    error_message = models.TextField(blank=True, verbose_name="Error Message")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Print Job"
        verbose_name_plural = "Print Jobs"

    def __str__(self):
        return f"PrintJob {self.job_id} [{self.status}] ({self.printer_type})"
