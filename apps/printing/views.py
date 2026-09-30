import json
import logging
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, Http404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from apps.printing.models import PublicPrintToken, PrintJob
from apps.printing.services.sticker_renderer import StickerRenderer
from apps.printing.services.printer_service import StickerPrintService
from apps.printing.services.pdf_generator import PatientPdfGenerator

logger = logging.getLogger(__name__)


class PublicPrintView(View):
    """
    Public, unauthenticated endpoint for patients scanning OP/Review QR codes
    using mobile cameras (Android, iPhone, Google Lens).
    Presents ONLY the printable patient document without any HMS navigation or UI.
    """
    def get(self, request, token):
        token_obj = PublicPrintToken.objects.filter(
            token=token,
            is_active=True
        ).select_related('patient', 'visit').first()

        if not token_obj or not token_obj.is_valid:
            return render(
                request,
                'printing/token_error.html',
                {'error_message': 'This document link is invalid, expired, or has been revoked for patient data privacy.'},
                status=404
            )

        # Record public access for security/audit
        try:
            token_obj.record_access()
        except Exception as e:
            logger.warning(f"Error recording token access: {e}")

        # Check if caller explicitly requested raw PDF stream
        if request.GET.get('format', '').lower() == 'pdf':
            generator = PatientPdfGenerator(token_obj)
            pdf_bytes = generator.generate_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="VMMC_{token_obj.print_type}_{token_obj.patient.patient_id}.pdf"'
            return response

        patient = token_obj.patient
        visit = token_obj.visit
        display_date = visit.visit_date if (visit and visit.visit_date) else patient.created_at
        display_dept = (visit.department if (visit and visit.department) else patient.department) or "GENERAL MEDICINE"

        renderer = StickerRenderer()
        sticker_data = renderer.extract_sticker_data(token_obj)
        sticker_html = renderer.render_html(sticker_data)

        context = {
            'token_obj': token_obj,
            'patient': patient,
            'visit': visit,
            'display_date': display_date,
            'display_dept': display_dept,
            'public_url': token_obj.get_public_url(request),
            'pdf_download_url': reverse('printing:public_pdf', kwargs={'token': token_obj.token}),
            'sticker_data': sticker_data,
            'sticker_html': sticker_html,
            'sticker_renderer': renderer,
        }
        return render(request, 'printing/public_patient_print.html', context)


class PublicPdfDownloadView(View):
    """
    Direct application/pdf binary download and inline view endpoint.
    Used by browser PDF controls and mobile viewers.
    """
    def get(self, request, token):
        token_obj = PublicPrintToken.objects.filter(
            token=token,
            is_active=True
        ).select_related('patient', 'visit').first()

        if not token_obj or not token_obj.is_valid:
            return render(
                request,
                'printing/token_error.html',
                {'error_message': 'This document link is invalid or expired.'},
                status=404
            )

        try:
            token_obj.record_access()
        except Exception:
            pass

        generator = PatientPdfGenerator(token_obj)
        pdf_bytes = generator.generate_pdf()

        as_attachment = request.GET.get('download', '').lower() in ('1', 'true', 'yes')
        disposition = 'attachment' if as_attachment else 'inline'
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"VMMC_{token_obj.print_type}_{token_obj.patient.patient_id}.pdf"
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response


class PublicStickerPreviewView(View):
    """
    Thermal sticker preview endpoint (60mm x 30mm configurable).
    Provides visual verification, browser print, PRN download, and workstation dispatch.
    """
    def get(self, request, token):
        token_obj = PublicPrintToken.objects.filter(
            token=token,
            is_active=True
        ).select_related('patient', 'visit').first()

        if not token_obj or not token_obj.is_valid:
            return render(
                request,
                'printing/token_error.html',
                {'error_message': 'Sticker link is invalid or expired.'},
                status=404
            )

        renderer = StickerRenderer()
        sticker_data = renderer.extract_sticker_data(token_obj)
        sticker_html = renderer.render_html(sticker_data)
        prn_payload = renderer.render_prn(sticker_data)

        context = {
            'token_obj': token_obj,
            'sticker_data': sticker_data,
            'sticker_html': sticker_html,
            'prn_payload': prn_payload,
            'sticker_renderer': renderer,
        }
        return render(request, 'printing/public_sticker_preview.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class PublicWorkstationPrintTriggerView(View):
    """
    API endpoint invoked by dedicated QR scanners and workstation print bridges
    to automatically print a thermal sticker to the configured printer.
    """
    def post(self, request, token):
        return self._handle_print(request, token)

    def get(self, request, token):
        # Support GET triggers for simple barcode scanner browser links
        return self._handle_print(request, token)

    def _handle_print(self, request, token):
        token_obj = PublicPrintToken.objects.filter(
            token=token,
            is_active=True
        ).select_related('patient', 'visit').first()

        if not token_obj or not token_obj.is_valid:
            return JsonResponse({
                'success': False,
                'status': 'FAILED',
                'message': 'Invalid, expired, or inactive print token.'
            }, status=404)

        try:
            options = {}
            if request.method == 'POST' and request.body:
                try:
                    options = json.loads(request.body.decode('utf-8'))
                except Exception:
                    options = {}

            service = StickerPrintService()
            result = service.print_sticker(token_obj, options=options)

            result.update({
                'patient_name': token_obj.patient.name,
                'uhid': token_obj.patient.patient_id,
                'print_type': token_obj.print_type,
                'printer_name': getattr(settings, 'STICKER_PRINTER_NAME', 'Sticker_Printer'),
            })
            return JsonResponse(result)

        except Exception as e:
            logger.error(f"Error handling workstation print trigger for token {token}: {e}")
            return JsonResponse({
                'success': False,
                'status': 'FAILED',
                'message': str(e)
            }, status=500)


class PrintWorkstationScannerView(LoginRequiredMixin, TemplateView):
    """
    Hospital staff workstation UI for dedicated handheld QR/barcode scanners.
    Automatically catches scanned QR codes and transmits sticker print jobs to the printer.
    """
    template_name = 'printing/workstation_scanner.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['printer_name'] = getattr(settings, 'STICKER_PRINTER_NAME', 'TVS Thermal Printer')
        context['printer_type'] = getattr(settings, 'STICKER_PRINTER_TYPE', 'mock')
        context['sticker_width'] = getattr(settings, 'STICKER_PRINTER_WIDTH', '60mm')
        context['sticker_height'] = getattr(settings, 'STICKER_PRINTER_HEIGHT', '30mm')
        context['recent_jobs'] = PrintJob.objects.select_related('patient', 'token').order_by('-created_at')[:25]
        return context
