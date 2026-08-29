import re

with open('apps/lab/views.py', 'r') as f:
    content = f.read()

replacement = """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wo = self.object
        patient = wo.service_request.patient
        
        # Calculate patient age in days
        patient_age_days = (patient.age_years * 365) + (patient.age_months * 30) + patient.age_days
        
        from apps.lab.models import InvestigationParameter, ParameterReferenceRange, AgeGroup
        
        parameters = InvestigationParameter.objects.filter(
            investigation=wo.investigation,
            is_active=True
        ).select_related('parameter').order_by('display_order')
        
        age_groups = AgeGroup.objects.filter(is_active=True).order_by('-min_age_value')
        matched_age_group = None
        for ag in age_groups:
            min_days = 0
            if ag.min_age_unit == 'Years': min_days = (ag.min_age_value or 0) * 365
            elif ag.min_age_unit == 'Months': min_days = (ag.min_age_value or 0) * 30
            else: min_days = ag.min_age_value or 0
            
            max_days = float('inf')
            if ag.max_age_value is not None:
                if ag.max_age_unit == 'Years': max_days = ag.max_age_value * 365
                elif ag.max_age_unit == 'Months': max_days = ag.max_age_value * 30
                else: max_days = ag.max_age_value
            
            if min_days <= patient_age_days <= max_days:
                if ag.gender == 'All' or ag.gender == patient.gender:
                    matched_age_group = ag
                    break
                    
        if not matched_age_group:
            matched_age_group = AgeGroup.objects.filter(label__icontains='Adult').first()
            
        param_data = []
        for ip in parameters:
            ref_range = None
            if matched_age_group:
                ref_range = ParameterReferenceRange.objects.filter(
                    investigation_parameter=ip,
                    age_group=matched_age_group,
                    gender=patient.gender
                ).first()
                if not ref_range:
                    ref_range = ParameterReferenceRange.objects.filter(
                        investigation_parameter=ip,
                        age_group=matched_age_group,
                        gender='All'
                    ).first()
            
            unit = "-"
            if ref_range and ref_range.unit: unit = ref_range.unit
            elif ip.unit: unit = ip.unit
            elif ip.parameter and ip.parameter.default_unit: unit = ip.parameter.default_unit
            
            ref_text = "-"
            if ref_range and ref_range.reference_text: ref_text = ref_range.reference_text
            elif ip.reference_range: ref_text = ip.reference_range
            
            param_data.append({
                'ip': ip,
                'parameter': ip.parameter,
                'ref_range': ref_range,
                'unit': unit,
                'reference_text': ref_text,
                'min_value': ref_range.min_value if ref_range else None,
                'max_value': ref_range.max_value if ref_range else None,
                'method': 'Colorimetric' if 'HGB' in str(ip.code) else ('Laser Flow' if 'WBC' in str(ip.code) else 'Calculated')
            })
            
        diagnosis_texts = []
        for d in wo.service_request.diagnoses.all():
            if d.diagnosis: diagnosis_texts.append(d.diagnosis.name)
            elif d.chief_complaint: diagnosis_texts.append(d.chief_complaint.name)
            
        context['diagnosis_text'] = ", ".join(diagnosis_texts) if diagnosis_texts else "Not Added"
        context['parameters'] = parameters
        context['param_data'] = param_data
        context['matched_age_group'] = matched_age_group
        return context
"""

new_content = re.sub(
    r"    def get_context_data\(self, \*\*kwargs\):.*?return context",
    replacement,
    content,
    flags=re.DOTALL
)

with open('apps/lab/views.py', 'w') as f:
    f.write(new_content)
