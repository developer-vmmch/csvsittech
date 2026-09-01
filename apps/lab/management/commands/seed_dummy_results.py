import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.lab.models import Investigation, AutomationDummyResult, AutomationDummyResultParameter
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Seeds dummy automation results for CBC, ESR, and SR'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        investigations_to_seed = ['CBC', 'ESR', 'SR']
        
        # Ranges for variance
        ranges = {
            'Hemoglobin': (11.0, 16.0),
            'RBC Count': (4.0, 6.0),
            'WBC Count': (4000, 11000),
            'Platelet Count': (150000, 400000),
            'Hematocrit (PCV)': (36.0, 50.0),
            'MCV': (80.0, 100.0),
            'MCH': (27.0, 32.0),
            'MCHC': (32.0, 36.0),
            'Neutrophils': (40, 75),
            'Lymphocytes': (20, 45),
            'Eosinophils': (1, 6),
            'Monocytes': (2, 10),
            'Basophils': (0, 2),
            'ESR': (0, 20),
            'SR': (10, 50) # Assuming SR has some numerical value
        }

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
                now = datetime.now()
                prefix = f"RES-{now.strftime('%Y-%m')}-"
                last_result = AutomationDummyResult.objects.filter(result_id__startswith=prefix).order_by('-result_id').first()
                if last_result:
                    last_num = int(last_result.result_id.split('-')[-1])
                    new_num = last_num + 1
                else:
                    new_num = 1
                result_id = f"{prefix}{new_num:05d}"
                
                count = AutomationDummyResult.objects.filter(investigation=inv).count() + 1
                dummy_name = f"{inv.short_name or inv.name} Dummy {count}"
                
                # Make slightly older timestamps for variety
                created_at = timezone.now() - timedelta(minutes=random.randint(1, 120))

                dummy = AutomationDummyResult.objects.create(
                    result_id=result_id,
                    investigation=inv,
                    investigation_code=inv.code or '',
                    dummy_name=dummy_name,
                    created_by=admin_user,
                    remarks=f"Auto-generated test record {i}",
                )
                
                # Update created_at
                AutomationDummyResult.objects.filter(id=dummy.id).update(created_at=created_at)

                for display_order, p in enumerate(params):
                    param_name = p.parameter.name if p.parameter else p.name
                    # Generate a random value based on the range or fallback
                    if param_name in ranges:
                        min_v, max_v = ranges[param_name]
                        if isinstance(min_v, float):
                            val = round(random.uniform(min_v, max_v), 1)
                        else:
                            val = random.randint(min_v, max_v)
                        val_str = str(val)
                    else:
                        val_str = str(round(random.uniform(10.0, 50.0), 1))

                    AutomationDummyResultParameter.objects.create(
                        dummy_result=dummy,
                        parameter=p.parameter,
                        parameter_name=param_name,
                        result_value=val_str,
                        unit=(p.parameter.unit.name if getattr(p.parameter, 'unit', None) else '') if p.parameter else p.unit,
                        reference_range='-', # Dummy range
                        display_order=display_order
                    )
                
                total_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully created {total_created} dummy results!"))
