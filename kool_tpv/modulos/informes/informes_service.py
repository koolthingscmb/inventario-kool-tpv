"""Service layer for Informes.

Lógica de negocio y formateo de datos para informes.
Todas las queries están centralizadas en InformesRepository.
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import List, Optional

from kool_tpv.modulos.informes.informes_repository import InformesRepository


class InformesService:
    """Service para el módulo de Informes."""

    def __init__(self, db):
        self.db = db
        self.repo = InformesRepository(db)

    # Helper to ensure monetary precision: two decimal places, HALF_UP
    def _money(self, value):
        try:
            d = Decimal(str(value))
            return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except Exception:
            return 0.0

    def _money_from_db(self, value):
        """Convierte valor de BD (céntimos) a euros formateados."""
        try:
            d = Decimal(str(value)) / Decimal('100')
            return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except Exception:
            return 0.0

    def _ahora_formateado(self) -> str:
        """Fecha y hora actual formateada para mostrar."""
        from datetime import datetime
        return datetime.now().strftime('%d/%m/%Y %H:%M')

    def get_resumen_ventas_por_rango(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen agregado de ventas entre fechas."""
        raw = self.repo.get_resumen_ventas(fecha_inicio, fecha_fin)
        total_tickets = raw["total_tickets"]
        total_ventas = raw["total_ventas"]
        total_base = raw["total_base"]
        total_iva = total_ventas - total_base
        ticket_medio = total_ventas / total_tickets if total_tickets > 0 else 0.0
        num_devoluciones = raw.get("num_devoluciones", 0)
        total_devoluciones = raw.get("total_devoluciones", 0.0)
        return {
            "total_tickets": total_tickets,
            "total_ventas": total_ventas,
            "total_base": total_base,
            "total_iva": total_iva,
            "ticket_medio": ticket_medio,
            "num_devoluciones": num_devoluciones,
            "total_devoluciones": total_devoluciones,
        }

    def get_ventas_diarias_por_rango(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas agregadas por día dentro del rango."""
        return self.repo.get_ventas_diarias(fecha_inicio, fecha_fin)

    def get_informe_resumen_ventas(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen agregado de ventas entre fechas."""
        try:
            resumen = self.get_resumen_ventas_por_rango(fecha_inicio, fecha_fin)
        except Exception:
            resumen = {
                "total_tickets": 0,
                "total_ventas": 0.0,
                "total_base": 0.0,
                "total_iva": 0.0,
                "ticket_medio": 0.0,
                "num_devoluciones": 0,
                "total_devoluciones": 0.0,
            }

        from datetime import datetime

        # Construir items para justified_list
        # Estructura: Total Tickets, Base, IVA, TOTAL, Ticket Medio, Devoluciones (info)
        items = [
            {"nombre": "Total Tickets", "tickets": 0, "uds": resumen.get("total_tickets", 0), "euros": 0.0},
            {"nombre": "Base Imponible", "tickets": 0, "uds": 0, "euros": resumen.get("total_base", 0.0)},
            {"nombre": "Total IVA", "tickets": 0, "uds": 0, "euros": resumen.get("total_iva", 0.0)},
            {"nombre": "TOTAL", "tickets": 0, "uds": resumen.get("total_tickets", 0), "euros": resumen.get("total_ventas", 0.0)},
            {"nombre": "Ticket Medio", "tickets": 0, "uds": 0, "euros": resumen.get("ticket_medio", 0.0), "tipo": "destacado"},
        ]
        # Devoluciones como información al final (no afecta a totales)
        num_dev = resumen.get("num_devoluciones", 0)
        if num_dev and num_dev > 0:
            items.append({
                "nombre": f"Devoluciones ({num_dev})",
                "tickets": 0, "uds": 0,
                "euros": resumen.get("total_devoluciones", 0.0),
                "tipo": "info",
            })

        return {
            "title": "INFORME RESUMEN DE VENTAS",
            "display_format": "justified_list",
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_diarias(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Ventas agregadas por día dentro del rango."""
        try:
            ventas_diarias = self.get_ventas_diarias_por_rango(fecha_inicio, fecha_fin)
        except Exception:
            ventas_diarias = []

        from datetime import datetime

        items = []
        total_tickets = 0
        total_uds = 0
        total_euros = 0.0
        for item in ventas_diarias or []:
            fecha = item.get("fecha", "")
            total = item.get("total", 0.0)
            num_tickets = item.get("num_tickets", 0)
            total_uds_dia = item.get("total_uds", 0)
            items.append({
                "nombre": fecha,
                "tickets": num_tickets,
                "uds": total_uds_dia,
                "euros": total,
            })
            total_tickets += num_tickets
            total_uds += total_uds_dia
            total_euros += total

        # Línea TOTAL TICKETS
        items.append({
            "nombre": f"TOTAL TICKETS ({total_tickets})",
            "tickets": total_tickets,
            "uds": total_uds,
            "euros": total_euros,
            "tipo": "total_global",
        })

        # Línea TOTAL DEVOLUCIONES (informativa, no afecta a totales)
        try:
            devol = self.repo.get_devoluciones_resumen(fecha_inicio, fecha_fin)
        except Exception:
            devol = {"num_tickets": 0, "total_uds": 0, "total": 0.0}
        if devol["num_tickets"] > 0:
            items.append({
                "nombre": f"TOTAL DEVOLUCIONES ({devol['num_tickets']})",
                "tickets": devol["num_tickets"],
                "uds": devol["total_uds"],
                "euros": devol["total"],
                "tipo": "info",
            })

        return {
            "title": "INFORME DE VENTAS DIARIAS",
            "display_format": "justified_list",
            "display_subformat": "daily",
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_cajero(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Construye informe de ventas agrupado por cajero y día."""
        resultados = self.repo.get_ventas_por_cajero_y_dia(fecha_inicio, fecha_fin)

        # Agrupar por cajero para insertar subtotales
        por_cajero = defaultdict(list)
        for r in resultados:
            por_cajero[r["cajero"]].append(r)

        items = []
        for cajero, filas in por_cajero.items():
            total_tickets_cajero = 0
            total_uds_cajero = 0
            total_euros_cajero = 0.0
            for fila in filas:
                items.append({
                    "nombre": cajero,
                    "fecha": fila["fecha"],
                    "tickets": fila["num_tickets"],
                    "uds": fila["total_uds"],
                    "euros": fila["total"],
                    "tipo": "linea_cajero",
                })
                total_tickets_cajero += fila["num_tickets"]
                total_uds_cajero += fila["total_uds"]
                total_euros_cajero += fila["total"]
            items.append({
                "nombre": cajero,
                "tickets": total_tickets_cajero,
                "uds": total_uds_cajero,
                "euros": total_euros_cajero,
                "tipo": "subtotal_cajero",
            })

        return {
            "title": "INFORME DE VENTAS POR CAJERO",
            "display_format": "justified_list",
            "display_subformat": "cajero",
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def _build_ventas_por_grupo(self, fecha_inicio: str, fecha_fin: str,
                                group_by: str, filter_ids, title: str,
                                subformat: str, total_label: str) -> dict:
        """Helper genérico para informes de ventas por categoría o tipo con desglose por día."""
        filter_ids_clean = filter_ids if filter_ids and isinstance(filter_ids, (list, tuple)) and len(filter_ids) > 0 else None
        resultados = self.repo.get_ventas_por_grupo_y_dia(fecha_inicio, fecha_fin, group_by, filter_ids_clean)

        # Agrupar por grupo para insertar subtotales
        por_grupo = defaultdict(list)
        for r in resultados:
            por_grupo[r["group_name"]].append(r)

        items = []
        total_uds_global = 0
        total_euros_global = 0.0

        for group_name, filas in por_grupo.items():
            total_tickets_grupo = 0
            total_uds_grupo = 0
            total_euros_grupo = 0.0
            for fila in filas:
                items.append({
                    "nombre": group_name,
                    "fecha": fila["fecha"],
                    "tickets": fila["num_tickets"],
                    "uds": fila["total_uds"],
                    "euros": fila["total"],
                    "tipo": "linea_grupo",
                })
                total_tickets_grupo += fila["num_tickets"]
                total_uds_grupo += fila["total_uds"]
                total_euros_grupo += fila["total"]
            items.append({
                "nombre": group_name,
                "tickets": total_tickets_grupo,
                "uds": total_uds_grupo,
                "euros": total_euros_grupo,
                "tipo": "subtotal_grupo",
            })
            total_uds_global += total_uds_grupo
            total_euros_global += total_euros_grupo

        # Total global de tickets: COUNT(DISTINCT) real, no suma de subtotales
        total_tickets_global = self.repo.count_distinct_tickets_ventas(
            fecha_inicio, fecha_fin, group_by=group_by, filter_ids=filter_ids_clean
        )

        # Item de total global
        items.append({
            "nombre": total_label,
            "tickets": total_tickets_global,
            "uds": total_uds_global,
            "euros": total_euros_global,
            "tipo": "total_global",
        })

        return {
            "title": title,
            "display_format": "justified_list",
            "display_subformat": subformat,
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_producto(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Informe de ventas por producto desglosado por día."""
        resultados = self.repo.get_ventas_por_producto_y_dia(fecha_inicio, fecha_fin)

        por_producto = defaultdict(list)
        for r in resultados:
            por_producto[r["group_name"]].append(r)

        items = []
        total_uds_global = 0
        total_euros_global = 0.0

        for product_name, filas in por_producto.items():
            total_tickets_p = 0
            total_uds_p = 0
            total_euros_p = 0.0
            for fila in filas:
                items.append({
                    "nombre": product_name,
                    "fecha": fila["fecha"],
                    "tickets": fila["num_tickets"],
                    "uds": fila["total_uds"],
                    "euros": fila["total"],
                    "tipo": "linea_grupo",
                })
                total_tickets_p += fila["num_tickets"]
                total_uds_p += fila["total_uds"]
                total_euros_p += fila["total"]
            items.append({
                "nombre": product_name,
                "tickets": total_tickets_p,
                "uds": total_uds_p,
                "euros": total_euros_p,
                "tipo": "subtotal_grupo",
            })
            total_uds_global += total_uds_p
            total_euros_global += total_euros_p

        # Total global de tickets: COUNT(DISTINCT) real, no suma de subtotales
        total_tickets_global = self.repo.count_distinct_tickets_ventas(
            fecha_inicio, fecha_fin
        )

        items.append({
            "nombre": "TOTAL",
            "tickets": total_tickets_global,
            "uds": total_uds_global,
            "euros": total_euros_global,
            "tipo": "total_global",
        })

        return {
            "title": "INFORME DE VENTAS POR PRODUCTO",
            "display_format": "justified_list",
            "display_subformat": "producto",
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_categoria(self, fecha_inicio: str, fecha_fin: str, categorias: list = None) -> dict:
        """Informe de ventas por categoría desglosado por día."""
        return self._build_ventas_por_grupo(
            fecha_inicio, fecha_fin,
            group_by='categoria',
            filter_ids=categorias,
            title='INFORME DE VENTAS POR CATEGORÍA',
            subformat='categoria',
            total_label='TOTAL',
        )

    def get_informe_ventas_por_tipo(self, fecha_inicio: str, fecha_fin: str, tipos: list = None) -> dict:
        """Informe de ventas por tipo desglosado por día."""
        return self._build_ventas_por_grupo(
            fecha_inicio, fecha_fin,
            group_by='tipo',
            filter_ids=tipos,
            title='INFORME DE VENTAS POR TIPO',
            subformat='tipo',
            total_label='TOTAL',
        )

    def buscar_categorias_dinamico(self, texto: str):
        """Búsqueda dinámica de categorías para widgets de tipo TagSelector.

        Retorna lista de dicts: [{'id': int, 'nombre_display': str}, ...]
        """
        try:
            pattern = f"%{texto}%"
            query = "SELECT id, nombre as nombre_display FROM categorias WHERE nombre LIKE ? ORDER BY nombre ASC"
            rows = self.db.fetch_all(query, (pattern,))
        except Exception:
            rows = None

        results = []
        if not rows:
            return results

        for r in rows:
            try:
                if hasattr(r, 'keys') and 'id' in r.keys():
                    results.append({'id': r['id'], 'nombre_display': r['nombre_display']})
                else:
                    results.append({'id': r[0], 'nombre_display': r[1]})
            except Exception:
                continue

        return results

    def buscar_tipos_dinamico(self, texto: str):
        """Búsqueda dinámica de tipos para widgets de tipo TagSelector.

        Retorna lista de dicts: [{'id': int, 'nombre_display': str}, ...]
        """
        try:
            pattern = f"%{texto}%"
            query = "SELECT id, nombre as nombre_display FROM tipos WHERE nombre LIKE ? ORDER BY nombre ASC"
            rows = self.db.fetch_all(query, (pattern,))
        except Exception:
            rows = None

        results = []
        if not rows:
            return results

        for r in rows:
            try:
                if hasattr(r, 'keys') and 'id' in r.keys():
                    results.append({'id': r['id'], 'nombre_display': r['nombre_display']})
                else:
                    results.append({'id': r[0], 'nombre_display': r[1]})
            except Exception:
                continue

        return results

    def _build_stock_report(self, group_by: str, filter_ids: list, title: str,
                            section_title: str, fallback_name: str,
                            export_headers: list) -> dict:
        """Helper genérico para informes de stock agrupados."""
        rows = self.repo.get_stock_por_grupo(group_by, filter_ids if filter_ids else None)

        agrupado = defaultdict(list)
        export_rows = []

        for r in rows:
            group_name = r['group_name']
            agrupado[group_name].append(r)
            export_rows.append([group_name, r['sku'], r['nombre'], r['stock_actual'], r['stock_minimo'], r['coste']])

        blocks = []
        for gname, productos in agrupado.items():
            fields = []
            for p in productos:
                label = f"{p['sku']} - {p['nombre']}"
                value = f"Stock: {p['stock_actual']} - Min: {p['stock_minimo']} - Coste: {p['coste']}"
                fields.append({"label": label, "value": value, "is_money": False})
            blocks.append({"title": gname, "fields": fields})

        return {
            "title": title,
            "generated_at": self._ahora_formateado(),
            "range": None,
            "sections": [
                {
                    "type": "blocks",
                    "title": section_title,
                    "blocks": blocks,
                    "export_table": {
                        "headers": export_headers,
                        "money_columns": [5],
                        "rows": export_rows,
                    }
                }
            ],
        }

    def get_informe_stock_por_categoria(self, categoria_ids: List[int] = None) -> dict:
        """Informe de stock filtrable por categorías."""
        return self._build_stock_report(
            group_by='categoria',
            filter_ids=categoria_ids,
            title='Informe de Stock por Categoría',
            section_title='Stock por Categoría',
            fallback_name='Sin categoría',
            export_headers=['Categoría', 'SKU', 'Nombre', 'Stock actual', 'Stock mínimo', 'Precio coste'],
        )

    def get_informe_stock_por_tipo(self, tipo_ids: List[int] = None) -> dict:
        """Informe de stock filtrable por tipos."""
        return self._build_stock_report(
            group_by='tipo',
            filter_ids=tipo_ids,
            title='Informe de Stock por Tipo',
            section_title='Stock por Tipo',
            fallback_name='Sin tipo',
            export_headers=['Tipo', 'SKU', 'Nombre', 'Stock actual', 'Stock mínimo', 'Precio coste'],
        )

    # ── PRESENCIA ─────────────────────────────────────────────────────────────

    def buscar_usuarios_dinamico(self, texto: str):
        """Búsqueda dinámica de usuarios para el TagSelector."""
        try:
            pattern = f"%{texto}%"
            query = "SELECT id, nombre as nombre_display FROM usuarios WHERE nombre LIKE ? ORDER BY nombre ASC"
            rows = self.db.fetch_all(query, (pattern,))
            return [{"id": r[0], "nombre_display": r[1]} for r in (rows or [])]
        except Exception:
            logging.exception('Error buscando usuarios para informes')
            return []

    def get_informe_presencia(self, fecha_inicio: str, fecha_fin: str, usuario_ids: List[int] = None) -> dict:
        """Genera el informe de presencia en formato de lista justificada."""
        rows = self.repo.get_presencia_informe(fecha_inicio, fecha_fin, usuario_ids)
        
        items = []
        total_minutos = 0
        
        for r in rows:
            dur = r['duracion_minutos'] or 0
            total_minutos += dur
            
            # Formatear duración
            if dur < 60: dur_str = f"{dur} min"
            else: dur_str = f"{dur // 60}h {dur % 60}m"
            
            # Limpiar timestamps
            t_in = r['entrada'].split()[1][:5] if ' ' in r['entrada'] else r['entrada']
            t_out = r['salida'].split()[1][:5] if r['salida'] and ' ' in r['salida'] else '...'
            
            items.append({
                "usuario": r['usuario'],
                "fecha": r['entrada'].split()[0],
                "entrada": t_in,
                "salida": t_out,
                "duracion": dur_str,
                "estado": r['estado'].upper(),
                "notas": r['notas']
            })
            
        # Resumen final
        h = total_minutos // 60
        m = total_minutos % 60
        total_str = f"{h}h {m}m"

        # Nombre del usuario si hay filtro de uno solo
        usuario_header = "TODOS"
        if usuario_ids and len(usuario_ids) == 1 and items:
            usuario_header = items[0]['usuario']
        elif usuario_ids and len(usuario_ids) > 1:
            usuario_header = "VARIOS"

        return {
            "title": "INFORME DE CONTROL DE PRESENCIA",
            "display_format": "justified_list",
            "display_subformat": "presencia",
            "generated_at": self._ahora_formateado(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "usuario_header": usuario_header,
            "total_registros": len(rows),
            "total_tiempo": total_str,
            "items": items
        }
