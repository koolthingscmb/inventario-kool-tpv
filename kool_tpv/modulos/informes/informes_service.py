"""Service layer scaffold for Informes.

Prepared for future database queries and business logic related to reports.
"""

from decimal import Decimal, ROUND_HALF_UP


class InformesService:
    """Placeholder service for Informes module.

    Constructor receives a `db` parameter (database wrapper/connection) and
    stores it for future use. No methods implemented yet.
    """

    def __init__(self, db):
        self.db = db

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
                total_ventas = float(row["total_ventas"] if "total_ventas" in row.keys() else row[1])
            except Exception:
                try:
                    total_ventas = float(row[1] or 0.0)
                except Exception:
                    total_ventas = 0.0

            try:
                total_base = float(row["total_base"] if "total_base" in row.keys() else row[2])
            except Exception:
                try:
                    total_base = float(row[2] or 0.0)
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
                    total_f = float(total) if total is not None else 0.0
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

        # Helper to ensure monetary precision: two decimal places, HALF_UP
        def _money(value):
            try:
                d = Decimal(str(value))
                return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            except Exception:
                return 0.0

        # Apply monetary normalization to the resumen values (except total_tickets)
        try:
            resumen["total_ventas"] = _money(resumen.get("total_ventas"))
        except Exception:
            resumen["total_ventas"] = 0.0
        try:
            resumen["total_base"] = _money(resumen.get("total_base"))
        except Exception:
            resumen["total_base"] = 0.0
        try:
            resumen["total_iva"] = _money(resumen.get("total_iva"))
        except Exception:
            resumen["total_iva"] = 0.0
        try:
            resumen["ticket_medio"] = _money(resumen.get("ticket_medio"))
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
                            [item.get("fecha"), _money(item["total"]) ]
                            for item in (ventas_diarias or [])
                        ],
                },
            ],
        }

        return informe
