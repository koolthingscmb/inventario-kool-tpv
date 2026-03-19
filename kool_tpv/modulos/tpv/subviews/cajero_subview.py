from customtkinter import CTkFrame, CTkLabel, CTkScrollableFrame
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning
from kool_tpv.utils.auth_service import AuthService


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

        try:
            self.auth_service = AuthService(self.db)
        except Exception:
            self.auth_service = None

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
            cajero_id = cajero.get("id") if isinstance(cajero, dict) else getattr(cajero, "id", None)
            nombre = cajero.get("nombre") if isinstance(cajero, dict) else getattr(cajero, "nombre", str(cajero))

            btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text=nombre,
                style_key="cajero_chip",
                command=(lambda uid=cajero_id, n=nombre: self._select_cajero(uid, n))
            )
            btn.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # Ajustar columnas para que se expandan equitativamente
        for c in range(3):
            try:
                self.chips_frame.grid_columnconfigure(c, weight=1)
            except Exception:
                pass

    def _select_cajero(self, user_id, nombre):
        try:
            # Determinar parent para diálogos
            parent = None
            try:
                parent = self.winfo_toplevel()
            except Exception:
                parent = None

            # Pedir contraseña
            password = show_password_dialog(
                parent,
                titulo="Autenticación",
                mensaje=f"Introduce la contraseña de {nombre}:"
            )

            if password is None or password == "":
                return

            # Validar password
            valid = False
            try:
                if self.auth_service:
                    valid = self.auth_service.validate_user_password(user_id, password)
            except Exception:
                valid = False

            if valid:
                # Guardar cajero en CarritoService
                try:
                    self.carrito_service.set_cajero({"id": user_id, "nombre": nombre})
                except Exception:
                    pass

                # Actualizar widget de ticket si existe
                if getattr(self.view, "ticket_widget", None) is not None:
                    try:
                        self.view.ticket_widget.update_cajero(nombre)
                    except Exception:
                        pass

                # Cerrar la subvista
                if getattr(self.view, "pop_subview", None) is not None:
                    self.view.pop_subview()
            else:
                # Mostrar warning y permitir retry
                try:
                    show_warning(
                        parent,
                        "CÓDIGO NO VÁLIDO",
                        "La contraseña introducida es incorrecta.\nInténtalo de nuevo.",
                        callback=lambda: self._select_cajero(user_id, nombre)
                    )
                except Exception:
                    pass

        except Exception:
            pass

