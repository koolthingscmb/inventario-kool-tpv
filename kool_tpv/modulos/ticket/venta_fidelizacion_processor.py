from __future__ import annotations
from typing import Any
import logging

from kool_tpv.modulos.ticket.venta_processor import VentaProcessor

logger = logging.getLogger(__name__)


class VentaFidelizacionProcessor(VentaProcessor):
    def process(self, **kwargs):
        proc_res = super().process(**kwargs)
        if isinstance(proc_res, (tuple, list)):
            ticket_id = proc_res[0]
        else:
            ticket_id = proc_res
        cliente_id = kwargs.get('cliente_id')
        puntos_otorgar_cents = kwargs.get('puntos_otorgar_cents')
        puntos_gastados_cents = kwargs.get('puntos_gastados_cents')
        puntos_restar_cents = kwargs.get('puntos_restar_cents', 0)
        if cliente_id:
            if puntos_otorgar_cents or puntos_gastados_cents or puntos_restar_cents:
                if puntos_otorgar_cents > 0:
                    self.repo.insert_points_movement_raw(cliente_id, +puntos_otorgar_cents, 'compra', ticket_id, None)
                if puntos_gastados_cents > 0:
                    self.repo.insert_points_movement_raw(cliente_id, -puntos_gastados_cents, 'gasto', ticket_id, None)
                if puntos_restar_cents > 0:
                    self.repo.insert_points_movement_raw(cliente_id, -puntos_restar_cents, 'ajuste', ticket_id, None)
                self.fidel_repo.actualizar_loyalty_y_recalcular_nivel(
                    cliente_id=cliente_id,
                    puntos_otorgar_cents=puntos_otorgar_cents or 0,
                    puntos_restar_cents=puntos_restar_cents or 0,
                    puntos_gastados_cents=puntos_gastados_cents or 0,
                    total_ticket_cents=kwargs.get('total_cents', 0),
                    unidades_vendidas=kwargs.get('total_unidades', 0),
                    fecha=(kwargs.get('created_at') or '').split(' ')[0]
                )
        return ticket_id
