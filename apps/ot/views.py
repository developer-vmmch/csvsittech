"""
apps/ot/views.py
All views for the Operation Theatre module.
"""
import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db.models import Q, Count

from apps.patients.models import Patient, PatientVisit
from apps.lab.models import Diagnosis
from .models import (
    OTRoom, OTProcedure, OTCase, OTStatusHistory,
    OTPreOp, OTSchedule, OTChecklist, OTAnesthesia,
    OTOperation, OTSpecimen, OTDisposition, OTTransfer,
    OTPostOp, OTClosure
)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    today = datetime.date.today()
    qs = OTCase.objects.all()

    total_today = qs.filter(preferred_date=today).count()
    scheduled = qs.filter(preferred_date=today, status=OTCase.StatusChoices.SCHEDULED).count()
    in_progress = qs.filter(status=OTCase.StatusChoices.SURGERY_IN_PROGRESS).count()
    completed_today = qs.filter(preferred_date=today, status__in=[
        OTCase.StatusChoices.SURGERY_COMPLETED, OTCase.StatusChoices.OUTCOME_RECORDED,
        OTCase.StatusChoices.RECOVERY, OTCase.StatusChoices.WARD, OTCase.StatusChoices.ICU,
        OTCase.StatusChoices.CLOSED
    ]).count()
    emergency_today = qs.filter(preferred_date=today, case_type=OTCase.CaseTypeChoices.EMERGENCY).count()
    pending_consent = qs.filter(status=OTCase.StatusChoices.CONSENT_PENDING).count()
    pending_pac = qs.filter(status=OTCase.StatusChoices.PAC_PENDING).count()
    pending_preop = qs.filter(status=OTCase.StatusChoices.PRE_OP).count()

    today_cases = qs.filter(preferred_date=today).select_related(
        'patient', 'procedure', 'ot_room', 'surgeon'
    ).order_by('expected_start')

    rooms = OTRoom.objects.filter(status=OTRoom.StatusChoices.ACTIVE)

    context = {
        'page_title': 'OT Dashboard',
        'total_today': total_today,
        'scheduled': scheduled,
        'in_progress': in_progress,
        'completed_today': completed_today,
        'emergency_today': emergency_today,
        'pending_consent': pending_consent,
        'pending_pac': pending_pac,
        'pending_preop': pending_preop,
        'today_cases': today_cases,
        'today': today,
        'rooms': rooms,
    }
    return render(request, 'ot/dashboard.html', context)


# ─────────────────────────────────────────────
# BOOKING LIST
# ─────────────────────────────────────────────

@login_required
def booking_list(request):
    qs = OTCase.objects.select_related('patient', 'procedure', 'ot_room', 'surgeon').all()

    # Filters
    status_filter = request.GET.get('status', '')
    case_type_filter = request.GET.get('case_type', '')
    date_filter = request.GET.get('date', '')
    search = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if case_type_filter:
        qs = qs.filter(case_type=case_type_filter)
    if date_filter:
        try:
            d = datetime.date.fromisoformat(date_filter)
            qs = qs.filter(preferred_date=d)
        except ValueError:
            pass
    if search:
        qs = qs.filter(
            Q(ot_number__icontains=search) |
            Q(patient__name__icontains=search) |
            Q(patient__patient_id__icontains=search) |
            Q(procedure__name__icontains=search)
        )

    context = {
        'page_title': 'OT Booking',
        'cases': qs[:200],
        'status_choices': OTCase.StatusChoices.choices,
        'case_type_choices': OTCase.CaseTypeChoices.choices,
        'status_filter': status_filter,
        'case_type_filter': case_type_filter,
        'date_filter': date_filter,
        'search': search,
    }
    return render(request, 'ot/booking/list.html', context)


# ─────────────────────────────────────────────
# CREATE BOOKING
# ─────────────────────────────────────────────

@login_required
def booking_create(request):
    rooms = OTRoom.objects.filter(status=OTRoom.StatusChoices.ACTIVE)
    procedures = OTProcedure.objects.filter(is_active=True)
    surgeons = _get_surgeons()

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        ip_admission_id = request.POST.get('ip_admission_id')
        diagnosis_id = request.POST.get('diagnosis_id')
        procedure_id = request.POST.get('procedure_id')
        case_type = request.POST.get('case_type', 'ELECTIVE')
        priority = request.POST.get('priority', 'NORMAL')
        surgeon_id = request.POST.get('surgeon_id')
        assistant_id = request.POST.get('assistant_id')
        anesthetist_id = request.POST.get('anesthetist_id')
        room_id = request.POST.get('room_id')
        preferred_date = request.POST.get('preferred_date')
        expected_start = request.POST.get('expected_start')
        expected_duration = request.POST.get('expected_duration', 60)
        emergency_reason = request.POST.get('emergency_reason', '')
        is_mlc = request.POST.get('is_mlc') == 'on'
        mlc_number = request.POST.get('mlc_number', '')
        remarks = request.POST.get('remarks', '')

        # Validate required fields
        errors = []
        if not patient_id:
            errors.append("Patient is required.")
        if not procedure_id:
            errors.append("Procedure is required.")
        if not surgeon_id:
            errors.append("Surgeon is required.")
        if not room_id:
            errors.append("OT Room is required.")
        if not preferred_date:
            errors.append("Preferred date is required.")

        # Elective requires IP admission
        if case_type == 'ELECTIVE' and not ip_admission_id:
            errors.append("Elective cases require an active IP admission.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                patient = Patient.objects.get(patient_id=patient_id)
                procedure = OTProcedure.objects.get(pk=procedure_id)
                room = OTRoom.objects.get(pk=room_id)
                from apps.users.models import User
                surgeon = User.objects.get(pk=surgeon_id)

                case = OTCase(
                    patient=patient,
                    procedure=procedure,
                    case_type=case_type,
                    priority=priority,
                    surgeon=surgeon,
                    ot_room=room,
                    preferred_date=preferred_date,
                    emergency_reason=emergency_reason,
                    is_mlc=is_mlc,
                    mlc_number=mlc_number,
                    remarks=remarks,
                    created_by=request.user,
                    status=OTCase.StatusChoices.BOOKED,
                )
                case.ot_number = OTCase.generate_ot_number()

                if ip_admission_id:
                    case.ip_admission = PatientVisit.objects.get(pk=ip_admission_id)
                if diagnosis_id:
                    case.diagnosis = Diagnosis.objects.get(pk=diagnosis_id)
                if assistant_id:
                    case.assistant_surgeon = User.objects.get(pk=assistant_id)
                if anesthetist_id:
                    case.anesthetist = User.objects.get(pk=anesthetist_id)
                if expected_start:
                    case.expected_start = expected_start
                if expected_duration:
                    case.expected_duration_min = int(expected_duration)

                case.save()

                # Log initial status history
                OTStatusHistory.objects.create(
                    ot_case=case,
                    from_status='',
                    to_status=OTCase.StatusChoices.BOOKED,
                    changed_by=request.user,
                    remarks='Case created',
                )

                messages.success(request, f"OT Case {case.ot_number} booked successfully.")
                return redirect('ot:case_detail', pk=case.pk)
            except Exception as e:
                messages.error(request, f"Error creating booking: {e}")

    context = {
        'page_title': 'New OT Booking',
        'rooms': rooms,
        'procedures': procedures,
        'surgeons': surgeons,
        'today': datetime.date.today().isoformat(),
        'case_type_choices': OTCase.CaseTypeChoices.choices,
        'priority_choices': OTCase.PriorityChoices.choices,
    }
    return render(request, 'ot/booking/create.html', context)


# ─────────────────────────────────────────────
# CASE DETAIL
# ─────────────────────────────────────────────

@login_required
def case_detail(request, pk):
    case = get_object_or_404(
        OTCase.objects.select_related(
            'patient', 'procedure', 'ot_room', 'surgeon',
            'assistant_surgeon', 'anesthetist', 'diagnosis', 'ip_admission'
        ),
        pk=pk
    )
    history = case.status_history.select_related('changed_by').order_by('changed_at')

    # Sub-records (safe get)
    preop = getattr(case, 'preop', None)
    schedule = getattr(case, 'schedule', None)
    checklist = getattr(case, 'checklist', None)
    anesthesia = getattr(case, 'anesthesia', None)
    operation = getattr(case, 'operation', None)
    postop = getattr(case, 'postop', None)
    disposition = getattr(case, 'disposition', None)
    closure = getattr(case, 'closure', None)
    specimens = case.specimens.all()
    transfers = case.transfers.select_related('authorized_by').order_by('transfer_time')

    # Workflow steps with completion state
    steps = _get_workflow_steps(case)

    context = {
        'page_title': f'OT Case: {case.ot_number}',
        'case': case,
        'history': history,
        'preop': preop,
        'schedule': schedule,
        'checklist': checklist,
        'anesthesia': anesthesia,
        'operation': operation,
        'postop': postop,
        'disposition': disposition,
        'closure': closure,
        'specimens': specimens,
        'transfers': transfers,
        'steps': steps,
        'next_actions': _get_next_actions(case),
    }
    return render(request, 'ot/booking/detail.html', context)


# ─────────────────────────────────────────────
# PRE-OP FORM
# ─────────────────────────────────────────────

@login_required
def preop_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    preop, created = OTPreOp.objects.get_or_create(ot_case=case)

    if request.method == 'POST':
        preop.npo_given = request.POST.get('npo_given') == 'on'
        npo_from_str = request.POST.get('npo_from')
        if npo_from_str:
            try:
                preop.npo_from = datetime.datetime.fromisoformat(npo_from_str)
            except ValueError:
                pass

        preop.consent_status = request.POST.get('consent_status', 'PENDING')
        preop.consent_mode = request.POST.get('consent_mode', 'STANDARD')
        preop.consent_signed_by = request.POST.get('consent_signed_by', '')
        preop.consent_relation = request.POST.get('consent_relation', '')
        preop.consent_witness = request.POST.get('consent_witness', '')
        preop.consent_life_saving_reason = request.POST.get('consent_life_saving_reason', '')
        preop.consent_consultant_1 = request.POST.get('consent_consultant_1', '')
        preop.consent_consultant_2 = request.POST.get('consent_consultant_2', '')
        consent_time_str = request.POST.get('consent_time')
        if consent_time_str:
            try:
                preop.consent_time = datetime.datetime.fromisoformat(consent_time_str)
            except ValueError:
                pass

        preop.pac_status = request.POST.get('pac_status', 'PENDING')
        preop.pac_mode = request.POST.get('pac_mode', 'STANDARD')
        preop.asa_grade = request.POST.get('asa_grade', '')
        preop.pac_fitness = request.POST.get('pac_fitness', '')
        preop.pac_remarks = request.POST.get('pac_remarks', '')
        preop.pac_date = timezone.now() if preop.pac_status == 'DONE' else preop.pac_date
        preop.pac_done_by = request.user if preop.pac_status == 'DONE' else preop.pac_done_by

        preop.site_not_applicable = request.POST.get('site_not_applicable') == 'on'
        preop.site_na_reason = request.POST.get('site_na_reason', '')
        preop.site_marked = request.POST.get('site_marked') == 'on'
        preop.site_description = request.POST.get('site_description', '')
        if preop.site_marked and not preop.site_marked_at:
            preop.site_marked_at = timezone.now()
            preop.site_marked_by = request.user.get_full_name() or request.user.username

        preop.blood_required = request.POST.get('blood_required') == 'on'
        preop.blood_arranged = request.POST.get('blood_arranged') == 'on'
        blood_units = request.POST.get('blood_units', 0)
        preop.blood_units = int(blood_units) if blood_units else 0

        preop.remarks = request.POST.get('remarks', '')
        preop.completed_by = request.user
        preop.save()

        # Advance case status based on what was completed
        _auto_advance_from_preop(case, preop, request.user)

        messages.success(request, "Pre-Op record saved successfully.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Pre-Op — {case.ot_number}',
        'case': case,
        'preop': preop,
        'pac_status_choices': OTPreOp.PACStatusChoices.choices,
        'pac_mode_choices': OTPreOp.PACModeChoices.choices,
        'asa_choices': OTPreOp.ASAGradeChoices.choices,
        'fitness_choices': OTPreOp.PACFitnessChoices.choices,
        'consent_status_choices': OTPreOp.ConsentStatusChoices.choices,
        'consent_mode_choices': OTPreOp.ConsentModeChoices.choices,
    }
    return render(request, 'ot/preop/form.html', context)


# ─────────────────────────────────────────────
# SCHEDULE FORM
# ─────────────────────────────────────────────

@login_required
def schedule_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    sched, created = OTSchedule.objects.get_or_create(
        ot_case=case,
        defaults={'room': case.ot_room, 'scheduled_date': case.preferred_date, 'scheduled_start': datetime.time(8, 0)}
    )
    rooms = OTRoom.objects.filter(status=OTRoom.StatusChoices.ACTIVE)

    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        scheduled_date = request.POST.get('scheduled_date')
        scheduled_start = request.POST.get('scheduled_start')
        scheduled_end = request.POST.get('scheduled_end')
        override = request.POST.get('override_conflict') == 'on'
        override_reason = request.POST.get('override_reason', '')

        try:
            room = OTRoom.objects.get(pk=room_id)
            d = datetime.date.fromisoformat(scheduled_date)
            t_start = datetime.time.fromisoformat(scheduled_start)
            t_end = datetime.time.fromisoformat(scheduled_end) if scheduled_end else None

            # Conflict detection
            conflicts = _check_conflicts(room, d, t_start, t_end, exclude_case=case)

            if conflicts and not override:
                context = _schedule_context(case, sched, rooms)
                context['conflicts'] = conflicts
                context['post_data'] = request.POST
                return render(request, 'ot/schedule/view.html', context)

            sched.room = room
            sched.scheduled_date = d
            sched.scheduled_start = t_start
            sched.scheduled_end = t_end
            sched.scheduled_by = request.user

            if override and conflicts:
                sched.override_conflict = True
                sched.override_reason = override_reason
                sched.override_by = request.user
                sched.override_at = timezone.now()

            sched.save()

            # Update room on case too
            case.ot_room = room
            case.preferred_date = d
            case.expected_start = t_start
            case.save(update_fields=['ot_room', 'preferred_date', 'expected_start', 'updated_at'])

            # Transition to SCHEDULED
            if case.status not in [OTCase.StatusChoices.SCHEDULED, OTCase.StatusChoices.SHIFTED_TO_OT,
                                    OTCase.StatusChoices.SIGN_IN, OTCase.StatusChoices.TIME_OUT,
                                    OTCase.StatusChoices.SURGERY_IN_PROGRESS, OTCase.StatusChoices.SIGN_OUT,
                                    OTCase.StatusChoices.SURGERY_COMPLETED]:
                case.transition(OTCase.StatusChoices.SCHEDULED, request.user, 'OT scheduled')

            messages.success(request, f"OT scheduled for {scheduled_date} at {scheduled_start}.")
            return redirect('ot:case_detail', pk=case.pk)
        except Exception as e:
            messages.error(request, f"Error scheduling: {e}")

    context = _schedule_context(case, sched, rooms)
    return render(request, 'ot/schedule/view.html', context)


# ─────────────────────────────────────────────
# SHIFT TO OT
# ─────────────────────────────────────────────

@login_required
@require_POST
def shift_to_ot(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    if case.status == OTCase.StatusChoices.SCHEDULED:
        case.transition(OTCase.StatusChoices.SHIFTED_TO_OT, request.user, 'Patient shifted to OT')
        messages.success(request, "Patient shifted to OT.")
    else:
        messages.error(request, f"Cannot shift: current status is {case.status}")
    return redirect('ot:case_detail', pk=case.pk)


# ─────────────────────────────────────────────
# SIGN IN
# ─────────────────────────────────────────────

@login_required
def sign_in(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    checklist, _ = OTChecklist.objects.get_or_create(ot_case=case)

    SIGN_IN_ITEMS = [
        ('patient_identity', 'Patient identity confirmed'),
        ('procedure_confirmed', 'Procedure confirmed'),
        ('consent_confirmed', 'Consent confirmed'),
        ('site_confirmed', 'Site confirmed'),
        ('allergy_checked', 'Allergy checked'),
        ('airway_risk', 'Airway risk assessed'),
        ('blood_loss_risk', 'Blood loss risk assessed'),
        ('equipment_available', 'Equipment available'),
        ('anesthesia_machine', 'Anesthesia machine checked'),
    ]

    if request.method == 'POST':
        data = {}
        all_checked = True
        for key, label in SIGN_IN_ITEMS:
            checked = request.POST.get(key) == 'on'
            data[key] = checked
            if not checked:
                all_checked = False

        if not all_checked:
            messages.warning(request, "All Sign-In checklist items must be completed before proceeding.")
            context = {'case': case, 'checklist': checklist, 'items': SIGN_IN_ITEMS, 'post_data': request.POST, 'page_title': f'Sign In — {case.ot_number}'}
            return render(request, 'ot/operation/signin.html', context)

        checklist.sign_in_done = True
        checklist.sign_in_data = data
        checklist.sign_in_by = request.user
        checklist.sign_in_at = timezone.now()
        checklist.save()

        case.transition(OTCase.StatusChoices.SIGN_IN, request.user, 'Sign-In completed')
        messages.success(request, "Sign-In completed successfully.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Sign In — {case.ot_number}',
        'case': case,
        'checklist': checklist,
        'items': SIGN_IN_ITEMS,
        'existing_data': checklist.sign_in_data or {},
    }
    return render(request, 'ot/operation/signin.html', context)


# ─────────────────────────────────────────────
# ANESTHESIA
# ─────────────────────────────────────────────

@login_required
def anesthesia_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    anes, _ = OTAnesthesia.objects.get_or_create(ot_case=case)

    if request.method == 'POST':
        anes.anesthesia_type = request.POST.get('anesthesia_type', 'GENERAL')
        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')
        if start_str:
            try:
                anes.start_time = datetime.datetime.fromisoformat(start_str)
            except ValueError:
                pass
        if end_str:
            try:
                anes.end_time = datetime.datetime.fromisoformat(end_str)
            except ValueError:
                pass
        anes.pre_bp = request.POST.get('pre_bp', '')
        anes.pre_pulse = request.POST.get('pre_pulse', '')
        anes.pre_spo2 = request.POST.get('pre_spo2', '')
        anes.post_bp = request.POST.get('post_bp', '')
        anes.post_pulse = request.POST.get('post_pulse', '')
        anes.post_spo2 = request.POST.get('post_spo2', '')
        anes.airway_notes = request.POST.get('airway_notes', '')
        anes.remarks = request.POST.get('remarks', '')
        anes.recorded_by = request.user
        anes.save()

        # Advance to ANESTHESIA status if at SIGN_IN
        if case.status == OTCase.StatusChoices.SIGN_IN:
            case.transition(OTCase.StatusChoices.ANESTHESIA, request.user, 'Anesthesia started')

        messages.success(request, "Anesthesia record saved.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Anesthesia — {case.ot_number}',
        'case': case,
        'anes': anes,
        'type_choices': OTAnesthesia.TypeChoices.choices,
    }
    return render(request, 'ot/operation/anesthesia.html', context)


# ─────────────────────────────────────────────
# TIME OUT
# ─────────────────────────────────────────────

@login_required
def time_out(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    checklist, _ = OTChecklist.objects.get_or_create(ot_case=case)

    TIMEOUT_ITEMS = [
        ('patient_confirmed', 'Patient identity confirmed'),
        ('procedure_confirmed', 'Procedure confirmed'),
        ('site_confirmed', 'Surgical site confirmed'),
        ('surgeon_confirmed', 'Surgeon confirmed'),
        ('anesthesia_confirmed', 'Anesthesia confirmed'),
        ('nursing_confirmed', 'Nursing team confirmed'),
        ('antibiotic_checked', 'Antibiotic prophylaxis administered'),
        ('imaging_available', 'Imaging available'),
        ('blood_available', 'Blood available if required'),
    ]

    if request.method == 'POST':
        data = {}
        all_checked = True
        for key, label in TIMEOUT_ITEMS:
            checked = request.POST.get(key) == 'on'
            data[key] = checked
            if not checked:
                all_checked = False

        if not all_checked:
            messages.warning(request, "All Time-Out checklist items must be completed.")
            context = {'case': case, 'checklist': checklist, 'items': TIMEOUT_ITEMS, 'post_data': request.POST, 'page_title': f'Time Out — {case.ot_number}'}
            return render(request, 'ot/operation/timeout.html', context)

        checklist.time_out_done = True
        checklist.time_out_data = data
        checklist.time_out_by = request.user
        checklist.time_out_at = timezone.now()
        checklist.save()

        case.transition(OTCase.StatusChoices.TIME_OUT, request.user, 'Time-Out completed')
        messages.success(request, "Time-Out completed. Surgery can proceed.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Time Out — {case.ot_number}',
        'case': case,
        'checklist': checklist,
        'items': TIMEOUT_ITEMS,
        'existing_data': checklist.time_out_data or {},
    }
    return render(request, 'ot/operation/timeout.html', context)


# ─────────────────────────────────────────────
# START SURGERY
# ─────────────────────────────────────────────

@login_required
@require_POST
def start_surgery(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    if case.status in [OTCase.StatusChoices.TIME_OUT, OTCase.StatusChoices.ANESTHESIA]:
        # Record schedule actual start
        sched = getattr(case, 'schedule', None)
        if sched and not sched.actual_start:
            sched.actual_start = timezone.now()
            sched.save(update_fields=['actual_start'])
        case.transition(OTCase.StatusChoices.SURGERY_IN_PROGRESS, request.user, 'Surgery started')
        messages.success(request, "Surgery started. Good luck, team.")
    else:
        messages.error(request, f"Cannot start surgery from status: {case.status}")
    return redirect('ot:case_detail', pk=case.pk)


# ─────────────────────────────────────────────
# OPERATION NOTES
# ─────────────────────────────────────────────

@login_required
def operation_notes(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    op, _ = OTOperation.objects.get_or_create(ot_case=case)

    if request.method == 'POST':
        op.preoperative_diagnosis = request.POST.get('preoperative_diagnosis', '')
        op.postoperative_diagnosis = request.POST.get('postoperative_diagnosis', '')
        op.procedure_performed = request.POST.get('procedure_performed', '')
        op.findings = request.POST.get('findings', '')
        op.procedure_details = request.POST.get('procedure_details', '')
        ebl = request.POST.get('estimated_blood_loss_ml')
        op.estimated_blood_loss_ml = int(ebl) if ebl else None
        op.fluids = request.POST.get('fluids', '')
        op.medications_summary = request.POST.get('medications_summary', '')
        op.drain_placed = request.POST.get('drain_placed') == 'on'
        op.drain_details = request.POST.get('drain_details', '')
        op.implants = request.POST.get('implants', '')
        op.complications = request.POST.get('complications', '')
        op.complication_action = request.POST.get('complication_action', '')
        op.recorded_by = request.user

        incision_str = request.POST.get('incision_time')
        if incision_str:
            try:
                op.incision_time = datetime.datetime.fromisoformat(incision_str)
            except ValueError:
                pass
        op.save()

        # Handle specimen
        specimen_name = request.POST.get('specimen_name')
        if specimen_name:
            OTSpecimen.objects.create(
                ot_case=case,
                specimen_name=specimen_name,
                specimen_type=request.POST.get('specimen_type', ''),
                destination=request.POST.get('specimen_destination', 'Pathology'),
                collected_at=timezone.now(),
                status='COLLECTED',
            )

        messages.success(request, "Operation notes saved.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Operation Notes — {case.ot_number}',
        'case': case,
        'op': op,
        'specimens': case.specimens.all(),
    }
    return render(request, 'ot/operation/notes.html', context)


# ─────────────────────────────────────────────
# SIGN OUT
# ─────────────────────────────────────────────

@login_required
def sign_out(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    checklist, _ = OTChecklist.objects.get_or_create(ot_case=case)

    SIGNOUT_ITEMS = [
        ('procedure_recorded', 'Procedure recorded'),
        ('instrument_count', 'Instrument count correct'),
        ('sponge_count', 'Sponge count correct'),
        ('needle_count', 'Needle count correct'),
        ('specimen_labelled', 'Specimen labelled'),
        ('specimen_sent', 'Specimen sent (if applicable)'),
        ('equipment_issues', 'Equipment issues noted'),
        ('postop_communicated', 'Post-op plan communicated'),
    ]

    if request.method == 'POST':
        data = {}
        for key, label in SIGNOUT_ITEMS:
            data[key] = request.POST.get(key) == 'on'

        checklist.sign_out_done = True
        checklist.sign_out_data = data
        checklist.sign_out_by = request.user
        checklist.sign_out_at = timezone.now()
        checklist.save()

        # Record actual end
        closure_str = request.POST.get('closure_time')
        sched = getattr(case, 'schedule', None)
        if sched:
            if not sched.actual_end:
                sched.actual_end = timezone.now()
                sched.save(update_fields=['actual_end'])
        op = getattr(case, 'operation', None)
        if op and closure_str:
            try:
                op.closure_time = datetime.datetime.fromisoformat(closure_str)
                op.save(update_fields=['closure_time'])
            except ValueError:
                pass

        case.transition(OTCase.StatusChoices.SIGN_OUT, request.user, 'Sign-Out completed')
        messages.success(request, "Sign-Out completed.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Sign Out — {case.ot_number}',
        'case': case,
        'checklist': checklist,
        'items': SIGNOUT_ITEMS,
        'existing_data': checklist.sign_out_data or {},
    }
    return render(request, 'ot/operation/signout.html', context)


# ─────────────────────────────────────────────
# COMPLETE SURGERY
# ─────────────────────────────────────────────

@login_required
@require_POST
def complete_surgery(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    checklist = getattr(case, 'checklist', None)
    if not checklist or not checklist.sign_out_done:
        messages.error(request, "Sign-Out must be completed before marking surgery as complete.")
        return redirect('ot:case_detail', pk=case.pk)
    case.transition(OTCase.StatusChoices.SURGERY_COMPLETED, request.user, 'Surgery completed')
    messages.success(request, "Surgery marked as completed.")
    return redirect('ot:outcome_form', pk=case.pk)


# ─────────────────────────────────────────────
# OUTCOME
# ─────────────────────────────────────────────

@login_required
def outcome_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    op, _ = OTOperation.objects.get_or_create(ot_case=case)

    if request.method == 'POST':
        outcome = request.POST.get('outcome')
        op.outcome = outcome
        op.procedure_status = request.POST.get('procedure_status', 'COMPLETED')
        op.complications = request.POST.get('complications', '')
        op.complication_action = request.POST.get('complication_action', '')
        op.death_cause = request.POST.get('death_cause', '')
        op.certifying_doctor = request.POST.get('certifying_doctor', '')
        op.death_remarks = request.POST.get('death_remarks', '')
        op.save()

        case.transition(OTCase.StatusChoices.OUTCOME_RECORDED, request.user, f'Outcome: {outcome}')
        messages.success(request, "Outcome recorded.")
        return redirect('ot:disposition_form', pk=case.pk)

    context = {
        'page_title': f'Outcome — {case.ot_number}',
        'case': case,
        'op': op,
        'outcome_choices': OTOperation.OutcomeChoices.choices,
        'procedure_status_choices': OTOperation.ProcedureStatusChoices.choices,
    }
    return render(request, 'ot/operation/outcome.html', context)


# ─────────────────────────────────────────────
# DISPOSITION
# ─────────────────────────────────────────────

@login_required
def disposition_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    disp = getattr(case, 'disposition', None)

    if request.method == 'POST':
        disposition = request.POST.get('disposition')
        location = request.POST.get('location', '')
        remarks = request.POST.get('remarks', '')

        if disp is None:
            disp = OTDisposition(ot_case=case)
        disp.disposition = disposition
        disp.location = location
        disp.shifted_at = timezone.now()
        disp.authorized_by = request.user
        disp.remarks = remarks
        disp.save()

        # Advance status
        status_map = {
            'RECOVERY': OTCase.StatusChoices.RECOVERY,
            'WARD': OTCase.StatusChoices.WARD,
            'ICU': OTCase.StatusChoices.ICU,
        }
        new_status = status_map.get(disposition, OTCase.StatusChoices.RECOVERY)
        case.transition(new_status, request.user, f'Shifted to {disposition}')

        # Log transfer
        OTTransfer.objects.create(
            ot_case=case,
            from_location='OT',
            to_location=f"{disposition} — {location}",
            transfer_time=timezone.now(),
            authorized_by=request.user,
            reason='Post-surgery disposition',
        )

        messages.success(request, f"Patient disposition recorded: {disposition}.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Disposition — {case.ot_number}',
        'case': case,
        'disposition': disp,
        'disposition_choices': OTDisposition.DispositionChoices.choices,
    }
    return render(request, 'ot/postop/disposition.html', context)


# ─────────────────────────────────────────────
# POST-OP
# ─────────────────────────────────────────────

@login_required
def postop_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    postop, _ = OTPostOp.objects.get_or_create(ot_case=case)

    if request.method == 'POST':
        postop.vitals_notes = request.POST.get('vitals_notes', '')
        pain = request.POST.get('pain_score')
        postop.pain_score = int(pain) if pain else None
        postop.wound_status = request.POST.get('wound_status', '')
        postop.drain_output = request.POST.get('drain_output', '')
        postop.urine_output = request.POST.get('urine_output', '')
        postop.diet_instructions = request.POST.get('diet_instructions', '')
        postop.medication_instructions = request.POST.get('medication_instructions', '')
        fu_str = request.POST.get('follow_up_date')
        if fu_str:
            try:
                postop.follow_up_date = datetime.date.fromisoformat(fu_str)
            except ValueError:
                pass
        postop.remarks = request.POST.get('remarks', '')
        postop.recorded_by = request.user
        postop.save()

        messages.success(request, "Post-Op notes saved.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Post-Op — {case.ot_number}',
        'case': case,
        'postop': postop,
    }
    return render(request, 'ot/postop/form.html', context)


# ─────────────────────────────────────────────
# CLOSURE
# ─────────────────────────────────────────────

@login_required
def closure_form(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    closure = getattr(case, 'closure', None)

    if request.method == 'POST':
        final_closure = request.POST.get('final_closure')
        if not final_closure:
            messages.error(request, "Final closure status is required.")
            return redirect('ot:closure_form', pk=case.pk)

        if closure is None:
            closure = OTClosure(ot_case=case)
        closure.final_closure = final_closure
        closure.closed_at = timezone.now()
        closure.closed_by = request.user
        closure.remarks = request.POST.get('remarks', '')

        if final_closure == 'DECEASED':
            closure.cause_of_death = request.POST.get('cause_of_death', '')
            closure.certifying_doctor = request.POST.get('certifying_doctor', '')
            closure.death_remarks = request.POST.get('death_remarks', '')
        else:
            closure.discharge_summary_reference = request.POST.get('discharge_summary_reference', '')
            closure.follow_up = request.POST.get('follow_up', '')
        closure.save()

        case.transition(OTCase.StatusChoices.CLOSED, request.user, f'Case closed: {final_closure}')
        messages.success(request, f"Case {case.ot_number} closed successfully.")
        return redirect('ot:case_detail', pk=case.pk)

    context = {
        'page_title': f'Closure — {case.ot_number}',
        'case': case,
        'closure': closure,
        'closure_choices': OTClosure.FinalStatusChoices.choices,
    }
    return render(request, 'ot/postop/closure.html', context)


# ─────────────────────────────────────────────
# CANCEL
# ─────────────────────────────────────────────

@login_required
@require_POST
def cancel_case(request, pk):
    case = get_object_or_404(OTCase, pk=pk)
    reason = request.POST.get('cancel_reason', 'No reason given')
    if case.status in [OTCase.StatusChoices.CLOSED, OTCase.StatusChoices.CANCELLED,
                        OTCase.StatusChoices.SURGERY_IN_PROGRESS, OTCase.StatusChoices.SIGN_OUT,
                        OTCase.StatusChoices.SURGERY_COMPLETED]:
        messages.error(request, f"Cannot cancel a case in status: {case.status}")
    else:
        case.transition(OTCase.StatusChoices.CANCELLED, request.user, f'Cancelled: {reason}')
        messages.warning(request, f"Case {case.ot_number} cancelled.")
    return redirect('ot:case_detail', pk=case.pk)


# ─────────────────────────────────────────────
# SCHEDULE VIEW (Calendar/Timeline)
# ─────────────────────────────────────────────

@login_required
def schedule_view(request):
    date_str = request.GET.get('date', datetime.date.today().isoformat())
    try:
        selected_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        selected_date = datetime.date.today()

    rooms = OTRoom.objects.filter(status=OTRoom.StatusChoices.ACTIVE)
    schedules = OTSchedule.objects.filter(scheduled_date=selected_date).select_related(
        'ot_case', 'ot_case__patient', 'ot_case__procedure',
        'ot_case__surgeon', 'room'
    )

    # Group by room
    room_schedules = {}
    for room in rooms:
        room_schedules[room] = []
    for s in schedules:
        if s.room in room_schedules:
            room_schedules[s.room].append(s)

    # Unscheduled today's cases
    unscheduled = OTCase.objects.filter(
        preferred_date=selected_date,
        status=OTCase.StatusChoices.BOOKED
    ).select_related('patient', 'procedure', 'surgeon')

    context = {
        'page_title': 'OT Schedule',
        'selected_date': selected_date,
        'room_schedules': room_schedules,
        'unscheduled': unscheduled,
        'prev_date': (selected_date - datetime.timedelta(days=1)).isoformat(),
        'next_date': (selected_date + datetime.timedelta(days=1)).isoformat(),
    }
    return render(request, 'ot/schedule/view.html', context)


# ─────────────────────────────────────────────
# LIVE OT BOARD
# ─────────────────────────────────────────────

@login_required
def live_board(request):
    rooms = OTRoom.objects.filter(status=OTRoom.StatusChoices.ACTIVE)
    active_cases = OTCase.objects.filter(
        status__in=[
            OTCase.StatusChoices.SHIFTED_TO_OT,
            OTCase.StatusChoices.SIGN_IN,
            OTCase.StatusChoices.ANESTHESIA,
            OTCase.StatusChoices.TIME_OUT,
            OTCase.StatusChoices.SURGERY_IN_PROGRESS,
            OTCase.StatusChoices.SIGN_OUT,
        ]
    ).select_related('patient', 'procedure', 'ot_room', 'surgeon', 'anesthetist')

    # Map room → active case
    room_case_map = {}
    for case in active_cases:
        room_case_map[case.ot_room_id] = case

    room_data = []
    for room in rooms:
        room_data.append({
            'room': room,
            'case': room_case_map.get(room.pk),
        })

    context = {
        'page_title': 'Live OT Board',
        'room_data': room_data,
        'now': timezone.now(),
    }
    return render(request, 'ot/live/board.html', context)


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@login_required
def history_list(request):
    qs = OTCase.objects.select_related('patient', 'procedure', 'ot_room', 'surgeon').all()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status_filter = request.GET.get('status', '')
    case_type = request.GET.get('case_type', '')
    search = request.GET.get('q', '')

    if date_from:
        try:
            qs = qs.filter(preferred_date__gte=datetime.date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(preferred_date__lte=datetime.date.fromisoformat(date_to))
        except ValueError:
            pass
    if status_filter:
        qs = qs.filter(status=status_filter)
    if case_type:
        qs = qs.filter(case_type=case_type)
    if search:
        qs = qs.filter(
            Q(ot_number__icontains=search) |
            Q(patient__name__icontains=search) |
            Q(patient__patient_id__icontains=search)
        )

    context = {
        'page_title': 'OT History',
        'cases': qs[:500],
        'status_choices': OTCase.StatusChoices.choices,
        'case_type_choices': OTCase.CaseTypeChoices.choices,
        'filters': {
            'date_from': date_from or '',
            'date_to': date_to or '',
            'status': status_filter,
            'case_type': case_type,
            'q': search,
        }
    }
    return render(request, 'ot/history/list.html', context)


# ─────────────────────────────────────────────
# OT MASTER
# ─────────────────────────────────────────────

@login_required
def master_index(request):
    rooms = OTRoom.objects.all()
    procedures = OTProcedure.objects.select_related('department').all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_room':
            code = request.POST.get('room_code', '').strip().upper()
            name = request.POST.get('room_name', '').strip()
            location = request.POST.get('room_location', '').strip()
            if code and name:
                OTRoom.objects.get_or_create(code=code, defaults={'name': name, 'location': location})
                messages.success(request, f"OT Room {code} added.")
            else:
                messages.error(request, "Code and Name are required.")
        elif action == 'add_procedure':
            code = request.POST.get('proc_code', '').strip().upper()
            name = request.POST.get('proc_name', '').strip()
            duration = request.POST.get('proc_duration', 60)
            if code and name:
                OTProcedure.objects.get_or_create(code=code, defaults={'name': name, 'avg_duration_min': int(duration)})
                messages.success(request, f"Procedure {name} added.")
            else:
                messages.error(request, "Code and Name are required.")
        elif action == 'toggle_room':
            room_id = request.POST.get('room_id')
            try:
                room = OTRoom.objects.get(pk=room_id)
                room.status = OTRoom.StatusChoices.INACTIVE if room.status == OTRoom.StatusChoices.ACTIVE else OTRoom.StatusChoices.ACTIVE
                room.save()
                messages.success(request, f"Room {room.code} status updated.")
            except OTRoom.DoesNotExist:
                messages.error(request, "Room not found.")
        return redirect('ot:master')

    context = {
        'page_title': 'OT Master',
        'rooms': rooms,
        'procedures': procedures,
    }
    return render(request, 'ot/master/index.html', context)


# ─────────────────────────────────────────────
# JSON APIS
# ─────────────────────────────────────────────

@login_required
def api_patient_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'patients': []})

    patients = Patient.objects.filter(
        Q(name__icontains=q) | Q(patient_id__icontains=q) | Q(mobile_no__icontains=q)
    )[:20]

    data = []
    for p in patients:
        data.append({
            'id': p.pk,
            'patient_id': p.patient_id,
            'name': p.name,
            'age': p.age_years,
            'gender': p.gender,
            'mobile': p.mobile_no,
            'department': p.department,
        })
    return JsonResponse({'patients': data})


@login_required
def api_patient_ip_admissions(request, patient_pk):
    visits = PatientVisit.objects.filter(
        patient_id=patient_pk,
        visit_type='IP'
    ).order_by('-visit_date')[:10]

    data = []
    for v in visits:
        data.append({
            'id': v.pk,
            'ipno': v.ipno or '',
            'visit_date': v.visit_date.strftime('%d/%b/%Y'),
            'ward': v.ward or '',
            'bed': v.bed or '',
            'department': v.department,
        })
    return JsonResponse({'admissions': data})


@login_required
def api_diagnosis_search(request):
    q = request.GET.get('q', '').strip()
    diagnoses = Diagnosis.objects.filter(
        Q(name__icontains=q) | Q(code__icontains=q), is_active=True
    )[:20]
    return JsonResponse({'diagnoses': [
        {'id': d.pk, 'name': d.name, 'code': d.code or ''} for d in diagnoses
    ]})


@login_required
def api_check_conflicts(request):
    """Check for scheduling conflicts for a given room/date/time/duration."""
    room_id = request.GET.get('room_id')
    date_str = request.GET.get('date')
    start_str = request.GET.get('start')
    duration = int(request.GET.get('duration', 60))
    exclude_case_id = request.GET.get('exclude_case')

    try:
        room = OTRoom.objects.get(pk=room_id)
        d = datetime.date.fromisoformat(date_str)
        t_start = datetime.time.fromisoformat(start_str)
        dt_start = datetime.datetime.combine(d, t_start)
        dt_end = dt_start + datetime.timedelta(minutes=duration)
        t_end = dt_end.time()
        exclude = OTCase.objects.get(pk=exclude_case_id) if exclude_case_id else None
        conflicts = _check_conflicts(room, d, t_start, t_end, exclude_case=exclude)
        return JsonResponse({'conflicts': [c['description'] for c in conflicts]})
    except Exception as e:
        return JsonResponse({'conflicts': [], 'error': str(e)})


@login_required
def api_live_status(request):
    """Poll endpoint for live OT board."""
    active = OTCase.objects.filter(
        status__in=[
            OTCase.StatusChoices.SHIFTED_TO_OT, OTCase.StatusChoices.SIGN_IN,
            OTCase.StatusChoices.ANESTHESIA, OTCase.StatusChoices.TIME_OUT,
            OTCase.StatusChoices.SURGERY_IN_PROGRESS, OTCase.StatusChoices.SIGN_OUT,
        ]
    ).select_related('patient', 'procedure', 'ot_room', 'surgeon')

    data = []
    now = timezone.now()
    for case in active:
        # Find start time from schedule
        start_dt = None
        sched = getattr(case, 'schedule', None)
        if sched and sched.actual_start:
            start_dt = sched.actual_start
        elapsed = None
        if start_dt:
            elapsed = int((now - start_dt).total_seconds() / 60)

        data.append({
            'pk': case.pk,
            'ot_number': case.ot_number,
            'room_code': case.ot_room.code,
            'patient': case.patient.name,
            'procedure': case.procedure.name,
            'surgeon': case.surgeon.get_full_name() or case.surgeon.username,
            'status': case.get_status_display(),
            'elapsed_min': elapsed,
            'is_emergency': case.is_emergency,
            'is_mlc': case.is_mlc,
        })
    return JsonResponse({'cases': data})


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_surgeons():
    from apps.users.models import User
    return User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')


def _check_conflicts(room, date, t_start, t_end, exclude_case=None):
    """Check for OT room scheduling conflicts."""
    if t_end is None:
        return []

    overlapping = OTSchedule.objects.filter(
        room=room,
        scheduled_date=date,
        scheduled_end__gt=t_start,
        scheduled_start__lt=t_end,
    ).exclude(
        ot_case__status=OTCase.StatusChoices.CANCELLED
    )

    if exclude_case:
        overlapping = overlapping.exclude(ot_case=exclude_case)

    conflicts = []
    for s in overlapping.select_related('ot_case__patient'):
        conflicts.append({
            'type': 'room',
            'description': f"Room conflict: {room.code} already booked for {s.ot_case.ot_number} ({s.ot_case.patient.name}) at {s.scheduled_start}–{s.scheduled_end}"
        })
    return conflicts


def _auto_advance_from_preop(case, preop, user):
    """Advance OT case status based on pre-op completion."""
    if case.status == OTCase.StatusChoices.BOOKED:
        case.transition(OTCase.StatusChoices.PRE_OP, user, 'Pre-Op started')
        case.refresh_from_db()

    if preop.pac_status == 'DONE' and case.status == OTCase.StatusChoices.PRE_OP:
        if preop.consent_status == 'OBTAINED':
            case.transition(OTCase.StatusChoices.PAC_DONE, user, 'PAC completed, consent obtained')
        else:
            case.transition(OTCase.StatusChoices.CONSENT_PENDING, user, 'PAC done, awaiting consent')


def _get_workflow_steps(case):
    """Returns workflow step definitions with completion state."""
    S = OTCase.StatusChoices
    completed_statuses = [
        S.PRE_OP, S.CONSENT_OBTAINED, S.PAC_DONE, S.SITE_MARKED,
        S.SCHEDULED, S.SHIFTED_TO_OT, S.SIGN_IN, S.ANESTHESIA,
        S.TIME_OUT, S.SURGERY_IN_PROGRESS, S.SIGN_OUT,
        S.SURGERY_COMPLETED, S.OUTCOME_RECORDED,
        S.RECOVERY, S.WARD, S.ICU, S.CLOSED
    ]
    status_order = [
        S.BOOKED, S.PRE_OP, S.CONSENT_OBTAINED, S.PAC_DONE,
        S.SITE_MARKED, S.SCHEDULED, S.SHIFTED_TO_OT, S.SIGN_IN,
        S.ANESTHESIA, S.TIME_OUT, S.SURGERY_IN_PROGRESS, S.SIGN_OUT,
        S.SURGERY_COMPLETED, S.OUTCOME_RECORDED, S.RECOVERY, S.CLOSED,
    ]
    try:
        current_idx = status_order.index(case.status)
    except ValueError:
        current_idx = 0

    steps = []
    step_defs = [
        ('Booking', S.BOOKED, 'bi-calendar-check'),
        ('Pre-Op', S.PRE_OP, 'bi-clipboard2-pulse'),
        ('Consent', S.CONSENT_OBTAINED, 'bi-file-earmark-check'),
        ('PAC', S.PAC_DONE, 'bi-heart-pulse'),
        ('Site Mark', S.SITE_MARKED, 'bi-geo-alt'),
        ('Schedule', S.SCHEDULED, 'bi-calendar-week'),
        ('Shift to OT', S.SHIFTED_TO_OT, 'bi-arrow-right-circle'),
        ('Sign In', S.SIGN_IN, 'bi-check-circle'),
        ('Anesthesia', S.ANESTHESIA, 'bi-droplet'),
        ('Time Out', S.TIME_OUT, 'bi-pause-circle'),
        ('Surgery', S.SURGERY_IN_PROGRESS, 'bi-scissors'),
        ('Sign Out', S.SIGN_OUT, 'bi-check2-circle'),
        ('Completed', S.SURGERY_COMPLETED, 'bi-trophy'),
        ('Outcome', S.OUTCOME_RECORDED, 'bi-clipboard-data'),
        ('Recovery', S.RECOVERY, 'bi-house-heart'),
        ('Closed', S.CLOSED, 'bi-lock'),
    ]
    for label, status, icon in step_defs:
        try:
            step_idx = status_order.index(status)
            is_done = step_idx < current_idx
            is_current = step_idx == current_idx
        except ValueError:
            is_done = False
            is_current = False
        steps.append({
            'label': label,
            'status': status,
            'icon': icon,
            'is_done': is_done,
            'is_current': is_current,
        })
    return steps


def _get_next_actions(case):
    """Returns list of (label, url_name, style) for the next valid actions."""
    S = OTCase.StatusChoices
    actions = {
        S.BOOKED: [('Start Pre-Op', 'ot:preop_form', 'primary')],
        S.PRE_OP: [('Update Pre-Op', 'ot:preop_form', 'primary')],
        S.CONSENT_PENDING: [('Update Pre-Op / Consent', 'ot:preop_form', 'primary')],
        S.CONSENT_OBTAINED: [('Update Pre-Op / PAC', 'ot:preop_form', 'primary')],
        S.PAC_PENDING: [('Update PAC', 'ot:preop_form', 'primary')],
        S.PAC_DONE: [('Schedule OT', 'ot:schedule_form', 'primary')],
        S.SITE_MARKED: [('Schedule OT', 'ot:schedule_form', 'primary')],
        S.SCHEDULED: [('Shift to OT', 'ot:shift_to_ot', 'success')],
        S.SHIFTED_TO_OT: [('Start Sign-In', 'ot:sign_in', 'primary')],
        S.SIGN_IN: [('Record Anesthesia', 'ot:anesthesia_form', 'primary')],
        S.ANESTHESIA: [('Start Time-Out', 'ot:time_out', 'primary')],
        S.TIME_OUT: [('Start Surgery', 'ot:start_surgery', 'danger')],
        S.SURGERY_IN_PROGRESS: [
            ('Operation Notes', 'ot:operation_notes', 'primary'),
            ('Start Sign-Out', 'ot:sign_out', 'warning'),
        ],
        S.SIGN_OUT: [('Mark Surgery Complete', 'ot:complete_surgery', 'success')],
        S.SURGERY_COMPLETED: [('Record Outcome', 'ot:outcome_form', 'primary')],
        S.OUTCOME_RECORDED: [('Record Disposition', 'ot:disposition_form', 'primary')],
        S.RECOVERY: [('Post-Op Notes', 'ot:postop_form', 'primary'), ('Close Case', 'ot:closure_form', 'secondary')],
        S.WARD: [('Post-Op Notes', 'ot:postop_form', 'primary'), ('Close Case', 'ot:closure_form', 'secondary')],
        S.ICU: [('Post-Op Notes', 'ot:postop_form', 'primary'), ('Close Case', 'ot:closure_form', 'secondary')],
    }
    return actions.get(case.status, [])


def _schedule_context(case, sched, rooms):
    return {
        'page_title': f'Schedule — {case.ot_number}',
        'case': case,
        'sched': sched,
        'rooms': rooms,
        'conflicts': [],
        'post_data': {},
    }
