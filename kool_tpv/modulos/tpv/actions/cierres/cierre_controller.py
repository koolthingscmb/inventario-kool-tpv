"""Controlador ligero para la funcionalidad de cierres.

Provee métodos para obtener tickets sin cierre (cierre_id IS NULL) y otras
operaciones de negocio mínimas. Está diseñado para ser extendido según las
necesidades posteriores (filtros por tipos/categorías/productos/fidelización).
"""
from typing import List, Dict, Any, Optional
import logging


class CierreController:
    def __init__(self, db):
        self.db = db

    def fetch_tickets_without_cierre(self, limit: int = 1000, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Devolver lista de tickets con `cierre_id IS NULL`.

        Usa el cursor de la conexión para recuperar nombres de columnas y
        mapear filas a dicts dinámicamente.
        """
        try:
            # Select ticket fields plus cliente nombre and number of lines (num_ventas)
            sql = (
                "SELECT t.id, t.created_at, t.num_ticket, t.total, COALESCE(c.nombre, 'Sin cliente') AS cliente_nombre, "
                "COUNT(tl.id) AS num_ventas "
                "FROM tickets t "
                "LEFT JOIN clientes c ON t.cliente_id = c.id "
                "LEFT JOIN ticket_lines tl ON tl.ticket_id = t.id "
                "WHERE t.cierre_id IS NULL "
                "GROUP BY t.id "
                "ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
            )
            # For now ignore `filters` (checkboxes) — to be implemented later
            cur = None
            self.db.connect()
            if getattr(self.db, 'connection', None) is not None:
                cur = self.db.connection.cursor()
                cur.execute(sql, (limit, offset))
                rows = cur.fetchall()
                cols = [c[0] for c in cur.description] if cur.description else []
                items = []
                for r in rows or []:
                    d = {cols[i]: r[i] for i in range(min(len(cols), len(r)))}
                    # ensure num_ventas is int
                    try:
                        if 'num_ventas' in d and d['num_ventas'] is not None:
                            d['num_ventas'] = int(d['num_ventas'])
                    except Exception:
                        pass
                    items.append(d)
                return items
            else:
                # fallback to db.fetch_all when connection not exposed
                rows = self.db.fetch_all(sql, (limit, offset))
                # cannot map columns without cursor description; return raw rows
                return [dict(row) if isinstance(row, dict) else {'row': row} for row in rows]
        except Exception:
            logging.exception('Error fetch_tickets_without_cierre')
            return []

    def mark_tickets_with_cierre(self, ticket_ids: List[int], cierre_id: int) -> bool:
        """Asignar `cierre_id` a una lista de tickets."""
        try:
            if not ticket_ids:
                return True
            placeholders = ','.join(['?'] * len(ticket_ids))
            sql = f'UPDATE tickets SET cierre_id = ? WHERE id IN ({placeholders})'
            params = (cierre_id, *ticket_ids)
            self.db.connect()
            self.db.execute_query(sql, params)
            return True
        except Exception:
            logging.exception('Error mark_tickets_with_cierre')
            return False
