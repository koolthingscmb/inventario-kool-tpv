import logging
import math
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from database import connect


class CierreService:
    """Servicio para centralizar cálculos y consultas de cierres de caja.

    No importa tkinter ni realiza operaciones de UI. Usa `database.connect()`.
    Todos los errores se registran con `logging.exception` para evitar fallos silenciosos.
    """

    def _normalize_fecha(self, fecha: Optional[Any], es_desde: Optional[bool] = None) -> str:
        """Normalize input dates.

        If `es_desde` is True/False the function will return a full ISO
        timestamp at the start/end of the given day when a date string in
        'YYYY-MM-DD' is provided. If `es_desde` is None the function keeps
        the previous behaviour (returns ISO date for date objects, string as-is).
        """
        if fecha is None:
            if es_desde is None:
                return date.today().isoformat()
            # return full day bounds for today
            today_iso = date.today().isoformat()
            return f"{today_iso}T00:00:00" if es_desde else f"{today_iso}T23:59:59"

        # datetime objects: return full ISO (date+time) when es_desde specified,
        # otherwise preserve previous behaviour (date only)
        if isinstance(fecha, datetime):
            if es_desde is None:
                return fecha.date().isoformat()
            return fecha.isoformat()

        if isinstance(fecha, date):
            if es_desde is None:
                return fecha.isoformat()
            return f"{fecha.isoformat()}T00:00:00" if es_desde else f"{fecha.isoformat()}T23:59:59"

        # assume string-like
        try:
            s = str(fecha)
            # if already contains a 'T' assume it's a full timestamp
            if 'T' in s:
                return s
            # if caller expects day-bounds, add time portion
            if es_desde is None:
                return s
            return f"{s}T00:00:00" if es_desde else f"{s}T23:59:59"
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
        desde_iso = self._normalize_fecha(fecha_desde, es_desde=True)
        hasta_iso = self._normalize_fecha(fecha_hasta, es_desde=False)
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

    def ventas_por_cajero(self, fecha_desde: Any, fecha_hasta: Any) -> List[Dict[str, Any]]:
        """
        Devuelve el total de ventas por cajero basado en cierres de caja dentro del intervalo seleccionado.

        Retorna una lista de dicts: {'cajero_id': Optional[int], 'nombre': str, 'total_ventas': float}
        """
        desde_iso = self._normalize_fecha(fecha_desde, es_desde=True)
        hasta_iso = self._normalize_fecha(fecha_hasta, es_desde=False)
        try:
            conn = connect()
            cur = conn.cursor()

            # Agrupamos por cajero tomando tickets que referencian cierres dentro del periodo.
            q = (
                """
                SELECT COALESCE(t.cajero, '') as cajero_nombre, COALESCE(SUM(t.total),0) as total_ventas
                FROM tickets t
                LEFT JOIN cierres_caja c ON t.cierre_id = c.id
                WHERE (c.fecha_hora IS NOT NULL AND c.fecha_hora BETWEEN ? AND ?)
                OR (c.fecha_hora IS NULL AND t.created_at BETWEEN ? AND ?)
                GROUP BY cajero_nombre
                ORDER BY total_ventas DESC
                """
            )
            try:
                cur.execute(q, (desde_iso, hasta_iso, desde_iso, hasta_iso))
                rows = cur.fetchall()
            except Exception:
                logging.exception('Error al ejecutar consulta ventas_por_cajero')
                rows = []
            results = []
            for cajero_nombre, total in rows:
                cajero_id = None
                try:
                    # Intentamos resolver el id del usuario si existe una tabla `usuarios` con el mismo nombre
                    cur.execute('SELECT id FROM usuarios WHERE nombre=? LIMIT 1', (cajero_nombre,))
                    r = cur.fetchone()
                    if r:
                        cajero_id = int(r[0])
                except Exception:
                    # tabla usuarios puede no existir; ignoramos en ese caso
                    pass

                results.append({'cajero_id': cajero_id, 'nombre': cajero_nombre, 'total_ventas': float(total or 0.0)})

            return results
        except Exception:
            logging.exception('Error al calcular ventas_por_cajero %s - %s', fecha_desde, fecha_hasta)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def desglose_impuestos_periodo(self, fecha_desde: Any, fecha_hasta: Any) -> List[Dict[str, Any]]:
        """Return list of tax breakdowns grouped by IVA rate for a period.

        Returns list of dicts: {'iva': <rate>, 'base': <base>, 'cuota': <tax>, 'total': <subtotal_incl_iva>}
        Dates may be date/datetime or ISO date strings.
        """
        desde_iso = self._normalize_fecha(fecha_desde, es_desde=True)
        hasta_iso = self._normalize_fecha(fecha_hasta, es_desde=False)
        try:
            conn = connect()
            cur = conn.cursor()
            # We use t.created_at BETWEEN ? AND ? to include both endpoints
            cur.execute(
                "SELECT tl.iva AS tipo_iva, COALESCE(SUM(tl.precio * tl.cantidad),0) as subtotal "
                "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id "
                "WHERE t.created_at BETWEEN ? AND ? GROUP BY tl.iva ORDER BY tl.iva DESC",
                (desde_iso, hasta_iso)
            )
            impuestos = []
            for iva_rate, subtotal in cur.fetchall():
                try:
                    iva_f = float(iva_rate or 0.0)
                    subtotal_f = float(subtotal or 0.0)
                    divisor = 1 + (iva_f / 100.0) if iva_f != 0 else 1.0
                    base = subtotal_f / divisor
                    cuota = subtotal_f - base
                except Exception:
                    iva_f = float(iva_rate or 0.0)
                    subtotal_f = float(subtotal or 0.0)
                    base = 0.0
                    cuota = 0.0
                impuestos.append({'iva': iva_f, 'base': base, 'cuota': cuota, 'total': subtotal_f})
            return impuestos
        except Exception:
            logging.exception('Error al obtener desglose de impuestos en periodo %s - %s', fecha_desde, fecha_hasta)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def desglose_impuestos_ticket(self, ticket_id: int) -> List[Dict[str, Any]]:
        """Return tax breakdown for a single ticket_id.

        Returns list of dicts: {'iva': <rate>, 'base': <base>, 'cuota': <tax>, 'total': <subtotal_incl_iva>}
        """
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(
                "SELECT tl.iva AS tipo_iva, COALESCE(SUM(tl.precio * tl.cantidad),0) as subtotal FROM ticket_lines tl WHERE tl.ticket_id = ? GROUP BY tl.iva ORDER BY tl.iva DESC",
                (ticket_id,)
            )
            impuestos = []
            for iva_rate, subtotal in cur.fetchall():
                try:
                    iva_f = float(iva_rate or 0.0)
                    subtotal_f = float(subtotal or 0.0)
                    divisor = 1 + (iva_f / 100.0) if iva_f != 0 else 1.0
                    base = subtotal_f / divisor
                    cuota = subtotal_f - base
                except Exception:
                    iva_f = float(iva_rate or 0.0)
                    subtotal_f = float(subtotal or 0.0)
                    base = 0.0
                    cuota = 0.0
                impuestos.append({'iva': iva_f, 'base': base, 'cuota': cuota, 'total': subtotal_f})
            return impuestos
        except Exception:
            logging.exception('Error al obtener desglose de impuestos para ticket %s', ticket_id)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def desglose_ventas(self, fecha_desde: Any, fecha_hasta: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Return sales breakdown grouped by category, type and article for a period.

        Returns dict with keys: 'por_categoria', 'por_tipo', 'por_articulo'
        Each value is a list of dicts with fields matching the UI expectations.
        """
        desde_iso = self._normalize_fecha(fecha_desde, es_desde=True)
        hasta_iso = self._normalize_fecha(fecha_hasta, es_desde=False)
        try:
            conn = connect()
            cur = conn.cursor()

            # By category (join on sku)
            try:
                q_cat = (
                    "SELECT COALESCE(p.categoria,''), SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at BETWEEN ? AND ? GROUP BY p.categoria"
                )
                cur.execute(q_cat, (desde_iso, hasta_iso))
                cat_rows = cur.fetchall()
                por_categoria = [{'categoria': r[0], 'qty': r[1], 'total': r[2]} for r in cat_rows]
            except Exception as e:
                print(f"[DEBUG desglose_ventas] Excepción en por_categoria: {e}")
                por_categoria = []

            # By type
            try:
                q_tipo = (
                    "SELECT COALESCE(p.tipo,''), SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at BETWEEN ? AND ? GROUP BY p.tipo"
                )
                cur.execute(q_tipo, (desde_iso, hasta_iso))
                tipo_rows = cur.fetchall()
                por_tipo = [{'tipo': r[0], 'qty': r[1], 'total': r[2]} for r in tipo_rows]
            except Exception as e:
                print(f"[DEBUG desglose_ventas] Excepción en por_tipo: {e}")
                por_tipo = []

            # By article (group by line name)
            try:
                q_art = (
                    "SELECT tl.nombre, SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at BETWEEN ? AND ? GROUP BY tl.nombre"
                )
                cur.execute(q_art, (desde_iso, hasta_iso))
                art_rows = cur.fetchall()
                por_articulo = [{'nombre': r[0], 'qty': r[1], 'total': r[2]} for r in art_rows]
            except Exception as e:
                print(f"[DEBUG desglose_ventas] Excepción en por_articulo: {e}")
                por_articulo = []

            return {'por_categoria': por_categoria, 'por_tipo': por_tipo, 'por_articulo': por_articulo}
        except Exception:
            logging.exception('Error al obtener desglose_ventas %s - %s', fecha_desde, fecha_hasta)
            return {'por_categoria': [], 'por_tipo': [], 'por_articulo': []}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def ventas_por_proveedor(self, fecha_desde: Any, fecha_hasta: Any) -> List[Dict[str, Any]]:
        """Devuelve ventas totales agrupadas por proveedor en el intervalo indicado.

        Retorna lista de dicts: {'proveedor_id': Optional[int], 'proveedor': str, 'total_ventas': float}
        """
        desde_iso = self._normalize_fecha(fecha_desde, es_desde=True)
        hasta_iso = self._normalize_fecha(fecha_hasta, es_desde=False)
        try:
            conn = connect()
            cur = conn.cursor()
            # Intentamos agrupar por proveedor normalizado (proveedor_id) y nombre
            q = (
                """
                SELECT COALESCE(prov.id, p.proveedor, -1) as proveedor_id,
                       COALESCE(prov.nombre, '') as proveedor_nombre,
                       COALESCE(SUM(tl.cantidad * tl.precio),0) as total_ventas
                FROM ticket_lines tl
                JOIN tickets t ON tl.ticket_id = t.id
                LEFT JOIN productos p ON tl.sku = p.sku
                LEFT JOIN proveedores prov ON p.proveedor = prov.id
                WHERE t.created_at BETWEEN ? AND ?
                AND tl.precio >= 0
                AND (tl.nombre IS NULL OR tl.nombre != 'DESC. PUNTOS')
                GROUP BY proveedor_nombre
                ORDER BY total_ventas DESC
                """
            )
            try:
                cur.execute(q, (desde_iso, hasta_iso))
                rows = cur.fetchall()
            except Exception:
                logging.exception('Error al ejecutar consulta ventas_por_proveedor')
                rows = []
            results = []
            for pid, pname, total in rows:
                try:
                    proveedor_id = int(pid) if pid and int(pid) != -1 else None
                except Exception:
                    proveedor_id = None
                results.append({'proveedor_id': proveedor_id, 'proveedor': pname or '', 'total_ventas': float(total or 0.0)})
            return results
        except Exception:
            logging.exception('Error al calcular ventas_por_proveedor %s - %s', fecha_desde, fecha_hasta)
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

            # Validate totals computed from tickets against stored totals in cierre_caja.
            try:
                calculado = float(sum((fp.get('total') or 0.0) for fp in por_forma_pago))
            except Exception:
                calculado = 0.0

            try:
                almacenado = float(cierre.get('total_ingresos') or 0.0)
            except Exception:
                almacenado = 0.0

            # If difference larger than a cent, log a warning and normalize per-payment totals
            try:
                if not math.isclose(calculado, almacenado, rel_tol=1e-2) and abs(calculado - almacenado) > 0.01:
                    logging.warning(
                        "Diferencia encontrada entre los ingresos totales almacenados y los recalculados: calculado=%.2f, almacenado=%.2f, cierre_id=%s",
                        calculado, almacenado, cierre.get('id')
                    )

                    # Normalize stored totals to the recalculated values so UI/reporting uses consistent numbers
                    cierre['total_ingresos'] = calculado
                    # Map per-forma totals (case-insensitive)
                    efectivo = sum(fp.get('total', 0.0) for fp in por_forma_pago if (str(fp.get('forma') or '').strip().lower() == 'efectivo'))
                    tarjeta = sum(fp.get('total', 0.0) for fp in por_forma_pago if (str(fp.get('forma') or '').strip().lower() == 'tarjeta'))
                    web = sum(fp.get('total', 0.0) for fp in por_forma_pago if (str(fp.get('forma') or '').strip().lower() == 'web'))
                    cierre['total_efectivo'] = float(efectivo)
                    cierre['total_tarjeta'] = float(tarjeta)
                    cierre['total_web'] = float(web)
            except Exception:
                # Do not fail the whole operation because of normalization/logging issues
                logging.exception('Error al validar/normalizar totales de cierre id=%s', cierre.get('id'))

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
