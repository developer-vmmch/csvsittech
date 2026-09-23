import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import PatientInvestigationOrder, ServiceRequest, ServiceRequestInvestigation, ServiceRequestDiagnosis
from django.utils import timezone

def migrate():
    orders = PatientInvestigationOrder.objects.all()
    count = 0
    for order in orders:
        # Check if a ServiceRequest already exists for this order (we can use created_at roughly, or just create new ones)
        # To group them, we could group by patient and ordered_on
        
        # Let's just create one ServiceRequest per order for simplicity, or group by patient + time
        sr, created = ServiceRequest.objects.get_or_create(
            patient=order.patient,
            created_by=order.ordered_by,
            request_date=order.ordered_on.date(),
            defaults={
                'status': ServiceRequest.StatusChoices.SAVED,
                'visit_type': 'OP'
            }
        )
        
        if order.diagnosis:
            ServiceRequestDiagnosis.objects.get_or_create(
                service_request=sr,
                diagnosis=order.diagnosis
            )
            
        status_map = {
            PatientInvestigationOrder.StatusChoices.PENDING: ServiceRequestInvestigation.StatusChoices.PENDING,
            PatientInvestigationOrder.StatusChoices.COMPLETED: ServiceRequestInvestigation.StatusChoices.COMPLETED,
            PatientInvestigationOrder.StatusChoices.CANCELLED: ServiceRequestInvestigation.StatusChoices.PENDING,
        }
        
        ServiceRequestInvestigation.objects.get_or_create(
            service_request=sr,
            investigation=order.investigation,
            defaults={
                'status': status_map.get(order.status, ServiceRequestInvestigation.StatusChoices.PENDING),
                'source': ServiceRequestInvestigation.SourceChoices.MANUAL
            }
        )
        count += 1
        
    print(f"Migrated {count} PatientInvestigationOrders to ServiceRequests.")

if __name__ == '__main__':
    migrate()
