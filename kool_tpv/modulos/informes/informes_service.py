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

    def get_resumen_ventas_por_rango(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen agregado de ventas entre fechas."""
        raw = self.repo.get_resumen_ventas(fecha_inicio, fecha_fin)
        total_tickets = raw["total_tickets"]
        total_ventas = raw["total_ventas"]
        total_base = raw["total_base"]
        total_iva = total_ventas - total_base
        ticket_medio = total_ventas / total_tickets if total_tickets > 0 else 0.0
        return {
            "total_tickets": total_tickets,
            "total_ventas": total_ventas,
            "total_base": total_base,
            "total_iva": total_iva,
            "ticket_medio": ticket_medio,
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
            }

        from datetime import datetime

        # Construir items para justified_list
        # Estructura: Total Tickets, Base, IVA, TOTAL, Ticket Medio (separado al final)
        items = [
            {"nombre": "Total Tickets", "tickets": 0, "uds": resumen.get("total_tickets", 0), "euros": 0.0},
            {"nombre": "Base Imponible", "tickets": 0, "uds": 0, "euros": resumen.get("total_base", 0.0)},
            {"nombre": "Total IVA", "tickets": 0, "uds": 0, "euros": resumen.get("total_iva", 0.0)},
            {"nombre": "TOTAL", "tickets": 0, "uds": resumen.get("total_tickets", 0), "euros": resumen.get("total_ventas", 0.0)},
            {"nombre": "---SEPARADOR---", "tickets": 0, "uds": 0, "euros": 0.0},  # Marcador para saltos
            {"nombre": "Ticket Medio", "tickets": 0, "uds": 0, "euros": resumen.get("ticket_medio", 0.0)},
        ]

        return {
            "title": "INFORME RESUMEN DE VENTAS",
            "display_format": "justified_list",
            "generated_at": datetime.now().isoformat(),
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
        for item in ventas_diarias or []:
            fecha = item.get("fecha", "")
            total = item.get("total", 0.0)
            num_tickets = item.get("num_tickets", 0)
            total_uds = item.get("total_uds", 0)
            items.append({
                "nombre": fecha,
                "tickets": num_tickets,
                "uds": total_uds,
                "euros": total,
            })

        return {
            "title": "INFORME DE VENTAS DIARIAS",
            "display_format": "justified_list",
            "display_subformat": "daily",
            "generated_at": datetime.now().isoformat(),
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

        from datetime import datetime

        return {
            "title": "INFORME DE VENTAS POR CAJERO",
            "display_format": "justified_list",
            "display_subformat": "cajero",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_categoria(self, fecha_inicio: str, fecha_fin: str, categorias: list = None) -> dict:
        """Informe de ventas agregadas por categoría."""
        ticket_ids = self.repo.get_ticket_ids_por_rango(fecha_inicio, fecha_fin)

        categoria_ids = categorias if categorias and isinstance(categorias, (list, tuple)) and len(categorias) > 0 else None
        resultados = self.repo.get_ventas_por_categoria(ticket_ids, categoria_ids=categoria_ids)

        items = []
        for nombre, num_tickets, uds, total_euros in resultados:
            items.append({
                "nombre": nombre,
                "tickets": num_tickets,
                "uds": uds,
                "euros": float(total_euros),
            })

        from datetime import datetime

        return {
            "title": "INFORME DE VENTAS POR CATEGORÍA",
            "display_format": "justified_list",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_tipo(self, fecha_inicio: str, fecha_fin: str, tipos: list = None) -> dict:
        """Informe de ventas agregadas por tipo de producto."""
        ticket_ids = self.repo.get_ticket_ids_por_rango(fecha_inicio, fecha_fin)

        tipo_ids = tipos if tipos and isinstance(tipos, (list, tuple)) and len(tipos) > 0 else None
        resultados = self.repo.get_ventas_por_tipo(ticket_ids, tipo_ids=tipo_ids)

        items = []
        for nombre, num_tickets, uds, total_euros in resultados:
            items.append({
                "nombre": nombre,
                "tickets": num_tickets,
                "uds": uds,
                "euros": float(total_euros),
            })

        from datetime import datetime

        return {
            "title": "INFORME DE VENTAS POR TIPO",
            "display_format": "justified_list",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

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

        from datetime import datetime
        return {
            "title": title,
            "generated_at": datetime.now().isoformat(),
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
