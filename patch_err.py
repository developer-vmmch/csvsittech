import os
file_path = 'apps/lab/auto_trigger_views.py'
with open(file_path, 'r') as f:
    content = f.read()

# Replace exception handling to get full trace
content = content.replace("p_err = e", "import traceback; p_err = traceback.format_exc()")

with open(file_path, 'w') as f:
    f.write(content)
