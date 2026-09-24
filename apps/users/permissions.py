"""
VMMC ERP Comprehensive Granular Permission Matrix Definitions.
Defines module and submodule permissions with specific Action verbs:
- view: View list & record details
- create: Create/Add new records
- update: Edit/Modify existing records
- delete: Delete/Remove records
- import: Bulk Import CSV/Excel data
- export: Export Reports/Excel/PDF/CSV
"""

PERMISSION_MODULES = [
    {
        "module": "dashboard",
        "label": "Dashboard Overview",
        "icon": "bi-speedometer2",
        "sub_modules": [
            {
                "code": "dashboard",
                "label": "Executive MIS Dashboard",
                "actions": ["view", "export"],
                "description": "Hospital KPI metrics, active admissions, census, and overview charts"
            }
        ]
    },
    {
        "module": "patients",
        "label": "Patient Management (OPD & Records)",
        "icon": "bi-people-fill",
        "sub_modules": [
            {
                "code": "patients.add_patient",
                "label": "Add Patient (UHID Registration)",
                "actions": ["view", "create"],
                "description": "Register new OPD/IPD patients and generate UHID"
            },
            {
                "code": "patients.search_patient",
                "label": "Search Patient (UHID Lookup)",
                "actions": ["view", "export"],
                "description": "Lookup patient records by UHID, name, or phone number"
            },
            {
                "code": "patients.patient_list",
                "label": "Patient Directory & Master List",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Complete directory of registered hospital patients"
            },
            {
                "code": "patients.patient_import",
                "label": "Patient Batch Import",
                "actions": ["view", "import", "export"],
                "description": "Bulk import patient data from CSV/Excel spreadsheets"
            },
            {
                "code": "patients.review",
                "label": "Patient Review & Case History",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Clinical case reviews, visit logs, and medical assessments"
            },
            {
                "code": "patients.discharge",
                "label": "Patient Discharge Management",
                "actions": ["view", "create", "update", "export"],
                "description": "Process patient discharges, summary notes, and clearance"
            },
            {
                "code": "patients.review_report",
                "label": "Patient Review Report",
                "actions": ["view", "export"],
                "description": "Audit and summary reports of patient clinical reviews"
            },
            {
                "code": "patients.op_census",
                "label": "OP Census Analytics",
                "actions": ["view", "export"],
                "description": "Daily and monthly outpatient footfall analytics"
            },
            {
                "code": "patients.patient_companies",
                "label": "Insurance & Corporate Companies",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Empanelled TPA, insurance providers, and corporate accounts"
            },
            {
                "code": "patients.department_list",
                "label": "Clinical Departments & Units",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Hospital medical departments, units, and specialties"
            },
        ]
    },
    {
        "module": "ward",
        "label": "Inpatient & Ward Management (IPD)",
        "icon": "bi-hospital",
        "sub_modules": [
            {
                "code": "ward.ward_allocation",
                "label": "Bed Matrix & Bed Allocation",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Assign beds, view real-time occupancy, and bed transfers"
            },
            {
                "code": "ward.ward_management",
                "label": "Ward Station & Room Config",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Configure ward wings, rooms, bed tariffs, and nursing stations"
            },
            {
                "code": "ward.ward_service_request",
                "label": "Ward Nursing Service Request",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Inpatient clinical orders, medication, and nursing requisitions"
            },
            {
                "code": "ward.branch_transfer",
                "label": "Ward & Inter-Department Transfer",
                "actions": ["view", "create", "update", "export"],
                "description": "Transfer admitted patients across wards or medical units"
            },
            {
                "code": "ward.branch_transfer_report",
                "label": "Ward Transfer Report",
                "actions": ["view", "export"],
                "description": "Historical audit registry of inpatient bed and ward movements"
            },
        ]
    },
    {
        "module": "lab_master",
        "label": "Laboratory Master Setup",
        "icon": "bi-sliders",
        "sub_modules": [
            {
                "code": "lab_master.diagnosis",
                "label": "Diagnosis Master Directory",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "ICD-10 clinical diagnosis catalog and department links"
            },
            {
                "code": "lab_master.investigation",
                "label": "Investigation Tests Master",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "Pathology, biochemistry, and microbiology test master catalog"
            },
            {
                "code": "lab_master.parameter",
                "label": "Test Parameters & Units Master",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "Individual analyte parameters, unit formulas, and specimen requirements"
            },
            {
                "code": "lab_master.mapping",
                "label": "Investigation-Parameter Mapping",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Map diagnostic parameters and formula sequences to parent tests"
            },
            {
                "code": "lab_master.reference_range",
                "label": "Biological Reference Ranges",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "Age, gender, and instrument-specific normal biological intervals"
            },
            {
                "code": "lab_master.workload_mapping",
                "label": "Workload Matrix Mapping",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "Diagnostic workload codes, instrument mapping, and test tariffs"
            },
            {
                "code": "lab_master.universal_import_export",
                "label": "Universal Master Import / Export",
                "actions": ["view", "import", "export"],
                "description": "Unified CSV/Excel bulk master data migration and backups"
            },
        ]
    },
    {
        "module": "lab_orders",
        "label": "Diagnostic Lab Orders & Processing",
        "icon": "bi-funnel-fill",
        "sub_modules": [
            {
                "code": "lab_orders.work_orders",
                "label": "Lab Work Orders Queue",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Active diagnostic test queue, accessioning, and barcode tracking"
            },
            {
                "code": "lab_orders.order_entry",
                "label": "New Diagnostic Order Entry",
                "actions": ["view", "create", "update", "delete"],
                "description": "Place test orders for OPD outpatients and IPD inpatients"
            },
            {
                "code": "lab_orders.result_entry",
                "label": "Lab Result Entry & Verification",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Enter test findings, flag critical values, and authorize reports"
            },
            {
                "code": "lab_orders.doctor_window",
                "label": "Doctor Window (Consultation Hub)",
                "actions": ["view", "create", "update", "export"],
                "description": "Consultant review window, diagnostic orders, and clinical impressions"
            },
        ]
    },
    {
        "module": "billing",
        "label": "Billing & Accounts",
        "icon": "bi-currency-rupee",
        "sub_modules": [
            {
                "code": "billing.opd_billing",
                "label": "OPD Consultation & Cash Counter",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Outpatient billing, cash collection, and receipt generation"
            },
            {
                "code": "billing.ipd_billing",
                "label": "IPD Inpatient Billing & Invoices",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Inpatient room tariffs, surgical fees, pharmacy bills, and final bill"
            },
            {
                "code": "billing.ledgers",
                "label": "Financial Ledgers & Vouchers",
                "actions": ["view", "create", "update", "export"],
                "description": "Cashbook, daybook, revenue reconciliation, and audit receipts"
            },
        ]
    },
    {
        "module": "lab_reports",
        "label": "Reports & Analytics",
        "icon": "bi-bar-chart-fill",
        "sub_modules": [
            {
                "code": "lab_reports.dashboard",
                "label": "Analytics & Reports Dashboard",
                "actions": ["view", "export"],
                "description": "Executive dashboard of clinical tests, turnaround times, and metrics"
            },
            {
                "code": "lab_reports.daily",
                "label": "Daily Test & Sample Reports",
                "actions": ["view", "export"],
                "description": "Daily workload summary, sample collections, and doctor referrals"
            },
            {
                "code": "lab_reports.monthly",
                "label": "Monthly Department Statistics",
                "actions": ["view", "export"],
                "description": "Monthly comparative revenue, volume metrics, and department reports"
            },
            {
                "code": "lab_reports.abnormal",
                "label": "Critical & Panic Value Reports",
                "actions": ["view", "export"],
                "description": "Urgent alert log of abnormal and critical biological results"
            },
        ]
    },
    {
        "module": "ot",
        "label": "Operation Theatre (OT)",
        "icon": "bi-scissors",
        "sub_modules": [
            {
                "code": "ot.booking",
                "label": "Surgical Procedure Bookings",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Register surgery bookings, anesthesiologist, and theatre room slots"
            },
            {
                "code": "ot.schedule",
                "label": "Theatre Timetable & Schedule",
                "actions": ["view", "create", "update", "export"],
                "description": "Daily and weekly surgical schedule grid across all theatre rooms"
            },
            {
                "code": "ot.live",
                "label": "Live OT Real-Time Progression",
                "actions": ["view", "update"],
                "description": "Real-time intra-operative tracking (Induction, Incision, Recovery)"
            },
            {
                "code": "ot.history",
                "label": "Surgery History & Post-Op Registry",
                "actions": ["view", "update", "export"],
                "description": "Historical surgical logs, implant details, and post-operative outcomes"
            },
            {
                "code": "ot.master",
                "label": "OT Theatres & Equipment Master",
                "actions": ["view", "create", "update", "delete"],
                "description": "Theatre room definitions, anesthesia types, and equipment master"
            },
        ]
    },
    {
        "module": "inventory",
        "label": "Stores & Stock Inventory",
        "icon": "bi-box-seam-fill",
        "sub_modules": [
            {
                "code": "inventory.stock",
                "label": "Stock Ledger & Reagent Inventory",
                "actions": ["view", "create", "update", "delete", "import", "export"],
                "description": "Track diagnostic reagent kits, consumables, batch numbers, and reorder levels"
            }
        ]
    },
    {
        "module": "administration",
        "label": "System Administration & Security",
        "icon": "bi-shield-lock-fill",
        "sub_modules": [
            {
                "code": "administration.user_management",
                "label": "User Accounts & Credentials",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Create, edit, reset passwords, and manage system user accounts"
            },
            {
                "code": "administration.roles",
                "label": "Role Profiles & Security Matrix",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Role profile definitions, access boundaries, and permissions matrix"
            },
            {
                "code": "administration.navbar_mapping",
                "label": "Nav Bar Modules & Submodules Mapping",
                "actions": ["view", "create", "update", "delete"],
                "description": "Configure top navigation bar structure per department and role"
            },
            {
                "code": "administration.landing_departments",
                "label": "Landing Page Departments Manager",
                "actions": ["view", "create", "update", "delete"],
                "description": "Create, edit, customize, and toggle front login department portals"
            },
        ]
    },
    {
        "module": "auto_trigger",
        "label": "Auto Trigger Engine & ATC",
        "icon": "bi-cpu-fill",
        "sub_modules": [
            {
                "code": "auto_trigger.configuration",
                "label": "Automation Schedule Rules",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Scheduled automation triggers, recurring rules, and cron routines"
            },
            {
                "code": "auto_trigger.history",
                "label": "Automation Run History & Logs",
                "actions": ["view", "export"],
                "description": "Execution logs, automated batch results, and performance metrics"
            },
            {
                "code": "auto_trigger.atc",
                "label": "ATC Control & Auto-Triggering",
                "actions": ["view", "create", "update", "delete", "export"],
                "description": "Automated test creation controls, test triggers, and emergency stops"
            },
        ]
    }
]

def get_all_permission_keys():
    """Returns list of all available permission keys across all modules and actions."""
    keys = []
    for mod in PERMISSION_MODULES:
        for sub in mod['sub_modules']:
            # Base access key
            keys.append(sub['code'])
            # Action keys
            for action in sub['actions']:
                keys.append(f"{sub['code']}.{action}")
                # Alias format: <subcode>_<action>
                keys.append(f"{sub['code'].replace('.', '_')}_{action}")
    return keys
