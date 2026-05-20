from __future__ import annotations
from typing import Dict, List
import logging

from kool_tpv.modulos.ticket.venta_processor import VentaProcessor

logger = logging.getLogger(__name__)


class DevolucionProcessor(VentaProcessor):
    """Processor para devoluciones.

    Extiende VentaProcessor con lógica propia de devolución:
      1. Inserta un registro en la tabla `devoluciones`.
      2. Acumula el importe devuelto en `clientes.total_devoluciones`.

    `total_cents` llega ya como int en céntimos (el payload builder
    aplica prepare_for_db() antes de construir el payload).
    Las dos operaciones secundarias son no-bloqueantes: si fallan
    se loguean pero no interrumpen el flujo.
    """

    def process(self, *, carrito_items: List[Dict], resumen: Dict, **kwargs) -> int:
        # 1. Flujo base: ticket, líneas, stock, pagos, audit
        ticket_id = super().process(carrito_items=carrito_items, resumen=resumen, **kwargs)

        # total_cents ya es int en céntimos; tomamos el valor absoluto (devuelto)
        devuelto_cents = abs(kwargs.get('total_cents', 0) or 0)
        cliente_id     = kwargs.get('cliente_id')
        cajero         = kwargs.get('cajero')
        created_at     = kwargs.get('created_at')

        # 2. Registrar en devoluciones + actualizar clientes.total_devoluciones
        try:
            self.db.execute_query(
                """INSERT INTO devoluciones (ticket_id, cliente_id, cajero, total_cents, created_at)
                   VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
                (ticket_id, cliente_id, cajero, devuelto_cents, created_at),
            )
            if cliente_id is not None:
                self.db.execute_query(
                    "UPDATE clientes SET total_devoluciones = total_devoluciones + ? WHERE id = ?",
                    (devuelto_cents, cliente_id),
                )
        except Exception:
            logger.exception(
                'DevolucionProcessor: error en operaciones secundarias (ticket_id=%s)', ticket_id
            )

        return ticket_id
