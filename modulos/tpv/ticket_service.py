import logging
from typing import Optional, List, Dict

from database import connect

logger = logging.getLogger(__name__)


class TicketService:
    """Service for ticket persistence.

    Responsible for transactional insertion of `tickets` and `ticket_lines`.
    Does not perform any UI work; logs errors and returns None on failure.
    """

    def guardar_ticket(self, datos_ticket: Dict, lineas_carrito: List[Dict]) -> Optional[int]:
        """Persist a ticket and its lines in a single transaction.

        Args:
            datos_ticket: Dict with keys like `total`, `cajero`, `cliente`,
                `forma_pago`, `pagado`, `cambio`, `puntos_ganados`, `puntos_canjeados`, etc.
            lineas_carrito: List of dicts with keys `sku`, `nombre`, `cantidad`, `precio`, `iva`.

        Returns:
            The created `ticket_id` on success, or `None` on failure.
        """
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()

            # Begin explicit transaction
            try:
                conn.execute('BEGIN')
            except Exception:
                # Some wrappers/isolation levels may already have started a transaction
                pass

            # Compute next ticket_no using ticket_seq for atomic increments
            try:
                # increment sequence atomically within the transaction
                cur.execute("UPDATE ticket_seq SET val = val + 1 WHERE name='ticket_no'")
                cur.execute("SELECT val FROM ticket_seq WHERE name='ticket_no'")
                row = cur.fetchone()
                next_no = int(row[0]) if row and row[0] is not None else 1
            except Exception:
                # fallback to older strategy if sequence is missing
                try:
                    cur.execute('SELECT COALESCE(MAX(ticket_no),0)+1 FROM tickets')
                    next_no = int(cur.fetchone()[0] or 1)
                except Exception:
                    next_no = int(datos_ticket.get('ticket_no') or 0) or 1

            # Prepare ticket fields
            created_at = datos_ticket.get('created_at')
            if not created_at:
                from datetime import datetime

                created_at = datetime.now().isoformat()

            ticket_params = (
                created_at,
                float(datos_ticket.get('total', 0.0)),
                datos_ticket.get('cajero'),
                datos_ticket.get('cliente'),
                next_no,
                datos_ticket.get('forma_pago'),
                datos_ticket.get('pagado'),
                datos_ticket.get('cambio'),
                datos_ticket.get('puntos_ganados'),
                datos_ticket.get('puntos_canjeados'),
                datos_ticket.get('puntos_total_momento'),
            )

            cur.execute(
                'INSERT INTO tickets (created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio, puntos_ganados, puntos_canjeados, puntos_total_momento) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                ticket_params,
            )

            ticket_id = cur.lastrowid

            # Insert ticket lines
            for line in lineas_carrito:
                try:
                    cur.execute(
                        'INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)',
                        (
                            ticket_id,
                            line.get('sku'),
                            line.get('nombre'),
                            line.get('cantidad'),
                            line.get('precio'),
                            line.get('iva'),
                        ),
                    )
                except Exception:
                    logger.exception('Error inserting ticket line: %s', line)
                    raise

            conn.commit()
            return ticket_id

        except Exception:
            logger.exception('Error saving ticket')
            try:
                if conn:
                    conn.rollback()
            except Exception:
                logger.exception('Error rolling back transaction')
            return None

        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection')

    def borrar_todos_los_tickets_PRUEBAS(self):
        """Delete all tickets and ticket_lines and reset ticket_seq to 0.

        WARNING: This method is intended ONLY for development/testing environments.
        Do NOT call in production unless you explicitly want to wipe all ticket data.
        """
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()
            try:
                conn.execute('BEGIN')
            except Exception:
                pass
            cur.execute('DELETE FROM ticket_lines')
            cur.execute('DELETE FROM tickets')
            # reset sequence
            try:
                cur.execute("UPDATE ticket_seq SET val = 0 WHERE name='ticket_no'")
            except Exception:
                pass
            conn.commit()
            return True
        except Exception:
            logger.exception('Error wiping tickets (testing utility)')
            try:
                if conn:
                    conn.rollback()
            except Exception:
                logger.exception('Error rolling back wipe')
            return False
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection after wipe')

    def obtener_ticket_completo(self, ticket_id: int) -> Optional[Dict]:
        """Return full ticket data including meta and lines.

        Returns dict: {'meta': {...}, 'lineas': [...] } or None if not found.
        """
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()

            cur.execute('SELECT * FROM tickets WHERE id=? LIMIT 1', (ticket_id,))
            row = cur.fetchone()
            if not row:
                return None

            cols = [c[0] for c in cur.description]
            meta = dict(zip(cols, row))

            cur.execute('SELECT * FROM ticket_lines WHERE ticket_id=? ORDER BY id ASC', (ticket_id,))
            rows = cur.fetchall()
            cols2 = [c[0] for c in cur.description]
            lineas = [dict(zip(cols2, r)) for r in rows]

            return {'meta': meta, 'lineas': lineas}

        except Exception:
            logger.exception('Error fetching full ticket %s', ticket_id)
            return None
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection')

    def listar_tickets_por_cierre(self, cierre_id: int):
        """Return list of tuples (id, created_at, ticket_no, cajero, total) for a given cierre_id."""
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE cierre_id=? ORDER BY created_at ASC', (cierre_id,))
            rows = cur.fetchall()
            # normalize to tuples
            results = []
            for r in rows:
                try:
                    results.append((r[0], r[1], r[2], r[3], r[4]))
                except Exception:
                    results.append(tuple(r))
            return results
        except Exception:
            logger.exception('Error listing tickets for cierre %s', cierre_id)
            return []
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection')

    def listar_tickets_por_fecha(self, fecha_str: str):
        """Return list of tuples (id, created_at, ticket_no, cajero, total) for tickets on a given date (YYYY-MM-DD)."""
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE date(created_at)=? ORDER BY created_at ASC', (fecha_str,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                try:
                    results.append((r[0], r[1], r[2], r[3], r[4]))
                except Exception:
                    results.append(tuple(r))
            return results
        except Exception:
            logger.exception('Error listing tickets for date %s', fecha_str)
            return []
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection')

    def resumen_dia(self, fecha_str: str):
        """Return a summary dict for the given date string (YYYY-MM-DD).

        Returns keys: from, to, count, total, pagos (list of tuples (forma_pago, count, total)).
        """
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT MIN(ticket_no), MAX(ticket_no), COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE date(created_at)=?", (fecha_str,))
            min_no, max_no, count_tickets, sum_total = cur.fetchone()
            cur.execute("SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE date(created_at)=? GROUP BY forma_pago", (fecha_str,))
            pagos = cur.fetchall()
            return {
                'fecha': fecha_str,
                'from': min_no,
                'to': max_no,
                'count': count_tickets,
                'total': float(sum_total or 0.0),
                'pagos': pagos
            }
        except Exception:
            logger.exception('Error computing day summary for %s', fecha_str)
            return None
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection')

    def close_day(self, fecha: str, tipo: str = 'Z', include_category: bool = False, include_products: bool = False, cajero: str = None, notas: str = None):
        """Delegate to database.close_day to perform cierre and return the resumen dict.

        This wrapper centralizes closure logic through the service layer.
        """
        try:
            from database import close_day as _close_day
            resumen = _close_day(fecha, tipo=tipo, include_category=include_category, include_products=include_products, cajero=cajero, notas=notas)
            # cache last cierre id if present
            try:
                cierre_id = resumen.get('cierre_id')
                if cierre_id:
                    self._last_cierre_id = cierre_id
            except Exception:
                pass
            return resumen
        except Exception:
            logger.exception('Error delegating close_day')
            return None
