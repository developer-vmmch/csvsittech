import os
import glob
import re

template_dir = 'templates/lab/master/'
files = glob.glob(os.path.join(template_dir, '*list.html')) + \
        glob.glob(os.path.join(template_dir, '*mapping.html')) + \
        [os.path.join(template_dir, 'reference_range_grid.html')]

pagination_html = """
        <!-- Pagination -->
        {% if is_paginated or page_obj %}
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; flex-wrap: wrap; gap: 0.75rem;">
            <div style="color: #64748b; font-size: 0.85rem; font-weight: 500;">
                Showing {{ page_obj.start_index }}–{{ page_obj.end_index }} of {{ page_obj.paginator.count }} entries
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                <div style="display: flex; gap: 0.2rem;">
                    {% if page_obj.has_previous %}
                    <a href="?page=1&search={{ request.GET.search }}" class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px;" title="First">&laquo;</a>
                    <a href="?page={{ page_obj.previous_page_number }}&search={{ request.GET.search }}" class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px;" title="Previous">&lsaquo;</a>
                    {% else %}
                    <span class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px; opacity:0.4; cursor:not-allowed;">&laquo;</span>
                    <span class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px; opacity:0.4; cursor:not-allowed;">&lsaquo;</span>
                    {% endif %}

                    <span class="btn btn-primary" style="padding:0.25rem 0.6rem; font-size:0.8rem; border-radius:5px; background:var(--accent-blue); color:#fff; border-color:var(--accent-blue); font-weight:700; pointer-events:none;">
                        {{ page_obj.number }}
                    </span>
                    <span style="padding:0.25rem 0.2rem; font-size:0.8rem; color:#64748b;">of {{ page_obj.paginator.num_pages }}</span>

                    {% if page_obj.has_next %}
                    <a href="?page={{ page_obj.next_page_number }}&search={{ request.GET.search }}" class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px;" title="Next">&rsaquo;</a>
                    <a href="?page={{ page_obj.paginator.num_pages }}&search={{ request.GET.search }}" class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px;" title="Last">&raquo;</a>
                    {% else %}
                    <span class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px; opacity:0.4; cursor:not-allowed;">&rsaquo;</span>
                    <span class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.8rem; border-radius:5px; opacity:0.4; cursor:not-allowed;">&raquo;</span>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endif %}
"""

for file in set(files):
    if not os.path.exists(file):
        continue
    with open(file, 'r') as f:
        content = f.read()

    # Replace Search Input UI
    # From: <div style="position: relative; width: 100%; max-width: 360px;">...<input type="text" id="searchInput" class="form-input" placeholder="..."></div>
    # To: <form method="get" style="display:flex; gap:0.5rem;"><input type="text" name="search" value="{{ request.GET.search }}" class="form-input" ...></form>
    search_div_pattern = r'<div style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: center;">(.*?)</div>\s*<div class="table-responsive">'
    
    def repl_search(m):
        inner = m.group(1)
        # Check if it already has <form
        if '<form' in inner: return m.group(0)
        
        # We need to extract the placeholder from the existing input
        placeholder = 'Search...'
        p_match = re.search(r'placeholder="([^"]+)"', inner)
        if p_match: placeholder = p_match.group(1)
        
        form_html = f'''
        <form method="get" action="" style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: center; width: 100%;">
            <div style="position: relative; width: 100%; max-width: 360px;">
                <i class="bi bi-search" style="position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--text-muted);"></i>
                <input type="text" name="search" value="{{{{ request.GET.search }}}}" class="form-input" placeholder="{placeholder}" style="padding-left: 2.5rem;">
            </div>
            <button type="submit" class="btn btn-primary">
                <i class="bi bi-search"></i> Search
            </button>
            <a href="?" class="btn btn-secondary">
                <i class="bi bi-arrow-repeat"></i> Reset
            </a>
        </form>
        '''
        return form_html + '\n        <div class="table-responsive">'
        
    content = re.sub(search_div_pattern, repl_search, content, flags=re.DOTALL)
    
    # Replace Pagination Block
    # Old pagination starts with <!-- Pagination -->
    pag_pattern = r'<!-- Pagination -->.*?</div>\s*</div>\s*</div>'
    
    def repl_pag(m):
        return pagination_html + '    </div>\n</div>'
        
    content = re.sub(pag_pattern, repl_pag, content, flags=re.DOTALL)
    
    # Also replace Total Records count in the header from {{ diagnoses|length }} to {{ page_obj.paginator.count }}
    content = re.sub(r'Total Records: \{\{.*?\|length \}\}', r'Total Records: {{ page_obj.paginator.count|default:0 }}', content)
    
    # Remove JS filterTable and clearSearch
    content = re.sub(r'function filterTable\(\) \{.*?\n    \}\n', '', content, flags=re.DOTALL)
    content = re.sub(r'function clearSearch\(\) \{.*?\n    \}\n', '', content, flags=re.DOTALL)
    
    with open(file, 'w') as f:
        f.write(content)

