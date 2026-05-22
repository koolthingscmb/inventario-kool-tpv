from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
import logging

from kool_tpv.modulos.ticket.base_processor import TicketProcessor
from kool_tpv.base_datos.cierre_service import CierreService
from kool_tpv.base_datos.money_adapter import read_from_db


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
                    int(num_ticket) if num_ticket is not None else None,
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
                            (cierre_id, int(tid), int(num_ticket) if num_ticket is not None else None, int(total_db) if isinstance(total_db, int) else int(total_db or 0), str(forma)),
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

        # Devolver datos del cierre; la UI/controlador decide si imprime
        cierre_data = cierre_svc.obtener_cierre_por_id(cierre_id) or {}
        cierre_data['totals'] = totals
        return {
            'success': True,
            'cierre_id': int(cierre_id),
            'num_tickets': len(ticket_ids),
            'totals': totals,
            'tickets': tickets_for_print,
            'cierre': cierre_data,
        }
