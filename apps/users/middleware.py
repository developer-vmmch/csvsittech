"""
Department Access Control Middleware for VMMC ERP.
Enforces server-side department-level security and URL protection.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .departments import get_department_by_code, get_department_by_slug, user_can_access_department, get_all_departments

class DepartmentAccessMiddleware:
    """
    Middleware that ensures authenticated users only access features
    and URLs belonging to their authorized department.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Allow static, media, admin, login, logout, and API endpoints
        path = request.path
        if (
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/admin/') or
            path == '/' or
            path.startswith('/login') or
            path.startswith('/logout')
        ):
            return None

        # Check authentication for protected paths
        if not request.user.is_authenticated:
            # Let Django's LoginRequiredMixin or login_required handle or redirect to login
            return None

        # Superusers and System Administrators have full access everywhere
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'ADMIN':
            return None

        # Identify if path belongs to a specific restricted module
        active_dept_code = request.session.get('active_department')
        if active_dept_code:
            active_dept = get_department_by_code(active_dept_code)
            if active_dept:
                # Check if user is trying to access another department's exclusive space
                all_depts = get_all_departments()
                for other_dept in all_depts:
                    if other_dept['code'] == active_dept['code']:
                        continue
                    
                    # If this other department has specific exclusive prefixes that the active dept doesn't have
                    # e.g., OT module (/ot/) or Lab module (/lab/)
                    other_prefixes = [p for p in other_dept.get('allowed_prefixes', []) if p not in ['/dashboard/', '/patients/']]
                    active_prefixes = active_dept.get('allowed_prefixes', [])

                    for prefix in other_prefixes:
                        if path.startswith(prefix) and not any(path.startswith(ap) for ap in active_prefixes):
                            # Verify if user has special permissions for this path
                            if not user_can_access_department(request.user, other_dept):
                                messages.error(
                                    request,
                                    f"Access Denied: You are not authorized to access the {other_dept['name']} department."
                                )
                                return redirect(active_dept.get('dashboard_url', '/dashboard/'))

        return None
