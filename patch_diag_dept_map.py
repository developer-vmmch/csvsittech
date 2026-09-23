import re

file_path = 'templates/lab/master/diagnosis_department_mapping.html'
with open(file_path, 'r') as f:
    content = f.read()

# Remove the Import Modal
content = re.sub(r'<!-- Import Modal.*?</div>\s*</div>\s*</div>\s*</div>', '', content, flags=re.DOTALL)

# Add extra_css for form-grid and select2
extra_css = """
{% block extra_css %}
<link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
<style>
.form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
}
@media (max-width: 768px) {
    .form-grid {
        grid-template-columns: 1fr;
    }
}
.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.form-group label {
    font-weight: 600;
    color: #475569;
    font-size: 0.9rem;
}
.form-select, .form-input {
    padding: 0.5rem 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 0.95rem;
    color: #1e293b;
    width: 100%;
}
.select2-container .select2-selection--single {
    height: 38px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
}
.select2-container--default .select2-selection--single .select2-selection__rendered {
    line-height: 36px;
    padding-left: 0.75rem;
}
.select2-container--default .select2-selection--single .select2-selection__arrow {
    height: 36px;
}
</style>
{% endblock %}
"""

if "{% block extra_css %}" not in content:
    content = content.replace("{% block content %}", extra_css + "\n{% block content %}")

# Fix select2 classes
content = content.replace('id="diagnosis" class="form-select"', 'id="diagnosis" class="form-select select2"')
content = content.replace('id="department" class="form-select"', 'id="department" class="form-select select2"')

# Fix per_page selector
old_select = """<select class="form-select form-select-sm" style="width: auto; border-color: #cbd5e1;">
                <option>10 per page</option>
                <option>25 per page</option>
                <option>50 per page</option>
            </select>"""
new_select = """<select class="form-select form-select-sm" style="width: auto; border-color: #cbd5e1;" onchange="window.location.href='?per_page='+this.value+'&search={{ request.GET.search }}'">
                <option value="20" {% if request.GET.per_page == '20' or not request.GET.per_page %}selected{% endif %}>20 per page</option>
                <option value="50" {% if request.GET.per_page == '50' %}selected{% endif %}>50 per page</option>
                <option value="100" {% if request.GET.per_page == '100' %}selected{% endif %}>100 per page</option>
            </select>"""
content = content.replace(old_select, new_select)

# Add Select2 JS
js_addition = """
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
<script>
    $(document).ready(function() {
        $('.select2').select2({
            width: '100%'
        });
    });
</script>
"""
if "select2.min.js" not in content:
    content = content.replace("{% endblock %}", js_addition + "\n{% endblock %}")

with open(file_path, 'w') as f:
    f.write(content)
