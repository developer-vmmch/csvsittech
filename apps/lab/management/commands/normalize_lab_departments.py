from django.core.management.base import BaseCommand
from apps.lab.models import LabDepartment, Investigation

class Command(BaseCommand):
    help = 'Normalize Lab Departments according to the Lab Master architecture'

    def handle(self, *args, **kwargs):
        TARGETS = [
            'Hematology',
            'Clinical Biochemistry',
            'Microbiology',
            'Serology / Immunology',
            'Clinical Pathology',
            'Histopathology',
            'Cytology',
            'Blood Bank'
        ]

        MAPPING = {
            'Haematology': 'Hematology',
            'Biochemistry': 'Clinical Biochemistry',
            'Body Fluids': 'Clinical Pathology',
            'Urine': 'Clinical Pathology'
        }

        self.stdout.write("Starting Lab Department Normalization...")

        # Create target departments if they don't exist
        target_depts = {}
        for name in TARGETS:
            dept, created = LabDepartment.objects.get_or_create(name=name)
            target_depts[name] = dept
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created missing target department: {name}"))
            else:
                if not dept.is_active:
                    dept.is_active = True
                    dept.save()
                    self.stdout.write(self.style.SUCCESS(f"Activated target department: {name}"))

        # Apply mappings
        for old_name, new_name in MAPPING.items():
            try:
                old_dept = LabDepartment.objects.get(name__iexact=old_name)
                target_dept = target_depts[new_name]
                
                # Re-map investigations
                invs_updated = Investigation.objects.filter(department=old_dept).update(department=target_dept)
                self.stdout.write(self.style.SUCCESS(f"Re-mapped {invs_updated} investigations from {old_name} to {new_name}"))
                
                # Deactivate the old department
                old_dept.is_active = False
                old_dept.save()
                self.stdout.write(self.style.WARNING(f"Deactivated old department: {old_name}"))
            except LabDepartment.DoesNotExist:
                pass

        # Handle Molecular Diagnostics
        try:
            mol = LabDepartment.objects.get(name__iexact='Molecular Diagnostics')
            inv_count = Investigation.objects.filter(department=mol).count()
            if inv_count == 0:
                mol.is_active = False
                mol.save()
                self.stdout.write(self.style.WARNING("Deactivated Molecular Diagnostics (0 investigations)"))
        except LabDepartment.DoesNotExist:
            LabDepartment.objects.create(name='Molecular Diagnostics', is_active=False)

        # Deactivate any other active departments not in the target list
        active_others = LabDepartment.objects.filter(is_active=True).exclude(name__in=TARGETS)
        for dept in active_others:
            dept.is_active = False
            dept.save()
            self.stdout.write(self.style.WARNING(f"Deactivated non-standard department: {dept.name}"))

        self.stdout.write(self.style.SUCCESS("Normalization Complete."))
