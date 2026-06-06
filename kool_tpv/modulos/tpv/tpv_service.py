"""kool_tpv.modulos.tpv.tpv_service

Servicio de lógica de negocio para operaciones del TPV.
Gestiona finalización de ventas, validaciones y persistencia.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
import logging
from decimal import Decimal

from kool_tpv.base_datos.ticket_service import save_ticket

logger = logging.getLogger(__name__)


class TpvService:
    """Servicio para operaciones de TPV (lógica de negocio pura).

    Responsabilidades:
    - Validar datos antes de persistir
    - Coordinar save_ticket + impresión
    - Retornar resultados estructurados

    NO conoce UI ni widgets.
    """

    def __init__(
        self, 
        db: Optional[Any] = None,
        fidelizacion_service: Optional[Any] = None,
        impresora_service: Optional[Any] = None
    ):
        """Constructor.

        Args:
            db: Database wrapper
            fidelizacion_service: Servicio de fidelización (opcional)
            impresora_service: Servicio de impresión (opcional)
        """
        self.db = db
        self.fidelizacion_service = fidelizacion_service
        self.impresora_service = impresora_service

    def finalize_sale_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Finalizar venta: validar, persistir, imprimir.

        Args:
            ticket_data: {
                'carrito_items': list,           # items del carrito
                'resumen': dict,                 # resumen financiero
                'efectivo': Decimal,             # cantidad pagada
                'cajero': str,                   # nombre cajero
                'cliente': dict,                 # {'id': int, 'nombre': str} o None
                'forma_pago': str,               # 'Efectivo'|'Tarjeta'|'Web'|'Multi'
                'importe_efectivo': Decimal,     # desglose efectivo
                'importe_tarjeta': Decimal,      # desglose tarjeta
                'descuento_data': dict,          # datos descuento o None
                'carrito_service': CarritoService # referencia al carrito
            }

        Returns:
            {
                'success': bool,
                'ticket_id': int,
                'num_ticket': str,
                'error': str  # solo si success=False
            }
        """
        try:
            # Validación 1: items no vacíos
            items = ticket_data.get('carrito_items', [])
            if not items:
                return {
                    'success': False,
                    'error': 'Carrito vacío - no hay artículos para vender'
                }

            # Validación 2: total > 0 (permitir negativos para devoluciones)
            resumen = ticket_data.get('resumen', {})
            total = resumen.get('total', 0)
            # No validar total > 0 porque devoluciones pueden tener total negativo

            # Extraer datos del cliente
            cliente_data = ticket_data.get('cliente')
            cliente_nombre = None
            cliente_id = None
            if cliente_data:
                cliente_nombre = cliente_data.get('nombre')
                cliente_id = cliente_data.get('id')

            # Normalizar efectivo a Decimal
            efectivo = ticket_data.get('efectivo')
            try:
                if efectivo is not None:
                    efectivo = Decimal(str(efectivo))
                else:
                    # Si es None, save_ticket inferirá del total
                    efectivo = None
            except Exception:
                efectivo = None

            # Normalizar importes
            try:
                importe_efectivo = Decimal(str(ticket_data.get('importe_efectivo', 0)))
            except Exception:
                importe_efectivo = Decimal('0')

            try:
                importe_tarjeta = Decimal(str(ticket_data.get('importe_tarjeta', 0)))
            except Exception:
                importe_tarjeta = Decimal('0')

            # Llamar a save_ticket (hace TODA la persistencia)
            logger.info('TpvService: iniciando save_ticket')

            try:
                result = save_ticket(
                    db=self.db,
                    carrito_items=items,
                    resumen=resumen,
                    efectivo=efectivo,
                    cajero=ticket_data.get('cajero'),
                    cliente=cliente_nombre,
                    cliente_id=cliente_id,
                    forma_pago=ticket_data.get('forma_pago', 'Efectivo'),
                    importe_efectivo=importe_efectivo,
                    importe_tarjeta=importe_tarjeta,
                    descuento_data=ticket_data.get('descuento_data'),
                    carrito_service=ticket_data.get('carrito_service'),
                    fidelizacion_service=self.fidelizacion_service
                )

                # Desempaquetar resultado
                ticket_id, num_ticket = result

            except Exception as e:
                logger.exception('Error en save_ticket')
                return {
                    'success': False,
                    'error': f'Error guardando ticket: {str(e)}'
                }

            # Imprimir ticket (no bloquea si falla)
            try:
                self._print_ticket(ticket_id)
            except Exception:
                logger.exception('Error imprimiendo ticket (no crítico)')

            # Retornar éxito
            logger.info(f'TpvService: venta finalizada ticket_id={ticket_id} num={num_ticket}')

            return {
                'success': True,
                'ticket_id': ticket_id,
                'num_ticket': num_ticket
            }

        except Exception as e:
            logger.exception('Error inesperado en finalize_sale_ticket')
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }

    def _print_ticket(self, ticket_id: int) -> None:
        """Imprimir ticket físicamente usando ImpresoraService.

        Args:
            ticket_id: ID del ticket a imprimir
        """
        try:
            # Leer configuración de impresión desde BD
            modo_impresion = 'texto'
            printer_name = None
            try:
                if self.db and getattr(self.db, 'fetch_one', None):
                    row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'modo_impresion'")
                    if row and row[0]:
                        modo_impresion = row[0]
                    row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_name'")
                    if row and row[0]:
                        printer_name = row[0]
            except Exception:
                logger.exception('Error leyendo configuración de impresión desde BD')

            # Si no hay modo escpos activado, solo simular
            if modo_impresion != 'escpos':
                logger.info('Modo impresión = texto (simulación). Para imprimir físicamente, activa ESC/POS en Config.')

            # Crear ImpresoraService con el modo correcto
            try:
                from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                imp = ImpresoraService(
                    db=self.db,
                    imprimir_en_consola=True,
                    modo_impresion=modo_impresion
                )
                # Generar e imprimir ticket
                texto = imp.generar_ticket_desde_id(ticket_id)

                if texto:
                    logger.info("=" * 50)
                    if modo_impresion == 'escpos':
                        logger.info(" ENVIANDO A IMPRESORA: %s ", printer_name or 'NO CONFIGURADA')
                    else:
                        logger.info(" SIMULACIÓN TICKET (modo texto) ")
                    logger.info("=" * 50)
                    logger.info("\n%s", texto)
                    logger.info("=" * 50)

                    # Si es modo escpos, enviar a impresora física
                    if modo_impresion == 'escpos' and printer_name:
                        try:
                            imp._imprimir_texto_generico(texto, {'num_ticket': ticket_id}, printer_name)
                            logger.info('Ticket enviado a impresora física')
                        except Exception:
                            logger.exception('Error enviando a impresora física')
                else:
                    logger.warning(f'No se pudo generar ticket para ticket_id={ticket_id}')
            except Exception:
                logger.exception(f'Error generando/imprimiendo ticket_id={ticket_id}')

        except Exception:
            logger.exception('Error en _print_ticket')


__all__ = ["TpvService"]
