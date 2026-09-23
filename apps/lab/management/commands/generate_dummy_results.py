"""
generate_dummy_results.py
Idempotent management command that generates dummy lab results for all investigations.
Uses existing master data via AutomationTestService.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.lab.models import Investigation, AutomationDummyResult
from apps.lab.services.automation_test_service import AutomationTestService

class Command(BaseCommand):
    help = 'Generates dummy lab results for all active investigations using AutomationTestService.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing dummy results first.')
        parser.add_argument('--investigation', type=str, default='all',
                            help='Comma-separated partial investigation names. Default: all.')
        parser.add_argument('--count', type=int, default=5,
                            help='Number of dummy results to generate per investigation.')

    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        if options['clear']:
            deleted, _ = AutomationDummyResult.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing dummy results."))

        inv_filter = options['investigation']
        count_per_inv = options['count']

        query = Investigation.objects.filter(is_active=True)
        if inv_filter != 'all':
            filters = [f.strip() for f in inv_filter.split(',')]
            from django.db.models import Q
            q_objs = Q()
            for f in filters:
                q_objs |= Q(name__icontains=f) | Q(short_name__icontains=f)
            query = query.filter(q_objs)

        investigations = list(query)
        
        if not investigations:
            self.stdout.write(self.style.WARNING("No matching investigations found."))
            return

        total_created = 0
        for inv in investigations:
            self.stdout.write(f"\nGenerating {count_per_inv} results for '{inv.name}'...")
            for idx in range(1, count_per_inv + 1):
                existing_count = AutomationDummyResult.objects.filter(investigation=inv).count()
                try:
                    dummy = AutomationTestService.generate_and_save_dummy_result(
                        investigation=inv,
                        admin_user=admin_user,
                        result_count=existing_count + 1
                    )
                    total_created += 1
                    self.stdout.write(f"  [{idx}] {dummy.result_id} | {dummy.patient_name} | {dummy.patient_age_display} | {dummy.patient_gender}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ERROR [{idx}]: {e}"))
                    import traceback; traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(f"\nDone. Total dummy results created: {total_created}"))
