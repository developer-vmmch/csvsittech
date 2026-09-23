with open('apps/lab/auto_trigger_views.py', 'r') as f:
    content = f.read()

replacement = """        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        from django.utils import timezone
        from datetime import timedelta
        context['default_from_date'] = (timezone.localdate() - timedelta(days=6)).strftime('%Y-%m-%d')
        context['default_to_date'] = timezone.localdate().strftime('%Y-%m-%d')"""

content = content.replace("        context['departments'] = Department.objects.filter(is_active=True).order_by('name')", replacement)

with open('apps/lab/auto_trigger_views.py', 'w') as f:
    f.write(content)
