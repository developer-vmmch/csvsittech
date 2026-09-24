from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views import DepartmentSelectView, DepartmentLoginView, RoleLoginView, ERPLogoutView
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DepartmentSelectView.as_view(), name='login'),
    path('login/', DepartmentSelectView.as_view(), name='department_select'),
    path('login/role/<slug:role_slug>/', RoleLoginView.as_view(), name='role_login'),
    path('login/<slug:dept_slug>/', DepartmentLoginView.as_view(), name='dept_login'),
    path('logout/', ERPLogoutView.as_view(), name='logout'),
    path('dashboard/', include(('apps.core.urls', 'core'), namespace='core')),
    path('patients/', include('apps.patients.urls')),
    path('lab/', include(('apps.lab.urls', 'lab'), namespace='lab')),
    path('administration/', include(('apps.users.urls', 'users'), namespace='users')),
    path('users/', RedirectView.as_view(url='/administration/', permanent=False)),
    path('users/<path:subpath>/', RedirectView.as_view(url='/administration/%(subpath)s/', permanent=False)),
    path('ot/', include(('apps.ot.urls', 'ot'), namespace='ot')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
