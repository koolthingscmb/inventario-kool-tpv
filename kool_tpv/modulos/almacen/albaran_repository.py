import logging
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)


class AlbaranRepository:
    def __init__(self, db: Database):
        self.db = db

    def guardar_albaran_completo(
        self, num_albaran, proveedor_id, fecha, tipo, lineas, totales
    ) -> int:
        """Guarda albarán COMPLETO (cabecera + líneas + stock) en una transacción atómica.

        Args:
            num_albaran: número del albarán
            proveedor_id: ID del proveedor
            fecha: fecha string 'YYYY-MM-DD'
            tipo: 'ENTRADA', 'SALIDA' o 'DEVOLUCIÓN'
            lineas: list of {producto_id, ean, nombre, cantidad (int),
                             coste (Decimal), descuento (Decimal),
                             importe (Decimal), tipo_iva (int)}
            totales: {total_neto, total_iva_4, total_iva_10, total_iva_21, total} (Decimal)

        Returns:
            albaran_id (int)
        Raises:
            Exception si falla
        """
        try:
            tipo = tipo or 'ENTRADA'
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')

            cur.execute(
                """
                INSERT INTO albaranes
                (num_albaran, proveedor_id, fecha, total_neto,
                 total_iva_4, total_iva_10, total_iva_21, total, tipo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    num_albaran, proveedor_id, fecha,
                    int(prepare_for_db(totales['total_neto'])),
                    int(prepare_for_db(totales['total_iva_4'])),
                    int(prepare_for_db(totales['total_iva_10'])),
                    int(prepare_for_db(totales['total_iva_21'])),
                    int(prepare_for_db(totales['total'])),
                    tipo,
                )
            )
            albaran_id = cur.lastrowid

            for line in lineas:
                cur.execute(
                    """
                    INSERT INTO albaran_lines
                    (albaran_id, producto_id, ean, nombre, cantidad,
                     coste, tipo_iva, editorial, fabricante, pvpr_cents)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        albaran_id,
                        line['producto_id'],
                        line['ean'],
                        line['nombre'],
                        line['cantidad'],
                        int(prepare_for_db(line['coste'])),
                        line['tipo_iva'],
                        line.get('editorial', ''),
                        line.get('fabricante', ''),
                        int(line.get('pvpr_cents', 0)),
                    )
                )

                # Solo sumar stock a productos EXISTENTES (no a nuevos creados desde albarán)
                if line['producto_id'] and not line.get('es_producto_nuevo', False):
                    cantidad_ajuste = line['cantidad'] if tipo == 'ENTRADA' else -line['cantidad']
                    try:
                        cur.execute(
                            "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
                            (cantidad_ajuste, line['producto_id'])
                        )
                    except Exception as e:
                        logger.warning('Error actualizando stock producto %s: %s', line['producto_id'], e)

            self.db.connection.commit()
            logger.info('Albarán %s guardado con id=%s', num_albaran, albaran_id)
            return albaran_id

        except Exception:
            self.db.connection.rollback()
            logger.exception('Error guardando albarán completo num=%s', num_albaran)
            raise

    def actualizar_albaran_con_lineas(
        self, albaran_id, nuevas_lineas, totales
    ) -> None:
        """Actualiza cabecera de albarán + inserta líneas nuevas + actualiza stock.

        Solo inserta las líneas nuevas (sin 'id'). Las líneas existentes no se tocan.

        Args:
            albaran_id: ID del albarán
            nuevas_lineas: list of {producto_id, ean, nombre, cantidad (int),
                                    coste (Decimal), descuento (Decimal),
                                    importe (Decimal), tipo_iva (int)}
            totales: {total_neto, total_iva_4, total_iva_10, total_iva_21, total} (Decimal)

        Raises:
            Exception si falla
        """
        try:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')

            cur.execute(
                """
                UPDATE albaranes
                SET total_neto = ?, total_iva_4 = ?, total_iva_10 = ?,
                    total_iva_21 = ?, total = ?
                WHERE id = ?
                """,
                (
                    int(prepare_for_db(totales['total_neto'])),
                    int(prepare_for_db(totales['total_iva_4'])),
                    int(prepare_for_db(totales['total_iva_10'])),
                    int(prepare_for_db(totales['total_iva_21'])),
                    int(prepare_for_db(totales['total'])),
                    albaran_id,
                )
            )

            for line in nuevas_lineas:
                cur.execute(
                    """
                    INSERT INTO albaran_lines
                    (albaran_id, producto_id, ean, nombre, cantidad,
                     coste, tipo_iva, editorial, fabricante, pvpr_cents)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        albaran_id,
                        line['producto_id'],
                        line['ean'],
                        line['nombre'],
                        line['cantidad'],
                        int(prepare_for_db(line['coste'])),
                        line['tipo_iva'],
                        line.get('editorial', ''),
                        line.get('fabricante', ''),
                        int(line.get('pvpr_cents', 0)),
                    )
                )

                if line['producto_id']:
                    try:
                        cur.execute(
                            "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
                            (line['cantidad'], line['producto_id'])
                        )
                        logger.debug('Stock actualizado: producto %s +%s', line['producto_id'], line['cantidad'])
                    except Exception as e:
                        logger.warning('Error actualizando stock producto %s: %s', line['producto_id'], e)

            self.db.connection.commit()
            logger.info('Albarán %s actualizado: %s líneas nuevas', albaran_id, len(nuevas_lineas))

        except Exception:
            self.db.connection.rollback()
            logger.exception('Error actualizando albarán id=%s', albaran_id)
            raise
