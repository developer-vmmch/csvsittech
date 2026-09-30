from django.urls import path
from apps.printing.views import (
    PublicPrintView,
    PublicPdfDownloadView,
    PublicStickerPreviewView,
    PublicWorkstationPrintTriggerView,
    PrintWorkstationScannerView,
)

app_name = 'printing'

urlpatterns = [
    # Public Patient Endpoints (No Authentication Required, Privacy Protected)
    path('public/print/<str:token>/', PublicPrintView.as_view(), name='public_print'),
    path('public/pdf/<str:token>/', PublicPdfDownloadView.as_view(), name='public_pdf'),
    path('public/sticker/<str:token>/', PublicStickerPreviewView.as_view(), name='public_sticker'),
    path('public/api/print-sticker/<str:token>/', PublicWorkstationPrintTriggerView.as_view(), name='public_print_trigger'),

    # Hospital Staff Workstation Scanner Page
    path('printing/scanner/', PrintWorkstationScannerView.as_view(), name='workstation_scanner'),
]
