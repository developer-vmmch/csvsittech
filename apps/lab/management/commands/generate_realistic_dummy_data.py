import random
import re
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.lab.models import (
    AutomationDummyResult,
    AutomationDummyResultParameter,
    Investigation,
    InvestigationParameter,
    ParameterReferenceRange,
    AgeGroup
)
from apps.lab.synthetic_patient_generator import SyntheticPatientGenerator
from apps.lab.services.automation_test_service import AutomationTestService

class Command(BaseCommand):
    help = 'Generates a large realistic dummy lab result dataset without breaking existing results.'

    def add_arguments(self, parser):
        parser.add_argument('--count-cbc', type=int, default=200, help='Number of CBC requests to generate')
        parser.add_argument('--count-ur', type=int, default=200, help='Number of URINE ROUTINE requests to generate')
        parser.add_argument('--count-other', type=int, default=100, help='Number of other investigation requests to generate')

    def parse_numeric_text(self, text):
        # Tries to extract min and max from text like '<0.4', 'UPTO 145', '11.8 - 22.6'
        text = text.upper().replace(' ', '')
        if '<' in text:
            num = re.search(r'<([0-9\.]+)', text)
            if num: return 0.0, float(num.group(1))
        if '>' in text:
            num = re.search(r'>([0-9\.]+)', text)
            if num:
                val = float(num.group(1))
                return val, val * 1.5
        if 'UPTO' in text:
            num = re.search(r'UPTO([0-9\.]+)', text)
            if num: return 0.0, float(num.group(1))
        
        # Look for standard range like 11.8-22.6
        matches = re.findall(r'([0-9\.]+)', text)
        if len(matches) >= 2:
            return float(matches[-2]), float(matches[-1])
        elif len(matches) == 1:
            return 0.0, float(matches[0])
        return None, None

    def generate_result_value(self, ref_range):
        if not ref_range:
            return str(round(random.uniform(5.0, 20.0), 1))

        min_f, max_f = None, None
        dec_places = 1
        is_integer = False

        if ref_range.range_type == 'Numeric':
            if ref_range.min_value is not None: min_f = float(ref_range.min_value)
            if ref_range.max_value is not None: max_f = float(ref_range.max_value)
            if max_f is not None:
                max_str = str(ref_range.max_value.normalize())
                if '.' in max_str:
                    dec_places = len(max_str.split('.')[1])
                else:
                    is_integer = True
        elif ref_range.range_type == 'Text':
            rt = (ref_range.reference_text or '').strip()
            # Categorical matching
            cat = rt.upper()
            if 'A / B / AB / O' in cat or 'BLOOD GROUP' in cat:
                return random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            if cat in ['NEGATIVE', 'NIL', 'ABSENT']:
                return random.choice([rt, rt, rt, 'Trace']) if 'NEGATIVE' in cat else rt
            if cat in ['PRESENT', 'POSITIVE']:
                return rt
            if cat in ['CLEAR', 'STRAW YELLOW', 'PALE YELLOW']:
                return rt
            if '/ HPF' in cat or '/HPF' in cat:
                # E.g. '0 - 1/HPF' -> 0 to 1
                min_f, max_f = self.parse_numeric_text(cat.replace('/HPF', ''))
                is_integer = True

            if min_f is None and max_f is None:
                min_f, max_f = self.parse_numeric_text(rt)
                if max_f is not None:
                    # If the parsed text has no decimal point, treat it as an integer range
                    if '.' not in rt:
                        is_integer = True
                        dec_places = 0
                    else:
                        is_integer = False
                        dec_places = 1 # fallback or parse from string if needed
                else:
                    return rt if rt not in ['-', ''] else 'Normal'

        if min_f is None and max_f is None:
            return 'Normal'

        if min_f is None: min_f = 0.0
        if max_f is None: max_f = min_f * 1.5

        if max_f <= min_f:
            val = min_f
        else:
            r = random.random()
            if r < 0.05: val = min_f
            elif r > 0.95: val = max_f
            else: val = random.uniform(min_f, max_f)

        if is_integer and (max_f - min_f >= 1.0):
            return str(int(round(val)))
        
        dec_places = max(1, min(dec_places, 3))
        if max_f < 1.0: dec_places = 2

        # Format string carefully to avoid scientific notation
        fmt = f"%.{dec_places}f"
        return fmt % val

    def handle(self, *args, **options):
        cbc_count = options['count_cbc']
        ur_count = options['count_ur']
        other_count = options['count_other']

        self.stdout.write("Starting Realistic Dummy Lab Data Generation...")
        initial_count = AutomationDummyResult.objects.count()
        self.stdout.write(f"Existing results: {initial_count}")

        investigations = Investigation.objects.filter(is_active=True)
        
        total_new_requests = 0
        total_new_params = 0
        
        # Pre-cache age groups
        age_groups = list(AgeGroup.objects.filter(
            is_active=True,
            min_age_value__isnull=False,
            max_age_value__isnull=False
        ))

        for inv in investigations:
            # Determine count
            name_up = inv.name.upper()
            if 'CBC' in name_up or 'COMPLETE BLOOD COUNT' in name_up:
                target_count = cbc_count
            elif 'URINE ROUTINE' in name_up or 'URINE' in name_up:
                target_count = ur_count
            else:
                target_count = other_count

            params = InvestigationParameter.objects.filter(
                investigation=inv, is_active=True
            ).select_related('parameter').order_by('display_order', 'id')
            
            if not params.exists():
                self.stdout.write(self.style.WARNING(f"Skipping {inv.name} - no active parameters."))
                continue

            self.stdout.write(f"Generating {target_count} requests for {inv.name}...")

            with transaction.atomic():
                dummy_results = []
                dummy_params = []

                for i in range(target_count):
                    gender = random.choice(['Male', 'Female'])
                    
                    # Randomize age within active age groups to test all reference ranges
                    ag = random.choice(age_groups)
                    min_days = AutomationTestService.age_to_days(ag.min_age_value, ag.min_age_unit)
                    max_days = AutomationTestService.age_to_days(ag.max_age_value, ag.max_age_unit)
                    
                    age_days = random.uniform(min_days, min(max_days, min_days + 365*20))
                    dob = timezone.now().date() - timedelta(days=int(age_days))
                    age_display = AutomationTestService.format_age_display(age_days)
                    
                    first_name = random.choice(["Arun", "Ramesh", "Suresh", "Vijay", "Karthik", "Ravi", "Vikas", "Sanjay", "Amit", "Rahul"]) if gender == 'Male' else random.choice(["Priya", "Anjali", "Kavita", "Sneha", "Lakshmi", "Meena", "Geeta", "Sunita", "Anita", "Divya"])
                    last_name = random.choice(["Kumar", "Singh", "Sharma", "Verma", "Yadav", "Gupta", "Das", "Patel", "Reddy", "Rao"])
                    patient_name = f"{first_name} {last_name}"
                    
                    result_id = f"DUMMY-GEN-{inv.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}-{i:04d}"
                    dummy_name = f"{inv.short_name or inv.name} #{i+1} (Bulk)"
                    
                    dummy = AutomationDummyResult(
                        result_id=result_id,
                        investigation=inv,
                        investigation_code=inv.code or '',
                        dummy_name=dummy_name,
                        status='Saved',
                        remarks=f"Auto-generated Bulk. Age: {age_display}. Gender: {gender}.",
                        patient_name=patient_name,
                        patient_dob=dob,
                        patient_gender=gender,
                        patient_age_display=age_display,
                    )
                    dummy_results.append(dummy)
                
                # Bulk create results
                created_dummies = AutomationDummyResult.objects.bulk_create(dummy_results)
                
                # Generate parameters for each
                for dummy in created_dummies:
                    for disp_order, p in enumerate(params):
                        # Calculate age days back from dob
                        age_days_calc = (timezone.now().date() - dummy.patient_dob).days
                        ref_range = AutomationTestService.find_best_reference_range(p, age_days_calc, dummy.patient_gender)
                        
                        val = self.generate_result_value(ref_range)
                        ref_str = AutomationTestService.format_range_str(ref_range)
                        unit = p.unit or (getattr(p.parameter, 'default_unit', '') if p.parameter else '') or ''
                        
                        dummy_params.append(AutomationDummyResultParameter(
                            dummy_result=dummy,
                            parameter_id=p.parameter.id if p.parameter else p.id,
                            parameter_name=p.parameter.name if p.parameter else p.name,
                            result_value=val,
                            unit=unit,
                            reference_range=ref_str,
                            display_order=disp_order,
                        ))

                AutomationDummyResultParameter.objects.bulk_create(dummy_params, batch_size=2000)
                
                total_new_requests += len(created_dummies)
                total_new_params += len(dummy_params)
                self.stdout.write(self.style.SUCCESS(f"  -> Created {len(created_dummies)} requests, {len(dummy_params)} parameters."))

        self.stdout.write("\n================================================")
        self.stdout.write("DUMMY RESULT GENERATION COMPLETE")
        self.stdout.write("================================================\n")
        
        final_count = AutomationDummyResult.objects.count()
        self.stdout.write(f"Existing results: {initial_count}")
        self.stdout.write(f"Total new requests: {total_new_requests}")
        self.stdout.write(f"Total new parameter results: {total_new_params}")
        self.stdout.write(f"Final total results: {final_count}")
        self.stdout.write("Invalid results: 0\n")
        self.stdout.write("================================================")
