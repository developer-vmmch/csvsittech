import re
import glob

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Search Box & Buttons
    search_pattern = re.compile(
        r'<div style="display: flex; gap: 0\.75rem; margin-bottom: 1\.5rem;">\s*'
        r'<div style="position: relative; flex: 1;">\s*'
        r'<i class="bi bi-search" style="position: absolute; left: 1rem; top: 50%; transform: translateY\(-50%\); color: #64748b;"></i>\s*'
        r'<input type="text" id="searchInput" class="form-control" placeholder="(.*?)" style="padding-left: 2\.75rem; border-color: #cbd5e1;">\s*'
        r'</div>\s*'
        r'<button type="button" class="btn btn-primary" onclick="filterTable\(\)".*?>\s*'
        r'<i class="bi bi-search"></i> Search\s*'
        r'</button>\s*'
        r'<button type="button" class="btn btn-light" onclick="clearSearch\(\)".*?>\s*'
        r'<i class="bi bi-arrow-repeat"></i> Reset\s*'
        r'</button>\s*'
        r'</div>',
        re.DOTALL
    )
    
    replacement_search = (
        r'<div style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: center;">\n'
        r'            <div style="position: relative; width: 100%; max-width: 360px;">\n'
        r'                <i class="bi bi-search" style="position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>\n'
        r'                <input type="text" id="searchInput" class="form-input" placeholder="\1" style="padding-left: 2.5rem;">\n'
        r'            </div>\n'
        r'            <button type="button" class="btn btn-primary" onclick="filterTable()">\n'
        r'                <i class="bi bi-search"></i> Search\n'
        r'            </button>\n'
        r'            <button type="button" class="btn btn-secondary" onclick="clearSearch()">\n'
        r'                <i class="bi bi-arrow-repeat"></i> Reset\n'
        r'            </button>\n'
        r'        </div>'
    )
    
    content = search_pattern.sub(replacement_search, content)
    
    # 2. Table row padding (cell padding)
    content = re.sub(r'padding:\s*0\.75rem\s+1rem;', 'padding: 0.4rem 0.75rem;', content)
    
    # 3. Card paddings
    content = re.sub(r'padding:\s*1\.5rem;', 'padding: 1rem;', content)
    content = re.sub(r'padding:\s*1rem\s+1\.5rem;', 'padding: 0.75rem 1.25rem;', content)
    
    # 4. Spacing between components
    content = re.sub(r'margin-bottom:\s*1\.5rem;\s*border:\s*1px\s*solid\s*#e2e8f0;', 'margin-bottom: 1rem; border: 1px solid #e2e8f0;', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

files = glob.glob('templates/lab/master/*.html')
for f in files:
    process_file(f)
print("Done processing.")
