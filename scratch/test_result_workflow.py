import os
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

import json
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient
from apps.lab.models import (
    Investigation, Parameter, InvestigationParameter,
    ServiceRequest, ServiceRequestInvestigation,
    ServiceRequestResult, ServiceRequestResultAudit,
    AgeGroup, ParameterReferenceRange
)
from apps.lab.services.work_order_service import (
    get_overall_sample_status,
    get_next_received_investigation,
    get_investigation_parameter_details
)
from apps.lab.views import (
    api_work_orders_list,
    api_work_order_save_result,
    WorkOrderResultEntryView,
    WorkOrderPrintPreviewView
)

User = get_user_model()
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
if not admin_user.has_usable_password():
    admin_user.set_password('admin123')
    admin_user.save()

print("--- STARTING WORK ORDER & RESULT ENTRY COMPREHENSIVE TESTS ---")

# Clean up any leftover test data
Patient.objects.filter(patient_id__startswith='TEST-WO-').delete()
ServiceRequest.objects.filter(sample_id__startswith='SAMPLE-TEST-').delete()
Investigation.objects.filter(code__startswith='TEST_').delete()
Parameter.objects.filter(code__startswith='PARAM_').delete()

# 1. TEST AGGREGATE STATUS LOGIC
print("\n[TEST 1] Testing Aggregate Status Rules...")
# Create a test patient
patient = Patient.objects.create(
    patient_id='TEST-WO-001',
    name='Test Patient Result Entry',
    age_years=35,
    gender='Male'
)

sr = ServiceRequest.objects.create(
    patient=patient,
    status='Draft',
    sample_id='SAMPLE-TEST-001'
)

# Create 3 dummy investigations
inv1 = Investigation.objects.create(name='Test CBC', code='TEST_CBC_01')
inv2 = Investigation.objects.create(name='Test ESR', code='TEST_ESR_01')
inv3 = Investigation.objects.create(name='Test LFT', code='TEST_LFT_01')

sri1 = ServiceRequestInvestigation.objects.create(service_request=sr, investigation=inv1, status='PENDING')
sri2 = ServiceRequestInvestigation.objects.create(service_request=sr, investigation=inv2, status='PENDING')
sri3 = ServiceRequestInvestigation.objects.create(service_request=sr, investigation=inv3, status='PENDING')

# Case A: All PENDING -> PENDING (BLACK)
st = get_overall_sample_status(sr)
assert st == 'PENDING', f"Expected PENDING, got {st}"
print("  ✓ Case A: All PENDING => PENDING")

# Case B: 1 RECEIVED, 2 PENDING -> RECEIVED (BLUE)
sri1.status = 'RECEIVED'
sri1.save()
st = get_overall_sample_status(sr)
assert st == 'RECEIVED', f"Expected RECEIVED, got {st}"
print("  ✓ Case B: 1 RECEIVED, 2 PENDING => RECEIVED")

# Case C: 1 COMPLETED, 2 PENDING -> RECEIVED (BLUE, partial completion)
sri1.status = 'COMPLETED'
sri1.save()
st = get_overall_sample_status(sr)
assert st == 'RECEIVED', f"Expected RECEIVED for partial completion, got {st}"
print("  ✓ Case C: 1 COMPLETED, 2 PENDING (partial completion) => RECEIVED")

# Case D: 1 REJECTED, 2 PENDING -> REJECTED (RED)
sri1.status = 'PENDING'
sri1.save()
sri2.status = 'REJECTED'
sri2.save()
st = get_overall_sample_status(sr)
assert st == 'REJECTED', f"Expected REJECTED, got {st}"
print("  ✓ Case D: 1 REJECTED, 2 PENDING => REJECTED")

# Case E: 100% COMPLETED -> COMPLETED (GREEN)
sri1.status = 'COMPLETED'
sri1.save()
sri2.status = 'COMPLETED'
sri2.save()
sri3.status = 'COMPLETED'
sri3.save()
st = get_overall_sample_status(sr)
assert st == 'COMPLETED', f"Expected COMPLETED for 100% completed, got {st}"
print("  ✓ Case E: 100% COMPLETED => COMPLETED")

# 2. TEST SQL ANNOTATION IN api_work_orders_list
print("\n[TEST 2] Testing api_work_orders_list SQL Annotation...")
factory = RequestFactory()
req = factory.get(f'/lab/api/work-orders/list/?search={patient.patient_id}')
req.user = admin_user
resp = api_work_orders_list(req)
data = json.loads(resp.content)
order_row = next((row for row in data.get('work_orders', []) if row['patient_id'] == patient.patient_id), None)
assert order_row is not None, "Order row not found in api_work_orders_list"
assert order_row['status'] == 'COMPLETED', f"Expected SQL annotated status COMPLETED, got {order_row['status']}"
print(f"  ✓ SQL Annotated status matches: {order_row['status']}")

# Now set sri3 to RECEIVED and check SQL annotation becomes RECEIVED
sri3.status = 'RECEIVED'
sri3.save()
resp = api_work_orders_list(req)
data = json.loads(resp.content)
order_row = next((row for row in data.get('work_orders', []) if row['patient_id'] == patient.patient_id), None)
assert order_row['status'] == 'RECEIVED', f"Expected SQL annotated status RECEIVED, got {order_row['status']}"
print(f"  ✓ Partial completion SQL annotated status matches: {order_row['status']}")

# 3. TEST PARAMETERS: HEADER ROWS VS EDITABLE PARAMETERS
print("\n[TEST 3] Testing Parameter Details & Header Exemption...")
# Parameter for inv1: 1 header row ("Differential Count"), 1 normal param with range, 1 param without range
p_hdr, _ = Parameter.objects.get_or_create(code='00020553', defaults={'name': 'Differential Count'})
p_normal, _ = Parameter.objects.get_or_create(code='PARAM_NEUT', defaults={'name': 'Neutrophils'})
p_norange, _ = Parameter.objects.get_or_create(code='PARAM_MORPH', defaults={'name': 'Morphology'})

ip_hdr = InvestigationParameter.objects.create(investigation=inv1, parameter=p_hdr, display_order=1)
ip_normal = InvestigationParameter.objects.create(investigation=inv1, parameter=p_normal, display_order=2)
ip_norange = InvestigationParameter.objects.create(investigation=inv1, parameter=p_norange, display_order=3)

# Add reference range for Neutrophils
ParameterReferenceRange.objects.create(
    investigation_parameter=ip_normal,
    gender='All',
    min_value=40,
    max_value=70,
    unit='%'
)

details = get_investigation_parameter_details(sri1, patient)
params_list = details['param_data']

hdr_item = next(p for p in params_list if p['ip'].id == ip_hdr.id)
normal_item = next(p for p in params_list if p['ip'].id == ip_normal.id)
norange_item = next(p for p in params_list if p['ip'].id == ip_norange.id)

assert hdr_item['is_header'] is True, "Expected Differential Count to be header"
assert hdr_item['is_editable'] is False, "Expected Differential Count to NOT be editable"
assert normal_item['is_editable'] is True, "Expected Neutrophils to be editable"
assert norange_item['is_editable'] is True, "Expected Morphology (no range) to still be editable"
print("  ✓ Parameter header and editable flags verified correctly.")

# 4. TEST VALIDATION BEFORE SAVE
print("\n[TEST 4] Testing Parameter Validation on Save Result...")
sri1.status = 'RECEIVED'
sri1.save()

# Try saving with empty parameters
req_save_empty = factory.post(
    f'/lab/work-orders/save-result/{sri1.id}/',
    data=json.dumps({'results': []}),
    content_type='application/json'
)
req_save_empty.user = admin_user
resp_save_empty = api_work_order_save_result(req_save_empty, sri1.id)
assert resp_save_empty.status_code == 400, f"Expected 400, got {resp_save_empty.status_code}"
err_data = json.loads(resp_save_empty.content)
assert 'Neutrophils' in err_data['missing_parameters'], "Neutrophils should be in missing_parameters"
assert 'Morphology' in err_data['missing_parameters'], "Morphology should be in missing_parameters"
assert 'Differential Count' not in err_data['missing_parameters'], "Differential Count should NOT be required"
print("  ✓ Validation blocked save with empty parameters and listed exact missing parameters.")

# Try saving with partial parameter (only Neutrophils, missing Morphology)
req_save_partial = factory.post(
    f'/lab/work-orders/save-result/{sri1.id}/',
    data=json.dumps({'results': [{'parameter_id': ip_normal.id, 'value': '55'}]}),
    content_type='application/json'
)
req_save_partial.user = admin_user
resp_save_partial = api_work_order_save_result(req_save_partial, sri1.id)
assert resp_save_partial.status_code == 400
err_data_partial = json.loads(resp_save_partial.content)
assert 'Morphology' in err_data_partial['missing_parameters']
assert 'Neutrophils' not in err_data_partial['missing_parameters']
print("  ✓ Validation blocked partial save correctly (Morphology required even without range).")

# 5. TEST SAVE & COMPLETE & AUTO-ADVANCE TO NEXT RECEIVED TEST
print("\n[TEST 5] Testing Save & Complete and Next Received Advance...")
# Make sri3 RECEIVED, sri2 PENDING
sri2.status = 'PENDING'
sri2.save()
sri3.status = 'RECEIVED'
sri3.save()

# Save all required parameters for sri1
req_save_full = factory.post(
    f'/lab/work-orders/save-result/{sri1.id}/',
    data=json.dumps({
        'results': [
            {'parameter_id': ip_normal.id, 'value': '60', 'remarks': 'Normal'},
            {'parameter_id': ip_norange.id, 'value': 'Adequate', 'remarks': ''}
        ],
        'verified_by_id': admin_user.id
    }),
    content_type='application/json'
)
req_save_full.user = admin_user
resp_save_full = api_work_order_save_result(req_save_full, sri1.id)
assert resp_save_full.status_code == 200, f"Expected 200, got {resp_save_full.status_code}: {resp_save_full.content}"
success_data = json.loads(resp_save_full.content)

sri1.refresh_from_db()
assert sri1.status == 'COMPLETED', f"Expected sri1 COMPLETED, got {sri1.status}"
assert sri1.verified_by == admin_user, "Expected verified_by to be set"
assert success_data['has_next_received'] is True, "Expected next received test to be detected"
assert success_data['next_received_id'] == sri3.id, f"Expected sri3 ({sri3.id}), got {success_data['next_received_id']}"
print(f"  ✓ sri1 marked COMPLETED; auto-advance detected next RECEIVED test: {success_data['next_received_name']} (ID: {success_data['next_received_id']})")

# 6. TEST MODIFY & AUDIT LOGGING
print("\n[TEST 6] Testing Modify & ServiceRequestResultAudit Log...")
audit_count_before = ServiceRequestResultAudit.objects.filter(sr_investigation=sri1).count()

# Modify Neutrophils from 60 to 68
req_modify = factory.post(
    f'/lab/work-orders/save-result/{sri1.id}/',
    data=json.dumps({
        'results': [
            {'parameter_id': ip_normal.id, 'value': '68', 'remarks': 'Updated'},
            {'parameter_id': ip_norange.id, 'value': 'Adequate', 'remarks': ''}
        ]
    }),
    content_type='application/json'
)
req_modify.user = admin_user
resp_modify = api_work_order_save_result(req_modify, sri1.id)
assert resp_modify.status_code == 200

audit_records = ServiceRequestResultAudit.objects.filter(sr_investigation=sri1).order_by('-created_at')
assert audit_records.count() == audit_count_before + 1, "Audit record should have been created"
latest_audit = audit_records.first()
assert latest_audit.old_value == '60', f"Expected old value 60, got {latest_audit.old_value}"
assert latest_audit.new_value == '68', f"Expected new value 68, got {latest_audit.new_value}"
assert latest_audit.modified_by == admin_user, "Expected modified_by to be admin_user"
print(f"  ✓ Audit record created: {latest_audit.investigation_parameter.parameter.name} changed from '{latest_audit.old_value}' to '{latest_audit.new_value}' by {latest_audit.modified_by.username}")

# 7. TEST COMPLETED-ONLY PRINT PREVIEW
print("\n[TEST 7] Testing Completed-Only Printing Rule...")
# sri1 is COMPLETED, sri2 is PENDING, sri3 is RECEIVED
# Single test print on COMPLETED test (sri1) -> should include sri1
req_print_sri1 = factory.get(f'/lab/work-orders/print/{sri1.id}/?type=single')
req_print_sri1.user = admin_user
view_single = WorkOrderPrintPreviewView.as_view()
resp_print_sri1 = view_single(req_print_sri1, pk=sri1.id)
ctx1 = resp_print_sri1.context_data
assert 'reports_data' in ctx1 and len(ctx1['reports_data']) == 1, "Print single should have 1 report"
assert ctx1['reports_data'][0]['inv'].id == sri1.id
print("  ✓ Single print on completed test includes test.")

# Single test print on RECEIVED test (sri3) -> should be blocked / no_completed_investigations=True
req_print_sri3 = factory.get(f'/lab/work-orders/print/{sri3.id}/?type=single')
req_print_sri3.user = admin_user
resp_print_sri3 = view_single(req_print_sri3, pk=sri3.id)
ctx3 = resp_print_sri3.context_data
assert ctx3.get('no_completed_investigations') is True, "Single print on non-completed test should return no_completed_investigations=True"
print("  ✓ Single print on non-completed test blocked with no_completed_investigations=True.")

# Print All (`type=all`) -> should ONLY include COMPLETED investigations (sri1), NOT sri2 (PENDING) or sri3 (RECEIVED)
req_print_all = factory.get(f'/lab/work-orders/print/{sri1.id}/?type=all')
req_print_all.user = admin_user
resp_print_all = view_single(req_print_all, pk=sri1.id)
ctx_all = resp_print_all.context_data
assert len(ctx_all['reports_data']) == 1, f"Print all should ONLY have completed tests (1), got {len(ctx_all['reports_data'])}"
assert ctx_all['reports_data'][0]['inv'].id == sri1.id
print("  ✓ Print All includes only COMPLETED tests; strictly excludes PENDING and RECEIVED tests.")

# 8. CLEAN UP TEST DATA
sri1.delete()
sri2.delete()
sri3.delete()
inv1.delete()
inv2.delete()
if p_hdr.code != '00020553':
    p_hdr.delete()
p_normal.delete()
p_norange.delete()
sr.delete()
patient.delete()
print("\n[CLEANUP] Test records cleaned up successfully.")

print("\nALL WORK ORDER & RESULT ENTRY TESTS PASSED SUCCESSFULLY! ✓✓✓")
