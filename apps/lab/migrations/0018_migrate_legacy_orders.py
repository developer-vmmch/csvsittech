from django.db import migrations
from django.utils import timezone

def migrate_legacy_orders(apps, schema_editor):
    PatientInvestigationOrder = apps.get_model('lab', 'PatientInvestigationOrder')
    ServiceRequest = apps.get_model('lab', 'ServiceRequest')
    ServiceRequestInvestigation = apps.get_model('lab', 'ServiceRequestInvestigation')
    ServiceRequestDiagnosis = apps.get_model('lab', 'ServiceRequestDiagnosis')

    # Group legacy orders by patient and date (ordered_on)
    # We will just iterate and group them in memory
    legacy_orders = PatientInvestigationOrder.objects.all()
    
    # We group by (patient_id, date) to merge multiple tests on the same day into one ServiceRequest
    groups = {}
    for order in legacy_orders:
        key = (order.patient_id, order.ordered_on.date())
        if key not in groups:
            groups[key] = []
        groups[key].append(order)
        
    for (patient_id, req_date), orders in groups.items():
        # Use the first order's ordered_by as the creator
        first_order = orders[0]
        
        sr = ServiceRequest.objects.create(
            patient_id=patient_id,
            created_by_id=first_order.ordered_by_id,
            request_date=req_date,
            status='Saved',
            visit_type='OP'
        )
        
        for order in orders:
            if order.diagnosis_id:
                ServiceRequestDiagnosis.objects.get_or_create(
                    service_request=sr,
                    diagnosis_id=order.diagnosis_id
                )
                
            status_map = {
                'PENDING': 'PENDING',
                'COMPLETED': 'COMPLETED',
                'CANCELLED': 'PENDING',
            }
            
            # Create the test
            ServiceRequestInvestigation.objects.create(
                service_request=sr,
                investigation_id=order.investigation_id,
                status=status_map.get(order.status, 'PENDING'),
                source='MANUAL'
            )
            
            # We don't delete the legacy orders to ensure no data is lost
            # But they are now duplicated in ServiceRequest so they appear in Work Orders.

def reverse_migration(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('lab', '0017_servicerequestinvestigation_completed_by_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_orders, reverse_migration),
    ]
