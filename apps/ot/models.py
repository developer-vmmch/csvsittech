"""
apps/ot/models.py
Operation Theatre module models for VMMC ERP.
Integrates with existing Patient, PatientVisit, Diagnosis and User models.
"""
import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient, PatientVisit, Department
from apps.lab.models import Diagnosis


# ---------------------------------------------------------------------------
# OT MASTER MODELS
# ---------------------------------------------------------------------------

class OTRoom(TimeStampedModel):
    """Physical OT rooms available for scheduling."""

    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        UNDER_MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'

    code = models.CharField(max_length=20, unique=True, verbose_name="OT Code")
    name = models.CharField(max_length=100, verbose_name="OT Name")
    location = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    equipment_notes = models.TextField(blank=True, null=True, verbose_name="Equipment Notes")

    class Meta:
        ordering = ['code']
        verbose_name = "OT Room"
        verbose_name_plural = "OT Rooms"

    def __str__(self):
        return f"{self.code} — {self.name}"


class OTProcedure(TimeStampedModel):
    """Surgical procedure master data."""

    code = models.CharField(max_length=30, unique=True, verbose_name="Procedure Code")
    name = models.CharField(max_length=200, verbose_name="Procedure Name")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_procedures')
    avg_duration_min = models.PositiveIntegerField(default=60, verbose_name="Average Duration (minutes)")
    default_room = models.ForeignKey(OTRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_procedures')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = "OT Procedure"
        verbose_name_plural = "OT Procedures"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ---------------------------------------------------------------------------
# OT CASE — CENTRAL OBJECT
# ---------------------------------------------------------------------------

class OTCase(TimeStampedModel):
    """Central OT Case record representing one surgical episode."""

    class CaseTypeChoices(models.TextChoices):
        ELECTIVE = 'ELECTIVE', 'Elective'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class PriorityChoices(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        URGENT = 'URGENT', 'Urgent'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class StatusChoices(models.TextChoices):
        BOOKED = 'BOOKED', 'Booked'
        PRE_OP = 'PRE_OP', 'Pre-Op'
        CONSENT_PENDING = 'CONSENT_PENDING', 'Consent Pending'
        CONSENT_OBTAINED = 'CONSENT_OBTAINED', 'Consent Obtained'
        PAC_PENDING = 'PAC_PENDING', 'PAC Pending'
        PAC_DONE = 'PAC_DONE', 'PAC Done'
        SITE_MARKED = 'SITE_MARKED', 'Site Marked'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        SHIFTED_TO_OT = 'SHIFTED_TO_OT', 'Shifted to OT'
        SIGN_IN = 'SIGN_IN', 'Sign In'
        ANESTHESIA = 'ANESTHESIA', 'Anesthesia'
        TIME_OUT = 'TIME_OUT', 'Time Out'
        SURGERY_IN_PROGRESS = 'SURGERY_IN_PROGRESS', 'Surgery In Progress'
        SIGN_OUT = 'SIGN_OUT', 'Sign Out'
        SURGERY_COMPLETED = 'SURGERY_COMPLETED', 'Surgery Completed'
        OUTCOME_RECORDED = 'OUTCOME_RECORDED', 'Outcome Recorded'
        RECOVERY = 'RECOVERY', 'Recovery'
        WARD = 'WARD', 'Ward'
        ICU = 'ICU', 'ICU'
        CLOSED = 'CLOSED', 'Closed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    ot_number = models.CharField(max_length=30, unique=True, verbose_name="OT Number")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='ot_cases')
    ip_admission = models.ForeignKey(
        PatientVisit, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ot_cases', verbose_name="IP Admission"
    )
    diagnosis = models.ForeignKey(
        Diagnosis, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_cases'
    )
    procedure = models.ForeignKey(OTProcedure, on_delete=models.PROTECT, related_name='ot_cases')
    case_type = models.CharField(max_length=20, choices=CaseTypeChoices.choices, default=CaseTypeChoices.ELECTIVE)
    priority = models.CharField(max_length=20, choices=PriorityChoices.choices, default=PriorityChoices.NORMAL)
    status = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.BOOKED)

    # Surgical team
    surgeon = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='ot_cases_as_surgeon', verbose_name="Surgeon"
    )
    assistant_surgeon = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ot_cases_as_assistant', verbose_name="Assistant Surgeon"
    )
    anesthetist = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ot_cases_as_anesthetist', verbose_name="Anesthetist"
    )

    # Room & time
    ot_room = models.ForeignKey(OTRoom, on_delete=models.PROTECT, related_name='ot_cases', verbose_name="OT Room")
    preferred_date = models.DateField(default=datetime.date.today, verbose_name="Preferred Date")
    expected_start = models.TimeField(null=True, blank=True, verbose_name="Expected Start Time")
    expected_duration_min = models.PositiveIntegerField(default=60, verbose_name="Expected Duration (min)")

    # Emergency-specific
    emergency_reason = models.TextField(blank=True, null=True, verbose_name="Emergency Reason")
    is_mlc = models.BooleanField(default=False, verbose_name="MLC Case")
    mlc_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="MLC Number")
    police_intimation = models.BooleanField(default=False, verbose_name="Police Intimated")
    police_intimation_time = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_ot_cases', verbose_name="Created By"
    )
    is_demo = models.BooleanField(default=False, verbose_name="Demo/Test Record")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "OT Case"
        verbose_name_plural = "OT Cases"

    def __str__(self):
        return f"{self.ot_number} — {self.patient.name}"

    @classmethod
    def generate_ot_number(cls):
        year = datetime.date.today().year
        prefix = f"OT-{year}-"
        last = cls.objects.filter(ot_number__startswith=prefix).order_by('-ot_number').first()
        if last:
            try:
                seq = int(last.ot_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:05d}"

    @property
    def is_emergency(self):
        return self.case_type == self.CaseTypeChoices.EMERGENCY

    @property
    def can_transition_to(self):
        """Returns the set of valid next statuses from current status."""
        S = self.StatusChoices
        transitions = {
            S.BOOKED: [S.PRE_OP, S.CANCELLED],
            S.PRE_OP: [S.CONSENT_PENDING, S.CONSENT_OBTAINED, S.CANCELLED],
            S.CONSENT_PENDING: [S.CONSENT_OBTAINED, S.CANCELLED],
            S.CONSENT_OBTAINED: [S.PAC_PENDING, S.PAC_DONE, S.CANCELLED],
            S.PAC_PENDING: [S.PAC_DONE, S.CANCELLED],
            S.PAC_DONE: [S.SITE_MARKED, S.SCHEDULED, S.CANCELLED],
            S.SITE_MARKED: [S.SCHEDULED, S.CANCELLED],
            S.SCHEDULED: [S.SHIFTED_TO_OT, S.CANCELLED],
            S.SHIFTED_TO_OT: [S.SIGN_IN],
            S.SIGN_IN: [S.TIME_OUT],
            S.TIME_OUT: [S.SURGERY_IN_PROGRESS],
            S.SURGERY_IN_PROGRESS: [S.SIGN_OUT],
            S.SIGN_OUT: [S.SURGERY_COMPLETED],
            S.SURGERY_COMPLETED: [S.OUTCOME_RECORDED],
            S.OUTCOME_RECORDED: [S.RECOVERY, S.WARD, S.ICU, S.CLOSED],
            S.RECOVERY: [S.WARD, S.ICU, S.CLOSED],
            S.WARD: [S.CLOSED],
            S.ICU: [S.WARD, S.CLOSED],
        }
        return transitions.get(self.status, [])

    def transition(self, new_status, user, remarks=''):
        """Perform a status transition with history logging."""
        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        OTStatusHistory.objects.create(
            ot_case=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            remarks=remarks,
        )

    def get_status_display_class(self):
        """Returns a CSS class name for the status badge."""
        classes = {
            'BOOKED': 'badge-blue',
            'PRE_OP': 'badge-purple',
            'CONSENT_PENDING': 'badge-orange',
            'CONSENT_OBTAINED': 'badge-teal',
            'PAC_PENDING': 'badge-orange',
            'PAC_DONE': 'badge-teal',
            'SITE_MARKED': 'badge-teal',
            'SCHEDULED': 'badge-blue',
            'SHIFTED_TO_OT': 'badge-indigo',
            'SIGN_IN': 'badge-indigo',
            'ANESTHESIA': 'badge-indigo',
            'TIME_OUT': 'badge-indigo',
            'SURGERY_IN_PROGRESS': 'badge-yellow',
            'SIGN_OUT': 'badge-green',
            'SURGERY_COMPLETED': 'badge-green',
            'OUTCOME_RECORDED': 'badge-green',
            'RECOVERY': 'badge-teal',
            'WARD': 'badge-teal',
            'ICU': 'badge-red',
            'CLOSED': 'badge-gray',
            'CANCELLED': 'badge-red',
        }
        return classes.get(self.status, 'badge-gray')


class OTStatusHistory(models.Model):
    """Immutable audit trail of every OT Case status change."""
    ot_case = models.ForeignKey(OTCase, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['changed_at']
        verbose_name = "OT Status History"
        verbose_name_plural = "OT Status Histories"

    def __str__(self):
        return f"{self.ot_case.ot_number}: {self.from_status} → {self.to_status}"


# ---------------------------------------------------------------------------
# PRE-OP
# ---------------------------------------------------------------------------

class OTPreOp(TimeStampedModel):
    """Pre-operative checklist, consent, PAC, and site marking."""

    class ConsentStatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        OBTAINED = 'OBTAINED', 'Obtained'
        REFUSED = 'REFUSED', 'Refused'

    class ConsentModeChoices(models.TextChoices):
        STANDARD = 'STANDARD', 'Standard (Written)'
        VERBAL = 'VERBAL', 'Verbal / Telephonic'
        LIFE_SAVING = 'LIFE_SAVING', 'Life-Saving / Unable to Obtain'

    class PACStatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        DONE = 'DONE', 'Done'
        NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'

    class PACModeChoices(models.TextChoices):
        STANDARD = 'STANDARD', 'Standard'
        CRASH = 'CRASH', 'Crash PAC (Emergency)'

    class ASAGradeChoices(models.TextChoices):
        I = 'I', 'ASA I — Healthy'
        II = 'II', 'ASA II — Mild Systemic Disease'
        III = 'III', 'ASA III — Severe Systemic Disease'
        IV = 'IV', 'ASA IV — Life-threatening'
        V = 'V', 'ASA V — Moribund'
        E = 'E', 'ASA E — Emergency'

    class PACFitnessChoices(models.TextChoices):
        FIT = 'FIT', 'Fit'
        FIT_WITH_CONDITIONS = 'FIT_CONDITIONS', 'Fit with Conditions'
        NOT_FIT = 'NOT_FIT', 'Not Fit'

    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='preop')

    # Diet / NPO
    npo_given = models.BooleanField(default=False, verbose_name="NPO Instructions Given")
    npo_from = models.DateTimeField(null=True, blank=True, verbose_name="NPO From")

    # Consent
    consent_status = models.CharField(max_length=20, choices=ConsentStatusChoices.choices, default=ConsentStatusChoices.PENDING)
    consent_mode = models.CharField(max_length=20, choices=ConsentModeChoices.choices, default=ConsentModeChoices.STANDARD)
    consent_signed_by = models.CharField(max_length=100, blank=True, null=True)
    consent_relation = models.CharField(max_length=50, blank=True, null=True)
    consent_time = models.DateTimeField(null=True, blank=True)
    consent_witness = models.CharField(max_length=100, blank=True, null=True, verbose_name="Witness (Verbal/LS)")
    consent_life_saving_reason = models.TextField(blank=True, null=True)
    consent_consultant_1 = models.CharField(max_length=100, blank=True, null=True)
    consent_consultant_2 = models.CharField(max_length=100, blank=True, null=True)

    # PAC
    pac_status = models.CharField(max_length=20, choices=PACStatusChoices.choices, default=PACStatusChoices.PENDING)
    pac_mode = models.CharField(max_length=20, choices=PACModeChoices.choices, default=PACModeChoices.STANDARD)
    pac_done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pac_done', verbose_name="PAC Done By"
    )
    pac_date = models.DateTimeField(null=True, blank=True)
    asa_grade = models.CharField(max_length=5, choices=ASAGradeChoices.choices, blank=True, null=True)
    pac_fitness = models.CharField(max_length=20, choices=PACFitnessChoices.choices, blank=True, null=True)
    pac_remarks = models.TextField(blank=True, null=True)

    # Site marking
    site_marked = models.BooleanField(default=False)
    site_not_applicable = models.BooleanField(default=False, verbose_name="Site Marking N/A")
    site_na_reason = models.CharField(max_length=200, blank=True, null=True)
    site_description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Site")
    site_marked_by = models.CharField(max_length=100, blank=True, null=True)
    site_marked_at = models.DateTimeField(null=True, blank=True)

    # Blood arrangement
    blood_required = models.BooleanField(default=False)
    blood_arranged = models.BooleanField(default=False)
    blood_units = models.PositiveIntegerField(default=0)

    remarks = models.TextField(blank=True, null=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='preop_completed'
    )

    class Meta:
        verbose_name = "OT Pre-Op"

    def __str__(self):
        return f"Pre-Op for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# SCHEDULING
# ---------------------------------------------------------------------------

class OTSchedule(TimeStampedModel):
    """Scheduling record — when the case is formally slotted in an OT room."""
    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='schedule')
    room = models.ForeignKey(OTRoom, on_delete=models.PROTECT, related_name='schedules')
    scheduled_date = models.DateField()
    scheduled_start = models.TimeField()
    scheduled_end = models.TimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    # Conflict override (emergency)
    override_conflict = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True, null=True)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_overrides'
    )
    override_at = models.DateTimeField(null=True, blank=True)
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_schedules'
    )

    class Meta:
        verbose_name = "OT Schedule"

    def __str__(self):
        return f"Schedule: {self.ot_case.ot_number} on {self.scheduled_date}"


# ---------------------------------------------------------------------------
# WHO CHECKLISTS
# ---------------------------------------------------------------------------

class OTChecklist(TimeStampedModel):
    """Sign-In, Time-Out, and Sign-Out WHO-style safety checklists."""
    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='checklist')

    # Sign In
    sign_in_done = models.BooleanField(default=False)
    sign_in_data = models.JSONField(default=dict, blank=True)
    sign_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sign_in_completed'
    )
    sign_in_at = models.DateTimeField(null=True, blank=True)

    # Time Out
    time_out_done = models.BooleanField(default=False)
    time_out_data = models.JSONField(default=dict, blank=True)
    time_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='timeout_completed'
    )
    time_out_at = models.DateTimeField(null=True, blank=True)

    # Sign Out
    sign_out_done = models.BooleanField(default=False)
    sign_out_data = models.JSONField(default=dict, blank=True)
    sign_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='signout_completed'
    )
    sign_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "OT Checklist"

    def __str__(self):
        return f"Checklist for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# ANESTHESIA
# ---------------------------------------------------------------------------

class OTAnesthesia(TimeStampedModel):
    """Anesthesia record for a case."""

    class TypeChoices(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        SPINAL = 'SPINAL', 'Spinal'
        EPIDURAL = 'EPIDURAL', 'Epidural'
        REGIONAL = 'REGIONAL', 'Regional'
        LOCAL = 'LOCAL', 'Local'
        SEDATION = 'SEDATION', 'Sedation'
        OTHER = 'OTHER', 'Other'

    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='anesthesia')
    anesthesia_type = models.CharField(max_length=20, choices=TypeChoices.choices)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    pre_bp = models.CharField(max_length=20, blank=True, null=True, verbose_name="Pre-op BP")
    pre_pulse = models.CharField(max_length=20, blank=True, null=True, verbose_name="Pre-op Pulse")
    pre_spo2 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Pre-op SpO2")
    post_bp = models.CharField(max_length=20, blank=True, null=True, verbose_name="Post-op BP")
    post_pulse = models.CharField(max_length=20, blank=True, null=True, verbose_name="Post-op Pulse")
    post_spo2 = models.CharField(max_length=20, blank=True, null=True, verbose_name="Post-op SpO2")

    airway_notes = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='anesthesia_records'
    )

    class Meta:
        verbose_name = "OT Anesthesia"

    def __str__(self):
        return f"Anesthesia for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# OPERATION NOTES
# ---------------------------------------------------------------------------

class OTOperation(TimeStampedModel):
    """Intraoperative record and operation notes."""

    class OutcomeChoices(models.TextChoices):
        SUCCESSFUL = 'SUCCESSFUL', 'Successful'
        COMPLICATION = 'COMPLICATION', 'Complication'
        MODIFIED = 'MODIFIED', 'Procedure Modified'
        ABORTED = 'ABORTED', 'Procedure Aborted'
        INTRAOPERATIVE_DEATH = 'INTRAOPERATIVE_DEATH', 'Intraoperative Death'

    class ProcedureStatusChoices(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completed'
        MODIFIED = 'MODIFIED', 'Modified'
        ABORTED = 'ABORTED', 'Aborted'

    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='operation')
    preoperative_diagnosis = models.TextField(blank=True, null=True)
    postoperative_diagnosis = models.TextField(blank=True, null=True)
    procedure_performed = models.TextField(blank=True, null=True)

    incision_time = models.DateTimeField(null=True, blank=True)
    closure_time = models.DateTimeField(null=True, blank=True)

    findings = models.TextField(blank=True, null=True)
    procedure_details = models.TextField(blank=True, null=True)
    estimated_blood_loss_ml = models.PositiveIntegerField(null=True, blank=True, verbose_name="EBL (ml)")
    fluids = models.TextField(blank=True, null=True)
    medications_summary = models.TextField(blank=True, null=True)
    drain_placed = models.BooleanField(default=False)
    drain_details = models.CharField(max_length=200, blank=True, null=True)
    implants = models.TextField(blank=True, null=True)

    procedure_status = models.CharField(max_length=20, choices=ProcedureStatusChoices.choices, default=ProcedureStatusChoices.COMPLETED)
    outcome = models.CharField(max_length=30, choices=OutcomeChoices.choices, blank=True, null=True)

    complications = models.TextField(blank=True, null=True)
    complication_action = models.TextField(blank=True, null=True, verbose_name="Action Taken")

    # Intraoperative death
    death_cause = models.TextField(blank=True, null=True, verbose_name="Cause of Death")
    certifying_doctor = models.CharField(max_length=150, blank=True, null=True)
    death_remarks = models.TextField(blank=True, null=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='operation_notes'
    )

    class Meta:
        verbose_name = "OT Operation Notes"

    def __str__(self):
        return f"Operation for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# SPECIMEN
# ---------------------------------------------------------------------------

class OTSpecimen(TimeStampedModel):
    """Specimens collected during surgery."""

    class StatusChoices(models.TextChoices):
        COLLECTED = 'COLLECTED', 'Collected'
        SENT = 'SENT', 'Sent to Lab'
        RESULT_PENDING = 'RESULT_PENDING', 'Result Pending'
        RESULT_RECEIVED = 'RESULT_RECEIVED', 'Result Received'

    ot_case = models.ForeignKey(OTCase, on_delete=models.CASCADE, related_name='specimens')
    specimen_name = models.CharField(max_length=200, verbose_name="Specimen Name")
    specimen_type = models.CharField(max_length=100, blank=True, null=True)
    destination = models.CharField(max_length=100, default='Pathology', verbose_name="Sent To")
    collected_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    result_received_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.COLLECTED)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "OT Specimen"

    def __str__(self):
        return f"Specimen: {self.specimen_name} for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# DISPOSITION & TRANSFER
# ---------------------------------------------------------------------------

class OTDisposition(TimeStampedModel):
    """Where the patient goes after surgery."""

    class DispositionChoices(models.TextChoices):
        RECOVERY = 'RECOVERY', 'Recovery Room'
        WARD = 'WARD', 'Ward'
        ICU = 'ICU', 'ICU'
        OTHER = 'OTHER', 'Other'

    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='disposition')
    disposition = models.CharField(max_length=20, choices=DispositionChoices.choices)
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ward/ICU/Room")
    shifted_at = models.DateTimeField(default=timezone.now)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_dispositions'
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "OT Disposition"

    def __str__(self):
        return f"Disposition for {self.ot_case.ot_number}: {self.disposition}"


class OTTransfer(TimeStampedModel):
    """Transfer history record — every move after surgery."""
    ot_case = models.ForeignKey(OTCase, on_delete=models.CASCADE, related_name='transfers')
    from_location = models.CharField(max_length=100)
    to_location = models.CharField(max_length=100)
    transfer_time = models.DateTimeField(default=timezone.now)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_transfers'
    )
    reason = models.CharField(max_length=200, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['transfer_time']
        verbose_name = "OT Transfer"

    def __str__(self):
        return f"Transfer: {self.from_location} → {self.to_location} ({self.ot_case.ot_number})"


# ---------------------------------------------------------------------------
# POST-OP
# ---------------------------------------------------------------------------

class OTPostOp(TimeStampedModel):
    """Post-operative care notes."""
    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='postop')
    vitals_notes = models.TextField(blank=True, null=True)
    pain_score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Pain Score (0-10)")
    wound_status = models.TextField(blank=True, null=True)
    drain_output = models.TextField(blank=True, null=True)
    urine_output = models.TextField(blank=True, null=True)
    diet_instructions = models.TextField(blank=True, null=True)
    medication_instructions = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='postop_records'
    )

    class Meta:
        verbose_name = "OT Post-Op"

    def __str__(self):
        return f"Post-Op for {self.ot_case.ot_number}"


# ---------------------------------------------------------------------------
# FINAL CLOSURE
# ---------------------------------------------------------------------------

class OTClosure(TimeStampedModel):
    """Final case closure record."""

    class FinalStatusChoices(models.TextChoices):
        DISCHARGED = 'DISCHARGED', 'Discharged'
        DECEASED = 'DECEASED', 'Deceased'

    ot_case = models.OneToOneField(OTCase, on_delete=models.CASCADE, related_name='closure')
    final_closure = models.CharField(max_length=20, choices=FinalStatusChoices.choices)
    closed_at = models.DateTimeField(default=timezone.now)

    # Deceased
    cause_of_death = models.TextField(blank=True, null=True)
    certifying_doctor = models.CharField(max_length=150, blank=True, null=True)
    death_remarks = models.TextField(blank=True, null=True)

    # Discharged
    discharge_summary_reference = models.CharField(max_length=100, blank=True, null=True)
    follow_up = models.TextField(blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ot_closures'
    )

    class Meta:
        verbose_name = "OT Closure"

    def __str__(self):
        return f"Closure for {self.ot_case.ot_number}: {self.final_closure}"
