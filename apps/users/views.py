from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login as auth_login, logout as auth_logout
from django.db import models
from .forms import UserCreationCustomForm, UserEditCustomForm, UserLoginForm, CustomRoleForm, LandingDepartmentForm
from .models import RoleMenuPermission, CustomRole, NavModule, NavSubmodule, LandingDepartment
from .permissions import PERMISSION_MODULES
from .departments import (
    get_all_departments, get_department_by_slug, get_department_by_code,
    user_can_access_department, get_all_system_roles, get_role_by_slug,
    user_can_access_role, seed_default_landing_departments_if_needed
)

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


class DepartmentSelectView(View):
    """
    First Screen: Select Department or System Role to Login.
    Displays all 16 ERP core departments and all dynamic User System Roles.
    """
    def get(self, request):
        if request.user.is_authenticated:
            active_dept_code = request.session.get('active_department')
            if active_dept_code:
                dept = get_department_by_code(active_dept_code)
                if dept:
                    return redirect(dept.get('dashboard_url', '/dashboard/'))
            return redirect(get_default_landing_url(request.user))

        departments = get_all_departments()
        roles = get_all_system_roles()
        active_view = request.GET.get('view', 'departments')
        if active_view not in ['departments', 'roles']:
            active_view = 'departments'

        return render(request, 'users/department_select.html', {
            'departments': departments,
            'roles': roles,
            'active_view': active_view,
        })


class DepartmentLoginView(View):
    """
    Second Screen: Department-Specific Login Screen.
    Enforces user credentials validation and department authorization.
    """
    def get(self, request, dept_slug=None):
        dept_slug = dept_slug or request.GET.get('dept')
        dept = get_department_by_slug(dept_slug)
        if not dept:
            messages.warning(request, "Please select a valid department to login.")
            return redirect('login')

        if request.user.is_authenticated:
            if user_can_access_department(request.user, dept):
                request.session['active_department'] = dept['code']
                request.session['active_department_name'] = dept['name']
                request.session['active_department_slug'] = dept['slug']
                return redirect(dept.get('dashboard_url', '/dashboard/'))

        return render(request, 'users/dept_login.html', {
            'department': dept,
            'next': request.GET.get('next', ''),
        })

    def post(self, request, dept_slug=None):
        dept_slug = dept_slug or request.POST.get('department_slug') or request.GET.get('dept')
        dept = get_department_by_slug(dept_slug)
        if not dept:
            messages.error(request, "Invalid department specified.")
            return redirect('login')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '').strip()

        if not username or not password:
            return render(request, 'users/dept_login.html', {
                'department': dept,
                'error_message': "Please enter both username and password.",
                'username': username,
                'next': next_url,
            })

        user = authenticate(request, username=username, password=password)

        if user is None:
            # Check if user exists but is inactive
            inactive_user = User.objects.filter(username__iexact=username, is_active=False).first()
            if inactive_user:
                error_msg = "Your account is inactive. Please contact the administrator."
            else:
                error_msg = "Invalid username or password."

            return render(request, 'users/dept_login.html', {
                'department': dept,
                'error_message': error_msg,
                'username': username,
                'next': next_url,
            })

        # User credentials verified! Now check department authorization:
        if not user_can_access_department(user, dept):
            error_msg = f"Access Denied. This user is not authorized to login to the {dept['name']} department."
            return render(request, 'users/dept_login.html', {
                'department': dept,
                'error_message': error_msg,
                'username': username,
                'next': next_url,
            })

        # Login successful and authorized!
        auth_login(request, user)
        request.session['active_department'] = dept['code']
        request.session['active_department_name'] = dept['name']
        request.session['active_department_slug'] = dept['slug']

        messages.success(request, f"Welcome {user.get_full_name() or user.username}! Successfully logged in to {dept['name']}.")

        if next_url and next_url != '/' and next_url != reverse_lazy('login'):
            from django.utils.http import url_has_allowed_host_and_scheme
            if url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

        return redirect(dept.get('dashboard_url', '/dashboard/'))


class RoleLoginView(View):
    """
    Role-Specific Login Screen.
    Allows logging in directly with a specific system role profile.
    """
    def get(self, request, role_slug=None):
        role_slug = role_slug or request.GET.get('role')
        role_obj = get_role_by_slug(role_slug)
        if not role_obj:
            messages.warning(request, "Please select a valid role to login.")
            return redirect('login')

        if request.user.is_authenticated:
            if user_can_access_role(request.user, role_obj):
                return redirect(get_default_landing_url(request.user))

        return render(request, 'users/role_login.html', {
            'role_obj': role_obj,
            'next': request.GET.get('next', ''),
        })

    def post(self, request, role_slug=None):
        role_slug = role_slug or request.POST.get('role_slug') or request.GET.get('role')
        role_obj = get_role_by_slug(role_slug)
        if not role_obj:
            messages.error(request, "Invalid role specified.")
            return redirect('login')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '').strip()

        if not username or not password:
            return render(request, 'users/role_login.html', {
                'role_obj': role_obj,
                'error_message': "Please enter both username and password.",
                'username': username,
                'next': next_url,
            })

        user = authenticate(request, username=username, password=password)

        if user is None:
            inactive_user = User.objects.filter(username__iexact=username, is_active=False).first()
            if inactive_user:
                error_msg = "Your account is inactive. Please contact the administrator."
            else:
                error_msg = "Invalid username or password."

            return render(request, 'users/role_login.html', {
                'role_obj': role_obj,
                'error_message': error_msg,
                'username': username,
                'next': next_url,
            })

        if not user_can_access_role(user, role_obj):
            error_msg = f"Access Denied. This user account does not have the {role_obj['name']} role."
            return render(request, 'users/role_login.html', {
                'role_obj': role_obj,
                'error_message': error_msg,
                'username': username,
                'next': next_url,
            })

        auth_login(request, user)
        messages.success(request, f"Welcome {user.get_full_name() or user.username}! Successfully logged in as {role_obj['name']}.")

        if next_url and next_url != '/' and next_url != reverse_lazy('login'):
            from django.utils.http import url_has_allowed_host_and_scheme
            if url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

        return redirect(role_obj.get('dashboard_url') or get_default_landing_url(user))


# Legacy alias
ERPLoginView = DepartmentSelectView


class ERPLogoutView(View):
    """
    Logout view that destroys the authentication session, clears department context,
    and redirects to the Department Selection screen.
    """
    def get(self, request):
        return self.post(request)

    def post(self, request):
        if request.user.is_authenticated:
            auth_logout(request)
        request.session.flush()
        messages.info(request, "You have been logged out successfully.")
        return redirect('login')


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
        if not (request.user.is_superuser or request.user.is_admin_role):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        mode = request.GET.get('mode', 'granular')
        if mode not in ['granular', 'overview']:
            mode = 'granular'

        roles = [
            {'code': User.Roles.ADMIN, 'label': 'Administrator', 'is_locked': True, 'badge_class': 'badge-admin'},
            {'code': User.Roles.MANAGER, 'label': 'Department Manager', 'is_locked': False, 'badge_class': 'badge-manager'},
            {'code': User.Roles.STAFF, 'label': 'Staff Member', 'is_locked': False, 'badge_class': 'badge-staff'},
            {'code': User.Roles.AUDITOR, 'label': 'Auditor', 'is_locked': False, 'badge_class': 'badge-auditor'},
        ]
        for cr in CustomRole.objects.all():
            roles.append({'code': cr.code, 'label': cr.name, 'is_locked': False, 'badge_class': 'badge-custom'})

        selected_role = request.GET.get('role', '')
        if not selected_role and len(roles) > 1:
            selected_role = roles[1]['code']
        elif not selected_role:
            selected_role = User.Roles.ADMIN

        selected_role_obj = next((r for r in roles if r['code'] == selected_role), roles[0])

        # 1. Granular Modules and Submodules Data
        from .permissions import PERMISSION_MODULES
        role_db_perms = RoleMenuPermission.get_permissions_for_role(selected_role) or {}

        granular_modules = []
        total_actions_count = 0
        granted_actions_count = 0

        for mod in PERMISSION_MODULES:
            sub_items = []
            for sub in mod['sub_modules']:
                sub_code = sub['code']
                actions_list = sub.get('actions', [])
                
                # Check permissions
                def _is_granted(act):
                    if selected_role == User.Roles.ADMIN:
                        return True
                    # Check exact key e.g. patients.patient_list.update
                    k1 = f"{sub_code}.{act}"
                    k2 = f"{sub_code}_{act}"
                    k3 = f"{sub_code.replace('.', '_')}_{act}"
                    if act == 'view':
                        # View can also be granted if base code is granted
                        return role_db_perms.get(k1, role_db_perms.get(k2, role_db_perms.get(sub_code, role_db_perms.get(sub_code.replace('.', '_'), False))))
                    return bool(role_db_perms.get(k1, role_db_perms.get(k2, role_db_perms.get(k3, False))))

                has_view = 'view' in actions_list
                has_create = 'create' in actions_list
                has_update = 'update' in actions_list or 'edit' in actions_list
                has_delete = 'delete' in actions_list or 'cancel' in actions_list
                has_import = 'import' in actions_list
                has_export = 'export' in actions_list

                view_granted = _is_granted('view') if has_view else False
                create_granted = _is_granted('create') if has_create else False
                update_granted = _is_granted('update') if has_update else False
                delete_granted = _is_granted('delete') if has_delete else False
                import_granted = _is_granted('import') if has_import else False
                export_granted = _is_granted('export') if has_export else False

                if has_view:
                    total_actions_count += 1
                    if view_granted: granted_actions_count += 1
                if has_create:
                    total_actions_count += 1
                    if create_granted: granted_actions_count += 1
                if has_update:
                    total_actions_count += 1
                    if update_granted: granted_actions_count += 1
                if has_delete:
                    total_actions_count += 1
                    if delete_granted: granted_actions_count += 1
                if has_import:
                    total_actions_count += 1
                    if import_granted: granted_actions_count += 1
                if has_export:
                    total_actions_count += 1
                    if export_granted: granted_actions_count += 1

                sub_items.append({
                    'code': sub_code,
                    'label': sub['label'],
                    'description': sub.get('description', ''),
                    'has_view': has_view,
                    'has_create': has_create,
                    'has_update': has_update,
                    'has_delete': has_delete,
                    'has_import': has_import,
                    'has_export': has_export,
                    'view_granted': view_granted,
                    'create_granted': create_granted,
                    'update_granted': update_granted,
                    'delete_granted': delete_granted,
                    'import_granted': import_granted,
                    'export_granted': export_granted,
                })

            granular_modules.append({
                'module': mod['module'],
                'label': mod['label'],
                'icon': mod.get('icon', 'bi-folder2'),
                'sub_modules': sub_items,
            })

        # 2. Overview High-Level Matrix
        menus = self.get_menu_definitions()
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
            'mode': mode,
            'roles': roles,
            'selected_role': selected_role,
            'selected_role_obj': selected_role_obj,
            'granular_modules': granular_modules,
            'total_actions_count': total_actions_count,
            'granted_actions_count': granted_actions_count,
            'menus': menus,
            'matrix': matrix,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_admin_role):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        mode = request.POST.get('mode', 'granular')

        if mode == 'granular':
            selected_role = request.POST.get('role')
            if not selected_role or selected_role == User.Roles.ADMIN:
                messages.error(request, "Administrator role cannot be altered as it retains full access.")
                return redirect(f"{reverse_lazy('users:role_permissions')}?mode=granular&role={User.Roles.MANAGER}")

            from .permissions import PERMISSION_MODULES
            perms_dict = {}

            for mod in PERMISSION_MODULES:
                for sub in mod['sub_modules']:
                    sub_code = sub['code']
                    actions_list = sub.get('actions', [])

                    for act in ['view', 'create', 'update', 'delete', 'import', 'export']:
                        field_name = f"perm_{sub_code}_{act}"
                        is_checked = field_name in request.POST
                        if act in actions_list:
                            perms_dict[f"{sub_code}.{act}"] = is_checked
                            perms_dict[f"{sub_code}_{act}"] = is_checked
                            perms_dict[f"{sub_code.replace('.', '_')}_{act}"] = is_checked
                            if act == 'update':
                                perms_dict[f"{sub_code}.edit"] = is_checked
                                perms_dict[f"{sub_code}_edit"] = is_checked
                                perms_dict[f"{sub_code.replace('.', '_')}_edit"] = is_checked

                    # Also set base module key based on 'view' action
                    is_view_checked = f"perm_{sub_code}_view" in request.POST
                    perms_dict[sub_code] = is_view_checked
                    perms_dict[sub_code.replace('.', '_')] = is_view_checked

            obj, created = RoleMenuPermission.objects.get_or_create(role=selected_role)
            existing = obj.menu_permissions if isinstance(obj.menu_permissions, dict) else {}
            existing.update(perms_dict)
            obj.menu_permissions = existing
            obj.save()

            messages.success(request, f"Granular permissions (View, Create, Edit, Delete, Import, Export) for '{selected_role}' saved successfully!")
            return redirect(f"{reverse_lazy('users:role_permissions')}?mode=granular&role={selected_role}")

        else:
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
            return redirect(f"{reverse_lazy('users:role_permissions')}?mode=overview")


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


NAVBAR_MODULES_CONFIG = [
    {
        'id': 'dashboard',
        'key': 'dashboard',
        'name': 'Dashboard',
        'icon': 'bi-speedometer2',
        'color': '#0284c7',
        'badge': 'Core',
        'description': 'Main analytical overview, live counters, and operational statistics',
        'submodules': [
            {
                'key': 'dashboard',
                'name': 'Dashboard Overview',
                'icon': 'bi-speedometer2',
                'url': '/dashboard/',
                'description': 'Real-time hospital operations overview, bed occupancy, and today visits',
            },
        ]
    },
    {
        'id': 'patients',
        'key': 'patients',
        'name': 'Patients',
        'icon': 'bi-people-fill',
        'color': '#0ea5e9',
        'badge': 'OPD / IPD',
        'description': 'Patient registration, search directory, review consultations, and discharge marking',
        'submodules': [
            {
                'key': 'add_patient',
                'name': '+ Add Patient',
                'icon': 'bi-person-plus-fill',
                'url': '/patients/add/',
                'description': 'Register new outpatient / inpatient records with auto-generated UHID',
            },
            {
                'key': 'search_patient',
                'name': 'Search Patient',
                'icon': 'bi-search',
                'url': '/patients/search/',
                'description': 'Find patient records by UHID, patient name, or mobile number',
            },
            {
                'key': 'patient_list',
                'name': 'Patient List',
                'icon': 'bi-person-lines-fill',
                'url': '/patients/',
                'description': 'Complete searchable and filterable directory of all registered patients',
            },
            {
                'key': 'patient_import',
                'name': 'Patient Import',
                'icon': 'bi-cloud-arrow-up',
                'url': '/patients/import/',
                'description': 'Bulk upload historical patient records via CSV / Excel sheets',
            },
            {
                'key': 'review',
                'name': 'Patient Review',
                'icon': 'bi-clock-history',
                'url': '/patients/review/',
                'description': 'Schedule and conduct follow-up consultations and review notes',
            },
            {
                'key': 'discharge',
                'name': 'Discharge Marking',
                'icon': 'bi-box-arrow-right',
                'url': '/patients/discharge/',
                'description': 'Mark patient discharge readiness and generate final discharge summary',
            },
            {
                'key': 'patient_companies',
                'name': 'Patient Companies',
                'icon': 'bi-building',
                'url': '/patients/companies/',
                'description': 'Corporate affiliations, insurances, and empanelled organizations',
            },
            {
                'key': 'department_list',
                'name': 'Departments & Units',
                'icon': 'bi-diagram-3',
                'url': '/patients/departments/',
                'description': 'Configure hospital clinical departments and medical specialty units',
            },
        ]
    },
    {
        'id': 'ward',
        'key': 'ward',
        'name': 'Ward & Transfer',
        'icon': 'bi-hospital',
        'color': '#2563eb',
        'badge': 'Inpatient',
        'description': 'Ward bed matrix allocation, occupancy management, service requests, and patient transfers',
        'submodules': [
            {
                'key': 'ward_allocation',
                'name': 'Ward Allocation (Bed Matrix)',
                'icon': 'bi-grid-3x3-gap',
                'url': '/patients/ward/allocation/',
                'description': 'Live visual matrix of hospital ward beds, occupancy status, and admission slotting',
            },
            {
                'key': 'ward_management',
                'name': 'Ward Management',
                'icon': 'bi-building',
                'url': '/patients/wards/',
                'description': 'Setup hospital wards, bed capacities, room types, and nurse stations',
            },
            {
                'key': 'ward_service_request',
                'name': 'Ward Service Request',
                'icon': 'bi-clipboard-plus',
                'url': '/patients/ward/service-request/',
                'description': 'Order diagnostic tests, nursing care, and medication for admitted patients',
            },
            {
                'key': 'branch_transfer',
                'name': 'Ward Transfer',
                'icon': 'bi-arrow-left-right',
                'url': '/patients/branch-transfer/',
                'description': 'Transfer admitted patients between different wards or bed categories',
            },
            {
                'key': 'branch_transfer_report',
                'name': 'Ward Transfer Report',
                'icon': 'bi-file-earmark-bar-graph',
                'url': '/patients/branch-transfer/report/',
                'description': 'Audit trail and chronological reports of all inpatient movements',
            },
        ]
    },
    {
        'id': 'master',
        'key': 'master',
        'name': 'Master Settings',
        'icon': 'bi-sliders2',
        'color': '#4f46e5',
        'badge': 'Configuration',
        'description': 'Master datasets for clinical departments, investigations, parameters, reference ranges, and mappings',
        'submodules': [
            {
                'key': 'lab_master_dashboard',
                'name': 'Lab Master Hub',
                'icon': 'bi-grid-fill',
                'url': '/lab/master/hub/',
                'description': 'Central hub for laboratory master definitions and quick shortcuts',
            },
            {
                'key': 'master_departments',
                'name': 'Hospital Departments',
                'icon': 'bi-building',
                'url': '/patients/departments/',
                'description': 'Medical department records and administrative classifications',
            },
            {
                'key': 'lab_sub_departments',
                'name': 'Lab Departments',
                'icon': 'bi-building-gear',
                'url': '/lab/master/lab-departments/',
                'description': 'Sub-lab divisions (Biochemistry, Hematology, Microbiology, Histopathology)',
            },
            {
                'key': 'master_wards',
                'name': 'Hospital Wards',
                'icon': 'bi-hospital',
                'url': '/patients/wards/',
                'description': 'Inpatient ward master configurations and categorization',
            },
            {
                'key': 'master_investigations',
                'name': 'Investigations Master',
                'icon': 'bi-file-medical',
                'url': '/lab/master/investigations/',
                'description': 'Catalog of laboratory diagnostic tests, test codes, and specimen types',
            },
            {
                'key': 'master_parameters',
                'name': 'Parameters Master',
                'icon': 'bi-list-check',
                'url': '/lab/master/parameters/',
                'description': 'Observable parameters, units of measure, and default values',
            },
            {
                'key': 'investigation_parameter_mapping',
                'name': 'Investigation Parameters',
                'icon': 'bi-diagram-3',
                'url': '/lab/master/investigation-parameter-mapping/',
                'description': 'Associate parameters with investigation tests and define observation ordering',
            },
            {
                'key': 'master_reference_ranges',
                'name': 'Reference Ranges',
                'icon': 'bi-rulers',
                'url': '/lab/master/reference-ranges/',
                'description': 'Age and gender-specific biological normal reference intervals',
            },
            {
                'key': 'master_diagnosis_list',
                'name': 'Diagnoses Master',
                'icon': 'bi-clipboard2-pulse',
                'url': '/lab/master/diagnoses/',
                'description': 'Clinical diagnosis codes and disease definitions directory',
            },
            {
                'key': 'master_diagnosis_investigation_mapping',
                'name': 'Diagnosis -> Investigation',
                'icon': 'bi-arrow-left-right',
                'url': '/lab/master/diagnosis-investigation-mapping/',
                'description': 'Link clinical diagnoses to recommended diagnostic investigation panels',
            },
            {
                'key': 'master_diagnosis_department_mapping',
                'name': 'Diagnosis -> Department',
                'icon': 'bi-building',
                'url': '/lab/master/diagnosis-department-mapping/',
                'description': 'Assign diagnosis codes to primary hospital specialty departments',
            },
            {
                'key': 'master_age_groups',
                'name': 'Age Groups',
                'icon': 'bi-people',
                'url': '/lab/master/age-groups/',
                'description': 'Age group bracket classifications for physiological reference evaluation',
            },
            {
                'key': 'mapping_validation',
                'name': 'Master Validation',
                'icon': 'bi-shield-check',
                'url': '/lab/master/validation/',
                'description': 'Automated validation check for orphaned tests, missing ranges, or broken mappings',
            },
            {
                'key': 'legacy_mapping',
                'name': 'Universal Import / Export',
                'icon': 'bi-file-earmark-spreadsheet',
                'url': '/lab/legacy-mapping/',
                'description': 'Bulk master data import / export from legacy systems and spreadsheets',
            },
        ]
    },
    {
        'id': 'lab',
        'key': 'auto_trigger_section',
        'name': 'Laboratory',
        'icon': 'bi-robot',
        'color': '#7c3aed',
        'badge': 'Diagnostics',
        'description': 'Doctor window, test ordering, auto test synthesizers, and Automated Test Controller (ATC)',
        'submodules': [
            {
                'key': 'doctor_window',
                'name': 'Doctor Window',
                'icon': 'bi-window-desktop',
                'url': '/lab/doctor-window/',
                'description': 'Physician consultation portal for placing test orders and viewing findings',
            },
            {
                'key': 'service_request_add',
                'name': 'Service Request',
                'icon': 'bi-file-earmark-medical',
                'url': '/lab/service-request/add/',
                'description': 'Initiate diagnostic and specialty clinical test requests for patients',
            },
            {
                'key': 'auto_trigger_automate_test',
                'name': 'Create Dummy Result',
                'icon': 'bi-robot',
                'url': '/lab/auto-trigger/automate-test/',
                'description': 'Synthesize simulated laboratory result values within valid reference ranges',
            },
            {
                'key': 'auto_trigger_result_view',
                'name': 'Saved Dummy Results',
                'icon': 'bi-journal-check',
                'url': '/lab/auto-trigger/result-view/',
                'description': 'Review, verify, and inspect generated dummy test results database',
            },
            {
                'key': 'auto_trigger_configuration',
                'name': 'Auto Trigger Configuration',
                'icon': 'bi-sliders',
                'url': '/lab/auto-trigger/configuration/',
                'description': 'Set up automated background diagnostic trigger rules and schedules',
            },
            {
                'key': 'auto_trigger_history',
                'name': 'Auto Trigger History',
                'icon': 'bi-clock-history',
                'url': '/lab/auto-trigger/history/',
                'description': 'Audit log of past automated test generation executions and batch runs',
            },
            {
                'key': 'auto_trigger_monthly_create',
                'name': 'Monthly Trigger',
                'icon': 'bi-calendar-plus',
                'url': '/lab/auto-trigger/monthly-create/',
                'description': 'Batch generate monthly simulation workloads across departments',
            },
            {
                'key': 'auto_trigger_monthly',
                'name': 'Monthly Trigger History',
                'icon': 'bi-calendar-month',
                'url': '/lab/auto-trigger/monthly/',
                'description': 'Monthly simulation records, execution dates, and archive logs',
            },
            {
                'key': 'auto_trigger_monthly_census',
                'name': 'Monthly Census',
                'icon': 'bi-bar-chart',
                'url': '/lab/auto-trigger/monthly-census/',
                'description': 'Comprehensive monthly test volume census and department breakdowns',
            },
            {
                'key': 'auto_trigger_atc',
                'name': 'ATC Automation',
                'icon': 'bi-play-circle-fill',
                'url': '/lab/auto-trigger/atc/',
                'description': 'Direct control and manual initiation of Automated Test Controller daemon',
            },
            {
                'key': 'investigation_marking',
                'name': 'Investigation Marking',
                'icon': 'bi-flask',
                'url': '/lab/investigation-marking/',
                'description': 'Track specimen barcode scanning, collection, and technician sign-off',
            },
            {
                'key': 'auto_trigger_atc_status',
                'name': 'ATC Live Status',
                'icon': 'bi-activity',
                'url': '/lab/auto-trigger/atc-status/',
                'description': 'Real-time telemetry and process status of the background ATC engine',
            },
            {
                'key': 'auto_trigger_atc_settings',
                'name': 'ATC Settings',
                'icon': 'bi-gear',
                'url': '/lab/auto-trigger/atc-settings/',
                'description': 'Tuning execution intervals, concurrency limits, and threshold limits',
            },
        ]
    },
    {
        'id': 'billing',
        'key': 'lab_orders',
        'name': 'Billing',
        'icon': 'bi-receipt-cutoff',
        'color': '#059669',
        'badge': 'Revenue',
        'description': 'Work orders, diagnostic billing entries, manual result entry, and service request lists',
        'submodules': [
            {
                'key': 'work_orders',
                'name': 'Work Orders',
                'icon': 'bi-list-task',
                'url': '/lab/work-orders/',
                'description': 'Active laboratory order queue and specimen accession management',
            },
            {
                'key': 'order_entry',
                'name': 'New Lab Order',
                'icon': 'bi-plus-circle',
                'url': '/lab/order-entry/',
                'description': 'Create new diagnostic billing requisition and generate work order invoice',
            },
            {
                'key': 'result_entry_list',
                'name': 'Result Entry',
                'icon': 'bi-journal-text',
                'url': '/lab/result-entry/',
                'description': 'Technician portal to record, modify, and authorize patient lab test findings',
            },
            {
                'key': 'service_request_list',
                'name': 'Service Request List',
                'icon': 'bi-file-earmark-ruled',
                'url': '/lab/service-requests/',
                'description': 'Central list of diagnostic service requisitions awaiting processing',
            },
        ]
    },
    {
        'id': 'reports',
        'key': 'lab_reports',
        'name': 'Reports',
        'icon': 'bi-file-earmark-bar-graph-fill',
        'color': '#d97706',
        'badge': 'Analytics',
        'description': 'Operational and clinical reports, daily/monthly summaries, and abnormal findings alerts',
        'submodules': [
            {
                'key': 'report_dashboard',
                'name': 'Lab Reports Dashboard',
                'icon': 'bi-speedometer2',
                'url': '/lab/reports/',
                'description': 'Executive reporting dashboard with high-level summaries and diagnostic trends',
            },
            {
                'key': 'review_report',
                'name': 'Review Report',
                'icon': 'bi-file-earmark-text',
                'url': '/patients/reports/review/',
                'description': 'Summary report of patient review appointments and consultation volumes',
            },
            {
                'key': 'op_census',
                'name': 'OP Census Report',
                'icon': 'bi-graph-up',
                'url': '/patients/reports/op-census/',
                'description': 'Outpatient attendance metrics grouped by specialty, unit, and date range',
            },
            {
                'key': 'branch_transfer_report',
                'name': 'Ward Transfer Report',
                'icon': 'bi-arrow-left-right',
                'url': '/patients/branch-transfer/report/',
                'description': 'Detailed breakdown of inpatient bed and ward transfer activity',
            },
            {
                'key': 'report_daily',
                'name': 'Daily Report',
                'icon': 'bi-calendar-day',
                'url': '/lab/reports/daily/',
                'description': 'Day-wise detailed breakdown of diagnostic test orders and results',
            },
            {
                'key': 'report_monthly',
                'name': 'Monthly Report',
                'icon': 'bi-calendar-month',
                'url': '/lab/reports/monthly/',
                'description': 'Aggregated monthly workload volume and operational diagnostics',
            },
            {
                'key': 'report_sub_department',
                'name': 'Sub Department Report',
                'icon': 'bi-diagram-2',
                'url': '/lab/reports/sub-department/',
                'description': 'Workload volume grouped by laboratory sub-departments',
            },
            {
                'key': 'report_investigation',
                'name': 'Investigation Report',
                'icon': 'bi-file-medical',
                'url': '/lab/reports/investigation/',
                'description': 'Frequency and workload statistics by individual investigation tests',
            },
            {
                'key': 'report_hospital_department',
                'name': 'Hospital Dept Report',
                'icon': 'bi-building',
                'url': '/lab/reports/hospital-department/',
                'description': 'Diagnostic test orders categorized by requesting hospital department',
            },
            {
                'key': 'report_abnormal',
                'name': 'Abnormal Result Report',
                'icon': 'bi-exclamation-triangle',
                'url': '/lab/reports/abnormal/',
                'description': 'Critical and out-of-range laboratory test results requiring clinical follow-up',
            },
        ]
    },
    {
        'id': 'ot',
        'key': 'ot',
        'name': 'Operation Theatre',
        'icon': 'bi-scissors',
        'color': '#dc2626',
        'badge': 'Surgery',
        'description': 'OT dashboards, surgical bookings, slot schedules, live OT monitor, and surgical history',
        'submodules': [
            {
                'key': 'ot_dashboard',
                'name': 'OT Dashboard',
                'icon': 'bi-grid-1x2',
                'url': '/ot/',
                'description': 'Overview of surgical theatre utilization, upcoming cases, and team readiness',
            },
            {
                'key': 'ot_booking',
                'name': 'OT Booking',
                'icon': 'bi-calendar-plus',
                'url': '/ot/bookings/',
                'description': 'Schedule and register surgical procedure bookings for admitted patients',
            },
            {
                'key': 'ot_schedule',
                'name': 'OT Schedule',
                'icon': 'bi-calendar-week',
                'url': '/ot/schedule/',
                'description': 'Daily and weekly surgeon, theatre room, and anesthesiology slot timetable',
            },
            {
                'key': 'ot_live',
                'name': 'Live OT',
                'icon': 'bi-activity',
                'url': '/ot/live/',
                'description': 'Real-time surgical progression tracker across all active operation theatres',
            },
            {
                'key': 'ot_history',
                'name': 'OT History',
                'icon': 'bi-clock-history',
                'url': '/ot/history/',
                'description': 'Historical surgical registry, post-operative notes, and surgery outcomes',
            },
            {
                'key': 'ot_master',
                'name': 'OT Master',
                'icon': 'bi-database-gear',
                'url': '/ot/master/',
                'description': 'Master definitions for theatre rooms, anesthesia types, and surgical equipment',
            },
        ]
    },
    {
        'id': 'administration',
        'key': 'system_section',
        'name': 'Administration',
        'icon': 'bi-shield-shaded',
        'color': '#6b21a8',
        'badge': 'System',
        'description': 'User accounts directory, custom role profiles, navbar mapping, and access matrices',
        'submodules': [
            {
                'key': 'administration',
                'name': 'User Accounts',
                'icon': 'bi-person-gear',
                'url': '/users/',
                'description': 'Create, edit, reset passwords, and manage active system user accounts',
            },
            {
                'key': 'users_roles',
                'name': 'Users & Roles',
                'icon': 'bi-person-badge',
                'url': '/users/roles-overview/',
                'description': 'Overview and configuration of user roles, staff profiles, and security levels',
            },
            {
                'key': 'navbar_mapping',
                'name': 'Nav Bar Mapping',
                'icon': 'bi-diagram-3-fill',
                'url': '/users/navbar-mapping/',
                'description': 'Map and toggle top navigation bar modules and dropdown submodules per role',
            },
            {
                'key': 'landing_departments',
                'name': 'Landing Departments',
                'icon': 'bi-grid-1x2-fill',
                'url': '/administration/landing-departments/',
                'description': 'Create, edit, delete, and customize department login cards on the landing page',
            },
            {
                'key': 'role_permissions',
                'name': 'Role Access Matrix',
                'icon': 'bi-grid-3x3-gap-fill',
                'url': '/users/roles/access-matrix/',
                'description': 'Comprehensive security permissions and sidebar access control matrix',
            },
        ]
    },
    {
        'id': 'inventory',
        'key': 'inventory',
        'name': 'Inventory',
        'icon': 'bi-boxes',
        'color': '#0891b2',
        'badge': 'Supplies',
        'description': 'Pharmacy consumables, diagnostic reagent stocks, and hospital store inventory',
        'submodules': [
            {
                'key': 'inventory',
                'name': 'Stock Management',
                'icon': 'bi-box-seam',
                'url': '#',
                'description': 'Track reagent kits, hospital consumables, stock batch numbers, and reorder levels',
            },
        ]
    },
    {
        'id': 'settings',
        'key': 'settings',
        'name': 'Settings',
        'icon': 'bi-gear-fill',
        'color': '#475569',
        'badge': 'Config',
        'description': 'Hospital branding parameters, timestamps, timezone, and system preferences',
        'submodules': [
            {
                'key': 'settings',
                'name': 'System Configuration',
                'icon': 'bi-sliders',
                'url': '#',
                'description': 'General ERP parameters, hospital metadata, logo branding, and print formats',
            },
        ]
    },
]


DEPT_DEFAULT_NAV_MAPPING = {
    'front_desk': {
        'patients': True, 'add_patient': True, 'search_patient': True,
        'patient_list': True, 'op_census': True, 'patient_import': True,
        'department_list': True,
    },
    'consultant': {
        'consultant': True, 'doctor_window': True, 'service_request_add': True,
        'patients': True, 'search_patient': True, 'patient_list': True,
        'review': True, 'ward': True, 'branch_transfer': True,
    },
    'billing': {
        'billing': True, 'patients': True, 'search_patient': True, 'patient_list': True,
    },
    'lab': {
        'lab_orders': True, 'lab_work_orders': True, 'doctor_window': True,
        'lab_sub_departments': True, 'workload_mapping_list': True,
        'universal_master_import_export': True, 'lab_reports': True,
        'lab_reports_dashboard': True,
    },
    'ward': {
        'ward': True, 'ward_allocation': True, 'ward_management': True,
        'ward_service_request': True, 'ward_transfer': True,
        'branch_transfer': True, 'branch_transfer_report': True,
        'patients': True, 'patient_list': True,
    },
    'mrd': {
        'patients': True, 'review': True, 'discharge': True,
        'review_report': True, 'search_patient': True, 'patient_list': True,
    },
    'pharmacy': {
        'inventory': True, 'patients': True, 'search_patient': True,
    },
    'inventory': {
        'inventory': True,
    },
    'blood_bank': {
        'lab_orders': True, 'lab_work_orders': True, 'lab_reports': True,
    },
    'radiology': {
        'lab_orders': True, 'lab_work_orders': True, 'lab_reports': True,
    },
    'ot': {
        'ot_module': True, 'ot_booking': True, 'ot_schedule': True,
        'ot_live': True, 'ot_history': True, 'ot_master': True,
        'ward': True, 'ward_management': True,
    },
    'summary': {
        'patients': True, 'discharge': True, 'review': True, 'review_report': True,
    },
    'accounts': {
        'billing': True, 'lab_reports': True,
    },
    'report': {
        'lab_reports': True, 'lab_reports_dashboard': True,
        'patients': True, 'review_report': True, 'op_census': True,
    },
    'mis': {
        'dashboard': True, 'lab_reports': True, 'lab_reports_dashboard': True,
        'patients': True, 'op_census': True,
    },
    'clinical_department': {
        'patients': True, 'department_list': True, 'patient_list': True,
        'op_census': True, 'ward': True, 'ward_allocation': True,
    },
}


class NavBarMappingView(LoginRequiredMixin, MenuAccessRequiredMixin, View):
    menu_key = 'users_roles'
    template_name = 'users/navbar_mapping.html'

    def get_role_list(self):
        roles = [
            {'code': User.Roles.ADMIN, 'label': 'Administrator', 'badge_class': 'badge-admin', 'is_locked': True, 'desc': 'Full unrestricted access to all modules & submodules.'},
            {'code': User.Roles.MANAGER, 'label': 'Department Manager', 'badge_class': 'badge-manager', 'is_locked': False, 'desc': 'Manage operations, departmental patients, wards, and master setups.'},
            {'code': User.Roles.STAFF, 'label': 'Staff Member', 'badge_class': 'badge-staff', 'is_locked': False, 'desc': 'Front-desk operations, patient registration, and service orders.'},
            {'code': User.Roles.AUDITOR, 'label': 'Auditor', 'badge_class': 'badge-auditor', 'is_locked': False, 'desc': 'Read-only audit access to reports, patient lists, and master records.'},
        ]
        for cr in CustomRole.objects.all():
            roles.append({
                'code': cr.code,
                'label': cr.name,
                'badge_class': 'badge-custom',
                'is_locked': False,
                'desc': cr.description or f'Custom role profile for {cr.name}.'
            })
        return roles

    def get(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_admin_role):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        # Auto-seed Landing Departments if needed
        seed_default_landing_departments_if_needed()

        # Auto-seed NavModules if empty
        if NavModule.objects.count() == 0:
            for i, m in enumerate(NAVBAR_MODULES_CONFIG, 1):
                mod_obj, _ = NavModule.objects.update_or_create(
                    code=m['key'],
                    defaults={
                        'name': m['name'],
                        'icon': m['icon'],
                        'url_path': m['submodules'][0]['url'] if m['submodules'] else '#',
                        'color': m['color'],
                        'badge': m['badge'],
                        'description': m['description'],
                        'order': i * 10,
                        'is_active': True,
                        'is_system': True,
                    }
                )
                for j, s in enumerate(m['submodules'], 1):
                    NavSubmodule.objects.update_or_create(
                        code=s['key'],
                        defaults={
                            'module': mod_obj,
                            'name': s['name'],
                            'icon': s['icon'],
                            'url_path': s['url'],
                            'description': s['description'],
                            'order': j * 10,
                            'is_active': True,
                            'is_system': True,
                        }
                    )

        view_mode = request.GET.get('mode', 'department')
        if view_mode not in ['department', 'role']:
            view_mode = 'department'

        landing_departments = LandingDepartment.objects.all().order_by('order', 'id')
        roles = self.get_role_list()

        selected_dept = None
        selected_dept_id = request.GET.get('dept', '')
        selected_role = request.GET.get('role', '')

        current_perms = {}

        if view_mode == 'department':
            if selected_dept_id:
                if selected_dept_id.isdigit():
                    selected_dept = landing_departments.filter(id=int(selected_dept_id)).first()
                else:
                    selected_dept = landing_departments.filter(code=selected_dept_id).first()
            if not selected_dept:
                selected_dept = landing_departments.first()

            if selected_dept:
                if selected_dept.nav_permissions and isinstance(selected_dept.nav_permissions, dict):
                    current_perms = selected_dept.nav_permissions
                else:
                    # Smart defaults for this department
                    current_perms = DEPT_DEFAULT_NAV_MAPPING.get(selected_dept.code, {})
        else:
            if not selected_role and len(roles) > 1:
                selected_role = roles[1]['code']
            elif not selected_role:
                selected_role = User.Roles.ADMIN

            selected_role_obj = next((r for r in roles if r['code'] == selected_role), roles[0])

            if selected_role == User.Roles.ADMIN:
                for mod in NavModule.objects.all():
                    current_perms[mod.code] = True
                    for sub in mod.submodules.all():
                        current_perms[sub.code] = True
            else:
                temp_user = User(role=selected_role)
                current_perms = temp_user.get_menu_mapping()

        # Build structured modules list from DB
        all_modules = NavModule.objects.prefetch_related('submodules').order_by('order', 'id')
        total_submodules = 0
        enabled_submodules = 0
        modules_data = []

        is_admin_selected = (view_mode == 'role' and selected_role == User.Roles.ADMIN)

        for mod in all_modules:
            mod_submodules = []
            mod_enabled_count = 0
            for sub in mod.submodules.order_by('order', 'id'):
                total_submodules += 1
                is_granted = current_perms.get(sub.code, False) if not is_admin_selected else True
                if is_granted and sub.is_active:
                    enabled_submodules += 1
                    mod_enabled_count += 1
                mod_submodules.append({
                    'id': sub.id,
                    'key': sub.code,
                    'name': sub.name,
                    'icon': sub.icon,
                    'url': sub.url_path,
                    'description': sub.description or '',
                    'order': sub.order,
                    'is_active': sub.is_active,
                    'is_system': sub.is_system,
                    'is_granted': is_granted,
                })

            mod_key_granted = current_perms.get(mod.code, False) if not is_admin_selected else True
            modules_data.append({
                'id': mod.id,
                'key': mod.code,
                'name': mod.name,
                'icon': mod.icon,
                'url_path': mod.url_path,
                'color': mod.color,
                'badge': mod.badge or '',
                'description': mod.description or '',
                'order': mod.order,
                'is_active': mod.is_active,
                'is_system': mod.is_system,
                'is_granted': mod_key_granted or (mod_enabled_count > 0),
                'enabled_count': mod_enabled_count,
                'total_count': len(mod_submodules),
                'submodules': mod_submodules,
            })

        context = {
            'view_mode': view_mode,
            'landing_departments': landing_departments,
            'selected_dept': selected_dept,
            'roles': roles,
            'selected_role': selected_role,
            'selected_role_obj': next((r for r in roles if r['code'] == selected_role), roles[0]) if view_mode == 'role' else None,
            'modules': modules_data,
            'all_modules_list': all_modules,
            'total_modules': len(modules_data),
            'total_submodules': total_submodules,
            'enabled_submodules': enabled_submodules,
            'disabled_submodules': total_submodules - enabled_submodules,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_admin_role):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        view_mode = request.POST.get('view_mode', 'department')
        perms_dict = {}
        all_modules = NavModule.objects.prefetch_related('submodules').all()
        for mod in all_modules:
            mod_sub_active = False
            for sub in mod.submodules.all():
                sub_key = sub.code
                post_key = f"perm_{sub_key}"
                is_checked = post_key in request.POST
                perms_dict[sub_key] = is_checked
                if is_checked:
                    mod_sub_active = True

            mod_post_key = f"perm_mod_{mod.code}"
            perms_dict[mod.code] = mod_sub_active or (mod_post_key in request.POST)

        if view_mode == 'department':
            dept_id = request.POST.get('dept_id')
            dept = get_object_or_404(LandingDepartment, pk=dept_id)
            dept.nav_permissions = perms_dict
            dept.save()
            messages.success(request, f"Top Navigation Bar mapping for '{dept.name}' department saved successfully!")
            return redirect(f"{reverse_lazy('users:navbar_mapping')}?mode=department&dept={dept.id}")
        else:
            selected_role = request.POST.get('role')
            if not selected_role or selected_role == User.Roles.ADMIN:
                messages.error(request, "Administrator role cannot be altered as it retains full access.")
                return redirect(f"{reverse_lazy('users:navbar_mapping')}?mode=role&role={User.Roles.MANAGER}")

            obj, created = RoleMenuPermission.objects.get_or_create(role=selected_role)
            existing = obj.menu_permissions if isinstance(obj.menu_permissions, dict) else {}
            existing.update(perms_dict)
            obj.menu_permissions = existing
            obj.save()

            messages.success(request, f"Nav Bar Modules & Submodules mapping for '{selected_role}' saved successfully!")
            return redirect(f"{reverse_lazy('users:navbar_mapping')}?mode=role&role={selected_role}")



def nav_module_create(request):
    """Create a new top-level navigation module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_')
        icon = request.POST.get('icon', 'bi-folder2').strip()
        url_path = request.POST.get('url_path', '#').strip()
        color = request.POST.get('color', '#0284c7').strip()
        badge = request.POST.get('badge', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')

        if not name:
            messages.error(request, "Module name is required.")
            return redirect('users:navbar_mapping')

        if not code:
            code = name.lower().replace(' ', '_')

        # Ensure unique code
        base_code = code
        counter = 1
        while NavModule.objects.filter(code=code).exists():
            code = f"{base_code}_{counter}"
            counter += 1

        try:
            order_int = int(order)
        except ValueError:
            order_int = 10

        NavModule.objects.create(
            name=name,
            code=code,
            icon=icon,
            url_path=url_path,
            color=color,
            badge=badge,
            description=description,
            order=order_int,
            is_active=True,
            is_system=False,
        )
        messages.success(request, f"Navigation Module '{name}' created successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_module_edit(request, pk):
    """Edit an existing navigation module's details."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        icon = request.POST.get('icon', '').strip()
        url_path = request.POST.get('url_path', '#').strip()
        color = request.POST.get('color', '#0284c7').strip()
        badge = request.POST.get('badge', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')
        is_active = request.POST.get('is_active') == 'on'

        if name:
            module.name = name
        if icon:
            module.icon = icon
        module.url_path = url_path
        module.color = color
        module.badge = badge
        module.description = description
        module.is_active = is_active
        try:
            module.order = int(order)
        except ValueError:
            pass

        module.save()
        messages.success(request, f"Module '{module.name}' updated successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_module_rename(request, pk):
    """Quickly rename a top-level module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
                return JsonResponse({'success': False, 'error': 'Module name cannot be blank.'}, status=400)
            messages.error(request, "Module name cannot be blank.")
            return redirect('users:navbar_mapping')

        module.name = name
        module.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': True, 'name': module.name, 'id': module.id})

        messages.success(request, f"Module renamed to '{module.name}' successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_module_delete(request, pk):
    """Remove a navigation module and its submodules."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    name = module.name
    module.delete()
    messages.success(request, f"Navigation Module '{name}' and its submodules have been removed.")

    role = request.GET.get('role', '') or request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_submodule_create(request):
    """Create a new submodule under a specified parent module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_')
        icon = request.POST.get('icon', 'bi-dot').strip()
        url_path = request.POST.get('url_path', '#').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')

        if not name:
            messages.error(request, "Submodule name is required.")
            return redirect('users:navbar_mapping')

        parent_module = get_object_or_404(NavModule, pk=module_id)
        if not code:
            code = f"{parent_module.code}_{name.lower().replace(' ', '_')}"

        base_code = code
        counter = 1
        while NavSubmodule.objects.filter(code=code).exists():
            code = f"{base_code}_{counter}"
            counter += 1

        try:
            order_int = int(order)
        except ValueError:
            order_int = 10

        NavSubmodule.objects.create(
            module=parent_module,
            name=name,
            code=code,
            icon=icon,
            url_path=url_path,
            description=description,
            order=order_int,
            is_active=True,
            is_system=False,
        )
        messages.success(request, f"Submodule '{name}' added under '{parent_module.name}' successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_submodule_edit(request, pk):
    """Edit an existing submodule's details."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        icon = request.POST.get('icon', '').strip()
        url_path = request.POST.get('url_path', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')
        is_active = request.POST.get('is_active') == 'on'

        if name:
            submodule.name = name
        if icon:
            submodule.icon = icon
        if url_path:
            submodule.url_path = url_path
        submodule.description = description
        submodule.is_active = is_active
        try:
            submodule.order = int(order)
        except ValueError:
            pass

        submodule.save()
        messages.success(request, f"Submodule '{submodule.name}' updated successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_submodule_rename(request, pk):
    """Quickly rename a submodule name."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
                return JsonResponse({'success': False, 'error': 'Submodule name cannot be blank.'}, status=400)
            messages.error(request, "Submodule name cannot be blank.")
            return redirect('users:navbar_mapping')

        submodule.name = name
        submodule.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': True, 'name': submodule.name, 'id': submodule.id})

        messages.success(request, f"Submodule renamed to '{submodule.name}' successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_submodule_remap(request, pk):
    """Remap / move a submodule to a different parent module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    if request.method == 'POST':
        target_module_id = request.POST.get('target_module_id')
        new_parent = get_object_or_404(NavModule, pk=target_module_id)
        old_parent_name = submodule.module.name
        submodule.module = new_parent
        submodule.save()
        messages.success(request, f"Submodule '{submodule.name}' moved from '{old_parent_name}' to '{new_parent.name}' successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_submodule_delete(request, pk):
    """Delete a submodule."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    name = submodule.name
    submodule.delete()
    messages.success(request, f"Submodule '{name}' deleted successfully!")

    role = request.GET.get('role', '') or request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


def nav_reset_defaults(request):
    """Restore default system navigation modules and submodules."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        NavSubmodule.objects.all().delete()
        NavModule.objects.all().delete()

        for i, m in enumerate(NAVBAR_MODULES_CONFIG, 1):
            mod_obj = NavModule.objects.create(
                code=m['key'],
                name=m['name'],
                icon=m['icon'],
                url_path=m['submodules'][0]['url'] if m['submodules'] else '#',
                color=m['color'],
                badge=m['badge'],
                description=m['description'],
                order=i * 10,
                is_active=True,
                is_system=True,
            )
            for j, s in enumerate(m['submodules'], 1):
                NavSubmodule.objects.create(
                    module=mod_obj,
                    code=s['key'],
                    name=s['name'],
                    icon=s['icon'],
                    url_path=s['url'],
                    description=s['description'],
                    order=j * 10,
                    is_active=True,
                    is_system=True,
                )
        messages.success(request, "Navigation hierarchy reset to factory system defaults successfully!")

    role = request.POST.get('role', '')
    url = reverse_lazy('users:navbar_mapping')
    return redirect(f"{url}?role={role}" if role else url)


# =========================================================================
# LANDING PAGE DEPARTMENTS MANAGEMENT (ADMINISTRATOR MODULE)
# =========================================================================

class LandingDepartmentManagerView(LoginRequiredMixin, View):
    """
    Administrator Module Page: Manage Landing Page Department Cards.
    Enables creating, editing, deleting, ordering, and toggling departments for the landing login screen.
    """
    def get(self, request):
        if not (request.user.is_superuser or request.user.is_admin_role):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        # Ensure defaults are seeded
        seed_default_landing_departments_if_needed()

        search_query = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', 'all')

        qs = LandingDepartment.objects.all().order_by('order', 'id')

        if search_query:
            qs = qs.filter(
                models.Q(name__icontains=search_query) |
                models.Q(code__icontains=search_query) |
                models.Q(slug__icontains=search_query) |
                models.Q(badge__icontains=search_query) |
                models.Q(description__icontains=search_query)
            )

        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)
        elif status_filter == 'system':
            qs = qs.filter(is_system=True)
        elif status_filter == 'custom':
            qs = qs.filter(is_system=False)

        all_depts = LandingDepartment.objects.all()
        stats = {
            'total': all_depts.count(),
            'active': all_depts.filter(is_active=True).count(),
            'inactive': all_depts.filter(is_active=False).count(),
            'system': all_depts.filter(is_system=True).count(),
            'custom': all_depts.filter(is_system=False).count(),
        }

        form = LandingDepartmentForm()

        popular_icons = [
            'bi-person-workspace', 'bi-person-badge', 'bi-currency-rupee', 'bi-funnel-fill',
            'bi-hospital', 'bi-file-earmark-medical-fill', 'bi-capsule', 'bi-box-seam-fill',
            'bi-droplet-fill', 'bi-lungs-fill', 'bi-scissors', 'bi-clipboard2-pulse-fill',
            'bi-cash-coin', 'bi-bar-chart-fill', 'bi-pie-chart-fill', 'bi-building-fill',
            'bi-heart-pulse-fill', 'bi-activity', 'bi-bandaid-fill', 'bi-prescription',
            'bi-shield-check', 'bi-shield-lock-fill', 'bi-cpu-fill', 'bi-gear-fill',
            'bi-person-fill-gear', 'bi-truck', 'bi-telephone-fill', 'bi-receipt-cutoff'
        ]

        color_palettes = [
            {'name': 'Sky Blue', 'bg': '#e0f2fe', 'icon': '#0284c7'},
            {'name': 'Emerald Green', 'bg': '#dcfce7', 'icon': '#16a34a'},
            {'name': 'Amber Gold', 'bg': '#fef3c7', 'icon': '#d97706'},
            {'name': 'Rose Pink', 'bg': '#ffe4e6', 'icon': '#e11d48'},
            {'name': 'Purple Violet', 'bg': '#f3e8ff', 'icon': '#9333ea'},
            {'name': 'Teal Cyan', 'bg': '#ccfbf1', 'icon': '#0d9488'},
            {'name': 'Indigo Blue', 'bg': '#dbeafe', 'icon': '#2563eb'},
            {'name': 'Orange Sunset', 'bg': '#ffedd5', 'icon': '#ea580c'},
            {'name': 'Crimson Red', 'bg': '#fee2e2', 'icon': '#dc2626'},
            {'name': 'Violet Purple', 'bg': '#ede9fe', 'icon': '#7c3aed'},
            {'name': 'Fuchsia Pink', 'bg': '#fae8ff', 'icon': '#c026d3'},
            {'name': 'Cyan Ocean', 'bg': '#cffafe', 'icon': '#0891b2'},
            {'name': 'Slate Gray', 'bg': '#f1f5f9', 'icon': '#475569'},
        ]

        return render(request, 'users/landing_departments.html', {
            'departments': qs,
            'stats': stats,
            'form': form,
            'popular_icons': popular_icons,
            'color_palettes': color_palettes,
            'search_query': search_query,
            'status_filter': status_filter,
            'total_count': stats['total'],
        })


def landing_department_create(request):
    """Create a new Landing Page Department."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        form = LandingDepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            msg = f"Department '{dept.name}' created and added to landing screen successfully!"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg, 'dept_id': dept.id})
            messages.success(request, msg)
            return redirect('users:landing_departments')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors, 'message': 'Please fix validation errors.'}, status=400)
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.title()}: {err}")
    return redirect('users:landing_departments')


def landing_department_edit(request, pk):
    """Edit an existing Landing Page Department."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    dept = get_object_or_404(LandingDepartment, pk=pk)

    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'id': dept.id,
            'name': dept.name,
            'slug': dept.slug,
            'code': dept.code,
            'icon': dept.icon,
            'color_bg': dept.color_bg,
            'color_icon': dept.color_icon,
            'badge': dept.badge or '',
            'dashboard_url': dept.dashboard_url,
            'landing_module': dept.landing_module or '',
            'allowed_prefixes': ", ".join(dept.allowed_prefixes) if isinstance(dept.allowed_prefixes, list) else str(dept.allowed_prefixes or ''),
            'aliases': ", ".join(dept.aliases) if isinstance(dept.aliases, list) else str(dept.aliases or ''),
            'order': dept.order,
            'is_active': dept.is_active,
            'is_system': dept.is_system,
            'description': dept.description or '',
        })

    if request.method == 'POST':
        form = LandingDepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            dept = form.save()
            msg = f"Department '{dept.name}' updated successfully!"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
            return redirect('users:landing_departments')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors, 'message': 'Please fix validation errors.'}, status=400)
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field.title()}: {err}")

    return redirect('users:landing_departments')


def landing_department_delete(request, pk):
    """Delete a Landing Page Department."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    dept = get_object_or_404(LandingDepartment, pk=pk)
    name = dept.name
    dept.delete()
    msg = f"Landing department '{name}' deleted successfully!"
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': msg})
    messages.success(request, msg)
    return redirect('users:landing_departments')


def landing_department_toggle_active(request, pk):
    """Quick AJAX toggle to enable/disable department card on landing page."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    dept = get_object_or_404(LandingDepartment, pk=pk)
    dept.is_active = not dept.is_active
    dept.save(update_fields=['is_active', 'updated_at'])
    status_str = "active & visible" if dept.is_active else "inactive & hidden"
    return JsonResponse({
        'success': True,
        'is_active': dept.is_active,
        'message': f"Department '{dept.name}' is now {status_str} on the landing page."
    })


def landing_department_reset_defaults(request):
    """Reset landing page departments to factory system defaults (16 departments)."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        from .departments import ERP_LOGIN_DEPARTMENTS
        LandingDepartment.objects.all().delete()
        for dept in ERP_LOGIN_DEPARTMENTS:
            LandingDepartment.objects.create(
                code=dept['code'],
                slug=dept['slug'],
                name=dept['name'],
                icon=dept['icon'],
                color_bg=dept['color_bg'],
                color_icon=dept['color_icon'],
                badge=dept['badge'],
                dashboard_url=dept['dashboard_url'],
                landing_module=dept.get('landing_module', ''),
                allowed_prefixes=dept.get('allowed_prefixes', []),
                aliases=dept.get('aliases', []),
                description=dept.get('description', ''),
                order=dept.get('id', 1) * 10,
                is_active=True,
                is_system=True,
            )
        messages.success(request, "Landing screen departments reset to factory system defaults successfully!")

    return redirect('users:landing_departments')




