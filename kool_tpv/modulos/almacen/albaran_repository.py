import logging
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)


class AlbaranRepository:
    def __init__(self, db: Database):
        self.db = db

    def guardar_albaran_completo(
        self, num_albaran, proveedor_id, fecha, tipo, lineas, totales, cur=None
    ) -> int:
        """Guarda albarán COMPLETO (cabecera + líneas + stock) en una transacción atómica."""
        if cur:
            return self._guardar_logic(num_albaran, proveedor_id, fecha, tipo, lineas, totales, cur)
        else:
            with self.db.transaction() as cur:
                return self._guardar_logic(num_albaran, proveedor_id, fecha, tipo, lineas, totales, cur)

    def _guardar_logic(
        self, num_albaran, proveedor_id, fecha, tipo, lineas, totales, cur
    ) -> int:
        try:
            tipo = tipo or 'ENTRADA'
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
                     coste, tipo_iva, editorial, fabricante, pvpr_cents, sku)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        line.get('sku', ''),
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

                    # Actualizar precio si el CSV trae PVPR
                    pvpr_cents = int(line.get('pvpr_cents', 0))
                    coste_cents = int(prepare_for_db(line.get('coste', 0)))
                    if pvpr_cents > 0:
                        try:
                            cur.execute(
                                'UPDATE precios SET activo = 0 WHERE producto_id = ?',
                                (line['producto_id'],)
                            )
                            cur.execute(
                                'INSERT INTO precios (producto_id, pvp, coste, activo) VALUES (?, ?, ?, 1)',
                                (line['producto_id'], pvpr_cents, coste_cents)
                            )
                            logger.info(
                                'Precio actualizado: producto %s → pvp=%s coste=%s',
                                line['producto_id'], pvpr_cents, coste_cents
                            )
                        except Exception as e:
                            logger.warning('Error actualizando precio producto %s: %s', line['producto_id'], e)

            logger.info('Albarán %s guardado con id=%s', num_albaran, albaran_id)
            return albaran_id

        except Exception:
            logger.exception('Error guardando albarán completo num=%s', num_albaran)
            raise

    def actualizar_albaran_con_lineas(
        self, albaran_id, todas_las_lineas, totales, cur=None
    ) -> None:
        """Actualiza cabecera de albarán + gestiona líneas (borra faltantes e inserta nuevas)."""
        if cur:
            self._actualizar_logic(albaran_id, todas_las_lineas, totales, cur)
        else:
            with self.db.transaction() as cur:
                self._actualizar_logic(albaran_id, todas_las_lineas, totales, cur)

    def _actualizar_logic(
        self, albaran_id, todas_las_lineas, totales, cur
    ) -> None:
        try:
            # 1. Actualizar cabecera
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

            # 2. Gestionar líneas
            # Obtener IDs actuales en BD
            cur.execute("SELECT id, producto_id, cantidad FROM albaran_lines WHERE albaran_id = ?", (albaran_id,))
            db_lines = {row[0]: {'producto_id': row[1], 'cantidad': row[2]} for row in cur.fetchall()}
            
            # IDs que nos llegan del service
            new_ids = {l['id'] for l in todas_las_lineas if 'id' in l}
            
            # A. Borrar líneas que ya no están
            ids_to_delete = set(db_lines.keys()) - new_ids
            if ids_to_delete:
                # Obtener tipo albarán para saber si revertir stock
                cur.execute("SELECT tipo FROM albaranes WHERE id = ?", (albaran_id,))
                row_tipo = cur.fetchone()
                tipo_alb = row_tipo[0] if row_tipo else 'ENTRADA'
                
                for lid in ids_to_delete:
                    old_l = db_lines[lid]
                    if old_l['producto_id']:
                        # Revertir stock (si era entrada, restamos; si era salida, sumamos)
                        adj = -old_l['cantidad'] if tipo_alb == 'ENTRADA' else old_l['cantidad']
                        try:
                            cur.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (adj, old_l['producto_id']))
                        except Exception as e:
                            logger.warning('Error al revertir stock de línea borrada %s: %s', lid, e)
                    
                    cur.execute("DELETE FROM albaran_lines WHERE id = ?", (lid,))

            # B. Insertar líneas nuevas (sin ID)
            # Obtener tipo albarán de nuevo para el stock de las nuevas si no se obtuvo antes
            cur.execute("SELECT tipo FROM albaranes WHERE id = ?", (albaran_id,))
            row_tipo = cur.fetchone()
            tipo_alb = row_tipo[0] if row_tipo else 'ENTRADA'

            for line in todas_las_lineas:
                if 'id' not in line:
                    cur.execute(
                        """
                        INSERT INTO albaran_lines
                        (albaran_id, producto_id, ean, nombre, cantidad,
                         coste, tipo_iva, editorial, fabricante, pvpr_cents, sku)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            line.get('sku', ''),
                        )
                    )

                    # Update stock para líneas nuevas de productos generales
                    if line['producto_id']:
                        cantidad_ajuste = line['cantidad'] if tipo_alb == 'ENTRADA' else -line['cantidad']
                        try:
                            cur.execute(
                                "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
                                (cantidad_ajuste, line['producto_id'])
                            )
                        except Exception as e:
                            logger.warning('Error actualizando stock producto %s: %s', line['producto_id'], e)

            logger.info('Albarán %s sincronizado: %s líneas borradas, %s líneas nuevas', 
                        albaran_id, len(ids_to_delete), len([l for l in todas_las_lineas if 'id' not in l]))

        except Exception:
            logger.exception('Error actualizando albarán id=%s', albaran_id)
            raise
