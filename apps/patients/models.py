from django.db import models
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
            {'code': 'GENMED', 'name': 'GENERAL MEDICINE'},
            {'code': 'PED', 'name': 'PEDIATRICS'},
            {'code': 'ORTHO', 'name': 'ORTHOPEDICS'},
            {'code': 'DERM', 'name': 'DERMATOLOGY'},
            {'code': 'SURG', 'name': 'SURGERY'},
            {'code': 'CARD', 'name': 'CARDIOLOGY'},
        ]
        for d in deps:
            dep_obj, _ = cls.objects.get_or_create(code=d['code'], defaults=d)
            
            # Create default units for department if missing
            if not dep_obj.units.exists():
                if d['code'] == 'GENMED':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='HOD-GENERAL MEDICINE-V', head_doctor='Dr. V. General')
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. KUMAR', head_doctor='Dr. Kumar')
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-II DR. SHARMA', head_doctor='Dr. Sharma')
                elif d['code'] == 'PED':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. ANITA (PEDIATRICS)', head_doctor='Dr. Anita')
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-II DR. RAHUL', head_doctor='Dr. Rahul')
                elif d['code'] == 'ORTHO':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. RAJESH (ORTHO)', head_doctor='Dr. Rajesh')
                elif d['code'] == 'DERM':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. MEENA (DERM)', head_doctor='Dr. Meena')
                elif d['code'] == 'SURG':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. SURESH (SURGERY)', head_doctor='Dr. Suresh')
                elif d['code'] == 'CARD':
                    DepartmentUnit.objects.get_or_create(department=dep_obj, unit_name='UNIT-I DR. ANAND (CARDIOLOGY)', head_doctor='Dr. Anand')


class DepartmentUnit(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units')
    unit_name = models.CharField(max_length=150, verbose_name="Unit / Doctor Name")
    head_doctor = models.CharField(max_length=100, blank=True, null=True, verbose_name="Head Doctor")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['unit_name']
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
        SO = 'S/O', 'S/O (Son of)'
        DO = 'D/O', 'D/O (Daughter of)'
        WO = 'W/O', 'W/O (Wife of)'
        CO = 'C/O', 'C/O (Care of)'

    # Patient Identification
    patient_id = models.CharField(max_length=50, unique=True, db_index=True)
    ipno = models.CharField(max_length=50, blank=True, null=True, verbose_name="IPNO")
    
    # Personal Info
    title = models.CharField(max_length=10, choices=TitleChoices.choices, default=TitleChoices.MR)
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
    guardian_relationship = models.CharField(max_length=10, choices=GuardianRelChoices.choices, default=GuardianRelChoices.SO)
    guardian_name = models.CharField(max_length=100, blank=True, null=True)
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
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    complaint = models.TextField(blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=100, default="GENERAL MEDICINE")
    unit_doctor = models.CharField(max_length=100, default="HOD-GENERAL MEDICINE-V", verbose_name="Unit / Doctor")
    department_obj = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    unit_obj = models.ForeignKey(DepartmentUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')
    pan_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN No")

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
