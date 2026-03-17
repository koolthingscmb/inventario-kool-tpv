from customtkinter import CTkFrame, CTkLabel
from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.utils.widgets.nav_list import NavList


class ClienteSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)

        # Mantener referencias a DB y servicio carrito
        self.db = db
        self.carrito_service = carrito_service

        # Header (arriba)
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        # Searchable combo para búsqueda dinámica de clientes
        from kool_tpv.utils.widgets.searchable_combo import SearchableCombo

        self.search_combo = SearchableCombo(
            master=self.header_frame,
            search_function=self._buscar_clientes_dinamico,
            placeholder="Buscar cliente...",
            width=300,
            module_name="clientes"
        )
        self.search_combo.pack(side="left", padx=10)
        self.search_combo.entry.bind(
            '<<SearchableComboSelected>>',
            lambda e: self._on_search_combo_selected()
        )

        # Placeholder para botón editar
        self.btn_editar = CTkLabel(self.header_frame, text="EDITAR (placeholder)")
        self.btn_editar.pack(side="right", padx=10)

        # Área de lista (contenido principal)
        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

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

        # Crear NavList
        try:
            self.nav_list = NavList(
                parent=self.list_frame,
                columns=columns,
                on_select=None,
                on_double_click=self._on_cliente_double_click,
                module_name="clientes",
                keyboard_manager=self.keyboard_manager
            )
            self.nav_list.pack(fill="both", expand=True)

            # Cargar datos (usar método de servicio existente)
            try:
                if self.cliente_service is not None:
                    raw_clientes = self.cliente_service.buscar_clientes(termino="")
                    print(raw_clientes[0].keys())
                    clientes = []
                    for c in raw_clientes:
                        detalle = self.cliente_service.get_cliente(c.get("id"))

                        clientes.append({
                            "id": detalle.get("id"),
                            "nombre": detalle.get("nombre"),
                            "nivel_level": detalle.get("nivel_level"),
                            "nivel_nombre": detalle.get("nivel_nombre"),
                            "tesoro_total": detalle.get("tesoro_total", 0),
                        })

                    # NavList espera lista de dicts con claves coincidentes a `columns`
                    self.nav_list.set_items(clientes)
            except Exception:
                pass
        except Exception:
            # Fallback: mostrar un placeholder si falla
            placeholder_label = CTkLabel(self.list_frame, text="LISTA CLIENTES (placeholder)", font=("Arial", 18))
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

    def _buscar_clientes_dinamico(self, texto):
        try:
            if not self.cliente_service:
                return []
            resultados = self.cliente_service.buscar_clientes(termino=texto)
            salida = []
            for r in resultados:
                salida.append({
                    "id": r.get("id"),
                    "nombre_display": r.get("nombre")
                })
            return salida
        except Exception:
            return []
        
    def _on_search_combo_selected(self):
        try:
            cliente_id = self.search_combo.get_id()
            if not cliente_id:
                return

            # Buscar índice en nav_list
            for idx, (data, _) in enumerate(self.nav_list.rows_data):
                if data.get("id") == cliente_id:
                    self.nav_list._select_row(idx)
                    self.nav_list.focus_set()
                    break
        except Exception:
            pass
