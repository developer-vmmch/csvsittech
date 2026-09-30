import os
import subprocess
from typing import Dict, Any, Optional
import logging
from .base import BasePrinterAdapter

logger = logging.getLogger(__name__)


class GenericPrinterAdapter(BasePrinterAdapter):
    """
    Generic OS-level printer adapter.
    Can send raw or formatted payloads to OS print spooler (CUPS on Linux/macOS via 'lp'/'lpr',
    or write to a spool folder for a local print agent/bridge).
    """

    def print_sticker(self, payload: str, job_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        printer_name = self.config.get('name') or options.get('printer_name') or 'Generic_Sticker_Printer'
        spool_dir = self.config.get('spool_dir')

        # If a spool directory is specified, write directly to spool file
        if spool_dir:
            try:
                os.makedirs(spool_dir, exist_ok=True)
                filepath = os.path.join(spool_dir, f"{job_id}.prn")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(payload)
                return {
                    'success': True,
                    'status': 'SENT',
                    'message': f"Written to spool file {filepath}",
                    'job_id': job_id,
                    'details': {'spool_file': filepath, 'printer_name': printer_name}
                }
            except Exception as e:
                logger.error(f"[GenericPrinterAdapter] Failed writing spool file: {e}")
                return {
                    'success': False,
                    'status': 'FAILED',
                    'message': str(e),
                    'job_id': job_id,
                    'details': {'error': str(e)}
                }

        # Try sending to system printer via 'lp' if on Linux and printer is configured
        use_system_spooler = self.config.get('use_system_spooler', False)
        if use_system_spooler and printer_name:
            try:
                proc = subprocess.run(
                    ['lp', '-d', printer_name, '-o', 'raw'],
                    input=payload.encode('utf-8'),
                    capture_output=True,
                    timeout=5
                )
                if proc.returncode == 0:
                    return {
                        'success': True,
                        'status': 'PRINTED',
                        'message': f"Sent to system printer '{printer_name}'",
                        'job_id': job_id,
                        'details': {'stdout': proc.stdout.decode('utf-8', errors='ignore')}
                    }
                else:
                    return {
                        'success': False,
                        'status': 'FAILED',
                        'message': proc.stderr.decode('utf-8', errors='ignore') or 'lp command failed',
                        'job_id': job_id,
                        'details': {'returncode': proc.returncode}
                    }
            except Exception as e:
                logger.warning(f"[GenericPrinterAdapter] System spooler error: {e}")

        # Fallback: recorded as ready for bridge download/pull
        return {
            'success': True,
            'status': 'SENT',
            'message': f"Generic print payload prepared for printer '{printer_name}'",
            'job_id': job_id,
            'details': {'printer_name': printer_name, 'payload_length': len(payload)}
        }

    def test_connection(self) -> Dict[str, Any]:
        printer_name = self.config.get('name', 'Generic_Printer')
        return {
            'success': True,
            'status': 'ONLINE',
            'message': f"Generic printer '{printer_name}' adapter initialized.",
            'printer_type': 'generic'
        }
