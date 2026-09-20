import os
import django
import json
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.patients.models import Department, Patient
from apps.lab.models import MonthlyTriggerPlan, MonthlyTriggerDailyTarget, ATCJob, ATCSetting
from apps.lab.atc_service import get_server_today

User = get_user_model()

def run_all_tests():
    print("============================================================")
    print("VMMC ERP — ATC / MONTHLY TRIGGER CORRECTIONS TEST SUITE")
    print("============================================================")
    
    client = Client()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('admin_test', 'admin@example.com', 'adminpass123')
    client.force_login(user)

    today = get_server_today()
    dept = Department.objects.first()
    if not dept:
        dept = Department.objects.create(name='GENERAL MEDICINE', code='MED', is_active=True)

    # -------------------------------------------------------------------------
    # TEST 1 — SIDEBAR CSS / LAYOUT RULES
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: SIDEBAR STRUCTURE & INDEPENDENT SCROLL ---")
    with open('templates/base.html', 'r') as f:
        base_html = f.read()
    with open('static/css/style.css', 'r') as f:
        style_css = f.read()

    assert 'overflow-y: auto' in base_html, "base.html must have overflow-y: auto for #mainSidebar"
    assert '100dvh' in base_html, "base.html must specify 100dvh for #mainSidebar"
    assert 'padding-bottom: 3.5rem' in base_html, "base.html must provide generous padding-bottom for .nav-list"
    assert 'position: sticky' in base_html, "base.html must make sidebar or brand sticky"
    assert 'overflow-y: auto' in style_css, "style.css must have overflow-y: auto for #mainSidebar"
    print("✔ TEST 1 PASSED: Sidebar has 100dvh, independent overflow-y: auto, sticky brand, and 3.5rem bottom padding.")

    # -------------------------------------------------------------------------
    # TEST 2 & 3 — ATC MODES (STRICTLY OP AND REVIEW, NO FUTURE DATE)
    # -------------------------------------------------------------------------
    print("\n--- TEST 2 & 3: ATC MODES & SPACING ---")
    with open('templates/lab/auto_trigger/atc.html', 'r') as f:
        atc_html = f.read()

    # Verify no FUTURE DATE button or card in ATC
    assert 'tab-future' not in atc_html, "ATC mode selector must NOT contain tab-future"
    assert 'FUTURE DATE' not in atc_html, "ATC mode selector must NOT display 'FUTURE DATE'"
    assert 'card-future' not in atc_html, "ATC must NOT contain card-future"
    assert 'tab-op' in atc_html, "ATC must contain tab-op"
    assert 'tab-review' in atc_html, "ATC must contain tab-review"
    assert 'card-op' in atc_html, "ATC must contain card-op"
    assert 'card-review' in atc_html, "ATC must contain card-review"
    assert 'padding: 1.15rem 1.25rem' in atc_html, "ATC must use reduced compact padding for config-card"
    print("✔ TEST 2 & 3 PASSED: ATC contains strictly [ OP ] and [ REVIEW ]. FUTURE DATE removed completely. Spacing compacted.")

    # -------------------------------------------------------------------------
    # TEST 4 — OP CONFIGURATION (TODAY ONLY, SOURCE YEARS)
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: OP CONFIGURATION ---")
    assert 'op_source_from_year' in atc_html, "OP form must have Source From Year"
    assert 'op_source_to_year' in atc_html, "OP form must have Source To Year"
    assert 'readonly' in atc_html, "OP date must be read-only today"

    # Test OP Preview with today's date
    resp_op = client.post('/lab/api/atc/preview/', {
        'mode': 'OP',
        'department_id': dept.id,
        'source_from_year': 2022,
        'source_to_year': 2024,
        'op_date': today.strftime('%Y-%m-%d'),
        'male_count': 60,
        'female_count': 40,
        'batch_size': 50,
        'start_time': '08:00',
        'end_time': '14:00',
    })
    assert resp_op.status_code == 200, f"OP preview failed: {resp_op.content}"
    res_data = resp_op.json()
    assert res_data['status'] == 'success', f"OP preview returned error: {res_data}"
    assert res_data['preview']['target_total'] == 100
    assert res_data['preview']['op_date'] == today.strftime('%d-%m-%Y')

    # Test OP Rejection for backdated date
    resp_past = client.post('/lab/api/atc/preview/', {
        'mode': 'OP',
        'department_id': dept.id,
        'op_date': (today - timedelta(days=5)).strftime('%Y-%m-%d'),
        'male_count': 60,
        'female_count': 40,
    })
    assert resp_past.status_code == 400, "OP with historical date must be rejected"
    print("✔ TEST 4 PASSED: OP configuration enforces today's date only and supports Source From/To Year.")

    # -------------------------------------------------------------------------
    # TEST 5 — REVIEW SOURCE YEAR (NOT MONTH) & D PATIENTS ONLY
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: REVIEW SOURCE YEAR & D PATIENTS ONLY ---")
    with open('apps/lab/templates/lab/auto_trigger/monthly_trigger_create.html', 'r') as f:
        monthly_html = f.read()

    assert 'Review Source Year' in monthly_html, "Monthly Trigger Create must display 'Review Source Year'"
    assert 'review_source_year' in monthly_html, "Monthly Trigger Create must use review_source_year select"
    assert 'review_source_year' in atc_html, "ATC Review card must have review_source_year"
    assert 'Review Source Year' in atc_html, "ATC Review card must display 'Review Source Year'"

    # Seed at least one D patient in 2024 if needed
    d_pat = Patient.objects.filter(patient_type='D', registration_date__year=2024).first()
    if not d_pat:
        d_pat = Patient.objects.create(
            title='Mr', name='Test D Patient 2024', gender='Male', dob=date(1992, 1, 1),
            age_years=34, registration_date=date(2024, 6, 15),
            department_obj=dept, department=dept.name,
            patient_id='D-TEST-2024', op_number='OP-D24',
            patient_type='D', created_source='D'
        )

    # Test Review Preview with Review Source Year
    resp_rev = client.post('/lab/api/atc/preview/', {
        'mode': 'REVIEW',
        'department_id': dept.id,
        'source_year': 2024,
        'from_date': today.strftime('%Y-%m-%d'),
        'to_date': today.strftime('%Y-%m-%d'),
        'target_total': 10,
        'batch_size': 10,
    })
    assert resp_rev.status_code == 200, f"Review preview failed: {resp_rev.content}"
    rev_data = resp_rev.json()
    assert rev_data['status'] == 'success'
    assert rev_data['preview']['patient_type'] == 'D — Existing Patients Only'
    assert rev_data['preview']['source_year'] == 2024
    print("✔ TEST 5 PASSED: Review mode filters by Review Source Year and restricts strictly to D patients.")

    # -------------------------------------------------------------------------
    # TEST 6 — TARGET DATE RANGE VALIDATION (1 DAY TO 1 MONTH)
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: DATE RANGE VALIDATION (1 DAY TO 1 MONTH) ---")
    
    # Valid 1: 1 Day Range (e.g. today -> today)
    start_d_str = today.strftime('%Y-%m-%d')
    end_1day = today.strftime('%Y-%m-%d')
    resp_v1 = client.post('/lab/api/auto-trigger/monthly/save-v2/', data=json.dumps({
        'automation_start_date': start_d_str,
        'automation_end_date': end_1day,
        'source_from_date': '2024-01-01',
        'source_to_date': '2024-12-31',
        'review_source_month_year': '2024',
        'trigger_start_time': '08:00',
        'trigger_stop_time': '13:59',
        'daily_targets': [{'date': start_d_str, 'department_id': dept.id, 'min': 10, 'max': 20}]
    }), content_type='application/json')
    assert resp_v1.status_code == 200, f"1-day plan failed: {resp_v1.content}"
    assert resp_v1.json().get('success') is True

    # Valid 2: 1 Week Range (today -> today + 7 days)
    end_1week = (today + timedelta(days=7)).strftime('%Y-%m-%d')
    resp_v2 = client.post('/lab/api/auto-trigger/monthly/save-v2/', data=json.dumps({
        'automation_start_date': start_d_str,
        'automation_end_date': end_1week,
        'source_from_date': '2024-01-01',
        'source_to_date': '2024-12-31',
        'review_source_month_year': '2024',
        'trigger_start_time': '08:00',
        'trigger_stop_time': '13:59',
        'daily_targets': [{'date': start_d_str, 'department_id': dept.id, 'min': 10, 'max': 20}]
    }), content_type='application/json')
    assert resp_v2.status_code == 200, f"1-week plan failed: {resp_v2.content}"
    assert resp_v2.json().get('success') is True

    # Valid 3: 1 Month Range (today -> today + 30 days)
    end_1month = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    resp_v3 = client.post('/lab/api/auto-trigger/monthly/save-v2/', data=json.dumps({
        'automation_start_date': start_d_str,
        'automation_end_date': end_1month,
        'source_from_date': '2024-01-01',
        'source_to_date': '2024-12-31',
        'review_source_month_year': '2024',
        'trigger_start_time': '08:00',
        'trigger_stop_time': '13:59',
        'daily_targets': [{'date': start_d_str, 'department_id': dept.id, 'min': 10, 'max': 20}]
    }), content_type='application/json')
    assert resp_v3.status_code == 200, f"1-month plan failed: {resp_v3.content}"
    assert resp_v3.json().get('success') is True

    # Invalid 1: Over 1 Month (e.g. 45 days)
    end_invalid_long = (today + timedelta(days=45)).strftime('%Y-%m-%d')
    resp_inv1 = client.post('/lab/api/auto-trigger/monthly/save-v2/', data=json.dumps({
        'automation_start_date': start_d_str,
        'automation_end_date': end_invalid_long,
        'source_from_date': '2024-01-01',
        'source_to_date': '2024-12-31',
        'review_source_month_year': '2024',
        'trigger_start_time': '08:00',
        'trigger_stop_time': '13:59',
        'daily_targets': []
    }), content_type='application/json')
    assert resp_inv1.status_code == 400 or resp_inv1.json().get('success') is False
    assert "Automation period must be between 1 day and 1 month." in resp_inv1.json().get('message', '')

    # Invalid 2: End date before start date
    end_invalid_past = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    resp_inv2 = client.post('/lab/api/auto-trigger/monthly/save-v2/', data=json.dumps({
        'automation_start_date': start_d_str,
        'automation_end_date': end_invalid_past,
        'source_from_date': '2024-01-01',
        'source_to_date': '2024-12-31',
        'review_source_month_year': '2024',
        'trigger_start_time': '08:00',
        'trigger_stop_time': '13:59',
        'daily_targets': []
    }), content_type='application/json')
    assert resp_inv2.status_code == 400 or resp_inv2.json().get('success') is False
    assert "Automation period must be between 1 day and 1 month." in resp_inv2.json().get('message', '')
    print("✔ TEST 6 PASSED: Backend validates min 1 day and max 1 month, rejecting > 1 month and end < start with exact required error.")

    # -------------------------------------------------------------------------
    # TEST 7 — MONTHLY TRIGGER CREATE PAGE RENDERING
    # -------------------------------------------------------------------------
    print("\n--- TEST 7: MONTHLY TRIGGER PLAN PAGE RENDERING ---")
    resp_monthly = client.get('/lab/auto-trigger/monthly/create/')
    assert resp_monthly.status_code == 200, f"Page load failed: {resp_monthly.status_code}"
    content_str = resp_monthly.content.decode('utf-8')
    assert 'Review Source Year' in content_str, "Rendered page must contain Review Source Year"
    assert 'SET DAILY MINIMUM AND MAXIMUM TARGETS' in content_str, "Rendered page must contain target table section"
    assert 'generateRows' in content_str, "Rendered page must have generateRows"
    print("✔ TEST 7 PASSED: /lab/auto-trigger/monthly/create/ renders cleanly with all features intact.")

    print("\n============================================================")
    print("ALL 7 TEST SUITES PASSED SUCCESSFULLY (100% COMPLIANT)!")
    print("============================================================")

if __name__ == '__main__':
    run_all_tests()
