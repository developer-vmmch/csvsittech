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

class ERPLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('patients:list')


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
    paginate_by = 20

    def get_queryset(self):
        return User.objects.order_by('-id')


class StaffListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'administration'
    model = User
    template_name = 'users/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 20

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
            {'key': 'dashboard', 'label': 'Dashboard Overview', 'section': 'MAIN NAVIGATION'},
            {'key': 'add_patient', 'label': 'Add Patient', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'search_patient', 'label': 'Search Patient', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'patient_list', 'label': 'Patient Directory', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'review', 'label': 'Review (Patient Record Log)', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'review_report', 'label': 'Review Report Analytics', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'op_census', 'label': 'OP Census Analytics', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'patient_companies', 'label': 'Patient Companies', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'department_list', 'label': 'Departments & Units List', 'section': 'PATIENT MANAGEMENT'},
            {'key': 'add_department', 'label': '+ Add Department', 'section': 'PATIENT SETUP'},
            {'key': 'add_company', 'label': '+ Add Company', 'section': 'PATIENT SETUP'},
            {'key': 'administration', 'label': 'User Administration', 'section': 'SYSTEM ADMINISTRATION'},
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
            obj.menu_permissions = perms_dict
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
