from __future__ import annotations
from typing import Any

from kool_tpv.modulos.ticket.base_processor import TicketProcessor


class DescuentoProcessor(TicketProcessor):
    def process(self, **kwargs):
        ticket_id = kwargs.get('ticket_id')
        descuentos = kwargs.get('descuentos', [])
        for desc in descuentos:
            self.repo.insert_ticket_line(ticket_id, None, 'Descuento', 1, int(desc.get('precio_cents', 0)), desc.get('iva', 0), 'descuento', None)
        return ticket_id
