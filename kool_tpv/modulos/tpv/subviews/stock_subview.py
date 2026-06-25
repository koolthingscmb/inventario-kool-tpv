from customtkinter import CTkFrame, CTkEntry
import logging

logger = logging.getLogger(__name__)


class StockSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None, module_name='tpv', on_select_callback=None):
        super().__init__(parent)

        self.db = db
        self.carrito_service = carrito_service
        self.view = view
        self.module_name = module_name
        self.on_select_callback = on_select_callback

        # Header
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_editar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="EDITAR",
            style_key="mini_outline_clientes",
            command=self._on_editar_producto
        )

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar producto...",
            width=300,
        )
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", lambda e: self.search_list.search(self.search_entry.get()))

        self.btn_editar.pack(side="right", padx=10)

        # Lista
        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        try:
            from kool_tpv.base_datos.producto_service import ProductoService
            self.producto_service = ProductoService(self.db)
        except Exception:
            self.producto_service = None

        columns = [
            ("id", 60, "ID"),
            ("nombre", 240, "Nombre Producto"),
            ("stock_actual", 80, "Stock"),
            ("ventas", 80, "Ventas"),
            ("pvp", 120, "PVP"),
        ]

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
        from kool_tpv.utils.config_loader import load_layout_config

        root = self.winfo_toplevel()
        from kool_tpv.utils.keyboard_manager import KeyboardManager
        _km = getattr(root, 'keyboard_manager', None)

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_productos,
            map_function=self._map_producto,
            module_name=self.module_name,
            page_limit=50,
            on_double_click=self._on_producto_seleccionado,
            keyboard_manager=_km,
            layout_config=load_layout_config(),
        )
        self.search_list.pack(fill="both", expand=True)

        nav = getattr(self.search_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_return'):
            nav.bind_return(self._add_selected_producto_to_carrito)

        self.after(100, self.search_entry.focus_set)

    def _on_producto_seleccionado(self, data):
        try:
            if not data:
                return

            try:
                if getattr(self, 'producto_service', None) and hasattr(self.producto_service, 'get_producto_completo'):
                    producto = self.producto_service.get_producto_completo(data.get('id')) or data
                else:
                    producto = data
            except Exception:
                producto = data

            # MODO SELECCIÓN: Si hay callback, devolver el producto y cerrar
            if self.on_select_callback:
                if callable(self.on_select_callback):
                    self.on_select_callback(producto)
                self.view.pop_subview()
                return

            # MODO VENTA: Comportamiento normal
            try:
                producto_data = self.producto_service.get_producto_para_carrito(producto)
            except Exception:
                producto_data = {
                    'id': producto.get('id'),
                    'nombre': producto.get('nombre'),
                    'pvp': producto.get('pvp'),
                    'tipo_iva': producto.get('tipo_iva', 21),
                    'cantidad': 1,
                    'pvp_variable': producto.get('pvp_variable', 0)
                }

            # Intentar usar el controlador de la vista TPV para añadir con lógica de PVP variable
            try:
                if self.view and hasattr(self.view, 'controller') and self.view.controller:
                    self.view.controller.handle_add_product(producto_data)
                    self.view.pop_subview()
                    return
            except Exception:
                logger.exception("Error intentando usar controller para añadir item desde StockSubView")

            parent_win = getattr(self.view, 'ticket_carrito', None)
            added = False
            try:
                added = self.carrito_service.add_item(producto_data, parent_window=parent_win)
            except Exception:
                pass

            if added:
                try:
                    if parent_win:
                        parent_win.update_carrito()
                except Exception:
                    pass
                self.view.pop_subview()

        except Exception:
            logger.exception('Error añadiendo producto al carrito desde StockSubView')

    def _add_selected_producto_to_carrito(self):
        nav = getattr(self.search_list, 'nav_list', None)
        if nav:
            data = nav.get_selected_data()
            if data:
                self._on_producto_seleccionado(data)

    def _on_editar_producto(self):
        try:
            selected = self.search_list.nav_list.get_selected_data()
            if not selected:
                return
            producto_id = selected.get("id")
            if not producto_id:
                return

            from kool_tpv.modulos.almacen.ui.Productos.crear_producto_ui import CrearProductoUI
            crear_ui = CrearProductoUI(
                parent=self.view.center_area,
                db=self.db,
                producto_id=producto_id,
                module_name="almacen"
            )
            try:
                from kool_tpv.modulos.almacen.ui.Productos.cargar_producto import CargarProductoUI
                loader = CargarProductoUI(self.view.center_area, db=self.db)
                loader.apply_to_ui(producto_id, crear_ui)
            except Exception:
                pass

            try:
                widget = crear_ui.get_widget()
            except Exception:
                widget = getattr(crear_ui, 'container', None)

            if widget:
                self.view.push_subview(widget, "PRODUCTO")
        except Exception:
            logger.exception("Error abriendo edición producto")

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

    def destroy(self):
        """Limpieza para evitar fugas de memoria con 5000+ productos."""
        try:
            self.on_select_callback = None
            self.view = None
            if hasattr(self, 'search_list'):
                self.search_list.destroy()
        except: pass
        finally:
            super().destroy()

