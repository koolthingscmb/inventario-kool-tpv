"""Repository para informes del módulo de Producción."""
import logging
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database


class ProduccionInformesRepository:
    """Acceso a datos para informes de producción."""

    def __init__(self, db: Database):
        self.db = db

    # ── 1. RESUMEN DE PRODUCCIÓN ─────────────────────────────────────────────

    def get_resumen_produccion(self, fecha_inicio: str, fecha_fin: str) -> dict:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            query = """SELECT
                        COUNT(DISTINCT o.id), COALESCE(SUM(l.cantidad), 0), COALESCE(SUM(l.coste_total), 0)
                       FROM produccion_ordenes o
                       LEFT JOIN produccion_lineas l ON l.orden_id = o.id
                       WHERE o.fecha_hora BETWEEN ? AND ?"""
            row = self.db.fetch_one(query, (fi, ff))
            total_ordenes = int(row[0]) if row else 0
            total_unidades = int(row[1]) if row else 0
            coste_total = int(row[2]) if row else 0

            q_est = """SELECT o.estado, COUNT(*), COALESCE(SUM(l.cantidad), 0)
                       FROM produccion_ordenes o
                       LEFT JOIN produccion_lineas l ON l.orden_id = o.id
                       WHERE o.fecha_hora BETWEEN ? AND ?
                       GROUP BY o.estado"""
            rows = self.db.fetch_all(q_est, (fi, ff))
            estados = [{'estado': r[0] or 'SIN ESTADO', 'num_ordenes': int(r[1]), 'unidades': int(r[2])} for r in rows or []]
            return {'total_ordenes': total_ordenes, 'total_unidades': total_unidades, 'coste_total': coste_total, 'estados': estados}
        except Exception:
            logging.exception('Error en get_resumen_produccion')
            return {'total_ordenes': 0, 'total_unidades': 0, 'coste_total': 0, 'estados': []}

    # ── 2. PRODUCCIÓN POR TIPO ───────────────────────────────────────────────

    def get_produccion_por_tipo(self, fecha_inicio: str, fecha_fin: str) -> list:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            query = """SELECT l.tipo_producto, COALESCE(SUM(l.cantidad), 0), COALESCE(SUM(l.coste_total), 0), COUNT(DISTINCT l.orden_id)
                       FROM produccion_lineas l
                       JOIN produccion_ordenes o ON o.id = l.orden_id
                       WHERE o.fecha_hora BETWEEN ? AND ?
                       GROUP BY l.tipo_producto ORDER BY SUM(l.cantidad) DESC"""
            rows = self.db.fetch_all(query, (fi, ff))
            return [{'tipo': r[0] or 'SIN TIPO', 'unidades': int(r[1]), 'coste_total': int(r[2]), 'num_ordenes': int(r[3])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_produccion_por_tipo')
            return []

    # ── 3. PRODUCCIÓN POR DISEÑO ─────────────────────────────────────────────

    def get_produccion_por_diseno(self, fecha_inicio: str, fecha_fin: str) -> list:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            query = """SELECT l.diseno_codigo, COALESCE(d.nombre, l.diseno_codigo),
                        COALESCE(d.coleccion, '-'), COALESCE(SUM(l.cantidad), 0), COALESCE(SUM(l.coste_total), 0)
                       FROM produccion_lineas l
                       JOIN produccion_ordenes o ON o.id = l.orden_id
                       LEFT JOIN produccion_disenos d ON d.codigo = l.diseno_codigo
                       WHERE o.fecha_hora BETWEEN ? AND ?
                       GROUP BY l.diseno_codigo ORDER BY SUM(l.cantidad) DESC"""
            rows = self.db.fetch_all(query, (fi, ff))
            return [{'diseno_codigo': r[0] or '', 'diseno_nombre': r[1] or '', 'coleccion': r[2] or '-',
                     'unidades': int(r[3]), 'coste_total': int(r[4])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_produccion_por_diseno')
            return []

    # ── 4. PRODUCCIÓN POR COLECCIÓN ──────────────────────────────────────────

    def get_produccion_por_coleccion(self, fecha_inicio: str, fecha_fin: str) -> list:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            query = """SELECT COALESCE(d.coleccion, 'SIN COLECCIÓN'),
                        COALESCE(SUM(l.cantidad), 0), COALESCE(SUM(l.coste_total), 0), COUNT(DISTINCT l.diseno_codigo)
                       FROM produccion_lineas l
                       JOIN produccion_ordenes o ON o.id = l.orden_id
                       LEFT JOIN produccion_disenos d ON d.codigo = l.diseno_codigo
                       WHERE o.fecha_hora BETWEEN ? AND ?
                       GROUP BY d.coleccion ORDER BY SUM(l.cantidad) DESC"""
            rows = self.db.fetch_all(query, (fi, ff))
            return [{'coleccion': r[0] or 'SIN COLECCIÓN', 'unidades': int(r[1]),
                     'coste_total': int(r[2]), 'num_disenos': int(r[3])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_produccion_por_coleccion')
            return []

    # ── 5. STOCK POR TIPO ────────────────────────────────────────────────────

    def get_stock_por_tipo(self) -> list:
        try:
            query = """SELECT t.nombre, COALESCE(SUM(s.cantidad), 0),
                        COALESCE(SUM(s.cantidad * s.coste_medio), 0), COUNT(*)
                       FROM produccion_stock_colores_tallas s
                       JOIN tipos t ON t.id = s.tipo_id
                       GROUP BY s.tipo_id ORDER BY t.nombre ASC"""
            rows = self.db.fetch_all(query)
            return [{'tipo_nombre': r[0] or '', 'total_unidades': int(r[1]),
                     'valor_stock': int(r[2]), 'num_referencias': int(r[3])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_stock_por_tipo')
            return []

    # ── 6. STOCK POR VARIANTE ────────────────────────────────────────────────

    def get_stock_por_variante(self) -> list:
        try:
            query = """SELECT t.nombre, COALESCE(v.nombre, 'SIN VARIANTE'),
                        COALESCE(SUM(s.cantidad), 0), COALESCE(SUM(s.cantidad * s.coste_medio), 0), COUNT(*)
                       FROM produccion_stock_colores_tallas s
                       JOIN tipos t ON t.id = s.tipo_id
                       LEFT JOIN tipos_variantes v ON v.tipo_id = s.tipo_id
                       GROUP BY t.id, v.id
                       ORDER BY t.nombre ASC, v.nombre ASC"""
            rows = self.db.fetch_all(query)
            return [{'tipo_nombre': r[0] or '', 'variante_nombre': r[1] or 'SIN VARIANTE',
                     'total_unidades': int(r[2]), 'valor_stock': int(r[3]),
                     'num_referencias': int(r[4])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_stock_por_variante')
            return []

    # ── 7. VENTAS DE DISEÑOS ─────────────────────────────────────────────────

    def get_ventas_disenos(self, fecha_inicio: str, fecha_fin: str) -> list:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            query = """SELECT dv.diseno_codigo, COALESCE(d.nombre, dv.diseno_codigo),
                        COALESCE(d.coleccion, '-'), COALESCE(SUM(dv.cantidad), 0),
                        COALESCE(SUM(tk.total), 0)
                       FROM produccion_disenos_ventas dv
                       JOIN tickets tk ON tk.id = dv.ticket_id
                       LEFT JOIN produccion_disenos d ON d.codigo = dv.diseno_codigo
                       WHERE dv.fecha_venta BETWEEN ? AND ?
                       GROUP BY dv.diseno_codigo ORDER BY SUM(dv.cantidad) DESC"""
            rows = self.db.fetch_all(query, (fi, ff))
            return [{'diseno_codigo': r[0] or '', 'diseno_nombre': r[1] or '', 'coleccion': r[2] or '-',
                     'unidades_vendidas': int(r[3]), 'total_ventas': int(r[4])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_ventas_disenos')
            return []
