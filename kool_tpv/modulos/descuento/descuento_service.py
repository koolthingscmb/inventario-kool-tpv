from __future__ import annotations
from typing import List, Dict, Any, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.ticket.ticket_repository import TicketRepository
from kool_tpv.modulos.descuento.descuento_repository import DescuentoRepository
from kool_tpv.base_datos.money_adapter import read_from_db


class DescuentoService:
    def __init__(self, db: Database, ticket_repo: TicketRepository, descuento_repo: DescuentoRepository):
        self.db = db
        self.ticket_repo = ticket_repo
        self.descuento_repo = descuento_repo

    def _resolve_desc(self, desc: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a descuento descriptor: may contain 'id' to load template or full fields."""
        if desc.get('id'):
            dto = self.descuento_repo.get_by_id(int(desc.get('id')))
            if not dto:
                raise ValueError(f"Descuento id={desc.get('id')} no encontrado")
            return dto
        return desc

    def apply_discount(self, ticket_id: int, descuentos: List[Dict[str, Any]], usuario: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Apply a list of discounts to a ticket atomically.

        Returns a summary dict: {'ticket_id', 'total_descuento_cents', 'line_ids', 'applied_ids'}
        """
        if not descuentos:
            return {'ticket_id': ticket_id, 'total_descuento_cents': 0, 'line_ids': [], 'applied_ids': []}

        # Fetch ticket and check cierre
        row = self.db.fetch_one('SELECT id, subtotal, cierre_id FROM tickets WHERE id = ?', (ticket_id,))
        if not row:
            raise ValueError('Ticket no encontrado')
        if row.get('cierre_id') is not None and not force:
            raise ValueError('Ticket ya cerrado; use force=True para forzar')

        subtotal_cents = int(row.get('subtotal') or 0)

        total_descuento = 0
        created_line_ids: List[int] = []
        applied_ids: List[int] = []

        with self.db.transaction() as cur:
            # For each discount, resolve template and compute amount
            for desc in descuentos:
                dto = self._resolve_desc(desc)
                tipo = dto.get('tipo')
                # Decide amount in cents
                if tipo == 'porcentaje' or dto.get('valor_porcentaje') is not None:
                    porcentaje = int(dto.get('valor_porcentaje') or dto.get('valor', 0))
                    monto = (subtotal_cents * porcentaje) // 100
                else:
                    # direct cents value in table: valor_cents
                    monto = int(dto.get('valor_cents') or 0)

                if monto == 0:
                    continue

                # Insert ticket_line of type 'descuento'
                line_id = self.ticket_repo.insert_ticket_line(ticket_id, None, 'Descuento', 1, -int(monto), dto.get('iva', 0), 'descuento', None, cur=cur)
                created_line_ids.append(line_id)

                # Persist applied discount snapshot on ticket (last applied wins for tipo/valor)
                dto_id = dto.get('id')
                self.descuento_repo.apply_to_ticket(ticket_id, dto_id, dto.get('tipo'), dto.get('valor_porcentaje') or dto.get('valor_cents') or dto.get('valor'), monto, cur=cur)
                if dto_id:
                    applied_ids.append(int(dto_id))

                total_descuento += monto

        # After commit, return summary
        return {
            'ticket_id': ticket_id,
            'total_descuento_cents': total_descuento,
            'line_ids': created_line_ids,
            'applied_ids': applied_ids,
        }
