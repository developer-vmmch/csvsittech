"""
Management command: seed_ot_demo
Seeds demo OT Rooms, Procedures, and OT Cases for testing.
Idempotent — safe to run multiple times.
"""
import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.patients.models import Patient
from apps.lab.models import Diagnosis
from apps.users.models import User
from apps.ot.models import (
    OTRoom, OTProcedure, OTCase, OTStatusHistory,
    OTPreOp, OTSchedule, OTChecklist, OTAnesthesia,
    OTOperation, OTDisposition, OTPostOp
)


ROOMS = [
    ('OT-01', 'Major OT 1', '2nd Floor, Block A'),
    ('OT-02', 'Major OT 2', '2nd Floor, Block A'),
    ('OT-03', 'Emergency OT', '1st Floor, Emergency Block'),
    ('OT-04', 'Day Care OT', 'Ground Floor, Day Surgery Centre'),
]

PROCEDURES = [
    ('APPY', 'Appendectomy', 60),
    ('CHOLE', 'Laparoscopic Cholecystectomy', 90),
    ('HERNIA', 'Inguinal Hernioplasty', 75),
    ('LSCS', 'Lower Segment Caesarean Section', 60),
    ('THYROID', 'Total Thyroidectomy', 120),
    ('MASTECT', 'Modified Radical Mastectomy', 150),
    ('THR', 'Total Hip Replacement', 180),
    ('TURP', 'Transurethral Resection of Prostate', 90),
    ('FRACT', 'Open Reduction Internal Fixation', 120),
    ('LAPAROTOMY', 'Exploratory Laparotomy', 120),
]

STATUS_SCENARIOS = [
    OTCase.StatusChoices.BOOKED,
    OTCase.StatusChoices.PRE_OP,
    OTCase.StatusChoices.PAC_DONE,
    OTCase.StatusChoices.SCHEDULED,
    OTCase.StatusChoices.SURGERY_IN_PROGRESS,
    OTCase.StatusChoices.SURGERY_COMPLETED,
    OTCase.StatusChoices.OUTCOME_RECORDED,
    OTCase.StatusChoices.CLOSED,
]


class Command(BaseCommand):
    help = 'Seed demo OT data (rooms, procedures, cases). Idempotent.'

    def add_arguments(self, parser):
        parser.add_argument('--cases', type=int, default=8, help='Number of demo cases to create')
        parser.add_argument('--clear', action='store_true', help='Remove existing demo cases before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = OTCase.objects.filter(is_demo=True).delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted} demo cases.'))

        # ── ROOMS ──────────────────────────────────────────────────────────
        rooms_created = 0
        rooms = []
        for code, name, location in ROOMS:
            room, created = OTRoom.objects.get_or_create(code=code, defaults={'name': name, 'location': location})
            if created:
                rooms_created += 1
            rooms.append(room)
        self.stdout.write(f'  Rooms: {rooms_created} created, {len(rooms)} total')

        # ── PROCEDURES ──────────────────────────────────────────────────────
        procs_created = 0
        procedures = []
        for code, name, duration in PROCEDURES:
            proc, created = OTProcedure.objects.get_or_create(code=code, defaults={'name': name, 'avg_duration_min': duration})
            if created:
                procs_created += 1
            procedures.append(proc)
        self.stdout.write(f'  Procedures: {procs_created} created, {len(procedures)} total')

        # ── PREREQS ──────────────────────────────────────────────────────────
        # Get available patients (prefer IP patients, fallback to any)
        patients = list(Patient.objects.filter(visit_through='IP').order_by('?')[:30])
        if not patients:
            patients = list(Patient.objects.filter(is_active=True).order_by('?')[:30])
        if not patients:
            self.stdout.write(self.style.ERROR('No patients found. Cannot seed demo cases.'))
            return

        # Get users for surgeon/anesthetist
        users = list(User.objects.filter(is_active=True).order_by('?')[:10])
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Cannot seed demo cases.'))
            return

        # Get diagnoses
        diagnoses = list(Diagnosis.objects.filter(is_active=True)[:10])

        # ── CASES ────────────────────────────────────────────────────────────
        n = options['cases']
        cases_created = 0
        today = datetime.date.today()

        for i in range(n):
            patient = random.choice(patients)
            proc = random.choice(procedures)
            surgeon = random.choice(users)
            room = random.choice(rooms)
            status = STATUS_SCENARIOS[i % len(STATUS_SCENARIOS)]
            case_type = OTCase.CaseTypeChoices.EMERGENCY if i % 4 == 3 else OTCase.CaseTypeChoices.ELECTIVE
            priority = OTCase.PriorityChoices.EMERGENCY if case_type == OTCase.CaseTypeChoices.EMERGENCY else OTCase.PriorityChoices.NORMAL
            pref_date = today + datetime.timedelta(days=(i - 3))  # spread across days

            # Check for duplicate
            existing_count = OTCase.objects.filter(
                patient=patient, procedure=proc, preferred_date=pref_date, is_demo=True
            ).count()
            if existing_count > 0:
                patient = random.choice(patients)  # try different patient

            case = OTCase(
                patient=patient,
                procedure=proc,
                case_type=case_type,
                priority=priority,
                status=status,
                surgeon=surgeon,
                ot_room=room,
                preferred_date=pref_date,
                expected_start=datetime.time(8 + i % 8, 0),
                expected_duration_min=proc.avg_duration_min,
                emergency_reason='Demo emergency case' if case_type == 'EMERGENCY' else '',
                is_mlc=False,
                created_by=surgeon,
                is_demo=True,
                remarks=f'Demo case #{i+1} — generated by seed_ot_demo',
            )
            case.ot_number = OTCase.generate_ot_number()
            if diagnoses:
                case.diagnosis = random.choice(diagnoses)
            if len(users) > 1:
                case.anesthetist = random.choice([u for u in users if u != surgeon] or [None])

            case.save()
            cases_created += 1

            # Create initial history
            OTStatusHistory.objects.create(
                ot_case=case,
                from_status='',
                to_status=OTCase.StatusChoices.BOOKED,
                changed_by=surgeon,
                remarks='Demo booking created',
            )

            # Create sub-records based on status
            _create_sub_records(case, surgeon, room, pref_date, status)

        self.stdout.write(self.style.SUCCESS(
            f'\nOT Demo Seed Complete!\n'
            f'   Rooms: {len(rooms)} | Procedures: {len(procedures)} | Cases: {cases_created}\n'
            f'   Visit http://127.0.0.1:8001/ot/ to explore the module.'
        ))


def _create_sub_records(case, user, room, date, status):
    """Create sub-records appropriate to the case status."""
    S = OTCase.StatusChoices
    completed = [
        S.PAC_DONE, S.SITE_MARKED, S.SCHEDULED, S.SHIFTED_TO_OT,
        S.SIGN_IN, S.ANESTHESIA, S.TIME_OUT, S.SURGERY_IN_PROGRESS,
        S.SIGN_OUT, S.SURGERY_COMPLETED, S.OUTCOME_RECORDED,
        S.RECOVERY, S.WARD, S.ICU, S.CLOSED
    ]

    if status in [S.PRE_OP, S.CONSENT_PENDING, S.CONSENT_OBTAINED, S.PAC_PENDING, S.PAC_DONE,
                  S.SITE_MARKED] + completed:
        OTPreOp.objects.get_or_create(
            ot_case=case,
            defaults={
                'npo_given': True,
                'npo_from': timezone.now() - datetime.timedelta(hours=8),
                'consent_status': 'OBTAINED' if status in completed else 'PENDING',
                'consent_mode': 'STANDARD',
                'pac_status': 'DONE' if status in completed else 'PENDING',
                'pac_mode': 'STANDARD',
                'asa_grade': 'II',
                'pac_fitness': 'FIT',
                'site_marked': status in completed,
                'completed_by': user,
            }
        )

    if status in completed:
        OTSchedule.objects.get_or_create(
            ot_case=case,
            defaults={
                'room': room,
                'scheduled_date': date,
                'scheduled_start': datetime.time(8, 0),
                'scheduled_end': datetime.time(9, 30),
                'actual_start': timezone.make_aware(datetime.datetime.combine(date, datetime.time(8, 5))) if status in [
                    S.SURGERY_IN_PROGRESS, S.SIGN_OUT, S.SURGERY_COMPLETED,
                    S.OUTCOME_RECORDED, S.RECOVERY, S.WARD, S.ICU, S.CLOSED
                ] else None,
                'scheduled_by': user,
            }
        )

    if status in [S.SURGERY_COMPLETED, S.OUTCOME_RECORDED, S.RECOVERY, S.WARD, S.ICU, S.CLOSED]:
        OTOperation.objects.get_or_create(
            ot_case=case,
            defaults={
                'preoperative_diagnosis': case.diagnosis.name if case.diagnosis else 'As per case',
                'postoperative_diagnosis': case.diagnosis.name if case.diagnosis else 'Confirmed',
                'procedure_performed': case.procedure.name,
                'findings': 'Intraoperative findings consistent with diagnosis.',
                'procedure_details': 'Procedure performed as planned without complications.',
                'estimated_blood_loss_ml': random.choice([50, 100, 150, 200]),
                'fluids': 'RL 1000ml, NS 500ml',
                'outcome': 'SUCCESSFUL',
                'procedure_status': 'COMPLETED',
                'recorded_by': user,
            }
        )

    if status in [S.RECOVERY, S.WARD, S.ICU, S.CLOSED]:
        OTDisposition.objects.get_or_create(
            ot_case=case,
            defaults={
                'disposition': 'WARD' if status in [S.WARD, S.CLOSED] else 'RECOVERY',
                'location': 'Ward 4' if status in [S.WARD, S.CLOSED] else 'Recovery Room',
                'shifted_at': timezone.now() - datetime.timedelta(hours=2),
                'authorized_by': user,
            }
        )
