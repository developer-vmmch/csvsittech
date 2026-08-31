import re

# 1. Update WorkOrdersView in apps/lab/views.py
with open('apps/lab/views.py', 'r') as f:
    content = f.read()

replacement = """        context['statuses'] = ServiceRequestInvestigation.StatusChoices.choices
        from django.utils import timezone
        from datetime import timedelta
        context['default_from_date'] = (timezone.localdate() - timedelta(days=6)).strftime('%Y-%m-%d')
        context['default_to_date'] = timezone.localdate().strftime('%Y-%m-%d')"""

content = content.replace("        context['statuses'] = ServiceRequestInvestigation.StatusChoices.choices", replacement)

with open('apps/lab/views.py', 'w') as f:
    f.write(content)

# 2. Update work_orders.html
with open('apps/lab/templates/lab/orders/work_orders.html', 'r') as f:
    html = f.read()

html = html.replace('value="{% now \'Y-m-d\' %}" onclick="if(this.showPicker)', 'value="{{ default_from_date }}" onclick="if(this.showPicker)')
html = html.replace('value="{% now \'Y-m-d\' %}" onclick="if(this.showPicker)', 'value="{{ default_to_date }}" onclick="if(this.showPicker)')
# Since the replace above might replace all with from_date, I need to do it precisely.

