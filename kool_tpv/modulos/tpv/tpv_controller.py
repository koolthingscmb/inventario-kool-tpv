"""tpv_controller.py - Controlador orquestador del TPV

Coordina servicios, acciones y payment controllers.
Delega lógica de negocio a TpvService y mantiene la vista limpia.
"""

from __future__ import annotations
import logging
from typing import Optional, Any
from decimal import Decimal
from datetime import datetime

from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)


class TpvController:
    """Controlador central del TPV.

    Responsabilidades:
    - Setup de servicios (fidelización, impresión, tpv_service)
    - Setup de acciones (cliente, cajero, stock, etc.)
    - Setup de payment controllers (factory)
    - Rebind de botones (mapper)
    - Workflow finalize_sale (preparar datos → delegar servicio → UI)
    """

    def __init__(self, view: Any, db: Optional[Any] = None):
        """Constructor.

        Args:
            view: Instancia de TpvView
            db: Database wrapper
        """
        self.view = view
        self.db = db

        # Referencias a componentes (se crearán en setups)
        self.fidelizacion_service = None
        self.impresora_service = None
        self.tpv_service = None

        # Acciones
        self._cliente_action = None
        self._cajero_action = None
        self.descuento_action = None
        self._devolucion_action = None
        self._stock_ui = None
        self._cierre_ui = None
        self._tickets_ui = None

        # Payment controllers (dict)
        self.payment_controllers = {}

        # Ejecutar setups
        self.setup_services()
        self.setup_actions()
        self.setup_payment_controllers()
        self.rebind_buttons()

        logger.info('TpvController inicializado')

    def setup_services(self):
        """Instanciar servicios de negocio."""
        # FidelizacionService
        try:
            from kool_tpv.modulos.fidelizacion.fidelizacion_service import FidelizacionService
            self.fidelizacion_service = FidelizacionService(self.db)
            logger.debug('FidelizacionService creado')
        except Exception:
            logger.exception('Error creando FidelizacionService')
            self.fidelizacion_service = None

        # ImpresoraService
        try:
            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
            self.impresora_service = ImpresoraService(db=self.db)
            logger.debug('ImpresoraService creado')
        except Exception:
            logger.exception('Error creando ImpresoraService')
            self.impresora_service = None

        # TpvService
        try:
            from kool_tpv.modulos.tpv.tpv_service import TpvService
            self.tpv_service = TpvService(
                db=self.db,
                fidelizacion_service=self.fidelizacion_service,
                impresora_service=self.impresora_service
            )
            logger.debug('TpvService creado')
        except Exception:
            logger.exception('Error creando TpvService')
            self.tpv_service = None

    def setup_actions(self):
        """Instanciar acciones (cliente, cajero, stock, etc.)."""
        carrito_service = getattr(self.view, 'carrito_service', None)

        # ClienteAction
        try:
            from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
            self._cliente_action = ClienteAction(self.view, self.db, carrito_service)
            logger.debug('ClienteAction creado')
        except Exception:
            logger.exception('Error creando ClienteAction')
            self._cliente_action = None

        # CajeroAction
        try:
            from kool_tpv.modulos.tpv.actions.cajero import CajeroAction
            self._cajero_action = CajeroAction(self.view, self.db)
            logger.debug('CajeroAction creado')
        except Exception:
            logger.exception('Error creando CajeroAction')
            self._cajero_action = None

        # DescuentoAction
        try:
            from kool_tpv.modulos.tpv.actions.descuento import DescuentoAction
            self.descuento_action = DescuentoAction(self.view, carrito_service)
            logger.debug('DescuentoAction creado')
        except Exception:
            logger.exception('Error creando DescuentoAction')
            self.descuento_action = None

        # DevolucionAction
        try:
            from kool_tpv.modulos.tpv.actions.devolucion import DevolucionAction
            self._devolucion_action = DevolucionAction(self.view, self.db, carrito_service)
            logger.debug('DevolucionAction creado')
        except Exception:
            logger.exception('Error creando DevolucionAction')
            self._devolucion_action = None

        # StockSubView (replace StockUI with subview push)
        try:
            from kool_tpv.modulos.tpv.subviews.stock_subview import StockSubView

            self._stock_ui = StockSubView(
                parent=self.view.center_area,
                db=self.db,
                carrito_service=carrito_service,
                view=self.view
            )
            logger.debug('StockSubView creado')
        except Exception:
            logger.exception('Error creando StockSubView')
            self._stock_ui = None

        # CierreUI
        try:
            from kool_tpv.modulos.tpv.actions.cierres.cierre_ui import CierreUI
            self._cierre_ui = CierreUI(self.view, self.db)
            logger.debug('CierreUI creado')
        except Exception:
            logger.exception('Error creando CierreUI')
            self._cierre_ui = None

        # TicketsUI
        try:
            from kool_tpv.modulos.tpv.actions.tickets.tickets_ui import TicketsUI
            self._tickets_ui = TicketsUI(self.view, self.db)
            logger.debug('TicketsUI creado')
        except Exception:
            logger.exception('Error creando TicketsUI')
            self._tickets_ui = None

        # Exponer acciones en view para compatibilidad
        self.view._cliente_action = self._cliente_action
        self.view._cajero_action = self._cajero_action
        self.view.descuento_action = self.descuento_action
        self.view._devolucion_action = self._devolucion_action
        self.view._stock_ui = self._stock_ui
        self.view._cierre_ui = self._cierre_ui
        self.view._tickets_ui = self._tickets_ui

    def setup_payment_controllers(self):
        """Instanciar payment controllers usando factory."""
        try:
            from kool_tpv.modulos.tpv.payment_controller_factory import create_controllers

            carrito_service = getattr(self.view, 'carrito_service', None)
            ticket_carrito = getattr(self.view, 'ticket_carrito', None)

            if not ticket_carrito:
                logger.warning('ticket_carrito no disponible, skip payment controllers')
                return

            # Callback unificado
            self.payment_controllers = create_controllers(
                parent=ticket_carrito.payment_area,
                carrito_service=carrito_service,
                on_finalize=self.finalize_sale
            )

            # Exponer en view para compatibilidad con button_action_mapper
            self.view._cash_controller = self.payment_controllers.get('cash')
            self.view._multi_controller = self.payment_controllers.get('multi')
            self.view._tarjeta_controller = self.payment_controllers.get('tarjeta')
            self.view._web_controller = self.payment_controllers.get('web')

            logger.info(f'Payment controllers creados: {list(self.payment_controllers.keys())}')

        except Exception:
            logger.exception('Error creando payment controllers')

    def rebind_buttons(self):
        """Rebind botones grid usando mapper."""
        try:
            from kool_tpv.modulos.tpv.button_action_mapper import rebind_buttons
            rebind_buttons(self.view)
            logger.info('Botones rebound con mapper')
        except Exception:
            logger.exception('Error rebinding botones')

    def _build_ticket_payload(self, db, carrito_items, resumen, efectivo, **kwargs):
        """Construir payload listo para los TicketProcessors.

        Convierte importes a céntimos y prepara la estructura esperada.
        """
        created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
        num_ticket = kwargs.get('num_ticket')
        # safe Decimal extraction
        def _dec(v, default='0'):
            try:
                return Decimal(str(v))
            except Exception:
                return Decimal(default)

        # Normalize cliente: accept dict from CarritoService but store only a string name
        _orig_cliente = kwargs.get('cliente')
        _cliente_id = kwargs.get('cliente_id')
        _cliente_name = None
        try:
            if isinstance(_orig_cliente, dict):
                _cliente_name = _orig_cliente.get('nombre') or None
                # populate cliente_id from cliente dict if missing
                if _cliente_id is None:
                    _cliente_id = _orig_cliente.get('id')
            else:
                # if a plain string was passed, use it as name
                if _orig_cliente is not None:
                    _cliente_name = str(_orig_cliente)
        except Exception:
            _cliente_name = None

        payload = {
            'resumen': resumen,
            'created_at': created_at,
            'num_ticket': num_ticket,
            'cajero': kwargs.get('cajero'),
            'cliente': _cliente_name,
            'cliente_id': _cliente_id,
            'subtotal_cents': prepare_for_db(_dec(resumen.get('subtotal', '0'))),
            'total_cents': prepare_for_db(_dec(resumen.get('total', '0'))),
            'pagado_cents': prepare_for_db(_dec(efectivo if efectivo is not None else 0)),
            'cambio_cents': prepare_for_db(_dec((efectivo if efectivo is not None else 0)) - _dec(resumen.get('total', '0'))),
            'importe_efectivo_cents': prepare_for_db(_dec(kwargs.get('importe_efectivo', 0))),
            'importe_tarjeta_cents': prepare_for_db(_dec(kwargs.get('importe_tarjeta', 0))),
            'descuento_euros_cents': prepare_for_db(_dec(kwargs.get('descuento_data', {}).get('euros', 0))),
            'descuento_tipo': kwargs.get('descuento_data', {}).get('tipo'),
            'descuento_valor': kwargs.get('descuento_data', {}).get('valor'),
            'forma_pago': kwargs.get('forma_pago', 'Efectivo'),
            'ticket_text_snapshot': None,
            'carrito_items': carrito_items,
            'pagos': [],
        }

        # pagos desglosados
        pagos = []
        if kwargs.get('importe_efectivo'):
            pagos.append(('efectivo', prepare_for_db(_dec(kwargs.get('importe_efectivo')))))
        if kwargs.get('importe_tarjeta'):
            pagos.append(('tarjeta', prepare_for_db(_dec(kwargs.get('importe_tarjeta')))))
        payload['pagos'] = pagos

        # puntos ya en céntimos (int) — sin conversión adicional
        if 'puntos_otorgar_cents' in kwargs:
            payload['puntos_otorgar_cents'] = int(kwargs.get('puntos_otorgar_cents', 0))
        if 'puntos_restar_cents' in kwargs:
            payload['puntos_restar_cents'] = int(kwargs.get('puntos_restar_cents', 0))
        if 'puntos_gastados_cents' in kwargs:
            payload['puntos_gastados_cents'] = int(kwargs.get('puntos_gastados_cents', 0))

        return payload

    def finalize_sale(
        self,
        efectivo=None,
        forma_pago='Efectivo',
        importe_efectivo=None,
        importe_tarjeta=None
    ):
        """Finalizar venta: preparar datos y delegar a TpvService.

        Args:
            efectivo: Cantidad pagada (Decimal o float)
            forma_pago: Método de pago
            importe_efectivo: Desglose efectivo
            importe_tarjeta: Desglose tarjeta
        """
        try:
            from kool_tpv.utils.custom_dialog import show_error, show_success

            carrito_service = getattr(self.view, 'carrito_service', None)
            if not carrito_service:
                logger.error('carrito_service no disponible')
                return

            # Validar carrito no vacío
            if carrito_service.is_empty():
                show_error(
                    self.view.container,
                    'Carrito vacío',
                    'No se puede realizar una venta sin artículos.'
                )
                return

            # Preparar ticket_data
            ticket_data = {
                'carrito_items': carrito_service.get_items(),
                'resumen': carrito_service.get_resumen_financiero(),
                'efectivo': efectivo,
                # cajero will be obtained from CarritoService (must be present)
                'cajero': None,
                'cliente': carrito_service.get_cliente(),
                'forma_pago': forma_pago,
                'importe_efectivo': importe_efectivo or 0.0,
                'importe_tarjeta': importe_tarjeta or 0.0,
                'descuento_data': carrito_service.get_descuento() or {},
                'carrito_service': carrito_service
            }

            # Verificar que exista un cajero activo en el CarritoService
            cajero_obj = None
            try:
                cajero_obj = carrito_service.get_cajero() if carrito_service else None
            except Exception:
                cajero_obj = None

            if not cajero_obj:
                show_error(
                    self.view.container,
                    'Sin cajero',
                    'Debe autenticar un cajero antes de finalizar la venta.'
                )
                return

            # Usar nombre del cajero para el ticket (save_ticket espera un nombre)
            try:
                ticket_data['cajero'] = cajero_obj.get('nombre') if isinstance(cajero_obj, dict) else str(cajero_obj)
            except Exception:
                ticket_data['cajero'] = None

            # Delegar a TicketProcessors (reemplaza el antiguo save_ticket/tpv_service)
            logger.info(f'Finalizando venta forma_pago={forma_pago}')

            carrito_items = ticket_data.get('carrito_items')
            resumen = ticket_data.get('resumen')

            # Determinar tipo de operación usando CarritoService (Strategy)
            try:
                tipo_ticket = carrito_service.get_ticket_type()
            except Exception:
                logger.exception('Error determinando tipo_ticket desde CarritoService, fallback a venta')
                tipo_ticket = 'venta'

            # Calcular puntos si procede (resultado ya en céntimos int)
            puntos_otorgar_cents = 0
            puntos_gastados_cents = 0
            try:
                if tipo_ticket == 'venta_fidelizacion' and self.fidelizacion_service:
                    _puntos_gastados_euros = Decimal(str(resumen.get('puntos_canjeados', 0)))
                    puntos_otorgar_cents = self.fidelizacion_service.calcular_puntos_ganados(carrito_items, _puntos_gastados_euros)
                    puntos_gastados_cents = int(prepare_for_db(_puntos_gastados_euros))
            except Exception:
                logger.exception('Error calculando puntos de fidelización')

            # Construir payload en céntimos
            # Obtener cliente_id de forma segura (CarritoService.get_cliente() devuelve dict)
            _cs = ticket_data.get('carrito_service')
            try:
                _cliente = _cs.get_cliente() if _cs else None
            except Exception:
                _cliente = None
            cliente_id = _cliente.get('id') if isinstance(_cliente, dict) and _cliente else None

            # Obtener num_ticket antes de llamar al processor
            num_ticket_val = None
            try:
                num_ticket_val = carrito_service.get_num_ticket()
            except Exception:
                num_ticket_val = None
            logger.info(f"num_ticket={num_ticket_val}")

            payload = self._build_ticket_payload(
                self.db,
                carrito_items,
                resumen,
                efectivo,
                cajero=ticket_data.get('cajero'),
                cliente=ticket_data.get('cliente'),
                cliente_id=cliente_id,
                forma_pago=forma_pago,
                importe_efectivo=importe_efectivo,
                importe_tarjeta=importe_tarjeta,
                descuento_data=ticket_data.get('descuento_data'),
                puntos_otorgar_cents=puntos_otorgar_cents,
                puntos_gastados_cents=puntos_gastados_cents,
                num_ticket=num_ticket_val,
            )

            # Seleccionar processor
            try:
                # import from package exports
                from kool_tpv.modulos.ticket import VentaProcessor, VentaFidelizacionProcessor, DevolucionProcessor

                if tipo_ticket == 'venta':
                    processor = VentaProcessor(self.db)
                elif tipo_ticket == 'venta_fidelizacion':
                    processor = VentaFidelizacionProcessor(self.db)
                elif tipo_ticket == 'devolucion':
                    processor = DevolucionProcessor(self.db)
                else:
                    processor = VentaProcessor(self.db)
            except Exception:
                logger.exception('Error creando processor para tipo %s', tipo_ticket)
                raise

            # Ejecutar el proceso
            try:
                # Temporal debug: registrar cliente_id/cliente y puntos antes de procesar
                try:
                    logger.info("DEBUG payload before processor.process: cliente_id=%r cliente=%r puntos_otorgar_cents=%r puntos_gastados_cents=%r puntos_restar_cents=%r",
                                payload.get('cliente_id'), payload.get('cliente'), payload.get('puntos_otorgar_cents'), payload.get('puntos_gastados_cents'), payload.get('puntos_restar_cents'))
                except Exception:
                    logger.debug('DEBUG payload logging failed')

                ticket_id = processor.process(**payload)
                result = {'success': True, 'ticket_id': ticket_id, 'num_ticket': payload.get('num_ticket')}
            except Exception as e:
                logger.exception('Error procesando ticket con processor')
                result = {'success': False, 'error': str(e)}

            # Procesar resultado
            if result['success']:
                ticket_id = result['ticket_id']
                num_ticket = result['num_ticket']

                # Limpiar carrito
                carrito_service.clear()

                # Actualizar UI
                ticket_carrito = getattr(self.view, 'ticket_carrito', None)
                if ticket_carrito:
                    ticket_carrito.update_carrito()

                # Finalizar devolución si activa
                if self._devolucion_action:
                    devol_service = getattr(self._devolucion_action, 'devolucion_service', None)
                    if devol_service:
                        try:
                            devol_service.end_devolucion()
                        except Exception:
                            pass

                # Imprimir ticket en terminal/impresora (no bloquea si falla)
                if self.tpv_service:
                    try:
                        self.tpv_service._print_ticket(ticket_id)
                    except Exception:
                        logger.exception('Error imprimiendo ticket (no crítico)')

                # Mostrar éxito
                show_success(
                    self.view.container,
                    'Venta guardada',
                    f'Ticket #{num_ticket} guardado correctamente'
                )

                logger.info(f'Venta finalizada exitosamente ticket_id={ticket_id}')
            else:
                # Mostrar error
                error_msg = result.get('error', 'Error desconocido')
                show_error(
                    self.view.container,
                    'Error guardando ticket',
                    error_msg
                )
                logger.error(f'Error finalizando venta: {error_msg}')

        except Exception:
            logger.exception('Error inesperado en finalize_sale')
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(
                    self.view.container,
                    'Error',
                    'Error interno al finalizar la venta'
                )
            except Exception:
                pass


__all__ = ['TpvController']
