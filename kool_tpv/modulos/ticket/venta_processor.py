from __future__ import annotations
from typing import Any, Dict, List
from decimal import Decimal
import logging
from kool_tpv.base_datos.money_adapter import prepare_for_db

from kool_tpv.modulos.ticket.base_processor import TicketProcessor

logger = logging.getLogger(__name__)


class VentaProcessor(TicketProcessor):
    def process(self, *, carrito_items: List[Dict], resumen: Dict, **kwargs):
        created_at = kwargs.get('created_at')
        cajero = kwargs.get('cajero')
        cliente = kwargs.get('cliente')
        cliente_id = kwargs.get('cliente_id')

        try:
            from kool_tpv.base_datos.configuracion_service import ConfiguracionService
            config_service = ConfiguracionService(self.db)

            with self.db.transaction() as cur:
                # Generate ticket number using the same cursor/transaction
                try:
                    num_ticket = config_service.get_next_ticket_number(cur=cur)
                except Exception:
                    logger.exception('Error generando num_ticket en VentaProcessor')
                    raise

                ticket_id = self.repo.insert_ticket(
                    created_at=created_at,
                    cajero=cajero,
                    cliente=cliente,
                    cliente_id=cliente_id,
                    num_ticket=num_ticket,
                    subtotal_cents=kwargs.get('subtotal_cents', 0),
                    forma_pago=kwargs.get('forma_pago', 'Efectivo'),
                    total_cents=kwargs.get('total_cents', 0),
                    pagado_cents=kwargs.get('pagado_cents', 0),
                    cambio_cents=kwargs.get('cambio_cents', 0),
                    importe_efectivo_cents=kwargs.get('importe_efectivo_cents', 0),
                    importe_tarjeta_cents=kwargs.get('importe_tarjeta_cents', 0),
                    importe_web_cents=kwargs.get('importe_web_cents', None),
                    descuento_euros_cents=kwargs.get('descuento_euros_cents', 0),
                    descuento_tipo=kwargs.get('descuento_tipo'),
                    descuento_valor=kwargs.get('descuento_valor'),
                    tesoro_ganado_str=kwargs.get('puntos_otorgar_cents', 0),
                    tesoro_gastado_str=kwargs.get('puntos_gastados_cents', 0),
                    ticket_text_snapshot=kwargs.get('ticket_text_snapshot'),
                    iva_desglose_json=kwargs.get('iva_desglose_json', '{}'),
                    cur=cur,
                )

                for it in carrito_items or []:
                    pvp_euros = Decimal(str(it.get('pvp', 0)))
                    precio_cents = prepare_for_db(pvp_euros)

                    logger.info(f"DEBUG SKU: it.get('sku')={it.get('sku')}, it keys={list(it.keys())}")

                    line_id = self.repo.insert_ticket_line(
                        ticket_id,
                        it.get('sku'),                      # SKU
                        it.get('nombre'),
                        int(it.get('cantidad', 0)),
                        precio_cents,                       # en céntimos (int)
                        int(it.get('tipo_iva', 0)),         # tipo_iva
                        it.get('line_tipo', 'venta'),
                        it.get('id'),                       # producto_id
                        cur=cur,
                    )

                    prod_id = it.get('id')
                    if prod_id is not None:
                        if it.get('line_tipo') == 'devolucion':
                            stock_change = int(it.get('cantidad', 0))
                            ventas_change = -int(it.get('cantidad', 0))
                        else:
                            stock_change = -int(it.get('cantidad', 0))
                            ventas_change = int(it.get('cantidad', 0))
                        try:
                            # Atomic update + movement recording to ensure consistency
                            self.repo.update_stock_and_record_movement(prod_id, stock_change, ventas_change, f"ticket:{ticket_id}", ticket_line_id=line_id, cur=cur)
                        except Exception:
                            logger.exception('Error updating stock and recording movement for producto_id=%s in ticket=%s', prod_id, ticket_id)
                            raise

                pagos = kwargs.get('pagos', [])
                for metodo, importe_cents in pagos:
                    self.repo.insert_payment(ticket_id, metodo, importe_cents, kwargs.get('created_at'), cur=cur)

                self.repo.insert_audit_log(kwargs.get('created_at'), ticket_id, kwargs.get('cajero'), 'save_ticket', f'num_ticket={num_ticket}', cur=cur)

            # Transaction committed successfully

            # Procesar descuentos (crear línea negativa)
            descuentos = kwargs.get('descuentos', [])
            if descuentos:
                try:
                    from kool_tpv.modulos.ticket.descuento_processor import DescuentoProcessor
                    desc_proc = DescuentoProcessor(self.db)
                    desc_proc.process(ticket_id=ticket_id, descuentos=descuentos)
                except Exception:
                    logger.exception('Error procesando descuentos')
                    raise

            return ticket_id, num_ticket

        except Exception:
            logger.exception('Error procesando venta en transacción')
            raise
