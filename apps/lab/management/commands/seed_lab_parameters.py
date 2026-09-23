import os
import csv
from django.core.management.base import BaseCommand
from apps.lab.models import Parameter, Investigation, InvestigationParameter

class Command(BaseCommand):
    help = 'Seed lab parameters and investigation parameter mappings from CSV files'

    def add_arguments(self, parser):
        parser.add_argument('--params-file', type=str, default='seed_parameters.csv', help='Path to seed_parameters.csv')
        parser.add_argument('--mapping-file', type=str, default='seed_investigation_parameter_mapping.csv', help='Path to seed_investigation_parameter_mapping.csv')

    def handle(self, *args, **options):
        params_file = options['params_file']
        mapping_file = options['mapping_file']

        self.stdout.write(self.style.NOTICE(f'Starting seeding from {params_file} and {mapping_file}...'))
        
        # 1. Fallback Dummy Data generation if files are missing
        if not os.path.exists(params_file) or not os.path.exists(mapping_file):
            self.stdout.write(self.style.WARNING(f'CSV files not found in {os.getcwd()}. Using fallback internal data...'))
            self._seed_fallback_data()
            return
            
        params_created = 0
        params_existed = 0
        
        # Load Parameters
        with open(params_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '').strip()
                unit = row.get('default_unit', '').strip()
                data_type = row.get('data_type', 'NUMERIC').strip()
                
                if not name:
                    continue
                    
                obj, created = Parameter.objects.get_or_create(
                    name=name,
                    defaults={
                        'code': f'PRM-{name.upper()[:10].replace(" ", "")}', 
                        'default_unit': unit, 
                        'data_type': data_type
                    }
                )
                if created:
                    params_created += 1
                else:
                    params_existed += 1

        inv_created = 0
        inv_existed = 0
        mapping_created = 0
        mapping_existed = 0
        
        # Load Mappings
        with open(mapping_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                inv_code = row.get('investigation_legacy_code', '').strip()
                inv_name = row.get('investigation_name', '').strip()
                param_name = row.get('parameter_name', '').strip()
                unit = row.get('unit', '').strip()
                order_val = row.get('display_order', 1)
                
                try:
                    display_order = int(order_val)
                except ValueError:
                    display_order = 1
                
                if not inv_code or not inv_name or not param_name:
                    continue
                
                # Get or Create Investigation
                inv, created = Investigation.objects.get_or_create(
                    legacy_code=inv_code,
                    defaults={
                        'name': inv_name,
                        'code': f'INV-{inv_code}',
                        'is_panel': True
                    }
                )
                if created:
                    inv_created += 1
                else:
                    inv_existed += 1
                    
                # Find Parameter
                param = Parameter.objects.filter(name=param_name).first()
                if not param:
                    self.stdout.write(self.style.ERROR(f'Parameter {param_name} not found!'))
                    continue
                
                # Get or Create Mapping
                mapping, m_created = InvestigationParameter.objects.get_or_create(
                    investigation=inv,
                    parameter=param,
                    defaults={
                        'unit': unit or param.default_unit,
                        'display_order': display_order
                    }
                )
                
                if m_created:
                    mapping_created += 1
                else:
                    mapping_existed += 1
                    
        self.stdout.write(self.style.SUCCESS(
            f'Summary:\n'
            f'- Parameters: {params_created} created, {params_existed} existed\n'
            f'- Investigations: {inv_created} created, {inv_existed} existed\n'
            f'- Mappings: {mapping_created} created, {mapping_existed} existed\n'
        ))

    def _seed_fallback_data(self):
        # Fallback dummy data if CSVs are missing
        parameters_data = [
            # CBC
            ("Hemoglobin", "g/dL"), ("WBC", "cells/cumm"), ("RBC", "mill/cumm"), 
            ("Platelets", "lakhs/cumm"), ("Hematocrit", "%"), ("MCV", "fL"), ("MCH", "pg"), ("MCHC", "g/dL"),
            # LFT
            ("Bilirubin Total", "mg/dL"), ("Bilirubin Direct", "mg/dL"), ("SGPT", "U/L"), 
            ("SGOT", "U/L"), ("Alkaline Phosphatase", "U/L"), ("Total Protein", "g/dL"), ("Albumin", "g/dL"),
            # RFT
            ("Urea", "mg/dL"), ("Creatinine", "mg/dL"), ("Uric Acid", "mg/dL"), 
            ("Sodium", "mEq/L"), ("Potassium", "mEq/L"), ("Chloride", "mEq/L"),
            # Lipid
            ("Total Cholesterol", "mg/dL"), ("Triglycerides", "mg/dL"), 
            ("HDL Cholesterol", "mg/dL"), ("LDL Cholesterol", "mg/dL"),
            # Other tests
            ("ESR", "mm/hr"), ("HbA1c", "%"), ("Fasting Blood Sugar", "mg/dL"), 
            ("PP Blood Sugar", "mg/dL"), ("Random Blood Sugar", "mg/dL"),
            # TFT
            ("T3", "ng/dL"), ("T4", "ug/dL"), ("TSH", "uIU/mL")
        ]
        
        investigations_data = [
            ("00020537", "CBC", ["Hemoglobin", "WBC", "RBC", "Platelets", "Hematocrit", "MCV", "MCH", "MCHC"]),
            ("00020538", "LFT", ["Bilirubin Total", "Bilirubin Direct", "SGPT", "SGOT", "Alkaline Phosphatase", "Total Protein", "Albumin"]),
            ("00020539", "RFT", ["Urea", "Creatinine", "Uric Acid", "Sodium", "Potassium", "Chloride"]),
            ("00020540", "Lipid Profile", ["Total Cholesterol", "Triglycerides", "HDL Cholesterol", "LDL Cholesterol"]),
            ("00020541", "ESR", ["ESR"]),
            ("00020542", "HbA1c", ["HbA1c"]),
            ("00020543", "Fasting Blood Sugar", ["Fasting Blood Sugar"]),
            ("00020544", "PP Blood Sugar", ["PP Blood Sugar"]),
            ("00020545", "Random Blood Sugar", ["Random Blood Sugar"]),
            ("00020546", "TFT", ["T3", "T4", "TSH"])
        ]
        
        params_created = 0
        inv_created = 0
        mapping_created = 0
        
        for i, (name, unit) in enumerate(parameters_data):
            obj, created = Parameter.objects.get_or_create(
                name=name, defaults={'code': f'PRM-{i}-{name.upper()[:8].replace(" ", "")}', 'default_unit': unit}
            )
            if created: params_created += 1
            
        for legacy_code, inv_name, param_names in investigations_data:
            inv, created = Investigation.objects.get_or_create(
                legacy_code=legacy_code,
                defaults={'name': inv_name, 'code': f'INV-{legacy_code}', 'is_panel': len(param_names) > 1}
            )
            if created: inv_created += 1
            
            for i, param_name in enumerate(param_names):
                param = Parameter.objects.get(name=param_name)
                mapping, m_created = InvestigationParameter.objects.get_or_create(
                    investigation=inv,
                    parameter=param,
                    defaults={'unit': param.default_unit, 'display_order': i+1}
                )
                if m_created: mapping_created += 1
                
        self.stdout.write(self.style.SUCCESS(
            f'Summary (Fallback Data):\n'
            f'- Parameters: {params_created} created\n'
            f'- Investigations: {inv_created} created\n'
            f'- Mappings: {mapping_created} created\n'
        ))
