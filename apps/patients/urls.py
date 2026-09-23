from django.urls import path
from .views import (
    PatientListView, PatientSearchView, PatientCreateView, PatientUpdateView, PatientPrintView, PatientDeleteView,
    PatientCompanyListView, PatientCompanyCreateView, PatientCompanyDeleteView,
    DepartmentListView, DepartmentCreateView, DepartmentUpdateView, DepartmentDeleteView,
    DepartmentUnitCreateView, DepartmentUnitUpdateView, DepartmentUnitDeleteView,
    WardListView, WardCreateView, WardUpdateView, WardDeleteView, WardAllocationView,
    get_department_units, OPCensusView, PatientReviewView, PatientReviewReportView, PatientMedicalHistoryPrintView,
    PatientDischargeView, PatientDischargeSlipView, BranchTransferListView, api_patient_active_admission,
    BranchTransferReportView, export_branch_transfers_csv, api_search_patient_for_allocation, api_available_ward_beds,
    WardServiceRequestView, api_ward_service_request_patients, api_patient_investigations_results
)
from .import_views import (
    PatientImportView, PatientImportHistoryView, api_patient_download_template,
    api_patient_preview, api_patient_import, api_patient_import_status
)

app_name = 'patients'

urlpatterns = [
    path('', PatientListView.as_view(), name='list'),
    path('review/', PatientReviewView.as_view(), name='review'),
    path('discharge/', PatientDischargeView.as_view(), name='discharge'),
    path('discharge/<int:pk>/slip/', PatientDischargeSlipView.as_view(), name='discharge_slip'),
    path('ward/allocation/', WardAllocationView.as_view(), name='ward_allocation'),
    path('ward/allocation/api/search-patient/', api_search_patient_for_allocation, name='api_search_patient_allocation'),
    path('ward/allocation/api/available-beds/', api_available_ward_beds, name='api_available_ward_beds'),
    path('ward/allocation/api/patient-investigations/', api_patient_investigations_results, name='api_patient_investigations_results'),
    path('ward/service-request/', WardServiceRequestView.as_view(), name='ward_service_request'),
    path('ward/service-request/api/patients/', api_ward_service_request_patients, name='api_ward_service_request_patients'),
    path('ward/branch-transfer/', BranchTransferListView.as_view(), name='branch_transfer'),
    path('ward/branch-transfer/report/', BranchTransferReportView.as_view(), name='branch_transfer_report'),
    path('ward/branch-transfer/report/export/', export_branch_transfers_csv, name='branch_transfer_report_export'),
    path('ward/branch-transfer/api/patient-info/', api_patient_active_admission, name='api_branch_transfer_patient_info'),
    path('review/report/', PatientReviewReportView.as_view(), name='review_report'),
    path('op-census/', OPCensusView.as_view(), name='op_census'),
    path('search/', PatientSearchView.as_view(), name='search'),
    path('add/', PatientCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', PatientUpdateView.as_view(), name='edit'),
    path('<int:pk>/print/', PatientPrintView.as_view(), name='print'),
    path('<int:pk>/history/print/', PatientMedicalHistoryPrintView.as_view(), name='medical_history_print'),
    path('<int:pk>/delete/', PatientDeleteView.as_view(), name='delete'),
    
    path('companies/', PatientCompanyListView.as_view(), name='company_list'),
    path('companies/add/', PatientCompanyCreateView.as_view(), name='company_add'),
    path('companies/<int:pk>/delete/', PatientCompanyDeleteView.as_view(), name='company_delete'),
    
    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/add/', DepartmentCreateView.as_view(), name='department_add'),
    path('departments/<int:pk>/edit/', DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/delete/', DepartmentDeleteView.as_view(), name='department_delete'),

    path('wards/', WardListView.as_view(), name='ward_list'),
    path('wards/add/', WardCreateView.as_view(), name='ward_add'),
    path('wards/<int:pk>/edit/', WardUpdateView.as_view(), name='ward_edit'),
    path('wards/<int:pk>/delete/', WardDeleteView.as_view(), name='ward_delete'),
    
    path('units/add/', DepartmentUnitCreateView.as_view(), name='unit_add'),
    path('units/<int:pk>/edit/', DepartmentUnitUpdateView.as_view(), name='unit_edit'),
    path('units/<int:pk>/delete/', DepartmentUnitDeleteView.as_view(), name='unit_delete'),
    
    path('api/units/', get_department_units, name='api_units'),
    
    # Import endpoints
    path('import/', PatientImportView.as_view(), name='import'),
    path('import/history/', PatientImportHistoryView.as_view(), name='import_history'),
    path('api/import/template/', api_patient_download_template, name='api_import_template'),
    path('api/import/preview/', api_patient_preview, name='api_import_preview'),
    path('api/import/process/', api_patient_import, name='api_import_process'),
    path('api/import/status/', api_patient_import_status, name='api_import_status'),
]
