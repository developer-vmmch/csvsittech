"""
VMMC ERP Department Configurations and Access Control Utilities.
Defines the 16 core ERP Login Departments matching the hospital ERP workflow.
"""

ERP_LOGIN_DEPARTMENTS = [
    {
        'id': 1,
        'code': 'front_desk',
        'slug': 'front-desk',
        'name': 'Front Desk',
        'icon': 'bi-person-workspace',
        'color_bg': '#e0f2fe',
        'color_icon': '#0284c7',
        'badge': 'OPD / Registration',
        'dashboard_url': '/patients/add/',
        'landing_module': 'patients',
        'allowed_prefixes': ['/patients/add/', '/patients/search/', '/patients/', '/dashboard/'],
        'aliases': ['front desk', 'front_desk', 'front-desk', 'front office', 'front_office', 'front-office', 'opd', 'reception', 'registration'],
        'description': 'Patient registration, UHID creation, OPD search & appointments',
    },
    {
        'id': 2,
        'code': 'consultant',
        'slug': 'consultant',
        'name': 'Consultant',
        'icon': 'bi-person-badge',
        'color_bg': '#dcfce7',
        'color_icon': '#16a34a',
        'badge': 'Doctor Window',
        'dashboard_url': '/lab/doctor-window/',
        'landing_module': 'consultant',
        'allowed_prefixes': ['/lab/doctor-window/', '/patients/', '/dashboard/'],
        'aliases': ['consultant', 'doctor', 'physician', 'medical officer', 'specialist'],
        'description': 'Doctor window, consultation review, diagnostic orders & clinical records',
    },
    {
        'id': 3,
        'code': 'billing',
        'slug': 'billing',
        'name': 'Billing',
        'icon': 'bi-currency-rupee',
        'color_bg': '#fef3c7',
        'color_icon': '#d97706',
        'badge': 'Cashier / Billing',
        'dashboard_url': '/patients/',
        'landing_module': 'billing',
        'allowed_prefixes': ['/patients/', '/dashboard/'],
        'aliases': ['billing', 'cashier', 'accounts billing', 'finance'],
        'description': 'OPD / IPD billing, cash counter, insurance claims & payments',
    },
    {
        'id': 4,
        'code': 'lab',
        'slug': 'lab',
        'name': 'Lab',
        'icon': 'bi-funnel-fill',
        'color_bg': '#ffe4e6',
        'color_icon': '#e11d48',
        'badge': 'Diagnostics / Lab',
        'dashboard_url': '/lab/work-orders/',
        'landing_module': 'lab_orders',
        'allowed_prefixes': ['/lab/', '/dashboard/'],
        'aliases': ['lab', 'laboratory', 'pathology', 'biochemistry', 'microbiology', 'hematology', 'lab_tech'],
        'description': 'Laboratory investigations, sample collection, test results & verification',
    },
    {
        'id': 5,
        'code': 'ward',
        'slug': 'ward',
        'name': 'Ward',
        'icon': 'bi-hospital',
        'color_bg': '#f3e8ff',
        'color_icon': '#9333ea',
        'badge': 'IPD / Wards',
        'dashboard_url': '/patients/ward/allocation/',
        'landing_module': 'ward',
        'allowed_prefixes': ['/patients/ward/', '/patients/branch-transfer/', '/patients/wards/', '/dashboard/'],
        'aliases': ['ward', 'ipd', 'nursing', 'ward staff', 'inpatient'],
        'description': 'Inpatient bed matrix allocation, ward management & nurse station',
    },
    {
        'id': 6,
        'code': 'mrd',
        'slug': 'mrd',
        'name': 'MRD',
        'icon': 'bi-file-earmark-medical-fill',
        'color_bg': '#ccfbf1',
        'color_icon': '#0d9488',
        'badge': 'Medical Records',
        'dashboard_url': '/patients/review/',
        'landing_module': 'review',
        'allowed_prefixes': ['/patients/review/', '/patients/', '/dashboard/'],
        'aliases': ['mrd', 'medical records', 'records', 'medical records department'],
        'description': 'Medical Records Department, discharge summaries & archive tracking',
    },
    {
        'id': 7,
        'code': 'pharmacy',
        'slug': 'pharmacy',
        'name': 'Pharmacy',
        'icon': 'bi-capsule',
        'color_bg': '#dbeafe',
        'color_icon': '#2563eb',
        'badge': 'Drugs / Dispensary',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'allowed_prefixes': ['/dashboard/', '/patients/'],
        'aliases': ['pharmacy', 'pharmacist', 'dispensary', 'drugs'],
        'description': 'Prescription dispensing, drug inventory & pharmacy stock',
    },
    {
        'id': 8,
        'code': 'inventory',
        'slug': 'inventory',
        'name': 'Inventory',
        'icon': 'bi-box-seam-fill',
        'color_bg': '#ffedd5',
        'color_icon': '#ea580c',
        'badge': 'Stores / Stock',
        'dashboard_url': '/dashboard/',
        'landing_module': 'inventory',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['inventory', 'stores', 'central stores', 'purchase', 'warehouse'],
        'description': 'Central stores, purchase indents, stock ledger & supplies',
    },
    {
        'id': 9,
        'code': 'blood_bank',
        'slug': 'blood-bank',
        'name': 'Blood Bank',
        'icon': 'bi-droplet-fill',
        'color_bg': '#fee2e2',
        'color_icon': '#dc2626',
        'badge': 'Transfusion / Bank',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'allowed_prefixes': ['/dashboard/', '/lab/'],
        'aliases': ['blood bank', 'blood_bank', 'blood-bank', 'transfusion'],
        'description': 'Blood donor management, screening, component cross-matching & reserves',
    },
    {
        'id': 10,
        'code': 'radiology',
        'slug': 'radiology',
        'name': 'Radiology',
        'icon': 'bi-lungs-fill',
        'color_bg': '#ede9fe',
        'color_icon': '#7c3aed',
        'badge': 'Imaging / X-Ray',
        'dashboard_url': '/lab/work-orders/',
        'landing_module': 'lab_orders',
        'allowed_prefixes': ['/lab/', '/dashboard/'],
        'aliases': ['radiology', 'xray', 'x-ray', 'imaging', 'scan', 'ct scan', 'mri', 'ultrasound'],
        'description': 'X-Ray, CT Scan, MRI, Ultrasound imaging & radiology reporting',
    },
    {
        'id': 11,
        'code': 'ot',
        'slug': 'ot',
        'name': 'OT',
        'icon': 'bi-activity',
        'color_bg': '#d1fae5',
        'color_icon': '#059669',
        'badge': 'Operation Theater',
        'dashboard_url': '/ot/',
        'landing_module': 'ot',
        'allowed_prefixes': ['/ot/', '/dashboard/'],
        'aliases': ['ot', 'operation theater', 'surgery', 'surgical', 'operation theatre'],
        'description': 'Operation Theater booking, scheduling, surgeon notes & PAC',
    },
    {
        'id': 12,
        'code': 'summary',
        'slug': 'summary',
        'name': 'Summary',
        'icon': 'bi-card-checklist',
        'color_bg': '#e0e7ff',
        'color_icon': '#4f46e5',
        'badge': 'Clinical Summary',
        'dashboard_url': '/patients/discharge/',
        'landing_module': 'discharge',
        'allowed_prefixes': ['/patients/discharge/', '/dashboard/'],
        'aliases': ['summary', 'clinical summary', 'discharge summary', 'audit'],
        'description': 'Patient discharge summary, case sheet summaries & audits',
    },
    {
        'id': 13,
        'code': 'accounts',
        'slug': 'accounts',
        'name': 'Accounts',
        'icon': 'bi-calculator-fill',
        'color_bg': '#e0f2fe',
        'color_icon': '#0284c7',
        'badge': 'Finance / Audit',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['accounts', 'finance', 'accounting', 'auditor'],
        'description': 'Financial ledgers, receipts, payment vouchers & reconciliation',
    },
    {
        'id': 14,
        'code': 'report',
        'slug': 'report',
        'name': 'Report',
        'icon': 'bi-bar-chart-fill',
        'color_bg': '#dcfce7',
        'color_icon': '#16a34a',
        'badge': 'Analytics / Reports',
        'dashboard_url': '/lab/reports/dashboard/',
        'landing_module': 'lab_reports',
        'allowed_prefixes': ['/lab/reports/', '/dashboard/'],
        'aliases': ['report', 'reports', 'analytics', 'statistics', 'census'],
        'description': 'Hospital analytics, OPD/IPD statistics, workload & audit reports',
    },
    {
        'id': 15,
        'code': 'mis',
        'slug': 'mis',
        'name': 'MIS',
        'icon': 'bi-pie-chart-fill',
        'color_bg': '#fee2e2',
        'color_icon': '#ea580c',
        'badge': 'Executive / MIS',
        'dashboard_url': '/dashboard/',
        'landing_module': 'dashboard',
        'allowed_prefixes': ['/dashboard/'],
        'aliases': ['mis', 'management', 'executive', 'kpi', 'admin'],
        'description': 'Management Information System, key executive metrics & KPIs',
    },
    {
        'id': 16,
        'code': 'clinical_department',
        'slug': 'clinical-department',
        'name': 'Clinical Department',
        'icon': 'bi-building-fill',
        'color_bg': '#cffafe',
        'color_icon': '#0891b2',
        'badge': 'Specialties & Units',
        'dashboard_url': '/patients/departments/',
        'landing_module': 'department_list',
        'allowed_prefixes': ['/patients/departments/', '/patients/wards/', '/dashboard/'],
        'aliases': ['clinical department', 'clinical_department', 'clinical-department', 'department', 'departments', 'hospital departments', 'clinical departments'],
        'description': 'Clinical medical departments, specialty units & doctor assignments',
    },
]


def seed_default_landing_departments_if_needed():
    """Seed the 16 core ERP departments into the database if the table is empty."""
    try:
        from apps.users.models import LandingDepartment
        if not LandingDepartment.objects.exists():
            for dept in ERP_LOGIN_DEPARTMENTS:
                LandingDepartment.objects.create(
                    code=dept['code'],
                    slug=dept['slug'],
                    name=dept['name'],
                    icon=dept['icon'],
                    color_bg=dept['color_bg'],
                    color_icon=dept['color_icon'],
                    badge=dept['badge'],
                    dashboard_url=dept['dashboard_url'],
                    landing_module=dept.get('landing_module', ''),
                    allowed_prefixes=dept.get('allowed_prefixes', []),
                    aliases=dept.get('aliases', []),
                    description=dept.get('description', ''),
                    order=dept.get('id', 1) * 10,
                    is_active=True,
                    is_system=True,
                )
    except Exception:
        pass


def get_all_departments(active_only=True):
    """Returns the list of ERP login departments from the database or static config."""
    try:
        from apps.users.models import LandingDepartment
        seed_default_landing_departments_if_needed()
        qs = LandingDepartment.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        if qs.exists():
            return [d.to_dict() for d in qs.order_by('order', 'id')]
    except Exception:
        pass
    return ERP_LOGIN_DEPARTMENTS


def get_department_by_slug(slug):
    """Fetch a department dictionary by slug, code, or alias."""
    if not slug:
        return None
    slug_norm = str(slug).strip().lower().replace('_', '-')
    try:
        from apps.users.models import LandingDepartment
        seed_default_landing_departments_if_needed()
        dept_obj = LandingDepartment.objects.filter(slug__iexact=slug_norm).first()
        if not dept_obj:
            dept_obj = LandingDepartment.objects.filter(code__iexact=slug_norm.replace('-', '_')).first()
        if dept_obj:
            return dept_obj.to_dict()

        for d in LandingDepartment.objects.all():
            aliases = d.aliases if isinstance(d.aliases, list) else []
            for alias in aliases:
                if str(alias).lower().replace(' ', '-').replace('_', '-') == slug_norm:
                    return d.to_dict()
    except Exception:
        pass

    for dept in ERP_LOGIN_DEPARTMENTS:
        if dept['slug'] == slug_norm or dept['code'] == slug_norm.replace('-', '_'):
            return dept
        for alias in dept.get('aliases', []):
            if alias.lower().replace(' ', '-').replace('_', '-') == slug_norm:
                return dept
    return None


def get_department_by_code(code):
    """Fetch a department dictionary by code, slug, or alias."""
    if not code:
        return None
    code_norm = str(code).strip().lower().replace('-', '_')
    try:
        from apps.users.models import LandingDepartment
        seed_default_landing_departments_if_needed()
        dept_obj = LandingDepartment.objects.filter(code__iexact=code_norm).first()
        if not dept_obj:
            dept_obj = LandingDepartment.objects.filter(slug__iexact=code_norm.replace('_', '-')).first()
        if dept_obj:
            return dept_obj.to_dict()

        for d in LandingDepartment.objects.all():
            aliases = d.aliases if isinstance(d.aliases, list) else []
            for alias in aliases:
                if str(alias).lower().replace(' ', '_').replace('-', '_') == code_norm:
                    return d.to_dict()
    except Exception:
        pass

    for dept in ERP_LOGIN_DEPARTMENTS:
        if dept['code'] == code_norm or dept['slug'] == code_norm.replace('_', '-'):
            return dept
        for alias in dept.get('aliases', []):
            if alias.lower().replace(' ', '_').replace('-', '_') == code_norm:
                return dept
    return None



def user_can_access_department(user, dept_dict_or_slug):
    """
    Check if the user is authorized to login or access a specific department.
    - Superusers and Administrators (role == 'ADMIN') have universal access.
    - Regular users must be assigned to this department or an equivalent alias/clinical department.
    """
    if not user or not user.is_authenticated:
        return False

    # Superuser or Admin role has universal master access
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

    # Universal access keywords
    if user_dept in ['all', 'all departments', 'administrator', 'admin', 'superadmin', 'management']:
        return True

    # Exact code or slug match
    if user_dept in [dept['code'].lower(), dept['slug'].lower(), dept['name'].lower()]:
        return True

    # Check aliases
    for alias in dept.get('aliases', []):
        if alias.lower() == user_dept:
            return True

    # Check role-based mappings
    role_to_dept = {
        'manager': ['clinical_department', 'department', 'front_office', 'consultant', 'ward', 'mrd', 'report', 'mis'],
        'doctor': ['consultant', 'ward', 'ot', 'summary', 'clinical_department'],
        'consultant': ['consultant', 'ward', 'ot', 'summary', 'clinical_department'],
        'lab_tech': ['lab', 'blood_bank', 'report'],
        'radiologist': ['radiology', 'lab', 'report'],
        'pharmacist': ['pharmacy', 'inventory'],
        'accountant': ['accounts', 'billing'],
        'cashier': ['billing', 'accounts'],
        'nurse': ['ward', 'ot', 'front_office'],
        'staff': ['front_office', 'ward', 'billing', 'mrd', 'summary'],
    }

    allowed_depts_for_role = role_to_dept.get(user_role, [])
    if dept['code'] in allowed_depts_for_role or dept['slug'] in allowed_depts_for_role:
        return True

    # If user belongs to a clinical department (e.g. "GENERAL MEDICINE", "CARDIOLOGY"),
    # they are allowed into Consultant, Ward, Clinical Department, and Summary
    clinical_allowed = ['clinical_department', 'consultant', 'ward', 'department', 'summary', 'front_office']
    if user_dept and dept['code'] in clinical_allowed:
        # Check if department matches any clinical department name in DB
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

    # Superuser has master access to all roles
    if user.is_superuser:
        return True

    user_role = (getattr(user, 'role', '') or '').strip().upper()
    target_role = (role_dict.get('code', '') or '').strip().upper()

    if user_role == target_role:
        return True

    # Admin role can access other roles for management
    if user_role == 'ADMIN':
        return True

    return False

