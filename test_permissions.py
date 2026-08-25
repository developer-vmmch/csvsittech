import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vmmc_erp.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import RoleMenuPermission, CustomRole

User = get_user_model()

print("Setting up Roles...")
admin, _ = User.objects.get_or_create(username='admin', defaults={'role': 'ADMIN', 'is_superuser': True})
lab_tech_role, _ = CustomRole.objects.get_or_create(code='LAB_TECH', name='Lab Technician')
lab_tech_user, _ = User.objects.get_or_create(username='lab_tech_user', defaults={'role': 'LAB_TECH'})

print("Admin has patient_list.delete?", admin.has_perm_code('patients.patient_list.delete'))
print("Lab Tech has patient_list.delete initially?", lab_tech_user.has_perm_code('patients.patient_list.delete'))

RoleMenuPermission.objects.update_or_create(
    role='LAB_TECH',
    defaults={'menu_permissions': {'patients.patient_list.delete': True}}
)

print("Lab Tech has patient_list.delete after setting?", lab_tech_user.has_perm_code('patients.patient_list.delete'))

print("All tests completed.")
