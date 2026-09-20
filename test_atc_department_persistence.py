import os
import django
import json
from datetime import date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.patients.models import Department
from apps.lab.models import ATCJob, ATCSetting
from apps.lab.atc_views import ATCControlView, api_atc_save_config, api_atc_trigger, api_atc_preview

User = get_user_model()

def run_tests():
    print("======================================================================")
    print("RUNNING ATC DEPARTMENT SAVE + DAILY TARGET PERSISTENCE TEST SUITE")
    print("======================================================================")

    # Setup test user and permissions
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('testadmin', 'testadmin@vmmc.com', 'adminpass123')
    user.save()

    # Clean up any existing draft or active ATC jobs to start fresh
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.DRAFT, ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING]).delete()

    factory = RequestFactory()

    # Ensure required departments exist
    dept_derm = Department.objects.filter(name__iexact='DERMATOLOGY').first()
    if not dept_derm:
        dept_derm = Department.objects.create(name='DERMATOLOGY', is_active=True)

    dept_gm = Department.objects.filter(name__iexact='GENERAL MEDICINE').first()
    if not dept_gm:
        dept_gm = Department.objects.create(name='GENERAL MEDICINE', is_active=True)

    dept_ent = Department.objects.filter(name__iexact='ENT').first()
    if not dept_ent:
        dept_ent = Department.objects.create(name='ENT', is_active=True)

    dept_gs = Department.objects.filter(name__iexact='GENERAL SURGERY').first()
    if not dept_gs:
        dept_gs = Department.objects.create(name='GENERAL SURGERY', is_active=True)

    dept_em = Department.objects.filter(name__iexact='EMERGENCY MEDICINE').first()
    if not dept_em:
        dept_em = Department.objects.create(name='EMERGENCY MEDICINE', is_active=True)

    # -------------------------------------------------------------------------
    # TEST 1: Initial Page Load (Requirement 15, 28)
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: Initial Page Load ---")
    req = factory.get('/lab/auto-trigger/atc/')
    req.user = user
    view = ATCControlView()
    view.request = req
    context = view.get_context_data()

    plan_depts = json.loads(context['initial_plan_departments_json'])
    print(f"Loaded {len(plan_depts)} initial department columns:")
    for d in plan_depts:
        print(f"  - {d['name']}: is_configured={d.get('is_configured')}, min={d.get('min')}, max={d.get('max')}")
        assert d.get('is_configured') is False, f"Department {d['name']} should initially be unconfigured!"
        assert d.get('min') == 0 and d.get('max') == 0, f"Unconfigured department {d['name']} must show 0/0!"

    print("✓ Test 1 Passed: Initial departments have is_configured=False and MIN=0, MAX=0.")

    # -------------------------------------------------------------------------
    # TEST 2: Save Dermatology (Requirement 1, 2, 3, 28)
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Save Dermatology Configuration ---")
    # Date Range: 01-10-2026 -> 31-10-2026
    # Quotas: Male 200, Female 50, Child 15, Total 265, OP 80%, Review 20%
    # Targets: OP 212, Review 53, MIN 100, MAX 200
    from_date = "2026-10-01"
    to_date = "2026-10-31"

    # Generate daily targets across October for Dermatology
    oct_dates = [f"2026-10-{d:02d}" for d in range(1, 32)]
    daily_targets_payload = {}
    for dt in oct_dates:
        daily_targets_payload[dt] = {
            str(dept_derm.id): {"min": 100, "max": 200, "is_manual": False}
        }

    derm_dept_obj = {
        'department_id': dept_derm.id,
        'name': dept_derm.name,
        'source_data_period': '2024 – 2025',
        'signal': 'ALL',
        'male': 200,
        'female': 50,
        'child': 15,
        'total': 265,
        'op_daily_pct': 80,
        'review_pct': 20,
        'op_target': 212,
        'review_target': 53,
        'min': 100,
        'max': 200,
        'is_configured': True,
    }

    # Update plan_depts list with Dermatology configured
    updated_plan_depts = []
    for d in plan_depts:
        if d['department_id'] == dept_derm.id:
            updated_plan_depts.append(derm_dept_obj)
        else:
            updated_plan_depts.append(d)

    payload_save_derm = {
        'department_id': dept_derm.id,
        'source_data_period': '2024 – 2025',
        'operation_signal': 'ALL',
        'from_date': from_date,
        'to_date': to_date,
        'op_date': from_date,
        'male_count': 200,
        'female_count': 50,
        'child_count': 15,
        'op_daily_pct': 80,
        'review_pct': 20,
        'plan_departments': updated_plan_depts,
        'daily_targets': daily_targets_payload,
    }

    req_save = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(payload_save_derm),
        content_type='application/json'
    )
    req_save.user = user
    resp_save = api_atc_save_config(req_save)
    res_data = json.loads(resp_save.content)
    assert res_data['status'] == 'success', f"Save draft failed: {res_data}"
    print(f"✓ api_atc_save_config succeeded: {res_data['message']}")

    # Verify in DB
    draft = ATCJob.objects.filter(status=ATCJob.StatusChoices.DRAFT).first()
    assert draft is not None, "Draft ATCJob was not created!"
    assert draft.from_date == date(2026, 10, 1)
    assert draft.to_date == date(2026, 10, 31)
    assert draft.target_total == 265
    assert draft.target_male == 200
    assert draft.target_female == 50
    assert draft.child_target == 15
    assert draft.target_op == 212
    assert draft.target_review == 53
    print("✓ DB Draft Job totals and dates match Dermatology input.")

    # Check daily_targets in DB for Dermatology
    for dt in oct_dates:
        t_data = draft.daily_targets.get(dt, {}).get(str(dept_derm.id), {})
        assert t_data.get('min') == 100 and t_data.get('max') == 200, f"Date {dt} for Dermatology was not 100/200: {t_data}"
    print("✓ DB Draft Job daily targets for all 31 October dates are MIN=100, MAX=200 (NOT 0/0).")

    # -------------------------------------------------------------------------
    # TEST 3: Full Page Refresh After Saving Dermatology (Requirement 26, 28)
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Page Refresh After Saving Dermatology ---")
    req_refresh = factory.get('/lab/auto-trigger/atc/')
    req_refresh.user = user
    view_refresh = ATCControlView()
    view_refresh.request = req_refresh
    ctx_refresh = view_refresh.get_context_data()

    reloaded_depts = json.loads(ctx_refresh['initial_plan_departments_json'])
    reloaded_targets = json.loads(ctx_refresh['initial_daily_targets_json'])

    derm_reloaded = next((d for d in reloaded_depts if d['department_id'] == dept_derm.id), None)
    assert derm_reloaded is not None, "Dermatology missing after page refresh!"
    assert derm_reloaded['is_configured'] is True, "Dermatology must remain is_configured=True!"
    assert derm_reloaded['min'] == 100 and derm_reloaded['max'] == 200, "Dermatology min/max must remain 100/200!"
    assert derm_reloaded['total'] == 265, "Dermatology total must remain 265!"

    # Unconfigured depts should remain unconfigured
    for d in reloaded_depts:
        if d['department_id'] != dept_derm.id:
            assert d.get('is_configured') is False, f"{d['name']} should remain unconfigured!"
            assert d.get('min') == 0 and d.get('max') == 0, f"{d['name']} min/max must be 0/0!"

    print("✓ Test 3 Passed: Page refresh preserves Dermatology configuration and unconfigured status of other departments.")

    # -------------------------------------------------------------------------
    # TEST 4: Manual Daily Target Override on 15-Oct-2026 (Requirement 16, 28)
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Manual Daily Target Override (15 Oct: 150 / 250) ---")
    daily_targets_payload["2026-10-15"][str(dept_derm.id)] = {"min": 150, "max": 250, "is_manual": True}

    payload_override = {
        'department_id': dept_derm.id,
        'source_data_period': '2024 – 2025',
        'operation_signal': 'ALL',
        'from_date': from_date,
        'to_date': to_date,
        'op_date': from_date,
        'male_count': 200,
        'female_count': 50,
        'child_count': 15,
        'op_daily_pct': 80,
        'review_pct': 20,
        'plan_departments': updated_plan_depts,
        'daily_targets': daily_targets_payload,
    }

    req_override = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(payload_override),
        content_type='application/json'
    )
    req_override.user = user
    resp_override = api_atc_save_config(req_override)
    assert json.loads(resp_override.content)['status'] == 'success'

    # Refresh page from DB
    req_ref2 = factory.get('/lab/auto-trigger/atc/')
    req_ref2.user = user
    view_ref2 = ATCControlView()
    view_ref2.request = req_ref2
    ctx_ref2 = view_ref2.get_context_data()
    targets_ref2 = json.loads(ctx_ref2['initial_daily_targets_json'])

    oct15 = targets_ref2.get("2026-10-15", {}).get(str(dept_derm.id), {})
    assert oct15.get('min') == 150 and oct15.get('max') == 250, f"15 Oct should be 150/250, found: {oct15}"

    oct01 = targets_ref2.get("2026-10-01", {}).get(str(dept_derm.id), {})
    assert oct01.get('min') == 100 and oct01.get('max') == 200, f"01 Oct should remain 100/200, found: {oct01}"

    print(f"✓ 15 Oct Dermatology target is {oct15['min']}/{oct15['max']} (override preserved).")
    print(f"✓ 01 Oct Dermatology target is {oct01['min']}/{oct01['max']} (default preserved).")

    # -------------------------------------------------------------------------
    # TEST 5: Configure Second Department — GENERAL MEDICINE (Requirement 4, 29)
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Configure General Medicine (MIN=50, MAX=100) ---")
    # General Medicine: MIN=50, MAX=100, Male=120, Female=50, Child=30 (Total=200)
    gm_dept_obj = {
        'department_id': dept_gm.id,
        'name': dept_gm.name,
        'source_data_period': '2024 – 2025',
        'signal': 'ALL',
        'male': 120,
        'female': 50,
        'child': 30,
        'total': 200,
        'op_daily_pct': 75,
        'review_pct': 25,
        'op_target': 150,
        'review_target': 50,
        'min': 50,
        'max': 100,
        'is_configured': True,
    }

    # Populate daily targets for General Medicine
    for dt in oct_dates:
        daily_targets_payload[dt][str(dept_gm.id)] = {"min": 50, "max": 100, "is_manual": False}

    depts_after_gm = []
    for d in updated_plan_depts:
        if d['department_id'] == dept_gm.id:
            depts_after_gm.append(gm_dept_obj)
        else:
            depts_after_gm.append(d)

    payload_save_gm = {
        'department_id': dept_gm.id,
        'source_data_period': '2024 – 2025',
        'operation_signal': 'ALL',
        'from_date': from_date,
        'to_date': to_date,
        'op_date': from_date,
        'male_count': 120,
        'female_count': 50,
        'child_count': 30,
        'op_daily_pct': 75,
        'review_pct': 25,
        'plan_departments': depts_after_gm,
        'daily_targets': daily_targets_payload,
    }

    req_save_gm = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(payload_save_gm),
        content_type='application/json'
    )
    req_save_gm.user = user
    resp_save_gm = api_atc_save_config(req_save_gm)
    assert json.loads(resp_save_gm.content)['status'] == 'success'

    # Refresh page
    req_ref3 = factory.get('/lab/auto-trigger/atc/')
    req_ref3.user = user
    view_ref3 = ATCControlView()
    view_ref3.request = req_ref3
    ctx_ref3 = view_ref3.get_context_data()

    depts_ref3 = json.loads(ctx_ref3['initial_plan_departments_json'])
    targets_ref3 = json.loads(ctx_ref3['initial_daily_targets_json'])

    derm3 = next(d for d in depts_ref3 if d['department_id'] == dept_derm.id)
    gm3 = next(d for d in depts_ref3 if d['department_id'] == dept_gm.id)

    assert derm3['min'] == 100 and derm3['max'] == 200, "Dermatology must remain 100/200!"
    assert gm3['min'] == 50 and gm3['max'] == 100, "General Medicine must become 50/100!"

    # Verify daily target cells on refresh
    assert targets_ref3["2026-10-01"][str(dept_derm.id)]['min'] == 100
    assert targets_ref3["2026-10-01"][str(dept_derm.id)]['max'] == 200
    assert targets_ref3["2026-10-15"][str(dept_derm.id)]['min'] == 150
    assert targets_ref3["2026-10-15"][str(dept_derm.id)]['max'] == 250

    assert targets_ref3["2026-10-01"][str(dept_gm.id)]['min'] == 50
    assert targets_ref3["2026-10-01"][str(dept_gm.id)]['max'] == 100

    print("✓ Test 5 Passed: Dermatology remains 100/200 (15 Oct=150/250) and General Medicine is 50/100. Neither resets the other.")

    # -------------------------------------------------------------------------
    # TEST 6: Duplicate Department Detection (Requirement 13)
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: Duplicate Department Rejection ---")
    dup_depts = list(depts_after_gm) + [gm_dept_obj]  # duplicate General Medicine
    payload_dup = dict(payload_save_gm)
    payload_dup['plan_departments'] = dup_depts

    req_dup = factory.post(
        '/lab/api/atc/save-config/',
        data=json.dumps(payload_dup),
        content_type='application/json'
    )
    req_dup.user = user
    resp_dup = api_atc_save_config(req_dup)
    assert resp_dup.status_code == 400
    res_dup_data = json.loads(resp_dup.content)
    assert 'Duplicate department' in res_dup_data['message']
    print(f"✓ Test 6 Passed: Duplicate department successfully rejected ({res_dup_data['message']}).")

    # -------------------------------------------------------------------------
    # TEST 7: Minimum 5 Departments Rule for Save & Trigger (Requirement 21)
    # -------------------------------------------------------------------------
    print("\n--- TEST 7: Save & Trigger Validation (Min 5 Departments) ---")
    # Currently only 2 departments configured (Derm, GM)
    req_trig_fail = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(payload_save_gm),
        content_type='application/json'
    )
    req_trig_fail.user = user
    resp_trig_fail = api_atc_trigger(req_trig_fail)
    assert resp_trig_fail.status_code == 400
    fail_data = json.loads(resp_trig_fail.content)
    assert 'At least 5 different departments' in fail_data['message']
    print(f"✓ Trigger rejected with < 5 configured depts: {fail_data['message']}")

    # Configure 3 more departments: ENT, General Surgery, Emergency Medicine
    depts_full = []
    for d in depts_after_gm:
        if d['department_id'] in [dept_ent.id, dept_gs.id, dept_em.id]:
            d_copy = dict(d)
            d_copy['is_configured'] = True
            d_copy['min'] = 30
            d_copy['max'] = 60
            d_copy['total'] = 100
            d_copy['male'] = 60
            d_copy['female'] = 30
            d_copy['child'] = 10
            depts_full.append(d_copy)
            for dt in oct_dates:
                daily_targets_payload[dt][str(d['department_id'])] = {"min": 30, "max": 60, "is_manual": False}
        else:
            depts_full.append(d)

    configured_count = sum(1 for d in depts_full if d.get('is_configured'))
    print(f"Configured departments count now: {configured_count} / 5")
    assert configured_count == 5

    payload_trigger = dict(payload_save_gm)
    payload_trigger['plan_departments'] = depts_full
    payload_trigger['daily_targets'] = daily_targets_payload

    # Preview API check
    req_preview = factory.post(
        '/lab/api/atc/preview/',
        data=json.dumps(payload_trigger),
        content_type='application/json'
    )
    req_preview.user = user
    resp_preview = api_atc_preview(req_preview)
    p_data = json.loads(resp_preview.content)
    assert p_data['status'] == 'success'
    assert p_data['preview']['departments_count'] == 5
    print(f"✓ api_atc_preview reports {p_data['preview']['departments_count']} configured departments, Total target: {p_data['preview']['target_total']}")

    # Trigger API check
    req_trig_ok = factory.post(
        '/lab/api/atc/trigger/',
        data=json.dumps(payload_trigger),
        content_type='application/json'
    )
    req_trig_ok.user = user
    resp_trig_ok = api_atc_trigger(req_trig_ok)
    ok_data = json.loads(resp_trig_ok.content)
    assert ok_data['status'] == 'success'
    print(f"✓ Trigger succeeded: {ok_data['message']}, Job ID: {ok_data['job_code']}")

    triggered_job = ATCJob.objects.get(pk=ok_data['job_id'])
    assert triggered_job.is_locked is True
    print(f"✓ Triggered ATC job #{triggered_job.job_id} is locked for execution.")

    print("\n======================================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! 100% PERSISTENCE & FLOW VERIFIED.")
    print("======================================================================")

if __name__ == '__main__':
    run_tests()
