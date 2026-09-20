import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.patients.models import Department
from apps.lab.models import ATCJob

User = get_user_model()

def test_html_rendering():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('testadmin2', 'test2@vmmc.com', 'adminpass123')

    client = Client()
    client.force_login(user)

    # 1. Clean slate GET
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.DRAFT, ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING]).delete()
    resp = client.get('/lab/auto-trigger/atc/')
    assert resp.status_code == 200
    html = resp.content.decode('utf-8')

    assert '<select class="form-control" id="department_select"' in html
    assert '-- Select Department --' in html
    assert 'id="dept_min"' in html
    assert 'id="dept_max"' in html
    assert 'id="dailyTargetsTable"' in html
    assert 'addOrUpdateDepartment()' in html
    assert 'resetConfigForm()' in html
    assert 'updateDepartmentDropdownState()' in html
    assert 'editDepartment(' in html
    print("✓ Clean state HTML contains all required elements and functions.")

    # 2. Save a Draft with Dermatology (Requirement 28)
    dept_derm = Department.objects.filter(name__iexact='DERMATOLOGY').first()
    oct_dates = [f"2026-10-{d:02d}" for d in range(1, 32)]
    daily_targets = {}
    for dt in oct_dates:
        daily_targets[dt] = {str(dept_derm.id): {"min": 100, "max": 200}}
    daily_targets["2026-10-15"][str(dept_derm.id)] = {"min": 150, "max": 250, "is_manual": True}

    derm_obj = {
        'department_id': dept_derm.id,
        'name': dept_derm.name,
        'male': 200, 'female': 50, 'child': 15, 'total': 265,
        'op_daily_pct': 80, 'review_pct': 20,
        'min': 100, 'max': 200,
        'is_configured': True,
    }

    save_payload = {
        'from_date': '2026-10-01',
        'to_date': '2026-10-31',
        'department_id': dept_derm.id,
        'male_count': 200, 'female_count': 50, 'child_count': 15,
        'op_daily_pct': 80, 'review_pct': 20,
        'plan_departments': [derm_obj],
        'daily_targets': daily_targets,
    }

    save_resp = client.post('/lab/api/atc/save-config/', data=json.dumps(save_payload), content_type='application/json')
    assert save_resp.status_code == 200
    print("✓ Saved Draft successfully via Client POST.")

    # 3. Reload GET and check rendered context in HTML
    resp2 = client.get('/lab/auto-trigger/atc/')
    assert resp2.status_code == 200
    html2 = resp2.content.decode('utf-8')

    # Verify that initial_plan_departments_json and initial_daily_targets_json are in HTML
    assert f'"department_id": {dept_derm.id}' in html2
    assert '"is_configured": true' in html2
    assert '"2026-10-15"' in html2
    assert '"min": 150' in html2
    assert '"max": 250' in html2
    assert '"2026-10-01"' in html2
    assert '"min": 100' in html2
    assert '"max": 200' in html2
    print("✓ Reloaded HTML correctly contains saved Dermatology configuration and 15 Oct manual override in JSON payload.")
    print("ALL HTML RENDERING TESTS PASSED.")

if __name__ == '__main__':
    test_html_rendering()
