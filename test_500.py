import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.conf import settings

settings.DEBUG = False
settings.ALLOWED_HOSTS = ['*']

User = get_user_model()
c = Client()
u = User.objects.first()
if u:
    print(f'Logging in as {u}')
    c.force_login(u)
    try:
        response = c.get('/dashboard/')
        print(f'Status: {response.status_code}')
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print('No users found')
