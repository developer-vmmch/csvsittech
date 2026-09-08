import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from apps.lab.models import ParameterReferenceRange, AgeGroup

# Delete ranges associated with DEFAULT_CBC
try:
    ag = AgeGroup.objects.get(code="DEFAULT_CBC")
    ParameterReferenceRange.objects.filter(age_group=ag).delete()
    print("Deleted old reference ranges with DEFAULT_CBC age group.")
except AgeGroup.DoesNotExist:
    pass

import seed_cbc_exact
seed_cbc_exact.seed()
