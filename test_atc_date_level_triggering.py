import os
import django
import json
from datetime import date, timedelta
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.lab.models import ATCJob
from apps.patients.models import Department
from apps.lab.atc_views import (
    ATCControlView,
    api_atc_trigger,
    api_atc_stop,
    api_atc_date_statuses,
    get_plan_date_statuses,
    recover_stale_atc_jobs,
    get_server_today,
)
from apps.lab.atc_service import is_job_thread_alive

User = get_user_model()


def setup_test_environment():
    user, _ = User.objects.get_or_create(
        username='test_atc_admin',
        defaults={'is_superuser': True, 'is_staff': True}
    )
    dept_names = ['GENERAL MEDICINE', 'DERMATOLOGY', 'EMERGENCY MEDICINE', 'ENT', 'GENERAL SURGERY']
    departments = []
    for name in dept_names:
        dept, _ = Department.objects.get_or_create(name=name, defaults={'code': name[:4].upper()})
        departments.append(dept)

    # Clean up test jobs
    ATCJob.objects.filter(job_id__startswith="ATC-TEST-").delete()

    return user, departments


def run_tests():
    user, departments = setup_test_environment()
    factory = RequestFactory()
    today = get_server_today()
    results = {}

    print(f"==================================================================")
    print(f"=== Running ATC Date-Level Triggering & Status Tests (Today: {today}) ===")
    print(f"==================================================================")

    # Mock payload with 5 configured departments
    plan_depts_payload = [
        {
            'department_id': d.id,
            'name': d.name,
            'source_data_period': '2024 – 2025',
            'signal': 'ALL',
            'male': 30,
            'female': 20,
            'child': 10,
            'total': 60,
            'op_daily_pct': 75,
            'review_pct': 25,
            'op_target': 45,
            'review_target': 15,
            'min': 50,
            'max': 100,
            'is_configured': True,
        }
        for d in departments
    ]

    base_payload = {
        'source_data_period': '2024 – 2025',
        'operation_signal': 'ALL',
        'from_date': today.strftime('%Y-%m-%d'),
        'to_date': (today + timedelta(days=10)).strftime('%Y-%m-%d'),
        'op_daily_pct': 75,
        'review_pct': 25,
        'plan_departments': plan_depts_payload,
        'daily_targets': {},
    }

    d21 = today
    d22 = today + timedelta(days=1)
    d23 = today + timedelta(days=2)
    d24 = today + timedelta(days=3)

    d21_str = d21.strftime('%Y-%m-%d')
    d22_str = d22.strftime('%Y-%m-%d')
    d23_str = d23.strftime('%Y-%m-%d')
    d24_str = d24.strftime('%Y-%m-%d')

    # Ensure no lingering active jobs for our test dates
    ATCJob.objects.filter(automation_date__in=[d21, d22, d23, d24]).delete()

    # -------------------------------------------------------------
    # TEST 1: Initial state before any execution - all dates READY
    # -------------------------------------------------------------
    st = get_plan_date_statuses(from_d=d21, to_d=d23, configured_depts_count=5)
    assert st[d21_str]['status'] == 'READY', f"Expected {d21_str} to be READY, got {st[d21_str]['status']}"
    assert st[d22_str]['status'] == 'READY', f"Expected {d22_str} to be READY, got {st[d22_str]['status']}"
    assert st[d23_str]['status'] == 'READY', f"Expected {d23_str} to be READY, got {st[d23_str]['status']}"
    results['TEST 1: Initial Date States'] = 'PASSED (21, 22, 23 Sep are independent READY)'
    print("✓ TEST 1: Initial Date States: PASSED")

    # -------------------------------------------------------------
    # TEST 2: Trigger 21-09-2026 -> 21 RUNNING, 22 READY, 23 READY
    # -------------------------------------------------------------
    with patch('apps.lab.atc_views.trigger_atc_job_async') as mock_async:
        req = factory.post(
            '/lab/api/atc/trigger/',
            data=json.dumps({**base_payload, 'automation_date': d21_str, 'selected_date': d21_str}),
            content_type='application/json'
        )
        req.user = user
        res = api_atc_trigger(req)
        res_data = json.loads(res.content)
        assert res.status_code == 200, f"Trigger failed: {res_data}"
        assert res_data['status'] == 'success', f"Expected success: {res_data}"
        job_id_21 = res_data['job_id']
        job_21 = ATCJob.objects.get(job_id=job_id_21)
        assert job_21.automation_date == d21, f"Expected automation_date={d21}, got {job_21.automation_date}"
        assert job_21.status in [ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING]

    st = get_plan_date_statuses(from_d=d21, to_d=d23, configured_depts_count=5)
    assert st[d21_str]['status'] == 'RUNNING', f"Expected 21 to be RUNNING, got {st[d21_str]['status']}"
    assert st[d22_str]['status'] == 'READY', f"Expected 22 to be READY, got {st[d22_str]['status']}"
    assert st[d23_str]['status'] == 'READY', f"Expected 23 to be READY, got {st[d23_str]['status']}"
    results['TEST 2: Trigger 21-09-2026 (Independent State)'] = f"PASSED ({d21_str} RUNNING, {d22_str} READY, {d23_str} READY)"
    print(f"✓ TEST 2: Trigger {d21_str}: PASSED (21 RUNNING, 22 READY, 23 READY)")

    # -------------------------------------------------------------
    # TEST 3: Duplicate trigger for currently running date is rejected
    # -------------------------------------------------------------
    req_dup_running = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps({**base_payload, 'automation_date': d21_str, 'selected_date': d21_str}),
        content_type='application/json'
    )
    req_dup_running.user = user
    res_dup_running = api_atc_trigger(req_dup_running)
    res_dup_running_data = json.loads(res_dup_running.content)
    assert res_dup_running.status_code == 400, f"Expected 400 duplicate running error, got {res_dup_running.status_code}"
    assert f"Automation is currently running for {d21.strftime('%d-%m-%Y')}" in res_dup_running_data['message']
    results['TEST 3: Running Date Duplicate Rejection'] = 'PASSED (Duplicate trigger rejected with clear running error)'
    print("✓ TEST 3: Running Date Duplicate Rejection: PASSED")

    # -------------------------------------------------------------
    # TEST 4: Complete 21-09-2026 -> 21 COMPLETED, 22 READY, 23 READY
    # -------------------------------------------------------------
    job_21.status = ATCJob.StatusChoices.COMPLETED
    job_21.created_count = job_21.target_total
    job_21.save(update_fields=['status', 'created_count'])

    st = get_plan_date_statuses(from_d=d21, to_d=d23, configured_depts_count=5)
    assert st[d21_str]['status'] == 'COMPLETED', f"Expected 21 to be COMPLETED, got {st[d21_str]['status']}"
    assert st[d22_str]['status'] == 'READY', f"Expected 22 to be READY, got {st[d22_str]['status']}"
    assert st[d23_str]['status'] == 'READY', f"Expected 23 to be READY, got {st[d23_str]['status']}"
    results['TEST 4: Complete 21-09-2026'] = f"PASSED ({d21_str} COMPLETED, {d22_str} READY, {d23_str} READY)"
    print(f"✓ TEST 4: Complete {d21_str}: PASSED (21 COMPLETED, 22 READY, 23 READY)")

    # -------------------------------------------------------------
    # TEST 5: Duplicate trigger for completed date is rejected
    # -------------------------------------------------------------
    req_dup_completed = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps({**base_payload, 'automation_date': d21_str, 'selected_date': d21_str}),
        content_type='application/json'
    )
    req_dup_completed.user = user
    res_dup_completed = api_atc_trigger(req_dup_completed)
    res_dup_completed_data = json.loads(res_dup_completed.content)
    assert res_dup_completed.status_code == 400, f"Expected 400 duplicate completed error, got {res_dup_completed.status_code}"
    assert f"Automation already completed for {d21.strftime('%d-%m-%Y')}" in res_dup_completed_data['message']
    results['TEST 5: Completed Date Duplicate Rejection'] = 'PASSED (Duplicate trigger rejected with "Automation already completed for <date>.")'
    print("✓ TEST 5: Completed Date Duplicate Rejection: PASSED")

    # -------------------------------------------------------------
    # TEST 6: Trigger 22-09-2026 succeeds without global lock blocking it
    # -------------------------------------------------------------
    with patch('apps.lab.atc_views.trigger_atc_job_async') as mock_async:
        req_22 = factory.post(
            '/lab/api/atc/trigger/',
            data=json.dumps({**base_payload, 'automation_date': d22_str, 'selected_date': d22_str}),
            content_type='application/json'
        )
        req_22.user = user
        res_22 = api_atc_trigger(req_22)
        res_22_data = json.loads(res_22.content)
        assert res_22.status_code == 200, f"Trigger for {d22_str} failed: {res_22_data}"
        job_id_22 = res_22_data['job_id']
        job_22 = ATCJob.objects.get(job_id=job_id_22)
        assert job_22.automation_date == d22

    st = get_plan_date_statuses(from_d=d21, to_d=d23, configured_depts_count=5)
    assert st[d21_str]['status'] == 'COMPLETED'
    assert st[d22_str]['status'] == 'RUNNING'
    assert st[d23_str]['status'] == 'READY'
    results['TEST 6: Trigger 22-09-2026 without Global Lock'] = 'PASSED (21 COMPLETED, 22 RUNNING, 23 READY)'
    print(f"✓ TEST 6: Trigger {d22_str} without Global Lock: PASSED (21 COMPLETED, 22 RUNNING, 23 READY)")

    # -------------------------------------------------------------
    # TEST 7: Emergency Stop halts ONLY 22-09-2026; others unaffected
    # -------------------------------------------------------------
    req_stop = factory.post(
        f'/lab/api/atc/stop/{job_22.id}/',
        data=json.dumps({'automation_date': d22_str, 'selected_date': d22_str}),
        content_type='application/json'
    )
    req_stop.user = user
    res_stop = api_atc_stop(req_stop, job_id=job_22.id)
    res_stop_data = json.loads(res_stop.content)
    assert res_stop.status_code == 200, f"Stop failed: {res_stop_data}"

    job_22.refresh_from_db()
    assert job_22.status in [ATCJob.StatusChoices.STOPPED, ATCJob.StatusChoices.EMERGENCY_STOPPED, ATCJob.StatusChoices.STOP_REQUESTED]
    assert job_22.stopped_at is not None, "stopped_at timestamp must be recorded"

    # For status view check
    job_22.status = ATCJob.StatusChoices.STOPPED
    job_22.save(update_fields=['status'])

    st = get_plan_date_statuses(from_d=d21, to_d=d23, configured_depts_count=5)
    assert st[d21_str]['status'] == 'COMPLETED', "21 must remain COMPLETED"
    assert st[d22_str]['status'] == 'STOPPED', "22 must be STOPPED"
    assert st[d23_str]['status'] == 'READY', "23 must remain READY"
    results['TEST 7: Date-specific Emergency Stop'] = 'PASSED (22 STOPPED with stopped_at timestamp; 21 COMPLETED, 23 READY)'
    print("✓ TEST 7: Date-specific Emergency Stop: PASSED")

    # -------------------------------------------------------------
    # TEST 8: Status Persistence via GET /lab/api/atc/date-statuses/
    # -------------------------------------------------------------
    req_status = factory.get(f'/lab/api/atc/date-statuses/?from_date={d21_str}&to_date={d23_str}')
    req_status.user = user
    res_status = api_atc_date_statuses(req_status)
    res_status_data = json.loads(res_status.content)
    assert res_status_data['status'] == 'success'
    persisted_st = res_status_data['date_statuses']
    assert persisted_st[d21_str]['status'] == 'COMPLETED'
    assert persisted_st[d22_str]['status'] == 'STOPPED'
    assert persisted_st[d23_str]['status'] == 'READY'
    results['TEST 8: DB Status Persistence on Page Refresh / API'] = 'PASSED (Statuses persisted directly in DB)'
    print("✓ TEST 8: DB Status Persistence on Refresh / API: PASSED")

    # -------------------------------------------------------------
    # TEST 9: Legacy Job ATC-20260920-039 does not block other dates
    # -------------------------------------------------------------
    legacy_job, _ = ATCJob.objects.get_or_create(
        job_id="ATC-20260920-039",
        defaults={
            'from_date': date(2026, 9, 20),
            'to_date': date(2026, 9, 20),
            'automation_date': date(2026, 9, 20),
            'status': ATCJob.StatusChoices.STARTING,
            'source_from_year': 2024,
            'source_to_year': 2025,
            'review_source_year': 2024,
            'target_total': 100,
        }
    )

    # Now attempt to trigger 23-09-2026
    with patch('apps.lab.atc_views.trigger_atc_job_async') as mock_async:
        req_23 = factory.post(
            '/lab/api/atc/trigger/',
            data=json.dumps({**base_payload, 'automation_date': d23_str, 'selected_date': d23_str}),
            content_type='application/json'
        )
        req_23.user = user
        res_23 = api_atc_trigger(req_23)
        res_23_data = json.loads(res_23.content)
        assert res_23.status_code == 200, f"Trigger for {d23_str} blocked by legacy job: {res_23_data}"
        assert res_23_data['status'] == 'success'
    results['TEST 9: Legacy Job Non-Interference'] = 'PASSED (ATC-20260920-039 from 20-09 does not block 23-09)'
    print("✓ TEST 9: Legacy Job Non-Interference: PASSED")

    # Clean up test jobs
    ATCJob.objects.filter(automation_date__in=[d21, d22, d23, d24]).delete()

    print("\n======================= TEST SUMMARY =======================")
    for test_name, result in results.items():
        print(f"  {test_name}: {result}")
    print("============================================================\n")


if __name__ == '__main__':
    run_tests()
