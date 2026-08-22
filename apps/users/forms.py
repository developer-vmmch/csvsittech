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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_all_role_choices()
        self.fields['role'].choices = choices
        self.fields['role'].widget.choices = choices

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role',
            'department', 'phone_number', 'employee_id', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. EDWIN or DR_KUMAR', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'user@vmmc.edu.in'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. GENERAL MEDICINE or FRONT OFFICE'}),
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

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserEditCustomForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank to keep existing password'}),
        required=False,
        label="New Password (Optional)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_all_role_choices()
        self.fields['role'].choices = choices
        self.fields['role'].widget.choices = choices

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'role',
            'department', 'phone_number', 'employee_id', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-input'}),
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

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
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
