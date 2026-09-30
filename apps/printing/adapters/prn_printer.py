import os
import subprocess
from typing import Dict, Any, Optional
import logging
from .base import BasePrinterAdapter

logger = logging.getLogger(__name__)


class PRNPrinterAdapter(BasePrinterAdapter):
    """
    Direct PRN thermal printer adapter.
    Handles raw command payloads (such as TSPL, ESC/POS, or ZPL byte streams)
    suitable for TVS LP 46 Neo, TVS LP 44, Citizen, Zebra, and compatible thermal sticker printers.
    """

    def print_sticker(self, payload: str, job_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        device_path = self.config.get('device_path') or options.get('device_path')
        save_prn_path = self.config.get('save_prn_path') or options.get('save_prn_path')

        raw_bytes = payload.encode('utf-8')

        # 1. Option to save PRN file for inspection or external bridge
        if save_prn_path:
            try:
                os.makedirs(os.path.dirname(save_prn_path), exist_ok=True)
                with open(save_prn_path, 'wb') as f:
                    f.write(raw_bytes)
            except Exception as e:
                logger.error(f"[PRNPrinterAdapter] Error saving PRN file: {e}")

        # 2. If a local direct device path is specified (e.g. /dev/usb/lp0 or COM3)
        if device_path and os.path.exists(device_path):
            try:
                with open(device_path, 'wb') as dev:
                    dev.write(raw_bytes)
                return {
                    'success': True,
                    'status': 'PRINTED',
                    'message': f"PRN stream successfully sent to hardware device {device_path}",
                    'job_id': job_id,
                    'details': {'device': device_path, 'bytes_written': len(raw_bytes)}
                }
            except Exception as e:
                logger.error(f"[PRNPrinterAdapter] Direct device write failed: {e}")
                return {
                    'success': False,
                    'status': 'FAILED',
                    'message': f"Device write error: {str(e)}",
                    'job_id': job_id,
                    'details': {'device': device_path, 'error': str(e)}
                }

        # 3. Default: PRN payload successfully formulated and staged for local workstation bridge
        return {
            'success': True,
            'status': 'SENT',
            'message': f"PRN payload generated ({len(raw_bytes)} bytes) and ready for printer",
            'job_id': job_id,
            'details': {
                'format': 'PRN_TSPL',
                'bytes': len(raw_bytes),
                'device_path': device_path or 'Workstation Bridge',
            }
        }

    def test_connection(self) -> Dict[str, Any]:
        device_path = self.config.get('device_path')
        is_ready = bool(device_path and os.path.exists(device_path))
        return {
            'success': True,
            'status': 'ONLINE' if is_ready else 'CONFIGURED',
            'message': f"PRN Adapter ready. Target device: {device_path or 'Virtual/Bridge'}",
            'printer_type': 'prn'
        }
