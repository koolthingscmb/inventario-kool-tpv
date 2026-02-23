"""Servicios para obtener 'tops' de clientes (backend).

Este módulo expone `ClientesTopsService` con consultas limpias hacia la
tabla `clientes` para calcular rankings/posiciones en Python.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class ClientesTopsService:
    """Servicio que provee rankings/Top de clientes."""

    @staticmethod
    def get_top_clientes_general(db, limit: int = 50) -> List[Dict]:
        """
        Obtiene el Top general de clientes ordenado por `total_compras_euros`.

        Args:
            db: instancia del wrapper Database (debe exponer .connection)
            limit: número máximo de filas a devolver

        Returns:
            Lista de diccionarios con claves: posicion, cliente_id, nombre,
            total_tickets, total_unidades, total_euros
        """
        if db is None:
            return []

        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

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
            cur.execute(q, (limit,))
            rows = cur.fetchall() or []

            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top general de clientes')
            return []

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

            # Detectar si la fila incluye campos de tesoro adicionales
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

    @staticmethod
    def get_top_por_producto(db, producto_id: int, limit: int = 50) -> List[Dict]:
        if db is None:
            return []
        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

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
            cur.execute(q, (producto_id, limit))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top por producto')
            return []

    @staticmethod
    def get_top_por_categoria(db, categoria_id: int, limit: int = 50) -> List[Dict]:
        if db is None:
            return []
        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

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
            cur.execute(q, (categoria_id, limit))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top por categoria')
            return []

    @staticmethod
    def get_top_por_tipo(db, tipo_id: int, limit: int = 50) -> List[Dict]:
        if db is None:
            return []
        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

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
            cur.execute(q, (tipo_id, limit))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top por tipo')
            return []

    @staticmethod
    def get_top_por_tesoro(db, limit: int = 50) -> List[Dict]:
        """Ranking por tesoro: sumar el tesoro_total_ticket por cliente."""
        if db is None:
            return []
        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()
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
            cur.execute(q, (limit,))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top por tesoro')
            return []

    @staticmethod
    def get_top_ordenado_por_tesoro(db, field: str, limit: int = 50) -> List[Dict]:
        """Obtiene top de clientes ordenado por un campo de tesoro del cliente.

        `field` debe ser uno de: 'tesoro_total', 'tesoro_gastado_total', 'tesoro_historico'.
        """
        if db is None:
            return []

        allowed = ('tesoro_total', 'tesoro_gastado_total', 'tesoro_historico')
        if field not in allowed:
            logger.warning('Campo de tesoro no permitido para orden: %s', field)
            return []

        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

            # Ordenar por la columna de clientes (campo seguro porque se valida)
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
            cur.execute(q, (limit,))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top ordenado por tesoro')
            return []

    @staticmethod
    def get_top_filtrado(
        db,
        categoria_id: int = None,
        tipo_id: int = None,
        producto_id: int = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Obtiene top de clientes aplicando filtros combinados sobre productos/ticket_lines.

        La consulta agrupa por cliente y suma importe (precio * cantidad) en
        ticket_lines. Devuelve la misma estructura que los otros métodos.
        """
        if db is None:
            return []
        try:
            conn = getattr(db, 'connection', None)
            if conn is None:
                return []
            cur = conn.cursor()

            # Base SELECT (añadir campos de tesoro desde la tabla clientes)
            select = (
                "SELECT t.cliente_id AS cliente_id, COALESCE(c.nombre, '') AS nombre, "
                "COUNT(DISTINCT t.id) AS total_tickets, "
                "COALESCE(SUM(tl.cantidad),0) AS total_unidades, "
                "COALESCE(SUM(tl.precio * tl.cantidad),0) AS total_euros, "
                "COALESCE(c.tesoro_total,0) AS tesoro_total, "
                "COALESCE(c.tesoro_gastado_total,0) AS tesoro_gastado_total, "
                "COALESCE(c.tesoro_historico,0) AS tesoro_historico "
            )

            # FROM / JOIN
            frm = (
                "FROM tickets t "
                "JOIN ticket_lines tl ON tl.ticket_id = t.id "
                "JOIN productos p ON p.id = tl.producto_id "
                "JOIN clientes c ON c.id = t.cliente_id "
            )

            # WHERE base
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

            cur.execute(q, tuple(params))
            rows = cur.fetchall() or []
            return ClientesTopsService._rows_to_result(rows)
        except Exception:
            logger.exception('Error obteniendo top filtrado')
            return []
