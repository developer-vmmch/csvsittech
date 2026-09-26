from django import forms
from django.db.models import Q
from .models import Patient, PatientCompany, Department, DepartmentUnit, PatientVisit, BranchTransferRequest, Ward

class WardForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="-- Select Mapped Department (Optional) --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_ward_department'})
    )

    class Meta:
        model = Ward
        fields = ['code', 'name', 'department', 'ward_type', 'gender_category', 'total_beds', 'floor_building', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. GW-01 or ICU-01', 'required': 'required'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. General Ward or Medical ICU', 'required': 'required'}),
            'ward_type': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'gender_category': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'total_beds': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'placeholder': 'e.g. 20'}),
            'floor_building': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Main Block - 2nd Floor'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Optional notes or ward features'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            qs = Ward.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ward name already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip()
            qs = Ward.objects.filter(code__iexact=code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ward code already exists.")
        return code


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
        
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            qs = Department.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Department name already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip()
            qs = Department.objects.filter(code__iexact=code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Department code already exists.")
        return code


class DepartmentUnitForm(forms.ModelForm):
    class Meta:
        model = DepartmentUnit
        fields = ['department', 'unit_name', 'code', 'unit_type', 'display_order', 'is_active']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'unit_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. HOD-GENERAL MEDICINE-V', 'required': 'required'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. GM-V', 'required': 'required'}),
            'unit_type': forms.Select(attrs={'class': 'form-select'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip()
            # Case insensitive check
            qs = DepartmentUnit.objects.filter(code__iexact=code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Unit/Doctor Code already exists.")
        return code


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

        # Mode-based dynamic requirements
        reg_mode = (self.data.get('registration_mode') or 'NORMAL').upper() if self.data else 'NORMAL'
        
        self.fields['patient_id'].required = False
        self.fields['age_years'].required = False
        self.fields['age_months'].required = False
        self.fields['age_days'].required = False
        self.fields['title'].required = (reg_mode != 'EMERGENCY')
        self.fields['title'].error_messages = {'required': 'Title is required.'}
        self.fields['name'].required = True
        self.fields['gender'].required = True
        self.fields['guardian_name'].required = (reg_mode != 'EMERGENCY')
        self.fields['guardian_name'].error_messages = {'required': 'Guardian Name is required.'}
        self.fields['street'].required = False
        self.fields['village_area'].required = False
        self.fields['mobile_no'].required = False
        self.fields['aadhar_card'].required = False
        self.fields['abha_id'].required = False

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
            category = str(self.data.get('category') or '').upper()
            dept_id = self.data.get('department_obj')
            is_emer = False
            if category in ['EMERGENCY', 'CASUALTY']:
                is_emer = True
            elif dept_id:
                try:
                    dept = Department.objects.filter(pk=dept_id).first()
                    if dept and any(term in dept.name.upper() for term in ['EMERGENCY', 'CASUALTY']):
                        is_emer = True
                except Exception:
                    pass
            return Patient.generate_next_patient_id(is_emergency=is_emer)
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

    patient_type = forms.ChoiceField(
        required=False,
        initial='O',
        choices=[('O', '+'), ('D', '-')],
        widget=forms.RadioSelect
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'id': 'id_email', 'placeholder': 'Email address'})
    )
    passport_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'id_passport_number', 'placeholder': 'Passport number'})
    )
    identification_mark = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'id_identification_mark', 'placeholder': 'Identification mark'})
    )
    employee_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'id_employee_id', 'placeholder': 'Employee ID'})
    )
    purpose = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'id_purpose', 'placeholder': 'Purpose of registration'})
    )
    emergency_medicine_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select Emergency Medicine Type'),
            ('Trauma / Accident', 'Trauma / Accident'),
            ('Acute Medical Emergency', 'Acute Medical Emergency'),
            ('Cardiac / Resuscitation', 'Cardiac / Resuscitation'),
            ('Poisoning / Toxicity', 'Poisoning / Toxicity'),
            ('Burns / Inhalation', 'Burns / Inhalation'),
            ('Pediatric Emergency', 'Pediatric Emergency'),
            ('General Casualty', 'General Casualty')
        ],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_emergency_medicine_type'})
    )

    def clean_mobile_no(self):
        mobile = (self.cleaned_data.get('mobile_no') or '').strip()
        if not mobile:
            return ""
        reg_mode = (self.data.get('registration_mode') or 'NORMAL').upper()
        if reg_mode == 'NRI':
            return mobile
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

        reg_mode = (self.data.get('registration_mode') or 'NORMAL').upper()
        if reg_mode == 'NRI':
            passport = (cleaned_data.get('passport_number') or self.data.get('passport_number') or '').strip()
            if not passport:
                self.add_error('passport_number', "Passport number is mandatory for NRI registration.")
            purpose = (cleaned_data.get('purpose') or self.data.get('purpose') or '').strip()
            if not purpose:
                self.add_error('purpose', "Purpose is mandatory for NRI registration.")

        if self.instance and self.instance.pk and self.instance.is_admitted_inpatient:
            raise forms.ValidationError("The patient is already admitted as an inpatient.")

        return cleaned_data

    class Meta:
        model = Patient
        fields = [
            'ipno', 'patient_id', 'centre', 'title', 'name', 'gender', 'dob', 'age_years', 'age_months', 'age_days',
            'aadhar_card', 'visit_through', 'category', 'marital_status', 'religion',
            'guardian_relationship', 'guardian_name', 'patient_company', 'abha_id', 'ofc_code',
            'street', 'village_area', 'country', 'state', 'city', 'pincode',
            'mobile_no', 'email', 'blood_group', 'patient_type', 'complaint', 'occupation', 'income',
            'department_obj', 'unit_obj', 'pan_no'
        ]
        widgets = {
            'patient_id': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'ipno': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'IPNO'}),
            'centre': forms.Select(attrs={'class': 'form-select', 'id': 'id_centre'}),
            'title': forms.Select(choices=[
                ('-', '-'), ('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Miss', 'Miss'), ('Master', 'Master'), ('Dr', 'Dr'), ('Baby', 'Baby')
            ], attrs={'class': 'form-select', 'id': 'id_title', 'required': 'required'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_name', 'placeholder': 'Patient Full Name', 'required': 'required'}),
            'gender': forms.Select(choices=[
                ('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')
            ], attrs={'class': 'form-select', 'id': 'id_gender', 'required': 'required'}),
            'dob': forms.DateInput(attrs={'class': 'form-input', 'type': 'date', 'id': 'id_dob'}),
            'age_years': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_years', 'placeholder': 'Y', 'min': '0'}),
            'age_months': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_months', 'placeholder': 'M', 'min': '0'}),
            'age_days': forms.NumberInput(attrs={'class': 'form-input small-input', 'id': 'id_age_days', 'placeholder': 'D', 'min': '0'}),
            'aadhar_card': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_aadhar_card', 'placeholder': '12-digit Aadhar number', 'maxlength': '12'}),
            'visit_through': forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_through'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'patient_company': forms.Select(attrs={'class': 'form-select', 'id': 'id_patient_company'}),
            'marital_status': forms.Select(choices=[
                ('', 'Select'), ('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed')
            ], attrs={'class': 'form-select', 'id': 'id_marital_status'}),
            'religion': forms.Select(choices=[
                ('', 'Select'), ('Hindu', 'Hindu'), ('Christian', 'Christian'), ('Muslim', 'Muslim'), ('Sikh', 'Sikh'), ('Other', 'Other')
            ], attrs={'class': 'form-select', 'id': 'id_religion'}),
            'guardian_relationship': forms.Select(choices=[
                ('-', '-'),
                ('S/O', 'S/O (Son of)'),
                ('D/O', 'D/O (Daughter of)'),
                ('W/O', 'W/O (Wife of)'),
                ('C/O', 'C/O (Care of)'),
                ('H/O', 'H/O (Husband of)'),
                ('F/O', 'F/O (Father of)'),
                ('M/O', 'M/O (Mother of)'),
            ], attrs={'class': 'form-select', 'id': 'id_guardian_rel'}),
            'guardian_name': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_guardian_name', 'placeholder': 'Guardian Name'}),
            'abha_id': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_abha_id', 'placeholder': 'ABHA Number / ID', 'maxlength': '50'}),
            'ofc_code': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_ofc_code', 'placeholder': 'OFC Code'}),
            'street': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_street', 'placeholder': 'Street / Address'}),
            'village_area': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_village_area', 'placeholder': 'Village / Area'}),
            'country': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_country'}),
            'state': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_state'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_city', 'required': 'required'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_pincode', 'placeholder': 'Pincode'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_mobile_no', 'placeholder': '10-digit mobile number'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'id': 'id_email', 'placeholder': 'Email address'}),
            'blood_group': forms.Select(choices=[
                ('', 'Select'), ('A', 'A'), ('B', 'B'), ('AB', 'AB'), ('O', 'O')
            ], attrs={'class': 'form-select', 'id': 'id_blood_group'}),
            'complaint': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_complaint', 'placeholder': 'Primary complaint'}),
            'occupation': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_occupation', 'placeholder': 'Occupation'}),
            'income': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_income', 'placeholder': 'Annual / Monthly Income'}),
            'department_obj': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'unit_obj': forms.Select(attrs={'class': 'form-select', 'id': 'id_unit'}),
            'pan_no': forms.TextInput(attrs={'class': 'form-input', 'id': 'id_pan_no', 'placeholder': 'PAN Number'}),
        }


WARD_CHOICES = [
    ('', 'Select Ward'),
    ('General Ward', 'General Ward'),
    ('Male Medical Ward', 'Male Medical Ward'),
    ('Female Medical Ward', 'Female Medical Ward'),
    ('Male Surgical Ward', 'Male Surgical Ward'),
    ('Female Surgical Ward', 'Female Surgical Ward'),
    ('Casualty / Emergency Ward', 'Casualty / Emergency Ward'),
    ('ICU (Intensive Care Unit)', 'ICU (Intensive Care Unit)'),
    ('ICCU (Intensive Cardiac Care Unit)', 'ICCU (Intensive Cardiac Care Unit)'),
    ('NICU (Neonatal ICU)', 'NICU (Neonatal ICU)'),
    ('PICU (Pediatric ICU)', 'PICU (Pediatric ICU)'),
    ('Maternity / OG Ward', 'Maternity / OG Ward'),
    ('Paediatric Ward', 'Paediatric Ward'),
    ('Orthopedic Ward', 'Orthopedic Ward'),
    ('ENT Ward', 'ENT Ward'),
    ('Ophthalmology Ward', 'Ophthalmology Ward'),
    ('Post-Operative Ward', 'Post-Operative Ward'),
    ('Special Ward (Single AC)', 'Special Ward (Single AC)'),
    ('Special Ward (Non-AC)', 'Special Ward (Non-AC)'),
    ('Semi-Special / Twin Sharing', 'Semi-Special / Twin Sharing'),
    ('Isolation Ward', 'Isolation Ward'),
    ('Day Care Ward', 'Day Care Ward'),
]


class PatientVisitForm(forms.ModelForm):
    department_obj = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=True,
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_department'})
    )
    unit_obj = forms.ModelChoiceField(
        queryset=DepartmentUnit.objects.filter(is_active=True),
        required=True,
        empty_label="Select Unit / Doctor",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_unit'})
    )
    ward = forms.ChoiceField(
        choices=WARD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_ward'})
    )

    class Meta:
        model = PatientVisit
        fields = [
            'department_obj', 'unit_obj', 'visit_type', 'centre', 'category',
            'ipno', 'ward', 'bed', 'ref_no', 'ref_by', 'reg_fees', 'coll_status', 'clinical_notes'
        ]
        widgets = {
            'visit_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_type'}),
            'centre': forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_centre'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_visit_category'}),
            'ipno': forms.HiddenInput(attrs={'id': 'id_ipno'}),
            'ward': forms.Select(choices=WARD_CHOICES, attrs={'class': 'form-select', 'id': 'id_visit_ward'}),
            'bed': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bed'}),
            'ref_no': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ref No'}),
            'ref_by': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Referred By'}),
            'reg_fees': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0.00'}),
            'coll_status': forms.Select(choices=[('Paid', 'Paid'), ('Pending', 'Pending'), ('Waived', 'Waived')], attrs={'class': 'form-select'}),
            'clinical_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Enter consultation diagnosis / medical notes...'}),
        }

    def __init__(self, *args, patient=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        Department.seed_defaults()
        self.patient = patient
        
        is_emergency = False
        if patient:
            is_emergency = (
                str(patient.patient_id or '').upper().startswith('E') or 
                patient.category in ['EMERGENCY', 'CASUALTY'] or
                (patient.department_obj and any(k in patient.department_obj.name.upper() for k in ['EMERGENCY', 'CASUALTY'])) or
                (patient.department and any(k in str(patient.department).upper() for k in ['EMERGENCY', 'CASUALTY']))
            )
            
        if is_emergency:
            emer_depts = Department.objects.filter(is_active=True).filter(
                Q(name__icontains='EMERGENCY') | Q(name__icontains='CASUALTY') | Q(code__icontains='EMR')
            )
            if not emer_depts.exists():
                emer_depts = Department.objects.filter(is_active=True)
                
            self.fields['department_obj'].queryset = emer_depts
            self.fields['department_obj'].empty_label = None
            if emer_depts.exists():
                self.fields['department_obj'].initial = emer_depts.first()
                self.fields['unit_obj'].queryset = DepartmentUnit.objects.filter(department__in=emer_depts, is_active=True)
                if self.fields['unit_obj'].queryset.exists():
                    self.fields['unit_obj'].initial = self.fields['unit_obj'].queryset.first()
            
            # Restrict Visit Type to IP only
            self.fields['visit_type'].choices = [('IP', 'In-Patient (IP)')]
            self.fields['visit_type'].initial = 'IP'
            self.fields['category'].choices = [('EMERGENCY', 'Emergency'), ('CASUALTY', 'Casualty')]
            self.fields['category'].initial = 'EMERGENCY'
            self.fields['ward'].initial = 'Casualty / Emergency Ward'
        else:
            self.fields['department_obj'].queryset = Department.objects.filter(is_active=True)
            self.fields['unit_obj'].queryset = DepartmentUnit.objects.filter(is_active=True)

        Ward.seed_defaults()
        ward_qs = Ward.objects.filter(is_active=True)

        if patient:
            gender_raw = str(patient.gender or '').strip().upper()
            title_raw = str(patient.title or '').strip().upper()
            age_years = patient.age_years if patient.age_years is not None else 0

            is_paediatric = (0 < age_years < 13) or title_raw in ['BABY', 'MASTER'] or str(patient.category or '').upper() == 'PAEDIATRIC'
            is_male = (gender_raw in ['MALE', 'M']) or (title_raw in ['MR', 'MASTER'] and not is_paediatric)
            is_female = (gender_raw in ['FEMALE', 'F']) or (title_raw in ['MRS', 'MS', 'MISS'])

            if is_paediatric:
                ward_qs = ward_qs.filter(gender_category__in=[Ward.GenderCategoryChoices.PAEDIATRIC, Ward.GenderCategoryChoices.UNISEX])
            elif is_male:
                ward_qs = ward_qs.filter(gender_category__in=[Ward.GenderCategoryChoices.MALE, Ward.GenderCategoryChoices.UNISEX])
            elif is_female:
                ward_qs = ward_qs.filter(gender_category__in=[Ward.GenderCategoryChoices.FEMALE, Ward.GenderCategoryChoices.UNISEX])

        active_wards = ward_qs.order_by('name').values_list('name', 'name')
        if active_wards.exists():
            self.fields['ward'].choices = [('', 'Select Ward')] + list(active_wards)
        else:
            self.fields['ward'].choices = [('', 'Select Ward')]

        self.fields['ipno'].required = False
        self.fields['ward'].required = False
        self.fields['centre'].required = False
        self.fields['reg_fees'].required = False
        self.fields['coll_status'].required = False
        self.fields['category'].required = False

    def clean_ward(self):
        ward_name = (self.cleaned_data.get('ward') or '').strip()
        if not ward_name:
            return ward_name

        if self.patient:
            gender_raw = str(self.patient.gender or '').strip().upper()
            title_raw = str(self.patient.title or '').strip().upper()
            age_years = self.patient.age_years if self.patient.age_years is not None else 0

            is_paediatric = (0 < age_years < 13) or title_raw in ['BABY', 'MASTER'] or str(self.patient.category or '').upper() == 'PAEDIATRIC'
            is_male = (gender_raw in ['MALE', 'M']) or (title_raw in ['MR', 'MASTER'] and not is_paediatric)
            is_female = (gender_raw in ['FEMALE', 'F']) or (title_raw in ['MRS', 'MS', 'MISS'])

            ward_obj = Ward.objects.filter(name__iexact=ward_name, is_active=True).first()
            if ward_obj:
                if is_male and ward_obj.gender_category == Ward.GenderCategoryChoices.FEMALE:
                    raise forms.ValidationError(f"Cannot assign Female ward '{ward_name}' to a Male patient.")
                elif is_female and ward_obj.gender_category == Ward.GenderCategoryChoices.MALE:
                    raise forms.ValidationError(f"Cannot assign Male ward '{ward_name}' to a Female patient.")
                elif not is_paediatric and ward_obj.gender_category == Ward.GenderCategoryChoices.PAEDIATRIC:
                    raise forms.ValidationError(f"Cannot assign Paediatric ward '{ward_name}' to an Adult patient.")

        return ward_name

    def clean_ipno(self):
        ip = (self.cleaned_data.get('ipno') or '').strip()
        if 'AUTO' in ip.upper():
            return ''
        return ip

    def clean_reg_fees(self):
        fees = self.cleaned_data.get('reg_fees')
        return fees if fees is not None else 0.00

    def clean_coll_status(self):
        status = self.cleaned_data.get('coll_status')
        return status if status else 'Paid'

    def clean_centre(self):
        centre = self.cleaned_data.get('centre')
        return centre if centre else 'VMMCH'

    def clean(self):
        cleaned_data = super().clean()
        if self.patient and self.patient.is_admitted_inpatient:
            raise forms.ValidationError("The patient is already admitted as an inpatient.")
        return cleaned_data


class BranchTransferRequestForm(forms.ModelForm):
    patient_id_input = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Patient ID / UHID or IP No...',
            'id': 'id_patient_search_input'
        })
    )

    class Meta:
        model = BranchTransferRequest
        fields = ['to_department', 'to_unit', 'transfer_reason']
        widgets = {
            'to_department': forms.Select(attrs={'class': 'form-select', 'id': 'id_to_department', 'required': 'required'}),
            'to_unit': forms.Select(attrs={'class': 'form-select', 'id': 'id_to_unit'}),
            'transfer_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain detailed clinical reason for transfer (e.g. specialized evaluation, treatment required, ICU management)...',
                'required': 'required'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.patient_instance = kwargs.pop('patient', None)
        self.active_admission = kwargs.pop('admission', None)
        self.requested_by = kwargs.pop('requested_by', None)
        super().__init__(*args, **kwargs)

        Department.seed_defaults()
        self.fields['to_department'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['to_unit'].queryset = DepartmentUnit.objects.filter(is_active=True).order_by('unit_name')
        self.fields['to_unit'].required = False

    def clean(self):
        cleaned_data = super().clean()
        patient_id_str = (cleaned_data.get('patient_id_input') or '').strip()
        to_dept = cleaned_data.get('to_department')
        transfer_reason = (cleaned_data.get('transfer_reason') or '').strip()

        # 1. Resolve Patient
        patient = self.patient_instance
        if not patient and patient_id_str:
            patient = Patient.objects.filter(
                Q(patient_id__iexact=patient_id_str) | Q(visits__ipno__iexact=patient_id_str)
            ).distinct().first()

        if not patient:
            raise forms.ValidationError("Selected patient does not exist in the hospital database.")

        self.patient_instance = patient

        # 2. Rule 2: Patient must have an active admission
        admission = self.active_admission or patient.active_ip_admission
        if not admission or not patient.is_admitted_inpatient:
            raise forms.ValidationError("Patient does not have an active admission. Branch transfer cannot be requested.")

        self.active_admission = admission

        # 3. Rule 3: Source Department
        from_dept = admission.department_obj
        if not from_dept and patient.department_obj:
            from_dept = patient.department_obj

        if not from_dept:
            from_dept = Department.objects.filter(name__iexact=admission.department).first()

        if not from_dept:
            from_dept = Department.objects.filter(is_active=True).first()

        self.from_department_instance = from_dept

        # 4. Rule 4: Destination Department must be different from source department
        if to_dept and from_dept and to_dept.id == from_dept.id:
            raise forms.ValidationError(
                f"Destination department cannot be the same as the current department ({from_dept.name})."
            )

        # 5. Rule 5: Prevent duplicate pending requests
        has_pending = BranchTransferRequest.objects.filter(
            patient=patient,
            status=BranchTransferRequest.StatusChoices.PENDING
        ).exists()

        if has_pending:
            raise forms.ValidationError("This patient already has a pending branch transfer request.")

        # 6. Validate Reason
        if not transfer_reason:
            raise forms.ValidationError("Transfer reason / clinical notes are mandatory.")

        return cleaned_data

