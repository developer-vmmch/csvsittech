from django import forms
from .models import (
    Diagnosis, Investigation, Parameter, AgeGroup,
    InvestigationParameter,
    ParameterReferenceRange, PatientInvestigationOrder, PatientInvestigationResult,
    ServiceRequest, LabDiagnosis
)

class DiagnosisForm(forms.ModelForm):
    class Meta:
        model = Diagnosis
        fields = ['name', 'code', 'icd11_title', 'chapter', 'synonyms', 'source', 'icd_version', 'who_uri', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'icd11_title': forms.TextInput(attrs={'class': 'form-control'}),
            'chapter': forms.TextInput(attrs={'class': 'form-control'}),
            'synonyms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'icd_version': forms.TextInput(attrs={'class': 'form-control'}),
            'who_uri': forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class LabDiagnosisForm(forms.ModelForm):
    class Meta:
        model = LabDiagnosis
        fields = ['name', 'code', 'icd11_title', 'chapter', 'synonyms', 'source', 'icd_version', 'who_uri', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'icd11_title': forms.TextInput(attrs={'class': 'form-control'}),
            'chapter': forms.TextInput(attrs={'class': 'form-control'}),
            'synonyms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'icd_version': forms.TextInput(attrs={'class': 'form-control'}),
            'who_uri': forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class InvestigationForm(forms.ModelForm):
    class Meta:
        model = Investigation
        fields = ['code', 'name', 'short_name', 'department', 'sample_type', 'is_panel', 'turnaround_time_hours', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'sample_type': forms.Select(attrs={'class': 'form-select'}),
            'is_panel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'turnaround_time_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ParameterForm(forms.ModelForm):
    class Meta:
        model = InvestigationParameter
        fields = [
            'investigation', 'code', 'name', 'short_name', 'result_type', 'unit', 
            'decimal_precision', 'reference_range', 'critical_low', 'critical_high',
            'male_reference_range', 'female_reference_range', 'child_reference_range',
            'minimum_age', 'maximum_age', 'display_order', 'is_active'
        ]
        widgets = {
            'investigation': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control'}),
            'result_type': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'decimal_precision': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference_range': forms.TextInput(attrs={'class': 'form-control'}),
            'critical_low': forms.TextInput(attrs={'class': 'form-control'}),
            'critical_high': forms.TextInput(attrs={'class': 'form-control'}),
            'male_reference_range': forms.TextInput(attrs={'class': 'form-control'}),
            'female_reference_range': forms.TextInput(attrs={'class': 'form-control'}),
            'child_reference_range': forms.TextInput(attrs={'class': 'form-control'}),
            'minimum_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximum_age': forms.NumberInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AgeGroupForm(forms.ModelForm):
    class Meta:
        model = AgeGroup
        fields = ['code', 'label', 'min_age_value', 'min_age_unit', 'max_age_value', 'max_age_unit', 'gender', 'pregnancy_applicable', 'sort_order', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'min_age_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_age_unit': forms.Select(attrs={'class': 'form-select'}),
            'max_age_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_age_unit': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'pregnancy_applicable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Ensure max age is strictly greater than min age in logical value if units are the same
        # Complex validation across units (e.g. 1 month > 30 days) is better done on save or explicitly
        return cleaned_data


class InvestigationParameterForm(forms.ModelForm):
    class Meta:
        model = InvestigationParameter
        fields = ['investigation', 'parameter', 'unit', 'display_order', 'is_active']
        widgets = {
            'investigation': forms.Select(attrs={'class': 'form-select'}),
            'parameter': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['patient', 'consultant', 'department', 'visit_type', 'request_date']
        widgets = {
            'patient': forms.HiddenInput(),
            'consultant': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'visit_type': forms.Select(attrs={'class': 'form-select'}),
            'request_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'onclick': 'if(this.showPicker) this.showPicker();'}),
        }
