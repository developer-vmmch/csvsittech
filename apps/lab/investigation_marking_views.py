import json
from datetime import datetime, date
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.patients.models import Department
from apps.lab.models import InvestigationMarkingConfig
from apps.lab.services.investigation_marking_service import InvestigationMarkingService


@login_required
def investigation_marking_view(request):
    """
    Main Investigation Marking operational UI view.
    Simple, compact, and grouped under Auto Trigger.
    """
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date(2026, 9, 20)
    else:
        # Default to 2026-09-20 if available, else today
        selected_date = date(2026, 9, 20)

    # All active hospital departments
    departments = Department.objects.filter(is_active=True).order_by('name')

    # Load existing config for this date if present
    config = InvestigationMarkingConfig.objects.filter(marking_date=selected_date).first()
    config_departments = []
    preview_patients = []
    grand_totals = {'male': 0, 'female': 0, 'total': 0}
    added_dept_ids = []

    if config:
        config_departments = list(config.departments.all())
        preview_patients = list(config.selected_patients.all())
        grand_totals = {
            'male': config.total_male,
            'female': config.total_female,
            'total': config.total_patients,
        }
        added_dept_ids = [d.department_id for d in config_departments]

    context = {
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'departments': departments,
        'config': config,
        'config_departments': config_departments,
        'preview_patients': preview_patients,
        'grand_totals': grand_totals,
        'added_dept_ids': added_dept_ids,
    }
    return render(request, 'lab/auto_trigger/investigation_marking.html', context)


def _build_config_json(marking_date):
    """Helper to return JSON response for a given marking date."""
    config = InvestigationMarkingConfig.objects.filter(marking_date=marking_date).first()
    if not config:
        return JsonResponse({
            'success': True,
            'config_status': 'DRAFT',
            'departments': [],
            'patients': [],
            'grand_totals': {'male': 0, 'female': 0, 'total': 0},
            'added_dept_ids': []
        })

    depts_data = [
        {
            'id': d.department_id,
            'name': d.department_name,
            'male': d.male_count,
            'female': d.female_count,
            'total': d.total_count,
        }
        for d in config.departments.all()
    ]

    patients_data = [
        {
            'patient_id': p.patient_id_str,
            'name': p.patient_name,
            'age': p.age_display,
            'gender': p.gender,
            'department': p.department_name,
            'diagnosis': p.primary_diagnosis_name,
            'investigations_count': p.investigations_count,
        }
        for p in config.selected_patients.all()
    ]

    return JsonResponse({
        'success': True,
        'config_status': config.status,
        'departments': depts_data,
        'patients': patients_data,
        'grand_totals': {
            'male': config.total_male,
            'female': config.total_female,
            'total': config.total_patients,
        },
        'added_dept_ids': [d.department_id for d in config.departments.all()]
    })


@login_required
@require_GET
def api_marking_load(request):
    """Loads configuration, department list, and persisted preview patients for a date."""
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'success': False, 'message': 'Date parameter is required.'})

    try:
        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid date format (YYYY-MM-DD required).'})

    return _build_config_json(marking_date)


@login_required
@require_POST
def api_marking_add_department(request):
    """Validates and adds department, randomly sampling D patients."""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        dept_id = data.get('department_id')
        male_count = int(data.get('male_count') or 0)
        female_count = int(data.get('female_count') or 0)

        if not date_str or not dept_id:
            return JsonResponse({'success': False, 'message': 'Date and Department are required.'})

        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        config = InvestigationMarkingService.get_or_create_config(marking_date, user=request.user)

        InvestigationMarkingService.add_department(
            config=config,
            department_id=dept_id,
            male_count=male_count,
            female_count=female_count,
            user=request.user
        )

        return _build_config_json(marking_date)
    except ValueError as ve:
        return JsonResponse({'success': False, 'message': str(ve)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {e}'})


@login_required
@require_POST
def api_marking_remove_department(request):
    """Removes department and all associated sampled patients."""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        dept_id = data.get('department_id')

        if not date_str or not dept_id:
            return JsonResponse({'success': False, 'message': 'Date and Department ID are required.'})

        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        config = InvestigationMarkingConfig.objects.filter(marking_date=marking_date).first()
        if config:
            InvestigationMarkingService.remove_department(config, dept_id)

        return _build_config_json(marking_date)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {e}'})


@login_required
@require_POST
def api_marking_save_configuration(request):
    """Saves the current configuration and persists all selections."""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        if not date_str:
            return JsonResponse({'success': False, 'message': 'Date is required.'})

        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        config = InvestigationMarkingConfig.objects.filter(marking_date=marking_date).first()
        if not config or not config.departments.exists():
            return JsonResponse({'success': False, 'message': 'Please add at least one department before saving.'})

        InvestigationMarkingService.save_configuration(config, user=request.user)
        return JsonResponse({'success': True, 'message': f'Configuration for {date_str} saved successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Server error: {e}'})


@login_required
@require_POST
def api_marking_trigger(request):
    """Executes Save & Trigger workflow."""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        if not date_str:
            return JsonResponse({'success': False, 'message': 'Date is required.'})

        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        config = InvestigationMarkingConfig.objects.filter(marking_date=marking_date).first()
        if not config or not config.departments.exists():
            return JsonResponse({'success': False, 'message': 'Please add at least one department before triggering.'})

        InvestigationMarkingService.trigger_investigations(config, user=request.user)
        return JsonResponse({
            'success': True,
            'message': f'Successfully triggered investigations for {config.total_patients} patients across {config.departments.count()} departments.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Trigger failed: {e}'})


@login_required
@require_POST
def api_marking_clear(request):
    """Clears all departments and selected patients for a date."""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        if not date_str:
            return JsonResponse({'success': False, 'message': 'Date is required.'})

        marking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        config = InvestigationMarkingConfig.objects.filter(marking_date=marking_date).first()
        if config:
            InvestigationMarkingService.clear_configuration(config)

        return JsonResponse({'success': True, 'message': 'Configuration cleared.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Clear failed: {e}'})
