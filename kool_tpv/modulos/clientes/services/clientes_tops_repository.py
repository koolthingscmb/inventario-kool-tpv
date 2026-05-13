"""Repository de consultas TOP de clientes (solo lectura)."""
from typing import List, Dict
import logging
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)


class ClientesTopsRepository:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ #
    #  Helper                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rows_to_result(rows) -> List[Dict]:
        result: List[Dict] = []
        for idx, row in enumerate(rows, start=1):
            try:
                cliente_id = int(row[0]) if row[0] is not None else None
            except Exception:
                cliente_id = None
            try:
                nombre = str(row[1]) if row[1] is not None else ''
            except Exception:
                nombre = ''
            try:
                total_tickets = int(row[2]) if row[2] is not None else 0
            except Exception:
                total_tickets = 0
            try:
                total_unidades = int(row[3]) if row[3] is not None else 0
            except Exception:
                total_unidades = 0
            try:
                total_euros = float(row[4]) if row[4] is not None else 0.0
            except Exception:
                try:
                    total_euros = float(str(row[4]))
                except Exception:
                    total_euros = 0.0

            tesoro_total = 0.0
            tesoro_gastado_total = 0.0
            tesoro_historico = 0.0
            try:
                if len(row) >= 8:
                    try:
                        tesoro_total = float(row[5]) if row[5] is not None else 0.0
                    except Exception:
                        tesoro_total = 0.0
                    try:
                        tesoro_gastado_total = float(row[6]) if row[6] is not None else 0.0
                    except Exception:
                        tesoro_gastado_total = 0.0
                    try:
                        tesoro_historico = float(row[7]) if row[7] is not None else 0.0
                    except Exception:
                        tesoro_historico = 0.0
            except Exception:
                pass

            result.append({
                'posicion': idx,
                'cliente_id': cliente_id,
                'nombre': nombre,
                'total_tickets': total_tickets,
                'total_unidades': total_unidades,
                'total_euros': total_euros,
                'tesoro_total': tesoro_total,
                'tesoro_gastado_total': tesoro_gastado_total,
                'tesoro_historico': tesoro_historico,
            })

        return result

    # ------------------------------------------------------------------ #
    #  Queries                                                             #
    # ------------------------------------------------------------------ #

    def get_top_clientes_general(self, limit: int = 50) -> List[Dict]:
        q = (
            "SELECT id, nombre, COALESCE(total_compras,0) AS total_compras, "
            "COALESCE(total_unidades,0) AS total_unidades, "
            "COALESCE(total_compras_euros,0) AS total_compras_euros, "
            "COALESCE(tesoro_total,0) AS tesoro_total, "
            "COALESCE(tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(tesoro_historico,0) AS tesoro_historico "
            "FROM clientes "
            "WHERE COALESCE(total_compras_euros,0) > 0 "
            "ORDER BY total_compras_euros DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (limit,)) or []
        return self._rows_to_result(rows)

    def get_top_por_producto(self, producto_id: int, limit: int = 50) -> List[Dict]:
        q = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(t.cliente,'') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(tl.cantidad),0) AS total_unidades, "
            "COALESCE(SUM(tl.precio * tl.cantidad),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            "FROM tickets t "
            "JOIN ticket_lines tl ON tl.ticket_id = t.id "
            "JOIN clientes c ON c.id = t.cliente_id "
            "WHERE tl.producto_id = ? AND t.cliente_id IS NOT NULL "
            "GROUP BY t.cliente_id, t.cliente "
            "HAVING total_euros > 0 "
            "ORDER BY total_euros DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (producto_id, limit)) or []
        return self._rows_to_result(rows)

    def get_top_por_categoria(self, categoria_id: int, limit: int = 50) -> List[Dict]:
        q = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(t.cliente,'') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(tl.cantidad),0) AS total_unidades, "
            "COALESCE(SUM(tl.precio * tl.cantidad),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            "FROM tickets t "
            "JOIN ticket_lines tl ON tl.ticket_id = t.id "
            "JOIN productos p ON p.id = tl.producto_id "
            "JOIN clientes c ON c.id = t.cliente_id "
            "WHERE p.categoria = ? AND t.cliente_id IS NOT NULL "
            "GROUP BY t.cliente_id, t.cliente "
            "HAVING total_euros > 0 "
            "ORDER BY total_euros DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (categoria_id, limit)) or []
        return self._rows_to_result(rows)

    def get_top_por_tipo(self, tipo_id: int, limit: int = 50) -> List[Dict]:
        q = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(t.cliente,'') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(tl.cantidad),0) AS total_unidades, "
            "COALESCE(SUM(tl.precio * tl.cantidad),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            "FROM tickets t "
            "JOIN ticket_lines tl ON tl.ticket_id = t.id "
            "JOIN productos p ON p.id = tl.producto_id "
            "JOIN clientes c ON c.id = t.cliente_id "
            "WHERE p.tipo = ? AND t.cliente_id IS NOT NULL "
            "GROUP BY t.cliente_id, t.cliente "
            "HAVING total_euros > 0 "
            "ORDER BY total_euros DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (tipo_id, limit)) or []
        return self._rows_to_result(rows)

    def get_top_por_tesoro(self, limit: int = 50) -> List[Dict]:
        q = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(t.cliente,'') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(t.num_ventas),0) AS total_unidades, "
            "COALESCE(SUM(COALESCE(t.tesoro_total_ticket,0)),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            "FROM tickets t "
            "JOIN clientes c ON c.id = t.cliente_id "
            "WHERE t.cliente_id IS NOT NULL "
            "GROUP BY t.cliente_id, t.cliente "
            "HAVING total_euros > 0 "
            "ORDER BY total_euros DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (limit,)) or []
        return self._rows_to_result(rows)

    def get_top_ordenado_por_tesoro(self, field: str, limit: int = 50) -> List[Dict]:
        allowed = ('tesoro_total', 'tesoro_gastado_total', 'tesoro_historico')
        if field not in allowed:
            logger.warning('Campo de tesoro no permitido para orden: %s', field)
            return []
        q = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(t.cliente,'') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(t.num_ventas),0) AS total_unidades, "
            "COALESCE(SUM(COALESCE(t.tesoro_total_ticket,0)),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            "FROM tickets t "
            "JOIN clientes c ON c.id = t.cliente_id "
            "WHERE t.cliente_id IS NOT NULL "
            "GROUP BY t.cliente_id, t.cliente "
            f"ORDER BY COALESCE(CAST(c.{field} AS REAL), 0) DESC "
            "LIMIT ?"
        )
        rows = self.db.fetch_all(q, (limit,)) or []
        return self._rows_to_result(rows)

    def get_top_filtrado(
        self,
        categoria_id: int = None,
        tipo_id: int = None,
        producto_id: int = None,
        limit: int = 50,
    ) -> List[Dict]:
        select = (
            "SELECT t.cliente_id AS cliente_id, COALESCE(c.nombre, '') AS nombre, "
            "COUNT(DISTINCT t.id) AS total_tickets, "
            "COALESCE(SUM(tl.cantidad),0) AS total_unidades, "
            "COALESCE(SUM(tl.precio * tl.cantidad),0) AS total_euros, "
            "COALESCE(c.tesoro_total,0) AS tesoro_total, "
            "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
            "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
        )
        frm = (
            "FROM tickets t "
            "JOIN ticket_lines tl ON tl.ticket_id = t.id "
            "JOIN productos p ON p.id = tl.producto_id "
            "JOIN clientes c ON c.id = t.cliente_id "
        )
        where_clauses = ["t.cliente_id IS NOT NULL"]
        params = []

        if categoria_id is not None:
            where_clauses.append("p.categoria = ?")
            params.append(categoria_id)
        if tipo_id is not None:
            where_clauses.append("p.tipo = ?")
            params.append(tipo_id)
        if producto_id is not None:
            where_clauses.append("tl.producto_id = ?")
            params.append(producto_id)

        where = "WHERE " + " AND ".join(where_clauses) + " "
        group = "GROUP BY t.cliente_id, c.nombre "
        having = "HAVING total_euros > 0 "
        order = "ORDER BY total_euros DESC "
        limit_sql = "LIMIT ?"
        params.append(limit)

        q = select + frm + where + group + having + order + limit_sql
        rows = self.db.fetch_all(q, tuple(params)) or []
        return self._rows_to_result(rows)
