from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient
from django.utils import timezone

class Diagnosis(TimeStampedModel):
    name = models.CharField(max_length=200, verbose_name="Diagnosis Name")
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="ICD-11 Code")
    icd11_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="ICD-11 Title")
    chapter = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chapter")
    synonyms = models.TextField(blank=True, null=True, verbose_name="Synonyms")
    class_kind = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Kind")
    legacy_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Legacy Code")
    source = models.CharField(max_length=100, blank=True, null=True, verbose_name="Source (e.g. WHO, Import)")
    icd_version = models.CharField(max_length=50, blank=True, null=True, verbose_name="ICD Version")
    who_uri = models.URLField(blank=True, null=True, verbose_name="WHO URI")
    department = models.ForeignKey('patients.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='primary_diagnoses')
    gender_eligibility = models.CharField(max_length=10, choices=[('All','All'), ('Male','Male'), ('Female','Female')], default='All', verbose_name="Gender Eligibility")
    min_age = models.PositiveIntegerField(null=True, blank=True, verbose_name="Minimum Age")
    max_age = models.PositiveIntegerField(null=True, blank=True, verbose_name="Maximum Age")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Diagnoses"

    def __str__(self):
        return f"{self.name} ({self.code})"

class LabDiagnosis(TimeStampedModel):
    name = models.CharField(max_length=200, verbose_name="Diagnosis Name")
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="ICD-11 Code")
    icd11_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="ICD-11 Title")
    chapter = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chapter")
    synonyms = models.TextField(blank=True, null=True, verbose_name="Synonyms")
    class_kind = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Kind")
    legacy_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Legacy Code")
    source = models.CharField(max_length=100, blank=True, null=True, verbose_name="Source (e.g. WHO, Import)")
    icd_version = models.CharField(max_length=50, blank=True, null=True, verbose_name="ICD Version")
    who_uri = models.URLField(blank=True, null=True, verbose_name="WHO URI")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']
        verbose_name = "Diagnosis"
        verbose_name_plural = "Diagnoses"

    def __str__(self):
        return f"{self.name} ({self.code})"



class DiagnosisImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='diagnosis_imports')
    total_rows = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    duplicates = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} on {self.created_at}"

class InvestigationImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='investigation_imports')
    total_investigations = models.IntegerField(default=0)
    total_parameters = models.IntegerField(default=0)
    investigations_imported = models.IntegerField(default=0)
    investigations_updated = models.IntegerField(default=0)
    investigations_skipped = models.IntegerField(default=0)
    parameters_imported = models.IntegerField(default=0)
    parameters_updated = models.IntegerField(default=0)
    parameters_skipped = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} on {self.created_at}"

class ChiefComplaint(TimeStampedModel):
    name = models.CharField(max_length=200, verbose_name="Complaint Name")
    legacy_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Legacy Code")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class HospitalService(TimeStampedModel):
    class CategoryChoices(models.TextChoices):
        BED_CHARGE = 'Bed Charge', 'Bed Charge'
        AMBULANCE = 'Ambulance', 'Ambulance'
        OT_CHARGE = 'OT Charge', 'OT Charge'
        DIALYSIS = 'Dialysis', 'Dialysis'
        PHYSIO = 'Physiotherapy Modality', 'Physiotherapy Modality'
        OTHER = 'Other', 'Other'

    name = models.CharField(max_length=200, verbose_name="Service Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="Code (Legacy Accession)")
    category = models.CharField(max_length=50, choices=CategoryChoices.choices, default=CategoryChoices.OTHER)
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class StagingDiagnosis(models.Model):
    legacy_id = models.CharField(max_length=50, unique=True)
    legacy_text = models.CharField(max_length=255)
    migrated = models.BooleanField(default=False)
    migrated_to_type = models.CharField(max_length=50, blank=True, null=True, help_text="Diagnosis, ChiefComplaint, or Skipped")
    migrated_to_id = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['legacy_id']

    def __str__(self):
        return f"{self.legacy_text} ({self.legacy_id})"

class StagingInvestigation(models.Model):
    legacy_code = models.CharField(max_length=50, unique=True)
    legacy_text = models.CharField(max_length=255)
    migrated = models.BooleanField(default=False)
    migrated_to_type = models.CharField(max_length=50, blank=True, null=True, help_text="Investigation, HospitalService, or Skipped")
    migrated_to_id = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['legacy_code']

    def __str__(self):
        return f"{self.legacy_text} ({self.legacy_code})"

class LabDepartment(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class SampleType(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True, verbose_name="Sample Type")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Investigation(TimeStampedModel):
    name = models.CharField(max_length=200, verbose_name="Investigation Name")
    short_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Short Name / Alias")
    code = models.CharField(max_length=50, unique=True, verbose_name="Investigation Code")
    department = models.ForeignKey(LabDepartment, on_delete=models.SET_NULL, null=True, blank=True, related_name='investigations', verbose_name="Department")
    sample_type = models.ForeignKey(SampleType, on_delete=models.SET_NULL, null=True, blank=True, related_name='investigations', verbose_name="Sample Type")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Category")
    specimen = models.CharField(max_length=100, blank=True, null=True, verbose_name="Specimen")
    method = models.CharField(max_length=150, blank=True, null=True, verbose_name="Method")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_panel = models.BooleanField(default=False, verbose_name="Is Panel (Multi-parameter)")
    turnaround_time_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name="Turnaround Time (Hours)")
    legacy_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Legacy Code")
    grpi = models.IntegerField(default=0, verbose_name="Group Index (Grpi)")
    grp = models.CharField(max_length=10, default='I', choices=[('G', 'Group'), ('I', 'Individual')], verbose_name="Group Type (Grp)")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class Parameter(TimeStampedModel):
    class DataTypeChoices(models.TextChoices):
        NUMERIC = 'NUMERIC', 'Numeric'
        TEXT = 'TEXT', 'Text'
        SELECT = 'SELECT', 'Select/Dropdown'

    name = models.CharField(max_length=200, verbose_name="Parameter Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="Parameter Code")
    default_unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="Default Unit")
    data_type = models.CharField(max_length=20, choices=DataTypeChoices.choices, default=DataTypeChoices.NUMERIC, verbose_name="Data Type")
    result_type = models.CharField(max_length=50, default='Numeric', blank=True, null=True, verbose_name="Result Type")
    default_decimal_places = models.PositiveIntegerField(default=2, blank=True, null=True, verbose_name="Default Decimal Places")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

class AgeGroup(TimeStampedModel):
    class AgeUnitChoices(models.TextChoices):
        DAY = 'Days', 'Days'
        MONTH = 'Months', 'Months'
        YEAR = 'Years', 'Years'

    class GenderChoices(models.TextChoices):
        ALL = 'All', 'All'
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'

    code = models.CharField(max_length=50, unique=True, verbose_name="Age Group Code", default="DEFAULT")
    label = models.CharField(max_length=100, verbose_name="Age Group Name")
    min_age_value = models.PositiveIntegerField(null=True, blank=True, verbose_name="Min Age Value")
    min_age_unit = models.CharField(max_length=10, choices=AgeUnitChoices.choices, default=AgeUnitChoices.YEAR, verbose_name="Min Age Unit")
    max_age_value = models.PositiveIntegerField(null=True, blank=True, verbose_name="Max Age Value")
    max_age_unit = models.CharField(max_length=10, choices=AgeUnitChoices.choices, default=AgeUnitChoices.YEAR, verbose_name="Max Age Unit")
    gender = models.CharField(max_length=10, choices=GenderChoices.choices, default=GenderChoices.ALL, verbose_name="Gender")
    pregnancy_applicable = models.BooleanField(default=False, verbose_name="Pregnancy Applicable")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['sort_order', 'label']

    def __str__(self):
        return self.label



class InvestigationParameter(TimeStampedModel):
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='investigations', null=True, blank=True)
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Parameter Code")
    name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Parameter Name")
    short_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Short Name")
    result_type = models.CharField(max_length=50, default='Numeric', verbose_name="Result Type")
    unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="Unit")
    decimal_precision = models.IntegerField(null=True, blank=True, verbose_name="Decimal Precision")
    reference_range = models.CharField(max_length=255, null=True, blank=True, verbose_name="Reference Range")
    critical_low = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Critical Low")
    critical_high = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Critical High")
    male_reference_range = models.CharField(max_length=255, null=True, blank=True, verbose_name="Male Reference Range")
    female_reference_range = models.CharField(max_length=255, null=True, blank=True, verbose_name="Female Reference Range")
    child_reference_range = models.CharField(max_length=255, null=True, blank=True, verbose_name="Child Reference Range")
    minimum_age = models.IntegerField(null=True, blank=True, verbose_name="Minimum Age")
    maximum_age = models.IntegerField(null=True, blank=True, verbose_name="Maximum Age")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    is_mandatory = models.BooleanField(default=False, verbose_name="Is Mandatory")
    is_calculated = models.BooleanField(default=False, verbose_name="Is Calculated")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        unique_together = ('investigation', 'code')
        ordering = ['investigation', 'display_order']

    def __str__(self):
        return f"{self.investigation.name} - {self.name or self.parameter}"

class ParameterReferenceRange(TimeStampedModel):
    class GenderChoices(models.TextChoices):
        ALL = 'All', 'All'
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'
    class PregnancyChoices(models.TextChoices):
        NO = 'No', 'No'
        YES = 'Yes', 'Yes'
        NA = 'N/A', 'N/A'

    class RangeTypeChoices(models.TextChoices):
        NUMERIC = 'Numeric', 'Numeric Range'
        TEXT = 'Text', 'Text / Qualitative'
        NONE = 'None', 'No Reference Range'

    investigation_parameter = models.ForeignKey(InvestigationParameter, on_delete=models.CASCADE, related_name='reference_ranges')
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='reference_ranges')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, null=True, blank=True, related_name='reference_ranges', help_text="Null means generic range for this age group")
    gender = models.CharField(max_length=10, choices=GenderChoices.choices, default=GenderChoices.ALL)
    pregnancy = models.CharField(max_length=10, choices=PregnancyChoices.choices, default=PregnancyChoices.NO, verbose_name="Pregnancy")
    
    range_type = models.CharField(max_length=20, choices=RangeTypeChoices.choices, default=RangeTypeChoices.NUMERIC, verbose_name="Range Type")
    min_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Min Value")
    max_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Max Value")
    reference_text = models.CharField(max_length=500, null=True, blank=True, verbose_name="Reference Text")
    unit = models.CharField(max_length=50, blank=True, null=True)
    method = models.CharField(max_length=200, null=True, blank=True, verbose_name="Method")
    remarks = models.TextField(null=True, blank=True, verbose_name="Remarks")
    
    critical_low = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Critical Low")
    critical_high = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Critical High")
    interpretation = models.TextField(null=True, blank=True, verbose_name="Interpretation")
    
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        unique_together = ('investigation_parameter', 'age_group', 'diagnosis', 'gender')

    def __str__(self):
        return f"Range for {self.investigation_parameter} ({self.age_group})"

class PatientInvestigationOrder(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_orders')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_orders')
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='lab_orders')
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_orders_placed')
    ordered_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    class Meta:
        ordering = ['-ordered_on']

    def __str__(self):
        return f"Order #{self.id} - {self.patient.name} - {self.investigation.name}"

class PatientInvestigationResult(TimeStampedModel):
    class FlagChoices(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        ABNORMAL_LOW = 'ABNORMAL_LOW', 'Abnormal Low'
        ABNORMAL_HIGH = 'ABNORMAL_HIGH', 'Abnormal High'
        CRITICAL_LOW = 'CRITICAL_LOW', 'Critical Low'
        CRITICAL_HIGH = 'CRITICAL_HIGH', 'Critical High'
        NOT_CONFIGURED = 'NOT_CONFIGURED', 'Not Configured'

    order = models.ForeignKey(PatientInvestigationOrder, on_delete=models.CASCADE, related_name='results')
    investigation_parameter = models.ForeignKey(InvestigationParameter, on_delete=models.CASCADE, related_name='results')
    result_value = models.CharField(max_length=255, verbose_name="Result Value")
    applied_reference_range = models.ForeignKey(ParameterReferenceRange, on_delete=models.SET_NULL, null=True, blank=True, related_name='applied_results')
    flag = models.CharField(max_length=20, choices=FlagChoices.choices, default=FlagChoices.NORMAL)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_results_entered')
    entered_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('order', 'investigation_parameter')

    def __str__(self):
        return f"Result for {self.investigation_parameter.parameter.name} (Order #{self.order.id})"

class ParameterImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    age_groups_created = models.IntegerField(default=0)
    age_groups_updated = models.IntegerField(default=0)
    age_groups_skipped = models.IntegerField(default=0)
    reference_ranges_created = models.IntegerField(default=0)
    reference_ranges_updated = models.IntegerField(default=0)
    reference_ranges_skipped = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')

    class Meta:
        ordering = ['-created_at']

class AgeGroupImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')

    class Meta:
        ordering = ['-created_at']

class ReferenceRangeImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    upload_file = models.FileField(upload_to='referencerange_imports/', null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')

    class Meta:
        ordering = ['-created_at']

class ServiceRequest(TimeStampedModel):
    class VisitTypeChoices(models.TextChoices):
        OP = 'OP', 'OP'
        INPATIENT = 'INPATIENT', 'Inpatient'

    class StatusChoices(models.TextChoices):
        DRAFT = 'Draft', 'Draft'
        SAVED = 'Saved', 'Saved'
        COMPLETED = 'Completed', 'Completed'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='service_requests')
    consultant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='service_requests_consulted')
    consultant_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Consultant Name")
    visit_no = models.PositiveIntegerField(null=True, blank=True, verbose_name="Visit No")
    department = models.ForeignKey('patients.Department', on_delete=models.SET_NULL, null=True, related_name='service_requests')
    visit_type = models.CharField(max_length=20, choices=VisitTypeChoices.choices, default=VisitTypeChoices.OP)
    request_date = models.DateField(default=timezone.now)
    sample_id = models.CharField(max_length=50, unique=True, blank=True)
    receipt_no = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
    clinical_remarks = models.TextField(blank=True, null=True, verbose_name="Clinical Remarks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_service_requests')
    
    class Meta:
        ordering = ['-created_at']
        
    def save(self, *args, **kwargs):
        if not self.sample_id:
            date_str = timezone.now().strftime('%y%m%d')
            # very basic generation, user should confirm
            last_req = ServiceRequest.objects.filter(sample_id__startswith=date_str).order_by('sample_id').last()
            if last_req and last_req.sample_id[6:].isdigit():
                next_seq = int(last_req.sample_id[6:]) + 1
            else:
                next_seq = 1
            self.sample_id = f"{date_str}{next_seq:04d}"
        super().save(*args, **kwargs)

class ServiceRequestDiagnosis(models.Model):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='diagnoses')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, null=True, blank=True)
    chief_complaint = models.ForeignKey(ChiefComplaint, on_delete=models.CASCADE, null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

class ServiceRequestInvestigation(models.Model):
    class SourceChoices(models.TextChoices):
        AUTO_SUGGESTED = 'AUTO_SUGGESTED', 'Auto Suggested'
        MANUAL = 'MANUAL', 'Manual'
        
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RECEIVED = 'RECEIVED', 'Received'
        COMPLETED = 'COMPLETED', 'Completed'

    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='investigations')
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    source = models.CharField(max_length=20, choices=SourceChoices.choices, default=SourceChoices.MANUAL)
    is_removed = models.BooleanField(default=False)
    
    # Work Order / Processing Tracking
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    result_status = models.CharField(max_length=20, null=True, blank=True, verbose_name="Overall Result Status")
    doc_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Doc No")
    received_date = models.DateField(null=True, blank=True)
    received_time = models.TimeField(null=True, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_samples')
    completed_date = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_samples')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_samples')

class ServiceRequestResult(TimeStampedModel):
    sr_investigation = models.ForeignKey(ServiceRequestInvestigation, on_delete=models.CASCADE, related_name='results')
    investigation_parameter = models.ForeignKey(InvestigationParameter, on_delete=models.CASCADE)
    result_value = models.CharField(max_length=255, verbose_name="Result Value")
    status = models.CharField(max_length=20, null=True, blank=True, verbose_name="Parameter Result Status")
    applied_reference_range = models.ForeignKey(ParameterReferenceRange, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('sr_investigation', 'investigation_parameter')

class ServiceRequestResultAudit(TimeStampedModel):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='result_audits')
    sr_investigation = models.ForeignKey(ServiceRequestInvestigation, on_delete=models.CASCADE, related_name='result_audits')
    investigation_parameter = models.ForeignKey(InvestigationParameter, on_delete=models.CASCADE, related_name='result_audits')
    old_value = models.CharField(max_length=255, null=True, blank=True)
    new_value = models.CharField(max_length=255)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_result_modifications')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sr_investigation.investigation.name} - {self.investigation_parameter.name}: {self.old_value} -> {self.new_value}"

class PatientVisitDiagnosis(TimeStampedModel):
    visit = models.ForeignKey('patients.PatientVisit', on_delete=models.CASCADE, related_name='diagnoses')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, null=True, blank=True)
    chief_complaint = models.ForeignKey(ChiefComplaint, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = (('visit', 'diagnosis'), ('visit', 'chief_complaint'))

    def __str__(self):
        return f"Visit #{self.visit.visit_no} - {self.diagnosis.name if self.diagnosis else self.chief_complaint.name}"

class DiagnosisInvestigationMap(TimeStampedModel):
    GENDER_CHOICES = (
        ('All', 'All'),
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, related_name='investigation_mappings')
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, related_name='investigation_mappings', null=True, blank=True)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='All')
    min_age = models.PositiveIntegerField(null=True, blank=True)
    max_age = models.PositiveIntegerField(null=True, blank=True)
    department = models.ForeignKey('patients.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='diagnosis_investigation_mappings')
    pregnancy_required = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=100)
    is_default = models.BooleanField(default=False, verbose_name="Default Investigation")
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        unique_together = ('diagnosis', 'age_group', 'investigation')
        ordering = ['priority', 'diagnosis', 'investigation']

    def __str__(self):
        return f"{self.diagnosis.name} -> {self.investigation.name}"

class DiagnosisEligibilityRule(TimeStampedModel):
    GENDER_CHOICES = (
        ('All', 'All'),
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, related_name='eligibility_rules')
    department = models.ForeignKey('patients.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='diagnosis_eligibility_rules')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='All')
    min_age = models.PositiveIntegerField(null=True, blank=True)
    max_age = models.PositiveIntegerField(null=True, blank=True)
    pregnancy_required = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['priority', '-created_at']

    def __str__(self):
        return f"Rule: {self.diagnosis.name} ({self.gender}, age {self.min_age}-{self.max_age})"


class DiagnosisDepartmentMapping(TimeStampedModel):
    department = models.ForeignKey('patients.Department', on_delete=models.CASCADE, related_name='diagnosis_mappings')
    age_group = models.ForeignKey(AgeGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='department_diagnosis_mappings')
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, related_name='department_mappings')
    status = models.CharField(max_length=20, choices=(('Active', 'Active'), ('Inactive', 'Inactive')), default='Active')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['department', 'diagnosis', 'age_group'], name='unique_department_diagnosis_mapping')
        ]
        ordering = ['department__name', 'diagnosis__name']

    def __str__(self):
        return f"{self.department.name} - {self.diagnosis.name}"


class DiagnosisDepartmentMappingImportHistory(TimeStampedModel):
    file_name = models.CharField(max_length=255)
    upload_file = models.FileField(upload_to='mapping_imports/', null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total_records = models.IntegerField(default=0)
    imported = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Completed')

    class Meta:
        ordering = ['-created_at']

class MonthlyTriggerGeneratedPatient(TimeStampedModel):
    target = models.ForeignKey('MonthlyTriggerDailyTarget', on_delete=models.CASCADE, related_name='generated_patients')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='monthly_trigger_records')
    is_duplicate = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='Success') # Success, Duplicate, Failed
    op_type = models.CharField(max_length=20, default='NEW OP') # NEW OP or REVIEW
    age_group_snapshot = models.CharField(max_length=100, blank=True, null=True)
    diagnosis_snapshot = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
class AutoTriggerTimeSetting(TimeStampedModel):
    name = models.CharField(max_length=150, default="Default Schedule")
    department = models.ForeignKey('patients.Department', on_delete=models.SET_NULL, null=True, blank=True, help_text="Optional department specific setting")
    lab_day_start = models.TimeField(default='04:00:00')
    lab_day_end = models.TimeField(default='03:59:00')
    rush_start = models.TimeField(default='10:00:00')
    rush_end = models.TimeField(default='14:00:00')
    rush_percentage = models.PositiveIntegerField(default=75)
    processing_interval = models.FloatField(default=30.0, help_text="In minutes (e.g. 0.5 for 30 seconds)")
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class AutoTriggerConfig(TimeStampedModel):
    department = models.ForeignKey('patients.Department', on_delete=models.CASCADE)
    time_setting = models.ForeignKey(AutoTriggerTimeSetting, on_delete=models.SET_NULL, null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField()
    min_entries = models.PositiveIntegerField(default=80)
    max_entries = models.PositiveIntegerField(default=125)
    trigger_start_time = models.TimeField(default='10:00:00')
    day_start_time = models.TimeField(default='04:00:00')
    day_end_time = models.TimeField(default='03:59:00')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

class AutoTriggerHistory(TimeStampedModel):
    STATUS_CHOICES = (
        ('Queued', 'Queued'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Partially Completed', 'Partially Completed'),
        ('Failed', 'Failed'),
        ('Cancelled', 'Cancelled'),
    )
    config = models.ForeignKey(AutoTriggerConfig, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey('patients.Department', on_delete=models.SET_NULL, null=True)
    from_date = models.DateField()
    to_date = models.DateField()
    
    # Rush configuration snapshotted at run time
    rush_percentage = models.PositiveIntegerField(default=75)
    rush_entries = models.PositiveIntegerField(default=0)
    remaining_entries = models.PositiveIntegerField(default=0)
    schedule_data = models.JSONField(null=True, blank=True)
    
    min_entries = models.PositiveIntegerField(default=80)
    max_entries = models.PositiveIntegerField(default=125)
    trigger_start_time = models.TimeField(default='10:00:00')
    day_start_time = models.TimeField(default='04:00:00')
    day_end_time = models.TimeField(default='03:59:00')
    
    processed_entries = models.PositiveIntegerField(default=0)
    successful = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Queued')
    current_stage = models.CharField(max_length=100, default='STAGE 1 — PATIENT CREATION')
    error_message = models.TextField(blank=True, null=True)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    last_processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def run_id(self):
        if self.created_at:
            return f"AT-{self.created_at.strftime('%Y%m%d')}-{self.id:03d}"
        return f"AT-{self.id:03d}"

class AutoTriggerLog(TimeStampedModel):
    STATUS_CHOICES = (
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Skipped', 'Skipped'),
    )
    history = models.ForeignKey(AutoTriggerHistory, on_delete=models.CASCADE, related_name='logs')
    entry_no = models.PositiveIntegerField()
    entry_date = models.DateField()
    department = models.CharField(max_length=200, blank=True, null=True)
    stage = models.CharField(max_length=50, default='STAGE 1 — PATIENT CREATION')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    source_patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_trigger_logs')
    new_patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_trigger_logs')
    visit = models.ForeignKey('patients.PatientVisit', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    message = models.TextField(blank=True, null=True)

class MonthlyTriggerPlan(TimeStampedModel):
    automation_start_date = models.DateField(null=True, blank=True)
    automation_end_date = models.DateField(null=True, blank=True)
    source_from_date = models.DateField()
    source_to_date = models.DateField()
    review_source_month_year = models.CharField(max_length=7, null=True, blank=True) # Format: YYYY-MM
    trigger_start_time = models.TimeField(default='08:00:00')
    trigger_stop_time = models.TimeField(default='13:59:00')
    interval_mins = models.FloatField(default=1.5)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active')
    is_saved = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

class MonthlyTriggerDailyTarget(TimeStampedModel):
    plan = models.ForeignKey(MonthlyTriggerPlan, on_delete=models.CASCADE, related_name='daily_targets')
    department = models.ForeignKey('patients.Department', on_delete=models.CASCADE)
    target_date = models.DateField()
    min_entries = models.PositiveIntegerField(default=100)
    max_entries = models.PositiveIntegerField(default=200)
    new_op_target = models.PositiveIntegerField(default=80)
    review_target = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=50, default='Not Started')  # Not Started, Running, Completed, Stopped, Failed
    created_count = models.PositiveIntegerField(default=0) # Legacy, keeping for compatibility
    new_op_created = models.PositiveIntegerField(default=0)
    review_created = models.PositiveIntegerField(default=0)
    duplicates_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stopped_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ['plan', 'department', 'target_date']
        ordering = ['target_date']

class MonthlyTriggerExecutionLog(TimeStampedModel):
    plan = models.ForeignKey(MonthlyTriggerPlan, on_delete=models.CASCADE, related_name='logs')
    target_date = models.DateField(null=True, blank=True)
    action = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    created_count = models.PositiveIntegerField(default=0)
    new_op_created_count = models.PositiveIntegerField(default=0)
    review_completed_count = models.PositiveIntegerField(default=0)
    duplicates_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    stopped_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']


class AutomationDummyResult(TimeStampedModel):
    result_id = models.CharField(max_length=50, unique=True)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='dummy_results')
    investigation_code = models.CharField(max_length=50, blank=True)
    dummy_name = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class StatusChoices(models.TextChoices):
        SAVED    = 'Saved',    'Saved'
        CONSUMED = 'Consumed', 'Consumed'

    class ResultStatusChoices(models.TextChoices):
        NORMAL      = 'NORMAL',      'Normal'
        BELOW       = 'BELOW',       'Below Range'
        ABOVE       = 'ABOVE',       'Above Range'
        MIXED       = 'MIXED',       'Mixed'
        NON_NUMERIC = 'NON_NUMERIC', 'Non-Numeric'

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.SAVED)
    result_status = models.CharField(
        max_length=20, choices=ResultStatusChoices.choices,
        blank=True, null=True,
        help_text='Computed classification: NORMAL/BELOW/ABOVE/MIXED/NON_NUMERIC'
    )
    remarks = models.TextField(blank=True, null=True)
    is_automation_test = models.BooleanField(default=True)
    # Synthetic patient context (stored directly, avoids polluting real Patient master)
    patient_name = models.CharField(max_length=150, blank=True, null=True)
    patient_dob = models.DateField(null=True, blank=True)
    patient_gender = models.CharField(max_length=10, blank=True, null=True)
    patient_age_display = models.CharField(max_length=50, blank=True, null=True)  # e.g. "3 days", "5 years"

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.result_id} - {self.dummy_name}"

class AutomationDummyResultParameter(TimeStampedModel):
    dummy_result = models.ForeignKey(AutomationDummyResult, on_delete=models.CASCADE, related_name='parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='dummy_results', null=True, blank=True)
    parameter_name = models.CharField(max_length=255)
    result_value = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, blank=True, null=True)
    reference_range = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    result_status = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='NORMAL | BELOW | ABOVE | NON_NUMERIC — computed by classify_existing_results'
    )

    class Meta:
        ordering = ['display_order', 'id']


class ServiceRequestAllocation(TimeStampedModel):
    """
    Links a ServiceRequestInvestigation to the AutomationDummyResult
    that was consumed for it.
    """
    sr_investigation = models.OneToOneField(
        ServiceRequestInvestigation, on_delete=models.CASCADE,
        related_name='dummy_allocation'
    )
    dummy_result = models.ForeignKey(
        AutomationDummyResult, on_delete=models.PROTECT,
        related_name='allocations'
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='dummy_allocations'
    )

    class Meta:
        ordering = ['-allocated_at']

    def __str__(self):
        return f'Alloc SR#{self.sr_investigation_id} -> {self.dummy_result.result_id}'

class LabWorkloadMapping(TimeStampedModel):
    hospital_department = models.ForeignKey('patients.Department', on_delete=models.CASCADE, related_name='lab_workloads')
    lab_sub_department = models.ForeignKey(LabDepartment, on_delete=models.CASCADE, related_name='workloads')
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='workloads')
    monthly_benchmark = models.PositiveIntegerField(null=True, blank=True)
    weekly_benchmark = models.PositiveIntegerField(null=True, blank=True)
    daily_benchmark = models.PositiveIntegerField(null=True, blank=True)
    source_file = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('hospital_department', 'lab_sub_department', 'investigation')
        ordering = ['hospital_department', 'lab_sub_department', 'investigation']

    def __str__(self):
        return f"{self.hospital_department} -> {self.investigation} ({self.lab_sub_department})"

class UnmappedLabInvestigation(TimeStampedModel):
    hospital_department_name = models.CharField(max_length=255)
    source_category = models.CharField(max_length=255, null=True, blank=True)
    investigation_name = models.CharField(max_length=255)
    reason = models.TextField(null=True, blank=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Unmapped: {self.investigation_name} ({self.hospital_department_name})"


# ===========================================================================
# ATC (AUTO TRIGGER CONTROL) MODULE MODELS
# ===========================================================================

class ATCSetting(TimeStampedModel):
    name = models.CharField(max_length=100, default="Default ATC Settings")
    default_start_time = models.TimeField(default='08:00:00', verbose_name="Default Start Time")
    default_end_time = models.TimeField(default='14:00:00', verbose_name="Default End Time")
    max_future_days = models.PositiveIntegerField(default=30, verbose_name="Max Future Generation Period (Days)")
    op_date_restriction = models.BooleanField(default=True, verbose_name="Enforce OP Today Only Restriction")
    allow_review_backdated = models.BooleanField(default=True, verbose_name="Allow Backdated Review Dates")
    allow_review_future = models.BooleanField(default=True, verbose_name="Allow Future Review Dates")
    default_batch_size = models.PositiveIntegerField(default=100, verbose_name="Default Batch Size")
    allowed_modes = models.JSONField(default=list, blank=True, verbose_name="Allowed Automation Modes")
    source_from_year = models.PositiveIntegerField(default=2022, verbose_name="Default Source From Year")
    source_to_year = models.PositiveIntegerField(default=2024, verbose_name="Default Source To Year")
    gender_ratio_male_pct = models.PositiveIntegerField(default=60, verbose_name="Default Male %")
    gender_ratio_female_pct = models.PositiveIntegerField(default=40, verbose_name="Default Female %")
    default_op_daily_pct = models.PositiveIntegerField(default=75, verbose_name="Default OP Daily %")
    default_review_pct = models.PositiveIntegerField(default=25, verbose_name="Default Review %")
    default_review_source_year = models.PositiveIntegerField(default=2024, verbose_name="Default Review Source Year")
    emergency_stop_policy = models.CharField(max_length=50, default='IMMEDIATE_PRESERVE', verbose_name="Emergency Stop Policy")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "ATC Setting"
        verbose_name_plural = "ATC Settings"

    def __str__(self):
        return self.name

    @classmethod
    def get_settings(cls):
        """Returns the active ATC settings instance, or creates a default one."""
        obj = cls.objects.filter(is_active=True).first()
        if not obj:
            obj = cls.objects.create(
                name="Default ATC Settings",
                allowed_modes=['OP', 'REVIEW', 'COMBINED']
            )
        elif not obj.allowed_modes:
            obj.allowed_modes = ['OP', 'REVIEW', 'COMBINED']
            obj.save(update_fields=['allowed_modes'])
        return obj


class ATCJob(TimeStampedModel):
    class ModeChoices(models.TextChoices):
        OP = 'OP', 'OP'
        REVIEW = 'REVIEW', 'Review'
        COMBINED = 'COMBINED', 'Combined OP + Review'
        FUTURE_PATIENT = 'FUTURE_PATIENT', 'Future Patient'

    class StatusChoices(models.TextChoices):
        IDLE = 'IDLE', 'IDLE'
        DRAFT = 'DRAFT', 'DRAFT'
        PENDING = 'PENDING', 'PENDING'
        READY = 'READY', 'READY'
        STARTING = 'STARTING', 'STARTING'
        RUNNING = 'RUNNING', 'RUNNING'
        STOP_REQUESTED = 'STOP_REQUESTED', 'STOP_REQUESTED'
        STOPPED = 'STOPPED', 'STOPPED'
        EMERGENCY_STOPPED = 'EMERGENCY_STOPPED', 'EMERGENCY STOPPED'
        COMPLETED = 'COMPLETED', 'COMPLETED'
        FAILED = 'FAILED', 'FAILED'

    job_id = models.CharField(max_length=50, unique=True, db_index=True)
    plan = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='execution_jobs')
    automation_date = models.DateField(null=True, blank=True, db_index=True)
    mode = models.CharField(max_length=20, choices=ModeChoices.choices, default=ModeChoices.COMBINED)
    department = models.ForeignKey('patients.Department', on_delete=models.SET_NULL, null=True, blank=True)
    source_from_year = models.PositiveIntegerField(default=2022)
    source_to_year = models.PositiveIntegerField(default=2024)
    review_source_year = models.PositiveIntegerField(default=2024, null=True, blank=True)

    source_data_period = models.CharField(max_length=50, default='2024 – 2025')
    operation_signal = models.CharField(max_length=20, default='ALL')  # REVIEW, OP, ALL

    target_total = models.PositiveIntegerField(default=0)
    target_male = models.PositiveIntegerField(default=0)
    target_female = models.PositiveIntegerField(default=0)
    child_target = models.PositiveIntegerField(default=0)

    # Percentage allocation
    op_daily_pct = models.PositiveIntegerField(default=75)
    review_pct = models.PositiveIntegerField(default=25)
    target_op = models.PositiveIntegerField(default=0)
    target_review = models.PositiveIntegerField(default=0)

    # Multi-Department Configuration & Daily Targets
    plan_departments = models.JSONField(default=list, blank=True)
    daily_targets = models.JSONField(default=dict, blank=True)
    is_locked = models.BooleanField(default=False)

    created_op = models.PositiveIntegerField(default=0)
    created_review = models.PositiveIntegerField(default=0)

    schedule_start_time = models.TimeField(default='08:00:00')
    schedule_end_time = models.TimeField(default='14:00:00')
    batch_size = models.PositiveIntegerField(default=100)

    # For REVIEW or Date range
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.IDLE)
    current_batch = models.PositiveIntegerField(default=0)
    total_batches = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    created_male = models.PositiveIntegerField(default=0)
    created_female = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    current_patient_info = models.CharField(max_length=255, blank=True, default='')
    error_summary = models.TextField(blank=True, default='')
    stop_reason = models.CharField(max_length=255, blank=True, default='')
    stop_requested = models.BooleanField(default=False)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['automation_date', 'status']),
            models.Index(fields=['plan', 'automation_date']),
        ]

    def __str__(self):
        return f"{self.job_id} ({self.mode}) - {self.status}"

    @property
    def remaining_count(self):
        return max(0, self.target_total - self.created_count)

    @property
    def progress_percentage(self):
        if self.target_total == 0:
            return 100 if self.status == self.StatusChoices.COMPLETED else 0
        return min(100, int((self.created_count / self.target_total) * 100))


class ATCJobLog(TimeStampedModel):
    STATUS_CHOICES = (
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Skipped', 'Skipped'),
    )
    job = models.ForeignKey(ATCJob, on_delete=models.CASCADE, related_name='logs')
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='atc_logs')
    visit = models.ForeignKey('patients.PatientVisit', on_delete=models.SET_NULL, null=True, blank=True, related_name='atc_logs')
    source_patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    patient_name = models.CharField(max_length=150, blank=True, default='')
    gender = models.CharField(max_length=10, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    batch_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Success')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"ATC Log [{self.job.job_id}] - {self.patient_name} ({self.status})"


# ===========================================================================
# INVESTIGATION MARKING MODULE MODELS
# ===========================================================================

class InvestigationMarkingConfig(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SAVED = 'SAVED', 'Saved'
        TRIGGERED = 'TRIGGERED', 'Triggered'
        COMPLETED = 'COMPLETED', 'Completed'

    marking_date = models.DateField(unique=True, db_index=True, verbose_name="Marking Date")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT)
    total_male = models.PositiveIntegerField(default=0)
    total_female = models.PositiveIntegerField(default=0)
    total_patients = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-marking_date']
        verbose_name = "Investigation Marking Config"
        verbose_name_plural = "Investigation Marking Configs"

    def __str__(self):
        return f"Marking Config ({self.marking_date}) - {self.status}"


class InvestigationMarkingDepartment(TimeStampedModel):
    config = models.ForeignKey(InvestigationMarkingConfig, on_delete=models.CASCADE, related_name='departments')
    department = models.ForeignKey('patients.Department', on_delete=models.CASCADE)
    department_name = models.CharField(max_length=150)
    male_count = models.PositiveIntegerField(default=0)
    female_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('config', 'department')
        ordering = ['id']

    def __str__(self):
        return f"{self.config.marking_date} - {self.department_name} ({self.total_count})"


class InvestigationMarkingPatient(TimeStampedModel):
    config = models.ForeignKey(InvestigationMarkingConfig, on_delete=models.CASCADE, related_name='selected_patients')
    department = models.ForeignKey('patients.Department', on_delete=models.SET_NULL, null=True, blank=True)
    department_name = models.CharField(max_length=150)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE)
    patient_id_str = models.CharField(max_length=50)
    patient_name = models.CharField(max_length=150)
    age_display = models.CharField(max_length=20)
    gender = models.CharField(max_length=10)
    primary_diagnosis = models.ForeignKey('lab.Diagnosis', on_delete=models.SET_NULL, null=True, blank=True)
    primary_diagnosis_name = models.CharField(max_length=255, blank=True, default='')
    investigations_count = models.PositiveIntegerField(default=0)
    investigations_summary = models.CharField(max_length=255, blank=True, default='')
    service_request = models.ForeignKey('lab.ServiceRequest', on_delete=models.SET_NULL, null=True, blank=True)
    is_triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    completion_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('config', 'patient')
        ordering = ['id']

    def __str__(self):
        return f"{self.patient_id_str} - {self.patient_name} ({self.department_name})"

