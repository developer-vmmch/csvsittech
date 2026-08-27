import os
import re

search_dirs = ['templates', 'apps']

for root, _, files in os.walk('.'):
    if not any(d in root for d in search_dirs):
        continue
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            # Simple regex to add onclick to <input type="date"
            if 'type="date"' in content and 'this.showPicker' not in content:
                new_content = re.sub(
                    r'(<input[^>]*type="date"[^>]*)>',
                    r'\1 onclick="if(this.showPicker) this.showPicker();">',
                    content
                )
                
                if new_content != content:
                    with open(path, 'w') as f:
                        f.write(new_content)
                    print(f"Updated {path}")
