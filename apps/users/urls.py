from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    RoleMenuPermissionsView, ProfilePermissionsView, StaffListView, RoleOverviewView, RoleCreateView,
    check_username_api
)

app_name = 'users'

urlpatterns = [
    path('', UserListView.as_view(), name='list'),
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('roles-overview/', RoleOverviewView.as_view(), name='roles_overview'),
    path('roles/access-matrix/', RoleMenuPermissionsView.as_view(), name='role_permissions'),
    path('roles/permissions/', ProfilePermissionsView.as_view(), name='profile_permissions'),
    path('roles/add/', RoleCreateView.as_view(), name='role_add'),
    path('add/', UserCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', UserUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', UserDeleteView.as_view(), name='delete'),
    path('api/check-username/', check_username_api, name='api_check_username'),
]
