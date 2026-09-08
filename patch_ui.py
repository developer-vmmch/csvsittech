import os
import sys

# 1. Update views.py
views_path = r'c:\Users\Admin\Desktop\erp1\apps\lab\views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    views_content = f.read()

target_context = """    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(PatientInvestigationOrder, id=kwargs.get('pk'))
        context['order'] = order
        context['parameters'] = InvestigationParameter.objects.filter(investigation=order.investigation, is_active=True).select_related('parameter')
        return context"""

new_context = """    def get_context_data(self, **kwargs):
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

if target_context in views_content:
    views_content = views_content.replace(target_context, new_context)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views_content)
    print("Updated views.py")
else:
    print("Could not find target_context in views.py")

# 2. Update result_entry.html
template_path = r'c:\Users\Admin\Desktop\erp1\templates\lab\orders\result_entry.html'
with open(template_path, 'r', encoding='utf-8') as f:
    template_content = f.read()

target_html = """                            <td>
                                {% if p.parameter.data_type == 'NUMERIC' %}"""

new_html = """                            <td>
                                {% if p.display_ref_range %}
                                <div style="color: red; font-size: 0.85rem; font-weight: bold; margin-bottom: 4px;">
                                    Ref: {{ p.display_ref_range }}
                                </div>
                                {% endif %}
                                {% if p.parameter.data_type == 'NUMERIC' %}"""

if target_html in template_content:
    template_content = template_content.replace(target_html, new_html)
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template_content)
    print("Updated result_entry.html")
else:
    print("Could not find target_html in result_entry.html")

