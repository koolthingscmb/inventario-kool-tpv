"""Servicio de Albaranes - CRUD y gestión de stock."""
import logging
from decimal import Decimal
from datetime import datetime
from kool_tpv.base_datos.money_adapter import read_from_db, prepare_for_db
from kool_tpv.modulos.almacen.albaran_repository import AlbaranRepository


class AlbaranService:
    def __init__(self, db):
        self.db = db
        self.repo = AlbaranRepository(db)

    def get_next_num_albaran(self):
        """Obtener el siguiente número de albarán disponible."""
        try:
            query = "SELECT MAX(num_albaran) FROM albaranes"
            row = self.db.fetch_one(query)
            last_num = row[0] if row and row[0] else 0
            return int(last_num) + 1
        except Exception:
            logging.exception('Error obteniendo siguiente num_albaran')
            return 1

    def buscar_producto_by_ean(self, ean):
        """Buscar producto por código EAN y devolver datos básicos.

        Returns:
            dict con {id, nombre, coste, tipo_iva} o None si no existe
        """
        try:
            query = """
        SELECT p.id, p.nombre, COALESCE(pr.coste, 0.0) AS coste, p.tipo_iva, COALESCE(pr.pvp, 0.0) AS pvp
        FROM productos p
        LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
        INNER JOIN codigos_barras cb ON cb.producto_id = p.id
        WHERE cb.ean = ?
        LIMIT 1
        """
            row = self.db.fetch_one(query, (ean,))
            if row:
                return {
                    'id': row[0],
                    'nombre': row[1] or '',
                    'coste': read_from_db(int(row[2] or 0)),
                    'tipo_iva': int(row[3] or 21),
                    'pvp': read_from_db(int(row[4] or 0))
                }
            return None
        except Exception:
            logging.exception('Error buscando producto por EAN')
            return None

    def save_albaran(self, num_albaran, proveedor_id, fecha, lines, tipo='ENTRADA'):
        """Guardar albarán con líneas y actualizar stock.

        Args:
            num_albaran: Número único del albarán
            proveedor_id: ID del proveedor
            fecha: Fecha en formato 'YYYY-MM-DD'
            lines: Lista de dicts con {producto_id, ean, nombre, cantidad, coste, descuento, tipo_iva}

        Returns:
            albaran_id si OK, None si error
        """
        try:
            tipo = tipo or 'ENTRADA'

            # Calcular totales y preparar líneas procesadas
            total_neto = Decimal('0.0')
            total_iva_4 = Decimal('0.0')
            total_iva_10 = Decimal('0.0')
            total_iva_21 = Decimal('0.0')
            lineas_procesadas = []

            for line in lines:
                producto_id = line.get('producto_id')
                ean = line.get('ean', '')
                nombre = line.get('nombre', '')
                cantidad = int(line.get('cantidad', 0))
                coste_dec = Decimal(str(line.get('coste', 0)))
                tipo_iva = int(line.get('tipo_iva', 21))

                importe_dec = coste_dec * Decimal(cantidad)
                total_neto += importe_dec

                iva_aplicable = Decimal(str(tipo_iva)) / Decimal('100')
                importe_iva = importe_dec * iva_aplicable
                if tipo_iva == 4:
                    total_iva_4 += importe_iva
                elif tipo_iva == 10:
                    total_iva_10 += importe_iva
                elif tipo_iva == 21:
                    total_iva_21 += importe_iva

                lineas_procesadas.append({
                    'producto_id': producto_id,
                    'ean': ean,
                    'nombre': nombre,
                    'cantidad': cantidad,
                    'coste': coste_dec,
                    'tipo_iva': tipo_iva,
                    'pvpr_cents': int(line.get('pvpr_cents', 0)),
                })

            total = total_neto + total_iva_4 + total_iva_10 + total_iva_21
            totales = {
                'total_neto': total_neto,
                'total_iva_4': total_iva_4,
                'total_iva_10': total_iva_10,
                'total_iva_21': total_iva_21,
                'total': total,
            }

            albaran_id = self.repo.guardar_albaran_completo(
                num_albaran, proveedor_id, fecha, tipo, lineas_procesadas, totales
            )
            logging.info(f'Albarán {num_albaran} guardado correctamente con ID {albaran_id}')
            return albaran_id

        except Exception:
            logging.exception('Error guardando albarán')
            return None

    def get_all_albaranes(self, limit=100):
        """Listar albaranes con datos básicos del proveedor.

        Returns:
            Lista de dicts con {id, num_albaran, fecha, proveedor_nombre, total}
        """
        try:
            query = """
        SELECT a.id, a.num_albaran, a.fecha, 
               COALESCE(p.nombre, 'Sin proveedor') AS proveedor_nombre,
               a.total
        FROM albaranes a
        LEFT JOIN proveedores p ON a.proveedor_id = p.id
        ORDER BY a.fecha DESC, a.num_albaran DESC
        LIMIT ?
        """
            rows = self.db.fetch_all(query, (limit,))
            albaranes = []
            for r in rows or []:
                albaranes.append({
                    'id': r[0],
                    'num_albaran': r[1],
                    'fecha': r[2],
                    'proveedor_nombre': r[3],
                    'total': read_from_db(int(r[4] or 0))
                })
            return albaranes
        except Exception:
            logging.exception('Error listando albaranes')
            return []

    def filtrar_albaranes(self, proveedor_id=None, fecha_desde=None, fecha_hasta=None, limit=100):
        """Filtrar albaranes por proveedor y/o rango de fechas.

        Args:
            proveedor_id (int, optional): ID del proveedor para filtrar
            fecha_desde (str, optional): Fecha inicio formato 'YYYY-MM-DD'
            fecha_hasta (str, optional): Fecha fin formato 'YYYY-MM-DD'
            limit (int): Número máximo de resultados (default 100)

        Returns:
            Lista de dicts con:
            {
                'id': int,
                'num_albaran': int,
                'fecha': str,
                'proveedor_nombre': str,
                'cant_productos': int,
                'total_neto': float,
                'total_iva': float,
                'total': float
            }
        """
        try:
            # Validaciones y normalizaciones
            try:
                if proveedor_id is not None:
                    proveedor_id = int(proveedor_id)
            except Exception:
                logging.warning(f'Proveedor_id inválido, ignorando filtro: {proveedor_id}')
                proveedor_id = None

            # Validar formato de fechas YYYY-MM-DD
            try:
                if fecha_desde:
                    datetime.strptime(fecha_desde, '%Y-%m-%d')
            except Exception:
                logging.warning(f'fecha_desde no tiene formato YYYY-MM-DD, ignorando: {fecha_desde}')
                fecha_desde = None

            try:
                if fecha_hasta:
                    datetime.strptime(fecha_hasta, '%Y-%m-%d')
            except Exception:
                logging.warning(f'fecha_hasta no tiene formato YYYY-MM-DD, ignorando: {fecha_hasta}')
                fecha_hasta = None

            logging.info(f"Filtrando albaranes: proveedor={proveedor_id}, desde={fecha_desde}, hasta={fecha_hasta}")

            query = """
        SELECT
        a.id,
        a.num_albaran,
        a.fecha,
        COALESCE(p.nombre, 'Sin proveedor') AS proveedor_nombre,
        COALESCE(SUM(al.cantidad), 0) AS cant_productos,
        a.total_neto,
        (a.total_iva_4 + a.total_iva_10 + a.total_iva_21) AS total_iva,
        a.total
        FROM albaranes a
        LEFT JOIN proveedores p ON a.proveedor_id = p.id
        LEFT JOIN albaran_lines al ON al.albaran_id = a.id
        WHERE 1=1
        """

            params = []
            if proveedor_id is not None:
                query += " AND a.proveedor_id = ?"
                params.append(proveedor_id)

            if fecha_desde:
                query += " AND a.fecha >= ?"
                params.append(fecha_desde)

            if fecha_hasta:
                query += " AND a.fecha <= ?"
                params.append(fecha_hasta)

            query += """
        GROUP BY a.id, a.num_albaran, a.fecha, p.nombre, a.total_neto,
        a.total_iva_4, a.total_iva_10, a.total_iva_21, a.total
        ORDER BY a.fecha DESC, a.num_albaran DESC
        LIMIT ?
        """
            params.append(limit)

            rows = self.db.fetch_all(query, tuple(params))
            albaranes = []
            for r in rows or []:
                albaranes.append({
                    'id': r[0],
                    'num_albaran': r[1],
                    'fecha': r[2],
                    'proveedor_nombre': r[3],
                    'cant_productos': int(r[4] or 0),
                    'total_neto': read_from_db(int(r[5] or 0)),
                    'total_iva': read_from_db(int(r[6] or 0)),
                    'total': read_from_db(int(r[7] or 0))
                })
            return albaranes
        except Exception:
            logging.exception('Error filtrando albaranes')
            return []

    def get_albaran_detalle(self, albaran_id):
        """Obtener albarán completo con líneas.

        Returns:
            dict con {albaran: {...}, lines: [...]} 
        """
        try:
            # Cabecera
            query_header = """
        SELECT a.id, a.num_albaran, a.fecha, a.proveedor_id,
               COALESCE(p.nombre, 'Sin proveedor') AS proveedor_nombre,
               a.total_neto, a.total_iva_4, a.total_iva_10, a.total_iva_21, a.total
        FROM albaranes a
        LEFT JOIN proveedores p ON a.proveedor_id = p.id
        WHERE a.id = ?
        """
            row = self.db.fetch_one(query_header, (albaran_id,))
            if not row:
                return None

            albaran = {
                'id': row[0],
                'num_albaran': row[1],
                'fecha': row[2],
                'proveedor_id': row[3],
                'proveedor_nombre': row[4],
                'total_neto': read_from_db(int(row[5] or 0)),
                'total_iva_4': read_from_db(int(row[6] or 0)),
                'total_iva_10': read_from_db(int(row[7] or 0)),
                'total_iva_21': read_from_db(int(row[8] or 0)),
                'total': read_from_db(int(row[9] or 0))
            }

            # Líneas
            query_lines = """
        SELECT id, producto_id, ean, nombre, cantidad, coste, tipo_iva, pvpr_cents
        FROM albaran_lines
        WHERE albaran_id = ?
        ORDER BY id ASC
        """
            rows_lines = self.db.fetch_all(query_lines, (albaran_id,))
            lines = []
            for rl in rows_lines or []:
                lines.append({
                    'id': rl[0],
                    'producto_id': rl[1],
                    'ean': rl[2] or '',
                    'nombre': rl[3] or '',
                    'cantidad': int(rl[4] or 0),
                    'coste': read_from_db(int(rl[5] or 0)),
                    'tipo_iva': int(rl[6] or 21),
                    'pvpr_cents': int(rl[7] or 0),
                })

            return {'albaran': albaran, 'lines': lines}

        except Exception:
            logging.exception('Error obteniendo detalle de albarán')
            return None

    def update_albaran_with_new_lines(self, albaran_id, all_lines):
        """Actualizar albarán con nuevas líneas añadidas y recalcular totales.

        Args:
            albaran_id (int): ID del albarán a actualizar
            all_lines (list): TODAS las líneas actuales del albarán (viejas con 'id' + nuevas sin 'id')
                             Cada línea debe tener: {producto_id, ean, nombre, cantidad, coste, descuento, tipo_iva}
                             Las líneas existentes tienen además: {'id': line_id}

        Returns:
            bool: True si OK, False si error

        Proceso:
            1. Recalcular totales con TODAS las líneas
            2. UPDATE cabecera albarán (totales)
            3. Filtrar líneas nuevas (sin 'id')
            4. INSERT líneas nuevas en albaran_lines
            5. UPDATE stock de productos nuevos
        """
        try:
            # 1. RECALCULAR TOTALES con TODAS las líneas (viejas + nuevas)
            total_neto = Decimal('0.0')
            total_iva_4 = Decimal('0.0')
            total_iva_10 = Decimal('0.0')
            total_iva_21 = Decimal('0.0')

            for line in all_lines:
                cantidad = Decimal(str(line.get('cantidad', 0)))
                coste = Decimal(str(line.get('coste', 0)))
                tipo_iva = int(line.get('tipo_iva', 21))

                importe_neto = coste * cantidad
                total_neto += importe_neto

                iva_aplicable = Decimal(str(tipo_iva)) / Decimal('100')
                importe_iva = importe_neto * iva_aplicable
                if tipo_iva == 4:
                    total_iva_4 += importe_iva
                elif tipo_iva == 10:
                    total_iva_10 += importe_iva
                elif tipo_iva == 21:
                    total_iva_21 += importe_iva

            total = total_neto + total_iva_4 + total_iva_10 + total_iva_21
            totales = {
                'total_neto': total_neto,
                'total_iva_4': total_iva_4,
                'total_iva_10': total_iva_10,
                'total_iva_21': total_iva_21,
                'total': total,
            }

            # 2. Filtrar y preparar SOLO líneas nuevas (sin 'id')
            new_lines = [l for l in all_lines if 'id' not in l or l.get('id') is None]
            logging.info(f'Actualizando albarán {albaran_id}: {len(new_lines)} líneas nuevas de {len(all_lines)} totales')

            nuevas_lineas_procesadas = []
            for line in new_lines:
                cantidad = int(line.get('cantidad', 0))
                coste_dec = Decimal(str(line.get('coste', 0)))
                nuevas_lineas_procesadas.append({
                    'producto_id': line.get('producto_id'),
                    'ean': line.get('ean', ''),
                    'nombre': line.get('nombre', ''),
                    'cantidad': cantidad,
                    'coste': coste_dec,
                    'tipo_iva': int(line.get('tipo_iva', 21)),
                    'pvpr_cents': int(line.get('pvpr_cents', 0)),
                })

            # 3. Delegar escritura al repo
            self.repo.actualizar_albaran_con_lineas(albaran_id, nuevas_lineas_procesadas, totales)
            logging.info(f'Albarán {albaran_id} actualizado: {len(new_lines)} líneas añadidas, totales recalculados')
            return True

        except Exception:
            logging.exception(f'Error actualizando albarán {albaran_id}')
            return False

    def delete_albaran(self, albaran_id):
        """Eliminar albarán (CASCADE elimina líneas automáticamente).

        ADVERTENCIA: NO revierte el stock. Debe hacerse manualmente si es necesario.
        """
        try:
            query = "DELETE FROM albaranes WHERE id = ?"
            self.db.execute_query(query, (albaran_id,))
            logging.info(f'Albarán {albaran_id} eliminado')
            return True
        except Exception:
            logging.exception('Error eliminando albarán')
            return False

    def buscar_productos_by_nombre(self, termino='', limit=50):
        """Buscar productos por nombre para autocompletado y buscador de albarán.

        Si termino está vacío devuelve todos los productos activos (carga inicial).
        Si termino tiene texto filtra por nombre.
        """
        try:
            query = """
        SELECT p.id, p.nombre, p.sku,
               COALESCE(pr.coste, 0.0) AS coste,
               p.tipo_iva,
               (SELECT cb.ean FROM codigos_barras cb WHERE cb.producto_id = p.id LIMIT 1) AS ean,
               COALESCE(pr.pvp, 0.0) AS pvp
        FROM productos p
        LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
        WHERE p.activo = 1 AND p.nombre LIKE ?
        ORDER BY p.nombre ASC
        LIMIT ?
        """

            termino_like = f'%{termino}%'
            rows = self.db.fetch_all(query, (termino_like, limit))

            resultados = []
            for r in rows or []:
                nombre_display = f"{r[1]} ({r[2]})" if r[2] else r[1]
                coste_val = read_from_db(int(r[3] or 0))
                pvp_val = read_from_db(int(r[6] or 0))
                # Si no hay coste activo, intentar fallback a cualquier precio histórico
                if coste_val == 0.0:
                    try:
                        q2 = "SELECT coste FROM precios WHERE producto_id = ? ORDER BY id DESC LIMIT 1"
                        row2 = self.db.fetch_one(q2, (r[0],))
                        if row2 and row2[0] is not None:
                            coste_val = read_from_db(int(row2[0] or 0))
                    except Exception:
                        pass
                if pvp_val == 0.0:
                    try:
                        q2 = "SELECT pvp FROM precios WHERE producto_id = ? ORDER BY id DESC LIMIT 1"
                        row2 = self.db.fetch_one(q2, (r[0],))
                        if row2 and row2[0] is not None:
                            pvp_val = read_from_db(int(row2[0] or 0))
                    except Exception:
                        pass

                resultados.append({
                    'id': r[0],
                    'nombre_display': nombre_display,
                    'nombre': r[1],
                    'sku': r[2] or '',
                    'coste': coste_val,
                    'tipo_iva': int(r[4] or 21),
                    'ean': r[5] or '',
                    'pvp': pvp_val
                })

            return resultados

        except Exception:
            logging.exception('Error buscando productos por nombre')
            return []
