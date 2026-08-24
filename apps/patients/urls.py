from django.urls import path
from .views import (
    PatientListView, PatientSearchView, PatientCreateView, PatientUpdateView, PatientPrintView, PatientDeleteView,
    PatientCompanyListView, PatientCompanyCreateView, PatientCompanyDeleteView,
    DepartmentListView, DepartmentCreateView, DepartmentDeleteView,
    DepartmentUnitCreateView, DepartmentUnitDeleteView,
    get_department_units, OPCensusView, PatientReviewView, PatientReviewReportView, PatientMedicalHistoryPrintView
)

app_name = 'patients'

urlpatterns = [
    path('', PatientListView.as_view(), name='list'),
    path('review/', PatientReviewView.as_view(), name='review'),
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
    path('departments/<int:pk>/delete/', DepartmentDeleteView.as_view(), name='department_delete'),
    
    path('units/add/', DepartmentUnitCreateView.as_view(), name='unit_add'),
    path('units/<int:pk>/delete/', DepartmentUnitDeleteView.as_view(), name='unit_delete'),
    
    path('api/units/', get_department_units, name='api_units'),
]
