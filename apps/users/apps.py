from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_default_admin(sender, **kwargs):
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@vmmc.edu.in', 'admin123')
            admin.role = 'ADMIN'
            admin.first_name = 'Administrator'
            admin.save()
    except Exception:
        pass

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'

    def ready(self):
        post_migrate.connect(create_default_admin, sender=self)
