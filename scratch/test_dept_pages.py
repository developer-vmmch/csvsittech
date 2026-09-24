import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')

import django
django.setup()

from django.test import Client
from apps.users.departments import get_all_departments

c = Client()
r = c.get('/login/')
print(f"Department Selection Page: HTTP {r.status_code}")
assert r.status_code == 200

departments = get_all_departments()
print(f"Total Departments: {len(departments)}")

for d in departments:
    slug = d['slug']
    name = d['name']
    resp = c.get(f"/login/{slug}/")
    bg = d.get('bg_image', 'NONE')
    print(f"  -> [{slug}] {name}: HTTP {resp.status_code} | BG: {bg}")
    assert resp.status_code == 200, f"Error rendering {slug}"

print("\nSUCCESS: All 16 department login pages and the main department selection page tested successfully!")
