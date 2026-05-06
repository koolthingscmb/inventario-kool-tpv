"""Service layer scaffold for Informes.

Prepared for future database queries and business logic related to reports.
"""

from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import List, Optional


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
        """
        Devuelve resumen agregado de ventas entre fechas (incluidas).
        Excluye tickets con total <= 0.

        Args:
            fecha_inicio: fecha inicio en formato 'YYYY-MM-DD'
            fecha_fin: fecha fin en formato 'YYYY-MM-DD'

        Returns:
            dict con claves: total_tickets (int), total_ventas (float),
            total_base (float), total_iva (float), ticket_medio (float)
        """
        # Construir rango completo
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = (
            "SELECT\n"
            "    COUNT(*) as total_tickets,\n"
            "    COALESCE(SUM(total), 0) as total_ventas,\n"
            "    COALESCE(SUM(subtotal), 0) as total_base\n"
            "FROM tickets\n"
            "WHERE created_at BETWEEN ? AND ?\n"
            "  AND total > 0"
        )

        row = None
        try:
            row = self.db.fetch_one(query, (fecha_inicio_sql, fecha_fin_sql))
        except Exception:
            # Let exceptions propagate in general use; but ensure we return a valid structure
            row = None

        # Manejar None y valores nulos
        if not row:
            total_tickets = 0
            total_ventas = 0.0
            total_base = 0.0
        else:
            # sqlite3.Row permite acceso por nombre o por índice
            try:
                total_tickets = int(row["total_tickets"] if "total_tickets" in row.keys() else row[0])
            except Exception:
                try:
                    total_tickets = int(row[0] or 0)
                except Exception:
                    total_tickets = 0

            try:
                total_ventas = self._money_from_db(row["total_ventas"] if "total_ventas" in row.keys() else row[1])
            except Exception:
                try:
                    total_ventas = self._money_from_db(row[1] or 0)
                except Exception:
                    total_ventas = 0.0

            try:
                total_base = self._money_from_db(row["total_base"] if "total_base" in row.keys() else row[2])
            except Exception:
                try:
                    total_base = self._money_from_db(row[2] or 0)
                except Exception:
                    total_base = 0.0

        # Cálculos derivados
        total_iva = total_ventas - total_base
        if total_tickets and total_tickets > 0:
            try:
                ticket_medio = total_ventas / total_tickets
            except Exception:
                ticket_medio = 0.0
        else:
            ticket_medio = 0.0

        return {
            "total_tickets": int(total_tickets),
            "total_ventas": float(total_ventas),
            "total_base": float(total_base),
            "total_iva": float(total_iva),
            "ticket_medio": float(ticket_medio),
        }

    def get_ventas_diarias_por_rango(self, fecha_inicio: str, fecha_fin: str) -> list:
        """
        Devuelve lista de ventas agregadas por día dentro del rango.
        Excluye tickets con total <= 0.

        Retorna:
            List[dict]: [{"fecha": "YYYY-MM-DD", "total": float}, ...]
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = (
            "SELECT\n"
            "  DATE(created_at) as fecha,\n"
            "  COALESCE(SUM(total), 0) as total_dia\n"
            "FROM tickets\n"
            "WHERE created_at BETWEEN ? AND ?\n"
            "  AND total > 0\n"
            "GROUP BY DATE(created_at)\n"
            "ORDER BY DATE(created_at) ASC"
        )

        try:
            rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        except Exception:
            rows = None

        result = []
        if not rows:
            return result

        for r in rows:
            try:
                # soportar sqlite3.Row y tuplas
                if hasattr(r, 'keys') and 'fecha' in r.keys():
                    fecha = r['fecha']
                    total = r['total_dia']
                else:
                    fecha = r[0]
                    total = r[1]
                # Normalizar tipos
                fecha_str = fecha if fecha is not None else ''
                try:
                    total_f = self._money_from_db(total or 0)
                except Exception:
                    total_f = 0.0

                result.append({"fecha": fecha_str, "total": total_f})
            except Exception:
                # ignorar filas mal formadas pero continuar
                continue

        return result

    def get_informe_ventas_por_rango(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Construye una estructura completa de informe de ventas para el rango.

        No formatea valores; devuelve datos "crudos" listos para serializar.
        """
        try:
            resumen = self.get_resumen_ventas_por_rango(fecha_inicio, fecha_fin)
        except Exception:
            logging = __import__('logging')
            logging.exception('Error obteniendo resumen para get_informe_ventas_por_rango')
            resumen = {
                "total_tickets": 0,
                "total_ventas": 0.0,
                "total_base": 0.0,
                "total_iva": 0.0,
                "ticket_medio": 0.0,
            }

        try:
            ventas_diarias = self.get_ventas_diarias_por_rango(fecha_inicio, fecha_fin)
        except Exception:
            logging = __import__('logging')
            logging.exception('Error obteniendo ventas_diarias para get_informe_ventas_por_rango')
            ventas_diarias = []

        from datetime import datetime

        # Apply monetary normalization to the resumen values (except total_tickets)
        try:
            resumen["total_ventas"] = self._money(resumen.get("total_ventas"))
        except Exception:
            resumen["total_ventas"] = 0.0
        try:
            resumen["total_base"] = self._money(resumen.get("total_base"))
        except Exception:
            resumen["total_base"] = 0.0
        try:
            resumen["total_iva"] = self._money(resumen.get("total_iva"))
        except Exception:
            resumen["total_iva"] = 0.0
        try:
            resumen["ticket_medio"] = self._money(resumen.get("ticket_medio"))
        except Exception:
            resumen["ticket_medio"] = 0.0

        informe = {
            "title": "Informe de Ventas",
            "generated_at": datetime.now().isoformat(),
            "range": {
                "start": fecha_inicio,
                "end": fecha_fin,
            },
            "sections": [
                {
                    "type": "summary",
                    "headers": [
                        "Total tickets",
                        "Total ventas",
                        "Base imponible",
                        "Total IVA",
                        "Ticket medio",
                    ],
                    "money_columns": [1, 2, 3, 4],
                    "rows": [[
                        resumen.get("total_tickets"),
                        resumen.get("total_ventas"),
                        resumen.get("total_base"),
                        resumen.get("total_iva"),
                        resumen.get("ticket_medio"),
                    ]],
                },
                {
                    "type": "table",
                    "title": "Ventas por día",
                    "headers": ["Fecha", "Total"],
                    "money_columns": [1],
                    "rows": [
                            [item.get("fecha"), self._money(item["total"]) ]
                            for item in (ventas_diarias or [])
                        ],
                },
            ],
        }

        return informe

    def get_informe_ventas_por_cajero(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Construye informe de ventas agrupado por cajero.

        Devuelve estructura genérica `report_data` con una sección tipo tabla.
        """
        # Construir rango completo
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = (
            "SELECT\n"
            "    cajero,\n"
            "    COUNT(*) as num_tickets,\n"
            "    COALESCE(SUM(total), 0) as total_ventas,\n"
            "    COALESCE(SUM(subtotal), 0) as total_base,\n"
            "    COALESCE(SUM(importe_efectivo), 0) as total_efectivo,\n"
            "    COALESCE(SUM(importe_tarjeta), 0) as total_tarjeta,\n"
            "    COALESCE(SUM(descuento_euros), 0) as total_descuentos\n"
            "FROM tickets\n"
            "WHERE created_at BETWEEN ? AND ?\n"
            "  AND total > 0\n"
            "GROUP BY cajero\n"
            "ORDER BY total_ventas DESC"
        )

        try:
            resultados = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        except Exception:
            resultados = None

        # Normalizar resultados a lista vacía si es necesario
        if not resultados:
            resultados = []

        blocks = []
        for r in resultados:
            try:
                # Leer campos soportando sqlite3.Row o tuplas
                if hasattr(r, 'keys') and 'cajero' in r.keys():
                    cajero = r['cajero']
                    num_tickets = int(r['num_tickets'] or 0)
                    total_ventas = self._money_from_db(r['total_ventas'] or 0)
                    total_base = self._money_from_db(r['total_base'] or 0)
                    total_efectivo = self._money_from_db(r['total_efectivo'] or 0)
                    total_tarjeta = self._money_from_db(r['total_tarjeta'] or 0)
                    total_descuentos = self._money_from_db(r['total_descuentos'] or 0)
                else:
                    cajero = r[0]
                    num_tickets = int(r[1] or 0)
                    total_ventas = self._money_from_db(r[2] or 0)
                    total_base = self._money_from_db(r[3] or 0)
                    total_efectivo = self._money_from_db(r[4] or 0)
                    total_tarjeta = self._money_from_db(r[5] or 0)
                    total_descuentos = self._money_from_db(r[6] or 0)

                total_iva = self._money(total_ventas - total_base)
                if num_tickets > 0:
                    try:
                        ticket_medio = self._money(total_ventas / num_tickets)
                    except Exception:
                        ticket_medio = 0.0
                else:
                    ticket_medio = 0.0

                # Construir block por cajero
                block = {
                    "title": cajero,
                    "fields": [
                        {"label": "Tickets", "value": num_tickets, "is_money": False},
                        {"label": "Total ventas", "value": self._money(total_ventas), "is_money": True},
                        {"label": "Base imponible", "value": self._money(total_base), "is_money": True},
                        {"label": "Total IVA", "value": total_iva, "is_money": True},
                        {"label": "Ticket medio", "value": ticket_medio, "is_money": True},
                        {"label": "Efectivo", "value": self._money(total_efectivo), "is_money": True},
                        {"label": "Tarjeta", "value": self._money(total_tarjeta), "is_money": True},
                        {"label": "Descuentos", "value": self._money(total_descuentos), "is_money": True},
                    ]
                }

                blocks.append(block)
            except Exception:
                # Ignorar filas mal formadas
                continue

        from datetime import datetime

        report_data = {
            "title": "Informe de Ventas por Cajero",
            "generated_at": datetime.now().isoformat(),
            "range": {
                "start": fecha_inicio,
                "end": fecha_fin
            },
            "sections": [
                {
                    "type": "blocks",
                    "title": "Ventas por Cajero",
                    "blocks": blocks
                }
            ]
        }

        return report_data

    def get_informe_ventas_por_categoria(self, fecha_inicio: str, fecha_fin: str, categorias: list = None) -> dict:
        """Informe de ventas agregadas por categoría.

        Devuelve una sección tipo `table` con columnas: Categoría, Tickets, Unidades, Total ventas.
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = [
            "SELECT",
            "    c.nombre as categoria,",
            "    COUNT(DISTINCT t.id) as num_tickets,",
            "    COALESCE(SUM(tl.cantidad), 0) as total_unidades,",
            "    COALESCE(SUM(tl.cantidad * tl.precio), 0) as total_ventas",
            "FROM tickets t",
            "JOIN ticket_lines tl ON t.id = tl.ticket_id",
            "JOIN productos p ON tl.producto_id = p.id",
            "JOIN categorias c ON p.categoria = c.id",
            "WHERE t.created_at BETWEEN ? AND ?",
            "  AND t.total > 0",
            "  AND tl.line_tipo = 'venta'",
        ]

        params = [fecha_inicio_sql, fecha_fin_sql]

        # Si se pasan categorías, aplicar filtro
        if categorias and isinstance(categorias, (list, tuple)) and len(categorias) > 0:
            placeholders = ','.join(['?'] * len(categorias))
            query.append(f"  AND p.categoria IN ({placeholders})")
            params.extend(categorias)

        query.extend([
            "GROUP BY c.nombre",
            "ORDER BY total_ventas DESC"
        ])

        full_query = "\n".join(query)

        try:
            resultados = self.db.fetch_all(full_query, tuple(params))
        except Exception:
            logging.exception('Error ejecutando consulta get_informe_ventas_por_categoria')
            resultados = None

        if not resultados:
            resultados = []

        rows = []
        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'categoria' in r.keys():
                    categoria = r['categoria']
                    num_tickets = int(r['num_tickets'] or 0)
                    total_unidades = int(r['total_unidades'] or 0)
                    total_ventas = float(r['total_ventas'] or 0.0)
                else:
                    categoria = r[0]
                    num_tickets = int(r[1] or 0)
                    total_unidades = int(r[2] or 0)
                    total_ventas = float(r[3] or 0.0)

                rows.append([
                    categoria,
                    num_tickets,
                    total_unidades,
                    self._money(total_ventas),
                ])
            except Exception:
                continue

        from datetime import datetime

        report_data = {
            "title": "Informe de Ventas por Categoría",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "sections": [
                {
                    "type": "table",
                    "title": "Ventas por Categoría",
                    "headers": ["Categoría", "Tickets", "Unidades", "Total ventas"],
                    "money_columns": [3],
                    "rows": rows,
                }
            ],
        }

        return report_data

    def get_informe_ventas_por_tipo(self, fecha_inicio: str, fecha_fin: str, tipos: list = None) -> dict:
        """Informe de ventas agregadas por tipo de producto.

        Similar a categoría, agrupa por `tp.nombre`.
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = [
            "SELECT",
            "    tp.nombre as tipo,",
            "    COUNT(DISTINCT t.id) as num_tickets,",
            "    COALESCE(SUM(tl.cantidad), 0) as total_unidades,",
            "    COALESCE(SUM(tl.cantidad * tl.precio), 0) as total_ventas",
            "FROM tickets t",
            "JOIN ticket_lines tl ON t.id = tl.ticket_id",
            "JOIN productos p ON tl.producto_id = p.id",
            "JOIN tipos tp ON p.tipo = tp.id",
            "WHERE t.created_at BETWEEN ? AND ?",
            "  AND t.total > 0",
            "  AND tl.line_tipo = 'venta'",
        ]

        params = [fecha_inicio_sql, fecha_fin_sql]

        # Si se pasan tipos, aplicar filtro
        if tipos and isinstance(tipos, (list, tuple)) and len(tipos) > 0:
            placeholders = ','.join(['?'] * len(tipos))
            query.append(f"  AND p.tipo IN ({placeholders})")
            params.extend(tipos)

        query.extend([
            "GROUP BY tp.nombre",
            "ORDER BY total_ventas DESC"
        ])

        full_query = "\n".join(query)

        try:
            resultados = self.db.fetch_all(full_query, tuple(params))
        except Exception:
            logging.exception('Error ejecutando consulta get_informe_ventas_por_tipo')
            resultados = None

        if not resultados:
            resultados = []

        rows = []
        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'tipo' in r.keys():
                    tipo = r['tipo']
                    num_tickets = int(r['num_tickets'] or 0)
                    total_unidades = int(r['total_unidades'] or 0)
                    total_ventas = self._money_from_db(r['total_ventas'] or 0)
                else:
                    tipo = r[0]
                    num_tickets = int(r[1] or 0)
                    total_unidades = int(r[2] or 0)
                    total_ventas = self._money_from_db(r[3] or 0)

                rows.append([
                    tipo,
                    num_tickets,
                    total_unidades,
                    self._money(total_ventas),
                ])
            except Exception:
                continue

        from datetime import datetime

        report_data = {
            "title": "Informe de Ventas por Tipo",
            "generated_at": datetime.now().isoformat(),
            "range": {"start": fecha_inicio, "end": fecha_fin},
            "sections": [
                {
                    "type": "table",
                    "title": "Ventas por Tipo",
                    "headers": ["Tipo", "Tickets", "Unidades", "Total ventas"],
                    "money_columns": [3],
                    "rows": rows,
                }
            ],
        }

        return report_data

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

    def get_informe_stock_por_categoria(self, categoria_ids: List[int] = None) -> dict:
        """Informe de stock filtrable por categorías.

        Args:
            categoria_ids: lista de ids de categoría a filtrar (None o lista vacía = todas)

        Returns:
            report_data dict con una sección tipo `table`.
        """
        fecha_inicio_sql = None  # no aplica, mantenemos la firma coherente con otros informes

        query = [
            "SELECT",
            "    p.sku,",
            "    p.nombre,",
            "    c.nombre as categoria,",
            "    p.stock_actual,",
            "    p.stock_minimo,",
            "    COALESCE(pr.coste, 0) as precio_coste",
            "FROM productos p",
            "LEFT JOIN categorias c ON p.categoria = c.id",
            "LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1",
            "WHERE p.activo = 1",
        ]

        params: List = []

        if categoria_ids and isinstance(categoria_ids, (list, tuple)) and len(categoria_ids) > 0:
            placeholders = ','.join(['?'] * len(categoria_ids))
            query.append(f"  AND p.categoria IN ({placeholders})")
            params.extend(categoria_ids)

        query.append("ORDER BY c.nombre, p.nombre")

        full_query = "\n".join(query)

        try:
            resultados = self.db.fetch_all(full_query, tuple(params) if params else ())
        except Exception:
            logging.exception('Error ejecutando consulta get_informe_stock_por_categoria')
            resultados = None

        if not resultados:
            resultados = []

        # Agrupar por categoría
        from collections import defaultdict
        agrupado = defaultdict(list)

        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'sku' in r.keys():
                    sku = r['sku']
                    nombre = r['nombre']
                    categoria = r['categoria']
                    stock_actual = r['stock_actual']
                    stock_minimo = r['stock_minimo']
                    precio_coste = r['precio_coste']
                else:
                    sku = r[0]
                    nombre = r[1]
                    categoria = r[2]
                    stock_actual = r[3]
                    stock_minimo = r[4]
                    precio_coste = r[5]

                cat_key = categoria or 'Sin categoría'
                agrupado[cat_key].append({
                    'sku': sku,
                    'nombre': nombre,
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo,
                    'precio_coste': precio_coste,
                })
            except Exception:
                continue

        blocks = []
        for categoria, productos in agrupado.items():
            fields = []
            for p in productos:
                try:
                    coste_fmt = self._money_from_db(p.get('precio_coste') or 0)
                except Exception:
                    coste_fmt = self._money_from_db(0)

                label = f"{p.get('sku')} - {p.get('nombre')}"
                value = f"Stock: {p.get('stock_actual')} - Mínimo: {p.get('stock_minimo')} - Coste: {coste_fmt}"
                fields.append({"label": label, "value": value, "is_money": False})

            blocks.append({"title": categoria, "fields": fields})
        # Construir tabla para exportación (analítica)
        export_rows = []
        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'sku' in r.keys():
                    sku = r['sku']
                    nombre = r['nombre']
                    categoria = r['categoria']
                    stock_actual = r['stock_actual']
                    stock_minimo = r['stock_minimo']
                    precio_coste = r['precio_coste']
                else:
                    sku = r[0]
                    nombre = r[1]
                    categoria = r[2]
                    stock_actual = r[3]
                    stock_minimo = r[4]
                    precio_coste = r[5]

                coste_fmt = self._money(precio_coste)
                export_rows.append([
                    categoria or 'Sin categoría',
                    sku,
                    nombre,
                    stock_actual,
                    stock_minimo,
                    coste_fmt,
                ])
            except Exception:
                continue

        from datetime import datetime

        report_data = {
            "title": "Informe de Stock por Categoría",
            "generated_at": datetime.now().isoformat(),
            "range": None,
            "sections": [
                {
                    "type": "blocks",
                    "title": "Stock por Categoría",
                    "blocks": blocks,
                    "export_table": {
                        "headers": ["Categoría", "SKU", "Nombre", "Stock actual", "Stock mínimo", "Precio coste"],
                        "money_columns": [5],
                        "rows": export_rows,
                    }
                }
            ],
        }

        return report_data

    def get_informe_stock_por_tipo(self, tipo_ids: List[int] = None) -> dict:
        """Informe de stock filtrable por tipos.
        Args:
            tipo_ids: lista de ids de tipo a filtrar (None o lista vacía = todos)

        Returns:
            report_data dict con una sección tipo `table`.
        """
        fecha_inicio_sql = None  # no aplica, mantenemos la firma coherente con otros informes

        query = [
            "SELECT",
            "    p.sku,",
            "    p.nombre,",
            "    t.nombre as tipo,",
            "    p.stock_actual,",
            "    p.stock_minimo,",
            "    COALESCE(pr.coste, 0) as precio_coste",
            "FROM productos p",
            "LEFT JOIN tipos t ON p.tipo = t.id",
            "LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1",
            "WHERE p.activo = 1",
        ]

        params: List = []

        if tipo_ids and isinstance(tipo_ids, (list, tuple)) and len(tipo_ids) > 0:
            placeholders = ','.join(['?'] * len(tipo_ids))
            query.append(f"  AND p.tipo IN ({placeholders})")
            params.extend(tipo_ids)

        query.append("ORDER BY t.nombre, p.nombre")

        full_query = "\n".join(query)

        try:
            resultados = self.db.fetch_all(full_query, tuple(params) if params else ())
        except Exception:
            logging.exception('Error ejecutando consulta get_informe_stock_por_tipo')
            resultados = None

        if not resultados:
            resultados = []

        # Agrupar por tipo
        from collections import defaultdict
        agrupado = defaultdict(list)

        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'sku' in r.keys():
                    sku = r['sku']
                    nombre = r['nombre']
                    tipo_nombre = r['tipo']
                    stock_actual = r['stock_actual']
                    stock_minimo = r['stock_minimo']
                    precio_coste = r['precio_coste']
                else:
                    sku = r[0]
                    nombre = r[1]
                    tipo_nombre = r[2]
                    stock_actual = r[3]
                    stock_minimo = r[4]
                    precio_coste = r[5]

                tipo_key = tipo_nombre or 'Sin tipo'
                agrupado[tipo_key].append({
                    'sku': sku,
                    'nombre': nombre,
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo,
                    'precio_coste': precio_coste,
                })
            except Exception:
                continue

        blocks = []
        for tipo_nombre, productos in agrupado.items():
            fields = []
            for p in productos:
                try:
                    coste_fmt = self._money_from_db(p.get('precio_coste') or 0)
                except Exception:
                    coste_fmt = self._money_from_db(0)

                label = f"{p.get('sku')} - {p.get('nombre')}"
                value = f"Stock: {p.get('stock_actual')} - Mínimo: {p.get('stock_minimo')} - Coste: {coste_fmt}"
                fields.append({"label": label, "value": value, "is_money": False})

            blocks.append({"title": tipo_nombre, "fields": fields})

        # Construir tabla para exportación (analítica)
        export_rows = []
        for r in resultados:
            try:
                if hasattr(r, 'keys') and 'sku' in r.keys():
                    sku = r['sku']
                    nombre = r['nombre']
                    tipo_nombre = r['tipo']
                    stock_actual = r['stock_actual']
                    stock_minimo = r['stock_minimo']
                    precio_coste = r['precio_coste']
                else:
                    sku = r[0]
                    nombre = r[1]
                    tipo_nombre = r[2]
                    stock_actual = r[3]
                    stock_minimo = r[4]
                    precio_coste = r[5]

                coste_fmt = self._money(precio_coste)
                export_rows.append([
                    tipo_nombre or 'Sin tipo',
                    sku,
                    nombre,
                    stock_actual,
                    stock_minimo,
                    coste_fmt,
                ])
            except Exception:
                continue

        from datetime import datetime

        report_data = {
            "title": "Informe de Stock por Tipo",
            "generated_at": datetime.now().isoformat(),
            "range": None,
            "sections": [
                {
                    "type": "blocks",
                    "title": "Stock por Tipo",
                    "blocks": blocks,
                    "export_table": {
                        "headers": ["Tipo", "SKU", "Nombre", "Stock actual", "Stock mínimo", "Precio coste"],
                        "money_columns": [5],
                        "rows": export_rows,
                    }
                }
            ],
        }

        return report_data
