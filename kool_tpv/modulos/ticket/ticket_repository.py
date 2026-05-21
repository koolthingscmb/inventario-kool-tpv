"""Repository encargado únicamente de las operaciones SQL necesarias para
persistir tickets, líneas, pagos, movimientos de stock y auditoría.

Esta capa no realiza cálculos de negocio (puntos, descuentos, etc.).
Las entradas deben ser ya preparadas (p.ej. cantidades en céntimos).
"""
import logging
from typing import Optional
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.base_datos.money_adapter import read_from_db

logger = logging.getLogger(__name__)


class TicketRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert_ticket(self, *, created_at, cajero, cliente, cliente_id, num_ticket,
                      subtotal_cents, forma_pago, total_cents, pagado_cents, cambio_cents,
                      importe_efectivo_cents, importe_tarjeta_cents,
                      descuento_euros_cents, descuento_tipo, descuento_valor,
                      tesoro_ganado_str, tesoro_gastado_str, ticket_text_snapshot=None,
                      iva_desglose_json='{}'):
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

        cur = self.db.connection.cursor()
        insert_ticket_q = (
            "INSERT INTO tickets (created_at, cajero, cliente, cliente_id, num_ticket, subtotal, forma_pago, total, pagado, cambio, importe_efectivo, importe_tarjeta, descuento_euros, descuento_tipo, descuento_valor, tesoro_ganado, tesoro_gastado, ticket_text, iva_desglose) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
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
                int(importe_efectivo_cents),
                int(importe_tarjeta_cents),
                int(descuento_euros_cents),
                descuento_tipo,
                descuento_valor,
                int(tesoro_ganado_str or 0),
                int(tesoro_gastado_str or 0),
                ticket_text_snapshot,
                iva_desglose_json,
            ),
        )
        self.db.connection.commit()
        return cur.lastrowid

    def insert_ticket_line(self, ticket_id: int, sku: Optional[str], nombre: str,
                           cantidad: int, precio_cents: int, iva: int, line_tipo: str, producto_id: Optional[int]):
        cur = self.db.connection.cursor()
        insert_line_q = (
            "INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo, producto_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        cur.execute(insert_line_q, (ticket_id, sku, nombre, cantidad, int(precio_cents), iva, line_tipo, producto_id))
        self.db.connection.commit()
        return cur.lastrowid

    def update_producto_stock_y_ventas(self, producto_id: int, stock_change: int, ventas_change: int):
        cur = self.db.connection.cursor()
        cur.execute('UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ?, ventas_totales = COALESCE(ventas_totales,0) + ? WHERE id = ?', (stock_change, ventas_change, producto_id))
        self.db.connection.commit()

    def insert_stock_movement(self, producto_id: int, cantidad: int, motivo: str, ticket_line_id: Optional[int]):
        try:
            if ticket_line_id is None:
                logger.error('Refusing to insert stock_movements without ticket_line_id')
                return
            cur = self.db.connection.cursor()
            cur.execute('INSERT INTO stock_movements (producto_id, cantidad, motivo, ticket_line_id) VALUES (?, ?, ?, ?)', (producto_id, cantidad, motivo, ticket_line_id))
            self.db.connection.commit()
        except Exception:
            logger.warning('stock_movements table not present or insert failed')

    def insert_payment(self, ticket_id: int, metodo: str, importe_cents: int, created_at: str):
        try:
            cur = self.db.connection.cursor()
            cur.execute('INSERT INTO payments (ticket_id, metodo, importe, created_at) VALUES (?, ?, ?, ?)', (ticket_id, metodo, int(importe_cents), created_at))
            self.db.connection.commit()
        except Exception:
            logger.warning('payments table not present or insert failed')

    def insert_audit_log(self, created_at: str, ticket_id: int, usuario: Optional[str], accion: str, detalles: str):
        try:
            cur = self.db.connection.cursor()
            cur.execute('INSERT INTO audit_logs (created_at, ticket_id, usuario, accion, detalles) VALUES (?, ?, ?, ?, ?)', (created_at, ticket_id, usuario, accion, detalles))
            self.db.connection.commit()
        except Exception:
            logger.warning('audit_logs table not present or insert failed')

    def insert_points_movement_raw(self, cliente_id: int, puntos, motivo: str, ticket_id: int, usuario_id: Optional[int] = None, created_at: Optional[str] = None):
        """Insertar movimiento de puntos en `points_movements`.

        Mejor logging y `created_at` por defecto; los errores se registran como WARNING
        pero no se elevan para no bloquear la venta en esquemas antiguos.
        """
        try:
            if created_at is None:
                created_at = datetime.now().isoformat()

            cur = self.db.connection.cursor()
            cur.execute(
                'INSERT INTO points_movements (cliente_id, puntos, motivo, ticket_id, usuario_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (cliente_id, int(puntos), motivo, ticket_id, usuario_id, created_at),
            )
            self.db.connection.commit()
        except Exception as e:
            logger.warning('Error insertando points_movement: %s', e)

    def listar_tickets(self, termino: str = ''):
        """Listar tickets para vistas / búsquedas.

        Devuelve una lista de dicts con claves:
        `id`, `num_ticket`, `created_at`, `total`, `cajero`, `cliente`, `forma_pago`, `ticket_text`.

        `total` ya viene convertido a `Decimal` usando `read_from_db`.
        """
        try:
            if termino:
                like = f"%{termino}%"
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, ticket_text "
                    "FROM tickets "
                    "WHERE cliente LIKE ? OR cajero LIKE ? OR CAST(num_ticket AS TEXT) LIKE ? "
                    "ORDER BY created_at DESC"
                )
                rows = self.db.fetch_all(query, (like, like, like))
            else:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, ticket_text "
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
                        'ticket_text': r[7] if len(r) > 7 else None,
                    }

                # Convertir total (céntimos) a Decimal euros
                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets')
            return []

    def listar_tickets_pendientes(self, termino: str = ''):
        """Listar tickets pendientes de cierre (where cierre_id IS NULL).

        Mantiene la misma firma y formato de retorno que `listar_tickets`.
        """
        try:
            params = None
            if termino:
                like = f"%{termino}%"
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, ticket_text "
                    "FROM tickets "
                    "WHERE (cliente LIKE ? OR cajero LIKE ? OR CAST(num_ticket AS TEXT) LIKE ?) AND (cierre_id IS NULL) "
                    "ORDER BY created_at DESC"
                )
                params = (like, like, like)
            else:
                query = (
                    "SELECT id, num_ticket, created_at, total, cajero, cliente, forma_pago, ticket_text "
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
                        'ticket_text': r[7] if len(r) > 7 else None,
                    }

                try:
                    row['total'] = read_from_db(row.get('total'))
                except Exception:
                    row['total'] = read_from_db(0)

                results.append(row)

            return results
        except Exception:
            logger.exception('Error listando tickets pendientes')
            return []
