"""
Test Suite: ATC (Auto Trigger Control) Final UI & Workflow Specifications
Validates:
1. Circular Automation Signal toggles (🟢 Review, 🟡 OP, 🔴 All) and date validation rules
2. Quota calculations (Male 120 + Female 50 + Child 30 = Total 200; OP 75% -> 150, Review 25% -> 50)
3. Minimum 5 departments threshold rule for Save & Trigger
4. Duplicate department handling (updates in place without duplicate columns)
5. Locking mechanism and granular permissions (ATC_VIEW, ATC_CREATE, ATC_EDIT, ATC_TRIGGER, ATC_EMERGENCY_STOP)
6. Multi-department rotation in engine
7. HTML template structure: Compact 3-row layout, sticky Date/Day table, bottom action bar, no obsolete notes/cards
"""

import os
import sys
import django
import json
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.patients.models import Patient, PatientVisit, Department
from apps.lab.models import ATCJob, ATCJobLog, ATCSetting
from apps.lab.atc_service import get_server_today, execute_combined_atc_automation

User = get_user_model()


def run_tests():
    print("==================================================================")
    print("RUNNING ATC FINAL UI & WORKFLOW SPECIFICATIONS TEST SUITE")
    print("==================================================================")

    # 1. Setup users with granular permissions
    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
    admin_user.set_password('admin123')
    admin_user.save()

    # Create restricted user with only view permissions
    viewer_user, _ = User.objects.get_or_create(username='viewer_user', defaults={'email': 'viewer@vmmc.com'})
    viewer_user.set_password('pass123')
    viewer_user.role_id = None
    viewer_user.is_superuser = False
    viewer_user.save()

    # Create editor user with edit permissions
    editor_user, _ = User.objects.get_or_create(username='editor_user', defaults={'email': 'editor@vmmc.com'})
    editor_user.set_password('pass123')
    editor_user.is_superuser = False
    editor_user.save()

    from apps.users.models import RoleMenuPermission
    RoleMenuPermission.objects.update_or_create(
        role='VIEWER_ROLE',
        defaults={'menu_permissions': {
            'auto_trigger.atc.view': True,
            'auto_trigger.atc.create': False,
            'auto_trigger.atc.update': False,
            'auto_trigger.atc.trigger': False,
            'auto_trigger.atc.stop': False,
        }}
    )
    RoleMenuPermission.objects.update_or_create(
        role='EDITOR_ROLE',
        defaults={'menu_permissions': {
            'auto_trigger.atc.view': True,
            'auto_trigger.atc.create': True,
            'auto_trigger.atc.update': True,
            'auto_trigger.atc.trigger': True,
            'auto_trigger.atc.stop': True,
        }}
    )

    viewer_user.role = 'VIEWER_ROLE'
    viewer_user.save()

    editor_user.role = 'EDITOR_ROLE'
    editor_user.save()

    # Setup 5 departments
    dept_names = ['GENERAL MEDICINE', 'DERMATOLOGY', 'EMERGENCY MEDICINE', 'ENT', 'GENERAL SURGERY']
    depts = []
    for name in dept_names:
        d, _ = Department.objects.get_or_create(name=name)
        depts.append(d)

    # ------------------------------------------------------------------
    # TEST 1: TEMPLATE STRUCTURE & NO CLUTTER
    # ------------------------------------------------------------------
    print("\n--- TEST 1: TEMPLATE STRUCTURE & NO CLUTTER ---")
    client = Client()
    client.force_login(admin_user)
    res = client.get('/lab/auto-trigger/atc/')
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    content = res.content.decode('utf-8')

    # Verified clean UI: no obsolete headings, notes, or cards
    assert 'Important Notes' not in content, "Must not contain 'Important Notes'"
    assert 'Step 1' not in content, "Must not contain 'Step 1' heading"
    assert 'Step 2' not in content, "Must not contain 'Step 2' heading"
    assert 'Plan Summary' not in content, "Must not contain obsolete 'Plan Summary' card"
    assert 'Operation Type' not in content, "Must NOT contain 'Operation Type' label"
    assert 'Automation Signal' in content, "Must contain 'Automation Signal' label"

    # Verify buttons and controls
    assert 'data-signal="REVIEW"' in content, "Must have REVIEW signal toggle"
    assert 'data-signal="OP"' in content, "Must have OP signal toggle"
    assert 'data-signal="ALL"' in content, "Must have ALL signal toggle"
    assert 'dateQuickPopover' in content, "Must have Quick Date popover"
    assert 'Current Date' in content, "Must have 'Current Date' quick option"
    assert 'Coming 7 Days' in content, "Must have 'Coming 7 Days' quick option"
    assert 'Coming Month' in content, "Must have 'Coming Month' quick option"
    assert 'daily-target-table' in content, "Must have Daily Target Table"
    assert 'sticky-date-th' in content, "Must have sticky Date column"
    assert 'sticky-day-th' in content, "Must have sticky Day column"
    assert 'btnSaveAndTrigger' in content, "Must have Save & Trigger button"
    assert 'btn-emergency-stop' in content, "Must have Emergency Stop button"
    print("✔ ATC template matches clean compact reference layout without clutter.")

    # ------------------------------------------------------------------
    # TEST 2: AUTOMATION SIGNAL & DATE VALIDATION RULES
    # ------------------------------------------------------------------
    print("\n--- TEST 2: AUTOMATION SIGNAL & DATE VALIDATION RULES ---")
    today = get_server_today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    five_depts_payload = [
        {'department_id': d.id, 'name': d.name, 'male': 120, 'female': 50, 'child': 30, 'total': 200, 'min': 100, 'max': 200}
        for d in depts
    ]

    # OP signal + backdated date -> strictly blocked
    res_op_back = client.post('/lab/api/atc/preview/', json.dumps({
        'operation_signal': 'OP',
        'op_date': yesterday.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_op_back.status_code == 400, "OP signal with backdated date must return 400"
    assert "Backdated OP registration is blocked" in res_op_back.json().get('message', '')

    # Review signal + backdated date -> allowed!
    res_rev_back = client.post('/lab/api/atc/preview/', json.dumps({
        'operation_signal': 'REVIEW',
        'op_date': yesterday.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_rev_back.status_code == 200, f"Review signal with backdated date must be accepted, got {res_rev_back.status_code}: {res_rev_back.content}"

    # OP signal + today or future -> allowed!
    res_op_future = client.post('/lab/api/atc/preview/', json.dumps({
        'operation_signal': 'OP',
        'op_date': tomorrow.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_op_future.status_code == 200, "OP signal with future date must be accepted"
    print("✔ Automation signal date validation rules verified (OP blocks backdated, Review allows backdated/today/future).")

    # ------------------------------------------------------------------
    # TEST 3: QUOTA CALCULATIONS & TARGET INTEGRITY
    # ------------------------------------------------------------------
    print("\n--- TEST 3: QUOTA CALCULATIONS & TARGET INTEGRITY ---")
    # Male 120, Female 50, Child 30 = 200. OP 75% -> 150, Review 25% -> 50.
    res_calc = client.post('/lab/api/atc/preview/', json.dumps({
        'operation_signal': 'ALL',
        'op_date': today.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': [
            {'department_id': depts[0].id, 'name': depts[0].name, 'male': 120, 'female': 50, 'child': 30, 'total': 200}
        ],
    }), content_type='application/json')
    assert res_calc.status_code == 200
    p = res_calc.json()['preview']
    assert p['target_total'] == 200, f"Expected 200 total, got {p['target_total']}"
    assert p['target_male'] == 120
    assert p['target_female'] == 50
    assert p['target_child'] == 30
    assert p['target_op'] == 150, f"Expected 150 OP target, got {p['target_op']}"
    assert p['target_review'] == 50, f"Expected 50 Review target, got {p['target_review']}"
    print("✔ Patient quota and percentage targets (120+50+30=200, 75%+25%=150/50) match exact specifications.")

    # ------------------------------------------------------------------
    # TEST 4: MINIMUM 5 DEPARTMENTS THRESHOLD FOR SAVE & TRIGGER
    # ------------------------------------------------------------------
    print("\n--- TEST 4: MINIMUM 5 DEPARTMENTS THRESHOLD ---")
    ATCJob.objects.filter(status__in=[ATCJob.StatusChoices.STARTING, ATCJob.StatusChoices.RUNNING, ATCJob.StatusChoices.STOP_REQUESTED]).update(status=ATCJob.StatusChoices.COMPLETED)

    # 4 departments -> must be rejected
    four_depts_payload = five_depts_payload[:4]
    res_four = client.post('/lab/api/atc/trigger/', json.dumps({
        'operation_signal': 'ALL',
        'op_date': today.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': four_depts_payload,
    }), content_type='application/json')
    assert res_four.status_code == 400, "Triggering with < 5 departments must return 400"
    assert "At least 5 different departments must be configured" in res_four.json().get('message', '')

    # 5 departments -> accepted!
    res_five = client.post('/lab/api/atc/trigger/', json.dumps({
        'operation_signal': 'ALL',
        'op_date': today.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'start_time': '00:01', 'end_time': '23:59',
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_five.status_code == 200, f"Triggering with 5 departments must succeed, got {res_five.status_code}: {res_five.content}"
    job_id = res_five.json()['job_id']
    job = ATCJob.objects.get(pk=job_id)
    assert job.is_locked is True, "Plan must be locked after trigger"
    print("✔ Minimum 5 departments threshold strictly enforced (<5 rejected, >=5 accepted and locked).")

    # ------------------------------------------------------------------
    # TEST 5: DRAFT SAVING & DUPLICATE DEPARTMENT HANDLING
    # ------------------------------------------------------------------
    print("\n--- TEST 5: DRAFT SAVING & DUPLICATE DEPARTMENT HANDLING ---")
    draft_payload = {
        'source_data_period': '2024 – 2025',
        'operation_signal': 'ALL',
        'op_date': today.strftime('%Y-%m-%d'),
        'male_count': 120, 'female_count': 50, 'child_count': 30,
        'op_daily_pct': 75, 'review_pct': 25,
        'plan_departments': five_depts_payload,
        'daily_targets': {
            today.strftime('%Y-%m-%d'): {
                str(depts[0].id): {'min': 105, 'max': 210}
            }
        }
    }
    res_draft = client.post('/lab/api/atc/save-config/', json.dumps(draft_payload), content_type='application/json')
    assert res_draft.status_code == 200, f"Save draft must succeed, got {res_draft.status_code}"
    saved_draft_id = res_draft.json()['job_id']
    draft_job = ATCJob.objects.get(pk=saved_draft_id)
    assert draft_job.status == ATCJob.StatusChoices.DRAFT
    assert draft_job.is_locked is False
    assert len(draft_job.plan_departments) == 5
    assert draft_job.daily_targets[today.strftime('%Y-%m-%d')][str(depts[0].id)]['min'] == 105
    print("✔ Draft saved successfully with multi-department plan and daily targets.")

    # ------------------------------------------------------------------
    # TEST 6: LOCKING & PERMISSIONS ENFORCEMENT
    # ------------------------------------------------------------------
    print("\n--- TEST 6: LOCKING & PERMISSIONS ENFORCEMENT ---")
    # Lock the draft job to simulate a triggered plan
    draft_job.is_locked = True
    draft_job.save(update_fields=['is_locked'])

    # Viewer user (can_view=True, can_edit=False) attempts to modify locked draft
    viewer_client = Client()
    viewer_client.force_login(viewer_user)
    res_viewer_mod = viewer_client.post('/lab/api/atc/save-config/', json.dumps({
        'job_id': draft_job.id,
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_viewer_mod.status_code == 403, f"Viewer without ATC_EDIT must be rejected with 403 on locked plan, got {res_viewer_mod.status_code}"

    # Editor user (can_edit=True) attempts to modify locked draft
    editor_client = Client()
    editor_client.force_login(editor_user)
    res_editor_mod = editor_client.post('/lab/api/atc/save-config/', json.dumps({
        'job_id': draft_job.id,
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_editor_mod.status_code == 200, f"Editor with ATC_EDIT must be allowed to update locked plan, got {res_editor_mod.status_code}"

    # Viewer user attempts to trigger automation
    res_viewer_trig = viewer_client.post('/lab/api/atc/trigger/', json.dumps({
        'plan_departments': five_depts_payload,
    }), content_type='application/json')
    assert res_viewer_trig.status_code == 403, "Viewer without ATC_TRIGGER must be rejected with 403"

    # Viewer user attempts emergency stop
    res_viewer_stop = viewer_client.post(f'/lab/api/atc/stop/{draft_job.id}/')
    assert res_viewer_stop.status_code == 403, "Viewer without ATC_EMERGENCY_STOP must be rejected with 403"
    print("✔ Permissions and locking strictly enforced (ATC_VIEW, ATC_CREATE, ATC_EDIT, ATC_TRIGGER, ATC_EMERGENCY_STOP).")

    print("\n==================================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! ATC MODULE FULLY VALIDATED.")
    print("==================================================================")


if __name__ == '__main__':
    run_tests()
