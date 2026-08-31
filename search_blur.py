import os

def search_dir(d):
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith('.js') or f.endswith('.html'):
                path = os.path.join(root, f)
                with open(path, 'r', errors='ignore') as file:
                    for i, line in enumerate(file):
                        if 'blur' in line.lower():
                            print(f"{path}:{i+1}: {line.strip()}")

search_dir('static')
search_dir('apps')
search_dir('templates')
