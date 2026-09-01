from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        MANAGER = 'MANAGER', 'Department Manager'
        STAFF = 'STAFF', 'Staff Member'
        AUDITOR = 'AUDITOR', 'Auditor'

    role = models.CharField(
        max_length=50,
        default=Roles.STAFF,
        help_text='Role within the ERP system'
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def get_role_display(self):
        built_in = dict(self.Roles.choices)
        if self.role in built_in:
            return built_in[self.role]
        try:
            cr = CustomRole.objects.filter(code__iexact=self.role).first()
            if cr:
                return cr.name
        except Exception:
            pass
        return (self.role or '').replace('_', ' ').title()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @classmethod
    def generate_next_employee_id(cls):
        """Generates sequential numeric Employee ID starting from EMP-001"""
        import re
        last_user = cls.objects.exclude(employee_id__isnull=True).exclude(employee_id='').order_by('-id').first()
        if last_user and last_user.employee_id:
            digits = re.findall(r'\d+', last_user.employee_id)
            if digits:
                next_num = int(digits[-1]) + 1
                return f"EMP-{next_num:03d}"
        return "EMP-001"

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_next_employee_id()
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Roles.ADMIN

    def has_perm_code(self, perm_code):
        """
        Check if user has a specific permission code, e.g. 'patients.patient_list.view'.
        Super Admin always returns True.
        """
        if self.is_superuser or self.role == self.Roles.ADMIN:
            return True
            
        from apps.users.models import RoleMenuPermission
        db_perms = RoleMenuPermission.get_permissions_for_role(self.role)
        if db_perms and isinstance(db_perms, dict):
            return db_perms.get(perm_code, False)
            
        # Default fallback for specific legacy roles if not configured in DB
        return False

    @property
    def is_manager_role(self):
        return self.is_admin_role or self.role == self.Roles.MANAGER

    @property
    def can_add_patient(self):
        return self.is_admin_role or self.role in [self.Roles.MANAGER, self.Roles.STAFF]

    @property
    def can_view_companies(self):
        return self.is_admin_role or self.role in [self.Roles.MANAGER, self.Roles.AUDITOR]

    @property
    def can_view_departments(self):
        return self.is_admin_role or self.role in [self.Roles.MANAGER, self.Roles.AUDITOR]

    @property
    def can_manage_departments(self):
        return self.is_manager_role

    @property
    def can_manage_companies(self):
        return self.is_manager_role

    @property
    def can_manage_users(self):
        return self.is_admin_role

    def get_menu_mapping(self):
        """
        Central mapping function returning a dictionary of sidebar menu keys
        and their accessibility boolean flags based on the user's role/profile.
        Supports dynamic DB overrides from RoleMenuPermission model.
        """
        if self.is_superuser or self.role == self.Roles.ADMIN:
            return {
                'dashboard': True,
                'add_patient': True,
                'search_patient': True,
                'patient_list': True,
                'review': True,
                'review_report': True,
                'op_census': True,
                'patient_companies': True,
                'department_list': True,
                'add_department': True,
                'add_company': True,
                'system_section': True,
                'administration': True,
                'users_roles': True,
                'inventory': True,
                'settings': True,
                'auto_trigger': True,
            }

        db_perms = RoleMenuPermission.get_permissions_for_role(self.role)

        role_mappings = {
            self.Roles.MANAGER: {
                'dashboard': True,
                'add_patient': True,
                'search_patient': True,
                'patient_list': True,
                'review': True,
                'review_report': True,
                'op_census': True,
                'patient_companies': True,
                'department_list': True,
                'add_department': True,
                'add_company': True,
                'system_section': True,
                'administration': False,
                'users_roles': False,
                'inventory': True,
                'settings': False,
                'auto_trigger': True,
            },
            self.Roles.STAFF: {
                'dashboard': True,
                'add_patient': True,
                'search_patient': True,
                'patient_list': True,
                'review': True,
                'review_report': True,
                'op_census': True,
                'patient_companies': False,
                'department_list': False,
                'add_department': False,
                'add_company': False,
                'system_section': False,
                'administration': False,
                'users_roles': False,
                'inventory': False,
                'settings': False,
                'auto_trigger': False,
            },
            self.Roles.AUDITOR: {
                'dashboard': True,
                'add_patient': False,
                'search_patient': True,
                'patient_list': True,
                'review': True,
                'review_report': True,
                'op_census': True,
                'patient_companies': True,
                'department_list': True,
                'add_department': False,
                'add_company': False,
                'system_section': False,
                'administration': False,
                'users_roles': False,
                'inventory': False,
                'settings': False,
                'auto_trigger': False,
            },
        }

        default_map = role_mappings.get(self.role, {
            'dashboard': True,
            'add_patient': True,
            'search_patient': True,
            'patient_list': True,
            'op_census': True,
            'patient_companies': False,
            'department_list': False,
            'add_department': False,
            'add_company': False,
            'system_section': False,
            'administration': False,
            'users_roles': False,
            'inventory': False,
            'settings': False,
            'auto_trigger': False,
        })

        if db_perms:
            merged = default_map.copy()
            merged.update(db_perms)
            return merged

        return default_map

    def can_access_menu(self, menu_key):
        """Checks whether the user's role profile has access to a given menu key."""
        mapping = self.get_menu_mapping()
        return mapping.get(menu_key, False)


class CustomRole(models.Model):
    code = models.CharField(max_length=30, unique=True, help_text="Unique uppercase role key e.g. DOCTOR, RECEPTIONIST")
    name = models.CharField(max_length=100, help_text="Human-readable role title e.g. Doctor / Specialist")
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=20, default="#0284c7")
    badge_class = models.CharField(max_length=50, default="badge-blue")
    icon = models.CharField(max_length=50, default="bi-person-badge-fill")

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper().strip().replace(' ', '_')
        super().save(*args, **kwargs)


class RoleMenuPermission(models.Model):
    role = models.CharField(max_length=50, unique=True)
    menu_permissions = models.JSONField(default=dict)

    def __str__(self):
        return f"Menu Mapping for {self.role}"

    @classmethod
    def get_permissions_for_role(cls, role_code):
        try:
            perm = cls.objects.filter(role=role_code).first()
            if perm and isinstance(perm.menu_permissions, dict):
                return perm.menu_permissions
        except Exception:
            pass
        return None
