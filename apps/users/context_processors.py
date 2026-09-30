from .models import NavModule, NavSubmodule, LandingDepartment
from .nav_config import (
    NAVBAR_MODULES_CONFIG,
    DEPT_DEFAULT_NAV_MAPPING,
    seed_default_nav_modules_if_needed,
)

def dynamic_navbar(request):
    """
    Context processor to provide dynamically configured navigation modules
    and submodules for the top navigation bar:
    1. System Administrators / Superusers: Unrestricted 100% FULL ACCESS to ALL modules and submodules.
    2. Non-admin users: Dynamic filtering based on active Landing Department or assigned User Role permissions.
    """
    user = getattr(request, 'user', None)
    active_lab_sub_dept = request.session.get('active_lab_sub_department', '') if hasattr(request, 'session') else ''
    if not user or not user.is_authenticated:
        return {'dynamic_nav_modules': [], 'active_lab_sub_department': active_lab_sub_dept}

    try:
        res = _build_dynamic_navbar(request, user)
        res['active_lab_sub_department'] = active_lab_sub_dept
        return res
    except Exception:
        return {'dynamic_nav_modules': [], 'active_lab_sub_department': active_lab_sub_dept}


def _build_dynamic_navbar(request, user):
    role_str = (getattr(user, 'role', '') or '').strip().upper()
    is_admin = (
        user.is_superuser
        or role_str in ['ADMIN', 'DEVELOPER', 'DEVELOPER_ROLE']
        or getattr(user, 'is_admin_role', False)
    )

    # Ensure NavModules exist in DB
    try:
        if not NavModule.objects.filter(is_active=True).exists():
            seed_default_nav_modules_if_needed()
    except Exception:
        pass

    modules = NavModule.objects.filter(is_active=True).prefetch_related('submodules').order_by('order', 'id')
    user_nav_modules = []

    if not modules.exists():
        return {'dynamic_nav_modules': []}

    # 1. Identify active Landing Department
    active_dept_code = request.session.get('active_department') or getattr(user, 'department', '')
    active_dept_slug = request.session.get('active_department_slug')
    
    dept_obj = None
    if active_dept_code:
        first_dept = str(active_dept_code).split(',')[0].strip()
        norm_code = first_dept.lower().replace('-', '_')
        dept_obj = (
            LandingDepartment.objects.filter(code__iexact=norm_code).first()
            or LandingDepartment.objects.filter(name__iexact=first_dept).first()
            or LandingDepartment.objects.filter(slug__iexact=first_dept.lower().replace('_', '-')).first()
        )
    if not dept_obj and active_dept_slug:
        norm_slug = str(active_dept_slug).strip().lower().replace('_', '-')
        dept_obj = LandingDepartment.objects.filter(slug__iexact=norm_slug).first()

    # Universal Admin mode: Admin in "All Departments" or with no specific active department
    is_universal_mode = str(active_dept_code).strip().lower() in ['all', 'all departments', 'all departments (universal access)']
    if is_admin and (is_universal_mode or not dept_obj):
        for mod in modules:
            active_subs = list(mod.submodules.filter(is_active=True).order_by('order', 'id'))
            primary_url = mod.url_path
            if (not primary_url or primary_url == '#') and active_subs:
                primary_url = active_subs[0].url_path

            user_nav_modules.append({
                'id': mod.id,
                'code': mod.code,
                'name': mod.name,
                'icon': mod.icon,
                'url_path': primary_url,
                'color': mod.color,
                'badge': mod.badge,
                'submodules': active_subs,
                'has_submodules': len(active_subs) > 0,
            })
        return {'dynamic_nav_modules': user_nav_modules}

    # 2. Strict Department Permission Resolution:
    # Retrieve department's saved permissions directly from DB
    dept_perms = {}
    if dept_obj:
        if dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0:
            dept_perms = dept_obj.nav_permissions
        else:
            dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})

    def _is_submodule_permitted(sub_code):
        # Must be explicitly True in dept_perms
        if dept_perms.get(sub_code) is not True:
            return False
        # Check View permission (if view is explicitly False, deny)
        if dept_perms.get(f"{sub_code}.view") is False:
            return False
        act_dict = dept_perms.get(f"{sub_code}_actions")
        if isinstance(act_dict, dict) and (act_dict.get('access') is False or act_dict.get('view') is False):
            return False
        return True

    # 3. Filter modules & submodules strictly for this department
    for mod in modules:
        active_subs = []
        all_mod_subs = list(mod.submodules.filter(is_active=True).order_by('order', 'id'))

        for sub in all_mod_subs:
            if _is_submodule_permitted(sub.code):
                active_subs.append(sub)

        # Include parent module ONLY if it has at least one permitted submodule,
        # OR if it's a standalone single-link module explicitly granted in department permissions
        mod_is_granted = bool(dept_perms.get(mod.code) is True)
        if len(active_subs) > 0 or (len(all_mod_subs) == 0 and mod_is_granted):
            primary_url = mod.url_path
            if (not primary_url or primary_url == '#') and active_subs:
                primary_url = active_subs[0].url_path

            user_nav_modules.append({
                'id': mod.id,
                'code': mod.code,
                'name': mod.name,
                'icon': mod.icon,
                'url_path': primary_url,
                'color': mod.color,
                'badge': mod.badge,
                'submodules': active_subs,
                'has_submodules': len(active_subs) > 0,
            })

    return {'dynamic_nav_modules': user_nav_modules}
