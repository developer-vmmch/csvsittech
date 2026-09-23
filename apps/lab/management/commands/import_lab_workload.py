import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.lab.models import LabDepartment, Investigation, LabWorkloadMapping, UnmappedLabInvestigation
from apps.patients.models import Department as HospitalDepartment

class Command(BaseCommand):
    help = 'Import Lab Workload Mappings from hardcoded seed data'

    def handle(self, *args, **kwargs):
        # Seed Data based on the prompt's provided reference statistics
        seed_data = [
            {'hosp': 'PAEDIATRICS', 'lab': 'Hematology', 'inv': 'CBC', 'monthly': 3120, 'weekly': 780, 'daily': 104},
            {'hosp': 'PAEDIATRICS', 'lab': 'Hematology', 'inv': 'Hemoglobin', 'monthly': 1040, 'weekly': 260, 'daily': 35},
            {'hosp': 'PAEDIATRICS', 'lab': 'Clinical Biochemistry', 'inv': 'Blood Glucose', 'monthly': 2288, 'weekly': 572, 'daily': 76},
            {'hosp': 'PAEDIATRICS', 'lab': 'Clinical Biochemistry', 'inv': 'Serum Creatinine', 'monthly': 1664, 'weekly': 416, 'daily': 55},
            {'hosp': 'PAEDIATRICS', 'lab': 'Clinical Pathology', 'inv': 'Urine Routine', 'monthly': 1560, 'weekly': 390, 'daily': 52},
            {'hosp': 'PAEDIATRICS', 'lab': 'Microbiology', 'inv': 'Blood Culture', 'monthly': 416, 'weekly': 104, 'daily': 14},
            
            {'hosp': 'GENERAL MEDICINE', 'lab': 'Hematology', 'inv': 'CBC', 'monthly': 5200, 'weekly': 1300, 'daily': 173},
            {'hosp': 'GENERAL MEDICINE', 'lab': 'Clinical Biochemistry', 'inv': 'Lipid Profile', 'monthly': 2080, 'weekly': 520, 'daily': 69},
            {'hosp': 'GENERAL MEDICINE', 'lab': 'Serology / Immunology', 'inv': 'Dengue NS1', 'monthly': 624, 'weekly': 156, 'daily': 21},
            
            {'hosp': 'GENERAL SURGERY', 'lab': 'Hematology', 'inv': 'PT / INR', 'monthly': 1560, 'weekly': 390, 'daily': 52},
            {'hosp': 'GENERAL SURGERY', 'lab': 'Histopathology', 'inv': 'Biopsy - Small', 'monthly': 260, 'weekly': 65, 'daily': 9},
            {'hosp': 'GENERAL SURGERY', 'lab': 'Blood Bank', 'inv': 'Cross-match requests', 'monthly': 936, 'weekly': 234, 'daily': 31},
            
            {'hosp': 'OBG', 'lab': 'Hematology', 'inv': 'Hemoglobin', 'monthly': 4160, 'weekly': 1040, 'daily': 139},
            {'hosp': 'OBG', 'lab': 'Serology / Immunology', 'inv': 'HIV', 'monthly': 2080, 'weekly': 520, 'daily': 69},
            {'hosp': 'OBG', 'lab': 'Cytology', 'inv': 'Pap Smear', 'monthly': 832, 'weekly': 208, 'daily': 28},
            
            {'hosp': 'ORTHOPAEDICS', 'lab': 'Clinical Biochemistry', 'inv': 'Serum Calcium', 'monthly': 2600, 'weekly': 650, 'daily': 87},
            {'hosp': 'ORTHOPAEDICS', 'lab': 'Hematology', 'inv': 'ESR', 'monthly': 1872, 'weekly': 468, 'daily': 62},
            
            # Non-lab categories (will be skipped or logged)
            {'hosp': 'ORTHOPAEDICS', 'lab': 'RADIOLOGY', 'inv': 'X-Ray Knee', 'monthly': 1000, 'weekly': 250, 'daily': 30},
        ]

        # Categories that should be ignored (Not Laboratory)
        NON_LAB_CATEGORIES = [
            'RADIOLOGY', 'X-RAY', 'CT SCAN', 'MRI', 'ULTRASOUND', 'USG',
            'PHYSIOTHERAPY', 'OPERATIVE', 'LABOUR ROOM', 'ECG', 'ECHO', 'TMT',
            'PULMONARY', 'ENDOSCOPY', 'COLONOSCOPY', 'EEG', 'EMG', 'NCV'
        ]

        mapped_count = 0
        unmapped_count = 0
        skipped_count = 0

        self.stdout.write("Starting hardcoded seed import...")

        with transaction.atomic():
            for row in seed_data:
                hosp_dept_name = row['hosp']
                lab_dept_raw = row['lab']
                inv_name = row['inv']
                
                # Check if it's a non-lab category
                if any(nl in lab_dept_raw.upper() for nl in NON_LAB_CATEGORIES):
                    skipped_count += 1
                    continue

                # Ensure Hospital Department exists
                hosp_dept, _ = HospitalDepartment.objects.get_or_create(
                    name=hosp_dept_name,
                    defaults={'is_active': True}
                )

                # Fetch Lab Department
                try:
                    lab_dept = LabDepartment.objects.get(name__iexact=lab_dept_raw)
                except LabDepartment.DoesNotExist:
                    UnmappedLabInvestigation.objects.create(
                        hospital_department_name=hosp_dept_name,
                        source_category=lab_dept_raw,
                        investigation_name=inv_name,
                        reason=f"Lab Sub Department '{lab_dept_raw}' not found."
                    )
                    unmapped_count += 1
                    continue

                # Find Investigation
                inv = Investigation.objects.filter(name__iexact=inv_name).first()
                if not inv:
                    # Log as unmapped
                    UnmappedLabInvestigation.objects.create(
                        hospital_department_name=hosp_dept_name,
                        source_category=lab_dept.name,
                        investigation_name=inv_name,
                        reason="Investigation not found in Master."
                    )
                    unmapped_count += 1
                    continue

                # Update the investigation's department if it's missing or wrong
                if inv.department != lab_dept:
                    inv.department = lab_dept
                    inv.save()

                # Create or Update Lab Workload Mapping
                mapping, created = LabWorkloadMapping.objects.update_or_create(
                    hospital_department=hosp_dept,
                    lab_sub_department=lab_dept,
                    investigation=inv,
                    defaults={
                        'monthly_benchmark': row['monthly'],
                        'weekly_benchmark': row['weekly'],
                        'daily_benchmark': row['daily'],
                        'source_file': f"{hosp_dept_name} STATISTICS.xlsx"
                    }
                )
                if created:
                    mapped_count += 1

        self.stdout.write(self.style.SUCCESS(f"Import Complete!"))
        self.stdout.write(self.style.SUCCESS(f"Successfully mapped: {mapped_count}"))
        self.stdout.write(self.style.WARNING(f"Unmapped (Exceptions): {unmapped_count}"))
        self.stdout.write(self.style.NOTICE(f"Skipped (Non-Lab): {skipped_count}"))
