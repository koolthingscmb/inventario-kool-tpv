from typing import Optional, Dict, Any, List
import logging

from kool_tpv.base_datos.db_wrapper import Database


class CategoriaRepository:
    """Repository de acceso a BD para la tabla `categorias`.

    Reglas:
     - Sin try/except (los errores escalan al caller)
     - Sin transformaciones de tipos
     - Sin normalización
     - Usa self.db.fetch_one / fetch_all / execute_query
    """

    def __init__(self, db: Database):
        self.db = db

    # ── LECTURA ──────────────────────────────────────────────────────────────

    def get_con_productos(self) -> List[str]:
        """Nombres de categorías que tienen al menos un producto asociado."""
        query = """
        SELECT DISTINCT c.nombre
        FROM categorias c
        INNER JOIN productos p ON c.id = p.categoria
        ORDER BY c.nombre
        """
        rows = self.db.fetch_all(query)
        return [str(r[0]) for r in rows] if rows else []

    def get_all(self) -> List[Dict[str, Any]]:
        """Todas las categorías ordenadas por nombre."""
        rows = self.db.fetch_all(
            'SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje, color, icono '
            'FROM categorias ORDER BY nombre'
        )
        return [
            {
                'id': r[0],
                'nombre': r[1],
                'descripcion': r[2],
                'shopify_taxonomy': r[3],
                'fide_porcentaje': r[4],
                'color': r[5],
                'icono': r[6],
            }
            for r in rows
        ] if rows else []

    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Categoría por id. Devuelve None si no existe."""
        row = self.db.fetch_one(
            'SELECT id, nombre, descripcion, shopify_taxonomy, fide_porcentaje, color, icono '
            'FROM categorias WHERE id = ?',
            (id,),
        )
        if row is None:
            return None
        return {
            'id': row[0],
            'nombre': row[1],
            'descripcion': row[2],
            'shopify_taxonomy': row[3],
            'fide_porcentaje': row[4],
            'color': row[5],
            'icono': row[6],
        }

    def get_ventas_por_categoria(self, ticket_ids: List[int], line_tipo: str = None, categoria_ids: List[int] = None):
        """Obtiene ventas agrupadas por categoría para un rango de tickets.

        Args:
            ticket_ids: Lista de IDs de tickets
            line_tipo: Opcional, filtrar por tipo de línea ('venta', 'devolucion')
            categoria_ids: Opcional, filtrar por IDs de categoría específicos

        Returns:
            List[(nombre_categoria, tickets_count, unidades_sum, total_euros)]
        """
        if not ticket_ids:
            return []

        try:
            placeholders = ','.join(['?'] * len(ticket_ids))
            sql = f"""
            SELECT c.nombre,
                   COUNT(DISTINCT tl.ticket_id) AS tickets_cnt,
                   COALESCE(SUM(tl.cantidad), 0) AS uds,
                   COALESCE(SUM(tl.cantidad * tl.precio), 0) AS total_cents
            FROM ticket_lines tl
            JOIN productos p ON tl.producto_id = p.id
            JOIN categorias c ON p.categoria = c.id
            WHERE tl.ticket_id IN ({placeholders})
            """

            params = list(ticket_ids)
            if line_tipo:
                sql += " AND tl.line_tipo = ?"
                params.append(line_tipo)

            if categoria_ids:
                cat_placeholders = ','.join(['?'] * len(categoria_ids))
                sql += f" AND p.categoria IN ({cat_placeholders})"
                params.extend(categoria_ids)

            sql += " GROUP BY c.id, c.nombre ORDER BY total_cents DESC"

            rows = self.db.fetch_all(sql, tuple(params))

            # Convertir céntimos a euros (Decimal) y devolver como Decimal
            from kool_tpv.base_datos.money_adapter import read_from_db
            result = []
            for row in (rows or []):
                nombre = row[0]
                tickets_cnt = int(row[1] or 0)
                uds = int(row[2] or 0)
                total_cents = int(row[3] or 0)
                total_euros = read_from_db(total_cents)
                result.append((nombre, tickets_cnt, uds, total_euros))

            return result

        except Exception as e:
            logging.exception("Error obteniendo ventas por categoría: %s", e)
            return []

    # ── ESCRITURA ─────────────────────────────────────────────────────────────

    def insert(
        self,
        nombre: str,
        descripcion: str,
        shopify_taxonomy: str,
        fide_porcentaje: float,
        color: str = None,
        icono: str = None,
    ) -> int:
        """Inserta una nueva categoría. Devuelve el id generado."""
        cur = self.db.execute_query(
            'INSERT INTO categorias (nombre, descripcion, shopify_taxonomy, fide_porcentaje, color, icono) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje), color, icono),
        )
        return cur.lastrowid

    def update(
        self,
        id: int,
        nombre: str,
        descripcion: str,
        shopify_taxonomy: str,
        fide_porcentaje: float,
        color: str = None,
        icono: str = None,
    ) -> None:
        """Actualiza una categoría existente."""
        self.db.execute_query(
            'UPDATE categorias SET nombre = ?, descripcion = ?, '
            'shopify_taxonomy = ?, fide_porcentaje = ?, color = ?, icono = ? WHERE id = ?',
            (nombre, descripcion, shopify_taxonomy, float(fide_porcentaje), color, icono, id),
        )

    def delete(self, id: int) -> None:
        """Elimina una categoría por id."""
        self.db.execute_query('DELETE FROM categorias WHERE id = ?', (id,))
