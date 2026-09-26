from django.db import transaction

NAVBAR_MODULES_CONFIG = [
    {
        'id': 'front_office',
        'key': 'front_office',
        'name': 'Front Office',
        'icon': 'bi-building-fill-check',
        'color': '#0284c7',
        'badge': 'Hub',
        'description': 'Front office operations, CRM enquiries, admission requests, patient search, and logs',
        'submodules': [
            {
                'key': 'fo_crm',
                'name': 'CRM (Enquiries)',
                'icon': 'bi-telephone-inbound-fill',
                'url': '/front-office/crm/',
                'description': 'Caller enquiry intake, appointment queries, and follow-up management',
            },
            {
                'key': 'fo_admission_request',
                'name': 'Admission Request',
                'icon': 'bi-door-open-fill',
                'url': '/front-office/admission-request/',
                'description': 'Create and process inpatient ward admission requests',
            },
            {
                'key': 'fo_registration_search',
                'name': 'Registration Search',
                'icon': 'bi-search',
                'url': '/front-office/registration-search/',
                'description': 'Search master patient directory by OP/IP status, date, or demographics',
            },
            {
                'key': 'fo_patient_count',
                'name': 'Patient Count',
                'icon': 'bi-bar-chart-line-fill',
                'url': '/front-office/patient-count/',
                'description': 'Daily and period-wise patient footfall and transaction volume counts',
            },
            {
                'key': 'fo_op_ip_census',
                'name': 'OP-IP Census',
                'icon': 'bi-pie-chart-fill',
                'url': '/front-office/op-ip-census/',
                'description': 'Live hospital census of new, review, admitted, and discharged patients',
            },
            {
                'key': 'fo_abha_search',
                'name': 'ABHA Search',
                'icon': 'bi-person-badge-fill',
                'url': '/front-office/abha-search/',
                'description': 'Patients Aadhaar and ABHAID directory and compliance review',
            },
            {
                'key': 'fo_patient_type',
                'name': 'Patient Type',
                'icon': 'bi-tags-fill',
                'url': '/front-office/patient-type/',
                'description': 'Filter and analyze patients by Normal, Company, NRI, and Emergency',
            },
            {
                'key': 'fo_user_log',
                'name': 'User Log',
                'icon': 'bi-person-lines-fill',
                'url': '/front-office/user-log/',
                'description': 'Front office staff user activity audit logs for registrations, billing, and discharges',
            },
        ]
    },
    {
        'id': 'patients',
        'key': 'patients',
        'name': 'Patients',
        'icon': 'bi-people-fill',
        'color': '#0ea5e9',
        'badge': 'OPD / IPD',
        'description': 'Patient registration, search directory, review consultations, and discharge marking',
        'submodules': [
            {
                'key': 'add_patient',
                'name': '+ Add Patient',
                'icon': 'bi-person-plus-fill',
                'url': '/patients/add/',
                'description': 'Register new outpatient / inpatient records with auto-generated UHID',
            },
            {
                'key': 'search_patient',
                'name': 'Search Patient',
                'icon': 'bi-search',
                'url': '/patients/search/',
                'description': 'Find patient records by UHID, patient name, or mobile number',
            },
            {
                'key': 'patient_list',
                'name': 'Patient List',
                'icon': 'bi-person-lines-fill',
                'url': '/patients/',
                'description': 'Complete searchable and filterable directory of all registered patients',
            },
            {
                'key': 'patient_import',
                'name': 'Patient Import',
                'icon': 'bi-cloud-arrow-up',
                'url': '/patients/import/',
                'description': 'Bulk upload historical patient records via CSV / Excel sheets',
            },
            {
                'key': 'review',
                'name': 'Patient Review',
                'icon': 'bi-clock-history',
                'url': '/patients/review/',
                'description': 'Schedule and conduct follow-up consultations and review notes',
            },
            {
                'key': 'discharge',
                'name': 'Discharge Marking',
                'icon': 'bi-box-arrow-right',
                'url': '/patients/discharge/',
                'description': 'Mark patient discharge readiness and generate final discharge summary',
            },
            {
                'key': 'patient_companies',
                'name': 'Patient Companies',
                'icon': 'bi-building',
                'url': '/patients/companies/',
                'description': 'Corporate affiliations, insurances, and empanelled organizations',
            },
            {
                'key': 'department_list',
                'name': 'Departments & Units',
                'icon': 'bi-diagram-3',
                'url': '/patients/departments/',
                'description': 'Configure hospital clinical departments and medical specialty units',
            },
        ]
    },
    {
        'id': 'ward',
        'key': 'ward',
        'name': 'Ward & Transfer',
        'icon': 'bi-hospital',
        'color': '#2563eb',
        'badge': 'Inpatient',
        'description': 'Ward bed matrix allocation, occupancy management, service requests, and patient transfers',
        'submodules': [
            {
                'key': 'ward_allocation',
                'name': 'Ward Allocation (Bed Matrix)',
                'icon': 'bi-grid-3x3-gap',
                'url': '/patients/ward/allocation/',
                'description': 'Live visual matrix of hospital ward beds, occupancy status, and admission slotting',
            },
            {
                'key': 'ward_management',
                'name': 'Ward Management',
                'icon': 'bi-building',
                'url': '/patients/wards/',
                'description': 'Setup hospital wards, bed capacities, room types, and nurse stations',
            },
            {
                'key': 'ward_service_request',
                'name': 'Ward Service Request',
                'icon': 'bi-clipboard-plus',
                'url': '/patients/ward/service-request/',
                'description': 'Order diagnostic tests, nursing care, and medication for admitted patients',
            },
            {
                'key': 'branch_transfer',
                'name': 'Ward Transfer',
                'icon': 'bi-arrow-left-right',
                'url': '/patients/branch-transfer/',
                'description': 'Transfer admitted patients between different wards or bed categories',
            },
            {
                'key': 'branch_transfer_report',
                'name': 'Ward Transfer Report',
                'icon': 'bi-file-earmark-bar-graph',
                'url': '/patients/branch-transfer/report/',
                'description': 'Audit trail and chronological reports of all inpatient movements',
            },
        ]
    },
    {
        'id': 'master',
        'key': 'master',
        'name': 'Master Settings',
        'icon': 'bi-sliders2',
        'color': '#4f46e5',
        'badge': 'Configuration',
        'description': 'Master datasets for clinical departments, investigations, parameters, reference ranges, and mappings',
        'submodules': [
            {
                'key': 'lab_master_dashboard',
                'name': 'Lab Master Hub',
                'icon': 'bi-grid-fill',
                'url': '/lab/master/hub/',
                'description': 'Central hub for laboratory master definitions and quick shortcuts',
            },
            {
                'key': 'master_departments',
                'name': 'Hospital Departments',
                'icon': 'bi-building',
                'url': '/patients/departments/',
                'description': 'Medical department records and administrative classifications',
            },
            {
                'key': 'lab_sub_departments',
                'name': 'Lab Departments',
                'icon': 'bi-building-gear',
                'url': '/lab/master/lab-departments/',
                'description': 'Sub-lab divisions (Biochemistry, Hematology, Microbiology, Histopathology)',
            },
            {
                'key': 'master_wards',
                'name': 'Hospital Wards',
                'icon': 'bi-hospital',
                'url': '/patients/wards/',
                'description': 'Inpatient ward master configurations and categorization',
            },
            {
                'key': 'master_investigations',
                'name': 'Investigations Master',
                'icon': 'bi-file-medical',
                'url': '/lab/master/investigations/',
                'description': 'Catalog of laboratory diagnostic tests, test codes, and specimen types',
            },
            {
                'key': 'master_parameters',
                'name': 'Parameters Master',
                'icon': 'bi-list-check',
                'url': '/lab/master/parameters/',
                'description': 'Observable parameters, units of measure, and default values',
            },
            {
                'key': 'investigation_parameter_mapping',
                'name': 'Investigation Parameters',
                'icon': 'bi-diagram-3',
                'url': '/lab/master/investigation-parameter-mapping/',
                'description': 'Associate parameters with investigation tests and define observation ordering',
            },
            {
                'key': 'master_reference_ranges',
                'name': 'Reference Ranges',
                'icon': 'bi-rulers',
                'url': '/lab/master/reference-ranges/',
                'description': 'Age and gender-specific biological normal reference intervals',
            },
            {
                'key': 'master_diagnosis_list',
                'name': 'Diagnoses Master',
                'icon': 'bi-clipboard2-pulse',
                'url': '/lab/master/diagnoses/',
                'description': 'Clinical diagnosis codes and disease definitions directory',
            },
            {
                'key': 'master_diagnosis_investigation_mapping',
                'name': 'Diagnosis -> Investigation',
                'icon': 'bi-arrow-left-right',
                'url': '/lab/master/diagnosis-investigation-mapping/',
                'description': 'Link clinical diagnoses to recommended diagnostic investigation panels',
            },
            {
                'key': 'master_diagnosis_department_mapping',
                'name': 'Diagnosis -> Department',
                'icon': 'bi-building',
                'url': '/lab/master/diagnosis-department-mapping/',
                'description': 'Assign diagnosis codes to primary hospital specialty departments',
            },
            {
                'key': 'master_age_groups',
                'name': 'Age Groups',
                'icon': 'bi-people',
                'url': '/lab/master/age-groups/',
                'description': 'Age group bracket classifications for physiological reference evaluation',
            },
            {
                'key': 'mapping_validation',
                'name': 'Master Validation',
                'icon': 'bi-shield-check',
                'url': '/lab/master/validation/',
                'description': 'Automated validation check for orphaned tests, missing ranges, or broken mappings',
            },
            {
                'key': 'legacy_mapping',
                'name': 'Universal Import / Export',
                'icon': 'bi-file-earmark-spreadsheet',
                'url': '/lab/legacy-mapping/',
                'description': 'Bulk master data import / export from legacy systems and spreadsheets',
            },
        ]
    },
    {
        'id': 'lab',
        'key': 'auto_trigger_section',
        'name': 'Laboratory',
        'icon': 'bi-robot',
        'color': '#7c3aed',
        'badge': 'Diagnostics',
        'description': 'Doctor window, test ordering, auto test synthesizers, and Automated Test Controller (ATC)',
        'submodules': [
            {
                'key': 'doctor_window',
                'name': 'Doctor Window',
                'icon': 'bi-window-desktop',
                'url': '/lab/doctor-window/',
                'description': 'Physician consultation portal for placing test orders and viewing findings',
            },
            {
                'key': 'service_request_add',
                'name': 'Service Request',
                'icon': 'bi-file-earmark-medical',
                'url': '/lab/service-request/add/',
                'description': 'Initiate diagnostic and specialty clinical test requests for patients',
            },
            {
                'key': 'auto_trigger_automate_test',
                'name': 'Create Dummy Result',
                'icon': 'bi-robot',
                'url': '/lab/auto-trigger/automate-test/',
                'description': 'Synthesize simulated laboratory result values within valid reference ranges',
            },
            {
                'key': 'auto_trigger_result_view',
                'name': 'Saved Dummy Results',
                'icon': 'bi-journal-check',
                'url': '/lab/auto-trigger/result-view/',
                'description': 'Review, verify, and inspect generated dummy test results database',
            },
            {
                'key': 'auto_trigger_configuration',
                'name': 'Auto Trigger Configuration',
                'icon': 'bi-sliders',
                'url': '/lab/auto-trigger/configuration/',
                'description': 'Set up automated background diagnostic trigger rules and schedules',
            },
            {
                'key': 'auto_trigger_history',
                'name': 'Auto Trigger History',
                'icon': 'bi-clock-history',
                'url': '/lab/auto-trigger/history/',
                'description': 'Audit log of past automated test generation executions and batch runs',
            },
            {
                'key': 'auto_trigger_monthly_create',
                'name': 'Monthly Trigger',
                'icon': 'bi-calendar-plus',
                'url': '/lab/auto-trigger/monthly-create/',
                'description': 'Batch generate monthly simulation workloads across departments',
            },
            {
                'key': 'auto_trigger_monthly',
                'name': 'Monthly Trigger History',
                'icon': 'bi-calendar-month',
                'url': '/lab/auto-trigger/monthly/',
                'description': 'Monthly simulation records, execution dates, and archive logs',
            },
            {
                'key': 'auto_trigger_monthly_census',
                'name': 'Monthly Census',
                'icon': 'bi-bar-chart',
                'url': '/lab/auto-trigger/monthly-census/',
                'description': 'Comprehensive monthly test volume census and department breakdowns',
            },
            {
                'key': 'auto_trigger_atc',
                'name': 'ATC Automation',
                'icon': 'bi-play-circle-fill',
                'url': '/lab/auto-trigger/atc/',
                'description': 'Direct control and manual initiation of Automated Test Controller daemon',
            },
            {
                'key': 'investigation_marking',
                'name': 'Investigation Marking',
                'icon': 'bi-flask',
                'url': '/lab/investigation-marking/',
                'description': 'Track specimen barcode scanning, collection, and technician sign-off',
            },
            {
                'key': 'auto_trigger_atc_status',
                'name': 'ATC Live Status',
                'icon': 'bi-activity',
                'url': '/lab/auto-trigger/atc-status/',
                'description': 'Real-time telemetry and process status of the background ATC engine',
            },
            {
                'key': 'auto_trigger_atc_settings',
                'name': 'ATC Settings',
                'icon': 'bi-gear',
                'url': '/lab/auto-trigger/atc-settings/',
                'description': 'Tuning execution intervals, concurrency limits, and threshold limits',
            },
        ]
    },
    {
        'id': 'billing',
        'key': 'lab_orders',
        'name': 'Billing',
        'icon': 'bi-receipt-cutoff',
        'color': '#059669',
        'badge': 'Revenue',
        'description': 'Work orders, diagnostic billing entries, manual result entry, and service request lists',
        'submodules': [
            {
                'key': 'work_orders',
                'name': 'Work Orders',
                'icon': 'bi-list-task',
                'url': '/lab/work-orders/',
                'description': 'Active laboratory order queue and specimen accession management',
            },
            {
                'key': 'order_entry',
                'name': 'New Lab Order',
                'icon': 'bi-plus-circle',
                'url': '/lab/order-entry/',
                'description': 'Create new diagnostic billing requisition and generate work order invoice',
            },
            {
                'key': 'result_entry_list',
                'name': 'Result Entry',
                'icon': 'bi-journal-text',
                'url': '/lab/result-entry/',
                'description': 'Technician portal to record, modify, and authorize patient lab test findings',
            },
            {
                'key': 'service_request_list',
                'name': 'Service Request List',
                'icon': 'bi-file-earmark-ruled',
                'url': '/lab/service-requests/',
                'description': 'Central list of diagnostic service requisitions awaiting processing',
            },
        ]
    },
    {
        'id': 'reports',
        'key': 'lab_reports',
        'name': 'Reports',
        'icon': 'bi-file-earmark-bar-graph-fill',
        'color': '#d97706',
        'badge': 'Analytics',
        'description': 'Operational and clinical reports, daily/monthly summaries, and abnormal findings alerts',
        'submodules': [
            {
                'key': 'report_dashboard',
                'name': 'Lab Reports Dashboard',
                'icon': 'bi-speedometer2',
                'url': '/lab/reports/',
                'description': 'Executive reporting dashboard with high-level summaries and diagnostic trends',
            },
            {
                'key': 'review_report',
                'name': 'Review Report',
                'icon': 'bi-file-earmark-text',
                'url': '/patients/reports/review/',
                'description': 'Summary report of patient review appointments and consultation volumes',
            },
            {
                'key': 'op_census',
                'name': 'OP Census Report',
                'icon': 'bi-graph-up',
                'url': '/patients/reports/op-census/',
                'description': 'Outpatient attendance metrics grouped by specialty, unit, and date range',
            },
            {
                'key': 'branch_transfer_report',
                'name': 'Ward Transfer Report',
                'icon': 'bi-arrow-left-right',
                'url': '/patients/branch-transfer/report/',
                'description': 'Detailed breakdown of inpatient bed and ward transfer activity',
            },
            {
                'key': 'report_daily',
                'name': 'Daily Report',
                'icon': 'bi-calendar-day',
                'url': '/lab/reports/daily/',
                'description': 'Day-wise detailed breakdown of diagnostic test orders and results',
            },
            {
                'key': 'report_monthly',
                'name': 'Monthly Report',
                'icon': 'bi-calendar-month',
                'url': '/lab/reports/monthly/',
                'description': 'Aggregated monthly workload volume and operational diagnostics',
            },
            {
                'key': 'report_sub_department',
                'name': 'Sub Department Report',
                'icon': 'bi-diagram-2',
                'url': '/lab/reports/sub-department/',
                'description': 'Workload volume grouped by laboratory sub-departments',
            },
            {
                'key': 'report_investigation',
                'name': 'Investigation Report',
                'icon': 'bi-file-medical',
                'url': '/lab/reports/investigation/',
                'description': 'Frequency and workload statistics by individual investigation tests',
            },
            {
                'key': 'report_hospital_department',
                'name': 'Hospital Dept Report',
                'icon': 'bi-building',
                'url': '/lab/reports/hospital-department/',
                'description': 'Diagnostic test orders categorized by requesting hospital department',
            },
            {
                'key': 'report_abnormal',
                'name': 'Abnormal Result Report',
                'icon': 'bi-exclamation-triangle',
                'url': '/lab/reports/abnormal/',
                'description': 'Critical and out-of-range laboratory test results requiring clinical follow-up',
            },
        ]
    },
    {
        'id': 'ot',
        'key': 'ot',
        'name': 'Operation Theatre',
        'icon': 'bi-scissors',
        'color': '#dc2626',
        'badge': 'Surgery',
        'description': 'OT dashboards, surgical bookings, slot schedules, live OT monitor, and surgical history',
        'submodules': [
            {
                'key': 'ot_dashboard',
                'name': 'OT Dashboard',
                'icon': 'bi-grid-1x2',
                'url': '/ot/',
                'description': 'Overview of surgical theatre utilization, upcoming cases, and team readiness',
            },
            {
                'key': 'ot_booking',
                'name': 'OT Booking',
                'icon': 'bi-calendar-plus',
                'url': '/ot/bookings/',
                'description': 'Schedule and register surgical procedure bookings for admitted patients',
            },
            {
                'key': 'ot_schedule',
                'name': 'OT Schedule',
                'icon': 'bi-calendar-week',
                'url': '/ot/schedule/',
                'description': 'Daily and weekly surgeon, theatre room, and anesthesiology slot timetable',
            },
            {
                'key': 'ot_live',
                'name': 'Live OT',
                'icon': 'bi-activity',
                'url': '/ot/live/',
                'description': 'Real-time surgical progression tracker across all active operation theatres',
            },
            {
                'key': 'ot_history',
                'name': 'OT History',
                'icon': 'bi-clock-history',
                'url': '/ot/history/',
                'description': 'Historical surgical registry, post-operative notes, and surgery outcomes',
            },
            {
                'key': 'ot_master',
                'name': 'OT Master',
                'icon': 'bi-database-gear',
                'url': '/ot/master/',
                'description': 'Master definitions for theatre rooms, anesthesia types, and surgical equipment',
            },
        ]
    },
    {
        'id': 'administration',
        'key': 'system_section',
        'name': 'Administration',
        'icon': 'bi-shield-shaded',
        'color': '#6b21a8',
        'badge': 'System',
        'description': 'User accounts directory, custom role profiles, navbar mapping, and access matrices',
        'submodules': [
            {
                'key': 'administration',
                'name': 'User Accounts',
                'icon': 'bi-person-gear',
                'url': '/administration/',
                'description': 'Create, edit, reset passwords, and manage active system user accounts',
            },
            {
                'key': 'users_roles',
                'name': 'Users & Roles',
                'icon': 'bi-person-badge',
                'url': '/administration/roles-overview/',
                'description': 'Overview and configuration of user roles, staff profiles, and security levels',
            },
            {
                'key': 'navbar_mapping',
                'name': 'Nav Bar Mapping',
                'icon': 'bi-diagram-3-fill',
                'url': '/administration/navbar-mapping/',
                'description': 'Map and toggle top navigation bar modules and dropdown submodules per role',
            },
            {
                'key': 'landing_departments',
                'name': 'Landing Departments',
                'icon': 'bi-grid-1x2-fill',
                'url': '/administration/landing-departments/',
                'description': 'Create, edit, delete, and customize department login cards on the landing page',
            },
            {
                'key': 'role_permissions',
                'name': 'Role Access Matrix',
                'icon': 'bi-grid-3x3-gap-fill',
                'url': '/administration/roles/access-matrix/',
                'description': 'Comprehensive security permissions and sidebar access control matrix',
            },
        ]
    },
    {
        'id': 'inventory',
        'key': 'inventory',
        'name': 'Inventory',
        'icon': 'bi-boxes',
        'color': '#0891b2',
        'badge': 'Supplies',
        'description': 'Pharmacy consumables, diagnostic reagent stocks, and hospital store inventory',
        'submodules': [
            {
                'key': 'inventory',
                'name': 'Stock Management',
                'icon': 'bi-box-seam',
                'url': '#',
                'description': 'Track reagent kits, hospital consumables, stock batch numbers, and reorder levels',
            },
        ]
    },
    {
        'id': 'settings',
        'key': 'settings',
        'name': 'Settings',
        'icon': 'bi-gear-fill',
        'color': '#475569',
        'badge': 'Config',
        'description': 'Hospital branding parameters, timestamps, timezone, and system preferences',
        'submodules': [
            {
                'key': 'settings',
                'name': 'System Configuration',
                'icon': 'bi-sliders',
                'url': '#',
                'description': 'General ERP parameters, hospital metadata, logo branding, and print formats',
            },
        ]
    },
]

DEPT_DEFAULT_NAV_MAPPING = {
    'front_desk': {
        'front_office': True, 'fo_landing': True, 'fo_crm': True, 'fo_admission_request': True,
        'fo_registration_search': True, 'fo_patient_count': True, 'fo_op_ip_census': True,
        'fo_abha_search': True, 'fo_patient_type': True, 'fo_user_log': True,
        'patients': True, 'add_patient': True, 'search_patient': True,
        'patient_list': True, 'op_census': True, 'patient_import': True,
        'department_list': True,
    },
    'consultant': {
        'front_office': True, 'fo_landing': True, 'doctor_window': True, 'service_request_add': True,
        'patients': True, 'search_patient': True, 'patient_list': True,
        'review': True, 'ward': True, 'branch_transfer': True,
    },
    'billing': {
        'front_office': True, 'fo_landing': True, 'fo_user_log': True, 'billing': True,
        'patients': True, 'search_patient': True, 'patient_list': True,
    },
    'lab': {
        'lab_orders': True, 'lab_work_orders': True, 'doctor_window': True,
        'lab_sub_departments': True, 'workload_mapping_list': True,
        'universal_master_import_export': True, 'lab_reports': True,
        'lab_reports_dashboard': True,
    },
    'ward': {
        'ward': True, 'ward_allocation': True, 'ward_management': True,
        'ward_service_request': True, 'ward_transfer': True,
        'branch_transfer': True, 'branch_transfer_report': True,
        'patients': True, 'patient_list': True,
    },
    'mrd': {
        'front_office': True, 'fo_registration_search': True, 'fo_op_ip_census': True,
        'patients': True, 'review': True, 'discharge': True,
        'review_report': True, 'search_patient': True, 'patient_list': True,
    },
    'pharmacy': {
        'inventory': True, 'patients': True, 'search_patient': True,
    },
    'inventory': {
        'inventory': True,
    },
    'blood_bank': {
        'lab_orders': True, 'lab_work_orders': True, 'lab_reports': True,
    },
    'radiology': {
        'lab_orders': True, 'lab_work_orders': True, 'lab_reports': True,
    },
    'ot': {
        'ot_module': True, 'ot_booking': True, 'ot_schedule': True,
        'ot_live': True, 'ot_history': True, 'ot_master': True,
        'ward': True, 'ward_management': True,
    },
    'summary': {
        'front_office': True, 'patients': True, 'discharge': True, 'review': True, 'review_report': True,
    },
    'accounts': {
        'front_office': True, 'billing': True, 'lab_reports': True,
    },
    'report': {
        'front_office': True, 'fo_op_ip_census': True, 'fo_patient_count': True,
        'lab_reports': True, 'lab_reports_dashboard': True,
        'patients': True, 'review_report': True, 'op_census': True,
    },
    'mis': {
        'front_office': True, 'fo_landing': True, 'fo_op_ip_census': True, 'fo_patient_count': True,
        'lab_reports': True, 'lab_reports_dashboard': True,
        'patients': True, 'op_census': True,
    },
    'clinical_department': {
        'front_office': True, 'patients': True, 'department_list': True, 'patient_list': True,
        'op_census': True, 'ward': True, 'ward_allocation': True,
    },
}


def seed_default_nav_modules_if_needed(force=False):
    """
    Seeds or updates default NavModule and NavSubmodule records in the database.
    """
    try:
        from apps.users.models import NavModule, NavSubmodule
        if not force and NavModule.objects.filter(is_active=True).exists():
            return

        with transaction.atomic():
            for i, m in enumerate(NAVBAR_MODULES_CONFIG, 1):
                mod_obj, _ = NavModule.objects.update_or_create(
                    code=m['key'],
                    defaults={
                        'name': m['name'],
                        'icon': m['icon'],
                        'url_path': m['submodules'][0]['url'] if m['submodules'] else '#',
                        'color': m.get('color', '#0284c7'),
                        'badge': m.get('badge', ''),
                        'description': m.get('description', ''),
                        'order': i * 10,
                        'is_active': True,
                        'is_system': True,
                    }
                )
                for j, s in enumerate(m.get('submodules', []), 1):
                    NavSubmodule.objects.update_or_create(
                        code=s['key'],
                        defaults={
                            'module': mod_obj,
                            'name': s['name'],
                            'icon': s['icon'],
                            'url_path': s['url'],
                            'description': s.get('description', ''),
                            'order': j * 10,
                            'is_active': True,
                            'is_system': True,
                        }
                    )
    except Exception as e:
        print(f"[seed_default_nav_modules_if_needed] Warning: {e}")
