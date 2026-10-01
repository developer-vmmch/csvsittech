from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    RoleMenuPermissionsView, NavBarMappingView, StaffListView, RoleOverviewView, RoleCreateView,
    LandingDepartmentManagerView, landing_department_create, landing_department_edit,
    landing_department_delete, landing_department_toggle_active, landing_department_reset_defaults,
    ModuleSubmoduleManagerView,
    check_username_api,
    nav_module_create, nav_module_edit, nav_module_rename, nav_module_toggle_active, nav_module_delete,
    nav_submodule_create, nav_submodule_edit, nav_submodule_rename, nav_submodule_remap, nav_submodule_toggle_active, nav_submodule_delete,
    nav_reset_defaults,
    UserProfileUpdateView, UserPasswordChangeView,
    ThemeSettingsView, save_theme_preference_api,
)

app_name = 'users'

urlpatterns = [
    path('', UserListView.as_view(), name='list'),
    path('users/', UserListView.as_view(), name='user_list_alias'),
    path('roles/', RoleOverviewView.as_view(), name='roles_alias'),
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('roles-overview/', RoleOverviewView.as_view(), name='roles_overview'),
    path('landing-departments/', LandingDepartmentManagerView.as_view(), name='landing_departments'),
    path('landing-departments/add/', landing_department_create, name='landing_department_create'),
    path('landing-departments/<int:pk>/edit/', landing_department_edit, name='landing_department_edit'),
    path('landing-departments/<int:pk>/delete/', landing_department_delete, name='landing_department_delete'),
    path('landing-departments/<int:pk>/toggle-active/', landing_department_toggle_active, name='landing_department_toggle_active'),
    path('landing-departments/reset-defaults/', landing_department_reset_defaults, name='landing_department_reset_defaults'),
    
    # Dedicated Module & Submodule Management
    path('modules/', ModuleSubmoduleManagerView.as_view(), name='module_manager'),
    path('modules-management/', ModuleSubmoduleManagerView.as_view(), name='modules_management_alias'),
    path('modules/add/', nav_module_create, name='nav_module_create'),
    path('modules/<int:pk>/edit/', nav_module_edit, name='nav_module_edit'),
    path('modules/<int:pk>/rename/', nav_module_rename, name='nav_module_rename'),
    path('modules/<int:pk>/toggle-active/', nav_module_toggle_active, name='nav_module_toggle_active'),
    path('modules/<int:pk>/delete/', nav_module_delete, name='nav_module_delete'),
    path('submodules/add/', nav_submodule_create, name='nav_submodule_create'),
    path('submodules/<int:pk>/edit/', nav_submodule_edit, name='nav_submodule_edit'),
    path('submodules/<int:pk>/rename/', nav_submodule_rename, name='nav_submodule_rename'),
    path('submodules/<int:pk>/remap/', nav_submodule_remap, name='nav_submodule_remap'),
    path('submodules/<int:pk>/toggle-active/', nav_submodule_toggle_active, name='nav_submodule_toggle_active'),
    path('submodules/<int:pk>/delete/', nav_submodule_delete, name='nav_submodule_delete'),
    path('modules/reset-defaults/', nav_reset_defaults, name='nav_reset_defaults'),
    
    # Nav Bar Mapping & Permissions
    path('navbar-mapping/', NavBarMappingView.as_view(), name='navbar_mapping'),
    path('navbar-mapping/modules/add/', nav_module_create, name='navbar_mapping_mod_add'),
    path('navbar-mapping/modules/<int:pk>/edit/', nav_module_edit, name='navbar_mapping_mod_edit'),
    path('navbar-mapping/modules/<int:pk>/rename/', nav_module_rename, name='navbar_mapping_mod_rename'),
    path('navbar-mapping/modules/<int:pk>/delete/', nav_module_delete, name='navbar_mapping_mod_delete'),
    path('navbar-mapping/submodules/add/', nav_submodule_create, name='navbar_mapping_sub_add'),
    path('navbar-mapping/submodules/<int:pk>/edit/', nav_submodule_edit, name='navbar_mapping_sub_edit'),
    path('navbar-mapping/submodules/<int:pk>/rename/', nav_submodule_rename, name='navbar_mapping_sub_rename'),
    path('navbar-mapping/submodules/<int:pk>/remap/', nav_submodule_remap, name='navbar_mapping_sub_remap'),
    path('navbar-mapping/submodules/<int:pk>/delete/', nav_submodule_delete, name='navbar_mapping_sub_delete'),
    path('navbar-mapping/reset-defaults/', nav_reset_defaults, name='navbar_mapping_reset_defaults'),
    
    path('roles/access-matrix/', RoleMenuPermissionsView.as_view(), name='role_permissions'),
    path('roles/add/', RoleCreateView.as_view(), name='role_add'),
    path('add/', UserCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='delete'),
    path('api/check-username/', check_username_api, name='api_check_username'),
    # Self-service profile and password
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('profile/change-password/', UserPasswordChangeView.as_view(), name='change_password'),
    path('settings/theme/', ThemeSettingsView.as_view(), name='theme_settings_alias'),
    path('settings/theme/save/', save_theme_preference_api, name='save_theme_preference_alias'),
    path('web-theme/', ThemeSettingsView.as_view(), name='web_theme_alias'),
    path('web-theme/save/', save_theme_preference_api, name='web_theme_save_alias'),
]
