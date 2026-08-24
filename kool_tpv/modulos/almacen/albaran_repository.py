import logging
from decimal import Decimal
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.base_datos.audit_service import AuditService

logger = logging.getLogger(__name__)


class AlbaranRepository:
    def __init__(self, db: Database):
        self.db = db
        self.audit = AuditService(db)

    def guardar_albaran_completo(
        self, num_albaran, proveedor_id, fecha, tipo, lineas, totales, usuario_id=None, cur=None
    ) -> int:
        """Guarda albarán COMPLETO (cabecera + líneas + stock) en una transacción atómica."""
        if cur:
            return self._guardar_logic(num_albaran, proveedor_id, fecha, tipo, lineas, totales, usuario_id, cur)
        else:
            with self.db.transaction() as cur:
                return self._guardar_logic(num_albaran, proveedor_id, fecha, tipo, lineas, totales, usuario_id, cur)

    def _guardar_logic(
        self, num_albaran, proveedor_id, fecha, tipo, lineas, totales, usuario_id, cur
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

            # Auditoría
            self.audit.registrar(
                entidad='albaranes',
                entidad_id=albaran_id,
                accion='CREACION',
                usuario_id=usuario_id,
                datos_nuevos=f"Albarán {num_albaran} ({tipo}) - Total: {totales['total']}",
                cur=cur
            )

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

                # Sumar stock a todos los productos (existentes y nuevos)
                if line['producto_id']:
                    # Vínculo Pro: Asegurar que el EAN esté asociado al producto
                    if line.get('ean'):
                        try:
                            # Verificar si ya existe este EAN para este producto
                            cur.execute("SELECT 1 FROM codigos_barras WHERE producto_id = ? AND ean = ?", (line['producto_id'], line['ean']))
                            if not cur.fetchone():
                                logger.info(f"VINCULO PRO: Intentando vincular EAN {line['ean']} a producto_id {line['producto_id']}")
                                cur.execute("INSERT INTO codigos_barras (producto_id, ean) VALUES (?, ?)", (line['producto_id'], line['ean']))
                                logger.info(f"VINCULO PRO: OK - Nuevo EAN {line['ean']} vinculado a producto {line['producto_id']}")
                            else:
                                logger.debug(f"VINCULO PRO: EAN {line['ean']} ya estaba asociado al producto {line['producto_id']}")
                        except Exception as e:
                            logger.error(f"VINCULO PRO: ERROR vinculando EAN {line['ean']} a producto {line['producto_id']}: {e}")

                    cantidad_ajuste = line['cantidad'] if tipo == 'ENTRADA' else -line['cantidad']
                    try:
                        cur.execute(
                            "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?",
                            (cantidad_ajuste, line['producto_id'])
                        )
                        # Registrar movimiento de stock con usuario_id
                        cur.execute(
                            "INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id) VALUES (?, ?, ?, ?)",
                            (line['producto_id'], cantidad_ajuste, f"albaran:{num_albaran}", usuario_id)
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
        self, albaran_id, todas_las_lineas, totales, usuario_id=None, cur=None
    ) -> None:
        """Actualiza cabecera de albarán + gestiona líneas (borra faltantes e inserta nuevas)."""
        if cur:
            self._actualizar_logic(albaran_id, todas_las_lineas, totales, usuario_id, cur)
        else:
            with self.db.transaction() as cur:
                self._actualizar_logic(albaran_id, todas_las_lineas, totales, usuario_id, cur)

    def _actualizar_logic(
        self, albaran_id, todas_las_lineas, totales, usuario_id, cur
    ) -> None:
        try:
            # 1. Obtener datos previos para auditoría y tipo albarán
            cur.execute("SELECT tipo, num_albaran, total FROM albaranes WHERE id = ?", (albaran_id,))
            row_alb = cur.fetchone()
            tipo_alb = row_alb[0] if row_alb else 'ENTRADA'
            num_albaran = row_alb[1] if row_alb else str(albaran_id)
            old_total = row_alb[2] if row_alb else 0

            # 2. Actualizar cabecera
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

            # Auditoría
            self.audit.registrar(
                entidad='albaranes',
                entidad_id=albaran_id,
                accion='EDICION',
                usuario_id=usuario_id,
                datos_previos=f"Total previo: {old_total}",
                datos_nuevos=f"Nuevo total: {totales['total']}",
                cur=cur
            )

            # 3. Gestionar líneas (Sincronización de diferencias)
            # Obtener líneas actuales en BD
            cur.execute("SELECT id, producto_id, cantidad FROM albaran_lines WHERE albaran_id = ?", (albaran_id,))
            db_lines = {row[0]: {'producto_id': row[1], 'cantidad': row[2]} for row in cur.fetchall()}
            
            # Procesar las líneas que nos llegan
            new_ids = set()
            for line in todas_las_lineas:
                line_id = line.get('id')
                producto_id = line.get('producto_id')
                cantidad_nueva = line.get('cantidad', 0)

                if line_id and line_id in db_lines:
                    # LÍNEA EXISTENTE: Calcular diferencia neta
                    new_ids.add(line_id)
                    old_data = db_lines[line_id]
                    cantidad_vieja = old_data['cantidad']
                    
                    if cantidad_nueva != cantidad_vieja:
                        diff = cantidad_nueva - cantidad_vieja
                        # El ajuste al stock es la diferencia (positiva o negativa)
                        stock_adj = diff if tipo_alb == 'ENTRADA' else -diff
                        
                        if producto_id:
                            cur.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (stock_adj, producto_id))
                            # Log de movimiento con usuario_id
                            cur.execute(
                                "INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id) VALUES (?, ?, ?, ?)",
                                (producto_id, stock_adj, f"Edición Albarán {num_albaran} (Ajuste cantidad)", usuario_id)
                            )
                    
                    # Actualizar la línea en BD
                    cur.execute(
                        """
                        UPDATE albaran_lines 
                        SET cantidad = ?, coste = ?, tipo_iva = ?, pvpr_cents = ?, sku = ?
                        WHERE id = ?
                        """,
                        (
                            cantidad_nueva,
                            int(prepare_for_db(line['coste'])),
                            line['tipo_iva'],
                            int(line.get('pvpr_cents', 0)),
                            line.get('sku', ''),
                            line_id
                        )
                    )
                else:
                    # LÍNEA NUEVA: Insertar y sumar stock total
                    cur.execute(
                        """
                        INSERT INTO albaran_lines
                        (albaran_id, producto_id, ean, nombre, cantidad,
                         coste, tipo_iva, editorial, fabricante, pvpr_cents, sku)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            albaran_id,
                            producto_id,
                            line['ean'],
                            line['nombre'],
                            cantidad_nueva,
                            int(prepare_for_db(line['coste'])),
                            line['tipo_iva'],
                            line.get('editorial', ''),
                            line.get('fabricante', ''),
                            int(line.get('pvpr_cents', 0)),
                            line.get('sku', ''),
                        )
                    )
                    if producto_id:
                        # Vínculo Pro: Asegurar que el EAN esté asociado al producto
                        if line.get('ean'):
                            try:
                                cur.execute("SELECT 1 FROM codigos_barras WHERE producto_id = ? AND ean = ?", (producto_id, line['ean']))
                                if not cur.fetchone():
                                    logger.info(f"VINCULO PRO (Edición): Intentando vincular EAN {line['ean']} a producto_id {producto_id}")
                                    cur.execute("INSERT INTO codigos_barras (producto_id, ean) VALUES (?, ?)", (producto_id, line['ean']))
                                    logger.info(f"VINCULO PRO (Edición): OK - Nuevo EAN {line['ean']} vinculado a producto {producto_id}")
                                else:
                                    logger.debug(f"VINCULO PRO (Edición): EAN {line['ean']} ya estaba asociado al producto {producto_id}")
                            except Exception as e:
                                logger.error(f"VINCULO PRO (Edición): ERROR vinculando EAN {line['ean']} a producto {producto_id}: {e}")

                        stock_adj = cantidad_nueva if tipo_alb == 'ENTRADA' else -cantidad_nueva
                        cur.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (stock_adj, producto_id))
                        cur.execute(
                            "INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id) VALUES (?, ?, ?, ?)",
                            (producto_id, stock_adj, f"Edición Albarán {num_albaran} (Línea añadida)", usuario_id)
                        )

            # 4. Borrar líneas que ya no están en la lista (Líneas eliminadas)
            ids_to_delete = set(db_lines.keys()) - new_ids
            for lid in ids_to_delete:
                old_l = db_lines[lid]
                if old_l['producto_id']:
                    # Revertir stock completamente
                    adj = -old_l['cantidad'] if tipo_alb == 'ENTRADA' else old_l['cantidad']
                    cur.execute("UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?", (adj, old_l['producto_id']))
                    cur.execute(
                        "INSERT INTO stock_movements (producto_id, cantidad, motivo, usuario_id) VALUES (?, ?, ?, ?)",
                        (old_l['producto_id'], adj, f"Edición Albarán {num_albaran} (Línea eliminada)", usuario_id)
                    )
                cur.execute("DELETE FROM albaran_lines WHERE id = ?", (lid,))

            logger.info('Albarán %s sincronizado correctamente', num_albaran)

        except Exception:
            logger.exception('Error actualizando albarán id=%s', albaran_id)
            raise
