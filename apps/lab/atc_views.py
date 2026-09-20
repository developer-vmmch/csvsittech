"""
Views and API Endpoints for the ATC (Auto Trigger Control) Module.
"""

import uuid
import math
from datetime import datetime, time, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from apps.core.mixins import GranularPermissionRequiredMixin
from apps.lab.models import ATCJob, ATCJobLog, ATCSetting
from apps.patients.models import Department, Patient
from apps.lab.atc_service import (
    trigger_atc_job_async,
    get_server_today,
    get_server_now,
)


def parse_source_period(period_str):
    """Extract from_year and to_year from string like '2024 – 2025' or '2026 – Current'."""
    import re
    years = [int(y) for y in re.findall(r'\b\d{4}\b', str(period_str or ''))]
    if len(years) >= 2:
        return years[0], years[1]
    elif len(years) == 1:
        return years[0], years[0]
    return 2022, 2024


class ATCControlView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    """
    Single-page control center for ATC matching reference layout.
    """
    permission_required = 'auto_trigger.atc.view'
    template_name = 'lab/auto_trigger/atc.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = ATCSetting.get_settings()
        today = get_server_today()

        context['settings'] = settings
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['today'] = today.strftime('%Y-%m-%d')
        context['today_display'] = today.strftime('%d-%m-%Y')
        context['current_month_name'] = today.strftime('%B %Y')
        context['current_year'] = today.year
        context['current_month'] = today.month

        # Source Data Periods
        context['source_data_periods'] = [
            '2020 – 2021',
            '2021 – 2022',
            '2022 – 2023',
            '2023 – 2024',
            '2024 – 2025',
            '2025 – 2026',
            '2026 – Current',
        ]
        context['default_source_data_period'] = '2024 – 2025'

        # Permission flags for template UI controls
        u = self.request.user
        context['can_view'] = True
        context['can_create'] = u.can_atc_create or u.is_superuser
        context['can_edit'] = u.can_atc_edit or u.is_superuser
        context['can_trigger'] = u.can_atc_trigger or u.is_superuser
        context['can_emergency_stop'] = u.can_atc_emergency_stop or u.is_superuser

        # Check for active or draft job
        active_job = ATCJob.objects.filter(
            status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]
        ).first()

        draft_job = None
        if not active_job:
            draft_job = ATCJob.objects.filter(status=ATCJob.StatusChoices.DRAFT).order_by('-id').first()

        selected_job = active_job or draft_job
        context['active_job'] = active_job
        context['draft_job'] = draft_job
        context['selected_job'] = selected_job
        context['is_locked'] = bool(selected_job and selected_job.is_locked and not context['can_edit'])

        # Preloaded departments for table (initial 5 from reference image or saved plan)
        initial_depts = []
        default_names = ['GENERAL MEDICINE', 'DERMATOLOGY', 'EMERGENCY MEDICINE', 'ENT', 'GENERAL SURGERY']
        if selected_job and selected_job.plan_departments:
            initial_depts = list(selected_job.plan_departments)
            existing_dept_ids = {int(d['department_id']) for d in initial_depts if isinstance(d, dict) and d.get('department_id')}
            for name in default_names:
                dept_obj = Department.objects.filter(name__iexact=name).first()
                if dept_obj and dept_obj.id not in existing_dept_ids:
                    initial_depts.append({
                        'department_id': dept_obj.id,
                        'name': dept_obj.name,
                        'source_data_period': '2024 – 2025',
                        'signal': 'ALL',
                        'male': 0,
                        'female': 0,
                        'child': 0,
                        'total': 0,
                        'op_daily_pct': 75,
                        'review_pct': 25,
                        'op_target': 0,
                        'review_target': 0,
                        'min': 0,
                        'max': 0,
                        'is_configured': False,
                    })
        else:
            for name in default_names:
                dept_obj = Department.objects.filter(name__iexact=name).first()
                if dept_obj:
                    initial_depts.append({
                        'department_id': dept_obj.id,
                        'name': dept_obj.name,
                        'source_data_period': '2024 – 2025',
                        'signal': 'ALL',
                        'male': 0,
                        'female': 0,
                        'child': 0,
                        'total': 0,
                        'op_daily_pct': 75,
                        'review_pct': 25,
                        'op_target': 0,
                        'review_target': 0,
                        'min': 0,
                        'max': 0,
                        'is_configured': False,
                    })

        import json
        context['initial_plan_departments_json'] = json.dumps(initial_depts)
        context['initial_daily_targets_json'] = json.dumps(selected_job.daily_targets if selected_job and selected_job.daily_targets else {})

        initial_from_date = today.strftime('%Y-%m-%d')
        initial_to_date = today.strftime('%Y-%m-%d')
        if selected_job and selected_job.from_date:
            initial_from_date = selected_job.from_date.strftime('%Y-%m-%d')
        if selected_job and selected_job.to_date:
            initial_to_date = selected_job.to_date.strftime('%Y-%m-%d')
        context['initial_from_date'] = initial_from_date
        context['initial_to_date'] = initial_to_date

        d1 = datetime.strptime(initial_from_date, '%Y-%m-%d').date()
        d2 = datetime.strptime(initial_to_date, '%Y-%m-%d').date()
        if d1 == d2:
            context['initial_date_display'] = d1.strftime('%d-%m-%Y')
        else:
            context['initial_date_display'] = f"{d1.strftime('%d-%m-%Y')} → {d2.strftime('%d-%m-%Y')}"

        return context


class ATCLiveStatusView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    """
    Dedicated submodule page for real-time monitoring and control of ATC automation jobs.
    """
    permission_required = 'auto_trigger.atc_status.view'
    template_name = 'lab/auto_trigger/atc_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = get_server_today()
        active_job = ATCJob.objects.filter(
            status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]
        ).first()

        if not active_job:
            active_job = ATCJob.objects.order_by('-id').first()

        context['active_job'] = active_job
        context['today_display'] = today.strftime('%d-%m-%Y')
        return context


class ATCSettingsView(LoginRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    """
    Settings view for ATC.
    """
    permission_required = 'auto_trigger.atc_settings.view'
    template_name = 'lab/auto_trigger/atc_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = ATCSetting.get_settings()
        return context

    def post(self, request, *args, **kwargs):
        settings = ATCSetting.get_settings()

        try:
            start_t = request.POST.get('default_start_time', '08:00')
            end_t = request.POST.get('default_end_time', '14:00')
            max_days = int(request.POST.get('max_future_days', 30))
            batch_size = int(request.POST.get('default_batch_size', 100))
            from_yr = int(request.POST.get('source_from_year', 2022))
            to_yr = int(request.POST.get('source_to_year', 2024))
            male_pct = int(request.POST.get('gender_ratio_male_pct', 60))
            female_pct = int(request.POST.get('gender_ratio_female_pct', 40))

            settings.default_start_time = start_t
            settings.default_end_time = end_t
            settings.max_future_days = max(1, max_days)
            settings.default_batch_size = max(1, batch_size)
            settings.source_from_year = from_yr
            settings.source_to_year = to_yr
            settings.gender_ratio_male_pct = male_pct
            settings.gender_ratio_female_pct = female_pct
            settings.op_date_restriction = request.POST.get('op_date_restriction') == 'on'
            settings.allow_review_backdated = request.POST.get('allow_review_backdated') == 'on'
            settings.allow_review_future = request.POST.get('allow_review_future') == 'on'
            settings.save()

            messages.success(request, "ATC Settings updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating settings: {e}")

        return redirect('lab:auto_trigger_atc_settings')


@require_POST
@login_required
def api_atc_trigger(request):
    """
    Trigger a new ATC automation job with concurrency and duplicate prevention.
    Combined OP + Review execution based on percentage allocation and multi-department daily targets.
    """
    # Permission check: ATC_TRIGGER
    if not (request.user.can_atc_trigger or request.user.is_superuser):
        return JsonResponse({
            'status': 'error',
            'message': 'Permission Denied: You do not have permission to trigger ATC automation (ATC_TRIGGER required).'
        }, status=403)

    # Double-click / Concurrency prevention:
    # If ATC is already running, return error
    running_job = ATCJob.objects.filter(
        status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]
    ).first()

    if running_job:
        return JsonResponse({
            'status': 'error',
            'message': f"An ATC job is already running (Job #{running_job.job_id}). Please wait for it to complete or use Emergency Stop."
        }, status=400)

    import json
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
            if 'plan_departments' in request.POST:
                try:
                    data['plan_departments'] = json.loads(request.POST.get('plan_departments'))
                except Exception:
                    pass
            if 'daily_targets' in request.POST:
                try:
                    data['daily_targets'] = json.loads(request.POST.get('daily_targets'))
                except Exception:
                    pass
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid request data: {e}'}, status=400)

    mode = data.get('mode', 'COMBINED')
    valid_modes = [c[0] for c in ATCJob.ModeChoices.choices]
    if mode not in valid_modes:
        return JsonResponse({
            'status': 'error',
            'message': f"Invalid ATC mode: '{mode}'. Must be one of: {valid_modes}"
        }, status=400)

    today = get_server_today()
    settings = ATCSetting.get_settings()

    if mode == 'FUTURE_PATIENT':
        to_date_str = data.get('to_date')
        if to_date_str:
            try:
                to_d = datetime.strptime(to_date_str, '%Y-%m-%d').date()
                if to_d > today + timedelta(days=31):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Future patient creation is limited to one month.'
                    }, status=400)
            except ValueError:
                pass

    plan_depts = data.get('plan_departments')
    daily_targets = data.get('daily_targets', {})

    # Check minimum 5 departments rule if plan_departments is provided
    if plan_depts is not None:
        configured_depts = [d for d in plan_depts if isinstance(d, dict) and d.get('is_configured') is not False and d.get('department_id')]
        if len(configured_depts) < 5:
            return JsonResponse({
                'status': 'error',
                'message': f"At least 5 different departments must be configured before triggering automation. Currently configured: {len(configured_depts)} / 5."
            }, status=400)
        c_ids = [d['department_id'] for d in configured_depts]
        if len(c_ids) != len(set(c_ids)):
            return JsonResponse({
                'status': 'error',
                'message': 'Duplicate department configuration detected. Each department must be unique within an ATC plan.'
            }, status=400)

    # Percentage validation
    try:
        op_daily_pct = int(data.get('op_daily_pct', getattr(settings, 'default_op_daily_pct', 75)))
    except (ValueError, TypeError):
        op_daily_pct = 75

    try:
        review_pct = int(data.get('review_pct', getattr(settings, 'default_review_pct', 25)))
    except (ValueError, TypeError):
        review_pct = 25

    if (op_daily_pct + review_pct) != 100:
        return JsonResponse({
            'status': 'error',
            'message': 'OP Daily % and Review % must total 100%.'
        }, status=400)

    signal = data.get('operation_signal', 'ALL')
    from_date_str = data.get('from_date', data.get('op_date'))
    to_date_str = data.get('to_date', data.get('op_date'))
    from_d = today
    to_d = today
    if from_date_str:
        try:
            from_d = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if to_date_str:
        try:
            to_d = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if from_d > to_d:
        return JsonResponse({
            'status': 'error',
            'message': 'From date cannot be after To date.'
        }, status=400)

    if signal in ['OP', 'ALL'] and from_d < today:
        return JsonResponse({
            'status': 'error',
            'message': f"OP automation can only create records for today's application date ({today.strftime('%d-%m-%Y')}) or future. Backdated OP registration is blocked."
        }, status=400)

    # Validate daily_targets: MIN cannot be greater than MAX
    if daily_targets and isinstance(daily_targets, dict):
        for date_k, depts_map in daily_targets.items():
            if isinstance(depts_map, dict):
                for d_k, vals in depts_map.items():
                    if isinstance(vals, dict):
                        d_min = int(vals.get('min', 0) or 0)
                        d_max = int(vals.get('max', 0) or 0)
                        if d_min > d_max:
                            return JsonResponse({
                                'status': 'error',
                                'message': 'Minimum target cannot be greater than maximum target.'
                            }, status=400)

    if plan_depts and isinstance(plan_depts, list):
        for d in plan_depts:
            if isinstance(d, dict):
                d_min = int(d.get('min', 0) or 0)
                d_max = int(d.get('max', 0) or 0)
                if d_min > d_max:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Minimum target cannot be greater than maximum target.'
                    }, status=400)

    # Target calculation
    try:
        male_count = int(data.get('male_count', data.get('male_patients', 0)) or 0)
        female_count = int(data.get('female_count', data.get('female_patients', 0)) or 0)
        child_count = int(data.get('child_count', data.get('child_patients', 0)) or 0)
    except (ValueError, TypeError):
        male_count, female_count, child_count = 0, 0, 0

    total_target = male_count + female_count + child_count
    if plan_depts:
        total_target = sum(int(d.get('total', 0) or (int(d.get('male', 0) or 0) + int(d.get('female', 0) or 0) + int(d.get('child', 0) or 0))) for d in plan_depts)
        male_count = sum(int(d.get('male', 0) or 0) for d in plan_depts)
        female_count = sum(int(d.get('female', 0) or 0) for d in plan_depts)
        child_count = sum(int(d.get('child', 0) or 0) for d in plan_depts)

    if total_target <= 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Target patient count must be greater than 0.'
        }, status=400)

    target_op = int(round(total_target * (op_daily_pct / 100.0)))
    target_review = total_target - target_op

    start_str = data.get('start_time', '08:00')
    end_str = data.get('end_time', '14:00')
    try:
        s_parts = [int(p) for p in start_str.split(':')[:2]]
        start_t = time(s_parts[0], s_parts[1])
    except Exception:
        start_t = time(8, 0)
    try:
        e_parts = [int(p) for p in end_str.split(':')[:2]]
        end_t = time(e_parts[0], e_parts[1])
    except Exception:
        end_t = time(14, 0)

    cur_time = get_server_now().time()
    if from_d == today and cur_time >= end_t and target_op > 0:
        return JsonResponse({
            'status': 'error',
            'message': f"Cannot start OP automation: Current server time ({cur_time.strftime('%H:%M')}) is past the configured day-end time ({end_t.strftime('%H:%M')})."
        }, status=400)

    dept_id = data.get('department_id')
    dept = Department.objects.filter(id=dept_id).first() if dept_id else None

    period_str = data.get('source_data_period', '2024 – 2025')
    from_year, to_year = parse_source_period(period_str)
    review_source_year = from_year

    date_prefix = today.strftime('%Y%m%d')
    todays_jobs_count = ATCJob.objects.filter(job_id__startswith=f"ATC-{date_prefix}").count()
    seq = todays_jobs_count + 1
    job_id_str = f"ATC-{date_prefix}-{seq:03d}"
    while ATCJob.objects.filter(job_id=job_id_str).exists():
        seq += 1
        job_id_str = f"ATC-{date_prefix}-{seq:03d}"

    # Lock configuration after Save & Trigger
    job = ATCJob.objects.create(
        job_id=job_id_str,
        mode=mode,
        department=dept,
        source_from_year=from_year,
        source_to_year=to_year,
        review_source_year=review_source_year,
        source_data_period=period_str,
        operation_signal=signal,
        target_total=total_target,
        target_male=male_count,
        target_female=female_count,
        child_target=child_count,
        op_daily_pct=op_daily_pct,
        review_pct=review_pct,
        target_op=target_op,
        target_review=target_review,
        plan_departments=plan_depts or [],
        daily_targets=daily_targets or {},
        schedule_start_time=start_t,
        schedule_end_time=end_t,
        batch_size=int(data.get('batch_size', 100) or 100),
        from_date=from_d,
        to_date=to_d,
        status=ATCJob.StatusChoices.STARTING,
        is_locked=True,
        created_by=request.user,
    )

    trigger_atc_job_async(job.id)

    return JsonResponse({
        'status': 'success',
        'message': f"ATC automation started successfully ({target_op} OP + {target_review} Reviews across {len(plan_depts or [1])} departments).",
        'job_id': job.id,
        'job_code': job.job_id,
        'target_op': target_op,
        'target_review': target_review,
        'target_total': total_target,
        'redirect_url': '/lab/auto-trigger/atc/status/'
    })


@require_GET
@login_required
def api_atc_status(request, job_id):
    """
    Returns live execution status, metrics, and progress for an ATC job.
    """
    job = get_object_or_404(ATCJob, pk=job_id)

    recent_logs = list(
        job.logs.order_by('-created_at')[:15].values(
            'id', 'patient_name', 'gender', 'department',
            'batch_number', 'status', 'error_message', 'created_at'
        )
    )

    for l in recent_logs:
        l['created_at'] = l['created_at'].strftime('%H:%M:%S')

    return JsonResponse({
        'status': 'success',
        'job': {
            'id': job.id,
            'job_code': job.job_id,
            'job_id': job.job_id,
            'mode': job.mode,
            'department_name': job.department.name if job.department else 'All / General',
            'status': job.status,
            'target_total': job.target_total,
            'target_male': job.target_male,
            'target_female': job.target_female,
            'child_target': job.child_target,
            'op_daily_pct': job.op_daily_pct,
            'review_pct': job.review_pct,
            'target_op': job.target_op,
            'target_review': job.target_review,
            'created_count': job.created_count,
            'created_op': job.created_op,
            'created_review': job.created_review,
            'created_male': job.created_male,
            'created_female': job.created_female,
            'failed_count': job.failed_count,
            'remaining_count': job.remaining_count,
            'progress_percentage': job.progress_percentage,
            'current_batch': job.current_batch,
            'total_batches': job.total_batches,
            'start_time': job.schedule_start_time.strftime('%I:%M %p') if job.schedule_start_time else '08:00 AM',
            'end_time': job.schedule_end_time.strftime('%I:%M %p') if job.schedule_end_time else '02:00 PM',
            'from_date': job.from_date.strftime('%d-%m-%Y') if job.from_date else '',
            'to_date': job.to_date.strftime('%d-%m-%Y') if job.to_date else '',
            'source_data_period': job.source_data_period,
            'operation_signal': job.operation_signal,
            'current_patient_info': job.current_patient_info,
            'stop_reason': job.stop_reason,
            'error_summary': job.error_summary,
            'is_locked': job.is_locked,
            'is_running': job.status in [ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STARTING],
            'is_stopped': job.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED],
            'is_completed': job.status == ATCJob.StatusChoices.COMPLETED,
            'is_failed': job.status == ATCJob.StatusChoices.FAILED,
        },
        'logs': recent_logs,
    })


@require_GET
@login_required
def api_atc_active_job(request):
    """Returns details of the currently active ATC job, if any."""
    active_job = ATCJob.objects.filter(
        status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]
    ).first()

    if not active_job:
        return JsonResponse({'status': 'none', 'active_job': None})

    return JsonResponse({
        'status': 'active',
        'active_job': {
            'id': active_job.id,
            'job_id': active_job.job_id,
            'status': active_job.status,
            'progress_percentage': active_job.progress_percentage,
            'created_count': active_job.created_count,
            'target_total': active_job.target_total,
            'target_op': active_job.target_op,
            'target_review': active_job.target_review,
            'created_op': active_job.created_op,
            'created_review': active_job.created_review,
            'failed_count': active_job.failed_count,
        }
    })


@require_POST
@login_required
def api_atc_stop(request, job_id):
    """
    Triggers Emergency Stop for an ongoing ATC job.
    """
    if not (request.user.can_atc_emergency_stop or request.user.is_superuser):
        return JsonResponse({
            'status': 'error',
            'message': 'Permission Denied: You do not have permission to emergency stop ATC automation (ATC_EMERGENCY_STOP required).'
        }, status=403)

    if job_id == 0:
        job = ATCJob.objects.filter(status__in=[
            ATCJob.StatusChoices.STARTING,
            ATCJob.StatusChoices.RUNNING,
            ATCJob.StatusChoices.STOP_REQUESTED,
        ]).first() or ATCJob.objects.order_by('-id').first()
        if not job:
            return JsonResponse({'status': 'info', 'message': 'No active ATC job found to stop.'})
    else:
        job = get_object_or_404(ATCJob, pk=job_id)

    if job.status in [ATCJob.StatusChoices.COMPLETED, ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED]:
        return JsonResponse({
            'status': 'info',
            'message': f"Job {job.job_id} is already in {job.status} state."
        })

    job.stop_requested = True
    job.status = ATCJob.StatusChoices.STOP_REQUESTED
    job.stop_reason = "Emergency Stop clicked by user."
    job.save(update_fields=['stop_requested', 'status', 'stop_reason'])

    return JsonResponse({
        'status': 'success',
        'message': "Emergency Stop signal sent. Automation will halt immediately."
    })


@require_POST
@login_required
def api_atc_preview(request):
    """
    Returns validation preview and calculated plan summary before triggering.
    Combined OP + Review calculation across configured departments.
    """
    import json
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
            if 'plan_departments' in request.POST:
                try:
                    data['plan_departments'] = json.loads(request.POST.get('plan_departments'))
                except Exception:
                    pass
    except Exception:
        data = request.POST.dict()

    today = get_server_today()
    settings = ATCSetting.get_settings()

    dept_id = data.get('department_id')
    dept = Department.objects.filter(id=dept_id).first() if dept_id else None
    dept_name = dept.name if dept else 'All Configured Departments'

    signal = data.get('operation_signal', 'ALL')
    from_date_str = data.get('from_date', data.get('op_date'))
    to_date_str = data.get('to_date', data.get('op_date'))
    from_d = today
    to_d = today
    if from_date_str:
        try:
            from_d = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if to_date_str:
        try:
            to_d = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if from_d > to_d:
        return JsonResponse({
            'status': 'error',
            'message': 'From date cannot be after To date.'
        }, status=400)

    if signal in ['OP', 'ALL'] and from_d < today:
        return JsonResponse({
            'status': 'error',
            'message': f"OP automation can only create records for today's application date ({today.strftime('%d-%m-%Y')}) or future. Backdated OP registration is blocked."
        }, status=400)

    # Validate daily_targets: MIN cannot be greater than MAX
    daily_targets = data.get('daily_targets', {})
    if daily_targets and isinstance(daily_targets, dict):
        for date_k, depts_map in daily_targets.items():
            if isinstance(depts_map, dict):
                for d_k, vals in depts_map.items():
                    if isinstance(vals, dict):
                        d_min = int(vals.get('min', 0) or 0)
                        d_max = int(vals.get('max', 0) or 0)
                        if d_min > d_max:
                            return JsonResponse({
                                'status': 'error',
                                'message': 'Minimum target cannot be greater than maximum target.'
                            }, status=400)

    plan_depts = data.get('plan_departments', [])
    try:
        m_count = int(data.get('male_count', data.get('male_patients', 0)) or 0)
        f_count = int(data.get('female_count', data.get('female_patients', 0)) or 0)
        c_count = int(data.get('child_count', data.get('child_patients', 0)) or 0)
    except (ValueError, TypeError):
        m_count, f_count, c_count = 0, 0, 0

    total = m_count + f_count + c_count
    configured_depts = []
    if plan_depts:
        configured_depts = [d for d in plan_depts if isinstance(d, dict) and d.get('is_configured') is not False and d.get('department_id')]
        target_depts = configured_depts if configured_depts else plan_depts
        total = sum(int(d.get('total', 0) or (int(d.get('male', 0) or 0) + int(d.get('female', 0) or 0) + int(d.get('child', 0) or 0))) for d in target_depts)
        m_count = sum(int(d.get('male', 0) or 0) for d in target_depts)
        f_count = sum(int(d.get('female', 0) or 0) for d in target_depts)
        c_count = sum(int(d.get('child', 0) or 0) for d in target_depts)

    if total <= 0:
        return JsonResponse({'status': 'error', 'message': 'Total patient target must be greater than 0.'}, status=400)

    try:
        op_daily_pct = int(data.get('op_daily_pct', getattr(settings, 'default_op_daily_pct', 75)))
    except (ValueError, TypeError):
        op_daily_pct = 75

    try:
        review_pct = int(data.get('review_pct', getattr(settings, 'default_review_pct', 25)))
    except (ValueError, TypeError):
        review_pct = 25

    if (op_daily_pct + review_pct) != 100:
        return JsonResponse({
            'status': 'error',
            'message': 'OP Daily % and Review % must total 100%.'
        }, status=400)

    target_op = int(round(total * (op_daily_pct / 100.0)))
    target_review = total - target_op

    period_str = data.get('source_data_period', '2024 – 2025')
    from_yr, to_yr = parse_source_period(period_str)
    review_source_year = from_yr

    d_qs = Patient.objects.filter(patient_type='D')
    if dept:
        d_qs = d_qs.filter(Q(department_obj=dept) | Q(department__iexact=dept.name))
    year_d = d_qs.filter(registration_date__year=review_source_year)
    eligible_d = year_d.count() if year_d.exists() else d_qs.count()

    batch_size = int(data.get('batch_size', settings.default_batch_size or 100) or 100)
    batch_size = max(1, batch_size)
    total_batches = math.ceil(total / batch_size)

    return JsonResponse({
        'status': 'success',
        'preview': {
            'mode': 'COMBINED',
            'title': 'ATC Plan Summary (Preview)',
            'department': dept_name,
            'departments_count': len(configured_depts) if configured_depts else (len(plan_depts) if plan_depts else 1),
            'source_period': period_str,
            'operation_signal': signal,
            'target_total': total,
            'target_male': m_count,
            'target_female': f_count,
            'target_child': c_count,
            'op_daily_pct': op_daily_pct,
            'review_pct': review_pct,
            'target_op': target_op,
            'target_review': target_review,
            'eligible_d_patients': eligible_d,
            'total_batches': total_batches,
            'batch_size': batch_size,
            'notes': f"OP ({target_op} patients) created for today/future. Review ({target_review} visits) generated against existing D patients from {review_source_year}."
        }
    })


@require_POST
@login_required
def api_atc_save_config(request):
    """
    Saves configuration parameters as a DRAFT without triggering execution.
    Can be loaded back into the ATC screen for further edits.
    """
    if not (request.user.can_atc_create or request.user.can_atc_edit or request.user.is_superuser):
        return JsonResponse({
            'status': 'error',
            'message': 'Permission Denied: You do not have permission to save ATC configuration (ATC_CREATE or ATC_EDIT required).'
        }, status=403)

    import json
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
            if 'plan_departments' in request.POST:
                try:
                    data['plan_departments'] = json.loads(request.POST.get('plan_departments'))
                except Exception:
                    pass
            if 'daily_targets' in request.POST:
                try:
                    data['daily_targets'] = json.loads(request.POST.get('daily_targets'))
                except Exception:
                    pass
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid request data: {e}'}, status=400)

    job_id = data.get('job_id')
    draft_job = None
    if job_id:
        draft_job = ATCJob.objects.filter(pk=job_id).first()
    if not draft_job:
        draft_job = ATCJob.objects.filter(status=ATCJob.StatusChoices.DRAFT).first()

    if draft_job and draft_job.is_locked and not (request.user.can_atc_edit or request.user.is_superuser):
        return JsonResponse({
            'status': 'error',
            'message': 'Permission Denied: This plan is locked. Only users with ATC_EDIT permission may modify it.'
        }, status=403)

    today = get_server_today()
    settings = ATCSetting.get_settings()

    if not draft_job:
        date_prefix = today.strftime('%Y%m%d')
        todays_jobs_count = ATCJob.objects.filter(job_id__startswith=f"ATC-{date_prefix}").count()
        seq = todays_jobs_count + 1
        job_id_str = f"ATC-{date_prefix}-{seq:03d}"
        while ATCJob.objects.filter(job_id=job_id_str).exists():
            seq += 1
            job_id_str = f"ATC-{date_prefix}-{seq:03d}"
        draft_job = ATCJob(job_id=job_id_str, created_by=request.user)

    plan_depts = data.get('plan_departments', [])
    daily_targets = data.get('daily_targets', {})
    period_str = data.get('source_data_period', '2024 – 2025')
    signal = data.get('operation_signal', 'ALL')

    from_date_str = data.get('from_date', data.get('op_date'))
    to_date_str = data.get('to_date', data.get('op_date'))
    from_d = today
    to_d = today
    if from_date_str:
        try:
            from_d = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if to_date_str:
        try:
            to_d = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if from_d > to_d:
        return JsonResponse({
            'status': 'error',
            'message': 'From date cannot be after To date.'
        }, status=400)

    if signal in ['OP', 'ALL'] and from_d < today:
        return JsonResponse({
            'status': 'error',
            'message': f"OP automation can only create records for today's application date ({today.strftime('%d-%m-%Y')}) or future. Backdated OP registration is blocked."
        }, status=400)

    # Validate daily_targets: MIN cannot be greater than MAX
    if daily_targets and isinstance(daily_targets, dict):
        for date_k, depts_map in daily_targets.items():
            if isinstance(depts_map, dict):
                for d_k, vals in depts_map.items():
                    if isinstance(vals, dict):
                        d_min = int(vals.get('min', 0) or 0)
                        d_max = int(vals.get('max', 0) or 0)
                        if d_min > d_max:
                            return JsonResponse({
                                'status': 'error',
                                'message': 'Minimum target cannot be greater than maximum target.'
                            }, status=400)

    if plan_depts and isinstance(plan_depts, list):
        configured_depts = [d for d in plan_depts if isinstance(d, dict) and d.get('is_configured') is not False and d.get('department_id')]
        c_ids = [d['department_id'] for d in configured_depts]
        if len(c_ids) != len(set(c_ids)):
            return JsonResponse({
                'status': 'error',
                'message': 'Duplicate department configuration detected. Each department must be unique within an ATC plan.'
            }, status=400)
        for d in plan_depts:
            if isinstance(d, dict):
                d_min = int(d.get('min', 0) or 0)
                d_max = int(d.get('max', 0) or 0)
                if d_min > d_max:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Minimum target cannot be greater than maximum target.'
                    }, status=400)

    from_yr, to_yr = parse_source_period(period_str)

    draft_job.plan_departments = plan_depts
    draft_job.daily_targets = daily_targets
    draft_job.from_date = from_d
    draft_job.to_date = to_d
    draft_job.source_data_period = period_str
    draft_job.operation_signal = signal
    draft_job.source_from_year = from_yr
    draft_job.source_to_year = to_yr
    draft_job.review_source_year = from_yr
    draft_job.mode = ATCJob.ModeChoices.COMBINED

    try:
        draft_job.target_male = int(data.get('male_count', data.get('male_patients', 120)) or 0)
        draft_job.target_female = int(data.get('female_count', data.get('female_patients', 50)) or 0)
        draft_job.child_target = int(data.get('child_count', data.get('child_patients', 30)) or 0)
    except (ValueError, TypeError):
        draft_job.target_male, draft_job.target_female, draft_job.child_target = 120, 50, 30

    draft_job.target_total = draft_job.target_male + draft_job.target_female + draft_job.child_target
    if plan_depts:
        configured_depts = [d for d in plan_depts if isinstance(d, dict) and d.get('is_configured') is not False and d.get('department_id')]
        target_depts = configured_depts if configured_depts else plan_depts
        draft_job.target_total = sum(int(d.get('total', 0) or (int(d.get('male', 0) or 0) + int(d.get('female', 0) or 0) + int(d.get('child', 0) or 0))) for d in target_depts)
        draft_job.target_male = sum(int(d.get('male', 0) or 0) for d in target_depts)
        draft_job.target_female = sum(int(d.get('female', 0) or 0) for d in target_depts)
        draft_job.child_target = sum(int(d.get('child', 0) or 0) for d in target_depts)

    try:
        draft_job.op_daily_pct = int(data.get('op_daily_pct', 75))
        draft_job.review_pct = int(data.get('review_pct', 25))
    except (ValueError, TypeError):
        draft_job.op_daily_pct, draft_job.review_pct = 75, 25

    draft_job.target_op = int(round(draft_job.target_total * (draft_job.op_daily_pct / 100.0)))
    draft_job.target_review = draft_job.target_total - draft_job.target_op

    dept_id = data.get('department_id')
    if dept_id:
        draft_job.department = Department.objects.filter(id=dept_id).first()

    draft_job.status = ATCJob.StatusChoices.DRAFT
    draft_job.is_locked = False
    draft_job.save()

    return JsonResponse({
        'status': 'success',
        'message': 'ATC configuration saved as draft successfully.',
        'job_id': draft_job.id,
        'job_code': draft_job.job_id,
        'departments_count': len(plan_depts)
    })
