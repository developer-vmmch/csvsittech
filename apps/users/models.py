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
        if self.role == self.Roles.MANAGER and perm_code.startswith('auto_trigger.'):
            return True

        # Check aliases e.g. ATC_EDIT -> auto_trigger.atc.update
        aliases = {
            'ATC_VIEW': 'auto_trigger.atc.view',
            'ATC_CREATE': 'auto_trigger.atc.create',
            'ATC_EDIT': 'auto_trigger.atc.update',
            'ATC_TRIGGER': 'auto_trigger.atc.trigger',
            'ATC_EMERGENCY_STOP': 'auto_trigger.atc.stop',
        }
        if perm_code in aliases:
            return self.has_perm_code(aliases[perm_code])

        return False

    @property
    def can_atc_view(self):
        return self.has_perm_code('auto_trigger.atc.view')

    @property
    def can_atc_create(self):
        return self.has_perm_code('auto_trigger.atc.create')

    @property
    def can_atc_edit(self):
        return self.has_perm_code('auto_trigger.atc.update')

    @property
    def can_atc_trigger(self):
        return self.has_perm_code('auto_trigger.atc.trigger')

    @property
    def can_atc_emergency_stop(self):
        return self.has_perm_code('auto_trigger.atc.stop')

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
        all_keys = [
            'dashboard',
            'patients', 'add_patient', 'search_patient', 'patient_list', 'patient_import',
            'review', 'discharge', 'review_report', 'op_census', 'patient_companies',
            'department_list', 'add_department', 'add_company',
            'ward', 'ward_management', 'ward_allocation', 'ward_transfer', 'branch_transfer', 'branch_transfer_report',
            'master', 'master_departments', 'master_investigations', 'master_parameters',
            'lab_master', 'lab_master_dashboard', 'lab_sub_departments',
            'investigation_parameter_mapping', 'workload_mapping_list', 'mapping_validation',
            'import_lab_workload_csv', 'export_lab_workload_csv', 'legacy_mapping', 'universal_master_import_export',
            'consultant', 'doctor_window', 'service_request_add',
            'lab_orders', 'work_orders', 'order_entry', 'result_entry_list',
            'lab_reports', 'report_dashboard', 'report_daily', 'report_monthly',
            'report_sub_department', 'report_investigation', 'report_hospital_department',
            'report_benchmark', 'report_abnormal',
            'auto_trigger', 'auto_trigger_configuration', 'auto_trigger_history',
            'auto_trigger_monthly_create', 'auto_trigger_monthly', 'auto_trigger_monthly_census',
            'auto_trigger_automate_test', 'auto_trigger_result_view',
            'auto_trigger_atc', 'auto_trigger_atc_status', 'auto_trigger_atc_settings',
            'ot', 'ot_dashboard', 'ot_booking', 'ot_schedule', 'ot_live', 'ot_history', 'ot_master',
            'system_section', 'administration', 'users_roles', 'inventory', 'settings',
        ]

        if self.is_superuser or self.role == self.Roles.ADMIN:
            return {k: True for k in all_keys}

        db_perms = RoleMenuPermission.get_permissions_for_role(self.role)

        role_mappings = {
            self.Roles.MANAGER: {
                'dashboard': True,
                'patients': True, 'add_patient': True, 'search_patient': True, 'patient_list': True, 'patient_import': True,
                'review': True, 'discharge': True, 'review_report': True, 'op_census': True, 'patient_companies': True,
                'department_list': True, 'add_department': True, 'add_company': True,
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': True, 'master_departments': True, 'master_investigations': True, 'master_parameters': True,
                'lab_master': True, 'lab_master_dashboard': True, 'lab_sub_departments': True,
                'investigation_parameter_mapping': True, 'workload_mapping_list': True, 'mapping_validation': True,
                'import_lab_workload_csv': True, 'export_lab_workload_csv': True,
                'consultant': True, 'doctor_window': True, 'service_request_add': True,
                'lab_orders': True, 'work_orders': True, 'order_entry': True, 'result_entry_list': True,
                'lab_reports': True, 'report_dashboard': True, 'report_daily': True, 'report_monthly': True,
                'report_sub_department': True, 'report_investigation': True, 'report_hospital_department': True,
                'report_benchmark': True, 'report_abnormal': True,
                'auto_trigger': True, 'auto_trigger_configuration': True, 'auto_trigger_history': True,
                'auto_trigger_monthly_create': True, 'auto_trigger_monthly': True, 'auto_trigger_monthly_census': True,
                'auto_trigger_automate_test': True, 'auto_trigger_result_view': True,
                'auto_trigger_atc': True, 'auto_trigger_atc_status': True, 'auto_trigger_atc_settings': True,
                'ot': True, 'ot_dashboard': True, 'ot_booking': True, 'ot_schedule': True, 'ot_live': True, 'ot_history': True, 'ot_master': True,
                'system_section': True, 'administration': False, 'users_roles': False, 'inventory': True, 'settings': False,
            },
            self.Roles.STAFF: {
                'dashboard': True,
                'patients': True, 'add_patient': True, 'search_patient': True, 'patient_list': True, 'patient_import': False,
                'review': True, 'discharge': True, 'review_report': True, 'op_census': True, 'patient_companies': False,
                'department_list': False, 'add_department': False, 'add_company': False,
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': False, 'master_departments': False, 'master_investigations': False, 'master_parameters': False,
                'lab_master': False, 'lab_master_dashboard': False, 'lab_sub_departments': False,
                'investigation_parameter_mapping': False, 'workload_mapping_list': False, 'mapping_validation': False,
                'import_lab_workload_csv': False, 'export_lab_workload_csv': False,
                'consultant': True, 'doctor_window': True, 'service_request_add': True,
                'lab_orders': True, 'work_orders': True, 'order_entry': True, 'result_entry_list': True,
                'lab_reports': True, 'report_dashboard': True, 'report_daily': True, 'report_monthly': False,
                'report_sub_department': False, 'report_investigation': False, 'report_hospital_department': False,
                'report_benchmark': False, 'report_abnormal': False,
                'auto_trigger': False, 'auto_trigger_configuration': False, 'auto_trigger_history': False,
                'auto_trigger_monthly_create': False, 'auto_trigger_monthly': False, 'auto_trigger_monthly_census': False,
                'auto_trigger_automate_test': False, 'auto_trigger_result_view': False,
                'ot': True, 'ot_dashboard': True, 'ot_booking': True, 'ot_schedule': True, 'ot_live': False, 'ot_history': False, 'ot_master': False,
                'system_section': False, 'administration': False, 'users_roles': False, 'inventory': False, 'settings': False,
            },
            self.Roles.AUDITOR: {
                'dashboard': True,
                'patients': True, 'add_patient': False, 'search_patient': True, 'patient_list': True, 'patient_import': False,
                'review': True, 'discharge': True, 'review_report': True, 'op_census': True, 'patient_companies': True,
                'department_list': True, 'add_department': False, 'add_company': False,
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': True, 'master_departments': True, 'master_investigations': True, 'master_parameters': True,
                'lab_master': False, 'lab_master_dashboard': False, 'lab_sub_departments': False,
                'investigation_parameter_mapping': False, 'workload_mapping_list': False, 'mapping_validation': False,
                'import_lab_workload_csv': False, 'export_lab_workload_csv': False,
                'consultant': False, 'doctor_window': False, 'service_request_add': False,
                'lab_orders': False, 'work_orders': False, 'order_entry': False, 'result_entry_list': False,
                'lab_reports': True, 'report_dashboard': True, 'report_daily': True, 'report_monthly': True,
                'report_sub_department': True, 'report_investigation': True, 'report_hospital_department': True,
                'report_benchmark': True, 'report_abnormal': True,
                'auto_trigger': False, 'auto_trigger_configuration': False, 'auto_trigger_history': False,
                'auto_trigger_monthly_create': False, 'auto_trigger_monthly': False, 'auto_trigger_monthly_census': False,
                'auto_trigger_automate_test': False, 'auto_trigger_result_view': False,
                'ot': True, 'ot_dashboard': True, 'ot_booking': False, 'ot_schedule': True, 'ot_live': False, 'ot_history': True, 'ot_master': False,
                'system_section': False, 'administration': False, 'users_roles': False, 'inventory': False, 'settings': False,
            },
        }

        default_map = role_mappings.get(self.role, {
            'dashboard': True,
            'patients': True, 'add_patient': True, 'search_patient': True, 'patient_list': True, 'patient_import': False,
            'review': True, 'discharge': True, 'review_report': True, 'op_census': True, 'patient_companies': False,
            'department_list': False, 'add_department': False, 'add_company': False,
            'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
            'master': False, 'master_departments': False, 'master_investigations': False, 'master_parameters': False,
            'lab_master': False, 'lab_master_dashboard': False, 'lab_sub_departments': False,
            'investigation_parameter_mapping': False, 'workload_mapping_list': False, 'mapping_validation': False,
            'import_lab_workload_csv': False, 'export_lab_workload_csv': False,
            'consultant': True, 'doctor_window': True, 'service_request_add': True,
            'lab_orders': True, 'work_orders': True, 'order_entry': True, 'result_entry_list': True,
            'lab_reports': True, 'report_dashboard': True, 'report_daily': True, 'report_monthly': False,
            'report_sub_department': False, 'report_investigation': False, 'report_hospital_department': False,
            'report_benchmark': False, 'report_abnormal': False,
            'auto_trigger': False, 'auto_trigger_configuration': False, 'auto_trigger_history': False,
            'auto_trigger_monthly_create': False, 'auto_trigger_monthly': False, 'auto_trigger_monthly_census': False,
            'auto_trigger_automate_test': False, 'auto_trigger_result_view': False,
            'ot': True, 'ot_dashboard': True, 'ot_booking': True, 'ot_schedule': True, 'ot_live': False, 'ot_history': False, 'ot_master': False,
            'system_section': False, 'administration': False, 'users_roles': False, 'inventory': False, 'settings': False,
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
