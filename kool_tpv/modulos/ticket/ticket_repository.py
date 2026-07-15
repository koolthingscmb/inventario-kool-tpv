"""Repository encargado únicamente de las operaciones SQL necesarias para
persistir tickets, líneas, pagos, movimientos de stock y auditoría.

Esta capa no realiza cálculos de negocio (puntos, descuentos, etc.).
Las entradas deben ser ya preparadas (p.ej. cantidades en céntimos).
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.base_datos.money_adapter import read_from_db

logger = logging.getLogger(__name__)


class TicketRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert_ticket(self, *, created_at, cajero, cliente, cliente_id, num_ticket,
                      subtotal_cents, forma_pago, total_cents, pagado_cents, cambio_cents,
                      importe_efectivo_cents, importe_tarjeta_cents, importe_web_cents=None,
                      descuento_euros_cents, descuento_tipo, descuento_valor,
                      tesoro_ganado_str, tesoro_gastado_str, tesoro_total_ticket_cents=0,
                      ticket_text_snapshot=None,
                      iva_desglose_json='{}', vale_id=None, vale_cents=None, cur=None):
        # Ensure `cliente` is a string or None before binding to SQLite
        try:
            if cliente is None:
                cliente_val = None
            elif isinstance(cliente, str):
                cliente_val = cliente
            else:
                # coerce other types (including dict) to a readable string
                cliente_val = str(cliente)
        except Exception:
            cliente_val = None

        # ensure created_at is set (UTC) to avoid NULLs and mixed timezones
        try:
            if created_at is None:
                created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        # Use provided cursor when inside an external transaction
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
        insert_ticket_q = (
            "INSERT INTO tickets (created_at, cajero, cliente, cliente_id, num_ticket, subtotal, forma_pago, total, pagado, cambio, importe_efectivo, importe_tarjeta, importe_web, descuento_euros, descuento_tipo, descuento_valor, tesoro_ganado, tesoro_gastado, tesoro_total_ticket, ticket_text, iva_desglose, vale_id, vale_cents) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        # Prepare values allowing nullable fields (forma_pago and importes pueden ser None)
        importe_efectivo_val = int(importe_efectivo_cents) if importe_efectivo_cents is not None else None
        importe_tarjeta_val = int(importe_tarjeta_cents) if importe_tarjeta_cents is not None else None
        importe_web_val = int(importe_web_cents) if importe_web_cents is not None else None

        cur.execute(
            insert_ticket_q,
            (
                created_at,
                cajero,
                cliente_val,
                cliente_id,
                num_ticket,
                int(subtotal_cents),
                forma_pago,
                int(total_cents),
                int(pagado_cents),
                int(cambio_cents),
                importe_efectivo_val,
                importe_tarjeta_val,
                importe_web_val,
                int(descuento_euros_cents),
                descuento_tipo,
                descuento_valor,
                int(tesoro_ganado_str or 0),
                int(tesoro_gastado_str or 0),
                int(tesoro_total_ticket_cents),
                ticket_text_snapshot,
                iva_desglose_json,
                vale_id,
                int(vale_cents) if vale_cents is not None else None,
            ),
        )
        # Commit only if we are not inside an external transaction
        if not use_external_cursor:
            self.db.connection.commit()
        return cur.lastrowid

    def insert_ticket_line(self, ticket_id: int, sku: Optional[str], nombre: str,
                           cantidad: int, precio_cents: int, iva: int, line_tipo: str, producto_id: Optional[int], cur=None):
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
        insert_line_q = (
            "INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo, producto_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        cur.execute(insert_line_q, (ticket_id, sku, nombre, cantidad, int(precio_cents), iva, line_tipo, producto_id))
        if not use_external_cursor:
            self.db.connection.commit()
        return cur.lastrowid

    def update_producto_stock_y_ventas(self, producto_id: int, stock_change: int, ventas_change: int, cur=None):
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
        cur.execute('UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ?, ventas_totales = COALESCE(ventas_totales,0) + ? WHERE id = ?', (stock_change, ventas_change, producto_id))
        if not use_external_cursor:
            self.db.connection.commit()

    def update_stock_and_record_movement(self, producto_id: int, stock_change: int, ventas_change: int, motivo: str, ticket_line_id: Optional[int] = None, cur=None):
        """Atomicamente actualizar stock/ventas y registrar movimiento de stock.

        Lanza excepción si falla, para que el caller (processor) pueda hacer rollback.
        """
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
        try:
            cur.execute('UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ?, ventas_totales = COALESCE(ventas_totales,0) + ? WHERE id = ?', (stock_change, ventas_change, producto_id))
            cur.execute('INSERT INTO stock_movements (producto_id, cantidad, motivo, ticket_line_id) VALUES (?, ?, ?, ?)', (producto_id, stock_change, motivo, ticket_line_id))
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            # Log full exception and re-raise so transaction semantics are preserved
            logger.exception('Error actualizando stock y registrando movimiento para producto_id=%s, motivo=%s', producto_id, motivo)
            if not use_external_cursor:
                try:
                    self.db.connection.rollback()
                except Exception:
                    pass
            raise

    def insert_stock_movement(self, producto_id: int, cantidad: int, motivo: str, ticket_line_id: Optional[int], cur=None):
        try:
            # Allow ticket_line_id to be None - the FK permits NULL. Insert and let callers
            # handle transactionality. Detailed exception logging is important for debugging.
            use_external_cursor = cur is not None
            if not use_external_cursor:
                cur = self.db.connection.cursor()
            cur.execute('INSERT INTO stock_movements (producto_id, cantidad, motivo, ticket_line_id) VALUES (?, ?, ?, ?)', (producto_id, cantidad, motivo, ticket_line_id))
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            logger.exception('insert_stock_movement failed for producto_id=%s, ticket_line_id=%s', producto_id, ticket_line_id)

    def insert_payment(self, ticket_id: int, metodo: str, importe_cents: int, created_at: str, cur=None):
        try:
            # ensure created_at in UTC if not provided
            if created_at is None:
                try:
                    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            use_external_cursor = cur is not None
            if not use_external_cursor:
                cur = self.db.connection.cursor()
            cur.execute('INSERT INTO payments (ticket_id, metodo, importe, created_at) VALUES (?, ?, ?, ?)', (ticket_id, metodo, int(importe_cents), created_at))
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            logger.warning('payments table not present or insert failed')

    def insert_audit_log(self, created_at: str, ticket_id: int, usuario: Optional[str], accion: str, detalles: str, cur=None):
        try:
            # ensure created_at in UTC if not provided
            if created_at is None:
                try:
                    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    try:
                        from kool_tpv.utils.time_utils import now_utc_str
                        created_at = now_utc_str()
                    except Exception:
                        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            use_external_cursor = cur is not None
            if not use_external_cursor:
                cur = self.db.connection.cursor()
            cur.execute('INSERT INTO audit_logs (created_at, ticket_id, usuario, accion, detalles) VALUES (?, ?, ?, ?, ?)', (created_at, ticket_id, usuario, accion, detalles))
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception:
            logger.warning('audit_logs table not present or insert failed')

    def insert_points_movement_raw(self, cliente_id: int, puntos, motivo: str, ticket_id: int, usuario_id: Optional[int] = None, created_at: Optional[str] = None, cur=None):
        """Insertar movimiento de puntos en `points_movements`.

        Mejor logging y `created_at` por defecto; los errores se registran como WARNING
        pero no se elevan para no bloquear la venta en esquemas antiguos.
        """
        try:
            if created_at is None:
                try:
                    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    created_at = datetime.now(timezone.utc).isoformat()

            use_external_cursor = cur is not None
            if not use_external_cursor:
                cur = self.db.connection.cursor()
            cur.execute(
                'INSERT INTO points_movements (cliente_id, puntos, motivo, ticket_id, usuario_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (cliente_id, int(puntos), motivo, ticket_id, usuario_id, created_at),
            )
            if not use_external_cursor:
                self.db.connection.commit()
        except Exception as e:
            logger.warning('Error insertando points_movement: %s', e)

    def get_ticket_ids_by_date_range(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Devuelve lista de ticket IDs dentro del rango de fechas (inclusive).

        Args:
            fecha_inicio: 'YYYY-MM-DD'
            fecha_fin: 'YYYY-MM-DD'

        Returns:
            List[int]: IDs de tickets con total > 0.
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT id FROM tickets "
            "WHERE created_at BETWEEN ? AND ? AND total > 0"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        return [int(r[0]) for r in (rows or [])]

    def get_resumen_ventas_por_rango(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen agregado de ventas entre fechas (total_tickets, total_ventas, total_base)."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT COUNT(*) as total_tickets, "
            "COALESCE(SUM(total), 0) as total_ventas, "
            "COALESCE(SUM(subtotal), 0) as total_base "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total > 0"
        )
        row = self.db.fetch_one(query, (fecha_inicio_sql, fecha_fin_sql))
        if not row:
            return {"total_tickets": 0, "total_ventas": 0.0, "total_base": 0.0}

        total_tickets = int(row[0] or 0)
        total_ventas = float(read_from_db(row[1] or 0))
        total_base = float(read_from_db(row[2] or 0))

        return {
            "total_tickets": total_tickets,
            "total_ventas": total_ventas,
            "total_base": total_base,
        }

    def get_ventas_diarias_por_rango(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas agregadas por día dentro del rango."""
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"
        query = (
            "SELECT DATE(t.created_at) as fecha, "
            "COUNT(DISTINCT t.id) as num_tickets, "
            "COALESCE(SUM(tl.cantidad), 0) as total_uds, "
            "COALESCE(SUM(t.total), 0) as total_dia "
            "FROM tickets t "
            "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id AND tl.line_tipo = 'venta' "
            "WHERE t.created_at BETWEEN ? AND ? AND t.total > 0 "
            "GROUP BY DATE(t.created_at) ORDER BY DATE(t.created_at) ASC"
        )
        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        result = []
        for r in rows or []:
            fecha = str(r[0]) if r[0] is not None else ''
            num_tickets = int(r[1] or 0)
            total_uds = int(r[2] or 0)
            total = float(read_from_db(r[3] or 0))
            result.append({"fecha": fecha, "num_tickets": num_tickets, "total_uds": total_uds, "total": total})
        return result

    def listar_tickets(self, termino: str = ''):
        """Listar tickets filtrando por cliente o nombre de producto en líneas.

        Devuelve una lista de dicts con claves:
        `id`, `num_ticket`, `created_at`, `total`, `cajero`, `cliente`, `forma_pago`, `ticket_text`.

        `total` ya viene convertido a `Decimal` usando `read_from_db`.
        """
        try:
            if termino:
                like = f"%{termino}%"
                query = (
                    "SELECT DISTINCT t.id, t.num_ticket, t.created_at, t.total, t.cajero, t.cliente, t.forma_pago, t.cierre_id, t.ticket_text, t.descuento_euros, t.descuento_tipo, t.descuento_valor, t.dto_aplicado_id "
                    "FROM tickets t "
                    "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id "
                    "WHERE t.cliente LIKE ? OR tl.nombre LIKE ? "
                    "ORDER BY t.created_at DESC"
                )
                rows = self.db.fetch_all(query, (like, like))
            else:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, cierre_id, ticket_text, descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id "
                    "FROM tickets "
                    "ORDER BY created_at DESC"
                )
                rows = self.db.fetch_all(query, None)

            results = []
            for r in rows or []:
                try:
                    row = dict(r)
                except Exception:
                    # fallback for non-row types
                    row = {
                        'id': r[0],
                        'num_ticket': r[1],
                        'created_at': r[2],
                        'total': r[3],
                        'cajero': r[4],
                        'cliente': r[5],
                        'forma_pago': r[6],
                        'cierre_id': r[7] if len(r) > 7 else None,
                        'ticket_text': r[8] if len(r) > 8 else None,
                        'descuento_euros': read_from_db(r[9]) if len(r) > 9 and r[9] is not None else None,
                        'descuento_tipo': r[10] if len(r) > 10 else None,
                        'descuento_valor': r[11] if len(r) > 11 else None,
                        'dto_aplicado_id': r[12] if len(r) > 12 else None,
                    }

                # Convertir total (céntimos) a Decimal euros
                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                # descuento_euros stored in DB as cents; convert for display if present
                try:
                    row['descuento_euros'] = read_from_db(row.get('descuento_euros')) if row.get('descuento_euros') is not None else None
                except Exception:
                    row['descuento_euros'] = None

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets')
            return []

    def listar_tickets_pendientes(self, termino: str = ''):
        """Listar tickets pendientes de cierre filtrando por cliente o nombre de producto."""
        try:
            params = None
            if termino:
                like = f"%{termino}%"
                query = (
                    "SELECT DISTINCT t.id, t.num_ticket, t.created_at, t.total, t.cajero, t.cliente, t.forma_pago, t.cierre_id, t.ticket_text, t.descuento_euros, t.descuento_tipo, t.descuento_valor, t.dto_aplicado_id "
                    "FROM tickets t "
                    "LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id "
                    "WHERE (t.cliente LIKE ? OR tl.nombre LIKE ?) AND (t.cierre_id IS NULL) "
                    "ORDER BY t.created_at DESC"
                )
                params = (like, like)
            else:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, cierre_id, ticket_text, descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id "
                    "FROM tickets "
                    "WHERE cierre_id IS NULL "
                    "ORDER BY created_at DESC"
                )

            rows = self.db.fetch_all(query, params)

            results = []
            for r in rows or []:
                try:
                    row = dict(r)
                except Exception:
                    row = {
                        'id': r[0],
                        'num_ticket': r[1],
                        'created_at': r[2],
                        'total': r[3],
                        'cajero': r[4],
                        'cliente': r[5],
                        'forma_pago': r[6],
                        'cierre_id': r[7] if len(r) > 7 else None,
                        'ticket_text': r[8] if len(r) > 8 else None,
                        'descuento_euros': read_from_db(r[9]) if len(r) > 9 and r[9] is not None else None,
                        'descuento_tipo': r[10] if len(r) > 10 else None,
                        'descuento_valor': r[11] if len(r) > 11 else None,
                        'dto_aplicado_id': r[12] if len(r) > 12 else None,
                    }

                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                try:
                    row['descuento_euros'] = read_from_db(row.get('descuento_euros')) if row.get('descuento_euros') is not None else None
                except Exception:
                    row['descuento_euros'] = None

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets pendientes')
            return []

    def listar_tickets_por_dia(self, fecha: str, solo_pendientes: bool = False) -> list:
        """Listar tickets de un día concreto.

        Args:
            fecha: 'YYYY-MM-DD'
            solo_pendientes: si True, filtra solo tickets con cierre_id IS NULL

        Returns:
            Lista de dicts con: id, num_ticket, created_at, total (Decimal),
            cajero, cliente, forma_pago, cierre_id, ticket_text,
            descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id
        """
        try:
            fecha_inicio_sql = f"{fecha} 00:00:00"
            fecha_fin_sql = f"{fecha} 23:59:59"

            if solo_pendientes:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, cierre_id, ticket_text, descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id "
                    "FROM tickets "
                    "WHERE created_at BETWEEN ? AND ? AND cierre_id IS NULL "
                    "ORDER BY created_at DESC"
                )
            else:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, cierre_id, ticket_text, descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id "
                    "FROM tickets "
                    "WHERE created_at BETWEEN ? AND ? "
                    "ORDER BY created_at DESC"
                )

            rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))

            results = []
            for r in rows or []:
                try:
                    row = dict(r)
                except Exception:
                    row = {
                        'id': r[0],
                        'num_ticket': r[1],
                        'created_at': r[2],
                        'total': r[3],
                        'cajero': r[4],
                        'cliente': r[5],
                        'forma_pago': r[6],
                        'cierre_id': r[7] if len(r) > 7 else None,
                        'ticket_text': r[8] if len(r) > 8 else None,
                        'descuento_euros': read_from_db(r[9]) if len(r) > 9 and r[9] is not None else None,
                        'descuento_tipo': r[10] if len(r) > 10 else None,
                        'descuento_valor': r[11] if len(r) > 11 else None,
                        'dto_aplicado_id': r[12] if len(r) > 12 else None,
                    }

                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                try:
                    row['descuento_euros'] = read_from_db(row.get('descuento_euros')) if row.get('descuento_euros') is not None else None
                except Exception:
                    row['descuento_euros'] = None

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets por día')
            return []

    def listar_tickets_por_cierre(self, cierre_id: int) -> list:
        """Listar tickets asociados a un cierre concreto.

        Args:
            cierre_id: ID del cierre

        Returns:
            Lista de dicts con: id, num_ticket, created_at, total (Decimal),
            cajero, cliente, forma_pago, cierre_id, ticket_text,
            descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id
        """
        try:
            query = (
                "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, cierre_id, ticket_text, descuento_euros, descuento_tipo, descuento_valor, dto_aplicado_id "
                "FROM tickets "
                "WHERE cierre_id = ? "
                "ORDER BY created_at DESC"
            )

            rows = self.db.fetch_all(query, (cierre_id,))

            results = []
            for r in rows or []:
                try:
                    row = dict(r)
                except Exception:
                    row = {
                        'id': r[0],
                        'num_ticket': r[1],
                        'created_at': r[2],
                        'total': r[3],
                        'cajero': r[4],
                        'cliente': r[5],
                        'forma_pago': r[6],
                        'cierre_id': r[7] if len(r) > 7 else None,
                        'ticket_text': r[8] if len(r) > 8 else None,
                        'descuento_euros': read_from_db(r[9]) if len(r) > 9 and r[9] is not None else None,
                        'descuento_tipo': r[10] if len(r) > 10 else None,
                        'descuento_valor': r[11] if len(r) > 11 else None,
                        'dto_aplicado_id': r[12] if len(r) > 12 else None,
                    }

                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                try:
                    row['descuento_euros'] = read_from_db(row.get('descuento_euros')) if row.get('descuento_euros') is not None else None
                except Exception:
                    row['descuento_euros'] = None

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets por cierre')
            return []

    def get_ventas_por_cajero(self, fecha_inicio: str, fecha_fin: str) -> list:
        """Ventas agregadas por cajero en el rango de fechas.

        Retorna lista de tuplas: (cajero, num_tickets, total_ventas)
        """
        fecha_inicio_sql = f"{fecha_inicio} 00:00:00"
        fecha_fin_sql = f"{fecha_fin} 23:59:59"

        query = (
            "SELECT cajero, COUNT(*) as num_tickets, "
            "COALESCE(SUM(total), 0) as total_ventas "
            "FROM tickets WHERE created_at BETWEEN ? AND ? AND total > 0 "
            "GROUP BY cajero ORDER BY total_ventas DESC"
        )

        rows = self.db.fetch_all(query, (fecha_inicio_sql, fecha_fin_sql))
        resultados = []
        for r in rows or []:
            cajero = r[0]
            num_tickets = int(r[1] or 0)
            total_ventas = float(read_from_db(r[2] or 0))
            resultados.append((cajero, num_tickets, total_ventas))
        return resultados
