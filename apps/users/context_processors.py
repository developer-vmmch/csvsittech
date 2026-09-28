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
    if not user or not user.is_authenticated:
        return {'dynamic_nav_modules': []}

    try:
        return _build_dynamic_navbar(request, user)
    except Exception:
        return {'dynamic_nav_modules': []}


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
        # If user has comma-separated depts, check the first or match session
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

    # If user is in "All Departments" universal mode and is admin with no specific active dept:
    is_universal_mode = False
    if str(active_dept_code).strip().lower() in ['all', 'all departments', 'all departments (universal access)']:
        is_universal_mode = True

    if is_admin and (is_universal_mode or (not dept_obj and not request.session.get('active_department'))):
        # Universal Admin View: Show all active modules and submodules
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

    # 2. Resolve Department Permissions Map
    dept_perms = None
    if dept_obj:
        if dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0:
            dept_perms = dept_obj.nav_permissions
        else:
            dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
    elif active_dept_code:
        norm_code = str(active_dept_code).split(',')[0].strip().lower().replace('-', '_')
        dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(norm_code, {})

    # Fallback to Role Permissions if no department found
    role_perms = {}
    if not dept_perms:
        from .models import RoleMenuPermission
        role_perms = RoleMenuPermission.get_permissions_for_role(user.role) or {}

    def _is_submodule_permitted(sub_code):
        if dept_perms is not None:
            # 1. Exact boolean in department mapping
            if dept_perms.get(sub_code) is True:
                return True
            if dept_perms.get(f"{sub_code}.view") is True:
                return True
            # 2. Check granular action dictionary
            act = dept_perms.get(f"{sub_code}_actions")
            if isinstance(act, dict):
                if act.get('access') is True or act.get('view') is True:
                    return True
                if any(act.get(a) is True for a in ['add', 'create', 'edit', 'update', 'delete', 'print', 'export']):
                    return True
            # Explicitly false or absent in department permissions
            return False
        else:
            # Role permissions fallback
            if role_perms.get(sub_code) is True or role_perms.get(f"{sub_code}.view") is True:
                return True
            act = role_perms.get(f"{sub_code}_actions")
            if isinstance(act, dict) and (act.get('access') is True or act.get('view') is True):
                return True
            return False

    # 3. Filter modules & submodules strictly
    has_admin_mod_added = False

    for mod in modules:
        active_subs = []
        all_mod_subs = mod.submodules.filter(is_active=True).order_by('order', 'id')

        for sub in all_mod_subs:
            if _is_submodule_permitted(sub.code):
                active_subs.append(sub)

        # Include parent module ONLY if it has at least one permitted submodule,
        # OR if it's a standalone single-link module explicitly granted
        mod_is_granted = False
        if dept_perms is not None:
            mod_is_granted = bool(dept_perms.get(mod.code, False))
        else:
            mod_is_granted = bool(role_perms.get(mod.code, False))

        if len(active_subs) > 0 or (len(all_mod_subs) == 0 and mod_is_granted):
            primary_url = mod.url_path
            if (not primary_url or primary_url == '#') and active_subs:
                primary_url = active_subs[0].url_path

            if mod.code in ['administration', 'system_section']:
                has_admin_mod_added = True

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

    # Always ensure Administrators can access Administration menu if on admin paths or needed
    if is_admin and not has_admin_mod_added and request.path.startswith('/administration/'):
        admin_mod = modules.filter(code__in=['administration', 'system_section']).first()
        if admin_mod:
            active_subs = list(admin_mod.submodules.filter(is_active=True).order_by('order', 'id'))
            user_nav_modules.append({
                'id': admin_mod.id,
                'code': admin_mod.code,
                'name': admin_mod.name,
                'icon': admin_mod.icon,
                'url_path': admin_mod.url_path or (active_subs[0].url_path if active_subs else '#'),
                'color': admin_mod.color,
                'badge': admin_mod.badge,
                'submodules': active_subs,
                'has_submodules': len(active_subs) > 0,
            })

    return {'dynamic_nav_modules': user_nav_modules}
