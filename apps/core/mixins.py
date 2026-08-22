from django.contrib.auth.mixins import AccessMixin
from django.contrib import messages
from django.shortcuts import redirect

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
