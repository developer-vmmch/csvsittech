from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    RoleMenuPermissionsView, NavBarMappingView, StaffListView, RoleOverviewView, RoleCreateView,
    LandingDepartmentManagerView, landing_department_create, landing_department_edit,
    landing_department_delete, landing_department_toggle_active, landing_department_reset_defaults,
    check_username_api,
    nav_module_create, nav_module_edit, nav_module_rename, nav_module_delete,
    nav_submodule_create, nav_submodule_edit, nav_submodule_rename, nav_submodule_remap, nav_submodule_delete,
    nav_reset_defaults
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
    path('navbar-mapping/', NavBarMappingView.as_view(), name='navbar_mapping'),
    path('navbar-mapping/modules/add/', nav_module_create, name='nav_module_create'),
    path('navbar-mapping/modules/<int:pk>/edit/', nav_module_edit, name='nav_module_edit'),
    path('navbar-mapping/modules/<int:pk>/rename/', nav_module_rename, name='nav_module_rename'),
    path('navbar-mapping/modules/<int:pk>/delete/', nav_module_delete, name='nav_module_delete'),
    path('navbar-mapping/submodules/add/', nav_submodule_create, name='nav_submodule_create'),
    path('navbar-mapping/submodules/<int:pk>/edit/', nav_submodule_edit, name='nav_submodule_edit'),
    path('navbar-mapping/submodules/<int:pk>/rename/', nav_submodule_rename, name='nav_submodule_rename'),
    path('navbar-mapping/submodules/<int:pk>/remap/', nav_submodule_remap, name='nav_submodule_remap'),
    path('navbar-mapping/submodules/<int:pk>/delete/', nav_submodule_delete, name='nav_submodule_delete'),
    path('navbar-mapping/reset-defaults/', nav_reset_defaults, name='nav_reset_defaults'),
    path('roles/access-matrix/', RoleMenuPermissionsView.as_view(), name='role_permissions'),
    path('roles/add/', RoleCreateView.as_view(), name='role_add'),
    path('add/', UserCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='delete'),
    path('api/check-username/', check_username_api, name='api_check_username'),
]
