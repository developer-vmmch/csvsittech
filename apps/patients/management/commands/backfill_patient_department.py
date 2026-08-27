import random
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.patients.models import Patient, Department, DepartmentUnit

class Command(BaseCommand):
    help = 'Backfill missing department on existing patients using weighted distribution.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Print summary without writing anything')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        target_weights = {
            'CHEST & TB': 3,
            'DENTAL': 3,
            'DERMATOLOGY': 12,
            'EMERGENCY MEDICINE': 4,
            'ENT': 13,
            'GENERAL MEDICINE': 9,
            'GENERAL SURGERY': 9,
            'GYNAECOLOGY': 9,
            'OBSTETRICS': 9,
            'OPHTHALMOLOGY': 9,
            'ORTHOPAEDICS': 9,
            'PAEDIATRICS': 9,
            'PSYCHIATRY': 2
        }

        departments = []
        weights = []
        for name, weight in target_weights.items():
            try:
                dept = Department.objects.get(name__iexact=name)
                departments.append(dept)
                weights.append(weight)
            except Department.DoesNotExist:
                self.stderr.write(f"Warning: Department '{name}' not found. Check your seeds.")
                return

        # Pre-fetch units for each department
        units_by_dept = {}
        for dept in departments:
            units = list(DepartmentUnit.objects.filter(department=dept, is_active=True))
            if not units:
                self.stderr.write(f"Warning: Department '{dept.name}' has no active units.")
                return
            units_by_dept[dept.id] = units

        patients_to_update = Patient.objects.filter(department_obj__isnull=True)
        total_missing = patients_to_update.count()
        
        self.stdout.write(f"Found {total_missing} patients missing department.")
        
        if total_missing == 0:
            return

        counts = {dept.name: 0 for dept in departments}

        # Instead of random.choices in a loop (slow for large items), use random.choices once
        chosen_departments = random.choices(departments, weights=weights, k=total_missing)
        
        updated_patients = []
        for i, patient in enumerate(patients_to_update):
            chosen_dept = chosen_departments[i]
            units = units_by_dept[chosen_dept.id]
            chosen_unit = random.choice(units)
            
            patient.department_obj = chosen_dept
            patient.department = chosen_dept.name
            patient.unit_obj = chosen_unit
            patient.unit_doctor = chosen_unit.unit_name
            
            updated_patients.append(patient)
            counts[chosen_dept.name] += 1
            
        if not dry_run:
            with transaction.atomic():
                Patient.objects.bulk_update(
                    updated_patients,
                    ['department_obj', 'department', 'unit_obj', 'unit_doctor'],
                    batch_size=2000
                )
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {total_missing} patients."))
        else:
            self.stdout.write(self.style.WARNING("DRY RUN: No data was changed."))

        self.stdout.write("\nDistribution summary:")
        for name, count in counts.items():
            percent = (count / total_missing) * 100
            target_percent = (target_weights[name] / sum(target_weights.values())) * 100
            self.stdout.write(f"{name}: {count} ({percent:.1f}% vs target {target_percent:.1f}%)")
