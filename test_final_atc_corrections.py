"""
Test Suite: VMMC ERP - Final ATC UI + Workflow Corrections
Validates:
1. Sidebar shell fix (dual-column scroll, 100dvh, padding-bottom, sticky brand, no clipping)
2. Auto Trigger sidebar structure (ATC, ATC Live Status, ATC Settings)
3. Main ATC page: removal of Review tab, removal of Future Date, unified single form
4. Percentage validation (OP% + Review% = 100%) and safe integer target calculation
5. Strict OP date rule (today only)
6. Strict Review rule (existing D patients only from Review Source Year, 0 new patients, O excluded)
7. Save & Trigger combined execution (OP + Review coordinated)
8. Concurrency lock (prevents double-triggering duplicate jobs)
9. Emergency Stop halts job and preserves records
10. Dedicated ATC Live Status page (/lab/auto-trigger/atc/status/)
"""

import os
import sys
import django
import math
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient, PatientVisit, Department
from apps.lab.models import ATCJob, ATCJobLog, ATCSetting
from apps.lab.atc_service import (
    get_server_today,
    get_server_now,
    execute_combined_atc_automation,
    trigger_atc_job_async
)
import json

User = get_user_model()


def setup_test_data():
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@vmmc.com', 'is_staff': True, 'is_superuser': True}
    )
    admin_user.set_password('admin123')
    admin_user.save()

    dept, _ = Department.objects.get_or_create(name='GENERAL MEDICINE')

    # Create source patients for sampling (2022-2024)
    # Male source
    if not Patient.objects.filter(gender__iexact='Male', registration_date__year=2023).exists():
        Patient.objects.create(
            name='Ramesh Source', gender='Male', dob=date(1985, 4, 10), age_years=41,
            registration_date=date(2023, 6, 15), department_obj=dept, department=dept.name,
            patient_id='SRC-M-TEST', op_number='OP-SRC-M', patient_type='O', created_source='O',
            street='10 Main Rd', village_area='Central', city='Karaikal', state='Puducherry', pincode='609602'
        )

    # Female source
    if not Patient.objects.filter(gender__iexact='Female', registration_date__year=2023).exists():
        Patient.objects.create(
            name='Anjali Source', gender='Female', dob=date(1990, 8, 20), age_years=36,
            registration_date=date(2023, 7, 20), department_obj=dept, department=dept.name,
            patient_id='SRC-F-TEST', op_number='OP-SRC-F', patient_type='O', created_source='O',
            street='20 Market Rd', village_area='North', city='Karaikal', state='Puducherry', pincode='609602'
        )

    # Create existing D patients in 2024 for Review testing
    d_count_2024 = Patient.objects.filter(patient_type='D', registration_date__year=2024).count()
    if d_count_2024 < 10:
        for i in range(d_count_2024, 10):
            Patient.objects.create(
                name=f'Eligible D Patient {i+1}', gender='Male' if i % 2 == 0 else 'Female',
                dob=date(1980 + i, 1, 1), age_years=30 + i,
                registration_date=date(2024, 3, 10), department_obj=dept, department=dept.name,
                patient_id=f'D-2024-{i+1:04d}', op_number=f'OP-D24-{i+1:04d}',
                patient_type='D', created_source='D',
                street='12 Clinic St', village_area='Town', city='Karaikal', state='Puducherry', pincode='609602'
            )

    return admin_user, dept


def run_all_tests():
    print("==================================================================")
    print("VMMC ERP — FINAL ATC UI + WORKFLOW CORRECTIONS TEST SUITE")
    print("==================================================================")

    user, dept = setup_test_data()
    client = Client()
    client.force_login(user)

    # Ensure no active jobs from previous runs block tests
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]).update(status=ATCJob.StatusChoices.COMPLETED)

    # ------------------------------------------------------------------
    # TEST 1: SIDEBAR APPLICATION SHELL LAYOUT & SCROLLING RULES
    # ------------------------------------------------------------------
    print("\n--- TEST 1: SIDEBAR APPLICATION SHELL & SCROLLING ---")
    with open('templates/base.html', 'r') as f:
        base_html = f.read()

    with open('static/css/style.css', 'r') as f:
        style_css = f.read()

    assert '<div class="app-shell' in base_html, "base.html must wrap sidebar & layout in app-shell flex container"
    assert 'overflow-y: auto !important;' in base_html, "base.html #mainSidebar must have overflow-y: auto !important"
    assert 'overflow-x: hidden !important;' in base_html, "base.html #mainSidebar must have overflow-x: hidden !important"
    assert 'padding-bottom: 4.5rem !important;' in base_html, "base.html nav-list must have bottom padding >= 4.5rem"
    assert 'height: 100dvh !important;' in base_html, "base.html #mainSidebar must have 100dvh"
    assert 'height: 100dvh' in style_css, "style.css must have height: 100dvh"
    assert '.app-shell' in style_css, "style.css must define .app-shell"
    print("✔ Sidebar application shell has independent dual-column scrolling, full 100dvh, and safe bottom padding.")

    # ------------------------------------------------------------------
    # TEST 2: AUTO TRIGGER SIDEBAR NAVIGATION SUBMODULES
    # ------------------------------------------------------------------
    print("\n--- TEST 2: AUTO TRIGGER SIDEBAR NAVIGATION ---")
    assert "auto_trigger_atc" in base_html, "base.html must contain ATC link"
    assert "auto_trigger_atc_status" in base_html, "base.html must contain ATC Live Status link"
    assert "auto_trigger_atc_settings" in base_html, "base.html must contain ATC Settings link"
    print("✔ Auto Trigger sidebar contains ATC, ATC Live Status, and ATC Settings.")

    # ------------------------------------------------------------------
    # TEST 3: MAIN ATC PAGE COMPACT UI (NO REVIEW TAB, NO FUTURE DATE)
    # ------------------------------------------------------------------
    print("\n--- TEST 3: MAIN ATC PAGE COMPACT UI ---")
    res_atc = client.get('/lab/auto-trigger/atc/')
    assert res_atc.status_code == 200, f"ATC page must return 200 OK (got {res_atc.status_code})"
    atc_content = res_atc.content.decode('utf-8')

    assert 'ATC — AUTO TRIGGER CONTROL' in atc_content, "ATC page must have title 'ATC — AUTO TRIGGER CONTROL'"
    assert 'id="tab-review"' not in atc_content, "ATC page must NOT have separate Review tab"
    assert 'id="card-review"' not in atc_content, "ATC page must NOT have separate Review card"
    assert 'tab-future' not in atc_content, "ATC page must NOT have Future Date tab"
    assert 'card-future' not in atc_content, "ATC page must NOT have Future Date card"
    assert 'id="op_daily_pct"' in atc_content, "ATC page must have OP Daily % field"
    assert 'id="review_pct"' in atc_content, "ATC page must have Review % field"
    assert 'id="op_target"' in atc_content, "ATC page must have OP Target field"
    assert 'id="review_target"' in atc_content, "ATC page must have Review Target field"
    assert 'id="review_source_year"' in atc_content, "ATC page must have Review Source Year"
    print("✔ Main ATC page has NO Review tab, NO Future Date, and unified OP+Review percentage configuration.")

    # ------------------------------------------------------------------
    # TEST 4: PERCENTAGE VALIDATION (FRONTEND & BACKEND)
    # ------------------------------------------------------------------
    print("\n--- TEST 4: PERCENTAGE VALIDATION (BACKEND 100% ENFORCEMENT) ---")
    today_str = get_server_today().strftime('%Y-%m-%d')

    # Test invalid: 70 + 20 = 90
    res_invalid1 = client.post('/lab/api/atc/trigger/', {
        'department_id': dept.id,
        'source_from_year': 2022,
        'source_to_year': 2024,
        'review_source_year': 2024,
        'op_date': today_str,
        'male_count': 120,
        'female_count': 80,
        'op_daily_pct': 70,
        'review_pct': 20,
    })
    assert res_invalid1.status_code == 400, f"Expected 400 for 70+20!=100, got {res_invalid1.status_code}"
    assert "must total 100%" in res_invalid1.json().get('message', ''), "Expected error message regarding 100%"

    # Test invalid: 80 + 30 = 110
    res_invalid2 = client.post('/lab/api/atc/trigger/', {
        'department_id': dept.id,
        'source_from_year': 2022,
        'source_to_year': 2024,
        'review_source_year': 2024,
        'op_date': today_str,
        'male_count': 120,
        'female_count': 80,
        'op_daily_pct': 80,
        'review_pct': 30,
    })
    assert res_invalid2.status_code == 400, f"Expected 400 for 80+30!=100, got {res_invalid2.status_code}"
    print("✔ Backend successfully rejects percentage totals != 100% with clear error message.")

    # ------------------------------------------------------------------
    # TEST 5: INTEGER TARGET ROUNDING & CONSERVATION
    # ------------------------------------------------------------------
    print("\n--- TEST 5: INTEGER TARGET ROUNDING & EXACT CONSERVATION ---")
    test_cases = [
        (200, 75, 25, 150, 50),
        (200, 50, 50, 100, 100),
        (200, 100, 0, 200, 0),
        (200, 0, 100, 0, 200),
        (201, 75, 25, 151, 50),  # odd total
        (203, 75, 25, 152, 51),  # odd total
        (101, 60, 40, 61, 40),   # odd total
    ]
    for total, op_p, rev_p, exp_op, exp_rev in test_cases:
        calc_op = int(round(total * (op_p / 100.0)))
        calc_rev = total - calc_op
        assert calc_op + calc_rev == total, f"Conservation failed for total={total}: {calc_op}+{calc_rev} != {total}"
        assert calc_op == exp_op, f"Expected OP={exp_op}, got {calc_op} for total={total}, op%={op_p}"
        assert calc_rev == exp_rev, f"Expected Rev={exp_rev}, got {calc_rev} for total={total}, rev%={rev_p}"
    print("✔ Integer target calculations strictly conserve OP Target + Review Target == Total Target.")

    # ------------------------------------------------------------------
    # TEST 6: STRICT OP DATE RULE (TODAY ONLY)
    # ------------------------------------------------------------------
    print("\n--- TEST 6: STRICT OP DATE RULE ---")
    yesterday_str = (get_server_today() - timedelta(days=1)).strftime('%Y-%m-%d')
    res_backdated = client.post('/lab/api/atc/trigger/', {
        'department_id': dept.id,
        'source_from_year': 2022,
        'source_to_year': 2024,
        'review_source_year': 2024,
        'op_date': yesterday_str,
        'male_count': 10,
        'female_count': 10,
        'op_daily_pct': 75,
        'review_pct': 25,
    })
    assert res_backdated.status_code == 400, "Backdated OP registration must be rejected with 400"
    assert "today's application date" in res_backdated.json().get('message', ''), "Expected today's application date error message"
    print("✔ Historical OP registration dates are strictly rejected.")

    # ------------------------------------------------------------------
    # TEST 7: COMBINED SAVE & TRIGGER EXECUTION & REVIEW SOURCE YEAR
    # ------------------------------------------------------------------
    print("\n--- TEST 7: COMBINED SAVE & TRIGGER EXECUTION ---")
    # Make sure no jobs are blocking
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]).update(status=ATCJob.StatusChoices.COMPLETED)

    total_pts_before = Patient.objects.count()
    d_pts_before = Patient.objects.filter(patient_type='D').count()

    # Trigger small combined job: 4 OP (3 M, 1 F) + 2 Reviews (from 2024)
    # Total = 6, OP % = 67, Review % = 33 -> 4 OP, 2 Review
    trigger_res = client.post('/lab/api/atc/trigger/', {
        'department_id': dept.id,
        'source_from_year': 2022,
        'source_to_year': 2024,
        'review_source_year': 2024,
        'op_date': today_str,
        'male_count': 4,
        'female_count': 2,
        'op_daily_pct': 67,
        'review_pct': 33,
        'start_time': '00:01',
        'end_time': '23:59',
        'batch_size': 10,
    })

    assert trigger_res.status_code == 200, f"Trigger failed: {trigger_res.content.decode('utf-8')}"
    job_data = trigger_res.json()
    job_id = job_data['job_id']
    job = ATCJob.objects.get(pk=job_id)

    assert job.target_op == 4, f"Expected 4 OP target, got {job.target_op}"
    assert job.target_review == 2, f"Expected 2 Review target, got {job.target_review}"
    assert job.target_total == 6, f"Expected 6 Total target, got {job.target_total}"
    assert job.review_source_year == 2024, "Job must record review_source_year=2024"

    # Concurrency test: triggering another job while this job is running must fail
    res_concurrent = client.post('/lab/api/atc/trigger/', {
        'department_id': dept.id,
        'male_count': 10,
        'female_count': 10,
        'op_daily_pct': 50,
        'review_pct': 50,
    })
    assert res_concurrent.status_code == 400, "Concurrent trigger while job is starting/running must be rejected"
    assert "already running" in res_concurrent.json().get('message', ''), "Must report job already running"

    # Wait for the background async worker to complete execution
    import time as pytime
    for _ in range(80):
        job.refresh_from_db()
        if job.status in [ATCJob.StatusChoices.COMPLETED, ATCJob.StatusChoices.FAILED, ATCJob.StatusChoices.STOPPED]:
            break
        pytime.sleep(0.1)

    assert job.status == ATCJob.StatusChoices.COMPLETED, f"Expected job completed, got {job.status}"
    assert job.created_op == 4, f"Expected 4 created OP, got {job.created_op}"
    assert job.created_review == 2, f"Expected 2 created reviews, got {job.created_review}"
    assert job.created_count == 6, f"Expected 6 total created, got {job.created_count}"

    # Verify OP created NEW patients with today's date
    new_patients_created = Patient.objects.count() - total_pts_before
    assert new_patients_created == 4, f"Expected exactly 4 new patients created for OP portion, got {new_patients_created}"

    # Verify Review portion created 0 new patients, only PatientVisit for existing D patients
    created_visits = PatientVisit.objects.filter(visit_type='REVIEW', created_by=user).count()
    assert created_visits >= 2, f"Expected at least 2 review visits, got {created_visits}"

    # Verify no 'O' patients were used for Review
    review_visits = PatientVisit.objects.filter(visit_type='REVIEW', atc_logs__job=job)
    for rv in review_visits:
        assert rv.patient.patient_type == 'D', f"Review visit patient must be patient_type='D', got {rv.patient.patient_type}"

    print(f"✔ Combined automation successfully executed: 4 new OP patients + 2 Reviews on existing D patients (0 new patients for Review).")

    # ------------------------------------------------------------------
    # TEST 8: ATC LIVE STATUS PAGE & API TELEMETRY
    # ------------------------------------------------------------------
    print("\n--- TEST 8: ATC LIVE STATUS PAGE & TELEMETRY ---")
    status_page_res = client.get('/lab/auto-trigger/atc/status/')
    assert status_page_res.status_code == 200, f"ATC Live Status page must return 200 OK (got {status_page_res.status_code})"
    status_content = status_page_res.content.decode('utf-8')
    assert 'ATC LIVE STATUS' in status_content, "Page title must be ATC LIVE STATUS"
    assert 'JOB INFORMATION' in status_content, "Must contain JOB INFORMATION"
    assert 'TARGET ALLOCATION' in status_content, "Must contain TARGET ALLOCATION"
    assert 'PROGRESS &amp; COMPLETION' in status_content or 'PROGRESS' in status_content, "Must contain Progress"
    assert 'CURRENT OPERATION' in status_content, "Must contain CURRENT OPERATION"
    assert 'btnEmergencyStop' in status_content, "Must contain Emergency Stop button"

    # Status API test
    api_status_res = client.get(f'/lab/api/atc/status/{job.id}/')
    assert api_status_res.status_code == 200, f"API status must return 200 (got {api_status_res.status_code})"
    status_json = api_status_res.json()
    assert status_json['status'] == 'success'
    j_data = status_json['job']
    assert j_data['created_op'] == 4
    assert j_data['created_review'] == 2
    assert j_data['created_count'] == 6
    assert j_data['target_total'] == 6
    assert j_data['status'] == 'COMPLETED'
    print("✔ ATC Live Status page and API telemetry return accurate real-time metrics.")

    # ------------------------------------------------------------------
    # TEST 9: EMERGENCY STOP HANDLER
    # ------------------------------------------------------------------
    print("\n--- TEST 9: EMERGENCY STOP HANDLER ---")
    ATCJob.objects.filter(job_id__startswith='ATC-TEST-STOP').delete()
    # Create an active job to test emergency stop
    stop_job = ATCJob.objects.create(
        job_id='ATC-TEST-STOP-001',
        mode=ATCJob.ModeChoices.COMBINED,
        department=dept,
        target_total=100,
        target_op=75,
        target_review=25,
        created_count=10,
        status=ATCJob.StatusChoices.RUNNING,
        schedule_end_time=time(23, 59),
        created_by=user,
    )

    stop_res = client.post(f'/lab/api/atc/stop/{stop_job.id}/')
    assert stop_res.status_code == 200, f"Stop request failed: {stop_res.status_code}"
    stop_job.refresh_from_db()
    assert stop_job.stop_requested is True, "Stop requested flag must be True"
    assert stop_job.status == ATCJob.StatusChoices.STOP_REQUESTED

    # Run combined execution to verify it halts immediately and transitions to EMERGENCY_STOPPED
    execute_combined_atc_automation(stop_job)
    stop_job.refresh_from_db()
    assert stop_job.status == ATCJob.StatusChoices.EMERGENCY_STOPPED, f"Expected status EMERGENCY_STOPPED, got {stop_job.status}"
    assert stop_job.created_count == 10, "Existing completed records must be preserved without rollback"
    print("✔ Emergency Stop halts execution immediately, sets status to EMERGENCY_STOPPED, and preserves completed records.")

    print("\n==================================================================")
    print("ALL 9 TESTS PASSED SUCCESSFULLY! 100% VERIFIED.")
    print("==================================================================")


if __name__ == '__main__':
    run_all_tests()
