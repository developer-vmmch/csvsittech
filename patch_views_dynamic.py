import os
import sys

views_path = r'c:\Users\Admin\Desktop\erp1\apps\lab\views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

target_context = """    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(PatientInvestigationOrder, id=kwargs.get('pk'))
        context['order'] = order
        
        parameters = InvestigationParameter.objects.filter(investigation=order.investigation, is_active=True).select_related('parameter')
        from .models import ParameterReferenceRange
        
        # Fetch reference range for display
        for p in parameters:
            ref = ParameterReferenceRange.objects.filter(investigation_parameter=p).first()
            if ref:
                if ref.range_type == 'Numeric':
                    p.display_ref_range = f"{ref.min_value} - {ref.max_value}"
                else:
                    p.display_ref_range = ref.reference_text or ''
            else:
                p.display_ref_range = ''
                
        context['parameters'] = parameters
        return context"""

new_context = """    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(PatientInvestigationOrder, id=kwargs.get('pk'))
        context['order'] = order
        
        patient = order.patient
        patient_gender = patient.gender or 'All'
        patient_age_days = (patient.age_years or 0) * 365 + (patient.age_months or 0) * 30 + (patient.age_days or 0)
        
        parameters = InvestigationParameter.objects.filter(investigation=order.investigation, is_active=True).select_related('parameter')
        from .models import ParameterReferenceRange
        
        # Fetch reference range for display dynamically
        for p in parameters:
            ranges = list(ParameterReferenceRange.objects.filter(investigation_parameter=p, is_active=True).select_related('age_group'))
            matched_ref = None
            
            # Try to find a precise match
            for ref in ranges:
                if ref.gender != 'All' and ref.gender != patient_gender:
                    continue
                
                if ref.age_group:
                    ag = ref.age_group
                    min_days, max_days = 0, 999999
                    
                    if ag.min_age_unit == 'Years': min_days = (ag.min_age_value or 0) * 365
                    elif ag.min_age_unit == 'Months': min_days = (ag.min_age_value or 0) * 30
                    elif ag.min_age_unit == 'Weeks': min_days = (ag.min_age_value or 0) * 7
                    elif ag.min_age_unit == 'Days': min_days = (ag.min_age_value or 0)
                    
                    if ag.max_age_unit == 'Years': max_days = (ag.max_age_value or 0) * 365
                    elif ag.max_age_unit == 'Months': max_days = (ag.max_age_value or 0) * 30
                    elif ag.max_age_unit == 'Weeks': max_days = (ag.max_age_value or 0) * 7
                    elif ag.max_age_unit == 'Days': max_days = (ag.max_age_value or 0)
                    
                    if not (min_days <= patient_age_days <= max_days):
                        continue
                
                # Special case for pregnancy (if the patient has it or if we don't know, we might just match the first we see)
                matched_ref = ref
                break
                
            if not matched_ref:
                # Fallback to general range (age_group=None) if exact match fails
                for ref in ranges:
                    if not ref.age_group and (ref.gender == 'All' or ref.gender == patient_gender):
                        matched_ref = ref
                        break
                
            if matched_ref:
                if matched_ref.reference_text:
                    p.display_ref_range = matched_ref.reference_text
                else:
                    p.display_ref_range = f"{matched_ref.min_value} - {matched_ref.max_value}"
                    if matched_ref.unit:
                        p.display_ref_range += f" {matched_ref.unit}"
            else:
                p.display_ref_range = ''
                
        context['parameters'] = parameters
        return context"""

if target_context in views_content:
    views_content = views_content.replace(target_context, new_context)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views_content)
    print("Updated views.py dynamically")
else:
    print("Could not find target_context in views.py")
