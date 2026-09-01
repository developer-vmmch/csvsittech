import sys
from django.test import Client
from apps.users.models import User

c = Client()
user = User.objects.get(username='admin')
c.force_login(user)

for path in [
    '/lab/auto-trigger/monthly/',
    '/lab/auto-trigger/automate-test/',
    '/lab/auto-trigger/result-view/'
]:
    response = c.get(path)
    print(f"Path: {path} | Status: {response.status_code}")
    if response.status_code == 302:
        print(f"Redirect to: {response.url}")
