from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
import logging

from kool_tpv.modulos.ticket.base_processor import TicketProcessor
from kool_tpv.base_datos.cierre_service import CierreService
from kool_tpv.base_datos.money_adapter import read_from_db
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
from kool_tpv.modulos.impresion.ticket_type import TicketType
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService


class CierreCajaProcessor(TicketProcessor):
    def process(self, ticket_ids: Optional[List[int]] = None, usuario_id: Optional[int] = None, cajero: Optional[str] = None, cierre_text: Optional[str] = None, imprimir: bool = True, printer_name: Optional[str] = None, print_options: Optional[dict] = None):
        """Crear un cierre a partir de `ticket_ids`.

        Pasos:
        - Si no se pasan `ticket_ids`, tomar todos los tickets con `cierre_id IS NULL`.
        - Calcular totales, crear cierre atómico (`CierreService.create_cierre_atomic`).
        - Insertar filas en `cierres_lineas` con resumen por ticket.
        - (Opcional) imprimir el cierre usando `ImpresoraService`.

        Retorna dict con `success`, `cierre_id` y `num_tickets` o `error`.
        """
        # Obtener ticket ids si no se especificaron
        if not ticket_ids:
            self.db.connect()
            rows = self.db.fetch_all('SELECT id FROM tickets WHERE cierre_id IS NULL ORDER BY created_at ASC')
            ticket_ids = [r[0] for r in (rows or [])]

        if not ticket_ids:
            return {'success': False, 'error': 'no_ticket_ids'}

        cierre_svc = CierreService(self.db)

        # calcular totales para pasar al generador e insertar en cierre
        totals = cierre_svc.compute_totals_for_ticket_ids(ticket_ids)

        # Calcular y agregar tesoro ANTES de guardar en BD
        try:
            puntos_resumen = cierre_svc.get_puntos_resumen_cierre(ticket_ids)
            totals['tesoro_otorgado'] = puntos_resumen.get('tesoro_otorgado', Decimal('0'))
            totals['tesoro_gastado'] = puntos_resumen.get('tesoro_gastado', Decimal('0'))
            totals['clientes_puntos'] = puntos_resumen.get('clientes_puntos', [])
        except Exception:
            logging.exception('Error agregando resumen de puntos a totals en cierre')
            totals['tesoro_otorgado'] = Decimal('0')
            totals['tesoro_gastado'] = Decimal('0')
            totals['clientes_puntos'] = []

        # crear el cierre (inserta en `cierres` y marca tickets)
        cierre_id = cierre_svc.create_cierre_atomic(ticket_ids, usuario_id, cajero, cierre_text=cierre_text)
        if cierre_id is None:
            return {'success': False, 'error': 'create_failed'}

        # Recuperar registros de tickets para poblar cierres_lineas
        placeholders = ','.join(['?'] * len(ticket_ids))
        sql = f"SELECT id, num_ticket, total, forma_pago, importe_efectivo, importe_tarjeta, importe_web, descuento_euros, tesoro_ganado, tesoro_gastado FROM tickets WHERE id IN ({placeholders})"
        self.db.connect()
        ticket_rows = self.db.fetch_all(sql, tuple(ticket_ids))

        # Calcular agregados de VENTAS a nivel de tickets (para pasar al generador)
        try:
            from kool_tpv.base_datos.money_adapter import read_from_db

            ventas_count = 0
            devoluciones_count = 0
            total_facturas = Decimal('0')
            total_devoluciones = Decimal('0')

            for tr in ticket_rows or []:
                try:
                    total_cents = int(tr[2] or 0)
                    total_euros = read_from_db(total_cents)
                    if total_cents < 0:
                        devoluciones_count += 1
                        total_devoluciones += abs(total_euros)
                    else:
                        ventas_count += 1
                        total_facturas += total_euros
                except Exception:
                    continue

            totals['ventas_count'] = ventas_count
            totals['devoluciones_count'] = devoluciones_count
            totals['total_facturas'] = total_facturas
            totals['total_devoluciones'] = total_devoluciones
            totals['total_ventas_net'] = (total_facturas - total_devoluciones)
        except Exception:
            # No interrumpir el proceso si falla el cálculo, dejar totals como estaban
            pass

        # Calcular ventas y devoluciones por categoría (excluir devoluciones del bloque VENTAS)
        try:
            cat_svc = CategoriaService(self.db)
            # ventas: solo líneas de tipo 'venta'
            ventas_cat = cat_svc.get_ventas_por_categoria(ticket_ids, line_tipo='venta', as_dict=True) or []
            ventas_cat_simple = []
            for entry in ventas_cat:
                try:
                    if isinstance(entry, dict):
                        nombre = entry.get('nombre')
                        uds = int(entry.get('uds', 0) or 0)
                        total_euros = entry.get('total')
                    else:
                        # backward-compat: tuple (nombre, tickets_cnt, uds, total)
                        nombre = entry[0]
                        uds = int(entry[2] or 0) if len(entry) > 2 else int(entry[1] or 0)
                        total_euros = entry[3] if len(entry) > 3 else entry[2]
                    ventas_cat_simple.append((nombre, uds, total_euros))
                except Exception:
                    continue

            # devoluciones: solo líneas de tipo 'devolucion'
            devol_cat = cat_svc.get_ventas_por_categoria(ticket_ids, line_tipo='devolucion', as_dict=True) or []
            devol_cat_simple = []
            for entry in devol_cat:
                try:
                    if isinstance(entry, dict):
                        nombre = entry.get('nombre')
                        uds = int(entry.get('uds', 0) or 0)
                        total_euros = entry.get('total')
                    else:
                        nombre = entry[0]
                        uds = int(entry[2] or 0) if len(entry) > 2 else int(entry[1] or 0)
                        total_euros = entry[3] if len(entry) > 3 else entry[2]
                    devol_cat_simple.append((nombre, uds, total_euros))
                except Exception:
                    continue

            if ventas_cat_simple:
                totals['ventas_por_categoria'] = ventas_cat_simple
            if devol_cat_simple:
                totals['devoluciones_por_categoria'] = devol_cat_simple
        except Exception:
            # no detener la creación del cierre por falta de desglose por categoría
            pass

        # Calcular ventas por tipo (solo 'venta') y añadir a totals en formato simple
        try:
            tipo_svc = TipoService(self.db)
            tipos_ventas = tipo_svc.get_ventas_por_tipo(ticket_ids, line_tipo='venta', as_dict=True) or []
            tipos_simple = []
            for entry in tipos_ventas:
                try:
                    if isinstance(entry, dict):
                        nombre = entry.get('nombre')
                        uds = int(entry.get('uds', 0) or 0)
                        total_euros = entry.get('total')
                    else:
                        nombre = entry[0]
                        uds = int(entry[2] or 0) if len(entry) > 2 else int(entry[1] or 0)
                        total_euros = entry[3] if len(entry) > 3 else entry[2]
                    tipos_simple.append((nombre, uds, total_euros))
                except Exception:
                    continue
            if tipos_simple:
                totals['ventas_por_tipo'] = tipos_simple
        except Exception:
            pass

        # Calcular ventas por cajero y productos (NECESARIO PARA EL GENERADOR)
        try:
            totals['ventas_por_cajero'] = cierre_svc.get_ventas_por_cajero_para_tickets(ticket_ids)
            from kool_tpv.base_datos.producto_service import ProductoService
            prod_svc = ProductoService(self.db)
            totals['productos'] = prod_svc.get_ventas_por_producto(ticket_ids)
        except Exception:
            logging.exception('Error calculando desgloses de cajero/productos en processor')

        # devoluciones por tipo: sólo líneas 'devolucion'
        try:
            tipo_svc = TipoService(self.db)
            tipos_devol = tipo_svc.get_ventas_por_tipo(ticket_ids, line_tipo='devolucion', as_dict=True) or []
            tipos_devol_simple = []
            for entry in tipos_devol:
                try:
                    if isinstance(entry, dict):
                        nombre = entry.get('nombre')
                        uds = int(entry.get('uds', 0) or 0)
                        total_euros = entry.get('total')
                    else:
                        nombre = entry[0]
                        uds = int(entry[2] or 0) if len(entry) > 2 else int(entry[1] or 0)
                        total_euros = entry[3] if len(entry) > 3 else entry[2]
                    tipos_devol_simple.append((nombre, uds, total_euros))
                except Exception:
                    continue
            if tipos_devol_simple:
                totals['devoluciones_por_tipo'] = tipos_devol_simple
        except Exception:
            pass


        # Insertar en cierres_lineas
        cur = getattr(self.db, 'connection', None).cursor()
        insert_sql = (
            'INSERT INTO cierres_lineas (cierre_id, ticket_id, ticket_num, ticket_total, forma_pago, efectivo, tarjeta, web, descuentos, devoluciones, tesoro_ganado, tesoro_gastado, notas) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        )

        tickets_for_print = []

        for tr in ticket_rows or []:
            try:
                tid = int(tr[0])
                num_ticket = tr[1]
                total_db = int(tr[2] or 0)
                forma = str(tr[3] or '')
                efectivo_db = int(tr[4] or 0)
                tarjeta_db = int(tr[5] or 0)
                web_db = int(tr[6] or 0) if len(tr) > 6 else 0

                # Extraer nuevos campos con validación
                descuento_euros = int(tr[7] or 0) if len(tr) > 7 else 0
                tesoro_ganado = int(tr[8] or 0) if len(tr) > 8 else 0
                tesoro_gastado = int(tr[9] or 0) if len(tr) > 9 else 0

                # LÓGICA: Distinguir descuentos vs devoluciones
                descuentos_valor = 0
                devoluciones_valor = 0
                if total_db < 0:
                    devoluciones_valor = abs(total_db)
                    descuentos_valor = 0
                else:
                    descuentos_valor = descuento_euros

                # Convertir total a Decimal euros para generador
                try:
                    total_decimal = read_from_db(total_db)
                except Exception:
                    total_decimal = Decimal('0')

                tickets_for_print.append({'id': tid, 'num_ventas': 0, 'total': total_decimal})

                params = (
                    cierre_id,
                    tid,
                    num_ticket,
                    total_db,
                    forma,
                    efectivo_db,
                    tarjeta_db,
                    web_db,
                    descuentos_valor,
                    devoluciones_valor,
                    tesoro_ganado,
                    tesoro_gastado,
                    None,
                )
                try:
                    cur.execute(insert_sql, params)
                except Exception:
                    try:
                        cur.execute(
                            'INSERT INTO cierres_lineas (cierre_id, ticket_id, ticket_num, ticket_total, forma_pago) VALUES (?, ?, ?, ?, ?)',
                            (cierre_id, tid, num_ticket, total_db, forma),
                        )
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error procesando fila de ticket al crear cierre')
                continue

        # commit de las inserciones en cierres_lineas
        try:
            getattr(self.db, 'connection', None).commit()
        except Exception:
            pass

        # Devolver datos del cierre; además, imprimir desde aquí si se solicitó.
        cierre_data = cierre_svc.obtener_cierre_por_id(cierre_id) or {}
        cierre_data['totals'] = totals
        cierre_data['print_options'] = print_options
        # El generador espera 'usuario', pero en la BD es 'cajero'
        if 'cajero' in cierre_data and 'usuario' not in cierre_data:
            cierre_data['usuario'] = cierre_data['cajero']

        printed = False
        if imprimir:
            try:
                # Leer configuración de impresión desde BD
                modo_impresion = 'texto'
                codepage = 'cp858'
                try:
                    row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'modo_impresion'")
                    if row and row[0]:
                        modo_impresion = row[0]
                    row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_codepage'")
                    if row and row[0]:
                        codepage = row[0]
                except Exception:
                    logging.exception('Error leyendo configuración de impresión desde BD')

                imp = ImpresoraService(db=self.db, imprimir_en_consola=True, modo_impresion=modo_impresion, codepage=codepage)
                try:
                    printed = bool(imp.imprimir(TicketType.CIERRE, cierre_data, items=tickets_for_print, printer_name=printer_name, print_options=print_options))
                except Exception:
                    # fallback: try to generate text and print via generic
                    try:
                        texto = imp.generar_cierre_desde_id(cierre_id, print_options=print_options)
                        if texto:
                            imp._imprimir_texto_generico(texto, {'num_ticket': cierre_data.get('cierre_num', '')}, printer_name)
                            printed = True
                    except Exception:
                        printed = False
            except Exception:
                printed = False

            if printed:
                try:
                    # marcar cierre impreso en BD
                    self.db.connect()
                    self.db.execute_query('UPDATE cierres SET printed = 1, printed_at = CURRENT_TIMESTAMP WHERE id = ?', (cierre_id,))
                except Exception:
                    logging.exception('Error marcando cierre impreso desde CierreCajaProcessor')

        return {
            'success': True,
            'cierre_id': int(cierre_id),
            'num_tickets': len(ticket_ids),
            'totals': totals,
            'tickets': tickets_for_print,
            'cierre': cierre_data,
            'printed': printed,
        }
