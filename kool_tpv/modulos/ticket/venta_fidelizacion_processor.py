from __future__ import annotations
from typing import Any
import logging

from kool_tpv.modulos.ticket.venta_processor import VentaProcessor

logger = logging.getLogger(__name__)


class VentaFidelizacionProcessor(VentaProcessor):
    def process(self, **kwargs):
        logger.info("!!! DEBUG: ENTRANDO EN VENTAFIDELIZACIONPROCESSOR.PROCESS !!!")
        proc_res = super().process(**kwargs)
        if isinstance(proc_res, (tuple, list)):
            ticket_id = proc_res[0]
            num_ticket = proc_res[1] if len(proc_res) > 1 else None
        else:
            ticket_id = proc_res
            num_ticket = None
        cliente_id = kwargs.get('cliente_id')
        puntos_otorgar_cents = kwargs.get('puntos_otorgar_cents')
        puntos_gastados_cents = kwargs.get('puntos_gastados_cents')
        puntos_restar_cents = kwargs.get('puntos_restar_cents', 0)
        if cliente_id:
            if puntos_otorgar_cents > 0:
                self.repo.insert_points_movement_raw(cliente_id, +puntos_otorgar_cents, 'compra', ticket_id, None)
            if puntos_gastados_cents > 0:
                self.repo.insert_points_movement_raw(cliente_id, -puntos_gastados_cents, 'gasto', ticket_id, None)
            if puntos_restar_cents > 0:
                self.repo.insert_points_movement_raw(cliente_id, -puntos_restar_cents, 'ajuste', ticket_id, None)
            
            res_nivel = self.fidel_repo.actualizar_loyalty_y_recalcular_nivel(
                cliente_id=cliente_id,
                puntos_otorgar_cents=puntos_otorgar_cents or 0,
                puntos_restar_cents=puntos_restar_cents or 0,
                puntos_gastados_cents=puntos_gastados_cents or 0,
                total_ticket_cents=kwargs.get('total_cents', 0),
                unidades_vendidas=kwargs.get('total_unidades', 0),
                fecha=(kwargs.get('created_at') or '').split(' ')[0]
            )

            logger.info(f"DEBUG res_nivel: {res_nivel}")
            logger.info(f"DEBUG impresora_service: {self.impresora_service is not None}")

            # Si subió de nivel y tenemos impresora, lanzar ticket
            if res_nivel.get('subida_nivel') and self.impresora_service:
                logger.info(f"DEBUG detectada subida de nivel para cliente {cliente_id}")
                try:
                    from datetime import datetime
                    from kool_tpv.modulos.fidelizacion.niveles_repository import NivelesRepository
                    niv_repo = NivelesRepository(self.db)
                    
                    nivel_ant = niv_repo.get_nivel_por_id(res_nivel['nivel_anterior_id'])
                    nivel_nue = niv_repo.get_nivel_por_id(res_nivel['nivel_nuevo_id'])
                    cliente_info = self.fidel_repo.get_cliente_info(cliente_id)
                    
                    logger.info(f"DEBUG nivel_ant: {nivel_ant}")
                    logger.info(f"DEBUG nivel_nue: {nivel_nue}")
                    logger.info(f"DEBUG cliente_info: {cliente_info}")
                    
                    from kool_tpv.base_datos.money_adapter import read_from_db
                    nivel_data = {
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'hora': datetime.now().strftime('%H:%M'),
                        'cliente': cliente_info['nombre_completo'] if cliente_info else f"Cliente #{cliente_id}",
                        'nivel_anterior': nivel_ant['nombre_nivel'] if nivel_ant else 'Base',
                        'nivel_nuevo': nivel_nue['nombre_nivel'] if nivel_nue else 'Nuevo',
                        'recompensa': nivel_nue.get('detalle_recompensa', '') if nivel_nue else '',
                        'grafismo': nivel_nue['grafismo_nivel'] if nivel_nue else '',
                        'total_acumulado': float(read_from_db(res_nivel['tesoro_historico']))
                    }
                    self.impresora_service.imprimir_ticket_nivel(nivel_data)
                    logger.info(f"Ticket de subida de nivel enviado para cliente {cliente_id}")
                except Exception:
                    logger.exception("Error al intentar imprimir ticket de subida de nivel")

        return ticket_id, num_ticket
