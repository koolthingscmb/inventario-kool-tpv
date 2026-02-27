"""Servicio para operaciones peligrosas de reseteo/limpieza de la base de datos.

Contiene utilidades usadas desde la UI de configuración para borrar tickets,
movimientos, albaranes y resetear contadores. Estas operaciones deben ser usadas
solo en entornos de desarrollo o con extremo cuidado.
"""

import logging
import datetime
from typing import List, Optional


class ResetService:
    """Servicio para operaciones de reset y limpieza de BD (desarrollo)."""

    def __init__(self, db):
        self.db = db

    def reset_tesoro_clientes(self, cliente_ids: Optional[List[int]] = None) -> bool:
        """Resetear puntos tesoro de clientes.

        If `cliente_ids` is None resets all clients.
        """
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            if cliente_ids:
                placeholders = ','.join('?' * len(cliente_ids))
                cur.execute(
                    f"""
                    UPDATE clientes
                    SET tesoro_total = 0, tesoro_gastado_total = 0, tesoro_historico = 0
                    WHERE id IN ({placeholders})
                    """,
                    cliente_ids,
                )
                logging.info('Tesoro reseteado para %s clientes', len(cliente_ids))
            else:
                cur.execute(
                    """
                    UPDATE clientes
                    SET tesoro_total = 0, tesoro_gastado_total = 0, tesoro_historico = 0
                    """
                )
                logging.warning('Tesoro reseteado para TODOS los clientes')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando tesoro de clientes')
            return False

    def borrar_tickets(self, ticket_nums: Optional[List[int]] = None) -> bool:
        """Borrar tickets por num_ticket (CASCADE limpia movimientos)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            if ticket_nums:
                placeholders = ','.join('?' * len(ticket_nums))
                cur.execute(f"DELETE FROM tickets WHERE num_ticket IN ({placeholders})", ticket_nums)
                logging.info('Tickets borrados: %s', ticket_nums)
            else:
                cur.execute("DELETE FROM tickets")
                logging.warning('TODOS los tickets borrados (CASCADE limpia movimientos)')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando tickets')
            return False

    def borrar_cierres(self) -> bool:
        """Borrar todos los cierres de caja."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute("DELETE FROM cierres_caja")
            logging.warning('TODOS los cierres borrados')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando cierres')
            return False

    def borrar_albaranes(self, albaran_ids: Optional[List[int]] = None) -> bool:
        """Borrar albaranes (CASCADE borra albaran_lines)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            if albaran_ids:
                placeholders = ','.join('?' * len(albaran_ids))
                cur.execute(f"DELETE FROM albaranes WHERE id IN ({placeholders})", albaran_ids)
                logging.info('Albaranes borrados: %s', albaran_ids)
            else:
                cur.execute("DELETE FROM albaranes")
                logging.warning('TODOS los albaranes borrados')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando albaranes')
            return False

    def borrar_productos(self, producto_ids: List[int]) -> bool:
        """Borrar productos seleccionados (CASCADE borra precios)."""
        if not producto_ids:
            logging.warning('borrar_productos: lista vacía')
            return False

        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            placeholders = ','.join('?' * len(producto_ids))
            cur.execute(f"DELETE FROM productos WHERE id IN ({placeholders})", producto_ids)
            logging.info('Productos borrados: %s', producto_ids)

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando productos')
            return False

    def reset_ticket_counter(self) -> bool:
        """Resetear contador de tickets a 0."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            year_actual = datetime.datetime.now().year

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('ticket_counter_value', '0')
                """
            )

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('ticket_counter_year', ?)
                """,
                (str(year_actual),),
            )

            logging.warning('Contador de tickets reseteado a 0, año: %s', year_actual)

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando contador de tickets')
            return False

    def reset_cierre_counter(self) -> bool:
        """Resetear contador de cierres a 0."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            year_actual = datetime.datetime.now().year

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('cierre_counter_value', '0')
                """
            )

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('cierre_counter_year', ?)
                """,
                (str(year_actual),),
            )

            logging.warning('Contador de cierres reseteado a 0, año: %s', year_actual)

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando contador de cierres')
            return False

    def reset_albaran_counter(self) -> bool:
        """Resetear contador de albaranes a 0."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            year_actual = datetime.datetime.now().year

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('albaran_counter_value', '0')
                """
            )

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('albaran_counter_year', ?)
                """,
                (str(year_actual),),
            )

            logging.warning('Contador de albaranes reseteado a 0, año: %s', year_actual)

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando contador de albaranes')
            return False

    def reset_factura_counter(self) -> bool:
        """Resetear contador de facturas a 0."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            year_actual = datetime.datetime.now().year

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('factura_counter_value', '0')
                """
            )

            cur.execute(
                """
                INSERT OR REPLACE INTO configuracion (clave, valor)
                VALUES ('factura_counter_year', ?)
                """,
                (str(year_actual),),
            )

            logging.warning('Contador de facturas reseteado a 0, año: %s', year_actual)

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando contador de facturas')
            return False

    def borrar_facturas(self, factura_ids: Optional[List[int]] = None) -> bool:
        """Borrar facturas (CASCADE borra facturas_lines)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            if factura_ids:
                placeholders = ','.join('?' * len(factura_ids))
                cur.execute(f"DELETE FROM facturas WHERE id IN ({placeholders})", factura_ids)
                logging.info('Facturas borradas: %s', factura_ids)
            else:
                cur.execute("DELETE FROM facturas")
                logging.warning('TODAS las facturas borradas')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando facturas')
            return False

    def reset_completo(self) -> bool:
        """Reset TOTAL: borra tickets, cierres, albaranes, facturas, resetea contadores."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute("DELETE FROM tickets")
            logging.warning('RESET COMPLETO: tickets borrados')

            cur.execute("DELETE FROM cierres_caja")
            logging.warning('RESET COMPLETO: cierres borrados')

            cur.execute("DELETE FROM albaranes")
            logging.warning('RESET COMPLETO: albaranes borrados')

            cur.execute("DELETE FROM facturas")
            logging.warning('RESET COMPLETO: facturas borradas')

            year_actual = datetime.datetime.now().year

            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('ticket_counter_value', '0')")
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('ticket_counter_year', ?)", (str(year_actual),))

            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('cierre_counter_value', '0')")
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('cierre_counter_year', ?)", (str(year_actual),))

            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('albaran_counter_value', '0')")
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('albaran_counter_year', ?)", (str(year_actual),))

            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('factura_counter_value', '0')")
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('factura_counter_year', ?)", (str(year_actual),))

            logging.warning('RESET COMPLETO: contadores reseteados')

            cur.execute(
                """
                UPDATE clientes
                SET tesoro_total = 0, tesoro_gastado_total = 0, tesoro_historico = 0
                """
            )
            logging.warning('RESET COMPLETO: tesoro clientes reseteado')

            conn.commit()
            logging.warning('⚠️⚠️⚠️ RESET COMPLETO EJECUTADO ⚠️⚠️⚠️')
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error en reset completo')
            return False
