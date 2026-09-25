from django.urls import path
from .views import (
    DashboardView,
    CRMView,
    CRMExportView,
    AdmissionRequestView,
    AdmissionRequestExportView,
    PatientSearchAPIView,
    RegistrationSearchView,
    PatientCountView,
    PatientCountExportView,
    OPIPCensusView,
    ABHASearchView,
    ABHAExportView,
    PatientTypeView,
    PatientTypeExportView,
    UserLogView,
    UserLogExportView,
)

app_name = 'core'

urlpatterns = [
    # Front Office Landing Dashboard
    path('', DashboardView.as_view(), name='dashboard'),

    # 1. CRM
    path('crm/', CRMView.as_view(), name='crm'),
    path('crm/export/', CRMExportView.as_view(), name='crm_export'),

    # 2. Admission Request
    path('admission-request/', AdmissionRequestView.as_view(), name='admission_request'),
    path('admission-request/export/', AdmissionRequestExportView.as_view(), name='admission_request_export'),
    path('api/patient-search/', PatientSearchAPIView.as_view(), name='api_patient_search'),

    # 3. Registration Search
    path('registration-search/', RegistrationSearchView.as_view(), name='registration_search'),

    # 4. Patient Count
    path('patient-count/', PatientCountView.as_view(), name='patient_count'),
    path('patient-count/export/', PatientCountExportView.as_view(), name='patient_count_export'),

    # 5. OP-IP Census
    path('op-ip-census/', OPIPCensusView.as_view(), name='op_ip_census'),

    # 6. ABHA Search
    path('abha-search/', ABHASearchView.as_view(), name='abha_search'),
    path('abha-search/export/', ABHAExportView.as_view(), name='abha_search_export'),

    # 7. Patient Type
    path('patient-type/', PatientTypeView.as_view(), name='patient_type'),
    path('patient-type/export/', PatientTypeExportView.as_view(), name='patient_type_export'),

    # 8. User Log
    path('user-log/', UserLogView.as_view(), name='user_log'),
    path('user-log/export/', UserLogExportView.as_view(), name='user_log_export'),
]
