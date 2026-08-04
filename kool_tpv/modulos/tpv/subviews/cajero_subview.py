"""
Subvista de selección de cajero con navegación por teclado (mixin).
"""
from customtkinter import CTkFrame, CTkScrollableFrame
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.dialogs import show_password_dialog
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin


class CajeroSubView(CTkFrame, KeyboardNavigableMixin):
    """Subvista para selección y autenticación de cajero."""

    def __init__(self, parent, db, carrito_service, view=None):
        CTkFrame.__init__(self, parent)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)

        self.db = db
        self.carrito_service = carrito_service
        self.view = view

        # Servicios
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

        # Crear chips y configurar navegación
        self._create_chips()
        self._setup_keyboard_navigation()

    def _create_chips(self):
        """Crear botones de cajero y poblar lista navegable."""
        cajeros = self.usuario_service.get_all_usuarios() if self.usuario_service else []

        for i, cajero in enumerate(cajeros or []):
            row = i // 3
            col = i % 3
            cajero_id = cajero.get("id") if isinstance(cajero, dict) else getattr(cajero, "id", None)
            nombre = cajero.get("nombre") if isinstance(cajero, dict) else getattr(cajero, "nombre", str(cajero))

            callback = lambda uid=cajero_id, n=nombre: self._select_cajero(uid, n)

            btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text=nombre,
                style_key="cajero_chip",
                command=callback
            )
            btn.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._navigable_buttons.append((btn, callback))

        for c in range(3):
            self.chips_frame.grid_columnconfigure(c, weight=1)

    def _select_cajero(self, user_id, nombre):
        parent = self.winfo_toplevel()

        password = show_password_dialog(
            parent,
            titulo="Autenticar Cajero",
            mensaje=f"Introduce la contraseña de {nombre}:"
        )

        if not password:
            return

        valid = self.auth_service.validate_user_password(user_id, password) if self.auth_service else False

        if valid:
            cajero_data = {"id": user_id, "nombre": nombre}
            user_color = None
            try:
                usr = self.usuario_service.get_usuario(user_id) if self.usuario_service else None
                if usr:
                    cajero_data['rol'] = usr.get('rol', 'Cajero')
                    cajero_data['permiso_cierre'] = usr.get('permiso_cierre', 0)
                    cajero_data['permiso_descuento'] = usr.get('permiso_descuento', 0)
                    cajero_data['permiso_devolucion'] = usr.get('permiso_devolucion', 0)
                    cajero_data['permiso_tickets'] = usr.get('permiso_tickets', 0)
                    cajero_data['permiso_cajon'] = usr.get('permiso_cajon', 0)
                    user_color = usr.get('ui_color')
            except Exception:
                pass
            self.carrito_service.set_cajero(cajero_data)

            ticket_widget = getattr(self.view, "ticket_widget", None)
            if ticket_widget is not None:
                ticket_widget.update_cajero(nombre, color=user_color)

            pop = getattr(self.view, "pop_subview", None)
            if callable(pop):
                pop()
        else:
            ToastWidget.show(parent, 'CÓDIGO NO VÁLIDO — INTÉNTALO DE NUEVO', tipo='error')

