from .models import NavModule, NavSubmodule, LandingDepartment

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

    is_admin = user.is_superuser or getattr(user, 'role', '') == 'ADMIN'

    modules = NavModule.objects.filter(is_active=True).prefetch_related('submodules').order_by('order', 'id')
    user_nav_modules = []

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
            dept_obj = LandingDepartment.objects.filter(code__iexact=str(active_dept_code).strip().lower().replace('-', '_')).first()
        if not dept_obj and active_dept_slug:
            dept_obj = LandingDepartment.objects.filter(slug__iexact=str(active_dept_slug).strip().lower().replace('_', '-')).first()
        if not dept_obj and active_dept_code:
            dept_obj = LandingDepartment.objects.filter(name__iexact=str(active_dept_code).strip()).first()
            
        if dept_obj and dept_obj.nav_permissions and isinstance(dept_obj.nav_permissions, dict):
            dept_perms = dept_obj.nav_permissions

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

    return {
        'dynamic_nav_modules': user_nav_modules
    }
