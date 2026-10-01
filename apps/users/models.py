from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        DEVELOPER = 'DEVELOPER', 'Developer'
        MANAGER = 'MANAGER', 'Department Manager'
        STAFF = 'STAFF', 'Staff Member'
        AUDITOR = 'AUDITOR', 'Auditor'

    role = models.CharField(
        max_length=50,
        default=Roles.STAFF,
        help_text='Role within the ERP system'
    )
    department = models.CharField(max_length=500, blank=True, null=True, help_text="Assigned department(s) (comma-separated or 'All Departments')")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def get_departments_list(self):
        """Returns the list of department names assigned to this user."""
        if not self.department:
            return []
        raw = str(self.department).strip()
        if raw.lower() in ['all', 'all departments', 'all departments (universal access)']:
            return ['All Departments']
        return [d.strip() for d in raw.split(',') if d.strip()]

    def get_role_display(self):
        built_in = dict(self.Roles.choices)
        if self.role in built_in:
            return built_in[self.role]
        if str(self.role).upper() in ['DEVELOPER', 'DEVELOPER_ROLE']:
            return 'Developer'
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
        role_str = (self.role or '').strip().upper()
        return self.is_superuser or role_str in [self.Roles.ADMIN, self.Roles.DEVELOPER, 'DEVELOPER', 'DEVELOPER_ROLE']

    def has_perm_code(self, perm_code):
        """
        Check if user has a specific granular permission code:
        e.g. 'patients.patient_list.view', 'patients.patient_list.update',
             'patients.patient_list.delete', 'patients.patient_list.import',
             'patients.patient_list.export', 'patient_list.edit', 'patient_list.delete'
        Unified Collaborative Permission Engine:
        Evaluates effective user permissions by combining:
        1. Landing Department Permission (LandingDepartment.nav_permissions / DEPT_DEFAULT_NAV_MAPPING)
        2. System Role Permission (RoleMenuPermission / role default mapping)

        RULE: Effective Access = Landing Department Permission AND System Role Permission.
        Both must explicitly permit access. If either denies or is not granted, access is DENIED.
        Superuser and Administrators retain full access.
        """
        role_str = (self.role or '').strip().upper()
        if self.is_superuser or role_str in [self.Roles.ADMIN, self.Roles.DEVELOPER, 'DEVELOPER', 'DEVELOPER_ROLE']:
            return True

        if not perm_code:
            return False

        # Check aliases e.g. ATC_EDIT -> auto_trigger.atc.update
        aliases = {
            'ATC_VIEW': 'auto_trigger.atc.view',
            'ATC_CREATE': 'auto_trigger.atc.create',
            'ATC_EDIT': 'auto_trigger.atc.update',
            'ATC_TRIGGER': 'auto_trigger.atc.trigger',
            'ATC_EMERGENCY_STOP': 'auto_trigger.atc.stop',
        }
        if perm_code in aliases:
            perm_code = aliases[perm_code]

        depts_list = self.get_departments_list()
        is_universal_dept = ('All Departments' in depts_list)

        # Helper to check a permission key/action in a permissions dict
        def _check_dict(perms_dict, code):
            if not perms_dict or not isinstance(perms_dict, dict):
                return None

            parts = code.split('.')
            if len(parts) == 1:
                sub_code = parts[0]
                action = 'view'
            elif len(parts) == 2:
                action_words = ['view', 'access', 'create', 'add', 'edit', 'update', 'delete', 'cancel', 'print', 'export', 'stop', 'trigger']
                if parts[1].lower() in action_words:
                    sub_code = parts[0]
                    action = parts[1].lower()
                else:
                    sub_code = parts[1]
                    action = 'view'
            else:
                sub_code = parts[-2]
                action = parts[-1].lower()

            # Map action synonyms
            action_aliases = [action]
            if action in ['edit', 'update']:
                action_aliases = ['edit', 'update']
            elif action in ['add', 'create']:
                action_aliases = ['add', 'create']
            elif action in ['delete', 'cancel']:
                action_aliases = ['delete', 'cancel']
            elif action in ['print', 'export']:
                action_aliases = ['print', 'export']
            elif action in ['view', 'access']:
                action_aliases = ['view', 'access']

            # 1. If the submodule itself is explicitly disabled (False), all actions under it are False
            if sub_code in perms_dict and perms_dict[sub_code] is False:
                return False
            if sub_code.replace('.', '_') in perms_dict and perms_dict[sub_code.replace('.', '_')] is False:
                return False

            # 2. Check granular action dict e.g. perms_dict.get('search_patient_actions')
            act_obj = perms_dict.get(f"{sub_code}_actions")
            if isinstance(act_obj, dict):
                for act in action_aliases:
                    if act in act_obj and act_obj[act] is not None:
                        return bool(act_obj[act])

            # 3. Check specific action keys
            for act in action_aliases:
                k1 = f"{sub_code}.{act}"
                k2 = f"{sub_code}_{act}"
                k3 = f"{code.replace('.', '_')}_{act}"
                if k1 in perms_dict and perms_dict[k1] is not None:
                    return bool(perms_dict[k1])
                if k2 in perms_dict and perms_dict[k2] is not None:
                    return bool(perms_dict[k2])
                if k3 in perms_dict and perms_dict[k3] is not None:
                    return bool(perms_dict[k3])

            # 4. Direct exact code match
            if code in perms_dict and perms_dict[code] is not None:
                return bool(perms_dict[code])

            # 5. If action is 'view' or 'access', fallback to submodule base toggle
            if action in ['view', 'access']:
                if sub_code in perms_dict and perms_dict[sub_code] is not None:
                    return bool(perms_dict[sub_code])
                if sub_code.replace('.', '_') in perms_dict and perms_dict[sub_code.replace('.', '_')] is not None:
                    return bool(perms_dict[sub_code.replace('.', '_')])

            return None

        # 1. Resolve Landing Department Permission
        dept_allowed = True
        if depts_list and not is_universal_dept:
            dept_res = None
            try:
                from apps.users.models import LandingDepartment
                from apps.users.nav_config import DEPT_DEFAULT_NAV_MAPPING
                for dept_name in depts_list:
                    dept_obj = (
                        LandingDepartment.objects.filter(name__iexact=dept_name).first()
                        or LandingDepartment.objects.filter(code__iexact=dept_name.lower().replace(' ', '_')).first()
                        or LandingDepartment.objects.filter(slug__iexact=dept_name.lower().replace(' ', '-')).first()
                    )
                    if dept_obj:
                        d_perms = dept_obj.nav_permissions if (dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0) else DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
                        d_res = _check_dict(d_perms, perm_code)
                        if d_res is not None:
                            dept_res = d_res
                            break
            except Exception:
                pass
            dept_allowed = bool(dept_res is True)

        # 2. Resolve System Role Permission
        role_res = None
        try:
            from apps.users.models import RoleMenuPermission
            r_perms = RoleMenuPermission.get_permissions_for_role(self.role)
            if r_perms and isinstance(r_perms, dict) and len(r_perms) > 0:
                role_res = _check_dict(r_perms, perm_code)
            else:
                default_role_map = self.get_role_default_mapping()
                role_res = _check_dict(default_role_map, perm_code)
        except Exception:
            pass

        role_allowed = bool(role_res is True)

        # 3. Collaborative Intersection: BOTH must allow access
        return bool(dept_allowed and role_allowed)

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
            'ward', 'ward_management', 'ward_allocation', 'ward_service_request', 'ward_transfer', 'branch_transfer', 'branch_transfer_report',
            'master', 'master_departments', 'master_wards', 'master_investigations', 'master_parameters',
            'lab_master', 'lab_master_dashboard', 'lab_sub_departments', 'lab_master_permissions',
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

        role_str = (self.role or '').strip().upper()
        if self.is_superuser or role_str in [self.Roles.ADMIN, self.Roles.DEVELOPER, 'DEVELOPER', 'DEVELOPER_ROLE']:
            return {k: True for k in all_keys}

        db_perms = RoleMenuPermission.get_permissions_for_role(self.role)

        role_mappings = {
            self.Roles.MANAGER: {
                'dashboard': True,
                'patients': True, 'add_patient': True, 'search_patient': True, 'patient_list': True, 'patient_import': True,
                'review': True, 'discharge': True, 'review_report': True, 'op_census': True, 'patient_companies': True,
                'department_list': True, 'add_department': True, 'add_company': True,
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_service_request': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': True, 'master_departments': True, 'master_wards': True, 'master_investigations': True, 'master_parameters': True,
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
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_service_request': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': False, 'master_departments': False, 'master_wards': False, 'master_investigations': False, 'master_parameters': False,
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
                'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_service_request': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
                'master': True, 'master_departments': True, 'master_wards': True, 'master_investigations': True, 'master_parameters': True,
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
            'ward': True, 'ward_management': True, 'ward_allocation': True, 'ward_service_request': True, 'ward_transfer': True, 'branch_transfer': True, 'branch_transfer_report': True,
            'master': False, 'master_departments': False, 'master_wards': False, 'master_investigations': False, 'master_parameters': False,
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

        role_map = default_map.copy()
        if db_perms:
            role_map.update(db_perms)

        # Department mapping from LandingDepartment
        dept_map = {}
        has_dept_perms = False
        depts_list = self.get_departments_list()
        if 'All Departments' in depts_list:
            return {k: bool(role_map.get(k, False)) for k in all_keys}

        try:
            from apps.users.models import LandingDepartment
            from apps.users.nav_config import DEPT_DEFAULT_NAV_MAPPING
            for dept_name in depts_list:
                dept_obj = (
                    LandingDepartment.objects.filter(name__iexact=dept_name).first()
                    or LandingDepartment.objects.filter(code__iexact=dept_name.lower().replace(' ', '_')).first()
                    or LandingDepartment.objects.filter(slug__iexact=dept_name.lower().replace(' ', '-')).first()
                )
                if dept_obj:
                    d_perms = dept_obj.nav_permissions if (dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0) else DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
                    if d_perms:
                        has_dept_perms = True
                        for k, v in d_perms.items():
                            if isinstance(v, bool):
                                dept_map[k] = v
        except Exception:
            pass

        if not has_dept_perms:
            return role_map

        # Collaborative intersection: Both Landing Department and System Role must permit access
        merged = {}
        all_keys_set = set(role_map.keys()) | set(dept_map.keys()) | set(all_keys)
        for k in all_keys_set:
            r_val = role_map.get(k)
            d_val = dept_map.get(k)
            if r_val is True and d_val is True:
                merged[k] = True
            elif r_val is True and d_val is None:
                merged[k] = True
            elif d_val is True and r_val is None:
                merged[k] = True
            else:
                merged[k] = False

        return merged

    def can_access_menu(self, menu_key):
        """Checks whether the user's role profile has access to a given menu key."""
        role_str = (self.role or '').strip().upper()
        if self.is_superuser or role_str in [self.Roles.ADMIN, self.Roles.DEVELOPER, 'DEVELOPER', 'DEVELOPER_ROLE']:
            return True
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


class NavModule(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Unique identifier key (e.g. patients, lab, custom_mod)")
    name = models.CharField(max_length=100, help_text="Display title in top navbar")
    icon = models.CharField(max_length=50, default="bi-folder2", help_text="Bootstrap icon class")
    url_path = models.CharField(max_length=255, default="#", help_text="Default URL or target link")
    color = models.CharField(max_length=20, default="#0284c7", help_text="Hex color or badge accent")
    badge = models.CharField(max_length=50, blank=True, null=True, help_text="Short category badge")
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Nav Module"
        verbose_name_plural = "Nav Modules"

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def active_submodules(self):
        return self.submodules.filter(is_active=True).order_by('order', 'id')


class NavSubmodule(models.Model):
    module = models.ForeignKey(NavModule, on_delete=models.CASCADE, related_name='submodules')
    code = models.CharField(max_length=60, unique=True, help_text="Permission / lookup key")
    name = models.CharField(max_length=100, help_text="Submodule link title")
    icon = models.CharField(max_length=50, default="bi-dot", help_text="Bootstrap icon class")
    url_path = models.CharField(max_length=255, default="#", help_text="Target URL or pattern")
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Nav Submodule"
        verbose_name_plural = "Nav Submodules"

    def __str__(self):
        return f"{self.module.name} -> {self.name} ({self.code})"


class LandingDepartment(models.Model):
    """
    Model representing a Hospital Department Card on the First Landing Screen.
    Allows administrators to dynamically create, edit, reorder, customize styling/icons,
    and enable/disable department login portals.
    """
    code = models.CharField(max_length=50, unique=True, help_text="Internal identifier code (e.g. front_desk, consultant)")
    slug = models.SlugField(max_length=60, unique=True, help_text="URL slug for login portal (e.g. front-desk)")
    name = models.CharField(max_length=100, help_text="Department display title on landing card")
    icon = models.CharField(max_length=50, default="bi-hospital", help_text="Bootstrap icon class (e.g. bi-person-workspace)")
    color_bg = models.CharField(max_length=20, default="#e0f2fe", help_text="Icon badge background hex color")
    color_icon = models.CharField(max_length=20, default="#0284c7", help_text="Icon foreground hex color")
    badge = models.CharField(max_length=80, blank=True, null=True, help_text="Subtitle or category badge on the card")
    dashboard_url = models.CharField(max_length=255, default="/dashboard/", help_text="Destination dashboard URL after successful login")
    landing_module = models.CharField(max_length=60, blank=True, null=True, help_text="Permission module code")
    allowed_prefixes = models.JSONField(default=list, blank=True, help_text="List of URL path prefixes allowed for this department")
    aliases = models.JSONField(default=list, blank=True, help_text="List of staff user department keywords matching this department")
    description = models.TextField(blank=True, null=True, help_text="Department duties, scope and notes")
    order = models.PositiveIntegerField(default=10, help_text="Sort order on landing grid")
    is_active = models.BooleanField(default=True, help_text="Whether visible on the landing page")
    is_system = models.BooleanField(default=False, help_text="System-protected default department")
    nav_permissions = models.JSONField(default=dict, blank=True, help_text="Department-specific Top Navigation Bar modules and submodules access mapping")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Landing Department"
        verbose_name_plural = "Landing Departments"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_nav_permissions(self):
        if isinstance(self.nav_permissions, dict) and self.nav_permissions:
            return self.nav_permissions
        return {}

    def to_dict(self):
        def _to_list(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str) and val.strip():
                return [x.strip() for x in val.split(',') if x.strip()]
            return []

        return {
            'id': self.id,
            'code': self.code,
            'slug': self.slug,
            'name': self.name,
            'icon': self.icon or 'bi-hospital',
            'color_bg': self.color_bg or '#e0f2fe',
            'color_icon': self.color_icon or '#0284c7',
            'badge': self.badge or '',
            'dashboard_url': self.dashboard_url or '/dashboard/',
            'landing_module': self.landing_module or '',
            'allowed_prefixes': _to_list(self.allowed_prefixes),
            'aliases': _to_list(self.aliases),
            'description': self.description or '',
            'order': self.order,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'nav_permissions': self.get_nav_permissions(),
        }


