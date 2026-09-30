import uuid
from typing import Dict, Any, Optional
import logging
from django.conf import settings
from apps.printing.models import PublicPrintToken, PrintJob
from apps.printing.adapters.base import BasePrinterAdapter
from apps.printing.adapters.mock_printer import MockPrinterAdapter
from apps.printing.adapters.generic_printer import GenericPrinterAdapter
from apps.printing.adapters.prn_printer import PRNPrinterAdapter
from apps.printing.adapters.network_printer import NetworkPrinterAdapter
from apps.printing.services.sticker_renderer import StickerRenderer

logger = logging.getLogger(__name__)


class StickerPrintService:
    """
    Core printer service layer. Coordinates sticker rendering, print job creation,
    and routing to the configured printer adapter.
    """

    ADAPTER_MAP = {
        'mock': MockPrinterAdapter,
        'generic': GenericPrinterAdapter,
        'prn': PRNPrinterAdapter,
        'network': NetworkPrinterAdapter,
    }

    def __init__(self, printer_type: Optional[str] = None):
        self.printer_type = (printer_type or getattr(settings, 'STICKER_PRINTER_TYPE', 'mock')).lower()
        self.renderer = StickerRenderer()

    def get_adapter(self, printer_type: Optional[str] = None) -> BasePrinterAdapter:
        p_type = (printer_type or self.printer_type).lower()
        adapter_cls = self.ADAPTER_MAP.get(p_type, MockPrinterAdapter)
        
        config = {
            'name': getattr(settings, 'STICKER_PRINTER_NAME', 'TVS_Sticker_Printer'),
            'host': getattr(settings, 'STICKER_PRINTER_HOST', '127.0.0.1'),
            'port': getattr(settings, 'STICKER_PRINTER_PORT', 9100),
            'spool_dir': getattr(settings, 'STICKER_PRINTER_SPOOL_DIR', None),
            'device_path': getattr(settings, 'STICKER_PRINTER_DEVICE_PATH', None),
        }
        return adapter_cls(config=config)

    def print_sticker(self, token_obj: PublicPrintToken, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for printing a thermal sticker from a secure token.
        1. Formats patient/visit data
        2. Renders PRN payload
        3. Creates a database PrintJob audit record
        4. Transmits payload to the configured printer adapter
        """
        options = options or {}
        adapter = self.get_adapter(options.get('printer_type'))
        
        sticker_data = self.renderer.extract_sticker_data(token_obj)
        prn_payload = self.renderer.render_prn(sticker_data)
        
        job_id = f"PJ-{uuid.uuid4().hex[:12].upper()}"

        print_job = PrintJob.objects.create(
            job_id=job_id,
            token=token_obj,
            patient=token_obj.patient,
            print_type=token_obj.print_type,
            printer_name=adapter.config.get('name', 'Sticker_Printer'),
            printer_type=self.printer_type,
            status=PrintJob.StatusChoices.PENDING,
            raw_payload=prn_payload,
        )

        try:
            result = adapter.print_sticker(prn_payload, job_id=job_id, options=options)
            
            # Map status to choices
            res_status = result.get('status', 'SENT')
            if res_status == 'PRINTED':
                print_job.status = PrintJob.StatusChoices.PRINTED
            elif res_status == 'SENT':
                print_job.status = PrintJob.StatusChoices.SENT
            else:
                print_job.status = PrintJob.StatusChoices.FAILED
                print_job.error_message = result.get('message', 'Unknown failure')
                
            print_job.save(update_fields=['status', 'error_message', 'updated_at'])
            result['job_id'] = job_id
            return result

        except Exception as e:
            logger.error(f"[StickerPrintService] Exception executing print job {job_id}: {e}")
            print_job.status = PrintJob.StatusChoices.FAILED
            print_job.error_message = str(e)
            print_job.save(update_fields=['status', 'error_message', 'updated_at'])
            return {
                'success': False,
                'status': 'FAILED',
                'message': str(e),
                'job_id': job_id,
            }
