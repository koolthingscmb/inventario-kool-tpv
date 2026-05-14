"""Base TicketProcessor class."""
from __future__ import annotations
from typing import Any
import logging

from kool_tpv.modulos.ticket.ticket_repository import TicketRepository
from kool_tpv.modulos.fidelizacion.fidelizacion_repository import FidelizacionRepository
from kool_tpv.modulos.fidelizacion.fidelizacion_service import FidelizacionService

logger = logging.getLogger(__name__)


class TicketProcessor:
    """Base processor interface."""

    def __init__(self, db: Any):
        self.db = db
        self.repo = TicketRepository(db)
        self.fidel_repo = FidelizacionRepository(db)
        self.fidel_service = FidelizacionService(db)

    def process(self, **kwargs):
        raise NotImplementedError()
