import os
import re

base_template = """{% extends "base.html" %}

{% block title %}{title} | VMMCerp{% endblock %}
{% block page_heading %}{title}{% endblock %}

{% block content %}
<!-- Page Header Area -->
<div style="margin-bottom: 1.5rem;">
    <!-- Breadcrumb -->
    <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 1rem;">
        Home <i class="bi bi-chevron-right" style="font-size: 0.7rem; margin: 0 0.25rem;"></i> Lab Master <i class="bi bi-chevron-right" style="font-size: 0.7rem; margin: 0 0.25rem;"></i> <span style="color: #0f172a; font-weight: 600;">{title}</span>
    </div>
    
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="background-color: #0d6efd; color: white; width: 50px; height: 50px; border-radius: 8px; display: flex; justify-content: center; align-items: center; font-size: 1.5rem;">
                <i class="{icon}"></i>
            </div>
            <div>
                <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #0f172a;">{title} Setup</h1>
                <p style="margin: 0; font-size: 0.9rem; color: #475569;">Manage {title_lower}</p>
            </div>
        </div>
        <div>
            <button class="btn" style="background-color: #dcfce7; color: #166534; font-weight: 600; border: none; padding: 0.5rem 1rem; border-radius: 6px;">
                <i class="bi bi-grid-3x3-gap-fill" style="margin-right: 0.25rem;"></i> Lab Master
            </button>
        </div>
    </div>
</div>

<!-- Alert Notifications -->
<div id="notificationArea" style="display: none; padding: 1rem; margin-bottom: 1.5rem; border-radius: 6px;"></div>

<!-- Add / Edit Card -->
<div class="card" style="margin-bottom: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); background: white;">
    <div class="card-header" style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-radius: 8px 8px 0 0;">
        <h5 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #1e40af; display: flex; align-items: center; gap: 0.5rem;">
            <i class="bi bi-plus-circle-fill"></i> Add / Edit {title}
        </h5>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span style="color: #ef4444; font-size: 0.85rem;">* Required fields</span>
            <div style="display: flex; gap: 0.5rem;">
                <button type="button" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0.35rem 0.75rem;">
                    <i class="bi bi-arrow-up"></i> Import
                </button>
                <button type="button" class="btn btn-sm" style="background-color: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; font-weight: 600; border-radius: 6px; padding: 0.35rem 0.75rem;">
                    <i class="bi bi-arrow-down"></i> Export
                </button>
            </div>
        </div>
    </div>
    
    <div class="card-body" style="padding: 1.5rem;">
        <form id="mainForm" onsubmit="saveRecord(event)">
            <input type="hidden" id="recordId" value="">
            {form_fields}
            
            <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1.5rem;">
                <button type="submit" id="btnSave" class="btn btn-primary" style="background-color: #0d6efd; min-width: 100px; font-weight: 600; border-radius: 6px;">
                    <i class="bi bi-save"></i> Save
                </button>
                <button type="button" id="btnClear" class="btn btn-secondary" style="background-color: #64748b; color: white; min-width: 100px; font-weight: 600; border-radius: 6px;" onclick="resetForm()">
                    <i class="bi bi-arrow-repeat"></i> Clear
                </button>
            </div>
        </form>
    </div>
</div>

<!-- List Card -->
<div class="card" style="border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); background: white;">
    <div class="card-header" style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-radius: 8px 8px 0 0;">
        <h5 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #1e40af; display: flex; align-items: center; gap: 0.5rem;">
            <i class="bi bi-list-ul"></i> {title} List
        </h5>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span style="font-size: 0.9rem; color: #475569; font-weight: 600;" id="total-count-badge">Total Records: {{{{ records|length }}}}</span>
            <select class="form-select form-select-sm" style="width: auto; border-color: #cbd5e1;">
                <option>10 per page</option>
                <option>25 per page</option>
                <option>50 per page</option>
            </select>
        </div>
    </div>
    
    <div class="card-body" style="padding: 1.5rem;">
        <div style="display: flex; gap: 0.75rem; margin-bottom: 1.5rem;">
            <div style="position: relative; flex: 1;">
                <i class="bi bi-search" style="position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: #64748b;"></i>
                <input type="text" id="searchInput" class="form-control" placeholder="Search..." style="padding-left: 2.75rem; border-color: #cbd5e1;">
            </div>
            <button type="button" class="btn btn-primary" onclick="filterTable()" style="background-color: #0d6efd; font-weight: 600; min-width: 100px; border-radius: 6px;">
                <i class="bi bi-search"></i> Search
            </button>
            <button type="button" class="btn btn-light" onclick="clearSearch()" style="border: 1px solid #cbd5e1; font-weight: 600; min-width: 100px; color: #334155; background-color: white; border-radius: 6px;">
                <i class="bi bi-arrow-repeat"></i> Reset
            </button>
        </div>

        <div class="table-responsive">
            <table id="dataTable" class="table" style="border: 1px solid #e2e8f0; margin-bottom: 1rem; width: 100%; text-align: left; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f8fafc;">
                        <th style="color: #1e293b; font-weight: 700; border-bottom: 1px solid #e2e8f0; padding: 0.75rem 1rem; width: 5%;">#</th>
                        {table_headers}
                        <th style="color: #1e293b; font-weight: 700; border-bottom: 1px solid #e2e8f0; padding: 0.75rem 1rem; width: 20%;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {{% for rec in records %}}
                    <tr id="row-{{{{ rec.id }}}}" data-search="{data_search_attrs}" style="border-bottom: 1px solid #e2e8f0;">
                        <td class="row-index" style="padding: 0.75rem 1rem; color: #334155;">{{{{ forloop.counter }}}}</td>
                        {table_cells}
                        <td style="padding: 0.75rem 1rem;">
                            <div style="display: flex; gap: 0.5rem;">
                                <button type="button" class="btn btn-sm btn-primary" style="background-color: #0d6efd; border-radius: 4px; padding: 0.25rem 0.75rem; font-size: 0.85rem;" onclick="editRecord({edit_args})">
                                    <i class="bi bi-pencil-fill"></i> Edit
                                </button>
                                <button type="button" class="btn btn-sm btn-danger" style="background-color: #ef4444; border-radius: 4px; padding: 0.25rem 0.75rem; font-size: 0.85rem;" onclick="deleteRecord('{{{{ rec.id }}}}')">
                                    <i class="bi bi-trash-fill"></i> Delete
                                </button>
                            </div>
                        </td>
                    </tr>
                    {{% empty %}}
                    <tr id="emptyRow">
                        <td colspan="10" style="text-align: center; padding: 2rem; color: #64748b;">
                            No records configured yet.
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
        
        <!-- Pagination -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
            <div style="color: #475569; font-size: 0.9rem;" id="pagination-info">Showing 1 to {{{{ records|length }}}} of {{{{ records|length }}}} records</div>
            <div style="display: flex; gap: 0.25rem;">
                <button class="btn btn-light btn-sm" style="border: 1px solid #e2e8f0; background: white;"><i class="bi bi-arrow-left"></i></button>
                <button class="btn btn-primary btn-sm" style="background-color: #0d6efd;">1</button>
                <button class="btn btn-light btn-sm" style="border: 1px solid #e2e8f0; background: white;"><i class="bi bi-arrow-right"></i></button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    let currentRowCount = {{{{ records|length }}}};
    
    document.addEventListener("DOMContentLoaded", function() {{
        updateCounts();
        
        document.getElementById('searchInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                filterTable();
            }}
        }});
    }});

    function showNotification(message, type) {{
        const area = document.getElementById('notificationArea');
        area.style.display = 'block';
        if (type === 'success') {{
            area.style.backgroundColor = '#dcfce7';
            area.style.color = '#166534';
            area.style.border = '1px solid #bbf7d0';
        }} else {{
            area.style.backgroundColor = '#fee2e2';
            area.style.color = '#991b1b';
            area.style.border = '1px solid #fecaca';
        }}
        area.innerHTML = `<strong>${{type === 'success' ? 'Success!' : 'Error!'}}</strong> ${{message}}`;
        setTimeout(() => {{ area.style.display = 'none'; }}, 5000);
    }}

    {reset_function}

    {edit_function}

    function clearSearch() {{
        document.getElementById('searchInput').value = '';
        filterTable();
    }}

    function filterTable() {{
        const search = document.getElementById('searchInput').value.toLowerCase();
        const rows = document.querySelectorAll('#dataTable tbody tr:not(#emptyRow)');
        let visible = 0;
        
        rows.forEach(row => {{
            const searchData = row.getAttribute('data-search') || '';
            if(searchData.includes(search)) {{
                row.style.display = '';
                visible++;
            }} else {{
                row.style.display = 'none';
            }}
        }});
        
        document.getElementById('pagination-info').innerText = `Showing 1 to ${{visible}} of ${{currentRowCount}} records`;
    }}

    function updateCounts() {{
        const badge = document.getElementById('total-count-badge');
        if(badge) badge.innerHTML = `Total Records: ${{currentRowCount}}`;
        const info = document.getElementById('pagination-info');
        if(info) info.innerText = `Showing 1 to ${{currentRowCount}} of ${{currentRowCount}} records`;
    }}
    
    function deleteRecord(id) {{
        if(confirm('Are you sure you want to delete this record?')) {{
            fetch(`{delete_url_prefix}${{id}}/delete/`, {{
                method: 'POST',
                headers: {{
                    'X-CSRFToken': '{{{{ csrf_token }}}}'
                }}
            }})
            .then(res => res.json())
            .then(data => {{
                if (data.status === 'success') {{
                    showNotification(data.message, 'success');
                    const row = document.getElementById('row-' + id);
                    if (row) row.remove();
                    currentRowCount--;
                    updateCounts();
                }} else {{
                    showNotification(data.message, 'error');
                }}
            }})
            .catch(err => {{
                showNotification('An unexpected error occurred while deleting.', 'error');
                console.error(err);
            }});
        }}
    }}

    {save_function}

    function escapeHtml(unsafe) {{
        return (unsafe || '').toString()
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }}

    {update_row_function}
</script>
{% endblock %}
"""

# Now write code to generate each specific template!
