import os
import threading
from django.apps import AppConfig

def start_scheduler():
    from django.core.management import call_command
    call_command('run_monthly_scheduler')

class LabConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.lab'
    
    def ready(self):
        # Run only in the main Django server process, not in the autoreloader process
        if os.environ.get('RUN_MAIN') == 'true':
            thread = threading.Thread(target=start_scheduler, daemon=True)
            thread.start()
