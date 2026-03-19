from customtkinter import CTkFrame, CTkLabel, CTkScrollableFrame
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.utils.factories.button_factory import ButtonFactory


class CajeroSubView(CTkFrame):

    def __init__(self, parent, db, carrito_service, view=None):
        super().__init__(parent)
        self.db = db
        self.carrito_service = carrito_service
        self.view = view

        # Frame completamente vacío
        # Sin header
        # Sin NavList
        # Sin search
        # Sin botones
        # Sin servicios
        # Sin columnas
        # Sin nada más

        # Servicio de usuarios (cajeros)
        try:
            self.usuario_service = UsuarioService(self.db)
        except Exception:
            self.usuario_service = None

        # Área scrollable para chips
        self.chips_frame = CTkScrollableFrame(self)
        self.chips_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Poblar chips con los usuarios (cajeros)
        cajeros = []
        try:
            if self.usuario_service:
                cajeros = self.usuario_service.get_all_usuarios() or []
        except Exception:
            cajeros = []

        for i, cajero in enumerate(cajeros):
            row = i // 3
            col = i % 3
            nombre = cajero.get("nombre") if isinstance(cajero, dict) else getattr(cajero, "nombre", str(cajero))

            btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text=nombre,
                style_key="cajero_chip",
                command=(lambda n=nombre: self._select_cajero(n))
            )
            btn.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Ajustar columnas para que se expandan equitativamente
        for c in range(3):
            try:
                self.chips_frame.grid_columnconfigure(c, weight=1)
            except Exception:
                pass

    def _select_cajero(self, nombre):
        try:
            # Asignar cajero al carrito
            self.carrito_service.set_cajero({"nombre": nombre})

            # Actualizar widget de ticket si existe
            if getattr(self.view, "ticket_widget", None) is not None:
                try:
                    self.view.ticket_widget.update_cajero(nombre)
                except Exception:
                    pass

            # Cerrar la subvista
            if getattr(self.view, "pop_subview", None) is not None:
                self.view.pop_subview()
        except Exception:
            pass

