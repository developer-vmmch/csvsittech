from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BasePrinterAdapter(ABC):
    """
    Abstract base class for all physical and virtual sticker printer adapters.
    Isolates printer-specific protocols (PRN, TSPL, ESC/POS, ZPL, Windows Spooler, CUPS, Network socket)
    from core patient, OP, and Review business logic.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def print_sticker(self, payload: str, job_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends the rendered sticker payload to the destination printer.
        Returns a dict:
        {
            'success': bool,
            'status': str ('SENT', 'PRINTED', 'FAILED'),
            'message': str,
            'job_id': str,
            'details': dict
        }
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Checks whether the printer or bridge endpoint is reachable.
        """
        pass
