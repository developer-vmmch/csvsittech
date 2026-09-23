import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.patients.models import Patient, Department
from apps.users.models import User
from apps.lab.models import Investigation, ServiceRequest, ServiceRequestInvestigation, SampleType, LabDepartment
from django.utils import timezone

# 1. Get or Create Patient
patient, _ = Patient.objects.get_or_create(
    patient_id="PAT-TEST-001",
    defaults={
        'name': 'Test Patient Lakshmi',
        'gender': 'Female',
        'dob': timezone.now().date(),
        'age_years': 45
    }
)

# 2. Get or Create Investigations
lab_dept, _ = LabDepartment.objects.get_or_create(name='HOD-ENT')
sample_edta, _ = SampleType.objects.get_or_create(name='EDTA')
sample_serum, _ = SampleType.objects.get_or_create(name='Serum')

cbc, _ = Investigation.objects.get_or_create(code='00020564', defaults={'name': 'CBC Complete Blood Count', 'department': lab_dept, 'sample_type': sample_edta})
rbs, _ = Investigation.objects.get_or_create(code='00014149', defaults={'name': 'RBS', 'department': lab_dept, 'sample_type': sample_serum})
rft, _ = Investigation.objects.get_or_create(code='00020686', defaults={'name': 'RFT - Renal Function Test', 'department': lab_dept, 'sample_type': sample_edta})
bt_ct, _ = Investigation.objects.get_or_create(code='00020517', defaults={'name': 'BT & CT', 'department': lab_dept})

# 3. Create Service Request
user = User.objects.first()
dept, _ = Department.objects.get_or_create(name='General Medicine')

sr = ServiceRequest.objects.create(
    patient=patient,
    consultant=user,
    department=dept,
    visit_type='OP',
    status='SAVED',
    created_by=user
)

# 4. Add Investigations to SR
for inv in [cbc, rbs, rft, bt_ct]:
    ServiceRequestInvestigation.objects.create(
        service_request=sr,
        investigation=inv,
        status='PENDING'
    )

print("Test Service Request created successfully. Sample ID:", sr.sample_id)
