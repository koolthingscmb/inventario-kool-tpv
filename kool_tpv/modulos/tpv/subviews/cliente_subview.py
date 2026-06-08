from customtkinter import CTkFrame, CTkEntry
import logging
from kool_tpv.modulos.clientes.cliente_service import ClienteService

logger = logging.getLogger(__name__)


class ClienteSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)

        self.db = db
        self.carrito_service = carrito_service
        self.view = view

        # Header
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_editar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="EDITAR",
            style_key="mini_outline_clientes",
            command=self._on_editar_cliente
        )

        self.search_entry = CTkEntry(
            self.header_frame,
            placeholder_text="Buscar cliente...",
            width=300,
        )
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", lambda e: self.search_list.search(self.search_entry.get()))

        self.btn_editar.pack(side="right", padx=10)

        # Lista
        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        try:
            self.cliente_service = ClienteService(self.db)
        except Exception:
            self.cliente_service = None

        columns = [
            ("id", 60, "ID"),
            ("nombre", 240, "Nombre"),
            ("nivel_level", 80, "Nivel"),
            ("nivel_nombre", 160, "Categoría"),
            ("tesoro_total", 120, "Tesoro"),
        ]

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
        from kool_tpv.utils.config_loader import load_layout_config

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_clientes,
            map_function=self._map_cliente,
            module_name="clientes",
            page_limit=50,
            on_double_click=self._on_cliente_seleccionado,
            layout_config=load_layout_config(),
        )
        self.search_list.pack(fill="both", expand=True)

        nav = getattr(self.search_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_return'):
            nav.bind_return(self._add_selected_cliente)

        self.after(100, self.search_entry.focus_set)


    def _on_cliente_seleccionado(self, data):
        try:
            if not data:
                return
            detalle = self.cliente_service.get_cliente(data.get("id"))
            self.carrito_service.set_cliente(detalle)
            if hasattr(self.view, "ticket_carrito"):
                self.view.ticket_carrito.update_cliente(detalle)
            self.view.pop_subview()
        except Exception:
            logger.exception("Error asignando cliente al carrito")

    def _add_selected_cliente(self):
        nav = getattr(self.search_list, 'nav_list', None)
        if nav:
            data = nav.get_selected_data()
            if data:
                self._on_cliente_seleccionado(data)

    def _on_editar_cliente(self):
        try:
            selected = self.search_list.nav_list.get_selected_data()
            if not selected:
                return
            cliente_id = selected.get("id")
            if not cliente_id:
                return

            from kool_tpv.modulos.clientes.crear_cliente_ui import CrearClienteUI
            editar_ui = CrearClienteUI(
                parent=self.view.center_area,
                db=self.db,
                cliente_id=cliente_id,
                module_name="clientes"
            )
            widget = editar_ui.get_widget()
            self.view.push_subview(widget, "EDITAR")
        except Exception:
            logger.exception("Error abriendo edición cliente")

    def _buscar_clientes(self, texto):
        try:
            if not self.cliente_service:
                return []
            return self.cliente_service.buscar_clientes(termino=texto)
        except Exception:
            return []

    def _map_cliente(self, detalle):
        try:
            return {
                "id": detalle.get("id"),
                "nombre": detalle.get("nombre"),
                "nivel_level": detalle.get("nivel_level"),
                "nivel_nombre": detalle.get("nivel_nombre"),
                "tesoro_total": detalle.get("tesoro_total", 0),
            }
        except Exception:
            return {}

    def destroy(self):
        super().destroy()

