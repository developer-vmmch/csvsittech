from django.contrib.auth.mixins import AccessMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from functools import wraps

class MenuAccessRequiredMixin(AccessMixin):
    """
    Mixin that verifies whether the logged-in user has permission to access
    the specified menu_key based on User.can_access_menu(menu_key).
    If permission is denied, displays an error alert message and redirects
    the user to a safe landing page.
    """
    menu_key = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        role_str = (getattr(request.user, 'role', '') or '').strip().upper()
        if request.user.is_superuser or role_str in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']:
            return super().dispatch(request, *args, **kwargs)

        active_dept_code = request.session.get('active_department') or getattr(request.user, 'department', '')
        active_dept_slug = request.session.get('active_department_slug')
        dept_obj = None
        if active_dept_code or active_dept_slug:
            try:
                from apps.users.models import LandingDepartment
                from apps.users.nav_config import DEPT_DEFAULT_NAV_MAPPING
                dept_obj = (
                    LandingDepartment.objects.filter(code__iexact=str(active_dept_code).strip().lower().replace('-', '_')).first()
                    or LandingDepartment.objects.filter(slug__iexact=str(active_dept_slug).strip().lower().replace('_', '-')).first()
                    or LandingDepartment.objects.filter(name__iexact=str(active_dept_code).strip()).first()
                )
            except Exception:
                dept_obj = None

        keys = self.menu_key if isinstance(self.menu_key, (list, tuple)) else ([self.menu_key] if self.menu_key else [])
        if dept_obj:
            dept_perms = dept_obj.nav_permissions if (dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0) else DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
            is_permitted = False
            if keys:
                for k in keys:
                    k_perm = (
                        dept_perms.get(k) is True
                        and dept_perms.get(f"{k}.view", True) is not False
                    )
                    act_dict = dept_perms.get(f"{k}_actions")
                    if isinstance(act_dict, dict) and (act_dict.get('access') is False or act_dict.get('view') is False):
                        k_perm = False
                    if k_perm:
                        is_permitted = True
                        break
            else:
                is_permitted = True

            if not is_permitted:
                from django.core.exceptions import PermissionDenied
                menu_title = self.get_menu_label()
                raise PermissionDenied(f"Access Denied: '{menu_title}' is not authorized for the {dept_obj.name} department.")
        elif keys and not any(request.user.can_access_menu(k) for k in keys):
            from django.core.exceptions import PermissionDenied
            menu_title = self.get_menu_label()
            raise PermissionDenied(f"Permission Denied: Your assigned user role ({request.user.get_role_display()}) does not have access to '{menu_title}'.")

        return super().dispatch(request, *args, **kwargs)

    def get_menu_label(self):
        labels = {
            'dashboard': 'Dashboard Overview',
            'add_patient': 'Add Patient',
            'search_patient': 'Search Patient',
            'patient_list': 'Patient Directory',
            'op_census': 'OP Census Analytics',
            'patient_companies': 'Patient Companies',
            'department_list': 'Departments & Units',
            'add_department': '+ Add Department',
            'add_company': '+ Add Company',
            'administration': 'User Administration',
            'users_roles': 'Users & Roles Matrix',
            'inventory': 'Inventory Management',
            'settings': 'System Settings',
        }
        return labels.get(self.menu_key, self.menu_key or 'requested module')

class GranularPermissionRequiredMixin(AccessMixin):
    """
    Mixin that verifies whether the logged-in user has the specific granular permission 
    (e.g., 'patients.patient_list.view') required to access this view.
    """
    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        role_str = (getattr(request.user, 'role', '') or '').strip().upper()
        if request.user.is_superuser or role_str in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']:
            return super().dispatch(request, *args, **kwargs)

        if self.permission_required:
            if isinstance(self.permission_required, (list, tuple)):
                has_perm = any(request.user.has_perm_code(perm) for perm in self.permission_required)
            else:
                has_perm = request.user.has_perm_code(self.permission_required)
                
            if not has_perm:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied(f"Access Denied: You do not have the required permission ({self.permission_required}) to perform this action.")

        return super().dispatch(request, *args, **kwargs)

def granular_permission_required(perm_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)
                return redirect('login')
                
            role_str = (getattr(request.user, 'role', '') or '').strip().upper()
            if request.user.is_superuser or role_str in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']:
                return view_func(request, *args, **kwargs)

            if not request.user.has_perm_code(perm_code):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': f'Access Denied: Required permission {perm_code}.'}, status=403)
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied(f"Access Denied: You do not have the required permission ({perm_code}).")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
