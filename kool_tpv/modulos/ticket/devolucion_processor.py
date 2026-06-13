from __future__ import annotations
from typing import Dict, List, Optional
import logging

from kool_tpv.modulos.ticket.venta_processor import VentaProcessor
from kool_tpv.modulos.ticket.devolucion_repository import DevolucionRepository
from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService

logger = logging.getLogger(__name__)


class DevolucionProcessor(VentaProcessor):
    """Processor transaccional para devoluciones.

    Reemplaza la llamada a super().process() por una operación transaccional
    que inserta ticket, líneas, pagos (si aplica) y registra la entrada en
    `devoluciones` y los movimientos de puntos dentro de la misma transacción.
    """

    def process(self, *, carrito_items: List[Dict], resumen: Dict, **kwargs) -> int:
        created_at = kwargs.get('created_at')
        cajero = kwargs.get('cajero')
        cliente = kwargs.get('cliente')
        cliente_id = kwargs.get('cliente_id')

        devol_repo = DevolucionRepository(self.db)

        try:
            # Ejecutar todo en una única transacción
            with self.db.transaction() as cur:
                # Reutilizamos la lógica de generación de num_ticket desde ConfiguracionService
                try:
                    from kool_tpv.base_datos.configuracion_service import ConfiguracionService

                    config_service = ConfiguracionService(self.db)
                    num_ticket = config_service.get_next_ticket_number(cur=cur)
                except Exception:
                    logger.exception('Error generando num_ticket en DevolucionProcessor')
                    raise

                # Insert ticket: para devoluciones mantenemos forma_pago = None
                ticket_id = self.repo.insert_ticket(
                    created_at=created_at,
                    cajero=cajero,
                    cliente=cliente,
                    cliente_id=cliente_id,
                    num_ticket=num_ticket,
                    subtotal_cents=kwargs.get('subtotal_cents', 0),
                    forma_pago=None,
                    total_cents=kwargs.get('total_cents', 0),
                    pagado_cents=kwargs.get('pagado_cents', None),
                    cambio_cents=kwargs.get('cambio_cents', None),
                    importe_efectivo_cents=kwargs.get('importe_efectivo_cents', None),
                    importe_tarjeta_cents=kwargs.get('importe_tarjeta_cents', None),
                    descuento_euros_cents=kwargs.get('descuento_euros_cents', 0),
                    descuento_tipo=kwargs.get('descuento_tipo'),
                    descuento_valor=kwargs.get('descuento_valor'),
                    tesoro_ganado_str=kwargs.get('puntos_otorgar_cents', 0),
                    tesoro_gastado_str=kwargs.get('puntos_gastados_cents', 0),
                    ticket_text_snapshot=kwargs.get('ticket_text_snapshot'),
                    iva_desglose_json=kwargs.get('iva_desglose_json', '{}'),
                    cur=cur,
                )

                # Insertar líneas y actualizar stock/ventas
                from kool_tpv.base_datos.money_adapter import prepare_for_db
                for it in carrito_items or []:
                    pvp_euros = it.get('pvp', 0)
                    try:
                        precio_cents = prepare_for_db(pvp_euros if pvp_euros is not None else 0)
                    except Exception:
                        precio_cents = prepare_for_db(0)

                    line_id = self.repo.insert_ticket_line(
                        ticket_id,
                        it.get('sku'),
                        it.get('nombre'),
                        int(it.get('cantidad', 0)),
                        precio_cents,
                        int(it.get('tipo_iva', 0)),
                        it.get('line_tipo', 'devolucion'),
                        it.get('id'),
                        cur=cur,
                    )

                    prod_id = it.get('id')
                    if prod_id is not None:
                        # En devolución, incrementamos stock y decrementamos ventas
                        stock_change = int(it.get('cantidad', 0))
                        ventas_change = -int(it.get('cantidad', 0))
                        try:
                            self.repo.update_stock_and_record_movement(prod_id, stock_change, ventas_change, f"ticket:{ticket_id}", ticket_line_id=line_id, cur=cur)
                        except Exception:
                            logger.exception('Error updating stock and recording movement for producto_id=%s in ticket=%s', prod_id, ticket_id)
                            raise

                # Pagos: para devoluciones normalmente no persistimos desglose; respetamos None
                pagos = kwargs.get('pagos', []) or []
                for metodo, importe_cents in pagos:
                    self.repo.insert_payment(ticket_id, metodo, importe_cents, kwargs.get('created_at'), cur=cur)

                # Registrar auditoría
                self.repo.insert_audit_log(kwargs.get('created_at'), ticket_id, kwargs.get('cajero'), 'save_ticket', f'num_ticket={num_ticket}', cur=cur)

                # Registrar en devoluciones y actualizar cliente/puntos dentro de la misma transacción
                devuelto_cents = abs(kwargs.get('total_cents', 0) or 0)
                try:
                    devol_repo.insert_devolucion(ticket_id, cliente_id, cajero, devuelto_cents, created_at, cur=cur)
                    if cliente_id is not None:
                        devol_repo.update_cliente_total_devoluciones(cliente_id, devuelto_cents, cur=cur)
                except Exception:
                    logger.exception('DevolucionProcessor: error en registro de devolucion (ticket_id=%s)', ticket_id)
                    raise

                # Revertir puntos tesoro si aplica
                puntos_revertir = abs(int(kwargs.get('puntos_restar_cents', 0) or 0))
                if cliente_id is not None and puntos_revertir > 0:
                    try:
                        devol_repo.insert_points_movement(cliente_id, -puntos_revertir, 'devolucion', ticket_id, None, kwargs.get('created_at'), cur=cur)
                        cur.execute(
                            """UPDATE clientes
                               SET tesoro_total    = MAX(0, COALESCE(tesoro_total, 0) - ?),
                                   tesoro_historico = MAX(0, COALESCE(tesoro_historico, 0) - ?)
                               WHERE id = ?""",
                            (puntos_revertir, puntos_revertir, cliente_id),
                        )
                        logger.info('DevolucionProcessor: revertidos %d puntos para cliente_id=%s (ticket_id=%s)', puntos_revertir, cliente_id, ticket_id)
                    except Exception:
                        logger.exception('DevolucionProcessor: error revirtiendo puntos (ticket_id=%s)', ticket_id)

            # Transaction committed successfully

            # Generar vale de devolución (fuera de la transacción BD para no bloquear)
            try:
                vale_service = ValeDevolucionService()
                cliente_nombre = None
                if cliente:
                    if isinstance(cliente, dict):
                        cliente_nombre = cliente.get('nombre')
                    else:
                        cliente_nombre = str(cliente)
                vale_service.guardar(
                    importe_cents=devuelto_cents,
                    num_ticket_devolucion=num_ticket,
                    cliente_id=cliente_id,
                    cliente_nombre=cliente_nombre,
                )
                logger.info('Vale generado para devolucion %s: %s cents', num_ticket, devuelto_cents)
            except Exception:
                logger.exception('Error generando vale para devolucion %s', num_ticket)

            return ticket_id, num_ticket
        except Exception:
            logger.exception('Error procesando devolucion en transacción')
            raise
