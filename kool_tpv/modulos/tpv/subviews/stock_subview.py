from customtkinter import CTkFrame, CTkLabel
import logging

logger = logging.getLogger(__name__)
# ClienteService and NavList are imported lazily inside methods to avoid
# potential circular imports at module import time.


class StockSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)

        # Mantener referencias a DB y servicio carrito
        self.db = db
        self.carrito_service = carrito_service

        # Header (arriba)
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_editar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="EDITAR",
            style_key="mini_outline_clientes",
            command=self._on_editar_cliente
        )

        from customtkinter import CTkEntry

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar producto...",
            width=300,
        )
        self.search_entry.pack(side="left", padx=10)

        self.search_entry.bind(
            "<Return>",
            lambda e: self.search_list.search(self.search_entry.get())
        )

        self.btn_editar.pack(side="right", padx=10)

        # Área de lista (contenido principal)
        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

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

        # Bind Enter en VirtualNavList para añadir producto al carrito
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if nav and hasattr(nav, 'bind_return'):
                nav.bind_return(self._add_selected_producto_to_carrito)
        except Exception:
            pass

        # Foco automático en el entry al abrir
        self.after(100, self._focus_search_entry)

                        
    def _focus_search_entry(self):
        try:
            self.search_entry.focus_set()
        except Exception:
            pass

    def _on_cliente_double_click(self, data):
        try:
            if data:
                detalle = self.cliente_service.get_cliente(data.get("id"))
                self.carrito_service.set_cliente(detalle)
                if hasattr(self.view, "ticket_carrito"):
                    self.view.ticket_carrito.update_cliente(detalle)

                # Volver atrás al grid
                if getattr(self, "view", None) is not None:
                        self.view.pop_subview()
                        try:
                            if getattr(self.view, "ticket_carrito", None):
                                self.view.ticket_carrito.update_carrito()
                        except Exception:
                            pass
                else:
                        parent_view = self.master.master  # fallback
                        try:
                            parent_view.pop_subview()
                        except Exception:
                            pass
                        try:
                            if getattr(parent_view, "ticket_carrito", None):
                                parent_view.ticket_carrito.update_carrito()
                        except Exception:
                            pass
        except Exception:
            import logging
            logging.exception("Error asignando cliente al carrito")

    def _on_producto_double_click(self, data):
        try:
            # Si no se pasa data, intentar obtener la fila seleccionada en la nav_list
            if not data:
                selected = getattr(self.search_list, 'nav_list', None)
                if selected:
                    data = selected.get_selected_data()

            if not data:
                return

            # Obtener detalle completo si el servicio lo permite
            producto = None
            try:
                if getattr(self, 'producto_service', None) and hasattr(self.producto_service, 'get_producto_completo'):
                    producto = self.producto_service.get_producto_completo(data.get('id')) or data
                else:
                    producto = data
            except Exception:
                producto = data

            # Preparar datos completos para añadir al carrito usando ProductoService
            try:
                producto_data = self.producto_service.get_producto_para_carrito(producto)
            except Exception:
                producto_data = {
                    'id': producto.get('id'),
                    'nombre': producto.get('nombre'),
                    'pvp': producto.get('pvp'),
                    'tipo_iva': producto.get('tipo_iva', producto.get('tipo_iva', 21)),
                    'cantidad': 1,
                }

            parent_win = None
            try:
                parent_win = getattr(self.view, 'ticket_carrito', None)
            except Exception:
                parent_win = None

            added = False
            try:
                added = self.carrito_service.add_item(producto_data, parent_window=parent_win)
            except Exception:
                added = False

            if added:
                try:
                    if hasattr(self.view, 'ticket_carrito'):
                        self.view.ticket_carrito.update_carrito()
                except Exception:
                    pass

                # Mantener StockSubView abierto; devolver foco a búsqueda
                try:
                    self.search_entry.focus_set()
                except Exception:
                    pass

        except Exception:
            import logging
            logging.exception('Error añadiendo producto al carrito desde StockSubView')

    def _add_selected_producto_to_carrito(self, event=None):
        try:
            nav = getattr(self.search_list, 'nav_list', None)
            if not nav:
                return
            selected = nav.get_selected_data()
            if not selected:
                return
            self._on_producto_double_click(selected)
        except Exception:
            import logging
            logging.exception('Error en _add_selected_producto_to_carrito')

    def _on_editar_cliente(self):
        try:
            # Obtener producto seleccionado desde el NavList
            try:
                selected = self.search_list.nav_list.get_selected_data()
            except Exception:
                selected = None

            if not selected:
                return

            producto_id = selected.get("id")
            if not producto_id:
                return

            # Instanciar la UI de producto (CrearProductoUI) y mostrar como subview
            try:
                from kool_tpv.modulos.almacen.ui.Productos.crear_producto_ui import CrearProductoUI
            except Exception:
                # Fallback a otra ruta por compatibilidad si existe
                try:
                    from kool_tpv.modulos.almacen.ui.Productos.crear_producto_ui import CrearProductoUI
                except Exception:
                    CrearProductoUI = None

            if CrearProductoUI is None:
                return

            crear_ui = CrearProductoUI(
                parent=self.view.center_area,
                db=self.db,
                producto_id=producto_id,
                module_name="almacen"
            )

            # Prefill: usar el loader para aplicar datos del producto a la instancia UI
            try:
                from kool_tpv.modulos.almacen.ui.Productos.cargar_producto import CargarProductoUI
                loader = CargarProductoUI(self.view.center_area, db=self.db)
                try:
                    applied = loader.apply_to_ui(producto_id, crear_ui)
                except Exception:
                    applied = False
                if not applied:
                    # no bloquear, solo loguear
                    try:
                        import logging
                        logging.warning('CrearProductoUI: no se aplicaron datos para producto_id=%s', producto_id)
                    except Exception:
                        pass
            except Exception:
                # loader no disponible, continuar sin prefill
                try:
                    import logging
                    logging.exception('CargarProductoUI no disponible para prefill')
                except Exception:
                    pass

            # Obtener el widget real y empujar como subview
            try:
                widget = crear_ui.get_widget()
            except Exception:
                widget = getattr(crear_ui, 'container', None)

            if widget is None:
                return

            self.view.push_subview(widget, "PRODUCTO")

        except Exception:
            import logging
            logging.exception("Error abriendo edición cliente")

    def _buscar_productos(self, texto):
        try:
            if not self.producto_service:
                return []
            # listar_productos acepta un termino; pasar texto para filtrar
            return self.producto_service.listar_productos(texto or '')
        except Exception:
            return []

    def _map_producto(self, detalle):
        try:
            # Mapear campos de producto a las columnas esperadas por NavList
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
        super().destroy()

    
