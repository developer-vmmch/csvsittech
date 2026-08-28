PERMISSION_MODULES = [
    {
        "module": "dashboard",
        "label": "Dashboard",
        "sub_modules": [
            {
                "code": "dashboard.overview",
                "label": "Overview",
                "actions": ["view"]
            }
        ]
    },
    {
        "module": "patients",
        "label": "Patients",
        "sub_modules": [
            {"code": "patients.add_patient", "label": "Add Patient", "actions": ["view", "create"]},
            {"code": "patients.search_patient", "label": "Search Patient", "actions": ["view"]},
            {"code": "patients.patient_list", "label": "Patient List", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "patients.patient_import", "label": "Patient Import", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "patients.patient_review", "label": "Patient Review", "actions": ["view", "create", "update", "delete", "export"]},
            {"code": "patients.review_report", "label": "Patient Review Report", "actions": ["view", "export"]},
            {"code": "patients.op_census", "label": "OP Census", "actions": ["view", "export"]},
            {"code": "patients.patient_companies", "label": "Patient Companies", "actions": ["view", "create", "update", "delete", "export"]},
            {"code": "patients.add_company", "label": "Add Company", "actions": ["view", "create"]},
            {"code": "patients.departments_units", "label": "Departments & Units", "actions": ["view", "create", "update", "delete", "export"]},
            {"code": "patients.add_department", "label": "Add Department", "actions": ["view", "create"]},
        ]
    },
    {
        "module": "lab_master",
        "label": "Lab Master",
        "sub_modules": [
            {"code": "lab_master.diagnosis", "label": "Diagnosis", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.investigation", "label": "Investigation", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.parameter", "label": "Parameter", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.age_group", "label": "Age Group", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.mapping", "label": "Investigation Parameter Mapping", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.reference_range", "label": "Reference Range Grid", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_master.legacy_mapping", "label": "Legacy Mapping", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
        ]
    },
    {
        "module": "lab_orders",
        "label": "Lab Orders",
        "sub_modules": [
            {"code": "lab_orders.service_request", "label": "Service Request", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.lab_order_list", "label": "Lab Order List", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.create_lab_order", "label": "Create Lab Order", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.pending_orders", "label": "Pending Orders", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.processing_orders", "label": "Processing Orders", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.completed_orders", "label": "Completed Orders", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.cancelled_orders", "label": "Cancelled Orders", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
            {"code": "lab_orders.lab_order_reports", "label": "Lab Order Reports", "actions": ["view", "create", "update", "cancel", "delete", "export"]},
        ]
    },
    {
        "module": "consultant",
        "label": "Consultant",
        "sub_modules": [
            {"code": "consultant.doctor_window", "label": "Doctor Window", "actions": ["view", "create", "update", "delete"]}
        ]
    },
    {
        "module": "administration",
        "label": "Administration",
        "sub_modules": [
            {"code": "administration.user_management", "label": "User Management", "actions": ["view", "create", "update", "delete", "export"]},
            {"code": "administration.profiles", "label": "Profiles", "actions": ["view", "create", "update", "delete", "export"]},
            {"code": "administration.permissions", "label": "Permissions", "actions": ["view", "update"]},
            {"code": "administration.import_history", "label": "Import History", "actions": ["view", "export"]},
        ]
    },
    {
        "module": "auto_trigger",
        "label": "Auto Trigger",
        "sub_modules": [
            {"code": "auto_trigger.configuration", "label": "Auto Trigger Configuration", "actions": ["view", "create", "update", "delete", "trigger", "export"]},
            {"code": "auto_trigger.time_settings", "label": "Auto Trigger Time Settings", "actions": ["view", "create", "update", "delete"]},
            {"code": "auto_trigger.history", "label": "Auto Trigger History", "actions": ["view", "retry", "export"]},
        ]
    }
]

def get_all_permission_keys():
    keys = []
    for mod in PERMISSION_MODULES:
        for sub in mod['sub_modules']:
            for action in sub['actions']:
                keys.append(f"{sub['code']}.{action}")
    return keys
