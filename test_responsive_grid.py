"""
Test responsive grid rules and HTML structure for ATC page layout
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vmmc_erp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_grid():
    admin_user = User.objects.filter(is_superuser=True).first()
    client = Client()
    client.force_login(admin_user)

    res = client.get('/lab/auto-trigger/atc/')
    assert res.status_code == 200
    html = res.content.decode('utf-8')

    # 1. Verify atc-grid-4 class and definition
    assert '.atc-grid-4 {' in html
    assert 'grid-template-columns: repeat(4, minmax(0, 1fr));' in html
    assert '@media (max-width: 1024px)' in html
    assert 'repeat(2, minmax(0, 1fr))' in html
    assert '@media (max-width: 640px)' in html

    # 2. Verify Row 1 has 4 columns
    assert 'Department</label>' in html
    assert 'Source Data Period</label>' in html
    assert 'OP Registration Date</label>' in html
    assert 'Automation Signal</label>' in html

    # 3. Verify Row 2 has 4 columns
    assert 'Male Patients' in html
    assert 'Female Patients' in html
    assert 'Child Patients' in html
    assert 'Total Patients' in html

    # 4. Verify Row 3 has 4 columns
    assert 'OP Daily %' in html
    assert 'Review %' in html
    assert 'OP Target' in html
    assert 'Review Target' in html

    # 5. Verify no full-width col-md-3 bootstrap classes without row
    assert 'col-md-3' not in html

    # 6. Verify table scroll and sticky columns
    assert 'table-scroll' in html
    assert 'table-container' in html
    assert 'sticky-col sticky-date-th' in html
    assert 'sticky-col sticky-day-th' in html

    # 7. Verify bottom action bar position
    table_pos = html.find('id="dailyTargetsTable"')
    bottom_bar_pos = html.find('class="bottom-action-bar"')
    assert table_pos > 0 and bottom_bar_pos > 0
    assert bottom_bar_pos > table_pos, "Bottom action bar must appear AFTER the daily target table"

    print("ALL RESPONSIVE GRID CHECKS PASSED!")

if __name__ == '__main__':
    test_grid()
