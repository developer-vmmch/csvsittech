import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VMMCerp.settings")
django.setup()

from django.test import Client
from apps.users.models import User

c = Client()
user = User.objects.get(username='admin')
c.force_login(user)

response = c.get('/lab/auto-trigger/monthly/')
print("Status code:", response.status_code)
if response.status_code == 302:
    print("Redirect to:", response.url)
