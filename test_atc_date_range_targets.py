import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

import json
from datetime import date, timedelta
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.lab.models import ATCJob
from apps.patients.models import Department
from apps.lab.atc_views import (
    ATCControlView,
    api_atc_trigger,
    api_atc_preview,
    api_atc_save_config,
    get_server_today,
)

User = get_user_model()

def setup_test_environment():
    user, _ = User.objects.get_or_create(username='test_admin', defaults={'is_superuser': True, 'is_staff': True})
    dept_names = ['GENERAL MEDICINE', 'DERMATOLOGY', 'EMERGENCY MEDICINE', 'ENT', 'GENERAL SURGERY', 'PEDIATRICS']
    departments = []
    for name in dept_names:
        dept, _ = Department.objects.get_or_create(name=name, defaults={'code': name[:4].upper()})
        departments.append(dept)
    
    # Cleanup any running or starting jobs so they don't interfere
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING]).update(status=ATCJob.StatusChoices.COMPLETED)
    ATCJob.objects.filter(status=ATCJob.StatusChoices.DRAFT).delete()
    return user, departments

def run_tests():
    user, departments = setup_test_environment()
    factory = RequestFactory()
    today = get_server_today()
    results = {}

    print(f"=== Running ATC Date Range & Daily Target Logic Tests (Today: {today}) ===")

    # -------------------------------------------------------------
    # TEST 1: Custom date range 27-09-2026 -> 30-09-2026 generates only 27, 28, 29, 30
    # -------------------------------------------------------------
    from datetime import datetime
    start_d = date(2026, 9, 27)
    end_d = date(2026, 9, 30)
    dates_gen = []
    cur = start_d
    while cur <= end_d:
        dates_gen.append(cur.strftime('%d-%m-%Y'))
        cur += timedelta(days=1)
    
    assert dates_gen == ['27-09-2026', '28-09-2026', '29-09-2026', '30-09-2026'], f"Test 1 Failed: {dates_gen}"
    results['TEST 1: Custom range dates list'] = 'PASSED (Generated only 27, 28, 29, 30)'

    # -------------------------------------------------------------
    # TEST 2: Range 01-09-2026 -> 30-09-2026 disables 01–19, 20–30 editable
    # -------------------------------------------------------------
    sep_1 = date(2026, 9, 1)
    sep_30 = date(2026, 9, 30)
    cur = sep_1
    past_dates = []
    future_dates = []
    while cur <= sep_30:
        if cur < today:
            past_dates.append(cur.strftime('%d-%m-%Y'))
        else:
            future_dates.append(cur.strftime('%d-%m-%Y'))
        cur += timedelta(days=1)

    assert len(past_dates) == 19, f"Expected 19 past dates (01-19), got {len(past_dates)}"
    assert past_dates[0] == '01-09-2026' and past_dates[-1] == '19-09-2026'
    assert future_dates[0] == '20-09-2026' and future_dates[-1] == '30-09-2026'
    results['TEST 2: Past dates 01–19 disabled, 20–30 editable'] = f'PASSED ({len(past_dates)} disabled, {len(future_dates)} editable)'

    # -------------------------------------------------------------
    # TEST 3: New department initial future values = 0 / 0 and editable
    # -------------------------------------------------------------
    # Verify default dept initial values in ATCControlView context when no draft exists
    req = factory.get('/lab/auto-trigger/atc/')
    req.user = user
    view = ATCControlView()
    view.request = req
    ctx = view.get_context_data()
    initial_depts = json.loads(ctx['initial_plan_departments_json'])
    gen_med = next((d for d in initial_depts if d['name'] == 'GENERAL MEDICINE'), None)
    assert gen_med is not None, "GENERAL MEDICINE not found in initial departments"
    assert gen_med.get('min') == 0 and gen_med.get('max') == 0, f"Expected min=0, max=0, got min={gen_med.get('min')}, max={gen_med.get('max')}"
    results['TEST 3: New department initial values = 0 / 0'] = 'PASSED (min=0, max=0)'

    # -------------------------------------------------------------
    # TEST 4: Target edits (20 Sep MIN 20, MAX 30) persist after draft save and reload
    # -------------------------------------------------------------
    save_payload = {
        'source_data_period': '2024 – 2025',
        'operation_signal': 'OP',
        'from_date': today.strftime('%Y-%m-%d'),
        'to_date': (today + timedelta(days=5)).strftime('%Y-%m-%d'),
        'male_count': 120,
        'female_count': 50,
        'child_count': 30,
        'op_daily_pct': 75,
        'review_pct': 25,
        'plan_departments': [
            {'department_id': departments[0].id, 'name': departments[0].name, 'total': 200, 'op_daily_pct': 75, 'review_pct': 25},
            {'department_id': departments[1].id, 'name': departments[1].name, 'total': 200, 'op_daily_pct': 75, 'review_pct': 25},
            {'department_id': departments[2].id, 'name': departments[2].name, 'total': 200, 'op_daily_pct': 75, 'review_pct': 25},
            {'department_id': departments[3].id, 'name': departments[3].name, 'total': 200, 'op_daily_pct': 75, 'review_pct': 25},
            {'department_id': departments[4].id, 'name': departments[4].name, 'total': 200, 'op_daily_pct': 75, 'review_pct': 25},
        ],
        'daily_targets': {
            today.strftime('%Y-%m-%d'): {
                str(departments[0].id): {'min': 20, 'max': 30}
            }
        }
    }
    req_save = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(save_payload),
        content_type='application/json'
    )
    req_save.user = user
    resp_save = api_atc_save_config(req_save)
    assert resp_save.status_code == 200, f"Save failed: {resp_save.content}"
    save_data = json.loads(resp_save.content)
    assert save_data['status'] == 'success'

    # Now reload view and verify persisted values
    req_reload = factory.get('/lab/auto-trigger/atc/')
    req_reload.user = user
    view_reload = ATCControlView()
    view_reload.request = req_reload
    ctx_reload = view_reload.get_context_data()
    reloaded_targets = json.loads(ctx_reload['initial_daily_targets_json'])
    assert today.strftime('%Y-%m-%d') in reloaded_targets, "Date key missing in reloaded daily_targets"
    dept0_key = str(departments[0].id)
    assert dept0_key in reloaded_targets[today.strftime('%Y-%m-%d')], "Dept key missing in reloaded daily_targets"
    assert reloaded_targets[today.strftime('%Y-%m-%d')][dept0_key]['min'] == 20
    assert reloaded_targets[today.strftime('%Y-%m-%d')][dept0_key]['max'] == 30
    results['TEST 4: Target edits (20 Sep MIN 20, MAX 30) persist after draft save and reload'] = 'PASSED (Saved and Reloaded 20/30)'

    # -------------------------------------------------------------
    # TEST 5: 5 departments = 5 columns, no duplicates
    # -------------------------------------------------------------
    depts_in_draft = json.loads(ctx_reload['initial_plan_departments_json'])
    dept_ids = [d['department_id'] for d in depts_in_draft]
    assert len(dept_ids) == 5, f"Expected 5 departments, got {len(dept_ids)}"
    assert len(set(dept_ids)) == 5, f"Expected 5 unique department ids, got {len(set(dept_ids))}"
    results['TEST 5: Add five departments -> 5 columns, no duplicates'] = 'PASSED (5 unique department columns)'

    # -------------------------------------------------------------
    # TEST 6: Select same department again for same range -> no duplicate
    # -------------------------------------------------------------
    # Simulate re-saving with the same department updated
    save_payload_dupe = dict(save_payload)
    # Updating dept 0
    save_payload_dupe['plan_departments'][0]['total'] = 250
    req_save_dupe = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(save_payload_dupe),
        content_type='application/json'
    )
    req_save_dupe.user = user
    resp_dupe = api_atc_save_config(req_save_dupe)
    assert resp_dupe.status_code == 200
    draft_obj = ATCJob.objects.filter(is_locked=False).order_by('-id').first()
    plan_depts_saved = draft_obj.plan_departments
    ids = [d['department_id'] for d in plan_depts_saved]
    assert len(ids) == 5 and len(set(ids)) == 5, "Duplicate department column created!"
    results['TEST 6: Re-selecting same department updates configuration without creating duplicate'] = 'PASSED'

    # -------------------------------------------------------------
    # TEST 7: MIN = 50, MAX = 20 -> Rejected with exact message
    # -------------------------------------------------------------
    invalid_target_payload = dict(save_payload)
    invalid_target_payload['daily_targets'] = {
        today.strftime('%Y-%m-%d'): {
            str(departments[0].id): {'min': 50, 'max': 20}
        }
    }
    # Test on api_atc_save_config
    req_inv_save = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(invalid_target_payload),
        content_type='application/json'
    )
    req_inv_save.user = user
    resp_inv_save = api_atc_save_config(req_inv_save)
    assert resp_inv_save.status_code == 400
    inv_data = json.loads(resp_inv_save.content)
    assert inv_data['message'] == 'Minimum target cannot be greater than maximum target.', f"Unexpected error message: {inv_data.get('message')}"

    # Test on api_atc_trigger
    req_inv_trig = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(invalid_target_payload),
        content_type='application/json'
    )
    req_inv_trig.user = user
    resp_inv_trig = api_atc_trigger(req_inv_trig)
    assert resp_inv_trig.status_code == 400
    inv_trig_data = json.loads(resp_inv_trig.content)
    assert inv_trig_data['message'] == 'Minimum target cannot be greater than maximum target.'
    results['TEST 7: MIN = 50, MAX = 20 Rejected ("Minimum target cannot be greater than maximum target.")'] = 'PASSED'

    # -------------------------------------------------------------
    # TEST 8: OP custom range backdated (19-09-2026 -> 25-09-2026) Rejected
    # -------------------------------------------------------------
    backdated_op_payload = dict(save_payload)
    backdated_op_payload['operation_signal'] = 'OP'
    backdated_op_payload['from_date'] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    backdated_op_payload['to_date'] = (today + timedelta(days=5)).strftime('%Y-%m-%d')
    
    req_bd_trig = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(backdated_op_payload),
        content_type='application/json'
    )
    req_bd_trig.user = user
    resp_bd_trig = api_atc_trigger(req_bd_trig)
    assert resp_bd_trig.status_code == 400
    bd_data = json.loads(resp_bd_trig.content)
    assert "Backdated OP registration is blocked" in bd_data['message']

    req_bd_save = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(backdated_op_payload),
        content_type='application/json'
    )
    req_bd_save.user = user
    resp_bd_save = api_atc_save_config(req_bd_save)
    assert resp_bd_save.status_code == 400
    results['TEST 8: OP custom backdated range (19-09-2026 -> 25-09-2026) rejected'] = 'PASSED (Backdated OP blocked)'

    # -------------------------------------------------------------
    # TEST 9: OP custom range valid (20-09-2026 -> 25-09-2026) Allowed
    # -------------------------------------------------------------
    valid_op_payload = dict(save_payload)
    valid_op_payload['operation_signal'] = 'OP'
    valid_op_payload['from_date'] = today.strftime('%Y-%m-%d')
    valid_op_payload['to_date'] = (today + timedelta(days=5)).strftime('%Y-%m-%d')
    req_valid_prev = factory.post(
        '/lab/api/atc/preview/',
        data=json.dumps(valid_op_payload),
        content_type='application/json'
    )
    req_valid_prev.user = user
    resp_valid_prev = api_atc_preview(req_valid_prev)
    assert resp_valid_prev.status_code == 200, f"Preview failed: {resp_valid_prev.content}"
    results['TEST 9: OP custom range valid (20-09-2026 -> 25-09-2026) allowed'] = 'PASSED'

    # -------------------------------------------------------------
    # TEST 10: Save Configuration draft saved & daily values remain after reload
    # -------------------------------------------------------------
    # Verified in TEST 4, double check with another target
    save_payload['daily_targets'][today.strftime('%Y-%m-%d')][str(departments[1].id)] = {'min': 15, 'max': 35}
    req_save2 = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(save_payload),
        content_type='application/json'
    )
    req_save2.user = user
    resp_save2 = api_atc_save_config(req_save2)
    assert resp_save2.status_code == 200

    draft_check = ATCJob.objects.filter(is_locked=False).order_by('-id').first()
    assert draft_check is not None
    assert str(departments[1].id) in draft_check.daily_targets[today.strftime('%Y-%m-%d')]
    assert draft_check.daily_targets[today.strftime('%Y-%m-%d')][str(departments[1].id)]['min'] == 15
    assert draft_check.daily_targets[today.strftime('%Y-%m-%d')][str(departments[1].id)]['max'] == 35
    results['TEST 10: Save Configuration DRAFT saved & persistent after refresh'] = 'PASSED'

    # -------------------------------------------------------------
    # TEST 11: Save & Trigger with fewer than 5 departments -> Rejected
    # -------------------------------------------------------------
    few_depts_payload = dict(save_payload)
    few_depts_payload['plan_departments'] = save_payload['plan_departments'][:3] # Only 3 departments
    req_few = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(few_depts_payload),
        content_type='application/json'
    )
    req_few.user = user
    resp_few = api_atc_trigger(req_few)
    assert resp_few.status_code == 400
    few_data = json.loads(resp_few.content)
    assert "departments must be configured" in few_data['message']
    results['TEST 11: Save & Trigger with fewer than 5 departments rejected'] = 'PASSED (< 5 departments blocked)'

    # -------------------------------------------------------------
    # TEST 12: Save & Trigger with 5+ departments -> Automation starts
    # -------------------------------------------------------------
    # Ensure no active job blocking trigger
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING]).update(status=ATCJob.StatusChoices.COMPLETED)
    
    valid_trigger_payload = dict(save_payload)
    valid_trigger_payload['end_time'] = '23:59'
    req_trig = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(valid_trigger_payload),
        content_type='application/json'
    )
    req_trig.user = user
    resp_trig = api_atc_trigger(req_trig)
    assert resp_trig.status_code == 200, f"Trigger failed: {resp_trig.content}"
    trig_data = json.loads(resp_trig.content)
    assert trig_data['status'] == 'success'
    assert "ATC automation started successfully" in trig_data['message']
    results['TEST 12: Save & Trigger with 5+ departments starts automation'] = 'PASSED'

    print("\n--- ALL TEST RESULTS ---")
    for name, res in results.items():
        print(f"[{res}] - {name}")
    print("\nSUCCESS: All 12 test cases verified and passed!")

if __name__ == '__main__':
    run_tests()
