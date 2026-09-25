from django.db import models
from django.conf import settings
from django.utils import timezone

class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    created_at and updated_at fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CRMEnquiry(TimeStampedModel):
    class CategoryChoices(models.TextChoices):
        GENERAL = 'General Enquiry', 'General Enquiry'
        APPOINTMENT = 'Appointment', 'Appointment'
        DOCTOR = 'Doctor Enquiry', 'Doctor Enquiry'
        DEPARTMENT = 'Department Enquiry', 'Department Enquiry'
        ADMISSION = 'Admission Enquiry', 'Admission Enquiry'
        BILLING = 'Billing Enquiry', 'Billing Enquiry'
        LABORATORY = 'Laboratory Enquiry', 'Laboratory Enquiry'
        PHARMACY = 'Pharmacy Enquiry', 'Pharmacy Enquiry'
        INSURANCE = 'Insurance', 'Insurance'
        COMPLAINT = 'Complaint', 'Complaint'
        FEEDBACK = 'Feedback', 'Feedback'
        OTHER = 'Other', 'Other'

    class PriorityChoices(models.TextChoices):
        LOW = 'Low', 'Low'
        NORMAL = 'Normal', 'Normal'
        HIGH = 'High', 'High'
        URGENT = 'Urgent', 'Urgent'

    class StatusChoices(models.TextChoices):
        OPEN = 'Open', 'Open'
        PENDING = 'Pending', 'Pending'
        FOLLOW_UP = 'Follow-up', 'Follow-up'
        COMPLETED = 'Completed', 'Completed'
        CLOSED = 'Closed', 'Closed'
        CANCELLED = 'Cancelled', 'Cancelled'

    class CallerSourceChoices(models.TextChoices):
        PHONE = 'Phone Call', 'Phone Call'
        WALKIN = 'Walk-in', 'Walk-in'
        WEBSITE = 'Website Enquiry', 'Website Enquiry'
        EMAIL = 'Email', 'Email'
        REFERRAL = 'Referral', 'Referral'
        OTHER = 'Other', 'Other'

    # Left Side Fields
    caller_mobile = models.CharField(max_length=20, verbose_name="Caller Mobile No")
    caller_name = models.CharField(max_length=150, verbose_name="Caller Name")
    street = models.CharField(max_length=200, blank=True, null=True, verbose_name="Street")
    area_village = models.CharField(max_length=150, blank=True, null=True, verbose_name="Area / Village")
    city = models.CharField(max_length=100, default="Karaikal", verbose_name="City")
    pincode = models.CharField(max_length=20, blank=True, null=True, verbose_name="Pincode")
    alternate_contact = models.CharField(max_length=30, blank=True, null=True, verbose_name="Alternate Contact")
    category = models.CharField(max_length=50, choices=CategoryChoices.choices, default=CategoryChoices.GENERAL, verbose_name="Category")
    enquiry_about = models.TextField(verbose_name="Enquiry About")

    # Right Side Fields
    caller_source = models.CharField(max_length=50, choices=CallerSourceChoices.choices, default=CallerSourceChoices.PHONE, verbose_name="Caller Type / Source")
    assign_to = models.CharField(max_length=150, verbose_name="Assign To")
    assign_contact = models.CharField(max_length=30, blank=True, null=True, verbose_name="Assign Contact No")
    followup_date = models.DateField(blank=True, null=True, verbose_name="Follow-up Date")
    call_received_by = models.CharField(max_length=150, blank=True, null=True, verbose_name="Call Received By")
    call_date = models.DateField(default=timezone.now, verbose_name="Call Received Date")
    call_time = models.TimeField(default=timezone.now, verbose_name="Call Received Time")
    remarks = models.TextField(blank=True, null=True, verbose_name="Remarks")
    priority = models.CharField(max_length=20, choices=PriorityChoices.choices, default=PriorityChoices.NORMAL, verbose_name="Priority")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN, verbose_name="Status")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crm_enquiries',
        verbose_name="Created By"
    )

    class Meta:
        ordering = ['-id']
        verbose_name = "CRM Enquiry"
        verbose_name_plural = "CRM Enquiries"

    def __str__(self):
        return f"{self.caller_name} ({self.caller_mobile}) - {self.category} [{self.status}]"


class AdmissionRequest(TimeStampedModel):
    class PriorityChoices(models.TextChoices):
        NORMAL = 'Normal', 'Normal'
        URGENT = 'Urgent', 'Urgent'
        EMERGENCY = 'Emergency', 'Emergency'

    class StatusChoices(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'
        CANCELLED = 'Cancelled', 'Cancelled'
        ADMITTED = 'Admitted', 'Admitted'

    class AdmissionTypeChoices(models.TextChoices):
        GENERAL = 'General Admission', 'General Admission'
        EMERGENCY = 'Emergency / Casualty', 'Emergency / Casualty'
        DAY_CARE = 'Day Care', 'Day Care'
        ICU = 'ICU / Critical Care', 'ICU / Critical Care'
        MATERNITY = 'Maternity / Delivery', 'Maternity / Delivery'
        SURGICAL = 'Surgical Admission', 'Surgical Admission'
        INSURANCE = 'Insurance / Corporate', 'Insurance / Corporate'
        OTHER = 'Other', 'Other'

    request_number = models.CharField(max_length=50, unique=True, verbose_name="Request No")
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='admission_requests',
        verbose_name="Patient"
    )
    department = models.ForeignKey(
        'patients.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admission_requests',
        verbose_name="Department"
    )
    unit_doctor = models.ForeignKey(
        'patients.DepartmentUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admission_requests',
        verbose_name="Unit / Doctor"
    )
    ward = models.ForeignKey(
        'patients.Ward',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admission_requests',
        verbose_name="Requested Ward"
    )
    bed_room = models.CharField(max_length=50, blank=True, null=True, verbose_name="Bed / Room No")
    admission_type = models.CharField(
        max_length=50,
        choices=AdmissionTypeChoices.choices,
        default=AdmissionTypeChoices.GENERAL,
        verbose_name="Admission Type"
    )
    request_date = models.DateTimeField(default=timezone.now, verbose_name="Request Date & Time")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_admissions',
        verbose_name="Requested By"
    )
    reason_remarks = models.TextField(blank=True, null=True, verbose_name="Reason / Clinical Remarks")
    priority = models.CharField(
        max_length=20,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL,
        verbose_name="Priority"
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name="Status"
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_admissions',
        verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed Date & Time")
    review_notes = models.TextField(blank=True, null=True, verbose_name="Review Notes")

    class Meta:
        ordering = ['-request_date', '-id']
        verbose_name = "Admission Request"
        verbose_name_plural = "Admission Requests"

    def __str__(self):
        return f"{self.request_number} - {self.patient.name} ({self.department.name if self.department else 'N/A'}) [{self.status}]"

    @classmethod
    def generate_request_number(cls):
        year = timezone.localdate().year
        prefix = f"AR-{year}-"
        last_req = cls.objects.filter(request_number__startswith=prefix).order_by('-id').first()
        if last_req and last_req.request_number:
            try:
                last_seq = int(last_req.request_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        return f"{prefix}{new_seq:05d}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self.generate_request_number()
        super().save(*args, **kwargs)

