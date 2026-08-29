import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()
client = Client()
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.create_superuser('testadmin', 'admin@test.com', 'password')

client.force_login(user)
response = client.get('/patients/?format=json&page=1&page_size=2&search=Ku')
print("JSON response:", json.loads(response.content))

response = client.get('/patients/?from_date=2026-05-01&to_date=2026-05-01')
print("HTML response context total_patients:", response.context['total_patients'])
print("HTML response context filtered_patients:", response.context['filtered_patients'])
