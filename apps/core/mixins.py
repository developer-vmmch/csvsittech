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

        if self.menu_key and not request.user.can_access_menu(self.menu_key):
            menu_title = self.get_menu_label()
            messages.error(request, f"Permission Denied: Your assigned user role ({request.user.get_role_display()}) does not have access to '{menu_title}'.")
            return redirect('patients:list')

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

        if self.permission_required:
            if isinstance(self.permission_required, (list, tuple)):
                has_perm = any(request.user.has_perm_code(perm) for perm in self.permission_required)
            else:
                has_perm = request.user.has_perm_code(self.permission_required)
                
            if not has_perm:
                messages.error(request, f"Access Denied: You do not have the required permission ({self.permission_required}) to perform this action.")
                return redirect('patients:list')

        return super().dispatch(request, *args, **kwargs)

def granular_permission_required(perm_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)
                return redirect('login')
                
            if not request.user.has_perm_code(perm_code):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'message': f'Access Denied: Required permission {perm_code}.'}, status=403)
                messages.error(request, f"Access Denied: You do not have the required permission ({perm_code}).")
                return redirect('patients:list')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
