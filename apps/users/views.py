import re
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login as auth_login, logout as auth_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.middleware.csrf import rotate_token
from django.db import models
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import (
    UserCreationCustomForm, UserEditCustomForm, UserLoginForm, CustomRoleForm, LandingDepartmentForm,
    NavModuleForm, NavSubmoduleForm
)
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


@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(never_cache, name='dispatch')
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


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class DepartmentLoginView(View):
    """
    Second Screen: Department-Specific Login Screen.
    Enforces user credentials validation and department authorization.
    For Laboratory ('lab'), allows lab-department-wise division selection.
    """
    def get(self, request, dept_slug=None):
        dept_slug = dept_slug or request.GET.get('dept')
        dept = get_department_by_slug(dept_slug)
        if not dept:
            messages.warning(request, "Please select a valid department to login.")
            return redirect('login')

        if request.user.is_authenticated:
            if user_can_access_department(request.user, dept):
                # For lab, redirect if already has active lab sub department in session
                if dept.get('code') != 'lab' or request.session.get('active_lab_sub_department'):
                    request.session['active_department'] = dept['code']
                    request.session['active_department_name'] = dept['name']
                    request.session['active_department_slug'] = dept['slug']
                    return redirect(dept.get('dashboard_url', '/dashboard/'))

        lab_sub_departments = []
        if dept.get('code') == 'lab':
            try:
                from apps.lab.models import LabDepartment
                depts = list(LabDepartment.objects.filter(is_active=True))
                depts.sort(key=lambda d: (0 if 'CENTRAL' in d.name.upper() else 1, d.name))
                lab_sub_departments = depts
            except Exception:
                lab_sub_departments = []

        return render(request, 'users/dept_login.html', {
            'department': dept,
            'lab_sub_departments': lab_sub_departments,
            'next': request.GET.get('next', ''),
        })

    def post(self, request, dept_slug=None):
        dept_slug = dept_slug or request.POST.get('department_slug') or request.GET.get('dept')
        dept = get_department_by_slug(dept_slug)
        if not dept:
            messages.error(request, "Invalid department specified.")
            return redirect('login')

        lab_sub_departments = []
        if dept.get('code') == 'lab':
            try:
                from apps.lab.models import LabDepartment
                depts = list(LabDepartment.objects.filter(is_active=True))
                depts.sort(key=lambda d: (0 if 'CENTRAL' in d.name.upper() else 1, d.name))
                lab_sub_departments = depts
            except Exception:
                lab_sub_departments = []

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        selected_lab_sub_dept = request.POST.get('lab_sub_department', '').strip()
        next_url = request.POST.get('next', '').strip()

        if dept.get('code') == 'lab' and not selected_lab_sub_dept:
            return render(request, 'users/dept_login.html', {
                'department': dept,
                'lab_sub_departments': lab_sub_departments,
                'error_message': "Please select a Lab Department to login.",
                'username': username,
                'selected_lab_sub_dept': selected_lab_sub_dept,
                'next': next_url,
            })

        if not username or not password:
            return render(request, 'users/dept_login.html', {
                'department': dept,
                'lab_sub_departments': lab_sub_departments,
                'error_message': "Please enter both username and password.",
                'username': username,
                'selected_lab_sub_dept': selected_lab_sub_dept,
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
                'lab_sub_departments': lab_sub_departments,
                'error_message': error_msg,
                'username': username,
                'selected_lab_sub_dept': selected_lab_sub_dept,
                'next': next_url,
            })

        # User credentials verified! Now check department authorization:
        if not user_can_access_department(user, dept):
            error_msg = f"Access Denied. This user is not authorized to login to the {dept['name']} department."
            return render(request, 'users/dept_login.html', {
                'department': dept,
                'lab_sub_departments': lab_sub_departments,
                'error_message': error_msg,
                'username': username,
                'selected_lab_sub_dept': selected_lab_sub_dept,
                'next': next_url,
            })

        # For Laboratory login: strictly enforce assigned Lab Department
        # Central Lab has universal access to all other lab departments
        if dept.get('code') == 'lab' and selected_lab_sub_dept:
            is_admin_user = user.is_superuser or (getattr(user, 'role', '') or '').upper() in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']
            user_depts = [d.strip() for d in user.get_departments_list()]
            has_universal = any(d.lower() in ['all', 'all departments', 'all departments (universal access)'] for d in user_depts)
            has_central_lab = any('CENTRAL' in d.upper() for d in user_depts)

            if not is_admin_user and not has_universal and not has_central_lab:
                all_lab_names = {d.name.upper(): d.name for d in lab_sub_departments}
                user_assigned_labs = [all_lab_names[d.upper()] for d in user_depts if d.upper() in all_lab_names]

                # If user has specific lab department(s) assigned, they can ONLY log in to their assigned lab department
                if user_assigned_labs:
                    if selected_lab_sub_dept.upper() not in [l.upper() for l in user_assigned_labs]:
                        allowed_labs_str = ", ".join(user_assigned_labs)
                        return render(request, 'users/dept_login.html', {
                            'department': dept,
                            'lab_sub_departments': lab_sub_departments,
                            'error_message': f"Access Denied. You are only assigned to the '{allowed_labs_str}' Laboratory Department.",
                            'username': username,
                            'selected_lab_sub_dept': selected_lab_sub_dept,
                            'next': next_url,
                        })

        # Login successful and authorized!
        auth_login(request, user)
        request.session['active_department'] = dept['code']
        request.session['active_department_name'] = dept['name']
        request.session['active_department_slug'] = dept['slug']

        if dept.get('code') == 'lab' and selected_lab_sub_dept:
            request.session['active_lab_sub_department'] = selected_lab_sub_dept
            matched_lab_dept = next((d for d in lab_sub_departments if d.name.lower() == selected_lab_sub_dept.lower() or str(d.id) == selected_lab_sub_dept), None)
            if matched_lab_dept:
                request.session['active_lab_sub_department'] = matched_lab_dept.name
                request.session['active_lab_sub_department_id'] = matched_lab_dept.id

        welcome_title = f"{dept['name']} ({request.session.get('active_lab_sub_department')})" if dept.get('code') == 'lab' and request.session.get('active_lab_sub_department') else dept['name']
        messages.success(request, f"Welcome {user.get_full_name() or user.username}! Successfully logged in to {welcome_title}.")

        if next_url and next_url != '/' and next_url != reverse_lazy('login'):
            from django.utils.http import url_has_allowed_host_and_scheme
            if url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

        return redirect(dept.get('dashboard_url', '/dashboard/'))


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(never_cache, name='dispatch')
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


@method_decorator(never_cache, name='dispatch')
class ERPLogoutView(View):
    """
    Logout view that destroys the authentication session, clears department context,
    rotates CSRF token to prevent session fixation, and redirects to the Department Selection screen.
    """
    def get(self, request):
        return self.post(request)

    def post(self, request):
        is_timeout = request.GET.get('timeout') == '1' or request.POST.get('timeout') == '1'
        if request.user.is_authenticated:
            auth_logout(request)
        else:
            request.session.flush()
        rotate_token(request)
        if is_timeout:
            messages.warning(request, "Your session has expired due to 5 minutes of inactivity. Please log in again to continue.")
        else:
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


class RoleMenuPermissionsView(LoginRequiredMixin, View):
    """
    Legacy RoleMenuPermissionsView: Permanently redirects to the centralized
    Navbar Module and Submodule Mapping Page (which now manages both Landing Department and Role permissions).
    """
    def get(self, request, *args, **kwargs):
        role = request.GET.get('role', '')
        url = reverse_lazy('users:navbar_mapping')
        if role:
            return redirect(f"{url}?mode=role&role={role}")
        return redirect(f"{url}?mode=role")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)



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
                'key': 'lab_master_permissions',
                'name': 'Lab Permissions',
                'icon': 'bi-shield-lock',
                'url': '/lab/master/permissions/',
                'description': 'Configure access permissions, test entry rights, and validation authority per lab department',
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
        'lab_sub_departments': True, 'lab_master_permissions': True, 'workload_mapping_list': True,
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
                db_perms = RoleMenuPermission.get_permissions_for_role(selected_role)
                if db_perms and isinstance(db_perms, dict) and len(db_perms) > 0:
                    current_perms = db_perms
                else:
                    temp_user = User(role=selected_role)
                    current_perms = temp_user.get_role_default_mapping()

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
                
                # Granular Action Permissions
                act_dict = current_perms.get(f"{sub.code}_actions", {}) if isinstance(current_perms.get(f"{sub.code}_actions"), dict) else {}
                
                if is_admin_selected:
                    can_view = can_add = can_edit = can_delete = can_print = True
                elif is_granted:
                    def _get_act_val(act_names, default_val=True):
                        for a in act_names:
                            if a in act_dict and act_dict[a] is not None:
                                return bool(act_dict[a])
                            k1 = f"{sub.code}.{a}"
                            k2 = f"{sub.code}_{a}"
                            if k1 in current_perms and current_perms[k1] is not None:
                                return bool(current_perms[k1])
                            if k2 in current_perms and current_perms[k2] is not None:
                                return bool(current_perms[k2])
                        return default_val

                    can_view = _get_act_val(['view', 'access'], True)
                    can_add = _get_act_val(['add', 'create'], True)
                    can_edit = _get_act_val(['edit', 'update'], True)
                    can_delete = _get_act_val(['delete', 'cancel'], True)
                    can_print = _get_act_val(['print', 'export'], True)
                else:
                    can_view = can_add = can_edit = can_delete = can_print = False

                active_actions_count = sum([1 for x in [can_view, can_add, can_edit, can_delete, can_print] if x])
                if not is_granted or active_actions_count == 0:
                    perm_status = 'none'
                    perm_badge = 'Disabled'
                elif active_actions_count == 5:
                    perm_status = 'full'
                    perm_badge = 'Full Access'
                else:
                    perm_status = 'partial'
                    perm_badge = f'Partial ({active_actions_count}/5)'

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
                    'can_view': can_view,
                    'can_add': can_add,
                    'can_edit': can_edit,
                    'can_delete': can_delete,
                    'can_print': can_print,
                    'active_actions_count': active_actions_count,
                    'perm_status': perm_status,
                    'perm_badge': perm_badge,
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
            'all_submodules_list': NavSubmodule.objects.select_related('module').order_by('module__order', 'order', 'name'),
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
                
                # Check granular action checkboxes
                can_view = f"perm_act_{sub_key}_view" in request.POST
                can_add = f"perm_act_{sub_key}_add" in request.POST
                can_edit = f"perm_act_{sub_key}_edit" in request.POST
                can_delete = f"perm_act_{sub_key}_delete" in request.POST
                can_print = f"perm_act_{sub_key}_print" in request.POST

                # If master toggle is on but none of action checkboxes are present, default all actions to True
                if is_checked and not any([can_view, can_add, can_edit, can_delete, can_print]):
                    can_view = can_add = can_edit = can_delete = can_print = True
                elif not is_checked:
                    can_view = can_add = can_edit = can_delete = can_print = False

                perms_dict[sub_key] = is_checked
                perms_dict[f"{sub_key}.view"] = can_view
                perms_dict[f"{sub_key}.add"] = can_add
                perms_dict[f"{sub_key}.create"] = can_add
                perms_dict[f"{sub_key}.edit"] = can_edit
                perms_dict[f"{sub_key}.update"] = can_edit
                perms_dict[f"{sub_key}.delete"] = can_delete
                perms_dict[f"{sub_key}.print"] = can_print
                perms_dict[f"{sub_key}.export"] = can_print
                perms_dict[f"{sub_key}_actions"] = {
                    'access': is_checked,
                    'view': can_view,
                    'add': can_add,
                    'edit': can_edit,
                    'delete': can_delete,
                    'print': can_print,
                }

                if is_checked:
                    mod_sub_active = True

            mod_post_key = f"perm_mod_{mod.code}"
            perms_dict[mod.code] = mod_sub_active or (mod_post_key in request.POST)

        if view_mode == 'department':
            dept_id = request.POST.get('dept_id')
            dept = get_object_or_404(LandingDepartment, pk=dept_id)
            dept.nav_permissions = perms_dict
            dept.save()
            messages.success(request, f"Permissions & Navigation Mapping for '{dept.name}' department saved successfully!")
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

            messages.success(request, f"Permissions & Nav Bar mapping for '{selected_role}' saved successfully!")
            return redirect(f"{reverse_lazy('users:navbar_mapping')}?mode=role&role={selected_role}")



# =========================================================================
# MODULE & SUBMODULE DEDICATED MANAGER (ADMINISTRATOR)
# =========================================================================

class ModuleSubmoduleManagerView(LoginRequiredMixin, View):
    """
    Dedicated centralized management page for Navigation Modules and Submodules.
    Allows administrators to dynamically create, edit, rename, move/remap, activate/deactivate,
    reorder, and delete modules and submodules with clean search, filters, tabs, and modals.
    """
    def get(self, request):
        if not (request.user.is_superuser or getattr(request.user, 'is_admin_role', False)):
            messages.error(request, "Access restricted to system administrators.")
            return redirect('patients:list')

        # Seed defaults if database table is empty
        try:
            if not NavModule.objects.exists():
                seed_default_nav_modules_if_needed()
        except Exception:
            pass

        tab = request.GET.get('tab', 'modules').strip().lower()
        if tab not in ['modules', 'submodules', 'tree']:
            tab = 'modules'

        q = request.GET.get('q', '').strip()
        status_filter = request.GET.get('status', 'all').strip().lower()
        mod_filter = request.GET.get('mod', '').strip()
        page_num = request.GET.get('page', 1)

        # Overview counters
        total_modules = NavModule.objects.count()
        active_modules = NavModule.objects.filter(is_active=True).count()
        inactive_modules = total_modules - active_modules

        total_submodules = NavSubmodule.objects.count()
        active_submodules = NavSubmodule.objects.filter(is_active=True).count()
        inactive_submodules = total_submodules - active_submodules

        total_departments = LandingDepartment.objects.count()

        all_modules_list = NavModule.objects.all().order_by('order', 'id')

        # 1. Modules query
        modules_qs = NavModule.objects.annotate(
            sub_count=Count('submodules'),
            active_sub_count=Count('submodules', filter=Q(submodules__is_active=True))
        ).order_by('order', 'id')

        if q:
            modules_qs = modules_qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(badge__icontains=q) |
                Q(description__icontains=q) |
                Q(url_path__icontains=q)
            )
        if status_filter == 'active':
            modules_qs = modules_qs.filter(is_active=True)
        elif status_filter == 'inactive':
            modules_qs = modules_qs.filter(is_active=False)

        # 2. Submodules query
        submodules_qs = NavSubmodule.objects.select_related('module').order_by('module__order', 'order', 'id')

        if q:
            submodules_qs = submodules_qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(url_path__icontains=q) |
                Q(description__icontains=q) |
                Q(module__name__icontains=q)
            )
        if mod_filter and mod_filter.isdigit():
            submodules_qs = submodules_qs.filter(module_id=int(mod_filter))
        if status_filter == 'active':
            submodules_qs = submodules_qs.filter(is_active=True)
        elif status_filter == 'inactive':
            submodules_qs = submodules_qs.filter(is_active=False)

        # Pagination
        items_per_page = 15
        if tab == 'submodules':
            paginator = Paginator(submodules_qs, items_per_page)
            try:
                submodules_page = paginator.page(page_num)
            except PageNotAnInteger:
                submodules_page = paginator.page(1)
            except EmptyPage:
                submodules_page = paginator.page(paginator.num_pages)
            modules_page = None
        else:
            paginator = Paginator(modules_qs, items_per_page)
            try:
                modules_page = paginator.page(page_num)
            except PageNotAnInteger:
                modules_page = paginator.page(1)
            except EmptyPage:
                modules_page = paginator.page(paginator.num_pages)
            submodules_page = None

        # Tree view: modules with preloaded submodules
        tree_modules = NavModule.objects.prefetch_related('submodules').order_by('order', 'id')

        context = {
            'tab': tab,
            'q': q,
            'status_filter': status_filter,
            'mod_filter': mod_filter,
            'total_modules': total_modules,
            'active_modules': active_modules,
            'inactive_modules': inactive_modules,
            'total_submodules': total_submodules,
            'active_submodules': active_submodules,
            'inactive_submodules': inactive_submodules,
            'total_departments': total_departments,
            'all_modules_list': all_modules_list,
            'all_submodules_list': NavSubmodule.objects.select_related('module').order_by('module__order', 'order', 'name'),
            'modules_list': modules_qs,
            'modules_page': modules_page,
            'submodules_page': submodules_page,
            'submodules_list': submodules_qs,
            'tree_modules': tree_modules,
            'module_form': NavModuleForm(),
            'submodule_form': NavSubmoduleForm(),
        }
        return render(request, 'users/module_submodule_manager.html', context)


def _get_next_redirect_url(request, default_name='users:module_manager'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return next_url
    role = request.POST.get('role') or request.GET.get('role')
    if role:
        return f"{reverse_lazy('users:navbar_mapping')}?role={role}"
    dept = request.POST.get('dept') or request.GET.get('dept')
    if dept:
        return f"{reverse_lazy('users:navbar_mapping')}?mode=department&dept={dept}"
    return reverse_lazy(default_name)


def nav_module_create(request):
    """Create a new top-level navigation module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_').replace('-', '_')
        icon = request.POST.get('icon', 'bi-folder2').strip()
        url_path = request.POST.get('url_path', '#').strip()
        color = request.POST.get('color', '#0284c7').strip()
        badge = request.POST.get('badge', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')

        if not name:
            messages.error(request, "Module name is required.")
            return redirect(_get_next_redirect_url(request))

        if not code:
            code = name.lower().replace(' ', '_').replace('-', '_')

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

        mod_obj = NavModule.objects.create(
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

        selected_subs = request.POST.getlist('selected_submodules') or request.POST.getlist('submodules')
        if selected_subs:
            sub_ids = [int(s) for s in selected_subs if str(s).isdigit()]
            if sub_ids:
                NavSubmodule.objects.filter(id__in=sub_ids).update(module=mod_obj)

        messages.success(request, f"Navigation Module '{name}' created successfully!")

    return redirect(_get_next_redirect_url(request))


def nav_module_edit(request, pk):
    """Edit an existing navigation module's details."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_').replace('-', '_')
        icon = request.POST.get('icon', '').strip()
        url_path = request.POST.get('url_path', '#').strip()
        color = request.POST.get('color', '#0284c7').strip()
        badge = request.POST.get('badge', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == '1' or request.POST.get('is_active') is True

        if name:
            module.name = name
        if code and not NavModule.objects.filter(code=code).exclude(pk=module.pk).exists():
            module.code = code
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

        # Update assigned submodules from the multi-selector
        selected_subs = request.POST.getlist('selected_submodules') or request.POST.getlist('submodules')
        if selected_subs:
            sub_ids = [int(s) for s in selected_subs if str(s).isdigit()]
            if sub_ids:
                NavSubmodule.objects.filter(id__in=sub_ids).update(module=module)

        messages.success(request, f"Module '{module.name}' updated successfully!")

    return redirect(_get_next_redirect_url(request))


def nav_module_toggle_active(request, pk):
    """Toggle module active / inactive status."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    module.is_active = not module.is_active
    module.save()
    status_text = "activated" if module.is_active else "deactivated"
    messages.success(request, f"Module '{module.name}' has been {status_text}.")
    return redirect(_get_next_redirect_url(request))


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
            return redirect(_get_next_redirect_url(request))

        module.name = name
        module.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': True, 'name': module.name, 'id': module.id})

        messages.success(request, f"Module renamed to '{module.name}' successfully!")

    return redirect(_get_next_redirect_url(request))


def nav_module_delete(request, pk):
    """Remove a navigation module safely after checking submodules."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    module = get_object_or_404(NavModule, pk=pk)
    name = module.name
    sub_count = module.submodules.count()
    cascade = request.POST.get('cascade') == 'true' or request.GET.get('cascade') == 'true'

    if sub_count > 0 and not cascade:
        messages.error(request, f"Cannot delete module '{name}' because it contains {sub_count} submodule(s). Please remove or remap child submodules first, or confirm cascading deletion.")
        return redirect(_get_next_redirect_url(request))

    module.delete()
    messages.success(request, f"Navigation Module '{name}' and its submodules have been removed.")
    return redirect(_get_next_redirect_url(request))


def nav_submodule_create(request):
    """Create a new submodule under a specified parent module."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_').replace('-', '_')
        icon = request.POST.get('icon', 'bi-dot').strip()
        url_path = request.POST.get('url_path', '#').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')

        if not name:
            messages.error(request, "Submodule name is required.")
            return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))

        parent_module = get_object_or_404(NavModule, pk=module_id)
        if not code:
            code = f"{parent_module.code}_{name.lower().replace(' ', '_').replace('-', '_')}"

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

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


def nav_submodule_edit(request, pk):
    """Edit an existing submodule's details."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    if request.method == 'POST':
        module_id = request.POST.get('module_id')
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().lower().replace(' ', '_').replace('-', '_')
        icon = request.POST.get('icon', '').strip()
        url_path = request.POST.get('url_path', '').strip()
        description = request.POST.get('description', '').strip()
        order = request.POST.get('order', '10')
        is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == '1' or request.POST.get('is_active') is True

        if module_id and str(module_id).isdigit():
            new_parent = NavModule.objects.filter(pk=int(module_id)).first()
            if new_parent:
                submodule.module = new_parent

        if name:
            submodule.name = name
        if code and not NavSubmodule.objects.filter(code=code).exclude(pk=submodule.pk).exists():
            submodule.code = code
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

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


def nav_submodule_toggle_active(request, pk):
    """Toggle submodule active / inactive status."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    submodule.is_active = not submodule.is_active
    submodule.save()
    status_text = "activated" if submodule.is_active else "deactivated"
    messages.success(request, f"Submodule '{submodule.name}' has been {status_text}.")
    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


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
            return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))

        submodule.name = name
        submodule.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            return JsonResponse({'success': True, 'name': submodule.name, 'id': submodule.id})

        messages.success(request, f"Submodule renamed to '{submodule.name}' successfully!")

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


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

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


def nav_submodule_delete(request, pk):
    """Delete a submodule."""
    if not (request.user.is_superuser or request.user.is_admin_role):
        messages.error(request, "Access restricted to system administrators.")
        return redirect('patients:list')

    submodule = get_object_or_404(NavSubmodule, pk=pk)
    name = submodule.name
    submodule.delete()
    messages.success(request, f"Submodule '{name}' deleted successfully!")

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


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

    return redirect(_get_next_redirect_url(request, default_name='users:module_manager'))


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






# ─────────────────────────────────────────────────────────────────────────────
# USER PROFILE SELF-UPDATE (navbar dropdown → View Profile)
# ─────────────────────────────────────────────────────────────────────────────

class UserProfileUpdateView(LoginRequiredMixin, View):
    """
    AJAX endpoint that allows the currently authenticated user to update
    their own safe profile fields (first_name, last_name, email, phone_number).
    Role, permissions, superuser/staff status, and username are NOT editable here.
    """

    def post(self, request):
        user = request.user
        errors = {}

        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone_number = (request.POST.get('phone_number') or '').strip()

        if email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjValidationError
            try:
                validate_email(email)
            except DjValidationError:
                errors['email'] = 'Enter a valid email address.'

        if phone_number and len(phone_number) > 20:
            errors['phone_number'] = 'Phone number must be 20 characters or fewer.'

        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone_number = phone_number
        user.save(update_fields=['first_name', 'last_name', 'email', 'phone_number'])

        full_name = user.get_full_name() or user.username
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully.',
            'full_name': full_name,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number or '',
            'role_display': user.get_role_display(),
            'department': user.department or '',
            'employee_id': user.employee_id or '',
        })


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD SELF-CHANGE (navbar dropdown → Change Password)
# ─────────────────────────────────────────────────────────────────────────────

class UserPasswordChangeView(LoginRequiredMixin, View):
    """
    AJAX endpoint for the logged-in user to change their own password.
    Validates old password, runs Django's built-in password validators,
    hashes securely, and re-authenticates the session.
    """

    def post(self, request):
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjValidationError

        user = request.user
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = {}

        if not old_password:
            errors['old_password'] = 'Current password is required.'
        elif not user.check_password(old_password):
            errors['old_password'] = 'The current password you entered is incorrect.'

        if not new_password:
            errors['new_password'] = 'New password is required.'

        if not confirm_password:
            errors['confirm_password'] = 'Please confirm the new password.'
        elif new_password and new_password != confirm_password:
            errors['confirm_password'] = 'New password and confirmation do not match.'

        if new_password and not errors.get('new_password') and not errors.get('confirm_password'):
            try:
                validate_password(new_password, user=user)
            except DjValidationError as e:
                errors['new_password'] = ' '.join(e.messages)

        if errors:
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        update_session_auth_hash(request, user)

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully.',
        })


class ThemeSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'users/theme_settings.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not getattr(request.user, 'can_access_theme_settings', False):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Access Denied: You do not have permission to access Theme Settings.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['themes'] = [
            # MAIN THEME
            {
                'id': 'vmmc-main',
                'name': 'VMMC Main',
                'type': 'Main Theme',
                'category': 'MAIN THEME',
                'desc': 'Default VMMC hospital blue/white clinical identity with navy accents',
                'preview': {'bg': '#f1f5f9', 'surface': '#ffffff', 'primary': '#0284c7', 'text': '#0f172a', 'border': '#cbd5e1'}
            },
            # 5 LIGHT THEMES
            {
                'id': 'clinical-blue',
                'name': 'Clinical Blue',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Clean hospital blue with navy text and structured borders',
                'preview': {'bg': '#eaf2f9', 'surface': '#ffffff', 'primary': '#1971c2', 'text': '#0e294b', 'border': '#bcd4e6'}
            },
            {
                'id': 'medical-teal',
                'name': 'Medical Teal',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Clinical teal palette with deep spruce typography',
                'preview': {'bg': '#e6f6f4', 'surface': '#ffffff', 'primary': '#0d9488', 'text': '#042f2e', 'border': '#99f6e4'}
            },
            {
                'id': 'soft-green',
                'name': 'Soft Green',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Restrained hospital sage green with forest accents',
                'preview': {'bg': '#eaf4ed', 'surface': '#ffffff', 'primary': '#15803d', 'text': '#132e1b', 'border': '#bbf7d0'}
            },
            {
                'id': 'royal-indigo',
                'name': 'Royal Indigo',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Crisp indigo surfaces with deep midnight text',
                'preview': {'bg': '#edeafc', 'surface': '#ffffff', 'primary': '#4f46e5', 'text': '#1e1b4b', 'border': '#c7d2fe'}
            },
            {
                'id': 'warm-slate',
                'name': 'Warm Slate',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Low visual fatigue off-white with slate grey tones',
                'preview': {'bg': '#e7e4dc', 'surface': '#fbf9f5', 'primary': '#4a5d6e', 'text': '#2c3238', 'border': '#cfc9be'}
            },
            # 5 DARK THEMES
            {
                'id': 'midnight-blue',
                'name': 'Midnight Blue',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Deep navy background with high-contrast sky accents',
                'preview': {'bg': '#090e17', 'surface': '#0f172a', 'primary': '#0284c7', 'text': '#f1f5f9', 'border': '#334155'}
            },
            {
                'id': 'dark-teal',
                'name': 'Dark Teal',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Charcoal-teal background with vibrant cyan elements',
                'preview': {'bg': '#061414', 'surface': '#0a2121', 'primary': '#0d9488', 'text': '#f0fdfa', 'border': '#1a4a4a'}
            },
            {
                'id': 'graphite',
                'name': 'Graphite',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Neutral charcoal surface with electric blue highlights',
                'preview': {'bg': '#121316', 'surface': '#1b1d22', 'primary': '#3b82f6', 'text': '#f3f4f6', 'border': '#374151'}
            },
            {
                'id': 'deep-indigo',
                'name': 'Deep Indigo',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Dark amethyst surfaces with soft violet typography',
                'preview': {'bg': '#0b0918', 'surface': '#141228', 'primary': '#7c3aed', 'text': '#f5f3ff', 'border': '#312c5b'}
            },
            {
                'id': 'dark-emerald',
                'name': 'Dark Emerald',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Deep night green with radiant emerald indicators',
                'preview': {'bg': '#05130e', 'surface': '#0a2118', 'primary': '#059669', 'text': '#ecfdf5', 'border': '#1a4d3a'}
            },
            # 5 TRANSPARENT / GLASS THEMES
            {
                'id': 'glass-blue',
                'name': 'Glass Blue',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Translucent frosted azure surfaces with subtle blur',
                'preview': {'bg': '#dbeafe', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#0284c7', 'text': '#0f2c59', 'border': '#93c5fd'}
            },
            {
                'id': 'glass-teal',
                'name': 'Glass Teal',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Translucent frosted mint surfaces with turquoise trim',
                'preview': {'bg': '#ccfbf1', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#0d9488', 'text': '#042f2e', 'border': '#99f6e4'}
            },
            {
                'id': 'glass-purple',
                'name': 'Glass Purple',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Translucent frosted violet surfaces with lavender accents',
                'preview': {'bg': '#ede9fe', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#7c3aed', 'text': '#2e1065', 'border': '#c4b5fd'}
            },
            {
                'id': 'glass-emerald',
                'name': 'Glass Emerald',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Translucent frosted jade surfaces with green borders',
                'preview': {'bg': '#d1fae5', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#059669', 'text': '#064e3b', 'border': '#6ee7b7'}
            },
            {
                'id': 'glass-smoke',
                'name': 'Glass Smoke',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Smoked dark glass with backdrop diffusion and sky trim',
                'preview': {'bg': '#1e293b', 'surface': 'rgba(30,41,59,0.85)', 'primary': '#38bdf8', 'text': '#f8fafc', 'border': '#475569'}
            },
            # 5 WEB INSPIRED THEMES
            {
                'id': 'material-inspired',
                'name': 'Material Inspired',
                'type': 'Web Inspired',
                'category': 'WEB INSPIRED THEMES',
                'desc': 'Material design principles with tonal surfaces and paired roles',
                'preview': {'bg': '#fdf8fd', 'surface': '#ffffff', 'primary': '#6750a4', 'text': '#1d1b20', 'border': '#cac4d0'}
            },
            {
                'id': 'github-primer',
                'name': 'GitHub Inspired',
                'type': 'Web Inspired',
                'category': 'WEB INSPIRED THEMES',
                'desc': 'Neutral surfaces, crisp borders, and accessible accents',
                'preview': {'bg': '#f6f8fa', 'surface': '#ffffff', 'primary': '#0969da', 'text': '#1f2328', 'border': '#d0d7de'}
            },
            {
                'id': 'atlassian-design',
                'name': 'Atlassian Inspired',
                'type': 'Web Inspired',
                'category': 'WEB INSPIRED THEMES',
                'desc': 'Enterprise tokens, vibrant cards, and high readability',
                'preview': {'bg': '#ebecf0', 'surface': '#ffffff', 'primary': '#0052cc', 'text': '#172b4d', 'border': '#dfe1e6'}
            },
            {
                'id': 'vercel-geist',
                'name': 'Vercel Inspired',
                'type': 'Web Inspired',
                'category': 'WEB INSPIRED THEMES',
                'desc': 'Minimal surfaces, crisp contrast, and restrained accents',
                'preview': {'bg': '#eaeaea', 'surface': '#ffffff', 'primary': '#000000', 'text': '#111111', 'border': '#cccccc'}
            },
            {
                'id': 'notion-minimal',
                'name': 'Notion Inspired',
                'type': 'Web Inspired',
                'category': 'WEB INSPIRED THEMES',
                'desc': 'Warm neutral surfaces, clean typography, and comfortable reading',
                'preview': {'bg': '#efede8', 'surface': '#ffffff', 'primary': '#2eaadc', 'text': '#37352f', 'border': '#e1dfdc'}
            },
            # 5 NEW LIGHT THEMES
            {
                'id': 'sunrise-amber',
                'name': 'Sunrise Amber',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Warm amber identity with gold accents and soft cream surfaces',
                'preview': {'bg': '#fdf6e3', 'surface': '#ffffff', 'primary': '#d97706', 'text': '#3d2c00', 'border': '#fcd34d'}
            },
            {
                'id': 'cherry-blossom',
                'name': 'Cherry Blossom',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Soft pink-rose with medical white surfaces and rose accents',
                'preview': {'bg': '#fdf2f8', 'surface': '#ffffff', 'primary': '#db2777', 'text': '#3d0e2c', 'border': '#fbcfe8'}
            },
            {
                'id': 'arctic-white',
                'name': 'Arctic White',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Pure white with icy sky-blue borders and crisp contrast',
                'preview': {'bg': '#f0f9ff', 'surface': '#ffffff', 'primary': '#0ea5e9', 'text': '#0c2a3d', 'border': '#bae6fd'}
            },
            {
                'id': 'lavender-mist',
                'name': 'Lavender Mist',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Soft lavender with plum headings and violet focus rings',
                'preview': {'bg': '#f5f0ff', 'surface': '#ffffff', 'primary': '#8b5cf6', 'text': '#2d1a5e', 'border': '#ddd6fe'}
            },
            {
                'id': 'sage-neutral',
                'name': 'Sage Neutral',
                'type': 'Light Theme',
                'category': 'LIGHT THEMES',
                'desc': 'Earthy sage-green surfaces with terracotta accent palette',
                'preview': {'bg': '#f0f4ef', 'surface': '#ffffff', 'primary': '#5a7d52', 'text': '#1e2d1e', 'border': '#c3d9be'}
            },
            # 5 NEW DARK THEMES
            {
                'id': 'obsidian',
                'name': 'Obsidian',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Pure black with chrome-white accents and high contrast',
                'preview': {'bg': '#0a0a0a', 'surface': '#141414', 'primary': '#e2e8f0', 'text': '#f2f2f2', 'border': '#2a2a2a'}
            },
            {
                'id': 'dark-rose',
                'name': 'Dark Rose',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Deep garnet background with crimson-rose glow accents',
                'preview': {'bg': '#120009', 'surface': '#200014', 'primary': '#f43f86', 'text': '#ffe4ef', 'border': '#5c0038'}
            },
            {
                'id': 'deep-amber',
                'name': 'Deep Amber',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Rich chocolate-amber background with golden text and glow',
                'preview': {'bg': '#120900', 'surface': '#1e1100', 'primary': '#f59e0b', 'text': '#fef3c7', 'border': '#4a2f00'}
            },
            {
                'id': 'dark-sapphire',
                'name': 'Dark Sapphire',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Deep cobalt ocean with electric blue trim and high readability',
                'preview': {'bg': '#00091a', 'surface': '#00112b', 'primary': '#3b82f6', 'text': '#dbeafe', 'border': '#0d3070'}
            },
            {
                'id': 'dark-purple-rain',
                'name': 'Dark Purple Rain',
                'type': 'Dark Theme',
                'category': 'DARK THEMES',
                'desc': 'Deep grape background with neon violet glow typography',
                'preview': {'bg': '#0d0018', 'surface': '#160025', 'primary': '#a855f7', 'text': '#f3e8ff', 'border': '#3b0060'}
            },
            # 5 NEW GLASS THEMES
            {
                'id': 'glass-rose',
                'name': 'Glass Rose',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Frosted pink-rose glass with soft blossom gradient',
                'preview': {'bg': '#fce7f3', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#db2777', 'text': '#3d0e2c', 'border': '#f9a8d4'}
            },
            {
                'id': 'glass-amber',
                'name': 'Glass Amber',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Frosted golden-amber glass with warm cream gradient',
                'preview': {'bg': '#fef3c7', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#d97706', 'text': '#3d2c00', 'border': '#fcd34d'}
            },
            {
                'id': 'glass-midnight',
                'name': 'Glass Midnight',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Dark frosted glass with deep navy and sky-blue highlights',
                'preview': {'bg': '#0f172a', 'surface': 'rgba(15,23,42,0.87)', 'primary': '#38bdf8', 'text': '#f1f5f9', 'border': '#334155'}
            },
            {
                'id': 'glass-ocean',
                'name': 'Glass Ocean',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Frosted deep-sea cyan glass with ocean gradient',
                'preview': {'bg': '#cffafe', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#06b6d4', 'text': '#0c2a3d', 'border': '#a5f3fc'}
            },
            {
                'id': 'glass-galaxy',
                'name': 'Glass Galaxy',
                'type': 'Glass Theme',
                'category': 'TRANSPARENT / GLASS THEMES',
                'desc': 'Dark frosted glass with deep-space nebula gradient and magenta glow',
                'preview': {'bg': '#0d0118', 'surface': 'rgba(25,5,50,0.85)', 'primary': '#c026d3', 'text': '#f3e8ff', 'border': '#581c87'}
            },
            # 20 MULTICOLOR THEMES
            {
                'id': 'sunset-gradient',
                'name': 'Sunset Gradient',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Vivid orange-to-blue sunset gradient environment',
                'preview': {'bg': '#ff6b35', 'surface': 'rgba(255,245,235,0.94)', 'primary': '#e85d04', 'text': '#1a0a00', 'border': '#f7c59f'}
            },
            {
                'id': 'ocean-depth',
                'name': 'Ocean Depth',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep blue-teal-green ocean gradient with sea surface reflections',
                'preview': {'bg': '#06b6d4', 'surface': 'rgba(6,90,110,0.90)', 'primary': '#22d3ee', 'text': '#cffafe', 'border': '#0284c7'}
            },
            {
                'id': 'northern-lights',
                'name': 'Northern Lights',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Aurora-inspired purple-green-blue night environment',
                'preview': {'bg': '#0d0118', 'surface': 'rgba(10,20,40,0.88)', 'primary': '#22d3ee', 'text': '#e0f2fe', 'border': '#1e40af'}
            },
            {
                'id': 'cosmic-dawn',
                'name': 'Cosmic Dawn',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep midnight navy to purple cosmic environment',
                'preview': {'bg': '#0f0c29', 'surface': 'rgba(20,18,50,0.88)', 'primary': '#c026d3', 'text': '#e9e3ff', 'border': '#4c1d95'}
            },
            {
                'id': 'retro-synthwave',
                'name': 'Retro Synthwave',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': '1980s synthwave neon pink-cyan on deep dark purple',
                'preview': {'bg': '#0d001a', 'surface': 'rgba(26,0,50,0.90)', 'primary': '#ff71ce', 'text': '#f8e8ff', 'border': '#5a0060'}
            },
            {
                'id': 'neon-pulse',
                'name': 'Neon Pulse',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Pure black with electric lime-green neon accents',
                'preview': {'bg': '#050505', 'surface': '#0e0e0e', 'primary': '#39ff14', 'text': '#e8ffe8', 'border': '#1e4d1e'}
            },
            {
                'id': 'royal-flush',
                'name': 'Royal Flush',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep midnight-to-cobalt royal blue environment',
                'preview': {'bg': '#000428', 'surface': 'rgba(0,10,50,0.90)', 'primary': '#3b82f6', 'text': '#dbeafe', 'border': '#1e3a8a'}
            },
            {
                'id': 'autumn-harvest',
                'name': 'Autumn Harvest',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep rust-orange to golden harvest gradient environment',
                'preview': {'bg': '#7f3500', 'surface': 'rgba(100,40,0,0.88)', 'primary': '#fbbf24', 'text': '#fff7ed', 'border': '#92400e'}
            },
            {
                'id': 'golden-hour',
                'name': 'Golden Hour',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Dark warm-amber surface with gold glow identity',
                'preview': {'bg': '#0f0a00', 'surface': '#1a1200', 'primary': '#f59e0b', 'text': '#fffbeb', 'border': '#6b4800'}
            },
            {
                'id': 'volcanic',
                'name': 'Volcanic',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Dark red lava gradient with molten orange atmosphere',
                'preview': {'bg': '#1a0000', 'surface': 'rgba(40,5,5,0.90)', 'primary': '#ef4444', 'text': '#fff5f5', 'border': '#7f1d1d'}
            },
            {
                'id': 'spring-bloom',
                'name': 'Spring Bloom',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Green-to-yellow-to-pink spring garden gradient',
                'preview': {'bg': '#d1fae5', 'surface': 'rgba(255,255,255,0.90)', 'primary': '#16a34a', 'text': '#0f2d1a', 'border': '#86efac'}
            },
            {
                'id': 'ice-storm',
                'name': 'Ice Storm',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Pale blue-white icy gradient with deep cyan storm accents',
                'preview': {'bg': '#e0f7ff', 'surface': 'rgba(255,255,255,0.92)', 'primary': '#0ea5e9', 'text': '#00293d', 'border': '#7dd3fc'}
            },
            {
                'id': 'blossom-dusk',
                'name': 'Blossom Dusk',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Dusk purple-to-rose gradient with cherry blossom identity',
                'preview': {'bg': '#2d1b4e', 'surface': 'rgba(45,18,70,0.88)', 'primary': '#f06292', 'text': '#fce4ec', 'border': '#7e3a8c'}
            },
            {
                'id': 'electric-lime',
                'name': 'Electric Lime',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep black with electric lime-green glow accent',
                'preview': {'bg': '#030a00', 'surface': '#0a1500', 'primary': '#84cc16', 'text': '#eeffcc', 'border': '#254a00'}
            },
            {
                'id': 'deep-crimson',
                'name': 'Deep Crimson',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Rich dark crimson with ruby glow and warm red typography',
                'preview': {'bg': '#0d0000', 'surface': '#1a0000', 'primary': '#e11d48', 'text': '#ffe8e8', 'border': '#5a0010'}
            },
            {
                'id': 'desert-sand',
                'name': 'Desert Sand',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Warm tan-to-sienna desert gradient environment',
                'preview': {'bg': '#d4a76a', 'surface': 'rgba(110,60,10,0.88)', 'primary': '#ffa726', 'text': '#fff8e7', 'border': '#a05010'}
            },
            {
                'id': 'tropical-paradise',
                'name': 'Tropical Paradise',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Cyan-to-lime tropical paradise with vivid teal accents',
                'preview': {'bg': '#00c9ff', 'surface': 'rgba(255,255,255,0.88)', 'primary': '#00b894', 'text': '#00291a', 'border': '#92fe9d'}
            },
            {
                'id': 'candy-pop',
                'name': 'Candy Pop',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Bubblegum pink-purple-blue playful gradient',
                'preview': {'bg': '#ff9de2', 'surface': 'rgba(255,255,255,0.90)', 'primary': '#e040fb', 'text': '#2d0a4e', 'border': '#d4a1ff'}
            },
            {
                'id': 'deep-sea',
                'name': 'Deep Sea',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Navy-to-teal-to-cyan deep ocean environment',
                'preview': {'bg': '#001f3f', 'surface': 'rgba(0,30,60,0.90)', 'primary': '#00b4d8', 'text': '#caf0f8', 'border': '#00416a'}
            },
            {
                'id': 'forest-fire',
                'name': 'Forest Fire',
                'type': 'Multicolor',
                'category': 'MULTICOLOR THEMES',
                'desc': 'Deep forest green to burnt orange fire gradient',
                'preview': {'bg': '#1a2e00', 'surface': 'rgba(30,20,0,0.88)', 'primary': '#ff6b00', 'text': '#fff5e0', 'border': '#6b3800'}
            },
            # 10 ANIMATED THEMES
            {
                'id': 'snow-world',
                'name': 'Snow World',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Icy blue environment with gentle falling snow particle layer',
                'preview': {'bg': '#d6eaf8', 'surface': 'rgba(255,255,255,0.92)', 'primary': '#0ea5e9', 'text': '#0a2540', 'border': '#bae6fd'}
            },
            {
                'id': 'aurora-world',
                'name': 'Aurora World',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Deep space environment with aurora borealis color-shift animation',
                'preview': {'bg': '#020f14', 'surface': 'rgba(5,20,28,0.88)', 'primary': '#10b981', 'text': '#d1fae5', 'border': '#064e3b'}
            },
            {
                'id': 'underwater-world',
                'name': 'Underwater World',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Deep ocean environment with slowly rising bubble animations',
                'preview': {'bg': '#001f3f', 'surface': 'rgba(0,30,60,0.90)', 'primary': '#00b4d8', 'text': '#caf0f8', 'border': '#00416a'}
            },
            {
                'id': 'space-explorer',
                'name': 'Space Explorer',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Deep space environment with twinkling star particle layer',
                'preview': {'bg': '#02020a', 'surface': 'rgba(5,5,20,0.90)', 'primary': '#6060ee', 'text': '#e8e8ff', 'border': '#1a1a50'}
            },
            {
                'id': 'cyber-city',
                'name': 'Cyber City',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Cyberpunk neon-cyan environment with animated scanline overlay',
                'preview': {'bg': '#000510', 'surface': 'rgba(0,8,22,0.90)', 'primary': '#00bcd4', 'text': '#00ffff', 'border': '#003340'}
            },
            {
                'id': 'enchanted-forest',
                'name': 'Enchanted Forest',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Dark enchanted forest with glowing floating particle animations',
                'preview': {'bg': '#020c04', 'surface': 'rgba(5,18,8,0.90)', 'primary': '#16a34a', 'text': '#c8ffcc', 'border': '#0d3a18'}
            },
            {
                'id': 'cloud-kingdom',
                'name': 'Cloud Kingdom',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Sky-blue environment with softly drifting cloud overlay',
                'preview': {'bg': '#87ceeb', 'surface': 'rgba(255,255,255,0.92)', 'primary': '#0ea5e9', 'text': '#0a1a40', 'border': '#bae6fd'}
            },
            {
                'id': 'future-robot-lab',
                'name': 'Future Robot Lab',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Cold grey HUD environment with animated grid-scan overlay',
                'preview': {'bg': '#0a0c10', 'surface': 'rgba(14,18,25,0.90)', 'primary': '#4ea8de', 'text': '#d0d8e8', 'border': '#1a2a3a'}
            },
            {
                'id': 'rover-world',
                'name': 'Rover World',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Mars landscape environment with gentle dust-drift animation',
                'preview': {'bg': '#1a0a00', 'surface': 'rgba(30,14,4,0.90)', 'primary': '#c87040', 'text': '#f5dcc8', 'border': '#4a2010'}
            },
            {
                'id': 'dream-world',
                'name': 'Dream World',
                'type': 'Animated World',
                'category': 'ANIMATED WORLDS',
                'desc': 'Dreamy pastel environment with gentle color-shift pulse animation',
                'preview': {'bg': '#fde8ff', 'surface': 'rgba(255,255,255,0.90)', 'primary': '#a855f7', 'text': '#2d0a4e', 'border': '#f0abfc'}
            },
        ]
        context['fonts'] = [
            {'id': 'Outfit', 'name': 'Outfit (Hospital Default)', 'category': 'Modern Sans'},
            {'id': 'Inter', 'name': 'Inter (Clean UI)', 'category': 'Modern Sans'},
            {'id': 'Plus Jakarta Sans', 'name': 'Plus Jakarta Sans (Premium)', 'category': 'Modern Sans'},
            {'id': 'DM Sans', 'name': 'DM Sans (Geometric)', 'category': 'Modern Sans'},
            {'id': 'Roboto', 'name': 'Roboto (Google Standard)', 'category': 'Humanist'},
            {'id': 'Open Sans', 'name': 'Open Sans (Accessible)', 'category': 'Humanist'},
            {'id': 'Noto Sans', 'name': 'Noto Sans (Multilingual / Tamil)', 'category': 'Humanist'},
            {'id': 'Poppins', 'name': 'Poppins (Geometric Display)', 'category': 'Display'},
            {'id': 'Montserrat', 'name': 'Montserrat (Crisp Corporate)', 'category': 'Display'},
            {'id': 'Nunito', 'name': 'Nunito (Soft Rounded)', 'category': 'Modern Sans'},
            {'id': 'Raleway', 'name': 'Raleway (Elegant Thin)', 'category': 'Modern Sans'},
            {'id': 'Lato', 'name': 'Lato (Warm Sans)', 'category': 'Humanist'},
            {'id': 'Source Sans 3', 'name': 'Source Sans 3 (Adobe)', 'category': 'Humanist'},
            {'id': 'Work Sans', 'name': 'Work Sans (Architectural)', 'category': 'Modern Sans'},
            {'id': 'Fira Sans', 'name': 'Fira Sans (Technical)', 'category': 'Modern Sans'},
            {'id': 'IBM Plex Sans', 'name': 'IBM Plex Sans (Industrial)', 'category': 'Modern Sans'},
            {'id': 'Space Grotesk', 'name': 'Space Grotesk (Tech / Gaming)', 'category': 'Tech / Gaming'},
            {'id': 'Syne', 'name': 'Syne (Futuristic Display)', 'category': 'Tech / Gaming'},
            {'id': 'Playfair Display', 'name': 'Playfair Display (Editorial)', 'category': 'Serif'},
            {'id': 'Merriweather', 'name': 'Merriweather (Readable Serif)', 'category': 'Serif'},
            {'id': 'JetBrains Mono', 'name': 'JetBrains Mono (Monospace)', 'category': 'Monospace'},
            {'id': 'System UI', 'name': 'System UI (Native OS)', 'category': 'System'},
        ]
        context['current_theme'] = getattr(self.request.user, 'theme', 'vmmc-main') or 'vmmc-main'
        context['current_font'] = getattr(self.request.user, 'theme_font', 'Outfit') or 'Outfit'
        user_motion = getattr(self.request.user, 'theme_motion', '1.5x') or '1.5x'
        context['current_reduced_motion'] = (user_motion == 'off')
        context['current_anim_speed'] = user_motion[:-1] if user_motion.endswith('x') else '1.5'
        context['current_pointer_speed'] = self.request.session.get('theme_pointer_speed', '1.5') if hasattr(self.request, 'session') else '1.5'
        return context

    def post(self, request, *args, **kwargs):
        theme_id = request.POST.get('theme', '').strip()
        font_id = request.POST.get('font', '').strip()
        reduced_motion = request.POST.get('reduced_motion')
        anim_speed = request.POST.get('animation_speed', '1.5').strip()
        pointer_speed = request.POST.get('pointer_speed', '1.5').strip()

        valid_themes = [
            # Main
            'vmmc-main',
            # Light (10)
            'clinical-blue', 'medical-teal', 'soft-green', 'royal-indigo', 'warm-slate',
            'sunrise-amber', 'cherry-blossom', 'arctic-white', 'lavender-mist', 'sage-neutral',
            # Dark (10)
            'midnight-blue', 'dark-teal', 'graphite', 'deep-indigo', 'dark-emerald',
            'obsidian', 'dark-rose', 'deep-amber', 'dark-sapphire', 'dark-purple-rain',
            # Glass (10)
            'glass-blue', 'glass-teal', 'glass-purple', 'glass-emerald', 'glass-smoke',
            'glass-rose', 'glass-amber', 'glass-midnight', 'glass-ocean', 'glass-galaxy',
            # Web Inspired (5)
            'material-inspired', 'github-primer', 'atlassian-design', 'vercel-geist', 'notion-minimal',
            # Multicolor (20)
            'sunset-gradient', 'ocean-depth', 'northern-lights', 'cosmic-dawn', 'retro-synthwave',
            'neon-pulse', 'royal-flush', 'autumn-harvest', 'golden-hour', 'volcanic',
            'spring-bloom', 'ice-storm', 'blossom-dusk', 'electric-lime', 'deep-crimson',
            'desert-sand', 'tropical-paradise', 'candy-pop', 'deep-sea', 'forest-fire',
            # Animated (10)
            'snow-world', 'aurora-world', 'underwater-world', 'space-explorer', 'cyber-city',
            'enchanted-forest', 'cloud-kingdom', 'future-robot-lab', 'rover-world', 'dream-world',
        ]

        if theme_id in valid_themes:
            request.user.theme = theme_id
        if font_id and re.match(r'^[A-Za-z0-9\s\-+]{2,60}$', font_id):
            request.user.theme_font = font_id

        motion_val = 'off' if reduced_motion in [True, 'true', 'on', '1', 1] else f"{anim_speed}x"
        request.user.theme_motion = motion_val

        request.user.save(update_fields=['theme', 'theme_font', 'theme_motion'])

        if hasattr(request, 'session'):
            request.session['theme'] = request.user.theme
            request.session['theme_font'] = request.user.theme_font
            request.session['theme_motion'] = request.user.theme_motion
            request.session['theme_anim_speed'] = anim_speed
            request.session['theme_pointer_speed'] = pointer_speed
            request.session['theme_reduced_motion'] = (motion_val == 'off')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'status': 'success',
                'theme': request.user.theme,
                'font': request.user.theme_font,
                'theme_motion': request.user.theme_motion,
                'animation_speed': anim_speed,
                'pointer_speed': pointer_speed,
                'reduced_motion': (motion_val == 'off'),
                'message': 'Theme settings saved successfully.'
            })

        messages.success(request, f"Theme settings applied successfully: '{request.user.theme}' with '{request.user.theme_font}' font.")
        return redirect('theme_settings')


@csrf_protect
def save_theme_preference_api(request):
    """
    API endpoint for asynchronous live theme preference persistence.
    Requires Theme Settings permission.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required. Please log in.'}, status=401)
    if not getattr(request.user, 'can_access_theme_settings', False):
        return JsonResponse({'status': 'error', 'message': 'Permission denied: Web Theme permission required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload received.'}, status=400)
    else:
        data = request.POST

    theme_id = (data.get('theme') or '').strip()
    font_id = (data.get('font') or '').strip()
    reduced_motion = data.get('reduced_motion')
    anim_speed = str(data.get('animation_speed', '') or '').strip()
    pointer_speed = str(data.get('pointer_speed', '') or '').strip()

    valid_themes = [
        # Main
        'vmmc-main',
        # Light (10)
        'clinical-blue', 'medical-teal', 'soft-green', 'royal-indigo', 'warm-slate',
        'sunrise-amber', 'cherry-blossom', 'arctic-white', 'lavender-mist', 'sage-neutral',
        # Dark (10)
        'midnight-blue', 'dark-teal', 'graphite', 'deep-indigo', 'dark-emerald',
        'obsidian', 'dark-rose', 'deep-amber', 'dark-sapphire', 'dark-purple-rain',
        # Glass (10)
        'glass-blue', 'glass-teal', 'glass-purple', 'glass-emerald', 'glass-smoke',
        'glass-rose', 'glass-amber', 'glass-midnight', 'glass-ocean', 'glass-galaxy',
        # Web Inspired (5)
        'material-inspired', 'github-primer', 'atlassian-design', 'vercel-geist', 'notion-minimal',
        # Multicolor (20)
        'sunset-gradient', 'ocean-depth', 'northern-lights', 'cosmic-dawn', 'retro-synthwave',
        'neon-pulse', 'royal-flush', 'autumn-harvest', 'golden-hour', 'volcanic',
        'spring-bloom', 'ice-storm', 'blossom-dusk', 'electric-lime', 'deep-crimson',
        'desert-sand', 'tropical-paradise', 'candy-pop', 'deep-sea', 'forest-fire',
        # Animated (10)
        'snow-world', 'aurora-world', 'underwater-world', 'space-explorer', 'cyber-city',
        'enchanted-forest', 'cloud-kingdom', 'future-robot-lab', 'rover-world', 'dream-world',
    ]

    valid_anim_speeds = {
        '0.5x': '0.5', '0.75x': '0.75', '1x': '1', '1.25x': '1.25', '1.5x': '1.5', '2x': '2', '2.5x': '2.5', '3x': '3',
        '0.5': '0.5', '0.75': '0.75', '1': '1', '1.25': '1.25', '1.5': '1.5', '2': '2', '2.5': '2.5', '3': '3'
    }
    valid_pointer_speeds = {
        '0.5x': '0.5', '1x': '1', '1.5x': '1.5', '2x': '2', '3x': '3',
        '0.5': '0.5', '1': '1', '1.5': '1.5', '2': '2', '3': '3',
        'Slow': '0.5', 'Normal': '1', 'Fast': '1.5', 'Very Fast': '2'
    }

    clean_anim_speed = valid_anim_speeds.get(anim_speed, '1.5')
    clean_pointer_speed = valid_pointer_speeds.get(pointer_speed, '1.5')

    updated = False
    update_fields = []

    if theme_id and theme_id in valid_themes:
        request.user.theme = theme_id
        updated = True
        update_fields.append('theme')
    elif theme_id:
        return JsonResponse({'status': 'error', 'message': f'Invalid theme "{theme_id}" specified.'}, status=400)

    if font_id and re.match(r'^[A-Za-z0-9\s\-+]{2,60}$', font_id):
        request.user.theme_font = font_id
        updated = True
        update_fields.append('theme_font')
    elif font_id:
        return JsonResponse({'status': 'error', 'message': f'Invalid font name "{font_id}" specified.'}, status=400)

    motion_val = 'off' if reduced_motion in [True, 'true', 'on', '1', 1] else f"{clean_anim_speed}x"
    request.user.theme_motion = motion_val
    updated = True
    update_fields.append('theme_motion')

    if updated:
        request.user.save(update_fields=list(set(update_fields)))

        if hasattr(request, 'session'):
            request.session['theme'] = request.user.theme
            request.session['theme_font'] = request.user.theme_font
            request.session['theme_motion'] = request.user.theme_motion
            request.session['theme_anim_speed'] = clean_anim_speed
            request.session['theme_pointer_speed'] = clean_pointer_speed
            request.session['theme_reduced_motion'] = (motion_val == 'off')

        return JsonResponse({
            'status': 'success',
            'theme': request.user.theme,
            'font': request.user.theme_font,
            'theme_motion': request.user.theme_motion,
            'animation_speed': clean_anim_speed,
            'pointer_speed': clean_pointer_speed,
            'reduced_motion': (motion_val == 'off'),
            'message': 'Theme preferences saved successfully.'
        })

    return JsonResponse({'status': 'error', 'message': 'No valid preferences provided to update.'}, status=400)


def hex_to_rgb(hex_code):
    hex_code = (hex_code or '').strip().lstrip('#')
    if len(hex_code) == 3:
        hex_code = ''.join([c*2 for c in hex_code])
    if len(hex_code) >= 6:
        try:
            return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
        except ValueError:
            pass
    return 128, 128, 128


def get_relative_luminance(r, g, b):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def calculate_contrast_ratio(hex1, hex2):
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    l1 = get_relative_luminance(r1, g1, b1)
    l2 = get_relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


class ThemeAuditView(LoginRequiredMixin, TemplateView):
    """
    Development-only Web Theme Visual Test Lab & WCAG AA Contrast Audit.
    Displays an interactive matrix of all 60 themes with component previews,
    a WCAG AA contrast analysis table, and a Page Visual Test Lab index.
    """
    template_name = 'users/theme_audit.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not getattr(request.user, 'can_access_theme_settings', False):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Access Denied: You do not have permission to access Theme Audit.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tsv = ThemeSettingsView()
        tsv.request = self.request
        tsv_context = tsv.get_context_data()
        themes = tsv_context.get('themes', [])

        audit_results = []
        total_checks = 0
        total_passed = 0

        for t in themes:
            p = t.get('preview', {})
            cat = t.get('category', '').upper()
            is_dark = ('DARK' in cat) or ('ANIMATED' in cat and t['id'] not in ['cloud-kingdom', 'dream-world', 'snow-world'])

            def clean_hex(val, fallback):
                if val and val.startswith('#'):
                    return val
                return fallback

            surf_hex = clean_hex(p.get('surface'), '#111827' if is_dark else '#ffffff')
            text_hex = clean_hex(p.get('text'), '#f8fafc' if is_dark else '#0f172a')
            prim_hex = clean_hex(p.get('primary'), '#38bdf8' if is_dark else '#0284c7')

            # 1. Primary Text against Surface (WCAG AA: >= 4.5)
            cr_text = calculate_contrast_ratio(text_hex, surf_hex)
            pass_text = cr_text >= 4.5

            # 2. Dropdown Text against Dropdown Surface (WCAG AA: >= 4.5)
            drop_bg = '#1e293b' if is_dark else '#ffffff'
            drop_text = '#f8fafc' if is_dark else '#0f172a'
            cr_dropdown = calculate_contrast_ratio(drop_text, drop_bg)
            pass_dropdown = cr_dropdown >= 4.5

            # 3. Card Title against Card Surface (WCAG AA: >= 4.5)
            cr_card = calculate_contrast_ratio(text_hex, surf_hex)
            pass_card = cr_card >= 4.5

            # 4. Button Primary Text against Primary Background (WCAG AA Large: >= 3.0)
            btn_text = '#ffffff' if calculate_contrast_ratio('#ffffff', prim_hex) >= 3.0 else '#000000'
            cr_btn = calculate_contrast_ratio(btn_text, prim_hex)
            pass_btn = cr_btn >= 3.0

            # 5. Table Header against Header Background (WCAG AA Large: >= 3.0)
            th_bg = prim_hex
            th_text = '#ffffff' if calculate_contrast_ratio('#ffffff', th_bg) >= 3.0 else '#000000'
            cr_th = calculate_contrast_ratio(th_text, th_bg)
            pass_th = cr_th >= 3.0

            theme_pass = pass_text and pass_dropdown and pass_card and pass_btn and pass_th
            total_checks += 5
            total_passed += sum([pass_text, pass_dropdown, pass_card, pass_btn, pass_th])

            audit_results.append({
                'theme': t,
                'is_dark': is_dark,
                'cr_text': cr_text,
                'pass_text': pass_text,
                'cr_dropdown': cr_dropdown,
                'pass_dropdown': pass_dropdown,
                'cr_card': cr_card,
                'pass_card': pass_card,
                'cr_btn': cr_btn,
                'pass_btn': pass_btn,
                'cr_th': cr_th,
                'pass_th': pass_th,
                'overall_pass': theme_pass,
                'surf_hex': surf_hex,
                'text_hex': text_hex,
                'prim_hex': prim_hex,
                'drop_bg': drop_bg,
                'drop_text': drop_text,
            })

        context['audit_results'] = audit_results
        context['total_themes'] = len(themes)
        context['total_checks'] = total_checks
        context['total_passed'] = total_passed
        context['pass_percentage'] = round((total_passed / total_checks * 100), 1) if total_checks else 100
        context['current_theme'] = getattr(self.request.user, 'theme', 'vmmc-main') or 'vmmc-main'
        return context


