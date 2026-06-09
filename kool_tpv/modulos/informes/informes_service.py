"""Service layer scaffold for Informes.

Prepared for future database queries and business logic related to reports.
"""

from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import List, Optional

from kool_tpv.modulos.almacen.tipo_repository import TipoRepository
from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository
from kool_tpv.modulos.ticket.ticket_repository import TicketRepository
from kool_tpv.base_datos.money_adapter import read_from_db


class InformesService:
    """Placeholder service for Informes module.

    Constructor receives a `db` parameter (database wrapper/connection) and
    stores it for future use. No methods implemented yet.
    """

    def __init__(self, db):
        self.db = db

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
        repo = TicketRepository(self.db)
        raw = repo.get_resumen_ventas_por_rango(fecha_inicio, fecha_fin)
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
        repo = TicketRepository(self.db)
        return repo.get_ventas_diarias_por_rango(fecha_inicio, fecha_fin)

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
        items = [
            {"nombre": "Total Tickets", "tickets": resumen.get("total_tickets", 0), "uds": resumen.get("total_tickets", 0), "euros": resumen.get("total_ventas", 0.0)},
            {"nombre": "Base Imponible", "tickets": 0, "uds": 0, "euros": resumen.get("total_base", 0.0)},
            {"nombre": "Total IVA", "tickets": 0, "uds": 0, "euros": resumen.get("total_iva", 0.0)},
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
            items.append({
                "nombre": fecha,
                "tickets": 1,
                "uds": 1,
                "euros": total,
            })

        return {
            "title": "INFORME DE VENTAS DIARIAS",
            "display_format": "justified_list",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_cajero(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Construye informe de ventas agrupado por cajero."""
        repo = TicketRepository(self.db)
        resultados = repo.get_ventas_por_cajero(fecha_inicio, fecha_fin)

        items = []
        for cajero, num_tickets, total_ventas in resultados:
            items.append({
                "nombre": cajero,
                "tickets": num_tickets,
                "uds": num_tickets,
                "euros": total_ventas,
            })

        from datetime import datetime

        return {
            "title": "INFORME DE VENTAS POR CAJERO",
            "display_format": "justified_list",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "items": items,
        }

    def get_informe_ventas_por_categoria(self, fecha_inicio: str, fecha_fin: str, categorias: list = None) -> dict:
        """Informe de ventas agregadas por categoría."""
        ticket_repo = TicketRepository(self.db)
        ticket_ids = ticket_repo.get_ticket_ids_by_date_range(fecha_inicio, fecha_fin)

        cat_repo = CategoriaRepository(self.db)
        categoria_ids = categorias if categorias and isinstance(categorias, (list, tuple)) and len(categorias) > 0 else None
        resultados = cat_repo.get_ventas_por_categoria(ticket_ids, line_tipo='venta', categoria_ids=categoria_ids)

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
        ticket_repo = TicketRepository(self.db)
        ticket_ids = ticket_repo.get_ticket_ids_by_date_range(fecha_inicio, fecha_fin)

        tipo_repo = TipoRepository(self.db)
        tipo_ids = tipos if tipos and isinstance(tipos, (list, tuple)) and len(tipos) > 0 else None
        resultados = tipo_repo.get_ventas_por_tipo(ticket_ids, line_tipo='venta', tipo_ids=tipo_ids)

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
        join_table = 'categorias' if group_by == 'categoria' else 'tipos'
        alias = 'c' if group_by == 'categoria' else 't'
        id_col = 'p.categoria' if group_by == 'categoria' else 'p.tipo'
        name_col = f"{alias}.nombre as {group_by}"
        order_by = f"{alias}.nombre, p.nombre"

        query = (
            f"SELECT p.sku, p.nombre, {name_col}, "
            f"p.stock_actual, p.stock_minimo, COALESCE(pr.coste, 0) as precio_coste "
            f"FROM productos p "
            f"LEFT JOIN {join_table} {alias} ON {id_col} = {alias}.id "
            f"LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1 "
            f"WHERE p.activo = 1"
        )

        params = []
        if filter_ids and isinstance(filter_ids, (list, tuple)) and len(filter_ids) > 0:
            placeholders = ','.join(['?'] * len(filter_ids))
            query += f" AND {id_col} IN ({placeholders})"
            params.extend(filter_ids)

        query += f" ORDER BY {order_by}"

        rows = self.db.fetch_all(query, tuple(params) if params else ())

        from collections import defaultdict
        agrupado = defaultdict(list)
        export_rows = []

        for r in rows or []:
            sku, nombre, group_name, stock_actual, stock_minimo, precio_coste = r
            group_name = group_name or fallback_name
            coste_fmt = float(read_from_db(precio_coste or 0))

            agrupado[group_name].append({
                'sku': sku, 'nombre': nombre,
                'stock_actual': stock_actual, 'stock_minimo': stock_minimo,
                'coste': coste_fmt,
            })
            export_rows.append([group_name, sku, nombre, stock_actual, stock_minimo, coste_fmt])

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
