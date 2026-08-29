import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.core.management import call_command
