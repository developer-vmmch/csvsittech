from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import models
from .forms import UserCreationCustomForm, UserEditCustomForm, UserLoginForm, CustomRoleForm
from .models import RoleMenuPermission, CustomRole
from .permissions import PERMISSION_MODULES

User = get_user_model()


def check_username_api(request):
    """API endpoint to check if a username is already taken"""
    username = request.GET.get('username', '').strip()
    user_id = request.GET.get('user_id', '').strip()

    if not username:
        return JsonResponse({'exists': False, 'message': ''})

    qs = User.objects.filter(username__iexact=username)
    if user_id and user_id.isdigit():
        qs = qs.exclude(pk=int(user_id))

    if qs.exists():
        return JsonResponse({
            'exists': True,
            'message': f'Username "{username}" is already taken. Please choose a different username.'
        })
    else:
        return JsonResponse({
            'exists': False,
            'message': f'Username "{username}" is available.'
        })

def get_default_landing_url(user):
    """
    Determine the correct post-login destination for a user.

    Priority:
      1. Dashboard (if accessible)
      2. First accessible sidebar module, in the order the sidebar defines them
      3. Safe fallback to /dashboard/
    """
    from django.urls import reverse

    LANDING_CANDIDATES = [
        # key                       url_name                    namespace
        ('dashboard',               'dashboard',                'core'),
        # Patients
        ('add_patient',             'add',                      'patients'),
        ('search_patient',          'search',                   'patients'),
        ('patient_list',            'list',                     'patients'),
        ('patient_import',          'import',                   'patients'),
        ('review',                  'review',                   'patients'),
        ('discharge',               'discharge',                'patients'),
        ('branch_transfer',         'branch_transfer',          'patients'),
        ('review_report',           'review_report',            'patients'),
        ('op_census',               'op_census',                'patients'),
        ('patient_companies',       'company_list',             'patients'),
        ('department_list',         'department_list',          'patients'),
        # Ward
        ('ward',                    'branch_transfer',          'patients'),
        ('ward_management',         'ward_list',                'patients'),
        ('ward_allocation',         'ward_allocation',          'patients'),
        ('ward_service_request',    'ward_service_request',     'patients'),
        ('ward_transfer',           'branch_transfer',          'patients'),
        # Master / Lab Master
        ('master',                  'department_list',          'patients'),
        ('master_departments',      'department_list',          'patients'),
        ('master_wards',            'ward_list',                'patients'),
        ('master_investigations',   'investigation_list',       'lab'),
        ('master_parameters',       'parameter_list',           'lab'),
        ('lab_master',              'lab_master_dashboard',     'lab'),
        ('lab_master_dashboard',    'lab_master_dashboard',     'lab'),
        ('lab_sub_departments',     'lab_sub_departments',      'lab'),
        ('investigation_parameter_mapping', 'investigation_parameter_mapping', 'lab'),
        ('workload_mapping_list',   'workload_mapping_list',    'lab'),
        ('legacy_mapping',          'legacy_mapping',           'lab'),
        # Consultant
        ('consultant',              'doctor_window',            'lab'),
        ('doctor_window',           'doctor_window',            'lab'),
        ('service_request_add',     'service_request_add',      'lab'),
        # Lab Orders
        ('lab_orders',              'work_orders',              'lab'),
        ('work_orders',             'work_orders',              'lab'),
        ('order_entry',             'order_entry',              'lab'),
        ('result_entry_list',       'result_entry_list',        'lab'),
        # Lab Reports
        ('lab_reports',             'report_dashboard',         'lab'),
        ('report_dashboard',        'report_dashboard',         'lab'),
        ('report_daily',            'report_daily',             'lab'),
        # Auto Trigger
        ('auto_trigger',            'auto_trigger_configuration', 'lab'),
        ('auto_trigger_configuration', 'auto_trigger_configuration', 'lab'),
        ('auto_trigger_history',    'auto_trigger_history',     'lab'),
        ('auto_trigger_atc',        'auto_trigger_atc',         'lab'),
        ('auto_trigger_atc_status', 'auto_trigger_atc_status',  'lab'),
        ('auto_trigger_atc_settings', 'auto_trigger_atc_settings', 'lab'),
        # OT
        ('ot',                      'dashboard',                'ot'),
        ('ot_dashboard',            'dashboard',                'ot'),
        ('ot_booking',              'booking_list',             'ot'),
        ('ot_schedule',             'schedule',                 'ot'),
        # Administration
        ('administration',          'list',                     'users'),
        ('users_roles',             'roles_overview',           'users'),
        ('system_section',          'list',                     'users'),
    ]

    menu_map = user.get_menu_mapping() if hasattr(user, 'get_menu_mapping') else {}

    for key, url_name, namespace in LANDING_CANDIDATES:
        # Admin users get all keys as True; others check the map
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') == getattr(user.__class__.Roles, 'ADMIN', 'ADMIN'):
            has_perm = True
        else:
            has_perm = menu_map.get(key, False)

        if has_perm:
            try:
                if namespace:
                    return reverse(f'{namespace}:{url_name}')
                return reverse(url_name)
            except Exception:
                continue

    # Absolute safe fallback for logged-in user:
    try:
        return reverse('core:dashboard')
    except Exception:
        return '/dashboard/'


class ERPLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # 1. Honour a safe, local "next" parameter if present.
        next_url = self.request.POST.get('next') or self.request.GET.get('next', '')
        if next_url and next_url != '/' and next_url != reverse_lazy('login'):
            from django.utils.http import url_has_allowed_host_and_scheme
            if url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            ):
                return next_url

        # 2. Determine landing page from the user's role/profile.
        url = get_default_landing_url(self.request.user)
        if not url or url == '/' or url == reverse_lazy('login'):
            return reverse_lazy('core:dashboard')
        return url


class ERPLogoutView(LogoutView):
    next_page = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


class UserListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'administration'
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'system_users'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and int(page_size) in [10, 25, 50, 100]:
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        return User.objects.order_by('-id')


class StaffListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'administration'
    model = User
    template_name = 'users/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and int(page_size) in [10, 25, 50, 100]:
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        return User.objects.filter(role=User.Roles.STAFF).order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_staff = User.objects.filter(role=User.Roles.STAFF)
        context['total_staff'] = all_staff.count()
        context['active_staff'] = all_staff.filter(is_active=True).count()
        context['disabled_staff'] = all_staff.filter(is_active=False).count()
        return context


class UserCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'administration'
    model = User
    form_class = UserCreationCustomForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:list')

    def get_initial(self):
        initial = super().get_initial()
        initial['employee_id'] = User.generate_next_employee_id()
        role_param = self.request.GET.get('role')
        if role_param and role_param.upper() in User.Roles.values:
            initial['role'] = role_param.upper()
        return initial

    def form_valid(self, form):
        try:
            user = form.save()
            messages.success(self.request, f"User account '{user.username}' ({user.get_role_display()}) created successfully!")
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f"Error creating user: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors in the form below.")
        return super().form_invalid(form)


class UserUpdateView(LoginRequiredMixin, MenuAccessRequiredMixin, UpdateView):
    menu_key = 'administration'
    model = User
    form_class = UserEditCustomForm
    template_name = 'users/user_edit_form.html'
    success_url = reverse_lazy('users:list')

    def form_valid(self, form):
        try:
            user = form.save()
            messages.success(self.request, f"User account '{user.username}' updated successfully!")
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f"Error updating user: {str(e)}")
            return self.form_invalid(form)


class UserDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, DeleteView):
    menu_key = 'administration'
    model = User
    success_url = reverse_lazy('users:list')

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            messages.error(request, "You cannot delete your own active session user account.")
            return redirect(self.success_url)
        messages.success(request, f"User account '{user.username}' deleted successfully.")
        return super().post(request, *args, **kwargs)


class RoleCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'users_roles'
    model = CustomRole
    form_class = CustomRoleForm
    template_name = 'users/role_add_form.html'
    success_url = reverse_lazy('users:roles_overview')

    def form_valid(self, form):
        try:
            role_obj = form.save()
            RoleMenuPermission.objects.get_or_create(
                role=role_obj.code,
                defaults={'menu_permissions': {'dashboard': True, 'search_patient': True, 'patient_list': True}}
            )
            messages.success(self.request, f"New Role Profile '{role_obj.name}' ({role_obj.code}) created successfully!")
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f"Error creating role profile: {str(e)}")
            return self.form_invalid(form)


class RoleMenuPermissionsView(LoginRequiredMixin, MenuAccessRequiredMixin, View):
    menu_key = 'users_roles'
    template_name = 'users/role_permissions.html'

    def get_menu_definitions(self):
        return [
            # Main Navigation
            {'key': 'dashboard', 'label': 'Dashboard Overview', 'section': 'MAIN NAVIGATION'},

            # Patients Management
            {'key': 'add_patient', 'label': 'Add Patient', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'search_patient', 'label': 'Search Patient', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'patient_list', 'label': 'Patient Directory', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'patient_import', 'label': 'Patient Import', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'review', 'label': 'Patient Review', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'discharge', 'label': 'Patient Discharge', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'review_report', 'label': 'Patient Review Report', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'op_census', 'label': 'OP Census Analytics', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'patient_companies', 'label': 'Patient Companies', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'department_list', 'label': 'Departments & Units', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'add_department', 'label': '+ Add Department', 'section': 'PATIENT SETUP'},
            {'key': 'add_company', 'label': '+ Add Company', 'section': 'PATIENT SETUP'},

            # Ward Management
            {'key': 'ward', 'label': 'Ward Module Access', 'section': 'WARD MANAGEMENT'},
            {'key': 'ward_management', 'label': 'Ward Management', 'section': 'WARD MANAGEMENT'},
            {'key': 'ward_allocation', 'label': 'Ward Allocation', 'section': 'WARD MANAGEMENT'},
            {'key': 'ward_service_request', 'label': 'Ward Service Request', 'section': 'WARD MANAGEMENT'},
            {'key': 'ward_transfer', 'label': 'Ward Transfer (Internal)', 'section': 'WARD MANAGEMENT'},
            {'key': 'branch_transfer', 'label': 'Ward Transfer', 'section': 'WARD MANAGEMENT'},
            {'key': 'branch_transfer_report', 'label': 'Ward Transfer Report', 'section': 'WARD MANAGEMENT'},

            # Master Setup
            {'key': 'master', 'label': 'Master Module Access', 'section': 'MASTER MODULE'},
            {'key': 'master_departments', 'label': 'Hospital Departments', 'section': 'MASTER MODULE'},
            {'key': 'master_wards', 'label': 'Hospital Wards', 'section': 'MASTER MODULE'},
            {'key': 'master_investigations', 'label': 'Investigations', 'section': 'MASTER MODULE'},
            {'key': 'master_parameters', 'label': 'Parameters', 'section': 'MASTER MODULE'},
            {'key': 'lab_master', 'label': 'Lab Master Access', 'section': 'MASTER MODULE'},
            {'key': 'lab_master_dashboard', 'label': 'Lab Dashboard', 'section': 'MASTER MODULE'},
            {'key': 'lab_sub_departments', 'label': 'Lab Sub Departments', 'section': 'MASTER MODULE'},
            {'key': 'investigation_parameter_mapping', 'label': 'Investigation Mapping', 'section': 'MASTER MODULE'},
            {'key': 'workload_mapping_list', 'label': 'Workload Mapping', 'section': 'MASTER MODULE'},
            {'key': 'mapping_validation', 'label': 'Mapping Validation', 'section': 'MASTER MODULE'},
            {'key': 'legacy_mapping', 'label': 'Universal Import / Export', 'section': 'MASTER MODULE'},
            {'key': 'import_lab_workload_csv', 'label': 'Workload Import', 'section': 'MASTER MODULE'},
            {'key': 'export_lab_workload_csv', 'label': 'Workload Export', 'section': 'MASTER MODULE'},

            # Consultant
            {'key': 'consultant', 'label': 'Consultant Module Access', 'section': 'CONSULTANT'},
            {'key': 'doctor_window', 'label': 'Doctor Window', 'section': 'CONSULTANT'},
            {'key': 'service_request_add', 'label': 'Service Request', 'section': 'CONSULTANT'},

            # Lab Orders
            {'key': 'lab_orders', 'label': 'Lab Orders Module Access', 'section': 'LAB ORDERS'},
            {'key': 'work_orders', 'label': 'Work Orders', 'section': 'LAB ORDERS'},
            {'key': 'order_entry', 'label': 'New Order Entry', 'section': 'LAB ORDERS'},
            {'key': 'result_entry_list', 'label': 'Result Entry', 'section': 'LAB ORDERS'},

            # Lab Reports
            {'key': 'lab_reports', 'label': 'Lab Reports Module Access', 'section': 'LAB REPORTS'},
            {'key': 'report_dashboard', 'label': 'Reports Dashboard', 'section': 'LAB REPORTS'},
            {'key': 'report_daily', 'label': 'Daily Report', 'section': 'LAB REPORTS'},
            {'key': 'report_monthly', 'label': 'Monthly Report', 'section': 'LAB REPORTS'},
            {'key': 'report_sub_department', 'label': 'Sub Department Report', 'section': 'LAB REPORTS'},
            {'key': 'report_investigation', 'label': 'Investigation Report', 'section': 'LAB REPORTS'},
            {'key': 'report_hospital_department', 'label': 'Hospital Department-wise Report', 'section': 'LAB REPORTS'},
            {'key': 'report_benchmark', 'label': 'Benchmark Report', 'section': 'LAB REPORTS'},
            {'key': 'report_abnormal', 'label': 'Abnormal Result Report', 'section': 'LAB REPORTS'},

            # Auto Trigger
            {'key': 'auto_trigger', 'label': 'Auto Trigger Module Access', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_configuration', 'label': 'Auto Trigger Configuration', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_history', 'label': 'Auto Trigger History', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_monthly_create', 'label': 'Monthly Trigger', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_monthly', 'label': 'Monthly Trigger History', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_monthly_census', 'label': 'Monthly Census', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_automate_test', 'label': 'Automate Test', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_result_view', 'label': 'Result View', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_atc', 'label': 'ATC Control', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_atc_status', 'label': 'ATC Live Status', 'section': 'AUTO TRIGGER'},
            {'key': 'auto_trigger_atc_settings', 'label': 'ATC Settings', 'section': 'AUTO TRIGGER'},

            # OT
            {'key': 'ot', 'label': 'OT Module Access', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_dashboard', 'label': 'OT Dashboard', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_booking', 'label': 'OT Booking', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_schedule', 'label': 'OT Schedule', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_live', 'label': 'Live OT', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_history', 'label': 'OT History', 'section': 'OPERATION THEATRE (OT)'},
            {'key': 'ot_master', 'label': 'OT Master', 'section': 'OPERATION THEATRE (OT)'},

            # System Administration
            {'key': 'system_section', 'label': 'Administration Access', 'section': 'SYSTEM ADMINISTRATION'},
            {'key': 'administration', 'label': 'User Accounts Directory', 'section': 'SYSTEM ADMINISTRATION'},
            {'key': 'users_roles', 'label': 'Users & Roles Matrix', 'section': 'SYSTEM ADMINISTRATION'},
            {'key': 'inventory', 'label': 'Inventory Management', 'section': 'SYSTEM ADMINISTRATION'},
            {'key': 'settings', 'label': 'System Settings', 'section': 'SYSTEM ADMINISTRATION'},
        ]

    def get(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role == User.Roles.ADMIN):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        menus = self.get_menu_definitions()
        roles = [
            {'code': User.Roles.ADMIN, 'label': 'Administrator', 'is_locked': True},
            {'code': User.Roles.MANAGER, 'label': 'Department Manager', 'is_locked': False},
            {'code': User.Roles.STAFF, 'label': 'Staff Member', 'is_locked': False},
            {'code': User.Roles.AUDITOR, 'label': 'Auditor', 'is_locked': False},
        ]
        for cr in CustomRole.objects.all():
            roles.append({'code': cr.code, 'label': cr.name, 'is_locked': False})

        matrix = []
        for menu in menus:
            m_key = menu['key']
            row = {
                'key': m_key,
                'label': menu['label'],
                'section': menu['section'],
                'role_perms': []
            }
            for role in roles:
                r_code = role['code']
                if r_code == User.Roles.ADMIN:
                    is_granted = True
                else:
                    temp_user = User(role=r_code)
                    is_granted = temp_user.can_access_menu(m_key)
                row['role_perms'].append({
                    'role_code': r_code,
                    'is_locked': role['is_locked'],
                    'is_granted': is_granted
                })
            matrix.append(row)

        context = {
            'menus': menus,
            'roles': roles,
            'matrix': matrix,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role == User.Roles.ADMIN):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        menus = self.get_menu_definitions()
        target_roles = [User.Roles.MANAGER, User.Roles.STAFF, User.Roles.AUDITOR] + list(CustomRole.objects.values_list('code', flat=True))

        for r_code in target_roles:
            perms_dict = {}
            for menu in menus:
                m_key = menu['key']
                field_name = f"perm_{r_code}_{m_key}"
                perms_dict[m_key] = field_name in request.POST

            obj, created = RoleMenuPermission.objects.get_or_create(role=r_code)
            existing = obj.menu_permissions if isinstance(obj.menu_permissions, dict) else {}
            existing.update(perms_dict)
            obj.menu_permissions = existing
            obj.save()

        messages.success(request, "Role & Sidebar Menu Access Mapping permissions updated successfully!")
        return redirect('users:role_permissions')


class RoleOverviewView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    menu_key = 'users_roles'
    template_name = 'users/roles_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles_info = [
            {
                'code': User.Roles.ADMIN,
                'label': 'Administrator',
                'badge_class': 'badge-purple',
                'icon': 'bi-shield-lock-fill',
                'color': '#8b5cf6',
                'description': 'Full system control, user account creation, role matrix configuration, and system parameters.',
                'user_count': User.objects.filter(models.Q(role=User.Roles.ADMIN) | models.Q(is_superuser=True)).distinct().count(),
                'features': ['All ERP Modules', 'User Directory', 'Role Access Matrix', 'System Settings']
            },
            {
                'code': User.Roles.MANAGER,
                'label': 'Department Manager',
                'badge_class': 'badge-blue',
                'icon': 'bi-diagram-3-fill',
                'color': '#0284c7',
                'description': 'Department oversight, patient registration, setup of departments, units, companies, and inventory.',
                'user_count': User.objects.filter(role=User.Roles.MANAGER).count(),
                'features': ['Patients Management', 'Departments & Units', 'Companies Setup', 'Inventory']
            },
            {
                'code': User.Roles.STAFF,
                'label': 'Staff Member',
                'badge_class': 'badge-green',
                'icon': 'bi-people-fill',
                'color': '#10b981',
                'description': 'Front-desk operations, patient registration, search, and OP slip printing.',
                'user_count': User.objects.filter(role=User.Roles.STAFF).count(),
                'features': ['Add Patient', 'Search Patient', 'Patient Directory', 'Print OP Slips']
            },
            {
                'code': User.Roles.AUDITOR,
                'label': 'Auditor',
                'badge_class': 'badge-yellow',
                'icon': 'bi-eye-fill',
                'color': '#f59e0b',
                'description': 'Operational view-only access to patient records, companies, and department reports.',
                'user_count': User.objects.filter(role=User.Roles.AUDITOR).count(),
                'features': ['Search Patient (Read)', 'Patient Directory', 'Companies (Read)', 'Departments (Read)']
            },
        ]
        for cr in CustomRole.objects.all():
            roles_info.append({
                'code': cr.code,
                'label': cr.name,
                'badge_class': cr.badge_class or 'badge-blue',
                'icon': cr.icon or 'bi-person-badge-fill',
                'color': cr.color or '#0284c7',
                'description': cr.description or f"Custom role profile for {cr.name}.",
                'user_count': User.objects.filter(role=cr.code).count(),
                'features': ['Custom Permissions', 'Patient Operations']
            })
        context['roles'] = roles_info
        return context

class ProfilePermissionsView(LoginRequiredMixin, MenuAccessRequiredMixin, View):
    menu_key = 'users_roles'
    template_name = 'users/profile_permissions.html'

    def get(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role == User.Roles.ADMIN):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')
        
        roles = [
            {'code': User.Roles.ADMIN, 'label': 'Administrator', 'is_locked': True},
            {'code': User.Roles.MANAGER, 'label': 'Department Manager', 'is_locked': False},
            {'code': User.Roles.STAFF, 'label': 'Staff Member', 'is_locked': False},
            {'code': User.Roles.AUDITOR, 'label': 'Auditor', 'is_locked': False},
        ]
        for cr in CustomRole.objects.all():
            roles.append({'code': cr.code, 'label': cr.name, 'is_locked': False})
            
        selected_role = request.GET.get('role', '')
        if not selected_role and roles:
            selected_role = roles[1]['code'] # Select the first non-admin role by default

        current_perms = {}
        if selected_role != User.Roles.ADMIN:
            perm_obj = RoleMenuPermission.objects.filter(role=selected_role).first()
            if perm_obj and isinstance(perm_obj.menu_permissions, dict):
                current_perms = perm_obj.menu_permissions
                
        context = {
            'modules': PERMISSION_MODULES,
            'roles': roles,
            'selected_role': selected_role,
            'current_perms': current_perms,
            'actions_list': ['view', 'create', 'update', 'cancel', 'delete', 'export']
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role == User.Roles.ADMIN):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        selected_role = request.POST.get('role')
        if not selected_role or selected_role == User.Roles.ADMIN:
            messages.error(request, "Invalid or locked profile selected.")
            return redirect('users:profile_permissions')
        
        obj, created = RoleMenuPermission.objects.get_or_create(role=selected_role)
        existing_perms = obj.menu_permissions if isinstance(obj.menu_permissions, dict) else {}
        
        for mod in PERMISSION_MODULES:
            for sub in mod['sub_modules']:
                for action in sub['actions']:
                    perm_key = f"{sub['code']}.{action}"
                    post_key = f"perm_{perm_key}"
                    if post_key in request.POST:
                        existing_perms[perm_key] = True
                    else:
                        existing_perms[perm_key] = False
                        
        obj.menu_permissions = existing_perms
        obj.save()

        messages.success(request, f"Permissions saved successfully for profile.")
        return redirect(f"{reverse_lazy('users:profile_permissions')}?role={selected_role}")

