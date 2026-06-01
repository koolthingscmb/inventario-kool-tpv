from customtkinter import CTkFrame, CTkLabel
import logging

logger = logging.getLogger(__name__)

class DevolucionSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)

        # Mantener referencias a DB y servicio carrito
        self.db = db
        self.carrito_service = carrito_service

        # Header (arriba)
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        from kool_tpv.utils.factories.button_factory import ButtonFactory
        # Button should say 'Cliente' instead of 'EDITAR'
        self.btn_cliente = ButtonFactory.create_button(
            parent=self.header_frame,
            text="Cliente",
            style_key="mini_outline_clientes",
            command=self._on_cliente_button
        )

        from customtkinter import CTkEntry

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar producto...",
            width=300,
        )
        self.search_entry.pack(side="left", padx=10)

        # Bind will be set after search_list exists

        self.btn_cliente.pack(side="right", padx=10)

        # Área de lista (contenido principal)
        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        # Apply visual palette from `config` (prefer 'config' colors over 'almacen')
        try:
            from kool_tpv.utils.config_loader import load_colors
            cfg_colors = load_colors('config') or {}
            # Apply safe fallbacks; do not change carrito or button styles
            header_bg = cfg_colors.get('header_bg') or cfg_colors.get('panel_bg') or cfg_colors.get('bg_dark')
            list_bg = cfg_colors.get('background') or cfg_colors.get('panel_bg')
            try:
                if header_bg is not None:
                    self.header_frame.configure(fg_color=header_bg)
            except Exception:
                pass
            try:
                if list_bg is not None:
                    self.list_frame.configure(fg_color=list_bg)
            except Exception:
                pass
        except Exception:
            pass

        # Servicio de productos (importar aquí para evitar ciclos)
        try:
            from kool_tpv.base_datos.producto_service import ProductoService
            self.producto_service = ProductoService(self.db)
        except Exception:
            self.producto_service = None

        # Guardar referencia a la vista que creó este subview (TpvView)
        self.view = view

        # Keyboard manager desde el toplevel (consistente con otras UIs)
        root = self.winfo_toplevel()

        from kool_tpv.utils.keyboard_manager import KeyboardManager

        if not hasattr(root, "keyboard_manager") or root.keyboard_manager is None:
            root.keyboard_manager = KeyboardManager(root)

        self.keyboard_manager = root.keyboard_manager

        # NOTE: Power handler registration removed from __init__
        # TpvView already handles power button for subviews via pop_subview()
        # No need for individual subviews to register their own handlers

        # Columnas para la NavList (clave, ancho, texto de cabecera)
        columns = [
            ("id", 60, "ID"),
            ("nombre", 240, "Nombre Producto"),
            ("stock_actual", 80, "Stock"),
            ("ventas", 80, "Ventas"),
            ("pvp", 120, "PVP"),
        ]

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList

        # Layout config: load central layout configuration (no hardcoded values)
        try:
            from kool_tpv.utils.config_loader import load_layout_config
            layout_config = load_layout_config()
        except Exception:
            layout_config = None

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_productos,
            map_function=self._map_producto,
            module_name="clientes",
            page_limit=50,
            on_double_click=self._on_producto_double_click,
            keyboard_manager=self.keyboard_manager,
            layout_config=layout_config,
        )

        # Al abrir la subvista, forzar que KeyboardManager use la nav_list
        try:
            if getattr(self, 'keyboard_manager', None) and getattr(self.search_list, 'nav_list', None):
                self.keyboard_manager.set_active_list(self.search_list.nav_list)
        except Exception:
            pass

        self.search_list.pack(fill="both", expand=True)

        # Bind Enter key on the internal nav_list to add selected producto via devoluciones
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if nav:
                nav.bind('<Return>', lambda e: self._add_selected_producto_to_devolucion())
        except Exception:
            pass

        # instantiate DevolucionesService and start mode
        try:
            from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService
            self.devoluciones_service = DevolucionesService(self.db, self.carrito_service)
            try:
                self.devoluciones_service.start_devolucion()
            except Exception:
                pass
        except Exception:
            self.devoluciones_service = None

    def _on_cliente_button(self):
        try:
            # reuse same fallback as DevolucionesPanel: open ClienteAction if available
            if getattr(self, 'view', None) is not None and getattr(self.view, '_cliente_action', None) is not None:
                try:
                    self.view._cliente_action.ejecutar()
                    return
                except Exception:
                    pass
            from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
            carrito = None
            if getattr(self, 'devoluciones_service', None) is not None and getattr(self.devoluciones_service, 'carrito_service', None) is not None:
                carrito = self.devoluciones_service.carrito_service
            if carrito is None and getattr(self, 'view', None) is not None and getattr(self.view, 'carrito_service', None) is not None:
                carrito = self.view.carrito_service
            db_ref = None
            try:
                db_ref = getattr(self.root, 'db', None) if getattr(self, 'root', None) is not None else None
                if db_ref is None:
                    db_ref = getattr(self, 'db', None)
            except Exception:
                db_ref = None
            try:
                action = ClienteAction(getattr(self, 'view', None) or self, db_ref, carrito)
                action.ejecutar()
            except Exception:
                logging.exception('Error abriendo panel CLIENTES desde DevolucionSubView')
        except Exception:
            logging.exception('Error en boton cliente')

    def _on_producto_double_click(self, data):
        try:
            # If no data provided, use selected row
            if not data:
                selected = getattr(self.search_list, 'nav_list', None)
                if selected:
                    data = selected.get_selected_data()

            if not data:
                return

            # Resolve full product if possible
            producto = None
            try:
                if getattr(self, 'producto_service', None) and hasattr(self.producto_service, 'get_producto_completo'):
                    producto = self.producto_service.get_producto_completo(data.get('id')) or data
                else:
                    producto = data
            except Exception:
                producto = data

            added = False
            try:
                if getattr(self, 'devoluciones_service', None) is not None:
                    added = self.devoluciones_service.add_devolucion_item(producto, cantidad=1)
                else:
                    # fallback: use carrito_service but mark as devolucion
                    prod = producto.copy()
                    try:
                        producto_para_carrito = self.producto_service.get_producto_para_carrito(prod, cantidad=1, line_tipo='devolucion')
                        added = self.carrito_service.add_item(producto_para_carrito)
                    except Exception:
                        logging.exception('DevolucionSubView: error añadiendo via carrito fallback')
            except Exception:
                logging.exception('DevolucionSubView: error añadiendo devolucion')

            if added:
                # refresh carrito UI if available
                try:
                    if getattr(self.view, 'ticket_carrito', None):
                        self.view.ticket_carrito.update_carrito()
                    top = self.winfo_toplevel()
                    if getattr(top, 'carrito_ui', None) is not None:
                        top.carrito_ui.update_display()
                except Exception:
                    pass

                # Close subview (pop)
                try:
                    if getattr(self, 'view', None) is not None and hasattr(self.view, 'pop_subview'):
                        self.view.pop_subview()
                except Exception:
                    pass

                # Mostrar indicador MODO DEVOLUCIÓN en payment_area
                try:
                    from kool_tpv.modulos.tpv.button_action_mapper import _activate_payment
                    _activate_payment(self.view, 'devolucion')
                except Exception:
                    pass

        except Exception:
            logging.exception('Error añadiendo producto al carrito desde DevolucionSubView')

    def _add_selected_producto_to_devolucion(self, event=None):
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if not nav:
                return
            selected = nav.get_selected_data()
            if not selected:
                return
            self._on_producto_double_click(selected)
        except Exception:
            logging.exception('Error en _add_selected_producto_to_devolucion')

    def _buscar_productos(self, texto):
        try:
            if not self.producto_service:
                return []
            return self.producto_service.listar_productos(texto or '')
        except Exception:
            return []

    def _map_producto(self, detalle):
        try:
            return {
                "id": detalle.get("id"),
                "nombre": detalle.get("nombre"),
                "stock_actual": detalle.get("stock_actual", 0),
                "ventas": detalle.get("ventas", 0),
                "pvp": detalle.get("pvp", '0.00'),
            }
        except Exception:
            return {}

    # NOTE: _handle_power removed - TpvView handles power button via pop_subview()
    # Individual subviews don't need their own power handlers

    def destroy(self):
        # NOTE: No need to unregister - we don't register in __init__ anymore
        # TpvView manages power handling for all subviews
        try:
            if getattr(self, 'devoluciones_service', None) is not None:
                self.devoluciones_service.end_devolucion()
        except Exception:
            pass
        super().destroy()
