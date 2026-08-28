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
            try:
                cls.objects.get_or_create(name__iexact=d['name'], defaults={'name': d['name'], 'code': d['code'], 'is_active': True})
            except cls.MultipleObjectsReturned:
                # If there are duplicates, we ignore instead of breaking the app
                pass


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

    class CentreChoices(models.TextChoices):
        VMMCH = 'VMMCH', 'VMMCH'
        CAMP = 'CAMP', 'Camp'
        RURAL = 'RURAL', 'Rural'
        URBAN = 'URBAN', 'Urban'

    # Patient Identification
    patient_id = models.CharField(max_length=50, unique=True, db_index=True)
    op_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="OP Number")
    ipno = models.CharField(max_length=50, blank=True, null=True, verbose_name="IPNO")
    centre = models.CharField(max_length=50, choices=CentreChoices.choices, default=CentreChoices.VMMCH, verbose_name="Centre")
    registration_date = models.DateField(default=timezone.now, verbose_name="Registration Date")
    
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
    mobile_no = models.CharField(max_length=20, verbose_name="Mobile No (without 91)")
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

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = self.generate_next_patient_id()
        super().save(*args, **kwargs)

    @classmethod
    def generate_next_patient_id(cls):
        """Generates sequential numeric patient ID starting from 26148626"""
        last_patient = cls.objects.order_by('-id').first()
        if last_patient and last_patient.patient_id and last_patient.patient_id.isdigit():
            return str(int(last_patient.patient_id) + 1)
        return "26148626"

    @classmethod
    def generate_next_ipno(cls):
        """Generates sequential numeric IP number starting from 600000"""
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
        """Generates sequential numeric OP number starting from OP-2026-000001 (or numeric 26100000 based on old data)"""
        last_patient = cls.objects.exclude(op_number__isnull=True).exclude(op_number='').order_by('-id').first()
        if last_patient and last_patient.op_number:
            op = last_patient.op_number
            if op.startswith("OP-2026-"):
                try:
                    seq = int(op.split("-")[-1])
                    return f"OP-2026-{seq + 1:06d}"
                except ValueError:
                    pass
            elif op.isdigit():
                return str(int(op) + 1)
        
        # If no previous valid OP number found, start fresh for Auto Trigger generated ones, 
        # or just continue from a base number. The test dataset had 26100000.
        return "OP-2026-000001"


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
