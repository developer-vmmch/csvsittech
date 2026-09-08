import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.auto_trigger_views import api_get_dummy_results
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import json

User = get_user_model()
u = User.objects.first()
rf = RequestFactory()

# Test AEC
req = rf.get('/api/dummy-results/?investigation_id=9')
req.user = u
resp = api_get_dummy_results(req)
data = json.loads(resp.content)
grp = data['groups'][0]
print(f"=== AEC ===")
print(f"Total results: {len(grp['results'])}")
r = grp['results'][0]
print(f"Patient: {r['patient_name']} | Age: {r['patient_age']} | Gender: {r['patient_gender']}")
p = r['parameters'][0]
print(f"Param: {p['name']} | Value: {p['value']} | Unit: {p['unit']} | Range: {p['reference_range']}")

# Test CBC
req2 = rf.get('/api/dummy-results/?investigation_id=1')
req2.user = u
resp2 = api_get_dummy_results(req2)
data2 = json.loads(resp2.content)
grp2 = data2['groups'][0]
print(f"\n=== CBC ===")
print(f"Total results: {len(grp2['results'])}")
r2 = grp2['results'][0]
print(f"Patient: {r2['patient_name']} | Age: {r2['patient_age']}")
print("First 5 params:")
for p2 in r2['parameters'][:5]:
    print(f"  {p2['name']} | val={p2['value']} | unit={p2['unit']} | range={p2['reference_range']}")
