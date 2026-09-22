from django.urls import path
from .views import (
    api_diagnosis_investigations,
    api_lab_diagnosis_save, api_lab_diagnosis_delete, api_investigation_delete, api_parameter_delete, api_agegroup_save, api_agegroup_delete,
    api_diagnosis_delete,
    DiagnosisListView, DiagnosisCreateView, DiagnosisUpdateView, api_diagnosis_save,
    LabDiagnosisListView, LabDiagnosisCreateView, LabDiagnosisUpdateView,
    InvestigationListView, InvestigationCreateView, InvestigationUpdateView, InvestigationDetailView, api_investigation_save,
    ParameterListView, ParameterCreateView, ParameterUpdateView, api_parameter_save,
    AgeGroupListView, AgeGroupCreateView, AgeGroupUpdateView,
    ReferenceRangeGridView, get_investigation_parameters, get_reference_ranges, get_reference_ranges_bulk, get_reference_ranges_all, save_reference_range, save_multiple_reference_ranges, delete_reference_range,
    InvestigationParameterMappingView, get_all_parameters, save_investigation_parameters, api_add_parameter,
    api_add_department, api_add_sample_type, api_referencerange_save, api_referencerange_delete,
    api_investigation_parameter_mapping_save, api_investigation_parameter_mapping_delete,
    OrderEntryView, ResultEntryListView, ResultEntryDetailView,
    LegacyMappingView, process_legacy_mapping,
    ServiceRequestListView, ServiceRequestCreateView,
    api_get_patients_for_request, api_search_diagnosis, api_suggest_investigations, api_search_investigation, api_allocate_service_request, api_save_and_trigger,
    api_diagnosis_count, api_investigation_count, api_parameter_count,
    DoctorWindowView, api_doctor_window_patients, api_doctor_window_get_diagnosis, api_doctor_window_save_diagnosis,
    WorkOrdersView, WorkOrderDetailView, api_work_orders_list, api_work_order_receive, api_work_order_receive_multiple, WorkOrderResultEntryView, WorkOrderPrintPreviewView, api_work_order_save_result, api_work_order_investigation_params
)
from .import_views import (
    DiagnosisImportView, DiagnosisImportHistoryView,
    LabDiagnosisImportView, LabDiagnosisImportHistoryView,
    api_diagnosis_download_template, api_diagnosis_preview, api_diagnosis_import,
    LabDiagnosisImportView, LabDiagnosisImportHistoryView,
    api_lab_diagnosis_download_template, api_lab_diagnosis_preview, api_lab_diagnosis_import,
    InvestigationImportView, InvestigationImportHistoryView,
    api_investigation_download_template, api_investigation_preview, api_investigation_import,
    ParameterImportView, ParameterImportHistoryView,
    api_parameter_download_template, api_parameter_preview, api_parameter_import,
    ReferenceRangeImportView, ReferenceRangeImportHistoryView,
    api_referencerange_download_template, api_referencerange_preview, api_referencerange_import,
    AgeGroupImportView, AgeGroupImportHistoryView,
    api_agegroup_download_template, api_agegroup_preview, api_agegroup_import,
    DiagnosisInvestigationMapImportView,
    api_diag_inv_map_download_template, api_diag_inv_map_preview, api_diag_inv_map_import
)

from .reference_range_grid_views import (
    api_reference_ranges_grid_list, api_reference_ranges_grid_detail,
    api_reference_ranges_grid_save, api_reference_ranges_grid_delete,
    api_agegroup_search
)

from .diagnosis_investigation_map_views import (
    diagnosis_investigation_mapping_view,
    api_diagnosis_investigation_map_list, api_diagnosis_investigation_map_detail,
    api_diagnosis_investigation_map_save, api_diagnosis_investigation_map_delete
)
from .diagnosis_department_mapping_views import (
    diagnosis_department_mapping_view, api_diagnosis_department_map_list,
    api_diagnosis_department_map_save, api_diagnosis_department_map_delete,
    api_diagnosis_department_map_unmapped_diagnoses, api_diagnosis_department_map_mapped_diagnoses,
    api_diag_dept_map_download_template, api_diag_dept_map_preview, api_diag_dept_map_import
)
from .mapping_import_views import (
    InvestigationParameterMappingImportView,
    api_inv_param_map_download_template, api_inv_param_map_preview, api_inv_param_map_import,
    DiagnosisDeptMappingImportView,
    api_diag_dept_smart_download_template, api_diag_dept_smart_preview, api_diag_dept_smart_import,
    api_diag_inv_smart_preview, api_diag_inv_smart_import,
)
from .auto_trigger_views import (
    AutoTriggerConfigurationView, AutoTriggerHistoryView, AutoTriggerMonthlyView, AutoTriggerMonthlyCreateView, AutoTriggerMonthlyCensusView, AutoTriggerTimeSettingsView,
    api_save_auto_trigger_config, api_get_auto_trigger_configs,
    api_execute_auto_trigger, api_get_auto_trigger_history,
    api_get_auto_trigger_history_detail, api_delete_auto_trigger_config,
    api_retry_failed_entries, api_save_time_setting, api_get_time_settings, api_delete_time_setting,
    api_get_auto_trigger_status, api_get_active_auto_trigger_run,
    api_get_monthly_trigger, api_save_monthly_trigger, api_stop_monthly_automation, api_stop_daily_execution,
    api_get_monthly_history, api_save_monthly_trigger_v2, api_get_daily_created_patients,
    AutoTriggerMonthlyReviewsView, api_get_monthly_reviews,
    AutoTriggerMonthlyExecutionView, AutoTriggerAutomateTestView, AutoTriggerResultView,
    api_get_investigation_parameters, api_generate_dummy_result_values, api_save_dummy_result, api_get_dummy_results, api_result_import_export
)

from .lab_master_views import (
    lab_master_dashboard, export_lab_workload_csv, import_lab_workload_csv,
    LabDepartmentListView, LabWorkloadMappingListView, UnmappedLabInvestigationListView
)
from .lab_reports import (
    lab_workload_dashboard, report_dashboard, report_daily, report_monthly,
    report_sub_department, report_investigation, report_hospital_department,
    report_benchmark, report_abnormal
)
from .atc_views import (
    ATCControlView, ATCLiveStatusView, ATCSettingsView,
    api_atc_trigger, api_atc_status, api_atc_stop, api_atc_active_job,
    api_atc_preview, api_atc_save_config, api_atc_date_statuses
)
from .master_views import (
    lab_master_hub,
    MasterInvestigationListView, MasterInvestigationDetailView,
    api_master_investigation_save, api_master_investigation_toggle_status,
    MasterParameterListView, api_master_parameter_save,
    MasterInvestigationParameterMappingView, api_master_inv_param_save, api_master_inv_param_delete,
    MasterReferenceRangeView, api_master_reference_range_save,
    MasterDiagnosisListView, api_master_diagnosis_save,
    api_master_diagnosis_get_rules, api_master_diagnosis_save_rule, api_master_diagnosis_delete_rule,
    MasterDiagnosisInvestigationMappingView, api_master_diag_inv_map_save, api_master_diag_inv_map_delete,
    MasterDiagnosisDepartmentMappingView, api_master_diag_dept_map_save,
    MasterAgeGroupListView, api_master_age_group_save,
    master_validation_view,
)
from .result_views import (
    lab_result_detail_view,
    lab_result_print_view,
)
from .investigation_marking_views import (
    investigation_marking_view,
    api_marking_load,
    api_marking_add_department,
    api_marking_remove_department,
    api_marking_save_configuration,
    api_marking_trigger,
    api_marking_clear,
)

app_name = 'lab'

urlpatterns = [
    # -----------------------------------------------------------------------
    # DEDICATED LAB MASTER MODULE
    # -----------------------------------------------------------------------
    path('master/', lab_master_hub, name='lab_master_hub'),
    path('master/investigations/', MasterInvestigationListView.as_view(), name='master_investigation_list'),
    path('master/investigations/<int:pk>/', MasterInvestigationDetailView.as_view(), name='master_investigation_detail'),
    path('master/api/investigations/save/', api_master_investigation_save, name='api_master_investigation_save'),
    path('master/api/investigations/<int:pk>/toggle-status/', api_master_investigation_toggle_status, name='api_master_investigation_toggle_status'),

    path('master/parameters/', MasterParameterListView.as_view(), name='master_parameter_list'),
    path('master/api/parameters/save/', api_master_parameter_save, name='api_master_parameter_save'),

    path('master/investigation-parameters/', MasterInvestigationParameterMappingView.as_view(), name='master_investigation_parameter_mapping'),
    path('master/api/investigation-parameters/save/', api_master_inv_param_save, name='api_master_inv_param_save'),
    path('master/api/investigation-parameters/<int:pk>/delete/', api_master_inv_param_delete, name='api_master_inv_param_delete'),

    path('master/reference-ranges/', MasterReferenceRangeView.as_view(), name='master_reference_ranges'),
    path('master/api/reference-ranges/save/', api_master_reference_range_save, name='api_master_reference_range_save'),

    path('master/diagnoses/', MasterDiagnosisListView.as_view(), name='master_diagnosis_list'),
    path('master/api/diagnoses/save/', api_master_diagnosis_save, name='api_master_diagnosis_save'),
    path('master/api/diagnoses/<int:pk>/rules/', api_master_diagnosis_get_rules, name='api_master_diagnosis_get_rules'),
    path('master/api/diagnoses/rules/save/', api_master_diagnosis_save_rule, name='api_master_diagnosis_save_rule'),
    path('master/api/diagnoses/rules/<int:pk>/delete/', api_master_diagnosis_delete_rule, name='api_master_diagnosis_delete_rule'),

    path('master/diagnosis-investigations/', MasterDiagnosisInvestigationMappingView.as_view(), name='master_diagnosis_investigation_mapping'),
    path('master/api/diagnosis-investigations/save/', api_master_diag_inv_map_save, name='api_master_diag_inv_map_save'),
    path('master/api/diagnosis-investigations/<int:pk>/delete/', api_master_diag_inv_map_delete, name='api_master_diag_inv_map_delete'),

    path('master/diagnosis-departments/', MasterDiagnosisDepartmentMappingView.as_view(), name='master_diagnosis_department_mapping'),
    path('master/api/diagnosis-departments/save/', api_master_diag_dept_map_save, name='api_master_diag_dept_map_save'),

    path('master/age-groups/', MasterAgeGroupListView.as_view(), name='master_age_groups'),
    path('master/api/age-groups/save/', api_master_age_group_save, name='api_master_age_group_save'),

    path('master/validation/', master_validation_view, name='master_validation'),

    # -----------------------------------------------------------------------
    # DYNAMIC LAB RESULTS & PRINTING
    # -----------------------------------------------------------------------
    path('results/view/<int:pk>/', lab_result_detail_view, name='lab_result_detail'),
    path('results/print/<int:pk>/', lab_result_print_view, name='lab_result_print'),

    path('api/reference-range/save/', api_referencerange_save, name='api_referencerange_save'),
    path('api/reference-range/<int:pk>/delete/', api_referencerange_delete, name='api_referencerange_delete'),
    path('api/investigation-parameter-mapping/save/', api_investigation_parameter_mapping_save, name='api_investigation_parameter_mapping_save'),
    path('api/investigation-parameter-mapping/<int:pk>/delete/', api_investigation_parameter_mapping_delete, name='api_investigation_parameter_mapping_delete'),
    # Diagnosis Master
    path('diagnosis/', DiagnosisListView.as_view(), name='diagnosis_list'),
    path('diagnosis/add/', DiagnosisCreateView.as_view(), name='diagnosis_add'),
    path('diagnosis/<int:pk>/edit/', DiagnosisUpdateView.as_view(), name='diagnosis_edit'),
    path('diagnosis/import/', DiagnosisImportView.as_view(), name='diagnosis_import'),
    path('diagnosis/import/history/', DiagnosisImportHistoryView.as_view(), name='diagnosis_import_history'),
    
    # Diagnosis Import APIs
    path('api/diagnosis/save/', api_diagnosis_save, name='api_diagnosis_save'),
    path('api/lab-diagnosis/save/', api_lab_diagnosis_save, name='api_lab_diagnosis_save'),
    path('api/lab-diagnosis/<int:pk>/delete/', api_lab_diagnosis_delete, name='api_lab_diagnosis_delete'),
    path('api/investigation/<int:pk>/delete/', api_investigation_delete, name='api_investigation_delete'),
    path('api/parameter/<int:pk>/delete/', api_parameter_delete, name='api_parameter_delete'),
    path('api/age-group/save/', api_agegroup_save, name='api_agegroup_save'),
    path('api/age-group/<int:pk>/delete/', api_agegroup_delete, name='api_agegroup_delete'),
    path('api/diagnosis/<int:pk>/delete/', api_diagnosis_delete, name='api_diagnosis_delete'),
    path('api/diagnosis-investigations/', api_diagnosis_investigations, name='api_diagnosis_investigations'),
    path('api/diagnosis/import/template/', api_diagnosis_download_template, name='api_diagnosis_import_template'),
    path('api/diagnosis/import/preview/', api_diagnosis_preview, name='api_diagnosis_import_preview'),
    path('api/diagnosis/import/process/', api_diagnosis_import, name='api_diagnosis_import_process'),
    
    # Lab Diagnosis
    path('lab-diagnosis/', LabDiagnosisListView.as_view(), name='lab_diagnosis_list'),
    path('lab-diagnosis/add/', LabDiagnosisCreateView.as_view(), name='lab_diagnosis_add'),
    path('lab-diagnosis/<int:pk>/edit/', LabDiagnosisUpdateView.as_view(), name='lab_diagnosis_edit'),

    path('lab-diagnosis/import/', LabDiagnosisImportView.as_view(), name='lab_diagnosis_import'),
    path('lab-diagnosis/import/history/', LabDiagnosisImportHistoryView.as_view(), name='lab_diagnosis_import_history'),
    path('api/lab-diagnosis/import/template/', api_lab_diagnosis_download_template, name='api_lab_diagnosis_import_template'),
    path('api/lab-diagnosis/import/preview/', api_lab_diagnosis_preview, name='api_lab_diagnosis_import_preview'),
    path('api/lab-diagnosis/import/process/', api_lab_diagnosis_import, name='api_lab_diagnosis_import_process'),

    
    # Investigation
    path('investigation/', InvestigationListView.as_view(), name='investigation_list'),
    path('investigation/<int:pk>/', InvestigationDetailView.as_view(), name='investigation_detail'),
    path('investigation/add/', InvestigationCreateView.as_view(), name='investigation_add'),
    path('investigation/<int:pk>/edit/', InvestigationUpdateView.as_view(), name='investigation_edit'),
    path('investigation/import/', InvestigationImportView.as_view(), name='investigation_import'),
    path('investigation/import/history/', InvestigationImportHistoryView.as_view(), name='investigation_import_history'),
    
    # Investigation Import APIs
    path('api/investigation/save/', api_investigation_save, name='api_investigation_save'),
    path('api/investigation/import/template/', api_investigation_download_template, name='api_investigation_import_template'),
    path('api/investigation/import/preview/', api_investigation_preview, name='api_investigation_import_preview'),
    path('api/investigation/import/process/', api_investigation_import, name='api_investigation_import_process'),
    
    # Parameter
    path('parameter/', ParameterListView.as_view(), name='parameter_list'),
    path('parameter/add/', ParameterCreateView.as_view(), name='parameter_add'),
    path('parameter/<int:pk>/edit/', ParameterUpdateView.as_view(), name='parameter_edit'),
    path('parameter/import/', ParameterImportView.as_view(), name='parameter_import'),
    path('parameter/import/history/', ParameterImportHistoryView.as_view(), name='parameter_import_history'),
    
    # Parameter Import APIs
    path('api/parameter/save/', api_parameter_save, name='api_parameter_save'),
    path('api/parameter/import/template/', api_parameter_download_template, name='api_parameter_import_template'),
    path('api/parameter/import/preview/', api_parameter_preview, name='api_parameter_import_preview'),
    path('api/parameter/import/process/', api_parameter_import, name='api_parameter_import_process'),
    
    # Age Group
    path('age-group/', AgeGroupListView.as_view(), name='agegroup_list'),
    path('age-group/add/', AgeGroupCreateView.as_view(), name='agegroup_add'),
    path('age-group/<int:pk>/edit/', AgeGroupUpdateView.as_view(), name='agegroup_edit'),
    path('age-group/import/', AgeGroupImportView.as_view(), name='agegroup_import'),
    path('age-group/import/history/', AgeGroupImportHistoryView.as_view(), name='agegroup_import_history'),
    
    # Age Group Import APIs
    path('api/age-group/search/', api_agegroup_search, name='api_agegroup_search'),
    path('api/age-group/import/template/', api_agegroup_download_template, name='api_agegroup_import_template'),
    path('api/age-group/import/preview/', api_agegroup_preview, name='api_agegroup_import_preview'),
    path('api/age-group/import/process/', api_agegroup_import, name='api_agegroup_import_process'),
    
    # Diagnosis Investigation Mapping
    path('diagnosis-investigation-age-mapping/', diagnosis_investigation_mapping_view, name='diagnosis_investigation_age_mapping'),
    
    # Reference Range Grid & Lookups
    path('reference-range/', ReferenceRangeGridView.as_view(), name='reference_range_grid'),
    path('investigation-parameter-mapping/', InvestigationParameterMappingView.as_view(), name='investigation_parameter_mapping'),
    path('api/investigation-parameters/', get_investigation_parameters, name='api_investigation_parameters'),
    path('api/investigation-parameters/all/', get_all_parameters, name='api_get_all_parameters'),
    path('api/investigation-parameters/save/', save_investigation_parameters, name='api_save_investigation_parameters'),
    path('api/parameters/add/', api_add_parameter, name='api_add_parameter'),
    path('api/reference-ranges/', get_reference_ranges, name='api_reference_ranges'),
    path('api/reference-ranges-bulk/', get_reference_ranges_bulk, name='api_reference_ranges_bulk'),
    path('api/reference-ranges-all/', get_reference_ranges_all, name='api_reference_ranges_all'),
    path('api/reference-ranges/save/', save_reference_range, name='api_reference_ranges_save'),
    path('api/reference-ranges/save-multiple/', save_multiple_reference_ranges, name='api_reference_ranges_save_multiple'),
    path('api/reference-ranges/<int:pk>/delete/', delete_reference_range, name='api_reference_ranges_delete'),
    path('api/reference-ranges-grid/list/', api_reference_ranges_grid_list, name='api_reference_ranges_grid_list'),
    path('api/reference-ranges-grid/detail/', api_reference_ranges_grid_detail, name='api_reference_ranges_grid_detail'),
    path('api/reference-ranges-grid/save/', api_reference_ranges_grid_save, name='api_reference_ranges_grid_save'),
    path('api/reference-ranges-grid/delete/', api_reference_ranges_grid_delete, name='api_reference_ranges_grid_delete'),

    # Diagnosis Investigation Mapping APIs
    path('api/diagnosis-investigation-map/list/', api_diagnosis_investigation_map_list, name='api_diagnosis_investigation_map_list'),
    path('api/diagnosis-investigation-map/detail/', api_diagnosis_investigation_map_detail, name='api_diagnosis_investigation_map_detail'),
    path('api/diagnosis-investigation-map/save/', api_diagnosis_investigation_map_save, name='api_diagnosis_investigation_map_save'),
    path('api/diagnosis-investigation-map/delete/', api_diagnosis_investigation_map_delete, name='api_diagnosis_investigation_map_delete'),
    
    path('reference-range/import/', ReferenceRangeImportView.as_view(), name='reference_range_import'),
    path('reference-range/import/history/', ReferenceRangeImportHistoryView.as_view(), name='reference_range_import_history'),
    path('api/reference-range/import/template/', api_referencerange_download_template, name='api_referencerange_import_template'),
    path('api/reference-range/import/preview/', api_referencerange_preview, name='api_referencerange_preview'),
    path('api/reference-range/import/save/', api_referencerange_import, name='api_referencerange_import'),

    # Diagnosis–Investigation Map Import (smart, name-based)
    path('diagnosis-investigation-age-mapping/import/', DiagnosisInvestigationMapImportView.as_view(), name='diagnosis_investigation_map_import'),
    path('api/diagnosis-investigation-map/import/template/', api_diag_inv_map_download_template, name='api_diag_inv_map_import_template'),
    path('api/diagnosis-investigation-map/import/preview/', api_diag_inv_map_preview, name='api_diag_inv_map_import_preview'),
    path('api/diagnosis-investigation-map/import/process/', api_diag_inv_map_import, name='api_diag_inv_map_import_process'),
    # Smart (name-based) variants
    path('api/diagnosis-investigation-map/smart-preview/', api_diag_inv_smart_preview, name='api_diag_inv_smart_preview'),
    path('api/diagnosis-investigation-map/smart-import/', api_diag_inv_smart_import, name='api_diag_inv_smart_import'),

    # Diagnosis-Department Mapping
    path('diagnosis-department-mapping/', diagnosis_department_mapping_view, name='diagnosis_department_mapping'),
    path('api/diagnosis-department-mapping/list/', api_diagnosis_department_map_list, name='api_diagnosis_department_map_list'),
    path('api/diagnosis-department-mapping/save/', api_diagnosis_department_map_save, name='api_diagnosis_department_map_save'),
    path('api/diagnosis-department-mapping/delete/', api_diagnosis_department_map_delete, name='api_diagnosis_department_map_delete'),
    path('api/diagnosis-department-mapping/unmapped/', api_diagnosis_department_map_unmapped_diagnoses, name='api_diagnosis_department_map_unmapped_diagnoses'),
    path('api/diagnosis-department-mapping/mapped/', api_diagnosis_department_map_mapped_diagnoses, name='api_diagnosis_department_map_mapped_diagnoses'),
    # Old import endpoints (kept for backward compat)
    path('api/diagnosis-department-mapping/import/template/', api_diag_dept_map_download_template, name='api_diag_dept_map_import_template'),
    path('api/diagnosis-department-mapping/import/preview/', api_diag_dept_map_preview, name='api_diag_dept_map_preview'),
    path('api/diagnosis-department-mapping/import/process/', api_diag_dept_map_import, name='api_diag_dept_map_import'),
    # Smart import page + APIs
    path('diagnosis-department-mapping/import/', DiagnosisDeptMappingImportView.as_view(), name='diagnosis_department_mapping_import'),
    path('api/diagnosis-department-mapping/smart-template/', api_diag_dept_smart_download_template, name='api_diag_dept_smart_template'),
    path('api/diagnosis-department-mapping/smart-preview/', api_diag_dept_smart_preview, name='api_diag_dept_smart_preview'),
    path('api/diagnosis-department-mapping/smart-import/', api_diag_dept_smart_import, name='api_diag_dept_smart_import'),

    # Investigation-Parameter Mapping Import
    path('investigation-parameter-mapping/import/', InvestigationParameterMappingImportView.as_view(), name='investigation_parameter_mapping_import'),
    path('api/investigation-parameter-mapping/import/template/', api_inv_param_map_download_template, name='api_inv_param_map_import_template'),
    path('api/investigation-parameter-mapping/import/preview/', api_inv_param_map_preview, name='api_inv_param_map_import_preview'),
    path('api/investigation-parameter-mapping/import/process/', api_inv_param_map_import, name='api_inv_param_map_import_process'),


    path('api/departments/add/', api_add_department, name='api_department_add'),
    path('api/sample-types/add/', api_add_sample_type, name='api_sample_type_add'),

    path('legacy-mapping/', LegacyMappingView.as_view(), name='legacy_mapping'),
    path('api/legacy-mapping/process/', process_legacy_mapping, name='api_legacy_mapping_process'),
    
    # Lab Master
    path('lab-master/dashboard/', lab_master_dashboard, name='lab_master_dashboard'),
    path('lab-master/sub-departments/', LabDepartmentListView.as_view(), name='lab_sub_departments'),
    path('lab-master/workload-mapping/', LabWorkloadMappingListView.as_view(), name='workload_mapping_list'),
    path('lab-master/mapping-validation/', UnmappedLabInvestigationListView.as_view(), name='mapping_validation'),
    path('lab-master/export/', export_lab_workload_csv, name='export_lab_workload_csv'),
    path('lab-master/import/', import_lab_workload_csv, name='import_lab_workload_csv'),
    
    # Lab Reports
    path('lab-reports/workload/', lab_workload_dashboard, name='lab_workload_dashboard'),
    path('lab-reports/dashboard/', report_dashboard, name='report_dashboard'),
    path('lab-reports/daily/', report_daily, name='report_daily'),
    path('lab-reports/monthly/', report_monthly, name='report_monthly'),
    path('lab-reports/sub-department/', report_sub_department, name='report_sub_department'),
    path('lab-reports/investigation/', report_investigation, name='report_investigation'),
    path('lab-reports/hospital-department/', report_hospital_department, name='report_hospital_department'),
    path('lab-reports/benchmark/', report_benchmark, name='report_benchmark'),
    path('lab-reports/abnormal/', report_abnormal, name='report_abnormal'),

    # Transactions
    path('order/add/', OrderEntryView.as_view(), name='order_entry'),
    path('result/', ResultEntryListView.as_view(), name='result_entry_list'),
    path('result/<int:pk>/', ResultEntryDetailView.as_view(), name='result_entry_detail'),
    path('work-orders/', WorkOrdersView.as_view(), name='work_orders'),
    path('work-orders/<int:pk>/', WorkOrderDetailView.as_view(), name='work_order_detail'),
    path('work-orders/result/<int:pk>/', WorkOrderResultEntryView.as_view(), name='work_order_result_entry'),
    path('work-orders/print-preview/<int:pk>/', WorkOrderPrintPreviewView.as_view(), name='work_order_print_preview'),
    path('work-orders/print/<int:pk>/', WorkOrderPrintPreviewView.as_view(), name='work_order_print'),
    path('api/work-orders/list/', api_work_orders_list, name='api_work_orders_list'),
    path('api/work-orders/<int:pk>/receive/', api_work_order_receive, name='api_work_order_receive'),
    path('api/work-orders/receive-multiple/', api_work_order_receive_multiple, name='api_work_order_receive_multiple'),
    path('api/work-orders/<int:pk>/save-result/', api_work_order_save_result, name='api_work_order_save_result'),
    path('api/work-orders/investigation/<int:pk>/params/', api_work_order_investigation_params, name='api_work_order_investigation_params'),
    
    # Service Request
    path('service-request/list/', ServiceRequestListView.as_view(), name='service_request_list'),
    path('service-request/', ServiceRequestCreateView.as_view(), name='service_request_add'),
    path('api/service-request/patients/', api_get_patients_for_request, name='api_get_patients_for_request'),
    path('api/service-request/diagnoses/', api_search_diagnosis, name='api_search_diagnosis'),
    path('api/service-request/suggest-investigations/', api_suggest_investigations, name='api_suggest_investigations'),
    path('api/service-request/search-investigations/', api_search_investigation, name='api_search_investigation'),
    path('api/service-request/<int:pk>/allocate/', api_allocate_service_request, name='api_allocate_service_request'),
    path('api/service-request/save-and-trigger/', api_save_and_trigger, name='api_save_and_trigger'),
    
    # Doctor Window
    path('doctor-window/', DoctorWindowView.as_view(), name='doctor_window'),
    path('api/doctor-window/patients/', api_doctor_window_patients, name='api_doctor_window_patients'),
    path('api/doctor-window/diagnosis/get/', api_doctor_window_get_diagnosis, name='api_doctor_window_get_diagnosis'),
    path('api/doctor-window/diagnosis/save/', api_doctor_window_save_diagnosis, name='api_doctor_window_save_diagnosis'),
    
    # Counts
    path('api/diagnoses/count/', api_diagnosis_count, name='api_diagnosis_count'),
    path('api/investigations/count/', api_investigation_count, name='api_investigation_count'),
    path('api/investigation-parameters/count/', api_parameter_count, name='api_parameter_count'),

    # Auto Trigger
    path('auto-trigger/configuration/', AutoTriggerConfigurationView.as_view(), name='auto_trigger_configuration'),
    path('auto-trigger/time-settings/', AutoTriggerConfigurationView.as_view(), name='auto_trigger_time_settings'),
    path('auto-trigger/history/', AutoTriggerHistoryView.as_view(), name='auto_trigger_history'),
    path('auto-trigger/monthly/', AutoTriggerMonthlyView.as_view(), name='auto_trigger_monthly'),
    path('auto-trigger/monthly/create/', AutoTriggerMonthlyCreateView.as_view(), name='auto_trigger_monthly_create'),
    path('auto-trigger/monthly/census/', AutoTriggerMonthlyCensusView.as_view(), name='auto_trigger_monthly_census'),
    path('auto-trigger/monthly/reviews/', AutoTriggerMonthlyReviewsView.as_view(), name='auto_trigger_monthly_reviews'),
    path('auto-trigger/monthly/execution/<int:plan_id>/<str:date_str>/', AutoTriggerMonthlyExecutionView.as_view(), name='auto_trigger_monthly_execution'),
    
    path('api/auto-trigger/save/', api_save_auto_trigger_config, name='api_save_auto_trigger_config'),
    path('api/auto-trigger/list/', api_get_auto_trigger_configs, name='api_get_auto_trigger_configs'),
    path('api/auto-trigger/execute/', api_execute_auto_trigger, name='api_execute_auto_trigger'),
    path('api/auto-trigger/status/<str:pk>/', api_get_auto_trigger_status, name='api_auto_trigger_status'),
    path('api/auto-trigger/active-run/', api_get_active_auto_trigger_run, name='api_auto_trigger_active_run'),
    path('api/auto-trigger/history/', api_get_auto_trigger_history, name='api_get_auto_trigger_history'),
    path('api/auto-trigger/history/<int:pk>/', api_get_auto_trigger_history_detail, name='api_get_auto_trigger_history_detail'),
    path('api/auto-trigger/config/<int:pk>/delete/', api_delete_auto_trigger_config, name='api_delete_auto_trigger_config'),
    path('api/auto-trigger/history/<int:pk>/retry/', api_retry_failed_entries, name='api_retry_failed_entries'),
    
    path('api/auto-trigger/monthly/get/', api_get_monthly_trigger, name='api_get_monthly_trigger'),
    path('api/auto-trigger/monthly/save/', api_save_monthly_trigger, name='api_save_monthly_trigger'),
    path('api/auto-trigger/monthly/save-v2/', api_save_monthly_trigger_v2, name='api_save_monthly_trigger_v2'),
    path('api/auto-trigger/monthly/stop/', api_stop_monthly_automation, name='api_stop_monthly_automation'),
    path('api/auto-trigger/monthly/stop-daily/', api_stop_daily_execution, name='api_stop_daily_execution'),
    path('api/auto-trigger/monthly/history/', api_get_monthly_history, name='api_get_monthly_history'),
    path('api/auto-trigger/monthly/created-patients/', api_get_daily_created_patients, name='api_get_daily_created_patients'),
    path('api/auto-trigger/monthly/reviews/', api_get_monthly_reviews, name='api_get_monthly_reviews'),
    
    path('api/auto-trigger/time-setting/save/', api_save_time_setting, name='api_save_time_setting'),
    path('api/auto-trigger/time-setting/list/', api_get_time_settings, name='api_get_time_settings'),
    path('api/auto-trigger/time-setting/<int:pk>/delete/', api_delete_time_setting, name='api_delete_time_setting'),
    
    path('auto-trigger/automate-test/', AutoTriggerAutomateTestView.as_view(), name='auto_trigger_automate_test'),
    path('auto-trigger/result-view/', AutoTriggerResultView.as_view(), name='auto_trigger_result_view'),
    path('api/auto-trigger/automate-test/parameters/', api_get_investigation_parameters, name='api_get_investigation_parameters'),
    path('api/auto-trigger/automate-test/generate-values/', api_generate_dummy_result_values, name='api_generate_dummy_result_values'),
    path('api/auto-trigger/automate-test/save/', api_save_dummy_result, name='api_save_dummy_result'),
    path('api/auto-trigger/result-view/list/', api_get_dummy_results, name='api_get_dummy_results'),
    path('api/auto-trigger/result-view/import-export/', api_result_import_export, name='api_result_import_export'),
    
    # ATC (Auto Trigger Control) Module
    path('auto-trigger/atc/', ATCControlView.as_view(), name='auto_trigger_atc'),
    path('auto-trigger/atc/status/', ATCLiveStatusView.as_view(), name='auto_trigger_atc_status'),
    path('auto-trigger/atc/settings/', ATCSettingsView.as_view(), name='auto_trigger_atc_settings'),
    path('api/atc/trigger/', api_atc_trigger, name='api_atc_trigger'),
    path('api/atc/preview/', api_atc_preview, name='api_atc_preview'),
    path('api/atc/save-config/', api_atc_save_config, name='api_atc_save_config'),
    path('api/atc/status/<int:job_id>/', api_atc_status, name='api_atc_status'),
    path('api/atc/stop/<int:job_id>/', api_atc_stop, name='api_atc_stop'),
    path('api/atc/active/', api_atc_active_job, name='api_atc_active_job'),
    path('api/atc/date-statuses/', api_atc_date_statuses, name='api_atc_date_statuses'),

    # Investigation Marking Module (Under Auto Trigger)
    path('auto-trigger/investigation-marking/', investigation_marking_view, name='investigation_marking'),
    path('api/investigation-marking/load/', api_marking_load, name='api_marking_load'),
    path('api/investigation-marking/add-department/', api_marking_add_department, name='api_marking_add_department'),
    path('api/investigation-marking/remove-department/', api_marking_remove_department, name='api_marking_remove_department'),
    path('api/investigation-marking/save-config/', api_marking_save_configuration, name='api_marking_save_configuration'),
    path('api/investigation-marking/trigger/', api_marking_trigger, name='api_marking_trigger'),
    path('api/investigation-marking/clear/', api_marking_clear, name='api_marking_clear'),
]
