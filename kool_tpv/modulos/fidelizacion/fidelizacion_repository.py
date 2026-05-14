import logging
from decimal import Decimal
from typing import Optional
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db

logger = logging.getLogger(__name__)


class FidelizacionRepository:
    def __init__(self, db: Database):
        self.db = db

    def actualizar_cliente_loyalty(
        self,
        cliente_id: int,
        puntos_otorgar_cents: int,
        puntos_restar_cents: int,
        puntos_gastados_cents: int,
        total_ticket_cents: int,
        unidades_vendidas: int,
        fecha: str,
    ) -> None:
        """
        Actualiza los campos de fidelización del cliente.
        Todos los valores de puntos y totales se reciben en céntimos (int).
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute(
                """
                UPDATE clientes
                SET
                    tesoro_total = COALESCE(tesoro_total, 0) + ?,
                    tesoro_historico = COALESCE(tesoro_historico, 0) + ?,
                    tesoro_gastado_total = COALESCE(tesoro_gastado_total, 0) + ?,
                    total_compras = COALESCE(total_compras, 0) + 1,
                    total_compras_euros = COALESCE(total_compras_euros, 0) + ?,
                    total_unidades = COALESCE(total_unidades, 0) + ?,
                    fecha_ultima_compra = ?
                WHERE id = ?
                """,
                (
                    int(puntos_otorgar_cents - puntos_restar_cents - puntos_gastados_cents),
                    int(puntos_otorgar_cents),
                    int(puntos_gastados_cents),
                    int(total_ticket_cents),
                    int(unidades_vendidas),
                    fecha,
                    cliente_id,
                ),
            )
            # Persistir cambios: el repo debe encargarse del commit
            self.db.connection.commit()

        except Exception:
            logger.exception('Error actualizando loyalty para cliente %s', cliente_id)
            try:
                self.db.connection.rollback()
            except Exception:
                logger.exception('Rollback fallido para cliente %s', cliente_id)
            raise

    def insertar_movimiento_puntos(
        self,
        cliente_id: int,
        puntos: Decimal,
        motivo: str,
        ticket_id: int,
        usuario_id: Optional[int] = None,
    ) -> None:
        """
        Inserta un movimiento de puntos en la tabla `points_movements`.
        El campo `puntos` se inserta como integer (céntimos).
        """
        try:
            # Guardar puntos en céntimos (integer) para mantener consistencia
            puntos_cents = prepare_for_db(puntos)
            cur = self.db.connection.cursor()
            cur.execute(
                """
                INSERT INTO points_movements
                    (cliente_id, puntos, motivo, ticket_id, usuario_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cliente_id,
                    int(puntos_cents),
                    motivo,
                    ticket_id,
                    usuario_id,
                    datetime.now(),
                ),
            )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error insertando movimiento de puntos para cliente %s', cliente_id)
            raise

    def actualizar_loyalty_y_recalcular_nivel(
        self,
        cliente_id: int,
        puntos_otorgar_cents: int,
        puntos_restar_cents: int,
        puntos_gastados_cents: int,
        total_ticket_cents: int,
        unidades_vendidas: int,
        fecha: str,
    ) -> None:
        """
        Actualiza los campos de loyalty del cliente y recalcula su nivel
        dentro de una única transacción atómica.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')

            cur.execute(
                """
                UPDATE clientes
                SET
                    tesoro_total = COALESCE(tesoro_total, 0) + ?,
                    tesoro_historico = COALESCE(tesoro_historico, 0) + ?,
                    tesoro_gastado_total = COALESCE(tesoro_gastado_total, 0) + ?,
                    total_compras = COALESCE(total_compras, 0) + 1,
                    total_compras_euros = COALESCE(total_compras_euros, 0) + ?,
                    total_unidades = COALESCE(total_unidades, 0) + ?,
                    fecha_ultima_compra = ?
                WHERE id = ?
                """,
                (
                    int(puntos_otorgar_cents - puntos_restar_cents - puntos_gastados_cents),
                    int(puntos_otorgar_cents),
                    int(puntos_gastados_cents),
                    int(total_ticket_cents),
                    int(unidades_vendidas),
                    fecha,
                    cliente_id,
                ),
            )

            # Recalcular nivel según tesoro_historico actualizado
            cur.execute(
                """
                UPDATE clientes SET id_nivel = (
                    SELECT id FROM niveles_fidelidad
                    WHERE tesoro_minimo <= (
                        SELECT tesoro_historico FROM clientes WHERE id = ?
                    )
                    ORDER BY tesoro_minimo DESC LIMIT 1
                )
                WHERE id = ?
                """,
                (cliente_id, cliente_id),
            )

            self.db.connection.commit()

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                logger.exception('Rollback fallido en actualizar_loyalty_y_recalcular_nivel para cliente %s', cliente_id)
            logger.exception('Error en actualizar_loyalty_y_recalcular_nivel para cliente %s', cliente_id)
            raise

    def recalcular_nivel_cliente(self, cliente_id: int) -> None:
        """
        Actualiza `clientes.id_nivel` al nivel más alto cuyo `tesoro_minimo`
        sea <= `tesoro_historico` del cliente.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute(
                """
                UPDATE clientes SET id_nivel = (
                    SELECT id FROM niveles_fidelidad
                    WHERE tesoro_minimo <= (
                        SELECT tesoro_historico FROM clientes WHERE id = ?
                    )
                    ORDER BY tesoro_minimo DESC LIMIT 1
                )
                WHERE id = ?
                """,
                (cliente_id, cliente_id),
            )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error recalculando nivel para cliente %s', cliente_id)
            raise

    def obtener_tesoro_cliente(self, cliente_id: int) -> dict:
        """
        Devuelve un diccionario con los valores de tesoro del cliente
        convertidos a euros (Decimal) usando `read_from_db`.

        {'total': Decimal, 'historico': Decimal, 'gastado': Decimal}
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute(
                """
                SELECT tesoro_total,
                       tesoro_historico,
                       tesoro_gastado_total
                FROM clientes
                WHERE id = ?
                """,
                (cliente_id,),
            )
            row = cur.fetchone()
            if not row:
                return {'total': Decimal('0'), 'historico': Decimal('0'), 'gastado': Decimal('0')}

            return {
                'total': read_from_db(row[0]),
                'historico': read_from_db(row[1]),
                'gastado': read_from_db(row[2]),
            }
        except Exception:
            logger.exception('Error leyendo tesoro del cliente %s', cliente_id)
            raise

    def actualizar_fidelizacion_categoria(self, categoria_id: int, fide_porcentaje: float) -> None:
        """Actualiza el porcentaje de fidelización de una categoría."""
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute(
                "UPDATE categorias SET fide_porcentaje = ? WHERE id = ?",
                (fide_porcentaje, categoria_id)
            )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error actualizando fidelización categoría %s', categoria_id)
            raise

    def actualizar_fidelizacion_tipo(self, tipo_id: int, fide_porcentaje: float) -> None:
        """Actualiza el porcentaje de fidelización de un tipo."""
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute(
                "UPDATE tipos SET fide_porcentaje = ? WHERE id = ?",
                (fide_porcentaje, tipo_id)
            )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error actualizando fidelización tipo %s', tipo_id)
            raise

    def actualizar_fidelizacion_producto(self, producto_id: int, fide_tipo: str, fide_valor: float) -> None:
        """Actualiza el tipo y valor de fidelización de un producto."""
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
            cur.execute(
                "UPDATE productos SET fidelizacion_tipo = ?, fidelizacion_valor = ? WHERE id = ?",
                (fide_tipo, fide_valor, producto_id)
            )
            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error actualizando fidelización producto %s', producto_id)
            raise

    def actualizar_fidelizacion_productos_bulk(self, productos_updates: list) -> None:
        """
        Actualiza múltiples productos en UNA sola transacción atómica.

        Args:
            productos_updates: Lista de tuplas (producto_id, fide_tipo, fide_valor)
                               Ejemplo: [(1, 'porcentaje', 10), (2, 'fijo', 0.5), ...]

        Si falla CUALQUIERA -> NADA se guarda (rollback automático).
        Si todos OK -> TODOS se guardan (commit único).
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')

            for prod_id, fide_tipo, fide_valor in productos_updates:
                cur.execute(
                    "UPDATE productos SET fidelizacion_tipo = ?, fidelizacion_valor = ? WHERE id = ?",
                    (fide_tipo, fide_valor, prod_id)
                )

            self.db.connection.commit()
        except Exception:
            self.db.connection.rollback()
            logger.exception('Error en actualización masiva de fidelización productos')
            raise
