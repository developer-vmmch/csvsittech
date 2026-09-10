from django.db import transaction
from django.utils import timezone
from apps.lab.models import (
    ServiceRequest, ServiceRequestDiagnosis, ServiceRequestInvestigation,
    ServiceRequestResult, InvestigationParameter
)
from apps.patients.models import Patient, Department
from django.contrib.auth import get_user_model

User = get_user_model()

class SaveAndTriggerService:
    @staticmethod
    @transaction.atomic
    def execute_trigger(data, user):
        patient_id = data.get('patient_id')
        consultant_name = data.get('consultant_name')
        department_id = data.get('department_id')
        visit_type = data.get('visit_type', 'OP')
        visit_no = data.get('visit_no')
        request_date = data.get('request_date')
        diagnoses_data = data.get('diagnoses', [])
        investigations_data = data.get('investigations', [])
        box_id = data.get('box_id')
        
        if not patient_id:
            raise ValueError("Patient ID is required")
            
        patient = Patient.objects.get(id=patient_id)
        if patient.patient_type != 'D':
            raise ValueError("Save & Trigger is only allowed for Dummy patients (Type D)")
            
        if not diagnoses_data:
            raise ValueError("At least one diagnosis is required")
            
        if not investigations_data:
            raise ValueError("At least one investigation is required")
            
        # Determine required status based on box_id
        required_status = None
        box_num = int(box_id) if box_id and box_id.isdigit() else 0
        
        if 1 <= box_num <= 5:
            required_status = "NORMAL"
        elif 6 <= box_num <= 7:
            required_status = "BELOW"
        elif 8 <= box_num <= 9:
            required_status = "ABOVE"
        elif box_num == 10:
            required_status = None
        else:
            raise ValueError("Invalid Box Selection")
            
        # Department Handling
        department = None
        if department_id:
            department = Department.objects.filter(id=department_id).first()
        if not department and patient.department:
            department = Department.objects.filter(name__iexact=patient.department).first()
            
        sr = ServiceRequest.objects.create(
            patient=patient,
            consultant_name=consultant_name,
            department=department,
            visit_type=visit_type,
            visit_no=visit_no,
            request_date=request_date or timezone.now().date(),
            status=ServiceRequest.StatusChoices.SAVED,
            created_by=user
        )

        for idx, diag in enumerate(diagnoses_data):
            item_type = diag.get('type')
            item_id = diag.get('id')
            if item_type == 'Diagnosis':
                ServiceRequestDiagnosis.objects.create(
                    service_request=sr,
                    diagnosis_id=item_id,
                    sort_order=idx
                )
            elif item_type == 'ChiefComplaint':
                ServiceRequestDiagnosis.objects.create(
                    service_request=sr,
                    chief_complaint_id=item_id,
                    sort_order=idx
                )

        created_sri = []
        for inv in investigations_data:
            sri = ServiceRequestInvestigation.objects.create(
                service_request=sr,
                investigation_id=inv.get('id'),
                qty=inv.get('qty', 1),
                source=inv.get('source', 'MANUAL'),
                is_removed=inv.get('is_removed', False)
            )
            created_sri.append(sri)

        # Atomically allocate dummy results
        from apps.lab.services.result_allocation_service import ResultAllocationService, ResultPoolExhaustedError
        allocations = ResultAllocationService.allocate_all_for_service_request(sr, required_status)
        
        # Now automatically process the work orders and results
        for sri in created_sri:
            dummy_result = allocations.get(sri.investigation_id)
            if not dummy_result:
                continue
                
            # 1. Auto-Receive
            sri.status = ServiceRequestInvestigation.StatusChoices.RECEIVED
            sri.received_date = timezone.now().date()
            sri.received_time = timezone.now().time()
            sri.received_by = user
            sri.save()
            
            # 2. Auto-Enter Results
            dummy_params = dummy_result.parameters.all()
            for dp in dummy_params:
                # Map Parameter back to InvestigationParameter for this investigation
                ip = InvestigationParameter.objects.filter(
                    investigation=sri.investigation,
                    parameter=dp.parameter,
                    is_active=True
                ).first()
                
                if ip:
                    ServiceRequestResult.objects.create(
                        sr_investigation=sri,
                        investigation_parameter=ip,
                        result_value=dp.result_value,
                        remarks="Auto-triggered from Dummy Pool",
                        entered_by=user
                    )
                    
            # 3. Complete Investigation
            sri.status = ServiceRequestInvestigation.StatusChoices.COMPLETED
            sri.completed_date = timezone.now()
            sri.completed_by = user
            sri.save()

        # Check if all sri are completed, if so, we can optionally mark SR as completed if that logic exists, 
        # but for now standard flow is sufficient.
        
        return sr
