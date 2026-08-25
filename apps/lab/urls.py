from django.urls import path
from .views import (
    DiagnosisListView, DiagnosisCreateView, DiagnosisUpdateView,
    InvestigationListView, InvestigationCreateView, InvestigationUpdateView, InvestigationDetailView,
    ParameterListView, ParameterCreateView, ParameterUpdateView,
    AgeGroupListView, AgeGroupCreateView, AgeGroupUpdateView,
    ReferenceRangeGridView, get_investigation_parameters, get_reference_ranges, get_reference_ranges_bulk, get_reference_ranges_all, save_reference_range, save_multiple_reference_ranges, delete_reference_range,
    InvestigationParameterMappingView, get_all_parameters, save_investigation_parameters, api_add_parameter,
    api_add_department, api_add_sample_type,
    OrderEntryView, ResultEntryListView, ResultEntryDetailView,
    LegacyMappingView, process_legacy_mapping,
    api_diagnosis_count, api_investigation_count, api_parameter_count
)
from .import_views import (
    DiagnosisImportView, DiagnosisImportHistoryView,
    api_diagnosis_download_template, api_diagnosis_preview, api_diagnosis_import,
    InvestigationImportView, InvestigationImportHistoryView,
    api_investigation_download_template, api_investigation_preview, api_investigation_import,
    ParameterImportView, ParameterImportHistoryView,
    api_parameter_download_template, api_parameter_preview, api_parameter_import,
    ReferenceRangeImportView, ReferenceRangeImportHistoryView,
    api_referencerange_download_template, api_referencerange_preview, api_referencerange_import,
    AgeGroupImportView, AgeGroupImportHistoryView,
    api_agegroup_download_template, api_agegroup_preview, api_agegroup_import
)

app_name = 'lab'

urlpatterns = [
    # Diagnosis Master
    path('diagnosis/', DiagnosisListView.as_view(), name='diagnosis_list'),
    path('diagnosis/add/', DiagnosisCreateView.as_view(), name='diagnosis_add'),
    path('diagnosis/<int:pk>/edit/', DiagnosisUpdateView.as_view(), name='diagnosis_edit'),
    path('diagnosis/import/', DiagnosisImportView.as_view(), name='diagnosis_import'),
    path('diagnosis/import/history/', DiagnosisImportHistoryView.as_view(), name='diagnosis_import_history'),
    
    # Diagnosis Import APIs
    path('api/diagnosis/import/template/', api_diagnosis_download_template, name='api_diagnosis_import_template'),
    path('api/diagnosis/import/preview/', api_diagnosis_preview, name='api_diagnosis_import_preview'),
    path('api/diagnosis/import/process/', api_diagnosis_import, name='api_diagnosis_import_process'),
    
    # Investigation
    path('investigation/', InvestigationListView.as_view(), name='investigation_list'),
    path('investigation/<int:pk>/', InvestigationDetailView.as_view(), name='investigation_detail'),
    path('investigation/add/', InvestigationCreateView.as_view(), name='investigation_add'),
    path('investigation/<int:pk>/edit/', InvestigationUpdateView.as_view(), name='investigation_edit'),
    path('investigation/import/', InvestigationImportView.as_view(), name='investigation_import'),
    path('investigation/import/history/', InvestigationImportHistoryView.as_view(), name='investigation_import_history'),
    
    # Investigation Import APIs
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
    path('api/age-group/import/template/', api_agegroup_download_template, name='api_agegroup_import_template'),
    path('api/age-group/import/preview/', api_agegroup_preview, name='api_agegroup_import_preview'),
    path('api/age-group/import/process/', api_agegroup_import, name='api_agegroup_import_process'),
    
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
    
    path('reference-range/import/', ReferenceRangeImportView.as_view(), name='reference_range_import'),
    path('reference-range/import/history/', ReferenceRangeImportHistoryView.as_view(), name='reference_range_import_history'),
    path('api/reference-range/import/template/', api_referencerange_download_template, name='api_referencerange_import_template'),
    path('api/reference-range/import/preview/', api_referencerange_preview, name='api_referencerange_preview'),
    path('api/reference-range/import/save/', api_referencerange_import, name='api_referencerange_import'),

    path('api/departments/add/', api_add_department, name='api_department_add'),
    path('api/sample-types/add/', api_add_sample_type, name='api_sample_type_add'),
    
    # Legacy Mapping
    path('legacy-mapping/', LegacyMappingView.as_view(), name='legacy_mapping'),
    path('api/legacy-mapping/process/', process_legacy_mapping, name='api_legacy_mapping_process'),
    
    # Transactions
    path('order/add/', OrderEntryView.as_view(), name='order_entry'),
    path('result/', ResultEntryListView.as_view(), name='result_entry_list'),
    path('result/<int:pk>/', ResultEntryDetailView.as_view(), name='result_entry_detail'),
    
    # Counts
    path('api/diagnoses/count/', api_diagnosis_count, name='api_diagnosis_count'),
    path('api/investigations/count/', api_investigation_count, name='api_investigation_count'),
    path('api/investigation-parameters/count/', api_parameter_count, name='api_parameter_count'),
]
