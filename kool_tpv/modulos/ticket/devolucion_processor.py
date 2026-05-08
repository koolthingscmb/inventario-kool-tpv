from __future__ import annotations
from kool_tpv.modulos.ticket.venta_processor import VentaProcessor


class DevolucionProcessor(VentaProcessor):
    def process(self, **kwargs):
        return super().process(**kwargs)
