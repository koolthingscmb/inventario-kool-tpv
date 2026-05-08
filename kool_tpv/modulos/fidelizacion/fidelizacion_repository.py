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
        puntos_otorgar: Decimal,
        puntos_restar: Decimal,
        puntos_gastados: Decimal,
        total_ticket: Decimal,
        unidades_vendidas: int,
        fecha: str,
    ) -> None:
        """
        Actualiza los campos de fidelización del cliente dentro de la transacción
        externa que ya está abierta (no hace commit/rollback aquí).
        """
        try:
            # Convertir a céntimos los valores monetarios
            delta_tesoro = prepare_for_db(puntos_otorgar - (puntos_restar + puntos_gastados))
            delta_historico = prepare_for_db(puntos_otorgar - puntos_restar)
            delta_gastado = prepare_for_db(puntos_gastados)
            total_ticket_cents = prepare_for_db(total_ticket)

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
                    int(delta_tesoro),
                    int(delta_historico),
                    int(delta_gastado),
                    int(total_ticket_cents),
                    int(unidades_vendidas),
                    fecha,
                    cliente_id,
                ),
            )

        except Exception:
            logger.exception('Error actualizando loyalty para cliente %s', cliente_id)
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
        except Exception:
            logger.exception('Error insertando movimiento de puntos para cliente %s', cliente_id)
            raise

    def recalcular_nivel_cliente(self, cliente_id: int) -> None:
        """
        Actualiza `clientes.id_nivel` al nivel más alto cuyo `gasto_minimo`
        sea <= `tesoro_historico` del cliente.
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute(
                """
                UPDATE clientes SET id_nivel = (
                    SELECT id FROM niveles_fidelidad
                    WHERE gasto_minimo <= (
                        SELECT tesoro_historico FROM clientes WHERE id = ?
                    )
                    ORDER BY gasto_minimo DESC LIMIT 1
                )
                WHERE id = ?
                """,
                (cliente_id, cliente_id),
            )
        except Exception:
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
