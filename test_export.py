import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.create_superuser('testadmin2', 'admin2@test.com', 'password')

client.force_login(user)
response = client.get('/patients/?export=excel&columns=Patient%20ID,Patient%20Name,Gender%20/%20Age,Guardian,Registration%20Date')
print("Status:", response.status_code)
print("Content-Disposition:", response.get('Content-Disposition'))
print("File length:", len(response.content))
