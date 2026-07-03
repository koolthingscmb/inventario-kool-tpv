"""Servicio para operaciones peligrosas de reseteo/limpieza de la base de datos.

Contiene utilidades usadas desde la UI de configuración para borrar tickets,
movimientos, albaranes y resetear contadores. Estas operaciones deben ser usadas
solo en entornos de desarrollo o con extremo cuidado.
"""

import logging
import datetime
from typing import List, Optional

# SQL compartido para resetear TODOS los campos estadísticos de un cliente.
# Usado en reset_estadisticas_clientes y reset_completo.
_CLIENTES_RESET_SET = """
    SET tesoro_total = 0,
        tesoro_gastado_total = 0,
        tesoro_historico = 0,
        id_nivel = (SELECT id FROM niveles_fidelidad ORDER BY tesoro_minimo ASC LIMIT 1),
        total_compras = 0,
        total_compras_euros = 0,
        total_unidades = 0,
        total_devoluciones = 0,
        fecha_ultima_compra = NULL,
        fecha_vencimiento_tesoro = NULL,
        fecha_ultima_comunicacion = NULL
"""


class ResetService:
    """Servicio para operaciones de reset y limpieza de BD (desarrollo)."""

    def __init__(self, db):
        self.db = db

    def reset_estadisticas_clientes(self, cliente_ids: Optional[List[int]] = None) -> bool:
        """Resetear todos los campos estadísticos de clientes.

        Incluye tesoro, nivel, compras, unidades y fechas.
        If `cliente_ids` is None resetea todos los clientes.
        """
        try:
            conn = self.db.connection
            cur = conn.cursor()

            if cliente_ids:
                placeholders = ','.join('?' * len(cliente_ids))
                cur.execute(
                    f"UPDATE clientes {_CLIENTES_RESET_SET} WHERE id IN ({placeholders})",
                    cliente_ids,
                )
                logging.info('Estadísticas reseteadas para %s clientes', len(cliente_ids))
            else:
                cur.execute(f"UPDATE clientes {_CLIENTES_RESET_SET}")
                logging.warning('Estadísticas reseteadas para TODOS los clientes')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando estadísticas de clientes')
            return False

    # Alias para compatibilidad con llamadas existentes en UI
    def reset_tesoro_clientes(self, cliente_ids: Optional[List[int]] = None) -> bool:
        return self.reset_estadisticas_clientes(cliente_ids)

    def borrar_ticket_lines(self, ticket_ids: Optional[List[int]] = None) -> bool:
        """Borrar líneas de tickets. Si ticket_ids es None borra TODAS las líneas."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")

            if ticket_ids:
                placeholders = ','.join('?' * len(ticket_ids))
                cur.execute(
                    f"DELETE FROM ticket_lines WHERE ticket_id IN ({placeholders})",
                    ticket_ids,
                )
                logging.info('ticket_lines borradas para tickets: %s', ticket_ids)
            else:
                cur.execute("DELETE FROM ticket_lines")
                logging.warning('TODAS las ticket_lines borradas')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando ticket_lines')
            return False

    def borrar_tickets(self, ticket_nums: Optional[List[int]] = None) -> bool:
        """Borrar tickets por num_ticket (CASCADE limpia movimientos y ticket_lines)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            if ticket_nums:
                placeholders = ','.join('?' * len(ticket_nums))
                # Eliminar stock_movements relacionados con las líneas de esos tickets
                cur.execute(
                    f"DELETE FROM stock_movements WHERE ticket_line_id IN (SELECT id FROM ticket_lines WHERE ticket_id IN (SELECT id FROM tickets WHERE num_ticket IN ({placeholders})))",
                    ticket_nums,
                )
                # Eliminar points_movements relacionados con esos tickets
                cur.execute(
                    f"DELETE FROM points_movements WHERE ticket_id IN (SELECT id FROM tickets WHERE num_ticket IN ({placeholders}))",
                    ticket_nums,
                )
                # devoluciones no tiene ON DELETE CASCADE, borrar manualmente
                cur.execute(
                    f"DELETE FROM devoluciones WHERE ticket_id IN "
                    f"(SELECT id FROM tickets WHERE num_ticket IN ({placeholders}))",
                    ticket_nums,
                )
                # Finalmente borrar los tickets
                cur.execute(f"DELETE FROM tickets WHERE num_ticket IN ({placeholders})", ticket_nums)
                logging.info('Tickets borrados: %s', ticket_nums)
            else:
                # Borrado global: eliminar movimientos y referencias antes de tickets
                cur.execute("DELETE FROM stock_movements")
                cur.execute("DELETE FROM points_movements")
                cur.execute("DELETE FROM devoluciones")
                cur.execute("DELETE FROM tickets")
                logging.warning('TODOS los tickets borrados (movimientos y referencias eliminados previamente)')

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
            cur.execute("PRAGMA foreign_keys = ON")

            cur.execute("DELETE FROM cierres")
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
            cur.execute("PRAGMA foreign_keys = ON")

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
            cur.execute("PRAGMA foreign_keys = ON")

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

            year_actual = datetime.datetime.now().year

            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('ticket_counter_value', '0')"
            )
            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('ticket_counter_year', ?)",
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

            year_actual = datetime.datetime.now().year

            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('cierre_counter_value', '0')"
            )
            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('cierre_counter_year', ?)",
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

            year_actual = datetime.datetime.now().year

            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('albaran_counter_value', '0')"
            )
            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('albaran_counter_year', ?)",
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

            year_actual = datetime.datetime.now().year

            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('factura_counter_value', '0')"
            )
            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('factura_counter_year', ?)",
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
            cur.execute("PRAGMA foreign_keys = ON")

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

    def borrar_points_movements(self) -> bool:
        """Borrar todos los movimientos de puntos de fidelización."""
        try:
            conn = self.db.connection
            cur = conn.cursor()

            cur.execute("DELETE FROM points_movements")
            logging.warning('TODOS los points_movements borrados')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando points_movements')
            return False

    def reset_stock_productos(self) -> bool:
        """Poner stock_actual y ventas_totales a 0 en todos los productos."""
        try:
            conn = self.db.connection
            cur = conn.cursor()

            cur.execute("UPDATE productos SET stock_actual = 0, ventas_totales = 0")
            logging.warning('stock_actual y ventas_totales reseteados a 0 en TODOS los productos')

            conn.commit()
            return True

        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando stock/ventas productos')
            return False

    def borrar_produccion_ordenes(self) -> bool:
        """Borrar TODAS las órdenes de producción y sus líneas (CASCADE)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM produccion_lineas")
            cur.execute("DELETE FROM produccion_ordenes")
            logging.warning('TODAS las órdenes y líneas de producción borradas')
            conn.commit()
            return True
        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando órdenes de producción')
            return False

    def borrar_produccion_stock_disenos(self) -> bool:
        """Borrar TODO el stock acumulado de diseños."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("DELETE FROM produccion_disenos_stock")
            logging.warning('Stock de diseños borrado')
            conn.commit()
            return True
        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando stock de diseños')
            return False

    def borrar_produccion_stock_bases(self) -> bool:
        """Borrar TODO el stock de bases (stock_colores_tallas)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("DELETE FROM produccion_stock_colores_tallas")
            logging.warning('Stock de bases borrado')
            conn.commit()
            return True
        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando stock de bases')
            return False

    def borrar_produccion_recetas(self) -> bool:
        """Borrar TODAS las recetas (tipo_color_tallas)."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("DELETE FROM produccion_tipo_color_tallas")
            logging.warning('Recetas (tipo_color_tallas) borradas')
            conn.commit()
            return True
        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error borrando recetas')
            return False

    def reset_produccion_contadores(self) -> bool:
        """Resetear los AUTOINCREMENT de las tablas de producción a 0."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('produccion_ordenes', 'produccion_lineas', 'produccion_disenos_stock', 'produccion_stock_colores_tallas', 'produccion_tipo_color_tallas')")
            logging.warning('Contadores AUTOINCREMENT de producción reseteados')
            conn.commit()
            return True
        except Exception:
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            logging.exception('Error reseteando contadores de producción')
            return False

    def reset_completo(self) -> bool:
        """Reset TOTAL: borra tickets, cierres, albaranes, facturas, resetea contadores y estadísticas clientes."""
        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = OFF")

            # Borrar en orden: hijos antes que padres
            # Devoluciones y líneas hijas
            cur.execute("DELETE FROM devoluciones")
            logging.warning('RESET COMPLETO: devoluciones borradas')

            # Líneas de tickets antes que tickets
            cur.execute("DELETE FROM payments")
            cur.execute("DELETE FROM ticket_lines")
            cur.execute("DELETE FROM stock_movements")
            cur.execute("DELETE FROM tickets")
            logging.warning('RESET COMPLETO: tickets, pagos, líneas y movimientos borrados')

            # Cierres y sus líneas
            cur.execute("DELETE FROM cierres_lineas")
            cur.execute("DELETE FROM cierres")
            logging.warning('RESET COMPLETO: cierres borrados')

            # Albaranes y sus líneas
            cur.execute("DELETE FROM albaran_lines")
            cur.execute("DELETE FROM albaranes")
            logging.warning('RESET COMPLETO: albaranes borrados')

            # Facturas y sus líneas
            cur.execute("DELETE FROM facturas_lines")
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

            cur.execute(f"UPDATE clientes {_CLIENTES_RESET_SET}")
            logging.warning('RESET COMPLETO: estadísticas clientes reseteadas')

            # Productos y catálogo
            cur.execute("DELETE FROM productos")
            cur.execute("DELETE FROM precios")
            cur.execute("DELETE FROM favoritos")
            cur.execute("DELETE FROM stock_movements")
            cur.execute("DELETE FROM descuentos")
            cur.execute("DELETE FROM categorias WHERE id != 1")
            cur.execute("DELETE FROM tipos WHERE id != 1")
            cur.execute("DELETE FROM proveedores")
            logging.warning('RESET COMPLETO: productos, precios, favoritos, categorias, tipos extra y proveedores borrados')

            # Producción — cada DELETE en su propio try/except por si alguna tabla no existe
            _tablas_prod = [
                'produccion_disenos_ventas',
                'produccion_disenos_metodos',
                'produccion_lineas', 'produccion_ordenes', 'produccion_disenos_stock',
                'produccion_disenos_tipos', 'produccion_disenos_costes',
                'produccion_disenos',
                'produccion_stock_colores_tallas', 'produccion_tipo_color_tallas',
                'produccion_menu_tipos', 'produccion_menu',
                'produccion_genero_colores', 'produccion_genero_color_tallas',
                'produccion_estados',
                'produccion_variantes_productos', 'tipos_variantes'
            ]
            for tbl in _tablas_prod:
                try:
                    cur.execute(f"DELETE FROM {tbl}")
                except Exception:
                    pass
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('tickets', 'ticket_lines', 'payments', 'cierres', 'cierres_lineas', 'albaranes', 'albaran_lines', 'facturas', 'facturas_lines', 'devoluciones', 'stock_movements', 'produccion_ordenes', 'produccion_lineas', 'produccion_disenos_stock', 'produccion_stock_colores_tallas', 'produccion_tipo_color_tallas', 'produccion_disenos', 'produccion_menu', 'categorias', 'tipos', 'productos', 'precios', 'descuentos', 'proveedores', 'favoritos', 'produccion_variantes_productos', 'tipos_variantes')")
            except Exception:
                pass
            logging.warning('RESET COMPLETO: datos de producción y catálogo borrados, contadores reseteados')

            cur.execute("PRAGMA foreign_keys = ON")
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
