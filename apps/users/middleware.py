"""
Department Access Control Middleware for VMMC ERP.
Enforces server-side department-level security, URL protection, and page permissions.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import LandingDepartment, NavSubmodule
from .departments import get_department_by_code, get_department_by_slug, user_can_access_department, get_all_departments
from .nav_config import DEPT_DEFAULT_NAV_MAPPING

class DepartmentAccessMiddleware:
    """
    Middleware that ensures authenticated users only access features
    and URLs belonging to their authorized department and granted permissions.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, 'user', None) and request.user.is_authenticated:
            path = getattr(request, 'path_info', None) or getattr(request, 'path', '')
            if not (path.startswith('/static/') or path.startswith('/media/')):
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Allow static, media, admin, login, logout, and landing endpoints
        path = request.path
        if (
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/admin/') or
            path == '/' or
            path.startswith('/login') or
            path.startswith('/logout') or
            path.startswith('/public/')
        ):
            return None

        # Check authentication for protected paths
        if not request.user.is_authenticated:
            return None

        # Superusers, System Administrators, and Developers have full access everywhere
        role_str = (getattr(request.user, 'role', '') or '').strip().upper()
        if request.user.is_superuser or role_str in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']:
            return None

        # 1. Identify active Landing Department
        active_dept_code = request.session.get('active_department') or getattr(request.user, 'department', '')
        active_dept_slug = request.session.get('active_department_slug')
        
        dept_obj = None
        if active_dept_code:
            norm_code = str(active_dept_code).strip().lower().replace('-', '_')
            dept_obj = LandingDepartment.objects.filter(code__iexact=norm_code).first()
        if not dept_obj and active_dept_slug:
            norm_slug = str(active_dept_slug).strip().lower().replace('_', '-')
            dept_obj = LandingDepartment.objects.filter(slug__iexact=norm_slug).first()
        if not dept_obj and active_dept_code:
            dept_obj = LandingDepartment.objects.filter(name__iexact=str(active_dept_code).strip()).first()

        if dept_obj:
            # Department's own primary dashboard URL and common dashboard are always accessible
            dept_dashboard = dept_obj.dashboard_url or '/dashboard/'
            if path == dept_dashboard or path == '/dashboard/' or path == '/':
                return None

            dept_perms = dept_obj.nav_permissions if (dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0) else DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
            
            is_api = path.startswith('/api/') or '/api/' in path or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'

            # Helper to safely redirect without creating an infinite loop
            def _safe_redirect(fallback_msg=None):
                if is_api:
                    from django.http import JsonResponse
                    return JsonResponse({'status': 'error', 'message': fallback_msg or 'Access Denied.'}, status=403)
                if fallback_msg:
                    messages.error(request, fallback_msg)
                dest = dept_obj.dashboard_url or '/dashboard/'
                if dest == path or (path.startswith(dest) and dest != '/'):
                    dest = '/dashboard/'
                if dest == path:
                    return None
                return redirect(dest)

            # 2. Check if current path matches any NavSubmodule
            matching_sub = None
            norm_path = path.replace('/api/', '/')
            try:
                submodules = NavSubmodule.objects.filter(is_active=True).exclude(url_path__in=['#', '', '/']).order_by('-url_path')
                for sub in submodules:
                    if sub.url_path and (
                        path == sub.url_path 
                        or (path.startswith(sub.url_path) and sub.url_path != '/')
                        or (norm_path.startswith(sub.url_path) and sub.url_path != '/')
                    ):
                        matching_sub = sub
                        break
            except Exception:
                matching_sub = None

            if matching_sub:
                sub_code = matching_sub.code
                is_granted = (
                    request.user.can_access_menu(sub_code)
                    or request.user.has_perm_code(sub_code)
                    or request.user.has_perm_code(f"{sub_code}.view")
                    or (dept_perms and dept_perms.get(sub_code) is True)
                )

                if not is_granted:
                    return _safe_redirect(f"Access Denied: You are not authorized to access '{matching_sub.name}'.")

                # 3. Check granular action permissions for mutation/action routes
                if request.method == 'POST':
                    is_delete_req = '/delete/' in path or request.POST.get('action') == 'delete'
                    if is_delete_req:
                        can_del = request.user.has_perm_code(f"{sub_code}.delete")
                        if can_del is False:
                            messages.error(request, f"Permission Denied: Delete operation is disabled for '{matching_sub.name}'.")
                            return redirect(matching_sub.url_path or dept_dashboard)

            # 4. Check department exclusive prefix boundaries
            if not is_api and not matching_sub:
                all_depts = get_all_departments()
                for other_dept in all_depts:
                    if other_dept['code'] == dept_obj.code:
                        continue
                    
                    other_prefixes = [p for p in other_dept.get('allowed_prefixes', []) if p not in ['/dashboard/', '/patients/']]
                    active_prefixes = dept_obj.allowed_prefixes if isinstance(dept_obj.allowed_prefixes, list) else []

                    for prefix in other_prefixes:
                        if path.startswith(prefix) and not any(path.startswith(ap) for ap in active_prefixes):
                            if not user_can_access_department(request.user, other_dept):
                                return _safe_redirect(f"Access Denied: You are not authorized to access the {other_dept['name']} department.")

        return None
