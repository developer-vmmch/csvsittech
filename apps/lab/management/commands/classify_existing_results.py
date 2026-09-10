from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Classify existing dummy result parameters'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch', type=int, default=500)

    def handle(self, *args, **options):
        from apps.lab.models import AutomationDummyResultParameter, AutomationDummyResult
        from apps.lab.services.result_classifier import classify_dummy_parameter, get_overall_result_status
        dry_run = options['dry_run']
        batch_size = options['batch']
        total = AutomationDummyResultParameter.objects.count()
        self.stdout.write('Classifying %d parameters...' % total)
        counts = {'NORMAL': 0, 'BELOW': 0, 'ABOVE': 0, 'NON_NUMERIC': 0}
        result_statuses = {}
        qs = AutomationDummyResultParameter.objects.select_related(
            'dummy_result', 'dummy_result__investigation', 'parameter'
        ).order_by('id')
        to_update = []
        processed = 0
        for param in qs.iterator(chunk_size=batch_size):
            try:
                status, _, _ = classify_dummy_parameter(param)
            except Exception:
                status = 'NON_NUMERIC'
            counts[status] = counts.get(status, 0) + 1
            param.result_status = status
            dr_id = param.dummy_result_id
            if dr_id not in result_statuses:
                result_statuses[dr_id] = []
            result_statuses[dr_id].append(status)
            if not dry_run:
                to_update.append(param)
            processed += 1
            if processed % 1000 == 0:
                self.stdout.write('  Processed %d/%d...' % (processed, total))
                if not dry_run and to_update:
                    AutomationDummyResultParameter.objects.bulk_update(
                        to_update, ['result_status'], batch_size=batch_size)
                    to_update = []
        if not dry_run and to_update:
            AutomationDummyResultParameter.objects.bulk_update(
                to_update, ['result_status'], batch_size=batch_size)
        self.stdout.write('Updating overall result_status on dummy results...')
        if not dry_run:
            results_to_update = []
            for dr_id, param_statuses in result_statuses.items():
                overall = get_overall_result_status(param_statuses)
                obj = AutomationDummyResult(id=dr_id, result_status=overall)
                results_to_update.append(obj)
            AutomationDummyResult.objects.bulk_update(
                results_to_update, ['result_status'], batch_size=batch_size)
        self.stdout.write('=== CLASSIFICATION COMPLETE ===')
        for key in ('NORMAL', 'BELOW', 'ABOVE', 'NON_NUMERIC'):
            self.stdout.write('  %s: %d' % (key, counts.get(key, 0)))
        self.stdout.write('  Total: %d' % processed)
        if dry_run:
            self.stdout.write('  (DRY RUN -- no changes saved)')
