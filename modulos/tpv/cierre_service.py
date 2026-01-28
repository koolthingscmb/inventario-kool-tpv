import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from database import connect


class CierreService:
    """Servicio para centralizar cálculos y consultas de cierres de caja.

    No importa tkinter ni realiza operaciones de UI. Usa `database.connect()`.
    Todos los errores se registran con `logging.exception` para evitar fallos silenciosos.
    """

    def _normalize_fecha(self, fecha: Optional[Any]) -> str:
        if fecha is None:
            return date.today().isoformat()
        if isinstance(fecha, date):
            return fecha.isoformat()
        # assume string-like
        try:
            # try to parse if it's a datetime
            if isinstance(fecha, datetime):
                return fecha.date().isoformat()
            return str(fecha)
        except Exception:
            return str(fecha)

    def obtener_resumen_dia(self, fecha: Optional[Any] = None) -> Dict[str, Any]:
        """Return a summary for a given day.

        The result contains: total_ingresos, num_ventas, desglose_pagos and puntos_fidelidad.
        It mirrors the calculations performed by `database.close_day` but DOES NOT
        write a cierre record nor modify tickets.
        """
        fecha_iso = self._normalize_fecha(fecha)
        try:
            conn = connect()
            cur = conn.cursor()

            ticket_where = "date(created_at)=? AND (cierre_id IS NULL)"

            cur.execute(f"SELECT COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {ticket_where}", (fecha_iso,))
            row = cur.fetchone()
            if row:
                num_ventas = int(row[0])
                total_ingresos = float(row[1] or 0.0)
            else:
                num_ventas = 0
                total_ingresos = 0.0

            # Desglose por forma de pago
            val_efectivo = 0.0
            val_tarjeta = 0.0
            val_web = 0.0
            cur.execute(f"SELECT forma_pago, SUM(total) FROM tickets WHERE {ticket_where} GROUP BY forma_pago", (fecha_iso,))
            for forma, total in cur.fetchall():
                f = (forma or "").upper()
                if f == 'EFECTIVO':
                    val_efectivo = float(total or 0)
                elif f == 'TARJETA':
                    val_tarjeta = float(total or 0)
                elif f == 'WEB':
                    val_web = float(total or 0)

            # Fidelización
            cur.execute(f"SELECT COALESCE(SUM(puntos_ganados),0), COALESCE(SUM(puntos_canjeados),0) FROM tickets WHERE {ticket_where}", (fecha_iso,))
            pts_row = cur.fetchone() or (0, 0)
            pts_ganados = int(pts_row[0] or 0)
            pts_canjeados = int(pts_row[1] or 0)

            return {
                'fecha': fecha_iso,
                'total_ingresos': total_ingresos,
                'num_ventas': num_ventas,
                'desglose_pagos': {
                    'efectivo': val_efectivo,
                    'tarjeta': val_tarjeta,
                    'web': val_web,
                },
                'puntos_fidelidad': {
                    'ganados': pts_ganados,
                    'canjeados': pts_canjeados,
                }
            }
        except Exception:
            logging.exception('Error al obtener resumen de día')
            return {}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def listar_cierres_periodo(self, fecha_desde: Any, fecha_hasta: Any) -> List[Dict[str, Any]]:
        """Return list of cierre records between two dates (inclusive).

        Dates may be date/datetime or ISO date strings.
        """
        desde_iso = self._normalize_fecha(fecha_desde)
        hasta_iso = self._normalize_fecha(fecha_hasta)
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT * FROM cierres_caja WHERE date(fecha_hora) BETWEEN ? AND ? ORDER BY fecha_hora ASC", (desde_iso, hasta_iso))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logging.exception('Error al listar cierres en periodo')
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def obtener_detalle_cierre(self, cierre_id: int) -> Optional[Dict[str, Any]]:
        """Return the cierre_caja record matching `cierre_id` or None if not found."""
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT * FROM cierres_caja WHERE id=?", (cierre_id,))
            row = cur.fetchone()
            if not row:
                return None
            cierre = dict(row)

            # determine previous cierre datetime (max fecha_hora < current)
            prev_dt = None
            try:
                cur.execute('SELECT MAX(fecha_hora) FROM cierres_caja WHERE fecha_hora < ?', (cierre.get('fecha_hora'),))
                p = cur.fetchone()
                prev_dt = p[0] if p and p[0] else None
            except Exception:
                prev_dt = None

            if not prev_dt:
                prev_dt = '1970-01-01T00:00:00'

            where_from = prev_dt
            where_to = cierre.get('fecha_hora')

            # Now compute ticket-level aggregates used by the UI. These queries were
            # previously in the UI; centralize them here so the UI has no SQL.
            por_categoria = []
            por_tipo = []
            por_articulo = []
            por_forma_pago = []
            try:
                # categories
                cur.execute(
                    "SELECT COALESCE(p.categoria,''), SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY p.categoria",
                    (where_from, where_to)
                )
                por_categoria = [{'categoria': r[0], 'qty': r[1], 'total': r[2]} for r in cur.fetchall()]
            except Exception:
                por_categoria = []

            try:
                cur.execute(
                    "SELECT COALESCE(p.tipo,''), SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY p.tipo",
                    (where_from, where_to)
                )
                por_tipo = [{'tipo': r[0], 'qty': r[1], 'total': r[2]} for r in cur.fetchall()]
            except Exception:
                por_tipo = []

            try:
                cur.execute(
                    "SELECT tl.nombre, SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY tl.nombre ORDER BY qty DESC LIMIT 10",
                    (where_from, where_to)
                )
                por_articulo = [{'nombre': r[0], 'qty': r[1], 'total': r[2]} for r in cur.fetchall()]
            except Exception:
                por_articulo = []

            try:
                cur.execute("SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE created_at > ? AND created_at <= ? GROUP BY forma_pago", (where_from, where_to))
                por_forma_pago = [{'forma': r[0] or '', 'count': r[1], 'total': r[2]} for r in cur.fetchall()]
            except Exception:
                por_forma_pago = []

            cierre['por_categoria'] = por_categoria
            cierre['por_tipo'] = por_tipo
            cierre['por_articulo'] = por_articulo
            cierre['por_forma_pago'] = por_forma_pago

            return cierre
        except Exception:
            logging.exception('Error al obtener detalle de cierre id=%s', cierre_id)
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass
