from customtkinter import CTkFrame, CTkLabel
from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList


class ClienteSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)

        # Mantener referencias a DB y servicio carrito
        self.db = db
        self.carrito_service = carrito_service

        # Header (arriba)
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        # Placeholder para botón editar
        self.btn_editar = CTkLabel(self.header_frame, text="EDITAR (placeholder)")
        self.btn_editar.pack(side="right", padx=10)

        # Servicio de clientes
        try:
            self.cliente_service = ClienteService(self.db)
        except Exception:
            self.cliente_service = None

        # Guardar referencia a la vista que creó este subview (TpvView)
        self.view = view

        # Keyboard manager desde el toplevel (consistente con otras UIs)
        root = self.winfo_toplevel()

        from kool_tpv.utils.keyboard_manager import KeyboardManager

        if not hasattr(root, "keyboard_manager") or root.keyboard_manager is None:
            root.keyboard_manager = KeyboardManager(root)

        self.keyboard_manager = root.keyboard_manager
        print("KeyboardManager en TPV:", self.keyboard_manager)

        # Columnas para la NavList
        columns = [
            ("id", 60),
            ("nombre", 240),
            ("nivel_level", 80),
            ("nivel_nombre", 160),
            ("tesoro_total", 120),
        ]

        # Crear SearchablePaginatedNavList reutilizable
        try:
            self.search_list = SearchablePaginatedNavList(
                parent=self,
                columns=columns,
                search_function=self._buscar_clientes,
                map_function=self._map_cliente,
                module_name="clientes",
                page_limit=50,
                on_double_click=self._on_cliente_double_click,
                keyboard_manager=self.keyboard_manager,
            )
            self.search_list.pack(fill="both", expand=True, padx=20, pady=10)
        except Exception:
            # Fallback: mostrar un placeholder si falla
            placeholder_label = CTkLabel(self, text="LISTA CLIENTES (placeholder)", font=("Arial", 18))
            placeholder_label.pack(pady=20)

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
                else:
                    parent_view = self.master.master  # fallback
                    parent_view.pop_subview()
        except Exception:
            import logging
            logging.exception("Error asignando cliente al carrito")

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
