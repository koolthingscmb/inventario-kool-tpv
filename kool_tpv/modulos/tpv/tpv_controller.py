"""tpv_controller.py - Controlador orquestador del TPV

Coordina servicios, acciones y payment controllers.
Delega lógica de negocio a TpvService y mantiene la vista limpia.
"""

from __future__ import annotations
import logging
from typing import Optional, Any
from decimal import Decimal

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
            from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService
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
                'descuento_data': carrito_service.get_descuento(),
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

            # Delegar a TpvService
            logger.info(f'Finalizando venta forma_pago={forma_pago}')

            result = self.tpv_service.finalize_sale_ticket(ticket_data)

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
