import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.lab.universal_importer import validate_import, import_universal_master, SHEET_ORDER


class Command(BaseCommand):
    help = 'Validate and import the Universal Master Excel workbook for Hospital Laboratory master data.'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            nargs='?',
            default='/home/Loosifer/Downloads/VMMC_Lab_Universal_Master_Import_Corrected.xlsx',
            help='Path to the Universal Master Excel workbook (.xlsx)'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only run pre-import validation checks without applying database changes.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate full import inside a rolled-back transaction.'
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']
        validate_only = options['validate_only']
        dry_run = options['dry_run']

        if not os.path.exists(excel_path):
            raise CommandError(f"Excel file not found at: {excel_path}")

        self.stdout.write(self.style.NOTICE(f"\n{'='*75}"))
        self.stdout.write(self.style.NOTICE(f"VMMC UNIVERSAL MASTER IMPORT TOOL"))
        self.stdout.write(self.style.NOTICE(f"Source file: {excel_path}"))
        self.stdout.write(self.style.NOTICE(f"{'='*75}\n"))

        # 1. Pre-import Validation
        self.stdout.write(self.style.MIGRATE_HEADING("Step 1: Running Pre-Import Validation..."))
        try:
            val_res = validate_import(excel_path)
        except Exception as e:
            raise CommandError(f"Validation failed with error: {e}")

        # Print sheet-by-sheet statistics table
        self.stdout.write(f"\n{'-'*95}")
        self.stdout.write(f"{'Stage / Sheet':<32} | {'Detected':<8} | {'Valid':<8} | {'Invalid':<8} | {'Dups':<6} | {'New':<6} | {'Exist':<6}")
        self.stdout.write(f"{'-'*95}")
        for idx, s_name in enumerate(SHEET_ORDER, start=1):
            st = val_res['sheet_stats'].get(s_name, {})
            self.stdout.write(
                f"{idx}. {s_name:<29} | "
                f"{st.get('detected_rows', 0):<8} | "
                f"{st.get('valid_rows', 0):<8} | "
                f"{st.get('invalid_rows', 0):<8} | "
                f"{st.get('duplicates', 0):<6} | "
                f"{st.get('new', 0):<6} | "
                f"{st.get('existing', 0):<6}"
            )
        self.stdout.write(f"{'-'*95}")
        t = val_res.get('total_stats', {})
        self.stdout.write(
            f"{'TOTALS':<32} | "
            f"{t.get('detected_rows', 0):<8} | "
            f"{t.get('valid_rows', 0):<8} | "
            f"{t.get('invalid_rows', 0):<8} | "
            f"{t.get('duplicates', 0):<6} | "
            f"{t.get('new', 0):<6} | "
            f"{t.get('existing', 0):<6}"
        )
        self.stdout.write(f"{'-'*95}\n")

        if val_res['warnings']:
            self.stdout.write(self.style.WARNING(f"Warnings ({len(val_res['warnings'])}):"))
            for w in val_res['warnings'][:15]:
                self.stdout.write(self.style.WARNING(f"  - {w}"))
            if len(val_res['warnings']) > 15:
                self.stdout.write(self.style.WARNING(f"  ... and {len(val_res['warnings']) - 15} more."))

        if not val_res['valid']:
            self.stdout.write(self.style.ERROR(f"\nValidation FAILED with {len(val_res['errors'])} errors:"))
            for err in val_res['errors'][:20]:
                self.stdout.write(self.style.ERROR(f"  - [{err.get('sheet')}] Row {err.get('row')}: {err.get('message')}"))
            if len(val_res['errors']) > 20:
                self.stdout.write(self.style.ERROR(f"  ... and {len(val_res['errors']) - 20} more errors."))
            raise CommandError("Aborting import due to validation errors.")

        self.stdout.write(self.style.SUCCESS("Validation PASSED! All records are valid and consistent."))

        if validate_only:
            self.stdout.write(self.style.SUCCESS("\n--validate-only specified. Exiting without writing changes."))
            return

        # 2. Import Execution
        if dry_run:
            self.stdout.write(self.style.MIGRATE_HEADING("\nStep 2: Simulating Import in Transaction (Dry Run)..."))
            try:
                with transaction.atomic():
                    counts = import_universal_master(excel_path)
                    transaction.set_rollback(True)
                self.stdout.write(self.style.SUCCESS("Dry run completed successfully! Transaction rolled back."))
                self._print_counts(counts)
            except Exception as e:
                raise CommandError(f"Dry run failed: {e}")
            return

        self.stdout.write(self.style.MIGRATE_HEADING("\nStep 2: Committing Import into Database..."))
        try:
            counts = import_universal_master(excel_path)
            self.stdout.write(self.style.SUCCESS("Import completed and committed successfully!"))
            self._print_counts(counts)
        except Exception as e:
            raise CommandError(f"Import failed and rolled back: {e}")

    def _print_counts(self, counts):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"IMPORT EXECUTION SUMMARY")
        self.stdout.write(f"{'='*60}")
        categories = [
            ('Departments', 'departments'),
            ('Age Groups', 'age_groups'),
            ('Diagnoses', 'diagnoses'),
            ('Investigations', 'investigations'),
            ('Parameters', 'parameters'),
            ('Diagnosis Departments', 'diag_dept_mappings'),
            ('Investigation Parameters', 'inv_params'),
            ('Reference Ranges', 'ref_ranges'),
            ('Diagnosis Investigations', 'diag_inv_mappings'),
        ]
        self.stdout.write(f"{'Entity / Mapping':<28} | {'Created':<8} | {'Updated':<8} | {'Skipped':<8}")
        self.stdout.write(f"{'-'*60}")
        for label, prefix in categories:
            created = counts.get(f'{prefix}_created', 0)
            updated = counts.get(f'{prefix}_updated', 0)
            skipped = counts.get(f'{prefix}_skipped', 0)
            self.stdout.write(f"{label:<28} | {created:<8} | {updated:<8} | {skipped:<8}")
        self.stdout.write(f"{'-'*60}")
        self.stdout.write(f"{'TOTALS':<28} | {counts.get('total_created', 0):<8} | {counts.get('total_updated', 0):<8} | {counts.get('total_skipped', 0):<8}")
        self.stdout.write(f"{'='*60}\n")
