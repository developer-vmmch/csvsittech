"""
generate_dummy_results.py
Idempotent management command that generates dummy lab results for all investigations.
Uses existing master data (InvestigationParameter, ParameterReferenceRange, AgeGroup)
as the single source of truth for units and reference ranges.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

MALE_NAMES = [
    "Arun Kumar", "Ramesh Singh", "Suresh Sharma", "Vijay Verma", "Karthik Yadav",
    "Ravi Gupta", "Vikas Das", "Sanjay Patel", "Amit Reddy", "Rahul Rao",
    "Prakash Nair", "Ganesh Iyer", "Ashok Chauhan", "Rajesh Jain", "Naveen Mishra",
    "Deepak Kumar", "Mukesh Singh", "Sunil Sharma", "Mahesh Verma", "Santosh Yadav",
]
FEMALE_NAMES = [
    "Priya Kumar", "Anjali Singh", "Kavita Sharma", "Sneha Verma", "Lakshmi Yadav",
    "Meena Gupta", "Geeta Das", "Sunita Patel", "Anita Reddy", "Divya Rao",
    "Pooja Nair", "Rekha Iyer", "Renu Chauhan", "Swati Jain", "Aarti Mishra",
    "Nisha Kumar", "Radha Singh", "Savita Sharma", "Beena Verma", "Vimala Yadav",
]


def age_to_days(value, unit):
    unit = unit.strip().lower()
    if unit in ('days', 'day'):
        return value
    elif unit in ('weeks', 'week'):
        return value * 7
    elif unit in ('months', 'month'):
        return value * 30
    elif unit in ('years', 'year'):
        return value * 365
    return value * 365


def format_age_display(total_days):
    if total_days < 1:
        return "< 1 day"
    if total_days < 30:
        d = round(total_days)
        return f"{d} day{'s' if d != 1 else ''}"
    if total_days < 365:
        m = round(total_days / 30)
        return f"{m} month{'s' if m != 1 else ''}"
    years = int(total_days // 365)
    rem_months = int((total_days % 365) // 30)
    if rem_months:
        return f"{years} yr {rem_months} mo"
    return f"{years} year{'s' if years != 1 else ''}"


def dob_from_age_days(age_days):
    return date.today() - timedelta(days=int(age_days))


def find_best_reference_range(inv_param, age_days, gender):
    from apps.lab.models import ParameterReferenceRange, AgeGroup
    age_groups = []
    for ag in AgeGroup.objects.filter(is_active=True):
        min_d = age_to_days(ag.min_age_value, ag.min_age_unit)
        max_d = age_to_days(ag.max_age_value, ag.max_age_unit)
        if min_d <= age_days <= max_d:
            age_groups.append(ag)

    qs = ParameterReferenceRange.objects.filter(
        investigation_parameter=inv_param, is_active=True
    )
    # Priority 1: specific gender + specific age group
    for ag in age_groups:
        r = qs.filter(age_group=ag, gender=gender).first()
        if r:
            return r
    # Priority 2: All gender + specific age group
    for ag in age_groups:
        r = qs.filter(age_group=ag, gender='All').first()
        if r:
            return r
    # Priority 3: specific gender + no age group
    r = qs.filter(age_group__isnull=True, gender=gender).first()
    if r:
        return r
    # Priority 4: All gender + no age group
    r = qs.filter(age_group__isnull=True, gender='All').first()
    if r:
        return r
    return qs.first()


def format_range_str(ref_range):
    if not ref_range:
        return "-"
    if ref_range.range_type == 'Numeric':
        if ref_range.min_value is None and ref_range.max_value is None:
            return ref_range.reference_text or "-"
        min_v = f"{ref_range.min_value.normalize():f}" if ref_range.min_value is not None else ""
        max_v = f"{ref_range.max_value.normalize():f}" if ref_range.max_value is not None else ""
        return f"{min_v}-{max_v}".strip("-")
    elif ref_range.range_type == 'Text':
        return ref_range.reference_text or "-"
    return "-"


def generate_value(ref_range):
    if ref_range is None:
        return str(round(random.uniform(5.0, 20.0), 1))
    if ref_range.range_type == 'Numeric' and ref_range.min_value is not None and ref_range.max_value is not None:
        min_f = float(ref_range.min_value)
        max_f = float(ref_range.max_value)
        if max_f <= min_f:
            return str(round(min_f, 2))
        val = random.uniform(min_f, max_f)
        max_str = str(ref_range.max_value.normalize())
        dec_places = len(max_str.split('.')[1]) if '.' in max_str else 1
        dec_places = max(1, min(dec_places, 3))
        return str(round(val, dec_places))
    # Text or missing numeric bounds — return reference_text as result
    rt = ref_range.reference_text
    if rt and rt not in ('-', '', 'None'):
        return rt.strip()
    return "Normal"


def make_result_id():
    from apps.lab.models import AutomationDummyResult
    from datetime import datetime
    now = datetime.now()
    id_prefix = f"DUMMY-{now.strftime('%Y%m%d')}-"
    last = AutomationDummyResult.objects.filter(result_id__startswith=id_prefix).order_by('-result_id').first()
    if last:
        try:
            num = int(last.result_id.split('-')[-1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"{id_prefix}{num:05d}"


def create_dummy_result(investigation, age_days, gender, admin_user, result_count):
    from apps.lab.models import (
        AutomationDummyResult, AutomationDummyResultParameter, InvestigationParameter
    )
    name = random.choice(MALE_NAMES if gender == 'Male' else FEMALE_NAMES)
    dob = dob_from_age_days(age_days)
    age_display = format_age_display(age_days)
    result_id = make_result_id()
    dummy_name = f"{investigation.short_name or investigation.name} #{result_count}"

    params = list(
        InvestigationParameter.objects
        .filter(investigation=investigation, is_active=True)
        .select_related('parameter')
        .order_by('display_order', 'id')
    )

    with transaction.atomic():
        dummy = AutomationDummyResult.objects.create(
            result_id=result_id,
            investigation=investigation,
            investigation_code=investigation.code or '',
            dummy_name=dummy_name,
            created_by=admin_user,
            status='Saved',
            remarks=f"Auto-generated. Age: {age_display}. Gender: {gender}.",
            patient_name=name,
            patient_dob=dob,
            patient_gender=gender,
            patient_age_display=age_display,
        )
        for disp_order, p in enumerate(params):
            param_name = p.parameter.name if p.parameter else p.name
            unit = p.unit or (getattr(p.parameter, 'default_unit', '') if p.parameter else '') or ''
            ref_range = find_best_reference_range(p, age_days, gender)
            ref_str = format_range_str(ref_range)
            val_str = generate_value(ref_range)
            AutomationDummyResultParameter.objects.create(
                dummy_result=dummy,
                parameter=p.parameter,
                parameter_name=param_name,
                result_value=val_str,
                unit=unit,
                reference_range=ref_str,
                display_order=disp_order,
            )
    return dummy


class Command(BaseCommand):
    help = 'Generates dummy lab results for all investigations using existing master data.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing dummy results first.')
        parser.add_argument('--investigation', type=str, default='all',
                            help='Comma-separated partial investigation names. Default: all.')

    def handle(self, *args, **options):
        from apps.lab.models import Investigation, AutomationDummyResult

        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        if options['clear']:
            deleted, _ = AutomationDummyResult.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing dummy results."))

        # --- AEC age specs ---
        aec_patients = (
            [{'age_days': random.uniform(0.5, 7), 'gender': random.choice(['Male', 'Female'])} for _ in range(10)] +
            [{'age_days': random.uniform(365, 365 * 7), 'gender': random.choice(['Male', 'Female'])} for _ in range(5)] +
            [{'age_days': random.uniform(365 * 7 + 1, 365 * 30), 'gender': random.choice(['Male', 'Female'])} for _ in range(15)]
        )

        SPECS = [
            {'search': 'AEC',                 'patients': aec_patients},
            {'search': 'Complete Blood Count','patients': [{'age_days': random.uniform(365*18, 365*55), 'gender': random.choice(['Male','Female'])} for _ in range(20)]},
            {'search': 'URINE ROUTINE',       'patients': [{'age_days': random.uniform(365*10, 365*60), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'ESR',                 'patients': [{'age_days': random.uniform(365*15, 365*70), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'ELECTROLYTES',        'patients': [{'age_days': random.uniform(365*20, 365*60), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'RFT',                 'patients': [{'age_days': random.uniform(365*25, 365*65), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'LFT',                 'patients': [{'age_days': random.uniform(365*20, 365*60), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'THYROID',             'patients': (
                [{'age_days': random.uniform(1, 4),         'gender': 'Male'}   for _ in range(2)] +
                [{'age_days': random.uniform(30, 330),      'gender': 'Female'} for _ in range(2)] +
                [{'age_days': random.uniform(365, 365*5),   'gender': 'Male'}   for _ in range(2)] +
                [{'age_days': random.uniform(365*6, 365*10),'gender': 'Female'} for _ in range(2)] +
                [{'age_days': random.uniform(365*16, 365*60),'gender': 'Female'}for _ in range(4)] +
                [{'age_days': random.uniform(365*51, 365*80),'gender': 'Male'}  for _ in range(3)]
            )},
            {'search': 'GRBS',                'patients': [{'age_days': random.uniform(365*18, 365*70), 'gender': random.choice(['Male','Female'])} for _ in range(10)]},
            {'search': 'FERRITIN',            'patients': (
                [{'age_days': random.uniform(365*2, 365*17),  'gender': random.choice(['Male','Female'])} for _ in range(5)] +
                [{'age_days': random.uniform(365*18, 365*55), 'gender': 'Male'}   for _ in range(5)] +
                [{'age_days': random.uniform(365*18, 365*55), 'gender': 'Female'} for _ in range(5)]
            )},
        ]

        inv_filter = options['investigation']
        if inv_filter != 'all':
            filters = [f.strip().upper() for f in inv_filter.split(',')]
            SPECS = [s for s in SPECS if any(f in s['search'].upper() for f in filters)]

        total_created = 0
        for spec in SPECS:
            search_term = spec['search']
            inv = (
                Investigation.objects.filter(name__icontains=search_term, is_active=True).first() or
                Investigation.objects.filter(short_name__icontains=search_term, is_active=True).first()
            )
            if not inv:
                self.stdout.write(self.style.WARNING(f"  SKIP: '{search_term}' not found."))
                continue

            self.stdout.write(f"\nGenerating {len(spec['patients'])} results for '{inv.name}'...")
            for idx, ps in enumerate(spec['patients'], start=1):
                gender = ps['gender']
                existing_count = AutomationDummyResult.objects.filter(investigation=inv).count()
                try:
                    dummy = create_dummy_result(inv, ps['age_days'], gender, admin_user, existing_count + 1)
                    total_created += 1
                    self.stdout.write(f"  [{idx}] {dummy.result_id} | {dummy.patient_name} | {dummy.patient_age_display} | {gender}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ERROR [{idx}]: {e}"))
                    import traceback; traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(f"\nDone. Total dummy results created: {total_created}"))
