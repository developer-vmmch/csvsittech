from django import forms
from .models import Patient, PatientCompany, Department, DepartmentUnit

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['code', 'name', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. GENMED or CARD', 'required': 'required'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Department Name (e.g. GENERAL MEDICINE)', 'required': 'required'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Department description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class DepartmentUnitForm(forms.ModelForm):
    class Meta:
        model = DepartmentUnit
        fields = ['department', 'unit_name', 'head_doctor', 'is_active']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'unit_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. HOD-GENERAL MEDICINE-V or UNIT-I DR. KUMAR', 'required': 'required'}),
            'head_doctor': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Head Doctor Name'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class PatientCompanyForm(forms.ModelForm):
    class Meta:
        model = PatientCompany
        fields = ['code', 'name', 'category', 'contact_person', 'phone_number', 'email', 'discount_percentage', 'address', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. CMP-001 or CGHS-01', 'required': 'required'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Company / Scheme Name', 'required': 'required'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Contact Person Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phone Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'company@domain.com'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0.00'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Company Address'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class PatientRegistrationForm(forms.ModelForm):
    patient_company = forms.ModelChoiceField(
        queryset=PatientCompany.objects.none(),
        required=False,
        empty_label="Select Company / Scheme",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_patient_company'})
    )
    department_obj = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=True,
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_department_select', 'required': 'required'}),
        error_messages={'required': 'Department is required.'}
    )
    unit_obj = forms.ModelChoiceField(
        queryset=DepartmentUnit.objects.none(),
        required=True,
        empty_label="Select Unit / Doctor",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_unit_select', 'required': 'required'}),
        error_messages={'required': 'Unit / Doctor is required.'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure default companies & departments exist
        PatientCompany.seed_defaults()
        Department.seed_defaults()

        self.fields['patient_company'].queryset = PatientCompany.objects.filter(is_active=True)
        self.fields['department_obj'].queryset = Department.objects.filter(is_active=True)

        # Enforce required validation on mandatory fields requested by user
        self.fields['patient_id'].required = False
        self.fields['age_years'].required = False
        self.fields['age_months'].required = False
        self.fields['age_days'].required = False
        self.fields['title'].required = True
        self.fields['name'].required = True
        self.fields['gender'].required = True
        self.fields['guardian_name'].required = True
        self.fields['street'].required = True
        self.fields['village_area'].required = True
        self.fields['mobile_no'].required = True

        # Dynamic queryset for unit_obj based on selected department
        if 'department_obj' in self.data:
            try:
                dept_id = int(self.data.get('department_obj'))
                self.fields['unit_obj'].queryset = DepartmentUnit.objects.filter(department_id=dept_id, is_active=True)
            except (ValueError, TypeError):
                self.fields['unit_obj'].queryset = DepartmentUnit.objects.filter(is_active=True)
        elif self.instance.pk and self.instance.department_obj:
            self.fields['unit_obj'].queryset = self.instance.department_obj.units.filter(is_active=True)
        else:
            self.fields['unit_obj'].queryset = DepartmentUnit.objects.filter(is_active=True)

    def clean_patient_id(self):
        patient_id = self.cleaned_data.get('patient_id')
        if not patient_id and not self.instance.pk:
            return Patient.generate_next_patient_id()
        return patient_id

    def clean_age_years(self):
        val = self.cleaned_data.get('age_years')
        return val if val is not None else 0

    def clean_age_months(self):
        val = self.cleaned_data.get('age_months')
        return val if val is not None else 0

    def clean_age_days(self):
        val = self.cleaned_data.get('age_days')
        return val if val is not None else 0

    def clean_mobile_no(self):
        mobile = (self.cleaned_data.get('mobile_no') or '').strip()
        if not mobile:
            raise forms.ValidationError("Mobile number is required.")
        if not mobile.isdigit() or len(mobile) != 10:
            raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        return mobile

    def clean_aadhar_card(self):
        aadhar = (self.cleaned_data.get('aadhar_card') or '').strip()
        if not aadhar:
            return ""
        if not aadhar.isdigit() or len(aadhar) != 12:
            raise forms.ValidationError("Aadhar card number must be exactly 12 digits.")
        return aadhar

    def clean(self):
        cleaned_data = super().clean()
        years = cleaned_data.get('age_years') or 0
        months = cleaned_data.get('age_months') or 0
        days = cleaned_data.get('age_days') or 0

        if years == 0 and months == 0 and days == 0:
            self.add_error('age_years', "Patient age must be selected.")
        return cleaned_data

    class Meta:
        model = Patient
        fields = [
            'ipno', 'patient_id', 'title', 'name', 'gender', 'dob', 'age_years', 'age_months', 'age_days',
            'aadhar_card', 'visit_through', 'category', 'marital_status', 'religion',
            'guardian_relationship', 'guardian_name', 'patient_company', 'abha_id', 'ofc_code',
            'street', 'village_area', 'country', 'state', 'city', 'pincode',
            'mobile_no', 'blood_group', 'complaint', 'occupation', 'income',
            'department_obj', 'unit_obj', 'pan_no'
        ]
        widgets = {
            'patient_id': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'ipno': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'IPNO'}),
            'title': forms.Select(choices=[
                ('-', '-'), ('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Miss', 'Miss'), ('Master', 'Master'), ('Dr', 'Dr'), ('Baby', 'Baby')
            ], attrs={'class': 'form-select', 'id': 'id_title', 'required': 'required'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_name', 'placeholder': 'Patient Full Name', 'required': 'required'}),
            'gender': forms.Select(attrs={'class': 'form-select', 'id': 'id_gender', 'required': 'required'}),
            'dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'age_years': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_years', 'placeholder': 'Y', 'min': '0'}),
            'age_months': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_months', 'placeholder': 'M', 'min': '0'}),
            'age_days': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_days', 'placeholder': 'D', 'min': '0'}),
            'aadhar_card': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_aadhar_card', 'placeholder': 'Aadhar Number (12 digits)', 'maxlength': '12'}),
            'visit_through': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'marital_status': forms.Select(choices=[
                ('', 'Select'), ('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')
            ], attrs={'class': 'form-select'}),
            'religion': forms.Select(choices=[
                ('', 'Select'), ('Hindu', 'Hindu'), ('Christian', 'Christian'), ('Muslim', 'Muslim'), ('Sikh', 'Sikh'), ('Other', 'Other')
            ], attrs={'class': 'form-select'}),
            'guardian_relationship': forms.Select(attrs={'class': 'form-select', 'id': 'id_guardian_rel'}),
            'guardian_name': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_guardian_name', 'placeholder': 'Guardian Name', 'required': 'required'}),
            'abha_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ABHA ID'}),
            'ofc_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'OFC Code'}),
            'street': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_street', 'placeholder': 'Street / Address', 'required': 'required'}),
            'village_area': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_village_area', 'placeholder': 'Village / Area', 'required': 'required'}),
            'country': forms.Select(choices=[('India', 'India'), ('Other', 'Other')], attrs={'class': 'form-select'}),
            'state': forms.Select(choices=[
                ('Puducherry', 'Puducherry'), ('Tamil Nadu', 'Tamil Nadu'), ('Kerala', 'Kerala'), ('Delhi', 'Delhi')
            ], attrs={'class': 'form-select'}),
            'city': forms.Select(choices=[
                ('Karaikal', 'Karaikal'), ('Puducherry', 'Puducherry'), ('Chennai', 'Chennai')
            ], attrs={'class': 'form-select'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Pincode'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_mobile_no', 'placeholder': 'Mobile Number (10 digits)', 'maxlength': '10', 'required': 'required'}),
            'blood_group': forms.Select(choices=[
                ('', 'Select'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
            ], attrs={'class': 'form-select'}),
            'complaint': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Complaint / Symptoms'}),
            'occupation': forms.Select(choices=[('', 'Select'), ('Private', 'Private Job'), ('Govt', 'Govt Employee'), ('Business', 'Business'), ('Student', 'Student')], attrs={'class': 'form-select'}),
            'income': forms.Select(choices=[('', 'Select'), ('< 1L', '< 1 Lakh'), ('1L-5L', '1-5 Lakhs'), ('> 5L', '> 5 Lakhs')], attrs={'class': 'form-select'}),
            'pan_no': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'PAN Card Number'}),
        }
