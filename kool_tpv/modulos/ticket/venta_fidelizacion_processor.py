from __future__ import annotations
from typing import Any
from decimal import Decimal
import logging

from kool_tpv.modulos.ticket.venta_processor import VentaProcessor

logger = logging.getLogger(__name__)


class VentaFidelizacionProcessor(VentaProcessor):
    def process(self, **kwargs):
        ticket_id = super().process(**kwargs)
        cliente_id = kwargs.get('cliente_id')
        puntos_otorgar_cents = kwargs.get('puntos_otorgar_cents')
        puntos_gastados_cents = kwargs.get('puntos_gastados_cents')
        puntos_restar_cents = kwargs.get('puntos_restar_cents', 0)
        if cliente_id:
            if puntos_otorgar_cents or puntos_gastados_cents or puntos_restar_cents:
                self.repo.insert_points_movement_raw(cliente_id, puntos_otorgar_cents - puntos_restar_cents - puntos_gastados_cents, 'ticket', ticket_id, None)
                self.fidel_repo.actualizar_cliente_loyalty(
                    cliente_id=cliente_id,
                    puntos_otorgar=Decimal(str(puntos_otorgar_cents / 100)) if puntos_otorgar_cents is not None else Decimal('0'),
                    puntos_restar=Decimal(str(puntos_restar_cents / 100)) if puntos_restar_cents is not None else Decimal('0'),
                    puntos_gastados=Decimal(str(puntos_gastados_cents / 100)) if puntos_gastados_cents is not None else Decimal('0'),
                    total_ticket=Decimal(str((kwargs.get('total_cents', 0)) / 100)),
                    unidades_vendidas=kwargs.get('total_unidades', 0),
                    fecha=(kwargs.get('created_at') or '').split(' ')[0]
                )
        return ticket_id
