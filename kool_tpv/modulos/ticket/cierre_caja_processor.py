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
    def process(self, ticket_ids: Optional[List[int]] = None, usuario_id: Optional[int] = None, cajero: Optional[str] = None, cierre_text: Optional[str] = None, imprimir: bool = True, printer_name: Optional[str] = None):
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

        # crear el cierre (inserta en `cierres` y marca tickets)
        cierre_id = cierre_svc.create_cierre_atomic(ticket_ids, usuario_id, cajero, cierre_text=cierre_text)
        if cierre_id is None:
            return {'success': False, 'error': 'create_failed'}

        # Recuperar registros de tickets para poblar cierres_lineas
        placeholders = ','.join(['?'] * len(ticket_ids))
        sql = f"SELECT id, num_ticket, total, forma_pago, importe_efectivo, importe_tarjeta FROM tickets WHERE id IN ({placeholders})"
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
            ventas_cat = cat_svc.get_ventas_por_categoria(ticket_ids, line_tipo='venta') or []
            ventas_cat_simple = []
            for entry in ventas_cat:
                try:
                    nombre = entry[0]
                    tickets_cnt = int(entry[1] or 0)
                    total_euros = entry[3] if len(entry) > 3 else entry[2]
                    ventas_cat_simple.append((nombre, tickets_cnt, total_euros))
                except Exception:
                    continue

            # devoluciones: solo líneas de tipo 'devolucion'
            devol_cat = cat_svc.get_ventas_por_categoria(ticket_ids, line_tipo='devolucion') or []
            devol_cat_simple = []
            for entry in devol_cat:
                try:
                    nombre = entry[0]
                    tickets_cnt = int(entry[1] or 0)
                    total_euros = entry[3] if len(entry) > 3 else entry[2]
                    devol_cat_simple.append((nombre, tickets_cnt, total_euros))
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
            tipos_ventas = tipo_svc.get_ventas_por_tipo(ticket_ids, line_tipo='venta') or []
            tipos_simple = []
            for entry in tipos_ventas:
                try:
                    nombre = entry[0]
                    tickets_cnt = int(entry[1] or 0)
                    # entry may be (nombre, tickets_cnt, uds, total_euros)
                    total_euros = entry[3] if len(entry) > 3 else entry[2]
                    tipos_simple.append((nombre, tickets_cnt, total_euros))
                except Exception:
                    continue
            if tipos_simple:
                totals['ventas_por_tipo'] = tipos_simple
        except Exception:
            pass

        # devoluciones por tipo: sólo líneas 'devolucion'
        try:
            tipo_svc = TipoService(self.db)
            tipos_devol = tipo_svc.get_ventas_por_tipo(ticket_ids, line_tipo='devolucion') or []
            tipos_devol_simple = []
            for entry in tipos_devol:
                try:
                    nombre = entry[0]
                    tickets_cnt = int(entry[1] or 0)
                    total_euros = entry[3] if len(entry) > 3 else entry[2]
                    tipos_devol_simple.append((nombre, tickets_cnt, total_euros))
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
                tid = tr[0]
                num_ticket = tr[1]
                total_db = tr[2] or 0
                forma = tr[3] or ''
                efectivo_db = tr[4] or 0
                tarjeta_db = tr[5] or 0

                # Convertir total a Decimal euros para generador
                try:
                    total_decimal = read_from_db(int(total_db))
                except Exception:
                    total_decimal = Decimal('0')

                # Preparar fila para imprimir
                tickets_for_print.append({'id': tid, 'num_ventas': 0, 'total': total_decimal})

                # Insertar línea de cierre (almacenar totales en céntimos)
                params = (
                    cierre_id,
                    int(tid),
                    num_ticket,
                    int(total_db) if isinstance(total_db, int) else int(total_db or 0),
                    str(forma),
                    int(efectivo_db) if isinstance(efectivo_db, int) else int(efectivo_db or 0),
                    int(tarjeta_db) if isinstance(tarjeta_db, int) else int(tarjeta_db or 0),
                    0,  # web
                    0,  # descuentos
                    0,  # devoluciones
                    0,  # tesoro_ganado
                    0,  # tesoro_gastado
                    None,
                )
                try:
                    cur.execute(insert_sql, params)
                except Exception:
                    # intentar sin campos opcionales si esquema antiguo
                    try:
                        cur.execute(
                            'INSERT INTO cierres_lineas (cierre_id, ticket_id, ticket_num, ticket_total, forma_pago) VALUES (?, ?, ?, ?, ?)',
                            (cierre_id, int(tid), num_ticket, int(total_db) if isinstance(total_db, int) else int(total_db or 0), str(forma)),
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

        printed = False
        if imprimir:
            try:
                imp = ImpresoraService(db=self.db, imprimir_en_consola=True)
                try:
                    printed = bool(imp.imprimir(TicketType.CIERRE, cierre_data, items=tickets_for_print, printer_name=printer_name))
                except Exception:
                    # fallback: try to generate text and print via generic
                    try:
                        texto = imp.generar_cierre_desde_id(cierre_id)
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
