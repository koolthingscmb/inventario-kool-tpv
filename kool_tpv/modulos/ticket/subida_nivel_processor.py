from __future__ import annotations
from kool_tpv.modulos.ticket.base_processor import TicketProcessor


class SubidaNivelProcessor(TicketProcessor):
    def process(self, **kwargs):
        cliente_id = kwargs.get('cliente_id')
        if cliente_id:
            self.fidel_repo.recalcular_nivel_cliente(cliente_id)
        return None
