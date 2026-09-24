"""
VMMC ERP Department Configurations and Access Control Utilities.
Defines the 16 core ERP Login Departments matching the hospital ERP workflow.
VINAYAKA MISSIONS MEDICAL COLLEGE AND HOSPITAL - KARAIKAL
Powered by CSVS IT Tech
"""

ERP_LOGIN_DEPARTMENTS = [
    {
        'id': 1,
        'code': 'front_office',
        'slug': 'front-office',
        'name': 'Front Office',
        'login_title': 'Front Office Login',
        'icon': 'bi-person-workspace',
        'color_bg': '#e0f2fe',
        'color_icon': '#0284c7',
        'badge': 'Patient Registration & Enquiry',
        'full_scope': 'Patient Registration | Enquiry | OP Services',
        'dashboard_url': '/patients/add/',
        'landing_module': 'patients',
        'bg_image': 'images/departments/front_office.jpg',
        'allowed_prefixes': ['/patients/add/', '/patients/search/', '/patients/', '/dashboard/'],
        'aliases': ['front office', 'front_office', 'front-office', 'front desk', 'front_desk', 'front-desk', 'opd', 'reception', 'registration', 'enquiry'],
        'description': 'Enter your credentials to access the Front Office module',
    },
    {
        'id': 2,
        'code': 'consultant',
        'slug': 'consultant',
        'name': 'Consultant',
        'login_title': 'Consultant Login',
        'icon': 'bi-person-badge',
        'color_bg': '#ccfbf1',
        'color_icon': '#0d9488',
        'badge': 'Doctor Window & Clinical Care',
        'full_scope': 'Doctor Consultation | Diagnosis | Treatment',
        'dashboard_url': '/lab/doctor-window/',
        'landing_module': 'consultant',
        'bg_image': 'images/departments/consultant.jpg',
        'allowed_prefixes': ['/lab/doctor-window/', '/patients/', '/dashboard/'],
        'aliases': ['consultant', 'doctor', 'physician', 'medical officer', 'specialist', 'clinician'],
        'description': 'Enter your credentials to access the Consultant module',
    },
    {
        'id': 3,
        'code': 'billing',
        'slug': 'billing',
        'name': 'Billing',
        'login_title': 'Billing Login',
        'icon': 'bi-currency-rupee',
        'color_bg': '#ffedd5',
        'color_icon': '#ea580c',
        'badge': 'OP & IP Billing Counters',
        'full_scope': 'OP Billing | IP Billing | Insurance | Payments',
        'dashboard_url': '/patients/',
        'landing_module': 'billing',
        'bg_image': 'images/departments/billing.jpg',
        'allowed_prefixes': ['/patients/', '/dashboard/'],
        'aliases': ['billing', 'cashier', 'accounts billing', 'finance cashier', 'op billing', 'ip billing'],
        'description': 'Enter your credentials to access the Billing module',
    },
    {
        'id': 4,
        'code': 'lab',
        'slug': 'lab',
        'name': 'Lab',
        'login_title': 'Laboratory Login',
        'icon': 'bi-funnel-fill',
        'color_bg': '#ede9fe',
        'color_icon': '#7c3aed',
        'badge': 'Diagnostics & Sample Analysis',
        'full_scope': 'Sample Processing | Analysis | Results',
        'dashboard_url': '/lab/work-orders/',
        'landing_module': 'lab_orders',
        'bg_image': 'images/departments/lab.jpg',
        'allowed_prefixes': ['/lab/', '/dashboard/'],
        'aliases': ['lab', 'laboratory', 'pathology', 'biochemistry', 'microbiology', 'hematology', 'lab_tech'],
        'description': 'Enter your credentials to access the Laboratory module',
    },
    {
        'id': 5,
        'code': 'ward',
        'slug': 'ward',
        'name': 'Ward',
        'login_title': 'Ward Login',
        'icon': 'bi-hospital',
        'color_bg': '#dcfce7',
        'color_icon': '#16a34a',
        'badge': 'Inpatient Care & Bed Matrix',
        'full_scope': 'Inpatient Care | Nursing | Bed Management',
        'dashboard_url': '/patients/ward/allocation/',
        'landing_module': 'ward',
        'bg_image': 'images/departments/ward.jpg',
        'allowed_prefixes': ['/patients/ward/', '/patients/branch-transfer/', '/patients/wards/', '/dashboard/'],
        'aliases': ['ward', 'ipd', 'nursing', 'ward staff', 'inpatient', 'nurse'],
        'description': 'Enter your credentials to access the Ward module',
    },
    {
        'id': 6,
        'code': 'mrd',
        'slug': 'mrd',
        'name': 'MRD',
        'login_title': 'MRD Login',
        'icon': 'bi-file-earmark-medical-fill',
        'color_bg': '#cffafe',
        'color_icon': '#0891b2',
        'badge': 'Medical Records & Archiving',
        'full_scope': 'Medical Records | Patient Files | Documentation',
        'dashboard_url': '/patients/review/',
        'landing_module': 'review',
        'bg_image': 'images/departments/mrd.jpg',
        'allowed_prefixes': ['/patients/review/', '/patients/', '/dashboard/'],
        'aliases': ['mrd', 'medical records', 'records', 'medical records department', 'archive'],
        'description': 'Enter your credentials to access the MRD module',
    },
    {
        'id': 7,
        'code': 'pharmacy',
        'slug': 'pharmacy',
        'name': 'Pharmacy',
        'login_title': 'Pharmacy Login',
        'icon': 'bi-capsule',
        'color_bg': '#dbeafe',
        'color_icon': '#2563eb',
        'badge': 'Prescriptions & Dispensary',
        'full_scope': 'Prescriptions | Dispensing | Pharmacy Management',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'bg_image': 'images/departments/pharmacy.jpg',
        'allowed_prefixes': ['/dashboard/', '/patients/'],
        'aliases': ['pharmacy', 'pharmacist', 'dispensary', 'drugs', 'chemist'],
        'description': 'Enter your credentials to access the Pharmacy module',
    },
    {
        'id': 8,
        'code': 'inventory',
        'slug': 'inventory',
        'name': 'Inventory',
        'login_title': 'Inventory Login',
        'icon': 'bi-box-seam-fill',
        'color_bg': '#fef3c7',
        'color_icon': '#d97706',
        'badge': 'Central Stores & Supplies',
        'full_scope': 'Stock | Supplies | Purchase | Inventory Control',
        'dashboard_url': '/dashboard/',
        'landing_module': 'inventory',
        'bg_image': 'images/departments/inventory.jpg',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['inventory', 'stores', 'central stores', 'purchase', 'warehouse', 'stock'],
        'description': 'Enter your credentials to access the Inventory module',
    },
    {
        'id': 9,
        'code': 'blood_bank',
        'slug': 'blood-bank',
        'name': 'Blood Bank',
        'login_title': 'Blood Bank Login',
        'icon': 'bi-droplet-fill',
        'color_bg': '#fee2e2',
        'color_icon': '#dc2626',
        'badge': 'Blood Storage & Transfusion',
        'full_scope': 'Blood Storage | Donor Services | Blood Management',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'bg_image': 'images/departments/blood_bank.jpg',
        'allowed_prefixes': ['/dashboard/', '/lab/'],
        'aliases': ['blood bank', 'blood_bank', 'blood-bank', 'transfusion', 'blood donor'],
        'description': 'Enter your credentials to access the Blood Bank module',
    },
    {
        'id': 10,
        'code': 'radiology',
        'slug': 'radiology',
        'name': 'Radiology',
        'login_title': 'Radiology Login',
        'icon': 'bi-lungs-fill',
        'color_bg': '#f3e8ff',
        'color_icon': '#9333ea',
        'badge': 'X-Ray, CT, MRI & Imaging',
        'full_scope': 'X-Ray | CT | MRI | Diagnostic Imaging',
        'dashboard_url': '/lab/work-orders/',
        'landing_module': 'lab_orders',
        'bg_image': 'images/departments/radiology.jpg',
        'allowed_prefixes': ['/lab/', '/dashboard/'],
        'aliases': ['radiology', 'xray', 'x-ray', 'imaging', 'scan', 'ct scan', 'mri', 'ultrasound', 'radiologist'],
        'description': 'Enter your credentials to access the Radiology module',
    },
    {
        'id': 11,
        'code': 'ot',
        'slug': 'ot',
        'name': 'OT',
        'login_title': 'OT Login',
        'icon': 'bi-activity',
        'color_bg': '#d1fae5',
        'color_icon': '#059669',
        'badge': 'Operation Theatre & Surgery',
        'full_scope': 'Operation Theatre | Surgical Workflow | OT Management',
        'dashboard_url': '/ot/',
        'landing_module': 'ot',
        'bg_image': 'images/departments/ot.jpg',
        'allowed_prefixes': ['/ot/', '/dashboard/'],
        'aliases': ['ot', 'operation theater', 'surgery', 'surgical', 'operation theatre', 'surgeon'],
        'description': 'Enter your credentials to access the OT module',
    },
    {
        'id': 12,
        'code': 'summary',
        'slug': 'summary',
        'name': 'Summary',
        'login_title': 'Summary Login',
        'icon': 'bi-card-checklist',
        'color_bg': '#e0e7ff',
        'color_icon': '#4f46e5',
        'badge': 'Discharge & Overview',
        'full_scope': 'Hospital Overview | Operations | Key Information',
        'dashboard_url': '/patients/discharge/',
        'landing_module': 'discharge',
        'bg_image': 'images/departments/summary.jpg',
        'allowed_prefixes': ['/patients/discharge/', '/dashboard/'],
        'aliases': ['summary', 'clinical summary', 'discharge summary', 'audit summary', 'overview'],
        'description': 'Enter your credentials to access the Summary module',
    },
    {
        'id': 13,
        'code': 'accounts',
        'slug': 'accounts',
        'name': 'Accounts',
        'login_title': 'Accounts Login',
        'icon': 'bi-calculator-fill',
        'color_bg': '#e0f2fe',
        'color_icon': '#0369a1',
        'badge': 'Finance & Audit Management',
        'full_scope': 'Finance | Accounts | Payments | Financial Management',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'bg_image': 'images/departments/accounts.svg',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['accounts', 'finance', 'accounting', 'auditor', 'internal audit', 'financial'],
        'description': 'Enter your credentials to access the Accounts module',
    },
    {
        'id': 14,
        'code': 'report',
        'slug': 'report',
        'name': 'Report',
        'login_title': 'Report Login',
        'icon': 'bi-bar-chart-fill',
        'color_bg': '#dcfce7',
        'color_icon': '#15803d',
        'badge': 'Analytics & Workload Reports',
        'full_scope': 'Reports | Analytics | Operational Information',
        'dashboard_url': '/lab/reports/dashboard/',
        'landing_module': 'lab_reports',
        'bg_image': 'images/departments/report.svg',
        'allowed_prefixes': ['/lab/reports/', '/dashboard/'],
        'aliases': ['report', 'reports', 'analytics', 'statistics', 'census', 'reporting'],
        'description': 'Enter your credentials to access the Report module',
    },
    {
        'id': 15,
        'code': 'mis',
        'slug': 'mis',
        'name': 'MIS',
        'login_title': 'MIS Login',
        'icon': 'bi-pie-chart-fill',
        'color_bg': '#ffedd5',
        'color_icon': '#ea580c',
        'badge': 'Executive KPIs & Intelligence',
        'full_scope': 'Management Information | KPIs | Hospital Intelligence',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'bg_image': 'images/departments/mis.svg',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['mis', 'management', 'executive', 'kpi', 'admin', 'intelligence', 'command center'],
        'description': 'Enter your credentials to access the MIS module',
    },
    {
        'id': 16,
        'code': 'department',
        'slug': 'department',
        'name': 'Department',
        'login_title': 'Department Login',
        'icon': 'bi-building-fill',
        'color_bg': '#cffafe',
        'color_icon': '#0891b2',
        'badge': 'Specialties & Administration',
        'full_scope': 'Department Management | Configuration | Administration',
        'dashboard_url': '/patients/departments/',
        'landing_module': 'department_list',
        'bg_image': 'images/departments/department.svg',
        'allowed_prefixes': ['/patients/departments/', '/patients/wards/', '/dashboard/'],
        'aliases': ['department', 'departments', 'clinical department', 'clinical_department', 'clinical-department', 'hospital departments', 'clinical departments', 'admin office'],
        'description': 'Enter your credentials to access the Department module',
    },
]


def sync_and_seed_landing_departments():
    """Seed or update the 16 core ERP departments in the database."""
    try:
        from apps.users.models import LandingDepartment
        for dept in ERP_LOGIN_DEPARTMENTS:
            obj, created = LandingDepartment.objects.get_or_create(
                slug=dept['slug'],
                defaults={
                    'code': dept['code'],
                    'name': dept['name'],
                    'icon': dept['icon'],
                    'color_bg': dept['color_bg'],
                    'color_icon': dept['color_icon'],
                    'badge': dept['badge'],
                    'dashboard_url': dept['dashboard_url'],
                    'landing_module': dept.get('landing_module', ''),
                    'allowed_prefixes': dept.get('allowed_prefixes', []),
                    'aliases': dept.get('aliases', []),
                    'description': dept.get('description', ''),
                    'order': dept.get('id', 1) * 10,
                    'is_active': True,
                    'is_system': True,
                }
            )
            if not created:
                obj.code = dept['code']
                obj.name = dept['name']
                obj.icon = dept['icon']
                obj.color_bg = dept['color_bg']
                obj.color_icon = dept['color_icon']
                obj.badge = dept['badge']
                obj.dashboard_url = dept['dashboard_url']
                obj.landing_module = dept.get('landing_module', '')
                obj.allowed_prefixes = dept.get('allowed_prefixes', [])
                obj.aliases = dept.get('aliases', [])
                obj.description = dept.get('description', '')
                obj.order = dept.get('id', 1) * 10
                obj.is_active = True
                obj.is_system = True
                obj.save()

        # Delete legacy obsolete slugs if any
        LandingDepartment.objects.filter(slug__in=['front-desk', 'clinical-department']).delete()
    except Exception as e:
        print(f"Error seeding departments: {e}")


def seed_default_landing_departments_if_needed():
    sync_and_seed_landing_departments()


def get_all_departments(active_only=True):
    """Returns the list of ERP login departments from the static config enhanced with DB state."""
    dept_map = {d['slug']: d for d in ERP_LOGIN_DEPARTMENTS}
    try:
        from apps.users.models import LandingDepartment
        seed_default_landing_departments_if_needed()
        qs = LandingDepartment.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        if qs.exists():
            res = []
            for d in qs.order_by('order', 'id'):
                dict_repr = d.to_dict()
                matched_static = dept_map.get(dict_repr['slug']) or next((x for x in ERP_LOGIN_DEPARTMENTS if x['code'] == dict_repr['code']), None)
                if matched_static:
                    dict_repr['badge'] = matched_static.get('badge', dict_repr.get('badge', ''))
                    dict_repr['full_scope'] = matched_static.get('full_scope', dict_repr.get('badge', ''))
                    dict_repr['bg_image'] = matched_static.get('bg_image', '')
                    dict_repr['login_title'] = matched_static.get('login_title', f"{dict_repr['name']} Login")
                else:
                    dict_repr['bg_image'] = 'images/departments/front_office.jpg'
                    dict_repr['login_title'] = f"{dict_repr['name']} Login"
                    dict_repr['full_scope'] = dict_repr.get('badge', '')
                res.append(dict_repr)
            return res
    except Exception:
        pass
    return ERP_LOGIN_DEPARTMENTS


def get_department_by_slug(slug):
    """Fetch a department dictionary by slug, code, or alias."""
    if not slug:
        return None
    slug_norm = str(slug).strip().lower().replace('_', '-')
    
    for dept in ERP_LOGIN_DEPARTMENTS:
        if dept['slug'] == slug_norm or dept['code'] == slug_norm.replace('-', '_'):
            return dept
        for alias in dept.get('aliases', []):
            if alias.lower().replace(' ', '-').replace('_', '-') == slug_norm:
                return dept

    try:
        from apps.users.models import LandingDepartment
        dept_obj = LandingDepartment.objects.filter(slug__iexact=slug_norm).first()
        if not dept_obj:
            dept_obj = LandingDepartment.objects.filter(code__iexact=slug_norm.replace('-', '_')).first()
        if dept_obj:
            d = dept_obj.to_dict()
            static_match = next((x for x in ERP_LOGIN_DEPARTMENTS if x['code'] == d['code'] or x['slug'] == d['slug']), None)
            if static_match:
                d['badge'] = static_match.get('badge', d.get('badge', ''))
                d['full_scope'] = static_match.get('full_scope', d.get('badge', ''))
                d['bg_image'] = static_match.get('bg_image', '')
                d['login_title'] = static_match.get('login_title', f"{d['name']} Login")
            return d
    except Exception:
        pass

    return None


def get_department_by_code(code):
    """Fetch a department dictionary by code, slug, or alias."""
    if not code:
        return None
    code_norm = str(code).strip().lower().replace('-', '_')
    for dept in ERP_LOGIN_DEPARTMENTS:
        if dept['code'] == code_norm or dept['slug'] == code_norm.replace('_', '-'):
            return dept
        for alias in dept.get('aliases', []):
            if alias.lower().replace(' ', '_').replace('-', '_') == code_norm:
                return dept
    return get_department_by_slug(code)


def user_can_access_department(user, dept_dict_or_slug):
    """
    Check if the user is authorized to login or access a specific department.
    - Superusers and Administrators (role == 'ADMIN') have universal access.
    - Regular users must be assigned to this department or an equivalent alias/clinical department.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or getattr(user, 'role', '') == 'ADMIN':
        return True

    if isinstance(dept_dict_or_slug, dict):
        dept = dept_dict_or_slug
    else:
        dept = get_department_by_slug(dept_dict_or_slug)

    if not dept:
        return False

    user_dept = (getattr(user, 'department', '') or '').strip().lower()
    user_role = (getattr(user, 'role', '') or '').strip().lower()

    if user_dept in ['all', 'all departments', 'administrator', 'admin', 'superadmin', 'management']:
        return True

    if user_dept in [dept['code'].lower(), dept['slug'].lower(), dept['name'].lower()]:
        return True

    for alias in dept.get('aliases', []):
        if alias.lower() == user_dept:
            return True

    role_to_dept = {
        'manager': ['clinical_department', 'department', 'front_office', 'consultant', 'ward', 'mrd', 'report', 'mis', 'accounts', 'billing', 'inventory'],
        'doctor': ['consultant', 'ward', 'ot', 'summary', 'clinical_department', 'department'],
        'consultant': ['consultant', 'ward', 'ot', 'summary', 'clinical_department', 'department'],
        'lab_tech': ['lab', 'blood_bank', 'report'],
        'radiologist': ['radiology', 'lab', 'report'],
        'pharmacist': ['pharmacy', 'inventory'],
        'accountant': ['accounts', 'billing'],
        'cashier': ['billing', 'accounts'],
        'nurse': ['ward', 'ot', 'front_office'],
        'staff': ['front_office', 'ward', 'billing', 'mrd', 'summary', 'pharmacy', 'inventory', 'blood_bank', 'radiology', 'ot', 'accounts', 'report', 'mis', 'department'],
    }

    allowed_depts_for_role = role_to_dept.get(user_role, [])
    if dept['code'] in allowed_depts_for_role or dept['slug'] in allowed_depts_for_role:
        return True

    clinical_allowed = ['clinical_department', 'department', 'consultant', 'ward', 'summary', 'front_office']
    if user_dept and dept['code'] in clinical_allowed:
        try:
            from apps.patients.models import Department
            if Department.objects.filter(name__iexact=user.department).exists():
                return True
        except Exception:
            pass

    return False


def get_all_system_roles():
    """
    Returns the dynamic list of all user system roles (built-in + custom roles)
    with their user counts, permissions summary, colors, and icons.
    """
    from apps.users.models import User, CustomRole
    from django.db.models import Q

    roles = [
        {
            'code': 'ADMIN',
            'slug': 'administrator',
            'name': 'Administrator',
            'badge': 'Full Control',
            'badge_class': 'badge-purple',
            'icon': 'bi-shield-lock-fill',
            'color_bg': '#f3e8ff',
            'color_icon': '#7c3aed',
            'description': 'Full system control, user account creation, role matrix configuration, and system parameters.',
            'user_count': User.objects.filter(Q(role=User.Roles.ADMIN) | Q(is_superuser=True)).distinct().count(),
            'features': ['All ERP Modules', 'User Directory', 'Role Access Matrix', 'System Settings'],
            'dashboard_url': '/dashboard/',
        },
        {
            'code': 'MANAGER',
            'slug': 'department-manager',
            'name': 'Department Manager',
            'badge': 'Management',
            'badge_class': 'badge-blue',
            'icon': 'bi-diagram-3-fill',
            'color_bg': '#e0f2fe',
            'color_icon': '#0284c7',
            'description': 'Department oversight, patient registration, setup of departments, units, companies, and inventory.',
            'user_count': User.objects.filter(role=User.Roles.MANAGER).count(),
            'features': ['Patients Management', 'Departments & Units', 'Companies Setup', 'Inventory'],
            'dashboard_url': '/patients/',
        },
        {
            'code': 'STAFF',
            'slug': 'staff-member',
            'name': 'Staff Member',
            'badge': 'Front Desk / Ops',
            'badge_class': 'badge-green',
            'icon': 'bi-people-fill',
            'color_bg': '#dcfce7',
            'color_icon': '#16a34a',
            'description': 'Front-desk operations, patient registration, search, and OP slip printing.',
            'user_count': User.objects.filter(role=User.Roles.STAFF).count(),
            'features': ['Add Patient', 'Search Patient', 'Patient Directory', 'Print OP Slips'],
            'dashboard_url': '/patients/add/',
        },
        {
            'code': 'AUDITOR',
            'slug': 'auditor',
            'name': 'Auditor',
            'badge': 'Read-Only Audit',
            'badge_class': 'badge-amber',
            'icon': 'bi-eye-fill',
            'color_bg': '#fef3c7',
            'color_icon': '#d97706',
            'description': 'Operational view-only access to patient records, companies, and department reports.',
            'user_count': User.objects.filter(role=User.Roles.AUDITOR).count(),
            'features': ['Search Patient (Read)', 'Patient Directory', 'Companies (Read)', 'Departments (Read)'],
            'dashboard_url': '/patients/',
        },
    ]

    try:
        for cr in CustomRole.objects.all():
            roles.append({
                'code': cr.code,
                'slug': cr.code.lower().replace('_', '-'),
                'name': cr.name,
                'badge': 'Custom Role',
                'badge_class': cr.badge_class or 'badge-blue',
                'icon': cr.icon or 'bi-person-badge-fill',
                'color_bg': '#f1f5f9',
                'color_icon': cr.color or '#0284c7',
                'description': cr.description or f"Custom configured role ({cr.code}).",
                'user_count': User.objects.filter(role=cr.code).count(),
                'features': ['Configured Access Mapping'],
                'dashboard_url': '/dashboard/',
            })
    except Exception:
        pass

    return roles


def get_role_by_slug(slug):
    """Fetch a role dictionary by slug or code."""
    if not slug:
        return None
    slug_norm = str(slug).strip().lower().replace('_', '-')
    all_roles = get_all_system_roles()
    for r in all_roles:
        if r['slug'] == slug_norm or r['code'].lower() == slug_norm.replace('-', '_'):
            return r
    return None


def user_can_access_role(user, role_dict_or_slug):
    """
    Validates if the user has the specified system role profile.
    """
    if not user or not user.is_authenticated:
        return False

    if isinstance(role_dict_or_slug, dict):
        role_dict = role_dict_or_slug
    else:
        role_dict = get_role_by_slug(role_dict_or_slug)

    if not role_dict:
        return False

    if user.is_superuser:
        return True

    user_role = (getattr(user, 'role', '') or '').strip().upper()
    target_role = (role_dict.get('code', '') or '').strip().upper()

    if user_role == target_role or user_role == 'ADMIN':
        return True

    return False
