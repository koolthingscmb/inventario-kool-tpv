from __future__ import annotations
from typing import Any

from kool_tpv.modulos.ticket.base_processor import TicketProcessor
from kool_tpv.modulos.descuento.descuento_repository import DescuentoRepository
import logging

logger = logging.getLogger(__name__)


class DescuentoProcessor(TicketProcessor):
    def process(self, **kwargs):
        ticket_id = kwargs.get('ticket_id')
        descuentos = kwargs.get('descuentos', []) or []

        if not ticket_id or not descuentos:
            return ticket_id

        # Resolve subtotal from ticket to compute percentage-based discounts
        try:
            row = self.db.fetch_one('SELECT id, subtotal, cierre_id FROM tickets WHERE id = ?', (ticket_id,))
        except Exception:
            row = None

        subtotal_cents = int(row['subtotal'] or 0) if row else 0

        desc_repo = DescuentoRepository(self.db)
        created_lines = []

        try:
            with self.db.transaction() as cur:
                for desc in descuentos:
                    # allow descriptor to be either an id reference or a full dict
                    dto = desc
                    try:
                        if desc and desc.get('id'):
                            dto = desc_repo.get_by_id(int(desc.get('id')))
                    except Exception:
                        logger.exception('DescuentoProcessor: error resolviendo plantilla de descuento')

                    if not dto:
                        continue

                    tipo = dto.get('tipo')
                    monto = 0
                    descuento_val = None

                    # porcentaje-based
                    if tipo == 'porcentaje' or dto.get('valor_porcentaje') is not None:
                        try:
                            porcentaje = int(dto.get('valor_porcentaje') or dto.get('valor') or 0)
                        except Exception:
                            porcentaje = 0
                        monto = (subtotal_cents * porcentaje) // 100
                        descuento_val = porcentaje
                    else:
                        # directo: valor en céntimos
                        try:
                            monto = int(dto.get('valor_cents') or dto.get('valor') or 0)
                        except Exception:
                            monto = 0
                        descuento_val = dto.get('valor_cents') or dto.get('valor')

                    if monto == 0:
                        continue

                    # Insertar línea negativa representando el descuento
                    try:
                        line_id = self.repo.insert_ticket_line(ticket_id, None, 'Descuento', 1, -int(monto), int(dto.get('iva', 0) or 0), 'descuento', None, cur=cur)
                        created_lines.append(line_id)
                    except Exception:
                        logger.exception('DescuentoProcessor: error insertando línea de descuento')
                        raise

                    # Persistir snapshot del descuento aplicado en la fila tickets
                    try:
                        dto_id = dto.get('id')
                        desc_repo.apply_to_ticket(ticket_id, dto_id, dto.get('tipo'), descuento_val, monto, cur=cur)
                    except Exception:
                        logger.exception('DescuentoProcessor: error guardando snapshot de descuento en ticket')
                        raise

        except Exception:
            logger.exception('DescuentoProcessor: transacción fallida')
            raise

        return ticket_id
