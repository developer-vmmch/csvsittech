import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.lab.models import Investigation, AutomationDummyResult
from django.contrib.auth import get_user_model
from apps.lab.services.automation_test_service import AutomationTestService

class Command(BaseCommand):
    help = 'Seeds dummy automation results for CBC, ESR, and SR using DB-driven generation'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        investigations_to_seed = ['CBC', 'ESR', 'SR']
        
        total_created = 0

        for inv_code in investigations_to_seed:
            # Try to find by code or short_name or name
            inv = Investigation.objects.filter(code__icontains=inv_code).first() or \
                  Investigation.objects.filter(short_name__icontains=inv_code).first() or \
                  Investigation.objects.filter(name__icontains=inv_code).first()

            if not inv:
                self.stdout.write(self.style.WARNING(f"Investigation '{inv_code}' not found in master data. Skipping."))
                continue

            params = list(inv.parameters.filter(is_active=True).select_related('parameter'))
            if not params:
                self.stdout.write(self.style.WARNING(f"No parameters found for '{inv.name}'. Skipping."))
                continue

            self.stdout.write(self.style.SUCCESS(f"Seeding 15 results for {inv.name}..."))

            for i in range(1, 16):
                count = AutomationDummyResult.objects.filter(investigation=inv).count() + 1
                
                dummy = AutomationTestService.generate_and_save_dummy_result(
                    investigation=inv,
                    admin_user=admin_user,
                    result_count=count
                )
                
                # Make slightly older timestamps for variety
                created_at = timezone.now() - timedelta(minutes=random.randint(1, 120))
                AutomationDummyResult.objects.filter(id=dummy.id).update(
                    created_at=created_at,
                    remarks=f"Auto-generated test record {i}"
                )
                
                total_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully created {total_created} dummy results!"))
