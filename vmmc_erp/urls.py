from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.users.views import ERPLoginView, ERPLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', ERPLoginView.as_view(), name='login'),
    path('login/', ERPLoginView.as_view()),
    path('logout/', ERPLogoutView.as_view(), name='logout'),
    path('dashboard/', include(('apps.core.urls', 'core'), namespace='core')),
    path('patients/', include('apps.patients.urls')),
    path('lab/', include(('apps.lab.urls', 'lab'), namespace='lab')),
    path('administration/', include(('apps.users.urls', 'users'), namespace='users')),
    path('ot/', include(('apps.ot.urls', 'ot'), namespace='ot')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
