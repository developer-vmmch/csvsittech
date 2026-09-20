from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import TimeStampedModel

class Department(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="Department Code")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def seed_defaults(cls):
        """Ensures default departments and units exist in DB"""
        deps = [
            {'code': 'CTB', 'name': 'CHEST & TB'},
            {'code': 'DENTAL', 'name': 'DENTAL'},
            {'code': 'DERM', 'name': 'DERMATOLOGY'},
            {'code': 'EMR', 'name': 'EMERGENCY MEDICINE'},
            {'code': 'ENT', 'name': 'ENT'},
            {'code': 'GM', 'name': 'GENERAL MEDICINE'},
            {'code': 'GS', 'name': 'GENERAL SURGERY'},
            {'code': 'GYN', 'name': 'GYNAECOLOGY'},
            {'code': 'OBS', 'name': 'OBSTETRICS'},
            {'code': 'OPH', 'name': 'OPHTHALMOLOGY'},
            {'code': 'ORTHO', 'name': 'ORTHOPAEDICS'},
            {'code': 'PED', 'name': 'PAEDIATRICS'},
            {'code': 'PSY', 'name': 'PSYCHIATRY'},
        ]
        for d in deps:
            if not cls.objects.filter(name__iexact=d['name']).exists():
                cls.objects.create(name=d['name'], code=d['code'], is_active=True)


class DepartmentUnit(TimeStampedModel):
    class UnitTypeChoices(models.TextChoices):
        HOD = 'HOD', 'HOD'
        UNIT = 'Unit', 'Unit'
        DOCTOR = 'Doctor', 'Doctor'
        CONSULTANT = 'Consultant', 'Consultant'
        OTHER = 'Other', 'Other'

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units')
    unit_name = models.CharField(max_length=150, verbose_name="Unit / Doctor Name")
    code = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Unit/Doctor Code")
    unit_type = models.CharField(max_length=20, choices=UnitTypeChoices.choices, default=UnitTypeChoices.OTHER, verbose_name="Type")
    head_doctor = models.CharField(max_length=100, blank=True, null=True, verbose_name="Head Doctor")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['department', 'display_order', 'unit_name']
        unique_together = ('department', 'unit_name')

    def __str__(self):
        return f"{self.unit_name} ({self.department.name})"


class PatientCompany(TimeStampedModel):
    class CompanyCategory(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', 'Individual / Self Pay'
        INTERNAL_STAFF = 'STAFF', 'Internal Staff / VMMC'
        GOVT_SCHEME = 'GOVT', 'Government Scheme (CGHS / ESI)'
        INSURANCE_TPA = 'INSURANCE', 'Insurance / TPA'
        CORPORATE = 'CORPORATE', 'Corporate Tie-up'

    code = models.CharField(max_length=50, unique=True, verbose_name="Company Code")
    name = models.CharField(max_length=150, verbose_name="Company / Scheme Name")
    category = models.CharField(max_length=30, choices=CompanyCategory.choices, default=CompanyCategory.INDIVIDUAL)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Discount (%)")
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Patient Companies"

    def __str__(self):
        return self.name

    @classmethod
    def seed_defaults(cls):
        """Ensures default patient companies exist in database"""
        defaults = [
            {'code': 'IND-001', 'name': 'INDIVIDUAL', 'category': cls.CompanyCategory.INDIVIDUAL},
            {'code': 'STF-001', 'name': 'VMMC STAFF', 'category': cls.CompanyCategory.INTERNAL_STAFF},
            {'code': 'CGHS-01', 'name': 'CGHS SCHEME', 'category': cls.CompanyCategory.GOVT_SCHEME},
            {'code': 'ESI-001', 'name': 'ESI CORPORATION', 'category': cls.CompanyCategory.GOVT_SCHEME},
            {'code': 'STAR-01', 'name': 'STAR HEALTH INSURANCE', 'category': cls.CompanyCategory.INSURANCE_TPA},
        ]
        for item in defaults:
            cls.objects.get_or_create(code=item['code'], defaults=item)


class Patient(TimeStampedModel):
    class TitleChoices(models.TextChoices):
        NONE = '-', '-'
        MR = 'Mr', 'Mr'
        MRS = 'Mrs', 'Mrs'
        MS = 'Ms', 'Ms'
        MISS = 'Miss', 'Miss'
        MASTER = 'Master', 'Master'
        DR = 'Dr', 'Dr'
        BABY = 'Baby', 'Baby'

    class GenderChoices(models.TextChoices):
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'
        OTHER = 'Other', 'Other'

    class VisitChoices(models.TextChoices):
        OP = 'OP', 'Out-Patient (OP)'
        IP = 'IP', 'In-Patient (IP)'
        REVIEW = 'REVIEW', 'Review'

    class CategoryChoices(models.TextChoices):
        CONSULTATION = 'CONSULTATION', 'Consultation'
        CASUALTY = 'CASUALTY', 'Casualty'
        EMERGENCY = 'EMERGENCY', 'Emergency'
        RE_CONSULTATION = 'RE_CONSULTATION', 'Re-Consultation'

    class GuardianRelChoices(models.TextChoices):
        NONE = '-', '-'
        SO = 'S/O', 'S/O (Son of)'
        DO = 'D/O', 'D/O (Daughter of)'
        WO = 'W/O', 'W/O (Wife of)'
        CO = 'C/O', 'C/O (Care of)'
        HO = 'H/O', 'H/O (Husband of)'
        FO = 'F/O', 'F/O (Father of)'
        MO = 'M/O', 'M/O (Mother of)'
        GO = 'G/O', 'G/O (Guardian of)'

    class CentreChoices(models.TextChoices):
        VMMCH = 'VMMCH', 'VMMCH'
        CAMP = 'CAMP', 'Camp'
        RURAL = 'RURAL', 'Rural'
        URBAN = 'URBAN', 'Urban'

    class SourceChoices(models.TextChoices):
        NORMAL = 'O', 'Normal Entry'
        AUTO_TRIGGER = 'D', 'Auto Trigger Entry'

    # Patient Identification
    patient_id = models.CharField(max_length=50, unique=True, db_index=True)
    op_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="OP Number")
    ipno = models.CharField(max_length=50, blank=True, null=True, verbose_name="IPNO")
    centre = models.CharField(max_length=50, choices=CentreChoices.choices, default=CentreChoices.VMMCH, verbose_name="Centre")
    registration_date = models.DateField(default=timezone.now, verbose_name="Registration Date")
    patient_type = models.CharField(
        max_length=1, 
        choices=SourceChoices.choices, 
        default=SourceChoices.NORMAL, 
        db_index=True,
        verbose_name="Patient Type"
    )
    created_source = models.CharField(
        max_length=1, 
        choices=SourceChoices.choices, 
        default=SourceChoices.NORMAL, 
        db_index=True,
        verbose_name="Entry Type / Source"
    )
    automation_scheduled_at = models.DateTimeField(
        null=True, 
        blank=True, 
        db_index=True, 
        verbose_name="Scheduled Creation Date & Time"
    )
    auto_trigger_run = models.ForeignKey(
        'lab.AutoTriggerHistory', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='generated_patients',
        verbose_name="Auto Trigger Run"
    )
    auto_trigger_stage = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        default='STAGE 1 - PATIENT CREATION',
        verbose_name="Auto Trigger Stage"
    )
    source_patient = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='auto_triggered_copies',
        verbose_name="Source Patient Reference"
    )
    
    # Personal Info
    title = models.CharField(max_length=10, choices=TitleChoices.choices, default='-')
    name = models.CharField(max_length=150, verbose_name="Patient Name")
    gender = models.CharField(max_length=10, choices=GenderChoices.choices, default=GenderChoices.MALE)
    dob = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    age_years = models.PositiveIntegerField(default=0, verbose_name="Age (Years)")
    age_months = models.PositiveIntegerField(default=0, verbose_name="Age (Months)")
    age_days = models.PositiveIntegerField(default=0, verbose_name="Age (Days)")
    
    # Government IDs & Visit Category
    aadhar_card = models.CharField(max_length=20, blank=True, null=True, verbose_name="AAdhar Card")
    visit_through = models.CharField(max_length=10, choices=VisitChoices.choices, default=VisitChoices.OP)
    category = models.CharField(max_length=50, choices=CategoryChoices.choices, default=CategoryChoices.CONSULTATION)
    marital_status = models.CharField(max_length=20, blank=True, null=True)
    religion = models.CharField(max_length=30, blank=True, null=True)
    
    # Guardian Info
    guardian_title = models.CharField(max_length=10, choices=TitleChoices.choices, default='-')
    guardian_relationship = models.CharField(max_length=10, choices=GuardianRelChoices.choices, default='-')
    guardian_name = models.CharField(max_length=100, blank=True, null=True)
    guardian_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Guardian Phone")
    company_name = models.CharField(max_length=100, default="INDIVIDUAL")
    patient_company = models.ForeignKey(PatientCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    abha_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ABHAID")
    ofc_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="OFC Code")
    
    # Address Info
    street = models.CharField(max_length=200, blank=True, null=True)
    village_area = models.CharField(max_length=100, blank=True, null=True, verbose_name="Village / Area")
    country = models.CharField(max_length=50, default="India")
    state = models.CharField(max_length=50, default="Puducherry")
    city = models.CharField(max_length=50, default="Karaikal")
    pincode = models.CharField(max_length=20, blank=True, null=True)
    
    # Medical & Doctor Assignment
    mobile_no = models.CharField(max_length=20, blank=True, null=True, default='', verbose_name="Mobile No (without 91)")
    alternate_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Alternate Phone")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Emergency Contact Phone")
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    complaint = models.TextField(blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=100, default="GENERAL MEDICINE")
    unit_doctor = models.CharField(max_length=100, default="HOD-GENERAL MEDICINE-V", verbose_name="Unit / Doctor")
    department_obj = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    unit_obj = models.ForeignKey(DepartmentUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    pan_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN No")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_patients',
        verbose_name="Created By User"
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} ({self.patient_id})"

    @property
    def active_ip_admission(self):
        """Returns the active (undischarged) IP visit if any, else None."""
        from django.db.models import Q
        return self.visits.filter(
            Q(visit_type=self.VisitChoices.IP) | Q(ipno__isnull=False, ipno__gt=''),
            discharge_date__isnull=True
        ).order_by('-id').first()

    @property
    def is_admitted_inpatient(self):
        """Returns True if the patient currently has an active, undischarged IP admission."""
        return self.active_ip_admission is not None

    def save(self, *args, **kwargs):
        if not self.patient_type:
            self.patient_type = self.created_source or 'O'
        if not self.created_source:
            self.created_source = self.patient_type or 'O'
            
        is_emer = False
        cat = str(self.category or '').upper()
        if cat in ['EMERGENCY', 'CASUALTY']:
            is_emer = True
        elif self.department_obj and any(term in self.department_obj.name.upper() for term in ['EMERGENCY', 'CASUALTY']):
            is_emer = True
        elif self.department and any(term in str(self.department).upper() for term in ['EMERGENCY', 'CASUALTY']):
            is_emer = True

        if not self.patient_id:
            self.patient_id = self.generate_next_patient_id(is_emergency=is_emer)
        elif is_emer and not str(self.patient_id).upper().startswith('E') and not self.pk:
            self.patient_id = f"E{self.patient_id}"

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.patient_type == 'D' or self.created_source == 'D':
            from django.core.exceptions import ValidationError
            raise ValidationError("Auto Trigger generated patients cannot be deleted.")
        super().delete(*args, **kwargs)

    @classmethod
    def generate_next_patient_id(cls, is_emergency=False):
        """
        Generate the next unique patient ID.
        Normal: Sequential numeric ID (e.g. 26148627)
        Emergency: Prefixed with 'E' (e.g. E26148627 or sequential emergency ID)
        """
        from django.db.models import Max
        from django.db.models.functions import Cast
        from django.db.models import BigIntegerField

        if is_emergency:
            e_patients = cls.objects.filter(patient_id__iregex=r'^E[0-9]+$').values_list('patient_id', flat=True)
            max_e_num = None
            for pid in e_patients:
                try:
                    num_val = int(pid[1:])
                    if max_e_num is None or num_val > max_e_num:
                        max_e_num = num_val
                except (ValueError, TypeError):
                    continue

            if max_e_num is not None:
                return f"E{max_e_num + 1}"
            else:
                normal_next = cls.generate_next_patient_id(is_emergency=False)
                return f"E{normal_next}"

        max_patient_id = (
            cls.objects
            .filter(patient_id__isnull=False)
            .exclude(patient_id='')
            .filter(patient_id__regex=r'^[0-9]+$')
            .annotate(
                numeric_patient_id=Cast(
                    'patient_id',
                    BigIntegerField()
                )
            )
            .aggregate(
                max_id=Max('numeric_patient_id')
            )['max_id']
        )

        if max_patient_id is None:
            return "26148626"

        return str(max_patient_id + 1)

    @classmethod
    def generate_next_ipno(cls, is_emergency=False):
        """
        Generates sequential numeric IP number starting from 600000.
        If is_emergency is True, prefixes with 'E' (e.g. E600000, E600001).
        """
        if is_emergency:
            max_num = None
            for p in cls.objects.filter(ipno__iregex=r'^E[0-9]+$').values_list('ipno', flat=True):
                try:
                    num_val = int(p[1:])
                    if max_num is None or num_val > max_num:
                        max_num = num_val
                except (ValueError, TypeError):
                    continue

            for v in PatientVisit.objects.filter(ipno__iregex=r'^E[0-9]+$').values_list('ipno', flat=True):
                try:
                    num_val = int(v[1:])
                    if max_num is None or num_val > max_num:
                        max_num = num_val
                except (ValueError, TypeError):
                    continue

            if max_num is not None:
                return f"E{max_num + 1}"
            else:
                normal_next = cls.generate_next_ipno(is_emergency=False)
                return f"E{normal_next}"

        max_num = 599999
        p_patients = cls.objects.filter(ipno__isnull=False).exclude(ipno='')
        for p in p_patients:
            if p.ipno and p.ipno.isdigit():
                val = int(p.ipno)
                if val > max_num:
                    max_num = val

        p_visits = PatientVisit.objects.filter(ipno__isnull=False).exclude(ipno='')
        for v in p_visits:
            if v.ipno and v.ipno.isdigit():
                val = int(v.ipno)
                if val > max_num:
                    max_num = val

        return str(max_num + 1)

    @classmethod
    def generate_next_op_number(cls):
        """Generate the next unique numeric OP number."""

        from django.db.models import Max
        from django.db.models.functions import Cast
        from django.db.models import BigIntegerField

        max_op_number = (
            cls.objects
            .filter(op_number__isnull=False)
            .exclude(op_number='')
            .filter(op_number__regex=r'^[0-9]+$')
            .annotate(
                numeric_op_number=Cast(
                    'op_number',
                    BigIntegerField()
                )
            )
            .aggregate(
                max_number=Max('numeric_op_number')
            )['max_number']
        )

        if max_op_number is None:
            return "26100000"

        return str(max_op_number + 1)



class PatientVisit(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_no = models.PositiveIntegerField(verbose_name="Visit No")
    visit_date = models.DateTimeField(default=timezone.now, verbose_name="Visit Date & Time")
    department_obj = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits')
    department = models.CharField(max_length=100, default="GENERAL MEDICINE")
    unit_obj = models.ForeignKey(DepartmentUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='visits')
    unit_doctor = models.CharField(max_length=100, default="HOD-GENERAL MEDICINE-V", verbose_name="Unit / Doctor")
    visit_type = models.CharField(max_length=20, choices=Patient.VisitChoices.choices, default=Patient.VisitChoices.OP)
    centre = models.CharField(max_length=50, choices=Patient.CentreChoices.choices, default=Patient.CentreChoices.VMMCH, verbose_name="Centre")
    category = models.CharField(max_length=50, choices=Patient.CategoryChoices.choices, default=Patient.CategoryChoices.RE_CONSULTATION)
    ipno = models.CharField(max_length=50, blank=True, null=True, verbose_name="IP Number")
    ward = models.CharField(max_length=50, blank=True, null=True)
    bed = models.CharField(max_length=50, blank=True, null=True)
    discharge_date = models.DateField(blank=True, null=True, verbose_name="Date of Discharge")
    discharge_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default='Normal / Improved',
        verbose_name="Discharge Type / Status"
    )
    discharge_notes = models.TextField(blank=True, null=True, verbose_name="Discharge Summary / Advice")
    ref_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ref No")
    ref_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referred By")
    ref_date = models.DateField(blank=True, null=True, verbose_name="Ref Date")
    reg_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Registration Fees")
    coll_status = models.CharField(max_length=20, default="Paid", verbose_name="Collection Status")
    clinical_notes = models.TextField(blank=True, null=True, verbose_name="Clinical Notes / Diagnosis")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_visits'
    )

    class Meta:
        ordering = ['-visit_no']
        unique_together = ['patient', 'visit_no']

    def __str__(self):
        return f"Visit #{self.visit_no} - {self.patient.name} ({self.visit_date.strftime('%d/%b/%Y')})"

    @property
    def is_active_ip(self):
        """Returns True if this visit is an active, undischarged Inpatient admission."""
        return (self.visit_type == Patient.VisitChoices.IP or bool(self.ipno)) and self.discharge_date is None

    @property
    def initial_department_name(self):
        """Returns the initial department name before any ward transfer, or current department."""
        first_transfer = self.branch_transfers.filter(status='ACCEPTED').order_by('reviewed_at').first()
        if first_transfer:
            return first_transfer.from_department.name
        return self.department

    @property
    def ip_department_name(self):
        """Returns the department where the patient is placed for IP admission."""
        if self.visit_type == Patient.VisitChoices.IP or bool(self.ipno):
            return self.department
        return None

    @property
    def is_transferred(self):
        """Returns True if this admission has been transferred to another department."""
        return self.branch_transfers.filter(status='ACCEPTED').exists()

    @property
    def latest_transfer(self):
        """Returns the latest accepted transfer request."""
        return self.branch_transfers.filter(status='ACCEPTED').order_by('-reviewed_at').first()

    def discharge(self, discharge_date=None, discharge_type='Normal / Improved', discharge_notes=None):
        """Marks this IP visit as discharged."""
        self.discharge_date = discharge_date or timezone.localdate()
        if discharge_type:
            self.discharge_type = discharge_type
        if discharge_notes is not None:
            self.discharge_notes = discharge_notes
        self.save(update_fields=['discharge_date', 'discharge_type', 'discharge_notes'])

class PatientImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    upload_file = models.FileField(upload_to='patient_imports/', null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_records = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.file_name} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class BranchTransferRequest(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    transfer_request_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Transfer Request ID"
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='branch_transfers',
        verbose_name="Patient"
    )
    admission = models.ForeignKey(
        PatientVisit,
        on_delete=models.CASCADE,
        related_name='branch_transfers',
        verbose_name="Active Admission"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='outgoing_branch_transfers',
        verbose_name="Current Department"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='incoming_branch_transfers',
        verbose_name="Requested Department"
    )
    to_unit = models.ForeignKey(
        DepartmentUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_unit_transfers',
        verbose_name="Destination Unit / Doctor"
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name="Status"
    )
    transfer_reason = models.TextField(
        verbose_name="Transfer Reason / Notes"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_branch_transfers',
        verbose_name="Requested By"
    )
    requested_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Requested Date & Time"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_branch_transfers',
        verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Reviewed Date & Time"
    )
    review_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Review / Rejection Notes"
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_branch_transfers',
        verbose_name="Cancelled By"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Cancelled Date & Time"
    )
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Cancellation Reason"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Branch Transfer Request"
        verbose_name_plural = "Branch Transfer Requests"

    def __str__(self):
        return f"{self.transfer_request_number} - {self.patient.name} ({self.from_department.name} -> {self.to_department.name}) [{self.status}]"

    @classmethod
    def generate_transfer_request_number(cls):
        """Generates sequential format: BTR-YYYY-XXXXX (e.g. BTR-2026-00001)"""
        year = timezone.localdate().year
        prefix = f"BTR-{year}-"
        last_req = cls.objects.filter(transfer_request_number__startswith=prefix).order_by('-id').first()
        if last_req and last_req.transfer_request_number:
            try:
                last_seq = int(last_req.transfer_request_number.split('-')[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        return f"{prefix}{new_seq:05d}"

    def save(self, *args, **kwargs):
        if not self.transfer_request_number:
            self.transfer_request_number = self.generate_transfer_request_number()
        super().save(*args, **kwargs)

    def accept(self, reviewed_by=None, review_notes=None, to_unit=None):
        """
        Atomically executes the transfer:
        - Updates the patient's active admission department to to_department.
        - Updates to_unit/doctor if supplied.
        - Updates patient.department_obj to to_department.
        - Sets status to ACCEPTED with reviewer info and timestamp.
        """
        from django.db import transaction
        if self.status != self.StatusChoices.PENDING:
            raise ValueError(f"Cannot accept transfer request with status '{self.status}'.")

        with transaction.atomic():
            # Update admission record
            admission = self.admission
            admission.department_obj = self.to_department
            admission.department = self.to_department.name
            if to_unit:
                self.to_unit = to_unit
                admission.unit_obj = to_unit
                admission.unit_doctor = to_unit.unit_name
            elif self.to_unit:
                admission.unit_obj = self.to_unit
                admission.unit_doctor = self.to_unit.unit_name
            elif self.to_department.units.exists():
                first_unit = self.to_department.units.first()
                admission.unit_obj = first_unit
                admission.unit_doctor = first_unit.unit_name
            admission.save(update_fields=['department_obj', 'department', 'unit_obj', 'unit_doctor'])

            # Update patient primary department
            self.patient.department_obj = self.to_department
            self.patient.department = self.to_department.name
            if admission.unit_obj:
                self.patient.unit_obj = admission.unit_obj
            self.patient.save(update_fields=['department_obj', 'department', 'unit_obj'])

            # Update transfer request record
            self.status = self.StatusChoices.ACCEPTED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            if review_notes:
                self.review_notes = review_notes
            self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'to_unit'])

    def reject(self, reviewed_by=None, rejection_reason=""):
        """
        Rejects the transfer request.
        Patient remains in the source department.
        """
        if self.status != self.StatusChoices.PENDING:
            raise ValueError(f"Cannot reject transfer request with status '{self.status}'.")
        if not (rejection_reason or '').strip():
            raise ValueError("Rejection reason is mandatory.")

        self.status = self.StatusChoices.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = rejection_reason.strip()
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])

    def cancel(self, cancelled_by=None, cancellation_reason=""):
        """
        Cancels the transfer request.
        """
        if self.status != self.StatusChoices.PENDING:
            raise ValueError(f"Cannot cancel transfer request with status '{self.status}'.")

        self.status = self.StatusChoices.CANCELLED
        self.cancelled_by = cancelled_by
        self.cancelled_at = timezone.now()
        if cancellation_reason:
            self.cancellation_reason = cancellation_reason.strip()
        self.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])

