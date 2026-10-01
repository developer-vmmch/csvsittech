from django.db import migrations


def seed_theme_navigation_and_permissions(apps, schema_editor):
    NavModule = apps.get_model('users', 'NavModule')
    NavSubmodule = apps.get_model('users', 'NavSubmodule')
    LandingDepartment = apps.get_model('users', 'LandingDepartment')

    # 1. Idempotently create or update NavModule: code="settings", name="WEB THEME"
    theme_module, _ = NavModule.objects.update_or_create(
        code="settings",
        defaults={
            "name": "WEB THEME",
            "icon": "bi-palette-fill",
            "url_path": "/settings/theme/",
            "color": "#0284c7",
            "badge": "Visual",
            "description": "Global hospital ERP theme engine, contrast protection, and typography",
            "order": 80,
            "is_active": True,
            "is_system": True,
        }
    )

    # 2. Idempotently create or update NavSubmodule: code="theme_settings"
    NavSubmodule.objects.update_or_create(
        code="theme_settings",
        defaults={
            "module": theme_module,
            "name": "Web Theme Settings",
            "icon": "bi-palette-fill",
            "url_path": "/settings/theme/",
            "description": "Customize global theme, colors, contrast, and typography",
            "order": 10,
            "is_active": True,
            "is_system": True,
        }
    )

    # Idempotently create or update NavSubmodule: code="settings" (System Configuration)
    NavSubmodule.objects.update_or_create(
        code="settings",
        defaults={
            "module": theme_module,
            "name": "System Configuration",
            "icon": "bi-sliders",
            "url_path": "#",
            "description": "General ERP parameters, hospital metadata, logo branding, and print formats",
            "order": 20,
            "is_active": True,
            "is_system": True,
        }
    )

    # 3. Update existing LandingDepartment records that have saved nav_permissions
    for dept in LandingDepartment.objects.all():
        if dept.nav_permissions and isinstance(dept.nav_permissions, dict):
            perms = dict(dept.nav_permissions)
            perms['theme_settings'] = True
            perms['theme_settings.view'] = True
            perms['theme_settings.change'] = True
            perms['settings'] = True
            dept.nav_permissions = perms
            dept.save(update_fields=['nav_permissions'])


def unseed_theme_navigation_and_permissions(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_user_theme_motion_alter_user_theme'),
    ]

    operations = [
        migrations.RunPython(
            seed_theme_navigation_and_permissions,
            reverse_code=unseed_theme_navigation_and_permissions,
        ),
    ]
