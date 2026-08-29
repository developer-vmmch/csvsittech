import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from apps.lab.models import Investigation, AgeGroup, Diagnosis, Parameter, InvestigationParameter

client = Client()

from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
if not admin:
    admin = User.objects.create_superuser('admin_test', 'admin@example.com', 'pass')
client.force_login(admin)

print("--- 1. Testing Page Load ---")
res = client.get('/lab/reference-range/')
if res.status_code == 200:
    print("SUCCESS: Page loaded with 200 OK")
else:
    print(f"FAILED: Page load returned {res.status_code}")

print("\n--- 2. Testing Diagnosis Search API ---")
res = client.get('/lab/api/service-request/diagnoses/?q=')
print(f"Status: {res.status_code}, Data: {res.json().get('results', [])[:2]}")

print("\n--- 3. Testing Age Group Search API ---")
res = client.get('/lab/api/age-group/search/?q=')
print(f"Status: {res.status_code}, Data: {res.json().get('results', [])[:2]}")

print("\n--- 4. Testing Investigation Search API ---")
res = client.get('/lab/api/service-request/search-investigation/?q=')
print(f"Status: {res.status_code}, Data: {res.json().get('results', [])[:2]}")

# Pick valid IDs if available
inv = Investigation.objects.filter(name='CBC').first()
ag = AgeGroup.objects.first()

if inv and ag:
    print(f"\n--- 5. Testing Parameters Load for Investigation {inv.id} ---")
    res = client.get(f'/lab/api/investigation-parameters/?investigation_id={inv.id}')
    print(f"Status: {res.status_code}, Data: {res.json()}")
    
    params = res.json().get('parameters', [])
    if params:
        print("\n--- 6. Testing Save Grid ---")
        payload = {
            "diagnosis_id": None,
            "age_group_id": ag.id,
            "investigation_id": inv.id,
            "gender": "All",
            "parameters": [
                {
                    "investigation_parameter_id": params[0]['id'],
                    "unit": "g/dL",
                    "min_value": "10",
                    "max_value": "15",
                    "critical_low": "8",
                    "critical_high": "18",
                    "is_active": True
                }
            ]
        }
        res = client.post('/lab/api/reference-ranges-grid/save/', data=payload, content_type='application/json')
        print(f"Status: {res.status_code}, Response: {res.json()}")
        
        print("\n--- 7. Testing Grid List ---")
        res = client.get('/lab/api/reference-ranges-grid/list/')
        print(f"Status: {res.status_code}, Data: {res.json()}")
    else:
        print("\nSkipping Save Grid test, no mapped parameters found for this investigation.")
else:
    print("\nSkipping Parameter tests, no Investigation or AgeGroup found in DB.")
