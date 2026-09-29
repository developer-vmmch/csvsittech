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

    # 2. Resolve Role Permissions & Department Permissions
    from .models import RoleMenuPermission
    role_perms = RoleMenuPermission.get_permissions_for_role(user.role)

    dept_perms = None
    if dept_obj and dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0:
        dept_perms = dept_obj.nav_permissions
    elif not role_perms:
        if dept_obj:
            dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(dept_obj.code, {})
        elif active_dept_code:
            norm_code = str(active_dept_code).split(',')[0].strip().lower().replace('-', '_')
            dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(norm_code, {})

    def _check_perm_map(perms_map, code):
        if perms_map is None or not isinstance(perms_map, dict):
            return None
        # 1. Exact boolean in mapping
        if code in perms_map:
            return bool(perms_map[code])
        if f"{code}.view" in perms_map:
            return bool(perms_map[f"{code}.view"])
        # 2. Check granular action dictionary
        act = perms_map.get(f"{code}_actions")
        if isinstance(act, dict):
            if act.get('access') is False and act.get('view') is False:
                return False
            if act.get('access') is True or act.get('view') is True:
                return True
            if any(act.get(a) is True for a in ['add', 'create', 'edit', 'update', 'delete', 'print', 'export']):
                return True
            return False
        return None

    def _is_submodule_permitted(sub_code):
        # 1. If role permissions are configured in DB:
        if role_perms is not None and isinstance(role_perms, dict):
            r_val = _check_perm_map(role_perms, sub_code)
            # Explicitly locked/disabled in role permissions -> strictly deny!
            if r_val is False:
                return False
            # If role permissions are saved in DB, and this sub_code is True:
            if r_val is True:
                # If department permissions are also customized in DB, ensure dept didn't lock it
                if dept_perms is not None and isinstance(dept_perms, dict):
                    d_val = _check_perm_map(dept_perms, sub_code)
                    if d_val is False:
                        return False
                return True
            # If not in role_perms, check if dept grants it
            if dept_perms is not None and isinstance(dept_perms, dict):
                d_val = _check_perm_map(dept_perms, sub_code)
                if d_val is True:
                    return True
            return False

        # 2. If only department permissions exist in DB:
        if dept_perms is not None and isinstance(dept_perms, dict):
            d_val = _check_perm_map(dept_perms, sub_code)
            if d_val is not None:
                return d_val

        # 3. Fallback to user role menu mapping
        return bool(user.can_access_menu(sub_code))

    # 3. Filter modules & submodules strictly
    has_admin_mod_added = False

    for mod in modules:
        active_subs = []
        all_mod_subs = list(mod.submodules.filter(is_active=True).order_by('order', 'id'))

        for sub in all_mod_subs:
            if _is_submodule_permitted(sub.code):
                active_subs.append(sub)

        # Include parent module ONLY if it has at least one permitted submodule,
        # OR if it's a standalone single-link module explicitly granted
        mod_is_granted = False
        if role_perms and isinstance(role_perms, dict) and mod.code in role_perms:
            mod_is_granted = bool(role_perms[mod.code])
        elif dept_perms and isinstance(dept_perms, dict) and mod.code in dept_perms:
            mod_is_granted = bool(dept_perms[mod.code])

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
