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
            "SELECT "
            "SUM(CASE WHEN total >= 0 THEN 1 ELSE 0 END) as total_tickets, "
            "COALESCE(SUM(CASE WHEN total >= 0 THEN total ELSE 0 END), 0) as total_ventas, "
            "COALESCE(SUM(CASE WHEN total >= 0 THEN subtotal ELSE 0 END), 0) as total_base, "
            "SUM(CASE WHEN total < 0 THEN 1 ELSE 0 END) as num_devoluciones, "
            "COALESCE(SUM(CASE WHEN total < 0 THEN total ELSE 0 END), 0) as total_devoluciones "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total != 0"
        )
        row = self.db.fetch_one(query, (fecha_inicio_sql, fecha_fin_sql))
        if not row:
            return {"total_tickets": 0, "total_ventas": 0.0, "total_base": 0.0,
                    "num_devoluciones": 0, "total_devoluciones": 0.0}
        return {
            "total_tickets": int(row[0] or 0),
            "total_ventas": float(read_from_db(row[1] or 0)),
            "total_base": float(read_from_db(row[2] or 0)),
            "num_devoluciones": int(row[3] or 0),
            "total_devoluciones": float(read_from_db(row[4] or 0)),
        }

    # ── VENTAS DIARIAS ────────────────────────────────────────────────────────

    def get_ventas_diarias(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas por día: fecha, num_tickets, total_uds, total."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "WITH daily_totals AS ("
            "SELECT DATE(created_at) as fecha, "
            "COALESCE(SUM(total), 0) as total_dia "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total > 0 "
            "GROUP BY DATE(created_at)"
            ") "
            "SELECT DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(dt.total_dia, 0) as total_dia "
            "FROM tickets t "
            "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id AND tl.line_tipo = 'venta' "
            "LEFT JOIN daily_totals dt ON DATE(t.created_at) = dt.fecha "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 "
            "GROUP BY DATE(t.created_at) ORDER BY DATE(t.created_at) ASC"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql, fecha_inicio_sql, fecha_fin_sql))
        result = []
        for r in rows or []:
            result.append({
                "fecha": str(r[0]) if r[0] is not None else '',
                "num_tickets": int(r[1] or 0),
                "total_uds": int(r[2] or 0),
                "total": float(read_from_db(r[3] or 0)),
            })
        return result

    # ── DEVOLUCIONES RESUMEN ──────────────────────────────────────────────────

    def get_devoluciones_resumen(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen de devoluciones: num_tickets, total_uds, total (negativo)."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT "
            "(SELECT COUNT(DISTINCT t.id) FROM tickets t "
            " WHERE t.created_at BETWEEN ? AND ? AND t.total < 0) as num_tickets, "
            "(SELECT COALESCE(SUM(tl.cantidad), 0) FROM ticket_lines tl "
            " JOIN tickets t ON tl.ticket_id = t.id "
            " WHERE t.created_at BETWEEN ? AND ? AND t.total < 0 AND tl.line_tipo = 'devolucion') as total_uds, "
            "(SELECT COALESCE(SUM(t.total), 0) FROM tickets t "
            " WHERE t.created_at BETWEEN ? AND ? AND t.total < 0) as total_devol"
        )
        row = self.db.fetch_one(query, (fecha_inicio_sql, fecha_fin_sql,
                                        fecha_inicio_sql, fecha_fin_sql,
                                        fecha_inicio_sql, fecha_fin_sql))
        if not row:
            return {"num_tickets": 0, "total_uds": 0, "total": 0.0}
        return {
            "num_tickets": int(row[0] or 0),
            "total_uds": int(row[1] or 0),
            "total": float(read_from_db(row[2] or 0)),
        }

    # ── VENTAS POR CAJERO ─────────────────────────────────────────────────────

    def get_ventas_por_cajero_y_dia(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas por cajero y día: cajero, fecha, num_tickets, total_uds, total."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "WITH cajero_totals AS ("
            "SELECT cajero, DATE(created_at) as fecha, "
            "COALESCE(SUM(total), 0) as total_dia "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total > 0 "
            "GROUP BY cajero, DATE(created_at)"
            ") "
            "SELECT t.cajero, DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(ct.total_dia, 0) as total_dia "
            "FROM tickets t "
            "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id AND tl.line_tipo = 'venta' "
            "LEFT JOIN cajero_totals ct ON t.cajero IS ct.cajero AND DATE(t.created_at) = ct.fecha "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 "
            "GROUP BY t.cajero, DATE(t.created_at) "
            "ORDER BY t.cajero ASC, DATE(t.created_at) ASC"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql, fecha_inicio_sql, fecha_fin_sql))
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

    # ── VENTAS POR PRODUCTO (desglosado por día) ──────────────────────────────

    def get_ventas_por_producto_y_dia(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        product_ids: Optional[List[int]] = None
    ) -> list:
        """Ventas por producto desglosadas por día.

        Returns:
            Lista de dicts: group_name (nombre producto), fecha, num_tickets, total_uds, total
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        sql = (
            "SELECT p.nombre, DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(SUM(tl.cantidad * tl.precio), 0) as total_cents "
            "FROM ticket_lines tl "
            "JOIN tickets t ON tl.ticket_id = t.id "
            "JOIN productos p ON tl.producto_id = p.id "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 AND tl.line_tipo = 'venta'"
        )
        params: list = [fecha_inicio_sql, fecha_fin_sql]
        if product_ids:
            ph = ','.join(['?'] * len(product_ids))
            sql += f" AND p.id IN ({ph})"
            params.extend(product_ids)
        sql += " GROUP BY p.id, p.nombre, DATE(t.created_at) ORDER BY p.nombre ASC, DATE(t.created_at) ASC"
        rows = self.db.fetch_all(sql, tuple(params))
        result = []
        for r in rows or []:
            result.append({
                "group_name": str(r[0] or ''),
                "fecha": str(r[1]) if r[1] is not None else '',
                "num_tickets": int(r[2] or 0),
                "total_uds": int(r[3] or 0),
                "total": float(read_from_db(int(r[4] or 0))),
            })
        return result

    # ── VENTAS POR CATEGORÍA / TIPO (desglosado por día) ─────────────────────

    def get_ventas_por_grupo_y_dia(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        group_by: str,
        filter_ids: Optional[List[int]] = None
    ) -> list:
        """Ventas por categoría o tipo desglosadas por día.

        Args:
            group_by: 'categoria' o 'tipo'
            filter_ids: IDs de categoría/tipo a filtrar (None = todos)

        Returns:
            Lista de dicts: group_name, fecha, num_tickets, total_uds, total
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        if group_by == 'categoria':
            join_table = 'categorias'
            alias = 'g'
            id_col = 'p.categoria'
        else:
            join_table = 'tipos'
            alias = 'g'
            id_col = 'p.tipo'

        sql = (
            f"SELECT {alias}.nombre, DATE(t.created_at) as fecha, "
            f"COUNT(DISTINCT t.id) as num_tickets, "
            f"COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            f"COALESCE(SUM(tl.cantidad * tl.precio), 0) as total_cents "
            f"FROM ticket_lines tl "
            f"JOIN tickets t ON tl.ticket_id = t.id "
            f"JOIN productos p ON tl.producto_id = p.id "
            f"JOIN {join_table} {alias} ON {id_col} = {alias}.id "
            f"WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 AND tl.line_tipo = 'venta'"
        )
        params: list = [fecha_inicio_sql, fecha_fin_sql]

        if filter_ids:
            ph = ','.join(['?'] * len(filter_ids))
            sql += f" AND {id_col} IN ({ph})"
            params.extend(filter_ids)

        sql += f" GROUP BY {alias}.id, {alias}.nombre, DATE(t.created_at) ORDER BY {alias}.nombre ASC, DATE(t.created_at) ASC"

        rows = self.db.fetch_all(sql, tuple(params))
        result = []
        for r in rows or []:
            result.append({
                "group_name": str(r[0] or ''),
                "fecha": str(r[1]) if r[1] is not None else '',
                "num_tickets": int(r[2] or 0),
                "total_uds": int(r[3] or 0),
                "total": float(read_from_db(int(r[4] or 0))),
            })
        return result

    # ── COUNT DISTINCT TICKETS ────────────────────────────────────────────────

    def count_distinct_tickets_ventas(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        group_by: str = None,
        filter_ids: Optional[List[int]] = None
    ) -> int:
        """Contar tickets distintos con líneas de venta en el rango.

        A diferencia de sumar COUNT(DISTINCT t.id) por grupo, esto devuelve
        el número real de tickets únicos, sin duplicar tickets que tienen
        varios productos/categorías/tipos.

        Args:
            group_by: 'categoria' o 'tipo' (para aplicar filter_ids)
            filter_ids: IDs de categoría/tipo a filtrar (None = todos)
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        sql = (
            "SELECT COUNT(DISTINCT t.id) "
            "FROM ticket_lines tl "
            "JOIN tickets t ON tl.ticket_id = t.id "
            "JOIN productos p ON tl.producto_id = p.id "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 AND tl.line_tipo = 'venta'"
        )
        params: list = [fecha_inicio_sql, fecha_fin_sql]
        if group_by and filter_ids:
            id_col = 'p.categoria' if group_by == 'categoria' else 'p.tipo'
            ph = ','.join(['?'] * len(filter_ids))
            sql += f" AND {id_col} IN ({ph})"
            params.extend(filter_ids)
        row = self.db.fetch_one(sql, tuple(params))
        return int(row[0] or 0) if row else 0

    # ── VENTAS POR CATEGORÍA ──────────────────────────────────────────────────

    def get_ticket_ids_por_rango(self, fecha_inicio: str, fecha_fin: str) -> List[int]:
        """IDs de tickets con venta en el rango de fechas."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT id FROM tickets "
            "WHERE created_at BETWEEN ? AND ? AND total != 0"
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
            f"COALESCE(SUM(CASE WHEN tl.line_tipo = 'devolucion' THEN -tl.cantidad ELSE tl.cantidad END), 0) AS uds, "
            f"COALESCE(SUM(CASE WHEN tl.line_tipo = 'devolucion' THEN -(tl.cantidad * tl.precio) ELSE (tl.cantidad * tl.precio) END), 0) AS total_cents "
            f"FROM ticket_lines tl "
            f"JOIN productos p ON tl.producto_id = p.id "
            f"JOIN categorias c ON p.categoria = c.id "
            f"WHERE tl.ticket_id IN ({placeholders}) AND tl.line_tipo IN ('venta', 'devolucion')"
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
            f"COALESCE(SUM(CASE WHEN tl.line_tipo = 'devolucion' THEN -tl.cantidad ELSE tl.cantidad END), 0) AS uds, "
            f"COALESCE(SUM(CASE WHEN tl.line_tipo = 'devolucion' THEN -(tl.cantidad * tl.precio) ELSE (tl.cantidad * tl.precio) END), 0) AS total_cents "
            f"FROM ticket_lines tl "
            f"JOIN productos p ON tl.producto_id = p.id "
            f"JOIN tipos t ON p.tipo = t.id "
            f"WHERE tl.ticket_id IN ({placeholders}) AND tl.line_tipo IN ('venta', 'devolucion')"
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

    # ── PRESENCIA ─────────────────────────────────────────────────────────────

    def get_presencia_informe(self, fecha_inicio: str, fecha_fin: str, usuario_ids: Optional[List[int]] = None) -> list:
        """Obtiene fichajes de usuarios en el rango de fechas."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        
        query = """
            SELECT u.nombre as usuario, p.entrada, p.salida, p.duracion_minutos, p.estado, p.notas
            FROM presencia p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.entrada BETWEEN ? AND ?
        """
        params = [fecha_inicio_sql, fecha_fin_sql]
        
        if usuario_ids:
            ph = ','.join(['?'] * len(usuario_ids))
            query += f" AND p.usuario_id IN ({ph})"
            params.extend(usuario_ids)
            
        query += " ORDER BY u.nombre ASC, p.entrada DESC"
        
        rows = self.db.fetch_all(query, tuple(params))
        result = []
        for r in rows or []:
            result.append({
                "usuario": r[0],
                "entrada": r[1],
                "salida": r[2],
                "duracion_minutos": r[3],
                "estado": r[4],
                "notas": r[5]
            })
        return result
