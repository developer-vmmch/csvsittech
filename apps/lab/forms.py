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
            'name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'code': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'icd11_title': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'chapter': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'synonyms': forms.Textarea(attrs={'class': 'lab-form-textarea form-control', 'rows': 3}),
            'source': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'icd_version': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'who_uri': forms.URLInput(attrs={'class': 'lab-form-input form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class LabDiagnosisForm(forms.ModelForm):
    class Meta:
        model = LabDiagnosis
        fields = ['name', 'code', 'icd11_title', 'chapter', 'synonyms', 'source', 'icd_version', 'who_uri', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'code': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'icd11_title': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'chapter': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'synonyms': forms.Textarea(attrs={'class': 'lab-form-textarea form-control', 'rows': 3}),
            'source': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'icd_version': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'who_uri': forms.URLInput(attrs={'class': 'lab-form-input form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class InvestigationForm(forms.ModelForm):
    class Meta:
        model = Investigation
        fields = ['code', 'name', 'short_name', 'department', 'sample_type', 'is_panel', 'turnaround_time_hours', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'short_name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'department': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'sample_type': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'is_panel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'turnaround_time_hours': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
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
            'investigation': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'code': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'short_name': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'result_type': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'unit': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'decimal_precision': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'reference_range': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'critical_low': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'critical_high': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'male_reference_range': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'female_reference_range': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'child_reference_range': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'minimum_age': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'maximum_age': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AgeGroupForm(forms.ModelForm):
    class Meta:
        model = AgeGroup
        fields = ['code', 'label', 'min_age_value', 'min_age_unit', 'max_age_value', 'max_age_unit', 'gender', 'pregnancy_applicable', 'sort_order', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'label': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'min_age_value': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'min_age_unit': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'max_age_value': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'max_age_unit': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'gender': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'pregnancy_applicable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class InvestigationParameterForm(forms.ModelForm):
    class Meta:
        model = InvestigationParameter
        fields = ['investigation', 'parameter', 'unit', 'display_order', 'is_active']
        widgets = {
            'investigation': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'parameter': forms.Select(attrs={'class': 'lab-form-select form-select'}),
            'unit': forms.TextInput(attrs={'class': 'lab-form-input form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'lab-form-input form-control'}),
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
