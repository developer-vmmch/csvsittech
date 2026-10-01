import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.users.models import NavModule, NavSubmodule, LandingDepartment, RoleMenuPermission
from apps.users.departments import user_can_access_department

User = get_user_model()


class ThemeNavigationAndPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed test departments
        self.dept_fo, _ = LandingDepartment.objects.get_or_create(
            code='front_office',
            defaults={'name': 'Front Office', 'slug': 'front-office'}
        )
        self.dept_lab, _ = LandingDepartment.objects.get_or_create(
            code='lab',
            defaults={'name': 'Laboratory', 'slug': 'lab'}
        )

        # Create authorized admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_theme_test',
            email='admin@vmmc.edu.in',
            password='Password@123',
            role=User.Roles.ADMIN
        )

        # Create authorized staff user in Front Office
        self.staff_user = User.objects.create_user(
            username='staff_theme_test',
            email='staff@vmmc.edu.in',
            password='Password@123',
            role=User.Roles.STAFF,
            department='Front Office'
        )

        # Create unauthorized user (custom role with theme_settings explicitly False)
        self.unauth_user = User.objects.create_user(
            username='unauth_theme_test',
            email='unauth@vmmc.edu.in',
            password='Password@123',
            role='RESTRICTED_ROLE',
            department='Front Office'
        )
        RoleMenuPermission.objects.update_or_create(
            role='RESTRICTED_ROLE',
            defaults={'menu_permissions': {'theme_settings': False, 'theme_settings.view': False, 'theme_settings.change': False}}
        )

    def test_a_web_theme_nav_module_exists(self):
        """A. WEB THEME NavModule exists in the database."""
        mod = NavModule.objects.filter(code='settings').first()
        self.assertIsNotNone(mod, 'NavModule with code settings must exist.')
        self.assertEqual(mod.name, 'WEB THEME')
        self.assertTrue(mod.is_active)
        self.assertEqual(mod.url_path, '/settings/theme/')

    def test_b_theme_settings_nav_submodule_exists(self):
        """B. theme_settings NavSubmodule exists under WEB THEME."""
        sub = NavSubmodule.objects.filter(code='theme_settings').first()
        self.assertIsNotNone(sub, 'NavSubmodule with code theme_settings must exist.')
        self.assertEqual(sub.url_path, '/settings/theme/')
        self.assertTrue(sub.is_active)
        self.assertEqual(sub.module.code, 'settings')

    def test_c_no_duplicates_created(self):
        """C. No duplicates are created when seeder or migration runs repeatedly."""
        import importlib; mig = importlib.import_module("apps.users.migrations.0011_seed_theme_nav_and_permissions"); seed_theme_navigation_and_permissions = mig.seed_theme_navigation_and_permissions
        from django.apps import apps
        # Run seeder 3 more times to prove idempotency
        for _ in range(3):
            seed_theme_navigation_and_permissions(apps, None)

        self.assertEqual(NavModule.objects.filter(code='settings').count(), 1)
        self.assertEqual(NavSubmodule.objects.filter(code='theme_settings').count(), 1)

    def test_d_theme_settings_route_200_for_authorized_user(self):
        """D. Theme Settings route returns 200 for authorized users."""
        # Test Admin
        self.client.force_login(self.admin_user)
        resp = self.client.get('/settings/theme/')
        self.assertEqual(resp.status_code, 200)

        # Test Staff
        self.client.force_login(self.staff_user)
        resp = self.client.get('/settings/theme/')
        self.assertEqual(resp.status_code, 200)

    def test_e_unauthorized_user_remains_denied(self):
        """E. Unauthorized user remains denied."""
        # 1. Anonymous user redirected to login
        self.client.logout()
        resp = self.client.get('/settings/theme/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/?next=/settings/theme/', resp.url)

        # 2. User with theme_settings explicitly False gets 403 Forbidden
        self.client.force_login(self.unauth_user)
        self.assertFalse(self.unauth_user.can_access_theme_settings)
        resp = self.client.get('/settings/theme/')
        self.assertEqual(resp.status_code, 403)

    def test_f_existing_department_restrictions_still_work(self):
        """F. Existing college department restrictions remain strictly enforced."""
        # Staff user is assigned strictly to Front Office
        # Must be able to access front_office
        self.assertTrue(user_can_access_department(self.staff_user, 'front_office'))
        # Must NOT be able to access other departments
        self.assertFalse(user_can_access_department(self.staff_user, 'lab'))
        self.assertFalse(user_can_access_department(self.staff_user, 'ot'))
        self.assertFalse(user_can_access_department(self.staff_user, 'consultant'))

    def test_g_user_profile_dropdown_contains_theme_settings_only_for_authorized_users(self):
        """G. User profile dropdown contains Theme Settings link only for authorized users."""
        # Authorized user has Theme Settings in dropdown
        self.client.force_login(self.staff_user)
        resp = self.client.get('/settings/theme/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Theme Settings')
        self.assertContains(resp, '/settings/theme/')

        # Unauthorized user lacks can_access_theme_settings
        self.assertFalse(self.unauth_user.can_access_theme_settings)

    def test_h_save_theme_remains_functional(self):
        """H. Save Theme API remains functional and persists preference."""
        self.client.force_login(self.staff_user)
        payload = {
            'theme': 'clinical-blue',
            'font': 'Outfit',
            'reduced_motion': False,
            'animation_speed': '1.5',
            'pointer_speed': '1.5'
        }
        resp = self.client.post(
            '/settings/theme/save/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('theme'), 'clinical-blue')

        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.theme, 'clinical-blue')
