import os
import django
import pandas as pd
import io

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VMMCerp.settings')
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

# Create a sample dataframe based on the user's requirements
df = pd.DataFrame({
    'parameter_code': ['CBC-HB', 'CBC-WBC'],
    'investigation_code': ['00020537', '00020537'],
    'parameter_name': ['Hemoglobin', 'WBC Count'],
    'short_name': ['Hb', 'WBC'],
    'result_type': ['Numeric', 'Numeric'],
    'unit': ['g/dL', '10^3/uL'],
    'decimal_precision': [1, 1],
    'age_group_code': ['ADULT-MALE', 'ADULT-MALE'],
    'gender': ['Male', 'Male'],
    'min_age': [18, 18],
    'max_age': [120, 120],
    'age_unit': ['Years', 'Years'],
    'reference_min': [12.0, 4.0],
    'reference_max': [17.5, 11.0],
    'reference_text': ['', ''],
    'critical_low': [7.0, 2.0],
    'critical_high': [20.0, 30.0],
    'display_order': [1, 2],
    'active': ['Yes', 'Yes']
})

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Template')
output.seek(0)

# Simulate upload
client = Client()

# We need to bypass login/permissions or login as a superuser
from django.contrib.auth import get_user_model
User = get_user_model()
user, _ = User.objects.get_or_create(username='testadmin', is_superuser=True, is_staff=True)
client.force_login(user)

file = SimpleUploadedFile("test.xlsx", output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

response = client.post('/lab/api/parameter/import/preview/', {'file': file})
print(f"Status Code: {response.status_code}")
print(f"Response Content: {response.content}")
