from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Booking
    path('booking/', views.booking_list, name='booking_list'),
    path('booking/create/', views.booking_create, name='booking_create'),
    path('booking/<int:pk>/', views.case_detail, name='case_detail'),
    path('booking/<int:pk>/preop/', views.preop_form, name='preop_form'),
    path('booking/<int:pk>/schedule/', views.schedule_form, name='schedule_form'),
    path('booking/<int:pk>/shift/', views.shift_to_ot, name='shift_to_ot'),
    path('booking/<int:pk>/signin/', views.sign_in, name='sign_in'),
    path('booking/<int:pk>/anesthesia/', views.anesthesia_form, name='anesthesia_form'),
    path('booking/<int:pk>/timeout/', views.time_out, name='time_out'),
    path('booking/<int:pk>/start-surgery/', views.start_surgery, name='start_surgery'),
    path('booking/<int:pk>/notes/', views.operation_notes, name='operation_notes'),
    path('booking/<int:pk>/signout/', views.sign_out, name='sign_out'),
    path('booking/<int:pk>/complete/', views.complete_surgery, name='complete_surgery'),
    path('booking/<int:pk>/outcome/', views.outcome_form, name='outcome_form'),
    path('booking/<int:pk>/disposition/', views.disposition_form, name='disposition_form'),
    path('booking/<int:pk>/postop/', views.postop_form, name='postop_form'),
    path('booking/<int:pk>/closure/', views.closure_form, name='closure_form'),
    path('booking/<int:pk>/cancel/', views.cancel_case, name='cancel_case'),

    # Schedule & Live
    path('schedule/', views.schedule_view, name='schedule'),
    path('live/', views.live_board, name='live'),

    # History & Master
    path('history/', views.history_list, name='history'),
    path('master/', views.master_index, name='master'),

    # JSON APIs
    path('api/patient-search/', views.api_patient_search, name='api_patient_search'),
    path('api/patient/<int:patient_pk>/admissions/', views.api_patient_ip_admissions, name='api_patient_admissions'),
    path('api/diagnosis-search/', views.api_diagnosis_search, name='api_diagnosis_search'),
    path('api/check-conflicts/', views.api_check_conflicts, name='api_check_conflicts'),
    path('api/live-status/', views.api_live_status, name='api_live_status'),
]
