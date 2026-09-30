import socket
from typing import Dict, Any, Optional
import logging
from .base import BasePrinterAdapter

logger = logging.getLogger(__name__)


class NetworkPrinterAdapter(BasePrinterAdapter):
    """
    Network TCP/IP raw socket printer adapter (Standard JetDirect / Port 9100).
    Allows sending thermal commands directly to networked TVS / TSC / Zebra printers.
    """

    def print_sticker(self, payload: str, job_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        host = self.config.get('host') or options.get('host') or '127.0.0.1'
        port = int(self.config.get('port') or options.get('port') or 9100)
        timeout = float(self.config.get('timeout', 5.0))

        raw_bytes = payload.encode('utf-8')
        try:
            with socket.create_connection((host, port), timeout=timeout) as s:
                s.sendall(raw_bytes)
            logger.info(f"[NetworkPrinterAdapter] Successfully sent {len(raw_bytes)} bytes to {host}:{port}")
            return {
                'success': True,
                'status': 'PRINTED',
                'message': f"Sent to network printer {host}:{port}",
                'job_id': job_id,
                'details': {'host': host, 'port': port, 'bytes_sent': len(raw_bytes)}
            }
        except Exception as e:
            logger.error(f"[NetworkPrinterAdapter] Connection to {host}:{port} failed: {e}")
            return {
                'success': False,
                'status': 'FAILED',
                'message': f"Network printer error: {str(e)}",
                'job_id': job_id,
                'details': {'host': host, 'port': port, 'error': str(e)}
            }

    def test_connection(self) -> Dict[str, Any]:
        host = self.config.get('host', '127.0.0.1')
        port = int(self.config.get('port', 9100))
        try:
            with socket.create_connection((host, port), timeout=2.0):
                return {
                    'success': True,
                    'status': 'ONLINE',
                    'message': f"Printer at {host}:{port} is reachable.",
                    'printer_type': 'network'
                }
        except Exception as e:
            return {
                'success': False,
                'status': 'OFFLINE',
                'message': f"Cannot connect to {host}:{port}: {e}",
                'printer_type': 'network'
            }
