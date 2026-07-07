"""tpv_controller.py - Controlador orquestador del TPV

Coordina servicios, acciones y payment controllers.
Delega lógica de negocio a TpvService y mantiene la vista limpia.
"""

from __future__ import annotations
import json
import logging
from typing import Optional, Any
from decimal import Decimal
from datetime import datetime

from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.custom_dialog import show_input_dialog

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

        # Barcode service
        self._barcode_service = None

        # Ejecutar setups
        self.setup_services()
        self.setup_actions()
        self.setup_payment_controllers()
        self.rebind_buttons()
        self.setup_barcode()
        self._setup_keyboard_shortcuts()

        # Comprobar productos pendientes (Incompletos)
        self.view.after(1000, self._comprobar_productos_pendientes)

        logger.info('TpvController inicializado')

    def _comprobar_productos_pendientes(self):
        """Busca productos en la categoría 'Incompleto' (ID 3) y avisa al usuario."""
        try:
            row = self.db.fetch_one("SELECT count(*), id FROM productos WHERE categoria = 3")
            count = row[0] if row else 0
            
            if count > 0:
                first_id = row[1]
                msg = f"TIENES {count} PRODUCTOS PENDIENTES DE COMPLETAR" if count > 1 else "TIENES 1 PRODUCTO PENDIENTE DE COMPLETAR"
                
                def ir_a_completar(confirmed):
                    if confirmed:
                        self._navegar_a_producto_pendiente(first_id if count == 1 else None)
                
                from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
                ToastWidget.show(
                    self.view, 
                    msg, 
                    tipo='info', 
                    duracion_ms=0, # Persistente hasta clic en OK
                    al_cerrar=ir_a_completar
                )
        except Exception:
            logger.exception("Error comprobando productos pendientes")

    def _navegar_a_producto_pendiente(self, producto_id=None):
        """Navega al módulo de Almacén para completar un producto."""
        # 1. Verificar si el TPV puede cerrarse (carrito vacío)
        if not self.view.carrito_service.is_empty():
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self.view, "VACÍA EL CARRITO PARA IR A COMPLETAR PRODUCTOS", tipo='warning')
            return

        try:
            root = self.view.winfo_toplevel()
            if hasattr(root, 'open_almacen'):
                # Salir del TPV (simular click en Power pero forzando salida)
                if hasattr(root, 'close_app'):
                    root.close_app() # En TPV, close_app vuelve al menú
                
                # Abrir Almacén
                root.open_almacen()
                
                # Si tenemos un ID específico, abrir su ficha
                if producto_id and hasattr(root, 'almacen_view'):
                    root.almacen_view.show_crear(producto_id=producto_id)
                elif hasattr(root, 'almacen_view'):
                    root.almacen_view.show_busqueda()
                    
        except Exception:
            logger.exception("Error navegando a Almacén desde recordatorio")

    def setup_barcode(self):
        """Inicializar captura de código de barras."""
        try:
            from kool_tpv.utils.barcode_service import BarcodeService
            root = self.view.winfo_toplevel()
            self._barcode_service = BarcodeService(root, on_barcode=self._on_barcode_scanned)
            self._barcode_service.attach()
            # Guardar referencia en el toplevel para que KeyboardNavigableMixin pueda consultar el buffer
            root._barcode_service = self._barcode_service
            # Pasar referencia al CarritoNavList para que ignore el Enter del escáner
            ticket = getattr(self.view, 'ticket_carrito', None)
            if ticket and hasattr(ticket, 'carrito_nav_list'):
                ticket.carrito_nav_list._barcode_service = self._barcode_service
            logger.info('BarcodeService inicializado')
        except Exception:
            logger.exception('Error inicializando BarcodeService')

    def _setup_keyboard_shortcuts(self):
        """Inicializar gestión de shortcuts de teclado."""
        try:
            from kool_tpv.modulos.tpv.tpv_keyboard_shortcuts import TpvKeyboardShortcuts
            self._keyboard_shortcuts = TpvKeyboardShortcuts(self)
        except Exception:
            logger.exception('Error inicializando TpvKeyboardShortcuts')
            self._keyboard_shortcuts = None

    def _on_barcode_scanned(self, code: str):
        """Callback cuando el escáner detecta un código de barras."""
        logger.info(f"TpvController: Procesando código escaneado: '{code}'")
        try:
            from kool_tpv.base_datos.producto_service import ProductoService
            producto_service = ProductoService(self.db)
            producto = producto_service.buscar_por_ean(code)
            
            if producto is None:
                # Mostrar diálogo de "No encontrado" con opción de Alta Rápida
                from kool_tpv.utils.custom_dialog import show_warning
                
                def on_dialog_closed(confirmed):
                    if confirmed:
                        self._mostrar_alta_rapida(code)
                
                show_warning(
                    parent=self.view,
                    titulo="PRODUCTO NO ENCONTRADO",
                    mensaje=f"EL CÓDIGO {code} NO EXISTE.\n¿DESEAS HACER UN ALTA RÁPIDA?",
                    confirm=True,
                    callback=on_dialog_closed
                )
                return
            
            # Usar el manejador unificado para añadir productos
            self.handle_add_product(producto)
            
        except Exception:
            logger.exception('Error procesando código de barras: %s', code)

    def _mostrar_alta_rapida(self, code: str):
        """Muestra el diálogo de alta rápida de producto."""
        from kool_tpv.modulos.tpv.ui.emergencia_producto_ui import EmergenciaProductoUI
        
        def on_saved(datos):
            if not datos:
                return
            
            try:
                # 1. Crear el producto en la BD (Categoría 3 = Incompleto)
                from kool_tpv.base_datos.producto_service import ProductoService
                service = ProductoService(self.db)
                
                # Datos mínimos para la creación rápida usando el repositorio
                # guardar_producto_completo maneja la transacción y tablas relacionadas (precios, códigos)
                producto_id = service.repo.guardar_producto_completo(
                    nombre=datos['nombre'],
                    nombre_boton='',
                    sku=datos['ean'], # Usamos el EAN como SKU inicial
                    categoria_id=3,   # Incompleto
                    tipo_id=1,        # General
                    proveedor_id=1,   # General
                    iva=21,           # IVA estándar
                    stock_actual=1,   # Empezamos con 1 ya que lo estamos vendiendo
                    stock_min=0,
                    activo=1,
                    pvp=datos['pvp'],
                    coste=Decimal('0.00'),
                    codigos_barras=[datos['ean']]
                )
                
                if not producto_id:
                    ToastWidget.show(self.view, "ERROR AL CREAR EL PRODUCTO", tipo='error')
                    return

                # 2. Obtener el objeto producto completo para el carrito
                nuevo_producto = service.get_producto_para_carrito(producto_id)
                if nuevo_producto:
                    # Añadir al carrito automáticamente
                    self.handle_add_product(nuevo_producto)
                    ToastWidget.show(self.view, "PRODUCTO CREADO Y AÑADIDO", tipo='success')
                    
            except Exception:
                logger.exception("Error en alta rápida de producto")
                ToastWidget.show(self.view, "ERROR CRÍTICO EN ALTA RÁPIDA", tipo='error')

        # Instanciar y mostrar el diálogo
        EmergenciaProductoUI(self.view, ean=code, callback=on_saved)


    def handle_add_product(self, producto: dict):
        """Manejador unificado para añadir productos al carrito con chequeo de pvp_variable."""
        carrito = getattr(self.view, 'carrito_service', None)
        if carrito is None:
            return

        # Si el PVP es variable, preguntar precio
        if int(producto.get('pvp_variable', 0)) == 1:
            def on_price_entered(valor):
                if valor is None: # Cancelado
                    return
                try:
                    # Normalizar separador decimal (coma a punto)
                    valor_limpio = str(valor).replace(',', '.')
                    nuevo_pvp = Decimal(valor_limpio)
                    if nuevo_pvp < 0:
                        ToastWidget.show(self.view, "EL PRECIO NO PUEDE SER NEGATIVO", tipo='error')
                        return
                    
                    # Actualizar PVP y total de línea
                    producto['pvp'] = nuevo_pvp
                    producto['total_linea'] = nuevo_pvp * Decimal(producto.get('cantidad', 1))
                    
                    # Añadir al carrito
                    self._finalizar_add_item(producto)
                except Exception:
                    ToastWidget.show(self.view, "PRECIO INVÁLIDO", tipo='error')

            show_input_dialog(
                parent=self.view,
                tipo='info',
                titulo='PRECIO VARIABLE',
                mensaje=f"INTRODUCE EL PRECIO PARA:\n{producto.get('nombre', '').upper()}",
                valor_defecto="",
                callback=on_price_entered,
                window_title="PVP VARIABLE"
            )
        else:
            # Añadir directamente
            self._finalizar_add_item(producto)

    def _finalizar_add_item(self, producto: dict):
        """Finaliza la adición del item al carrito y actualiza la UI."""
        carrito = getattr(self.view, 'carrito_service', None)
        if not carrito:
            return

        if carrito.add_item(producto, parent_window=self.view):
            logger.info('Producto añadido al carrito -> %s', producto.get('nombre'))
            # Actualizar ticket visual
            ticket = getattr(self.view, 'ticket_carrito', None)
            if ticket and hasattr(ticket, 'update_carrito'):
                ticket.update_carrito()
            
            # Si hay un callback on_add_callback en la subvista actual, llamarlo
            # Esto es para que Favoritos sepa que se añadió algo
            try:
                if hasattr(self.view, '_subview_stack') and self.view._subview_stack:
                    current_view = self.view._subview_stack[-1]["view"]
                    if hasattr(current_view, 'on_add_callback') and callable(current_view.on_add_callback):
                        current_view.on_add_callback()
            except Exception:
                pass

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

        # StockSubView: provide a proxy so it's created only on demand
        try:
            class _StockUIProxy:
                def __init__(self, view, db, carrito_service):
                    self.view = view
                    self.db = db
                    self.carrito_service = carrito_service

                def show(self):
                    try:
                        sub = getattr(self.view, '_stock_subview', None)
                        exists = False
                        try:
                            if sub and getattr(sub, 'winfo_exists', None):
                                exists = bool(sub.winfo_exists())
                        except Exception:
                            exists = False

                        if not sub or not exists:
                            try:
                                from kool_tpv.modulos.tpv.subviews.stock_subview import StockSubView
                                parent = getattr(self.view, 'center_area', self.view)
                                sub = StockSubView(
                                    parent=parent,
                                    db=self.db,
                                    carrito_service=self.carrito_service,
                                    view=self.view
                                )
                                self.view._stock_subview = sub
                            except Exception:
                                logger.exception('Error creando StockSubView dinámicamente')
                                return

                        try:
                            self.view.push_subview(sub, "STOCK")
                        except Exception:
                            logger.exception('Error mostrando StockSubView')
                    except Exception:
                        logger.exception('Error en StockUIProxy.show')

            self._stock_ui = _StockUIProxy(self.view, self.db, carrito_service)
            logger.debug('StockSubView proxy creado')
        except Exception:
            logger.exception('Error creando StockSubView proxy')
            self._stock_ui = None

        # CierreUI: provide a small adapter with `.show()` so button mapper can
        # call `view._cierre_ui.show()`. The adapter creates the subview
        # dynamically (same behaviour as TicketsSubView handling).
        try:
            class _CierresUIProxy:
                def __init__(self, view, db):
                    self.view = view
                    self.db = db

                def show(self):
                    try:
                        from kool_tpv.modulos.tpv.actions.permisos import check_permiso
                        parent = None
                        try:
                            parent = self.view.winfo_toplevel()
                        except Exception:
                            parent = self.view
                        carrito_service = getattr(self.view, 'carrito_service', None)
                        if not check_permiso(carrito_service, 'permiso_cierre', parent):
                            return

                        sub = getattr(self.view, '_cierres_subview', None)
                        exists = False
                        try:
                            if sub and getattr(sub, 'winfo_exists', None):
                                exists = bool(sub.winfo_exists())
                        except Exception:
                            exists = False

                        if not sub or not exists:
                            try:
                                from kool_tpv.modulos.tpv.subviews.cierres_subview import CierresSubView
                                parent = getattr(self.view, 'center_area', self.view)
                                sub = CierresSubView(parent=parent, db=self.db, view=self.view)
                            except Exception:
                                logger.exception('Error creando CierresSubView dinámicamente')
                                return

                            try:
                                self.view._cierres_subview = sub
                                if getattr(self.view, 'controller', None):
                                    try:
                                        self.view.controller._cierres_subview = sub
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        try:
                            self.view.push_subview(sub, "CIERRES")
                        except Exception:
                            logger.exception('Error mostrando CierresSubView')
                    except Exception:
                        logger.exception('Error en CierresUIProxy.show')

            self._cierre_ui = _CierresUIProxy(self.view, self.db)
            logger.debug('Cierre UI proxy creado')
        except Exception:
            logger.exception('Error creando CierreUI proxy')
            self._cierre_ui = None

        # Tickets handled via SubView on demand (TicketsSubView)
        self._tickets_ui = None

        # Exponer acciones en view para compatibilidad
        self.view._cliente_action = self._cliente_action
        self.view._cajero_action = self._cajero_action
        self.view.descuento_action = self.descuento_action
        self.view._devolucion_action = self._devolucion_action
        self.view._stock_ui = self._stock_ui
        self.view._cierre_ui = self._cierre_ui

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
                on_finalize=self.finalize_sale,
                view=self.view
            )

            # Exponer en view para compatibilidad con button_action_mapper
            self.view._cash_controller = self.payment_controllers.get('cash')
            self.view._multi_controller = self.payment_controllers.get('multi')
            self.view._tarjeta_controller = self.payment_controllers.get('tarjeta')
            self.view._web_controller = self.payment_controllers.get('web')
            self.view._devolucion_controller = self.payment_controllers.get('devolucion')
            self.view._vale_controller = self.payment_controllers.get('vale')

            logger.info(f'Payment controllers creados: {list(self.payment_controllers.keys())}')

        except Exception:
            logger.exception('Error creando payment controllers')

    def _after_vale_applied(self):
        """Callback tras aplicar un vale: actualiza UI y activa el pago original."""
        try:
            # Actualizar display del carrito
            ticket = getattr(self.view, 'ticket_carrito', None)
            if ticket and hasattr(ticket, 'update_carrito'):
                ticket.update_carrito()
            # Activar el tipo de pago que el usuario había elegido originalmente
            tc = getattr(self.view, 'ticket_carrito', None)
            pending = getattr(tc, 'pending_payment_type', 'efectivo') if tc else 'efectivo'
            try:
                from kool_tpv.modulos.tpv.button_action_mapper import _activate_payment
                _activate_payment(self.view, pending)
            except Exception:
                # Fallback a efectivo si falla la activación del pago pendiente
                if tc:
                    try:
                        for widget in tc.payment_area.winfo_children():
                            widget.pack_forget()
                    except Exception:
                        pass
                    cash_ctrl = getattr(self.view, '_cash_controller', None)
                    if cash_ctrl:
                        try:
                            carrito = getattr(self.view, 'carrito_service', None)
                            resumen = carrito.get_resumen_financiero() if carrito else {}
                            cash_ctrl.set_total(resumen.get('total', 0.0))
                            cash_ctrl.pack(in_=tc.payment_area, fill="both", expand=True)
                            tc.active_payment_controller = cash_ctrl
                            tc.active_payment_type = 'efectivo'
                        except Exception:
                            pass
            # Limpiar estado pendiente
            if tc:
                try:
                    tc.pending_payment_type = None
                except Exception:
                    pass
            logger.info(f'Vale aplicado, continuando a pago {pending}')
        except Exception:
            logger.exception('Error en _after_vale_applied')

    def _after_vale_omitted(self):
        """Callback tras omitir un vale: activa el pago original directamente."""
        try:
            tc = getattr(self.view, 'ticket_carrito', None)
            pending = getattr(tc, 'pending_payment_type', 'efectivo') if tc else 'efectivo'

            def _make_wrapper(tipo_pago):
                def wrapper(data: dict):
                    if tipo_pago == 'Efectivo':
                        efectivo = data.get('cantidad_entregada', data.get('total', 0.0))
                        self.finalize_sale(efectivo=efectivo, forma_pago='Efectivo', importe_efectivo=efectivo, importe_tarjeta=0.0)
                    elif tipo_pago == 'Tarjeta':
                        self.finalize_sale(efectivo=None, forma_pago='Tarjeta', importe_efectivo=0.0, importe_tarjeta=data.get('total', 0.0))
                    elif tipo_pago == 'Web':
                        self.finalize_sale(efectivo=None, forma_pago='Web', importe_efectivo=0.0, importe_tarjeta=0.0, importe_web=data.get('total', 0.0))
                    elif tipo_pago == 'Multi':
                        self.finalize_sale(efectivo=None, forma_pago='Multi', importe_efectivo=data.get('efectivo', 0.0), importe_tarjeta=data.get('tarjeta', 0.0))
                return wrapper

            try:
                if pending == 'efectivo':
                    tc.activar_pago_efectivo(on_finalizar=_make_wrapper('Efectivo'))
                elif pending == 'tarjeta':
                    tc.activar_pago_tarjeta(on_finalizar=_make_wrapper('Tarjeta'))
                elif pending == 'web':
                    tc.activar_pago_web(on_finalizar=_make_wrapper('Web'))
                elif pending == 'multi':
                    tc.activar_pago_multi(on_finalizar=_make_wrapper('Multi'))
            except Exception:
                logger.exception('Error activando pago tras omitir vale')
                # Fallback a efectivo
                if tc:
                    try:
                        for widget in tc.payment_area.winfo_children():
                            widget.pack_forget()
                    except Exception:
                        pass
                    cash_ctrl = getattr(self.view, '_cash_controller', None)
                    if cash_ctrl:
                        try:
                            carrito = getattr(self.view, 'carrito_service', None)
                            resumen = carrito.get_resumen_financiero() if carrito else {}
                            cash_ctrl.set_total(resumen.get('total', 0.0))
                            cash_ctrl.pack(in_=tc.payment_area, fill="both", expand=True)
                            tc.active_payment_controller = cash_ctrl
                            tc.active_payment_type = 'efectivo'
                        except Exception:
                            pass
            # Limpiar estado pendiente
            if tc:
                try:
                    tc.pending_payment_type = None
                except Exception:
                    pass
            logger.info(f'Vale omitido, continuando a pago {pending}')
        except Exception:
            logger.exception('Error en _after_vale_omitted')

    def rebind_buttons(self):
        """Rebind botones grid usando mapper."""
        try:
            from kool_tpv.modulos.tpv.button_action_mapper import rebind_buttons
            rebind_buttons(self.view)
            logger.info('Botones rebound con mapper')
        except Exception:
            logger.exception('Error rebinding botones')

        # Setup global TicketDisplay (overlay) and cache
        try:
            self.setup_ticket_display()
        except Exception:
            logger.exception('Error setting up global TicketDisplay')

    def setup_ticket_display(self):
        """Crear una instancia única de TicketDisplay colocada sobre el `ticket_carrito`.

        Esta instancia actúa como visor global reutilizable por subviews.
        """
        try:
            # cache para tickets generados en memoria
            self._ticket_display_cache = {}

            # crear widget pero no empaquetarlo; lo mostraremos con `place` cuando haga falta
            try:
                from kool_tpv.utils.widgets.ticket_display import TicketDisplay
                parent = getattr(self.view, 'right_container', None) or getattr(self.view, 'ticket_carrito', None)
                # ensure parent is a container
                if parent is None:
                    parent = self.view
                self._ticket_display = TicketDisplay(parent, module_name='tickets')
            except Exception:
                self._ticket_display = None
        except Exception:
            self._ticket_display = None
            self._ticket_display_cache = {}

    def show_ticket(self, ticket_id: int):
        """Mostrar el ticket en el visor global. Usa caché y genera via ImpresoraService si hace falta."""
        try:
            if ticket_id is None:
                return

            # buscar en caché
            content = None
            try:
                content = self._ticket_display_cache.get(ticket_id)
            except Exception:
                content = None

            if not content:
                try:
                    if self.impresora_service:
                        content = self.impresora_service.generar_ticket_desde_id(ticket_id)
                    else:
                        # fallback: instanciar localmente
                        from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                        imp = ImpresoraService(db=self.db)
                        content = imp.generar_ticket_desde_id(ticket_id)
                except Exception:
                    logger.exception('Error generando ticket para visor global')
                    content = 'No se pudo generar el ticket.'

                try:
                    self._ticket_display_cache[ticket_id] = content
                except Exception:
                    pass

            # mostrar en el visor
            if getattr(self, '_ticket_display', None):
                try:
                    # place over parent to behave as overlay
                    parent = self._ticket_display.master
                    try:
                        self._ticket_display.place(relx=0, rely=0, relwidth=1, relheight=1)
                    except Exception:
                        # fallback to pack if place fails
                        self._ticket_display.pack(fill='both', expand=True)

                    try:
                        self._ticket_display.lift()
                    except Exception:
                        pass

                    try:
                        self._ticket_display.set_content(content)
                    except Exception:
                        logger.exception('Error seteando contenido en visor global')
                except Exception:
                    logger.exception('Error mostrando visor global')

        except Exception:
            logger.exception('Error en show_ticket')

    def hide_ticket(self):
        """Ocultar y limpiar el visor global."""
        try:
            disp = getattr(self, '_ticket_display', None)
            if not disp:
                return
            try:
                disp.place_forget()
            except Exception:
                try:
                    disp.pack_forget()
                except Exception:
                    pass
            try:
                disp.clear()
            except Exception:
                pass
        except Exception:
            logger.exception('Error ocultando visor global')

    def show_cierre(self, cierre_id: int):
        """Mostrar cierre en visor global."""

        try:
            if cierre_id is None:
                return

            # Generar texto usando ImpresoraService
            imp = self.impresora_service
            if not imp:
                from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                imp = ImpresoraService(db=self.db)

            texto = imp.generar_cierre_desde_id(cierre_id)

            if not texto:
                logger.error(f'No se pudo generar cierre {cierre_id}')
                return

            # Mostrar en visor
            cache_key = f'cierre_{cierre_id}'
            try:
                self._ticket_display_cache[cache_key] = texto
            except Exception:
                try:
                    self._ticket_display_cache = {cache_key: texto}
                except Exception:
                    pass

            if self._ticket_display:
                try:
                    self._ticket_display.set_content(texto)
                except Exception:
                    logger.exception('Error seteando contenido en _ticket_display')
                try:
                    self._ticket_display.place(relx=0, rely=0, relwidth=1, relheight=1)
                except Exception:
                    try:
                        self._ticket_display.pack(fill='both', expand=True)
                    except Exception:
                        pass
                try:
                    self._ticket_display.lift()
                except Exception:
                    pass

        except Exception:
            logger.exception(f'Error en show_cierre({cierre_id})')

    def _build_ticket_payload(self, db, carrito_items, resumen, efectivo, **kwargs):
        """Construir payload listo para los TicketProcessors.

        Convierte importes a céntimos y prepara la estructura esperada.
        """
        try:
            from kool_tpv.utils.time_utils import now_utc_str
            created_at = now_utc_str()
        except Exception:
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

        # Calcular tesoro_total_ticket (snapshot del tesoro después de esta compra)
        tesoro_total_ticket_cents = 0
        try:
            if _cliente_id:
                row = db.fetch_one("SELECT COALESCE(tesoro_total, 0) FROM clientes WHERE id = ?", (_cliente_id,))
                tesoro_actual_cents = int(row[0]) if row and row[0] is not None else 0
                puntos_otorgar = int(kwargs.get('puntos_otorgar_cents', 0))
                puntos_gastados = int(kwargs.get('puntos_gastados_cents', 0))
                tesoro_total_ticket_cents = tesoro_actual_cents + puntos_otorgar - puntos_gastados
        except Exception:
            pass

        payload = {
            'resumen': resumen,
            'created_at': created_at,
            'num_ticket': num_ticket,
            'cajero': kwargs.get('cajero'),
            'cliente': _cliente_name,
            'cliente_id': _cliente_id,
            'subtotal_cents': prepare_for_db(_dec(resumen.get('subtotal', '0'))),
            'total_cents': prepare_for_db(_dec(resumen.get('total', '0'))),
            'iva_desglose_json': json.dumps({
                str(k): prepare_for_db(_dec(str(v)))
                for k, v in resumen.get('iva_desglose', {}).items()
            }),
            'pagado_cents': prepare_for_db(_dec(efectivo)) if efectivo is not None else prepare_for_db(_dec(resumen.get('total', '0'))),
            'cambio_cents': (
                0 if kwargs.get('tipo_ticket') == 'devolucion'
                else prepare_for_db(max(
                    _dec(0),
                    _dec(kwargs.get('importe_efectivo', 0)) + _dec(kwargs.get('importe_tarjeta', 0)) - _dec(resumen.get('total', '0'))
                ))
            ),
            'importe_efectivo_cents': prepare_for_db(_dec(kwargs.get('importe_efectivo', 0))),
            'importe_tarjeta_cents': prepare_for_db(_dec(kwargs.get('importe_tarjeta', 0))),
            'importe_web_cents': prepare_for_db(_dec(kwargs.get('importe_web', 0))) if kwargs.get('importe_web', None) is not None else None,
            'descuento_euros_cents': prepare_for_db(_dec(kwargs.get('descuento_data', {}).get('euros', 0))),
            'descuento_tipo': kwargs.get('descuento_data', {}).get('tipo'),
            # Normalizar descuento_valor según tipo: porcentaje -> int, directo -> céntimos int
            # Evitar pasar decimal.Decimal directamente al repositorio (SQLite no lo admite)
            'descuento_valor': None,
            'forma_pago': kwargs.get('forma_pago', 'Efectivo'),
            'tesoro_total_ticket_cents': tesoro_total_ticket_cents,
            'ticket_text_snapshot': None,
            'carrito_items': carrito_items,
            'total_unidades': sum(int(item.get('cantidad', 0)) for item in (carrito_items or [])),
            'pagos': [],
        }

        # pagos desglosados (métodos normalizados en minúsculas)
        pagos = []
        efectivo_val = kwargs.get('importe_efectivo')
        tarjeta_val = kwargs.get('importe_tarjeta')
        web_val = kwargs.get('importe_web')
        if efectivo_val:
            pagos.append(('efectivo', prepare_for_db(_dec(efectivo_val))))
        if tarjeta_val:
            pagos.append(('tarjeta', prepare_for_db(_dec(tarjeta_val))))
        # Preferimos importe_web si se proporciona; si no y la forma de pago indica 'web',
        # calcular el resto pendiente como pago web para mantener consistencia.
        if web_val:
            pagos.append(('web', prepare_for_db(_dec(web_val))))
        else:
            forma = (kwargs.get('forma_pago') or '').lower()
            try:
                total_cents = prepare_for_db(_dec(resumen.get('total', '0')))
            except Exception:
                total_cents = None
            # calcular restante = total - efectivo - tarjeta
            try:
                restante = None
                if total_cents is not None:
                    efe = prepare_for_db(_dec(efectivo_val)) if efectivo_val is not None else 0
                    tar = prepare_for_db(_dec(tarjeta_val)) if tarjeta_val is not None else 0
                    restante = int(total_cents) - int(efe) - int(tar)
                if forma in ('web', 'online') and restante and int(restante) > 0:
                    pagos.append(('web', int(restante)))
            except Exception:
                # no bloquear: si falla cálculo, no añadir pago web automáticamente
                pass
        payload['pagos'] = pagos

        # Normalizar descuento_valor y asignarlo al payload (int or None)
        try:
            descuento_raw = (kwargs.get('descuento_data') or {})
            d_tipo = descuento_raw.get('tipo')
            d_val = descuento_raw.get('valor')
            if d_tipo is None:
                payload['descuento_valor'] = None
            else:
                from decimal import Decimal as _Dec
                if d_val is None:
                    payload['descuento_valor'] = None
                else:
                    # porcentaje esperado como entero (e.g., 10)
                    if str(d_tipo).lower() in ('porcentaje', 'percent', '%'):
                        try:
                            payload['descuento_valor'] = int(_Dec(str(d_val)))
                        except Exception:
                            try:
                                payload['descuento_valor'] = int(float(d_val))
                            except Exception:
                                payload['descuento_valor'] = None
                    else:
                        # directo: valor expresado en euros -> convertir a céntimos
                        try:
                            payload['descuento_valor'] = int(prepare_for_db(_Dec(str(d_val))))
                        except Exception:
                            try:
                                payload['descuento_valor'] = int(prepare_for_db(_Dec(str(d_val or 0))))
                            except Exception:
                                payload['descuento_valor'] = None
        except Exception:
            payload['descuento_valor'] = None

        # No generar snapshot aquí: el `num_ticket` real se asigna en el processor
        # dentro de la transacción. La snapshot se generará y persistirá tras
        # la creación exitosa del ticket (ver finalize_sale). Mantener
        # `ticket_text_snapshot` vacío para evitar pasar Decimals a la BD.
        payload['ticket_text_snapshot'] = None

        # Log para depuración: mostrar pagos y campos relacionados
        try:
            logger.debug('TPV payload pagos: %s importe_web_cents=%s forma_pago=%s', pagos, payload.get('importe_web_cents'), payload.get('forma_pago'))
        except Exception:
            pass

        # puntos ya en céntimos (int) — sin conversión adicional
        if 'puntos_otorgar_cents' in kwargs:
            payload['puntos_otorgar_cents'] = int(kwargs.get('puntos_otorgar_cents', 0))
        if 'puntos_restar_cents' in kwargs:
            payload['puntos_restar_cents'] = int(kwargs.get('puntos_restar_cents', 0))
        if 'puntos_gastados_cents' in kwargs:
            payload['puntos_gastados_cents'] = int(kwargs.get('puntos_gastados_cents', 0))

        # Construir lista de descuentos para DescuentoProcessor
        descuentos_list = []
        desc_data = kwargs.get('descuento_data') or {}
        if desc_data and desc_data.get('euros') and float(desc_data.get('euros', 0)) > 0:
            descuentos_list.append({
                'tipo': desc_data.get('tipo'),
                'valor': desc_data.get('valor'),
                'valor_cents': prepare_for_db(_dec(desc_data.get('euros', 0))),
            })
        payload['descuentos'] = descuentos_list

        # Añadir datos del vale de devolución si existe
        vale_aplicado = kwargs.get('vale_aplicado')
        if vale_aplicado:
            payload['vale_id'] = vale_aplicado.get('id')
            payload['vale_cents'] = int(vale_aplicado.get('importe_cents', 0))
        else:
            payload['vale_id'] = None
            payload['vale_cents'] = None

        return payload

    def finalize_sale(
        self,
        efectivo=None,
        forma_pago='Efectivo',
        importe_efectivo=None,
        importe_tarjeta=None,
        importe_web=None,
    ):
        """Finalizar venta: preparar datos y delegar a TpvService.

        Args:
            efectivo: Cantidad pagada (Decimal o float)
            forma_pago: Método de pago
            importe_efectivo: Desglose efectivo
            importe_tarjeta: Desglose tarjeta
        """
        try:
            carrito_service = getattr(self.view, 'carrito_service', None)
            if not carrito_service:
                logger.error('carrito_service no disponible')
                return

            # Validar carrito no vacío
            if carrito_service.is_empty():
                ToastWidget.show(self.view, 'NO SE PUEDE REALIZAR UNA VENTA SIN ARTÍCULOS', tipo='error')
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
                'importe_web': importe_web if importe_web is not None else None,
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
                ToastWidget.show(self.view, 'DEBE AUTENTICAR UN CAJERO ANTES DE FINALIZAR LA VENTA', tipo='error')
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

            # Obtener cliente_id antes de calcular puntos (ambos bloques lo necesitan)
            _cs = ticket_data.get('carrito_service')
            try:
                _cliente = _cs.get_cliente() if _cs else None
            except Exception:
                _cliente = None
            cliente_id = _cliente.get('id') if isinstance(_cliente, dict) and _cliente else None

            # Calcular puntos si procede (resultado ya en céntimos int)
            puntos_otorgar_cents = 0
            puntos_gastados_cents = 0
            puntos_revertir_cents = 0
            try:
                if tipo_ticket == 'venta_fidelizacion' and self.fidelizacion_service:
                    _puntos_gastados_euros = Decimal(str(resumen.get('puntos_canjeados', 0)))
                    puntos_otorgar_cents = self.fidelizacion_service.calcular_puntos_ganados(carrito_items, _puntos_gastados_euros)
                    puntos_gastados_cents = int(prepare_for_db(_puntos_gastados_euros))
                elif tipo_ticket == 'devolucion' and self.fidelizacion_service and cliente_id:
                    # Calcular cuántos puntos generarían estos artículos en una venta normal
                    # para revertir exactamente esa cantidad del saldo del cliente
                    _items_abs = [{**it, 'cantidad': abs(int(it.get('cantidad', 0)))} for it in (carrito_items or [])]
                    puntos_revertir_cents = self.fidelizacion_service.calcular_puntos_ganados(_items_abs, Decimal('0'))
                    # tesoro_ganado en el ticket se guarda en negativo (auditoría coherente)
                    puntos_otorgar_cents = -puntos_revertir_cents
            except Exception:
                logger.exception('Error calculando puntos de fidelización')

            # Obtener num_ticket antes de llamar al processor
            num_ticket_val = None
            try:
                num_ticket_val = carrito_service.get_num_ticket()
            except Exception:
                num_ticket_val = None
            logger.info(f"num_ticket={num_ticket_val}")

            # Obtener vale aplicado del carrito para pasarlo al payload
            vale_aplicado = None
            try:
                vale_aplicado = carrito_service.get_vale_aplicado()
            except Exception:
                pass

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
                importe_web=importe_web,
                descuento_data=ticket_data.get('descuento_data'),
                puntos_otorgar_cents=puntos_otorgar_cents,
                puntos_gastados_cents=puntos_gastados_cents,
                puntos_restar_cents=puntos_revertir_cents,
                num_ticket=num_ticket_val,
                tipo_ticket=tipo_ticket,
                vale_aplicado=vale_aplicado,
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

                proc_res = processor.process(**payload)
                if isinstance(proc_res, (tuple, list)):
                    ticket_id = proc_res[0]
                    num_ticket = proc_res[1] if len(proc_res) > 1 else payload.get('num_ticket')
                else:
                    ticket_id = proc_res
                    num_ticket = payload.get('num_ticket')
                result = {'success': True, 'ticket_id': ticket_id, 'num_ticket': num_ticket}
            except Exception as e:
                logger.exception('Error procesando ticket con processor')
                result = {'success': False, 'error': str(e)}

            # Procesar resultado
            if result['success']:
                ticket_id = result['ticket_id']
                num_ticket = result['num_ticket']

                # Marcar vale como usado si había uno aplicado
                try:
                    vale_aplicado = carrito_service.get_vale_aplicado()
                    if vale_aplicado:
                        from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
                        vale_service = ValeDevolucionService()
                        vale_service.marcar_usado(vale_aplicado['id'], str(num_ticket))
                        logger.info(f"Vale {vale_aplicado['id']} marcado como usado en ticket {num_ticket}")
                except Exception:
                    logger.exception('Error marcando vale como usado')

                # (Snapshot persistence removed by user request)

                # Extraer datos para resumen ANTES de limpiar carrito
                resumen_data = self._build_resumen_data(ticket_data, num_ticket, forma_pago, efectivo)

                # Limpiar carrito
                carrito_service.clear()

                # Actualizar UI
                ticket_carrito = getattr(self.view, 'ticket_carrito', None)
                if ticket_carrito:
                    ticket_carrito.update_carrito()

                # Imprimir ticket en terminal/impresora (no bloquea si falla)
                if self.tpv_service:
                    try:
                        # Abrir cajón SIEMPRE por petición del usuario (integradado en impresión)
                        self.tpv_service._print_ticket(ticket_id, open_drawer=True)
                    except Exception:
                        logger.exception('Error imprimiendo ticket (no crítico)')

                # Abrir cajón SIEMPRE también por separado (para modo PRINT OFF)
                # Esto garantiza que el cajón se abra incluso si la impresión está desactivada
                try:
                    from kool_tpv.modulos.tpv.actions.cajon import abrir_cajon
                    abrir_cajon(db=self.db)
                except Exception:
                    logger.exception('Error abriendo cajón del dinero (no crítico)')

                # Mostrar resumen en payment_area (reemplaza show_success)
                self._mostrar_resumen_ticket(resumen_data)

                logger.info(f'Venta finalizada exitosamente ticket_id={ticket_id}')
            else:
                # Mostrar error
                error_msg = result.get('error', 'Error desconocido')
                ToastWidget.show(self.view, f'ERROR GUARDANDO TICKET: {error_msg}', tipo='error')
                logger.error(f'Error finalizando venta: {error_msg}')

        except Exception:
            logger.exception('Error inesperado en finalize_sale')
            try:
                ToastWidget.show(self.view, 'ERROR INTERNO AL FINALIZAR LA VENTA', tipo='error')
            except Exception:
                pass

    def _build_resumen_data(self, ticket_data: dict, num_ticket, forma_pago: str, efectivo) -> dict:
        """Construir dict con datos para el resumen post-venta."""
        resumen = ticket_data.get('resumen', {})
        total = float(resumen.get('total', 0.0))

        # Cliente
        cliente_data = ticket_data.get('cliente', {})
        cliente_nombre = cliente_data.get('nombre', '') if isinstance(cliente_data, dict) else str(cliente_data) if cliente_data else ''

        # Calcular efectivo entregado y cambio
        efectivo_entregado = 0.0
        cambio = 0.0

        if forma_pago == 'Efectivo' and efectivo is not None:
            try:
                efectivo_entregado = float(efectivo)
                cambio = max(0.0, efectivo_entregado - total)
            except Exception:
                pass
        elif forma_pago == 'Multi':
            importe_efectivo = ticket_data.get('importe_efectivo', 0.0)
            try:
                efectivo_entregado = float(importe_efectivo)
                cambio = max(0.0, efectivo_entregado - total) if efectivo_entregado > total else 0.0
            except Exception:
                pass

        return {
            'ticket_id': ticket_data.get('ticket_id'),
            'num_ticket': num_ticket,
            'total': total,
            'forma_pago': forma_pago,
            'efectivo_entregado': efectivo_entregado,
            'cambio': cambio,
            'cliente_nombre': cliente_nombre,
        }

    def _mostrar_resumen_ticket(self, resumen_data: dict):
        """Mostrar controller de resumen en el payment_area."""
        try:
            from kool_tpv.modulos.tpv.payment_controller_factory import create_resumen_controller

            ticket_carrito = getattr(self.view, 'ticket_carrito', None)
            if not ticket_carrito:
                return

            # Limpiar payment_area actual
            ticket_carrito._clear_payment_area()

            # Crear y mostrar controller de resumen
            def _on_nueva_venta():
                """Salir del resumen: limpiar payment_area completamente."""
                try:
                    ticket_carrito._clear_payment_area()
                    # No activar ningún controller - dejar el área vacía/limpia
                    ticket_carrito.active_payment_controller = None
                    ticket_carrito.active_payment_type = None
                    logger.info('PaymentControllerResumen cerrado - payment_area limpio')
                except Exception:
                    logger.exception('Error limpiando payment_area desde resumen')

            controller = create_resumen_controller(
                parent=ticket_carrito.payment_area,
                ticket_data=resumen_data,
                on_nueva_venta=_on_nueva_venta
            )

            if controller:
                controller.pack(fill='both', expand=True)
                ticket_carrito.active_payment_controller = controller
                ticket_carrito.active_payment_type = 'resumen'
                logger.info('PaymentControllerResumen mostrado')

        except Exception:
            logger.exception('Error mostrando resumen de ticket')
            try:
                ToastWidget.show(self.view.container, f'Ticket #{resumen_data.get("num_ticket", "---")} guardado', tipo='success')
            except Exception:
                pass


__all__ = ['TpvController']
