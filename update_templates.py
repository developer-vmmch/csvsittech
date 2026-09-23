import glob, re

templates = glob.glob('templates/**/*.html', recursive=True) + glob.glob('apps/**/*.html', recursive=True)

for t in templates:
    with open(t, 'r') as f:
        content = f.read()
    if 'type="date"' in content and 'auto_trigger/configuration' not in t:
        print(f"FOUND IN {t}")

