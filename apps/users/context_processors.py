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

    if modules.exists():
        if is_admin:
            # Administrator has universal full master access to ALL navigation modules and submodules
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

        # Non-admin users: Determine active department or role permissions
        active_dept_code = request.session.get('active_department') or getattr(user, 'department', '')
        active_dept_slug = request.session.get('active_department_slug')
        
        dept_perms = None
        if active_dept_code or active_dept_slug:
            dept_obj = None
            if active_dept_code:
                norm_code = str(active_dept_code).strip().lower().replace('-', '_')
                dept_obj = LandingDepartment.objects.filter(code__iexact=norm_code).first()
            if not dept_obj and active_dept_slug:
                norm_slug = str(active_dept_slug).strip().lower().replace('_', '-')
                dept_obj = LandingDepartment.objects.filter(slug__iexact=norm_slug).first()
            if not dept_obj and active_dept_code:
                dept_obj = LandingDepartment.objects.filter(name__iexact=str(active_dept_code).strip()).first()
                
            if dept_obj and dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict) and len(dept_obj.nav_permissions) > 0:
                dept_perms = dept_obj.nav_permissions
            elif active_dept_code and str(active_dept_code).strip().lower().replace('-', '_') in DEPT_DEFAULT_NAV_MAPPING:
                dept_perms = DEPT_DEFAULT_NAV_MAPPING.get(str(active_dept_code).strip().lower().replace('-', '_'))

        role_perms = user.get_menu_mapping() if hasattr(user, 'get_menu_mapping') else {}

        for mod in modules:
            if dept_perms is not None:
                mod_granted = dept_perms.get(mod.code, False)
            else:
                mod_granted = role_perms.get(mod.code, False)

            active_subs = []
            for sub in mod.submodules.filter(is_active=True).order_by('order', 'id'):
                if dept_perms is not None:
                    sub_granted = dept_perms.get(sub.code, False)
                else:
                    sub_granted = role_perms.get(sub.code, False)

                if sub_granted:
                    active_subs.append(sub)

            # Include module if explicitly granted or if user has permission to any of its submodules
            if mod_granted or len(active_subs) > 0:
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

    # Fallback to static config if DB records are unavailable
    for mod_cfg in NAVBAR_MODULES_CONFIG:
        subs = []
        for s in mod_cfg.get('submodules', []):
            subs.append({
                'name': s['name'],
                'icon': s['icon'],
                'url_path': s['url'],
            })
        primary_url = subs[0]['url_path'] if subs else '#'
        user_nav_modules.append({
            'id': mod_cfg['id'],
            'code': mod_cfg['key'],
            'name': mod_cfg['name'],
            'icon': mod_cfg['icon'],
            'url_path': primary_url,
            'color': mod_cfg.get('color', '#0284c7'),
            'badge': mod_cfg.get('badge', ''),
            'submodules': subs,
            'has_submodules': len(subs) > 0,
        })

    return {'dynamic_nav_modules': user_nav_modules}
