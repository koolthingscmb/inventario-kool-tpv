import logging
from database import connect
from modulos.almacen.producto_service import ProductoService

logger = logging.getLogger(__name__)


class ResetService:
    """Service that provides granular reset utilities for development/testing.

    WARNING: Methods in this service delete data. Use only in development
    environments or when you have a validated backup.
    """

    def borrar_ventas(self) -> bool:
        """Delete tickets, ticket_lines, cierres_caja and reset ticket_seq."""
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
            cur.execute('DELETE FROM cierres_caja')
            try:
                cur.execute("UPDATE ticket_seq SET val = 0 WHERE name='ticket_no'")
            except Exception:
                # If sequence table missing, ignore
                pass
            conn.commit()
            return True
        except Exception:
            logger.exception('Error wiping sales tables')
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

    def borrar_inventario(self) -> bool:
        """Delete products-related data: productos, precios, codigos_barras, product_images."""
        # Delegar borrado de inventario a ProductoService para centralizar lógica
        try:
            service = ProductoService()
            ok = service.vaciar_inventario_completo()
            return bool(ok)
        except Exception:
            logger.exception('Error delegando vaciado de inventario a ProductoService')
            return False

    def borrar_clientes(self) -> bool:
        """Delete clients table data."""
        conn = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('DELETE FROM clientes')
            conn.commit()
            return True
        except Exception:
            logger.exception('Error wiping clientes table')
            try:
                if conn:
                    conn.rollback()
            except Exception:
                logger.exception('Error rolling back clientes wipe')
            return False
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                logger.exception('Error closing DB connection after clientes wipe')

    def borrar_todo(self) -> bool:
        """Run all wipes. Returns True only if all succeeded."""
        ok1 = self.borrar_ventas()
        ok2 = self.borrar_inventario()
        ok3 = self.borrar_clientes()
        return ok1 and ok2 and ok3
