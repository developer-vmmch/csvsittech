from typing import Dict, Any, Optional
import logging
from .base import BasePrinterAdapter

logger = logging.getLogger(__name__)


class MockPrinterAdapter(BasePrinterAdapter):
    """
    Test and mock printer adapter. Stores sent print jobs in memory / log
    for test validation and environments without physical hardware.
    """
    printed_jobs = []

    def print_sticker(self, payload: str, job_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        entry = {
            'job_id': job_id,
            'payload': payload,
            'options': options,
            'printer_name': self.config.get('name', 'Mock_Thermal_Printer'),
            'status': 'PRINTED'
        }
        self.printed_jobs.append(entry)
        logger.info(f"[MockPrinterAdapter] Successfully processed print job {job_id} ({len(payload)} chars).")
        return {
            'success': True,
            'status': 'PRINTED',
            'message': f"Mock printer received job {job_id}",
            'job_id': job_id,
            'details': {
                'printer_name': entry['printer_name'],
                'payload_size_bytes': len(payload.encode('utf-8')),
                'payload_preview': payload[:120] + ('...' if len(payload) > 120 else ''),
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        return {
            'success': True,
            'status': 'ONLINE',
            'message': 'Mock printer is ready and accepting print jobs.',
            'printer_type': 'mock'
        }

    @classmethod
    def clear(cls):
        cls.printed_jobs.clear()
