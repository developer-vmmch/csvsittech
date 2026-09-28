from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomRole

User = get_user_model()

def get_all_role_choices():
    choices = list(User.Roles.choices)
    try:
        custom_roles = CustomRole.objects.all()
        for cr in custom_roles:
            if (cr.code, cr.name) not in choices:
                choices.append((cr.code, cr.name))
    except Exception:
        pass
    return choices


ERP_MODULE_LIST = [
    'Front Office', 'Consultant', 'Billing', 'Lab', 'Ward', 'MRD',
    'Pharmacy', 'Inventory', 'Blood Bank', 'Radiology', 'OT',
    'Summary', 'Accounts', 'Report', 'MIS', 'Department'
]

def get_erp_department_choices():
    choices = [('All Departments', 'All Departments (Universal Access)')]
    for d in ERP_MODULE_LIST:
        choices.append((d, d))
    return choices

def get_clinical_department_choices():
    choices = []
    try:
        from apps.patients.models import Department
        Department.seed_defaults()
        for dept in Department.objects.filter(is_active=True).order_by('name'):
            choices.append((dept.name, dept.name))
    except Exception:
        pass
    return choices

def get_all_department_choices(include_empty=False):
    choices = []
    if include_empty:
        choices.append(('', '-- Select Department --'))
    choices.append(('All Departments', 'All Departments (Universal Access)'))
    for d in ERP_MODULE_LIST:
        choices.append((d, f"{d} (ERP Module)"))
    for d, label in get_clinical_department_choices():
        if (d, label) not in choices:
            choices.append((d, label))
    return choices


class FlexibleMultipleChoiceField(forms.MultipleChoiceField):
    """MultipleChoiceField that does not fail if a valid department is selected."""
    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        return

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username',
            'autofocus': True,
            'required': 'required'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'required': 'required',
            'id': 'id_login_password'
        })
    )


class UserCreationCustomForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter Password', 'required': 'required'}),
        label="Password *"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm Password', 'required': 'required'}),
        label="Confirm Password *"
    )
    erp_departments = FlexibleMultipleChoiceField(
        choices=(),
        required=False,
        label="ERP Module / Portal Access",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select-multi-erp',
            'id': 'id_erp_departments',
        })
    )
    clinical_departments = FlexibleMultipleChoiceField(
        choices=(),
        required=False,
        label="Hospital / Clinical Department(s)",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select-multi-clinical',
            'id': 'id_clinical_departments',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_all_role_choices()
        self.fields['role'].choices = choices
        self.fields['role'].widget.choices = choices

        self.fields['erp_departments'].choices = get_erp_department_choices()
        self.fields['clinical_departments'].choices = get_clinical_department_choices()

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role',
            'phone_number', 'employee_id', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. EDWIN or DR_KUMAR', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'user@vmmc.edu.in'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mobile / Contact Number', 'maxlength': '10'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly', 'style': 'background-color: #f1f5f9; color: #475569; font-weight: 600;'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists. Please choose a different username.")
        return username

    def clean_employee_id(self):
        employee_id = (self.cleaned_data.get('employee_id') or '').strip()
        if not employee_id:
            return User.generate_next_employee_id()
        if User.objects.filter(employee_id__iexact=employee_id).exists():
            raise forms.ValidationError("A user with this Employee ID already exists.")
        return employee_id

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        erp_depts = cleaned_data.get('erp_departments') or []
        clin_depts = cleaned_data.get('clinical_departments') or []

        all_selected = []
        if 'All Departments' in erp_depts:
            all_selected.append('All Departments')
        else:
            for d in erp_depts:
                if d and d not in all_selected:
                    all_selected.append(d)

        for d in clin_depts:
            if d and d not in all_selected:
                all_selected.append(d)

        cleaned_data['department'] = ', '.join(all_selected)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        erp_depts = self.cleaned_data.get('erp_departments') or []
        clin_depts = self.cleaned_data.get('clinical_departments') or []

        all_selected = []
        if 'All Departments' in erp_depts:
            all_selected.append('All Departments')
        else:
            for d in erp_depts:
                if d and d not in all_selected:
                    all_selected.append(d)

        for d in clin_depts:
            if d and d not in all_selected:
                all_selected.append(d)

        user.department = ', '.join(all_selected)
        if commit:
            user.save()
        return user


class UserEditCustomForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank to keep existing password'}),
        required=False,
        label="New Password (Optional)"
    )
    erp_departments = FlexibleMultipleChoiceField(
        choices=(),
        required=False,
        label="ERP Module / Portal Access",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select-multi-erp',
            'id': 'id_erp_departments',
        })
    )
    clinical_departments = FlexibleMultipleChoiceField(
        choices=(),
        required=False,
        label="Hospital / Clinical Department(s)",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select-multi-clinical',
            'id': 'id_clinical_departments',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_all_role_choices()
        self.fields['role'].choices = choices
        self.fields['role'].widget.choices = choices

        erp_choices = get_erp_department_choices()
        clin_choices = get_clinical_department_choices()

        self.fields['erp_departments'].choices = erp_choices
        self.fields['clinical_departments'].choices = clin_choices

        if self.instance and self.instance.department:
            current_raw = str(self.instance.department).strip()
            depts_list = [d.strip() for d in current_raw.split(',') if d.strip()]

            erp_init = []
            clin_init = []
            erp_keys = [c[0] for c in erp_choices]

            for d in depts_list:
                if d.lower() in ['all', 'all departments', 'all departments (universal access)']:
                    erp_init.append('All Departments')
                elif d in erp_keys:
                    erp_init.append(d)
                else:
                    clin_init.append(d)

            self.fields['erp_departments'].initial = erp_init
            self.fields['clinical_departments'].initial = clin_init

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role',
            'phone_number', 'employee_id', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '10'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if username and User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_employee_id(self):
        employee_id = (self.cleaned_data.get('employee_id') or '').strip()
        if employee_id and User.objects.filter(employee_id__iexact=employee_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this Employee ID already exists.")
        return employee_id

    def clean(self):
        cleaned_data = super().clean()
        erp_depts = cleaned_data.get('erp_departments') or []
        clin_depts = cleaned_data.get('clinical_departments') or []

        all_selected = []
        if 'All Departments' in erp_depts:
            all_selected.append('All Departments')
        else:
            for d in erp_depts:
                if d and d not in all_selected:
                    all_selected.append(d)

        for d in clin_depts:
            if d and d not in all_selected:
                all_selected.append(d)

        cleaned_data['department'] = ', '.join(all_selected)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)

        erp_depts = self.cleaned_data.get('erp_departments') or []
        clin_depts = self.cleaned_data.get('clinical_departments') or []

        all_selected = []
        if 'All Departments' in erp_depts:
            all_selected.append('All Departments')
        else:
            for d in erp_depts:
                if d and d not in all_selected:
                    all_selected.append(d)

        for d in clin_depts:
            if d and d not in all_selected:
                all_selected.append(d)

        user.department = ', '.join(all_selected)
        if commit:
            user.save()
        return user


class CustomRoleForm(forms.ModelForm):
    class Meta:
        model = CustomRole
        fields = ['name', 'code', 'description', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Doctor / Specialist', 'required': 'required'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. DOCTOR', 'required': 'required'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe duties and permissions of this role profile...', 'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-input-color', 'style': 'height: 40px; padding: 2px;'}),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. bi-person-badge-fill'}),
        }

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper().replace(' ', '_')
        if not code:
            raise forms.ValidationError("Role code key is required.")
        if code in User.Roles.values or CustomRole.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A system role profile with this Code key already exists.")
        return code


class LandingDepartmentForm(forms.ModelForm):
    allowed_prefixes_raw = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '/patients/add/, /patients/search/, /dashboard/'
        }),
        help_text="Comma-separated URL path prefixes allowed for this department (e.g. /patients/, /dashboard/)",
        label="Allowed URL Prefixes"
    )
    aliases_raw = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'front desk, opd, reception, registration'
        }),
        help_text="Comma-separated user department keywords matching this login department",
        label="Staff Department Aliases"
    )

    class Meta:
        from .models import LandingDepartment
        model = LandingDepartment
        fields = [
            'name', 'slug', 'code', 'icon', 'color_bg', 'color_icon',
            'badge', 'dashboard_url', 'landing_module', 'order',
            'is_active', 'is_system', 'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Emergency & Trauma', 'required': 'required'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. emergency-trauma', 'required': 'required'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. emergency_trauma', 'required': 'required'}),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. bi-heart-pulse-fill'}),
            'color_bg': forms.TextInput(attrs={'type': 'color', 'class': 'form-input-color', 'style': 'height: 40px; padding: 2px;'}),
            'color_icon': forms.TextInput(attrs={'type': 'color', 'class': 'form-input-color', 'style': 'height: 40px; padding: 2px;'}),
            'badge': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Critical Care / 24x7'}),
            'dashboard_url': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. /patients/add/'}),
            'landing_module': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. patients'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'step': '1'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe department duties and scope...', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_system': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if isinstance(self.instance.allowed_prefixes, list):
                self.fields['allowed_prefixes_raw'].initial = ", ".join(self.instance.allowed_prefixes)
            elif self.instance.allowed_prefixes:
                self.fields['allowed_prefixes_raw'].initial = str(self.instance.allowed_prefixes)

            if isinstance(self.instance.aliases, list):
                self.fields['aliases_raw'].initial = ", ".join(self.instance.aliases)
            elif self.instance.aliases:
                self.fields['aliases_raw'].initial = str(self.instance.aliases)

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip().lower().replace(' ', '-').replace('_', '-')
        from .models import LandingDepartment
        qs = LandingDepartment.objects.filter(slug__iexact=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Department slug '{slug}' is already taken.")
        return slug

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().lower().replace(' ', '_').replace('-', '_')
        from .models import LandingDepartment
        qs = LandingDepartment.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Department code '{code}' is already taken.")
        return code

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_p = self.cleaned_data.get('allowed_prefixes_raw', '')
        if raw_p:
            instance.allowed_prefixes = [p.strip() for p in raw_p.split(',') if p.strip()]
        else:
            instance.allowed_prefixes = []

        raw_a = self.cleaned_data.get('aliases_raw', '')
        if raw_a:
            instance.aliases = [a.strip().lower() for a in raw_a.split(',') if a.strip()]
        else:
            instance.aliases = []

        if commit:
            instance.save()
        return instance


class NavModuleForm(forms.ModelForm):
    """Form for creating and editing Navigation Modules."""
    class Meta:
        from .models import NavModule
        model = NavModule
        fields = ['name', 'code', 'icon', 'url_path', 'color', 'badge', 'order', 'is_active', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. Pharmacy, OT, Accounts', 'required': True}),
            'code': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. pharmacy (auto-generated if blank)'}),
            'icon': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. bi-capsule, bi-hospital', 'value': 'bi-folder2'}),
            'url_path': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. /pharmacy/ or #', 'value': '#'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-input-modal', 'style': 'height: 38px; padding: 2px 6px;', 'value': '#0284c7'}),
            'badge': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. Clinical, Supplies, System'}),
            'order': forms.NumberInput(attrs={'class': 'form-input-modal', 'value': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input-modal', 'rows': 2, 'placeholder': 'Brief description of what this module covers...'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError("Module name is required.")
        return name

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().lower().replace(' ', '_').replace('-', '_')
        name = (self.cleaned_data.get('name') or '').strip().lower().replace(' ', '_').replace('-', '_')
        if not code:
            code = name
        
        from .models import NavModule
        qs = NavModule.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A module with code '{code}' already exists. Please choose a unique code.")
        return code


class NavSubmoduleForm(forms.ModelForm):
    """Form for creating and editing Navigation Submodules."""
    class Meta:
        from .models import NavSubmodule
        model = NavSubmodule
        fields = ['module', 'name', 'code', 'icon', 'url_path', 'order', 'is_active', 'description']
        widgets = {
            'module': forms.Select(attrs={'class': 'form-input-modal', 'required': True}),
            'name': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. Prescription Entry, Bed Matrix', 'required': True}),
            'code': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. prescription_entry (auto-generated if blank)'}),
            'icon': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. bi-grid, bi-flask', 'value': 'bi-dot'}),
            'url_path': forms.TextInput(attrs={'class': 'form-input-modal', 'placeholder': 'e.g. /pharmacy/prescriptions/', 'required': True}),
            'order': forms.NumberInput(attrs={'class': 'form-input-modal', 'value': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input-modal', 'rows': 2, 'placeholder': 'Brief summary of what this submodule does...'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError("Submodule name is required.")
        return name

    def clean_url_path(self):
        url = (self.cleaned_data.get('url_path') or '').strip()
        if not url:
            raise forms.ValidationError("Target URL / Route Link is required.")
        return url

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().lower().replace(' ', '_').replace('-', '_')
        name = (self.cleaned_data.get('name') or '').strip().lower().replace(' ', '_').replace('-', '_')
        parent_module = self.cleaned_data.get('module')
        
        if not code:
            prefix = parent_module.code if parent_module else 'sub'
            code = f"{prefix}_{name}"
        
        from .models import NavSubmodule
        qs = NavSubmodule.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            # If auto-generated collision, make unique
            base = code
            ctr = 1
            while NavSubmodule.objects.filter(code=code).exclude(pk=self.instance.pk if self.instance else None).exists():
                code = f"{base}_{ctr}"
                ctr += 1
        return code


