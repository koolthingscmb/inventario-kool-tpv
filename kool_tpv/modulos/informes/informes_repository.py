"""Repository de acceso a BD para el módulo de Informes.

Centraliza todas las queries necesarias para generar informes,
evitando dispersión en repositorios ajenos (Ticket, Categoria, Tipo).
"""
import logging
from typing import List, Optional

from kool_tpv.base_datos.money_adapter import read_from_db

logger = logging.getLogger(__name__)


class InformesRepository:
    """Acceso a BD exclusivo para informes. Sin lógica de negocio."""

    def __init__(self, db):
        self.db = db

    # ── VENTAS RESUMEN ────────────────────────────────────────────────────────

    def get_resumen_ventas(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen agregado: total_tickets, total_ventas, total_base."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT COUNT(*) as total_tickets, "
            "COALESCE(SUM(total), 0) as total_ventas, "
            "COALESCE(SUM(subtotal), 0) as total_base "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total > 0"
        )
        row = self.db.fetch_one(query, (fecha_inicio_sql, fecha_fin_sql))
        if not row:
            return {"total_tickets": 0, "total_ventas": 0.0, "total_base": 0.0}
        return {
            "total_tickets": int(row[0] or 0),
            "total_ventas": float(read_from_db(row[1] or 0)),
            "total_base": float(read_from_db(row[2] or 0)),
        }

    # ── VENTAS DIARIAS ────────────────────────────────────────────────────────

    def get_ventas_diarias(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas por día: fecha, num_tickets, total_uds, total."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(SUM(t.total), 0) as total_dia "
            "FROM tickets t "
            "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id AND tl.line_tipo = 'venta' "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 "
            "GROUP BY DATE(t.created_at) ORDER BY DATE(t.created_at) ASC"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        result = []
        for r in rows or []:
            result.append({
                "fecha": str(r[0]) if r[0] is not None else '',
                "num_tickets": int(r[1] or 0),
                "total_uds": int(r[2] or 0),
                "total": float(read_from_db(r[3] or 0)),
            })
        return result

    # ── VENTAS POR CAJERO ─────────────────────────────────────────────────────

    def get_ventas_por_cajero_y_dia(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas por cajero y día: cajero, fecha, num_tickets, total_uds, total."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT t.cajero, DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(SUM(t.total), 0) as total_dia "
            "FROM tickets t "
            "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id AND tl.line_tipo = 'venta' "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 "
            "GROUP BY t.cajero, DATE(t.created_at) "
            "ORDER BY t.cajero ASC, DATE(t.created_at) ASC"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        result = []
        for r in rows or []:
            result.append({
                "cajero": str(r[0] or 'Sin cajero'),
                "fecha": str(r[1]) if r[1] is not None else '',
                "num_tickets": int(r[2] or 0),
                "total_uds": int(r[3] or 0),
                "total": float(read_from_db(r[4] or 0)),
            })
        return result

    # ── VENTAS POR CATEGORÍA ──────────────────────────────────────────────────

    def get_ticket_ids_por_rango(self, fecha_inicio: str, fecha_fin: str) -> List[int]:
        """IDs de tickets con venta en el rango de fechas."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT id FROM tickets "
            "WHERE created_at BETWEEN ? AND ? AND total > 0"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        return [int(r[0]) for r in (rows or [])]

    def get_ventas_por_categoria(
        self,
        ticket_ids: List[int],
        categoria_ids: Optional[List[int]] = None
    ) -> list:
        """Ventas agrupadas por categoría. Retorna (nombre, tickets, uds, total_euros)."""
        if not ticket_ids:
            return []
        placeholders = ','.join(['?'] * len(ticket_ids))
        sql = (
            f"SELECT c.nombre, "
            f"COUNT(DISTINCT tl.ticket_id) AS tickets_cnt, "
            f"COALESCE(SUM(tl.cantidad), 0) AS uds, "
            f"COALESCE(SUM(tl.cantidad * tl.precio), 0) AS total_cents "
            f"FROM ticket_lines tl "
            f"JOIN productos p ON tl.producto_id = p.id "
            f"JOIN categorias c ON p.categoria = c.id "
            f"WHERE tl.ticket_id IN ({placeholders}) AND tl.line_tipo = 'venta'"
        )
        params = list(ticket_ids)
        if categoria_ids:
            cat_ph = ','.join(['?'] * len(categoria_ids))
            sql += f" AND p.categoria IN ({cat_ph})"
            params.extend(categoria_ids)
        sql += " GROUP BY c.id, c.nombre ORDER BY total_cents DESC"
        rows = self.db.fetch_all(sql, tuple(params))
        result = []
        for row in (rows or []):
            result.append((
                row[0],
                int(row[1] or 0),
                int(row[2] or 0),
                read_from_db(int(row[3] or 0)),
            ))
        return result

    # ── VENTAS POR TIPO ───────────────────────────────────────────────────────

    def get_ventas_por_tipo(
        self,
        ticket_ids: List[int],
        tipo_ids: Optional[List[int]] = None
    ) -> list:
        """Ventas agrupadas por tipo. Retorna (nombre, tickets, uds, total_euros)."""
        if not ticket_ids:
            return []
        placeholders = ','.join(['?'] * len(ticket_ids))
        sql = (
            f"SELECT t.nombre, "
            f"COUNT(DISTINCT tl.ticket_id) AS tickets_cnt, "
            f"COALESCE(SUM(tl.cantidad), 0) AS uds, "
            f"COALESCE(SUM(tl.cantidad * tl.precio), 0) AS total_cents "
            f"FROM ticket_lines tl "
            f"JOIN productos p ON tl.producto_id = p.id "
            f"JOIN tipos t ON p.tipo = t.id "
            f"WHERE tl.ticket_id IN ({placeholders}) AND tl.line_tipo = 'venta'"
        )
        params = list(ticket_ids)
        if tipo_ids:
            tipo_ph = ','.join(['?'] * len(tipo_ids))
            sql += f" AND p.tipo IN ({tipo_ph})"
            params.extend(tipo_ids)
        sql += " GROUP BY t.id, t.nombre ORDER BY total_cents DESC"
        rows = self.db.fetch_all(sql, tuple(params))
        result = []
        for row in (rows or []):
            result.append((
                row[0],
                int(row[1] or 0),
                int(row[2] or 0),
                read_from_db(int(row[3] or 0)),
            ))
        return result

    # ── STOCK ─────────────────────────────────────────────────────────────────

    def get_stock_por_grupo(
        self,
        group_by: str,
        filter_ids: Optional[List[int]] = None
    ) -> list:
        """Stock de productos agrupado por categoría o tipo.

        Args:
            group_by: 'categoria' o 'tipo'
            filter_ids: IDs de categoría/tipo a filtrar (None = todos)

        Returns:
            Lista de dicts: group_name, sku, nombre, stock_actual, stock_minimo, coste
        """
        join_table = 'categorias' if group_by == 'categoria' else 'tipos'
        alias = 'c' if group_by == 'categoria' else 't'
        id_col = 'p.categoria' if group_by == 'categoria' else 'p.tipo'
        name_col = f"{alias}.nombre as group_name"
        query = (
            f"SELECT p.sku, p.nombre, {name_col}, "
            f"p.stock_actual, p.stock_minimo, COALESCE(pr.coste, 0) as precio_coste "
            f"FROM productos p "
            f"LEFT JOIN {join_table} {alias} ON {id_col} = {alias}.id "
            f"LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1 "
            f"WHERE p.activo = 1"
        )
        params = []
        if filter_ids:
            ph = ','.join(['?'] * len(filter_ids))
            query += f" AND {id_col} IN ({ph})"
            params.extend(filter_ids)
        query += f" ORDER BY {alias}.nombre, p.nombre"
        rows = self.db.fetch_all(query, tuple(params) if params else ())
        result = []
        for r in rows or []:
            result.append({
                "sku": r[0],
                "nombre": r[1],
                "group_name": r[2] or f"Sin {group_by}",
                "stock_actual": r[3],
                "stock_minimo": r[4],
                "coste": float(read_from_db(r[5] or 0)),
            })
        return result
