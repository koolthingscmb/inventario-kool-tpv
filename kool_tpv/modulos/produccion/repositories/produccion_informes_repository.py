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
            query = """SELECT t.nombre, COALESCE(SUM(l.cantidad), 0), COALESCE(SUM(l.coste_total), 0), COUNT(DISTINCT l.orden_id)
                       FROM produccion_lineas l
                       JOIN produccion_ordenes o ON o.id = l.orden_id
                       JOIN tipos t ON t.id = l.tipo_id
                       WHERE o.fecha_hora BETWEEN ? AND ?
                       GROUP BY l.tipo_id ORDER BY SUM(l.cantidad) DESC"""
            rows = self.db.fetch_all(query, (fi, ff))
            return [{'tipo': r[0] or 'SIN TIPO', 'unidades': int(r[1]), 'coste_total': int(r[2]), 'num_ordenes': int(r[3])} for r in rows or []]
        except Exception:
            logging.exception('Error en get_produccion_por_tipo')
            return []

    # ── 3. PRODUCCIÓN DETALLADA DE DISEÑOS ───────────────────────────────────

    def get_produccion_detallada_disenos(self, fecha_inicio: str, fecha_fin: str, 
                                        coleccion_ids: list = None, 
                                        sufijo_ids: list = None) -> list:
        try:
            fi = f"{fecha_inicio} 00:00:00"
            ff = f"{fecha_fin} 23:59:59"
            
            query = """SELECT 
                        l.diseno_codigo, 
                        COALESCE(d.nombre, l.diseno_codigo) as diseno_nombre,
                        COALESCE(c.nombre, 'SIN COL.') as coleccion,
                        COALESCE(s.nombre, '-') as sufijo,
                        l.tipo_id,
                        t.nombre as tipo_nombre,
                        COALESCE(v.nombre, '-') as variante,
                        COALESCE(l.talla, '-') as talla,
                        COALESCE(col.nombre, '-') as color,
                        COALESCE(m.nombre, '-') as metodo,
                        SUM(l.cantidad) as unidades,
                        SUM(l.coste_total) as coste_total
                       FROM produccion_lineas l
                       JOIN produccion_ordenes o ON o.id = l.orden_id
                       JOIN tipos t ON t.id = l.tipo_id
                       LEFT JOIN produccion_disenos d ON d.codigo = l.diseno_codigo
                       LEFT JOIN produccion_colecciones c ON c.id = d.coleccion_id
                       LEFT JOIN produccion_sufijos s ON s.id = d.sufijo_id
                       LEFT JOIN tipos_variantes v ON v.id = l.variante_id
                       LEFT JOIN produccion_colores col ON col.id = l.color_id
                       LEFT JOIN produccion_metodos m ON m.id = l.metodo_id
                       WHERE o.fecha_hora BETWEEN ? AND ?
                    """
            params = [fi, ff]
            
            if coleccion_ids:
                placeholders = ",".join(["?"] * len(coleccion_ids))
                query += f" AND d.coleccion_id IN ({placeholders})"
                params.extend(coleccion_ids)
                
            if sufijo_ids:
                placeholders = ",".join(["?"] * len(sufijo_ids))
                query += f" AND d.sufijo_id IN ({placeholders})"
                params.extend(sufijo_ids)
                
            query += """ GROUP BY l.diseno_codigo, l.variante_id, l.talla, l.color_id, l.metodo_id 
                         ORDER BY c.nombre, d.nombre, l.cantidad DESC"""
            
            rows = self.db.fetch_all(query, tuple(params))
            return [{
                'diseno_codigo': r[0],
                'diseno_nombre': r[1],
                'coleccion': r[2],
                'sufijo': r[3],
                'tipo_id': r[4],
                'tipo_nombre': r[5],
                'variante': r[6],
                'talla': r[7],
                'color': r[8],
                'metodo': r[9],
                'unidades': int(r[10]),
                'coste_total': int(r[11])
            } for r in rows or []]
        except Exception:
            logging.exception('Error en get_produccion_detallada_disenos')
            return []
