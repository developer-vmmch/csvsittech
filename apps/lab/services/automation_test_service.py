import random
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from apps.lab.synthetic_patient_generator import SyntheticPatientGenerator
from apps.lab.models import (
    AutomationDummyResult, 
    AutomationDummyResultParameter, 
    InvestigationParameter, 
    ParameterReferenceRange, 
    AgeGroup
)

class AutomationTestService:
    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def find_best_reference_range(inv_param, age_days, gender):
        age_groups = []
        for ag in AgeGroup.objects.filter(is_active=True):
            min_d = AutomationTestService.age_to_days(ag.min_age_value, ag.min_age_unit)
            max_d = AutomationTestService.age_to_days(ag.max_age_value, ag.max_age_unit)
            if min_d <= age_days <= max_d:
                age_groups.append(ag)

        qs = ParameterReferenceRange.objects.filter(investigation_parameter=inv_param, is_active=True)
        # Priority 1: specific gender + specific age group
        for ag in age_groups:
            r = qs.filter(age_group=ag, gender=gender).first()
            if r: return r
        # Priority 2: All gender + specific age group
        for ag in age_groups:
            r = qs.filter(age_group=ag, gender='All').first()
            if r: return r
        # Priority 3: specific gender + no age group
        r = qs.filter(age_group__isnull=True, gender=gender).first()
        if r: return r
        # Priority 4: All gender + no age group
        r = qs.filter(age_group__isnull=True, gender='All').first()
        if r: return r
        return qs.first()

    @staticmethod
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

    @staticmethod
    def generate_value(ref_range):
        if ref_range is None:
            return str(round(random.uniform(5.0, 20.0), 1))
        if ref_range.range_type == 'Numeric':
            if ref_range.min_value is not None and ref_range.max_value is not None:
                min_f = float(ref_range.min_value)
                max_f = float(ref_range.max_value)
                if max_f <= min_f:
                    return str(round(min_f, 2))
                val = random.uniform(min_f, max_f)
                max_str = str(ref_range.max_value.normalize())
                dec_places = len(max_str.split('.')[1]) if '.' in max_str else 1
                dec_places = max(1, min(dec_places, 3))
                return str(round(val, dec_places))
            elif ref_range.max_value is not None:
                max_f = float(ref_range.max_value)
                val = random.uniform(max_f * 0.7, max_f * 1.1)
                max_str = str(ref_range.max_value.normalize())
                dec_places = len(max_str.split('.')[1]) if '.' in max_str else 1
                dec_places = max(1, min(dec_places, 3))
                return str(round(val, dec_places))
        rt = ref_range.reference_text
        if rt and rt not in ('-', '', 'None'):
            if "A / B / AB / O" in rt:
                return random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            return rt.strip()
        return "Normal"

    @staticmethod
    def generate_dummy_values_for_investigation(investigation, age_days=None, gender=None):
        if age_days is None:
            age_days = random.uniform(365 * 18, 365 * 60) # Default Adult
        if gender is None:
            gender = random.choice(['Male', 'Female'])

        params = InvestigationParameter.objects.filter(
            investigation=investigation, is_active=True
        ).select_related('parameter').order_by('display_order', 'id')
        
        result_data = []
        for p in params:
            ref_range = AutomationTestService.find_best_reference_range(p, age_days, gender)
            val = AutomationTestService.generate_value(ref_range)
            ref_str = AutomationTestService.format_range_str(ref_range)
            unit = p.unit or (getattr(p.parameter, 'default_unit', '') if p.parameter else '') or ''
            result_data.append({
                'parameter_id': p.parameter.id if p.parameter else p.id,
                'parameter_name': p.parameter.name if p.parameter else p.name,
                'result_value': val,
                'unit': unit,
                'reference_range': ref_str
            })
            
        return {
            'age_days': age_days,
            'gender': gender,
            'parameters': result_data
        }

    @staticmethod
    def make_result_id():
        now = timezone.now()
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

    @classmethod
    def generate_and_save_dummy_result(cls, investigation, admin_user, age_days=None, gender=None, result_count=1):
        if age_days is None:
            age_days = random.uniform(365 * 18, 365 * 60)
        if gender is None:
            gender = random.choice(['Male', 'Female'])

        data = cls.generate_dummy_values_for_investigation(investigation, age_days, gender)
        
        dob = date.today() - timedelta(days=int(age_days))
        age_display = cls.format_age_display(age_days)
        result_id = cls.make_result_id()
        dummy_name = f"{investigation.short_name or investigation.name} #{result_count}"
        
        patient = SyntheticPatientGenerator.generate_patient(gender=gender)
        name = f"{patient['first_name']} {patient['last_name']}"

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
            for disp_order, p_data in enumerate(data['parameters']):
                AutomationDummyResultParameter.objects.create(
                    dummy_result=dummy,
                    parameter_id=p_data['parameter_id'],
                    parameter_name=p_data['parameter_name'],
                    result_value=p_data['result_value'],
                    unit=p_data['unit'],
                    reference_range=p_data['reference_range'],
                    display_order=disp_order,
                )
        return dummy
