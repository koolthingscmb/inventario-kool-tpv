"""PresenciaUI: Interfaz para control de fichajes (entrada/salida)."""
import logging
import customtkinter as ctk
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.modulos.presencia.presencia_service import PresenciaService
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.font_loader import get_font

logger = logging.getLogger(__name__)

class PresenciaUI(ctk.CTkFrame):
    def __init__(self, parent, db, view=None):
        super().__init__(parent)
        self.db = db
        self.view = view
        
        # Servicios
        self.usuario_service = UsuarioService(db)
        self.auth_service = AuthService(db)
        self.presencia_service = PresenciaService(db)
        
        # Estado local
        self.selected_user = None
        
        self._setup_ui()

    def _setup_ui(self):
        # Título
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="CONTROL DE PRESENCIA", 
            font=get_font("title"),
            text_color="#00FF00"
        )
        lbl_titulo.pack(pady=20)

        # Split Container: Izquierda (Chips) | Derecha (Acciones)
        self.split_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Panel Izquierdo: Lista de Usuarios (Chips)
        self.left_panel = ctk.CTkFrame(self.split_frame, fg_color="#1a1a1a", width=500)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.chips_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.chips_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self._create_user_chips()

        # Panel Derecho: Ficha del Usuario Seleccionado
        self.right_panel = ctk.CTkFrame(self.split_frame, fg_color="#1a1a1a", width=400)
        self.right_panel.pack(side="right", fill="both", expand=True)
        
        self.detail_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.detail_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Mensaje inicial en panel derecho
        self.lbl_placeholder = ctk.CTkLabel(
            self.detail_container, 
            text="SELECCIONA UN USUARIO\nPARA FICHAR",
            font=get_font("label"),
            text_color="#666666"
        )
        self.lbl_placeholder.pack(expand=True)

    def _create_user_chips(self):
        """Crea los chips de usuarios al estilo CajeroSubView."""
        usuarios = self.usuario_service.get_all_usuarios()
        
        for i, user in enumerate(usuarios or []):
            row = i // 2
            col = i % 2
            user_id = user.get("id")
            nombre = user.get("nombre")

            btn = ButtonFactory.create_button(
                parent=self.chips_scroll,
                text=nombre,
                style_key="cajero_chip",
                command=lambda uid=user_id, n=nombre: self._on_user_click(uid, n)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        for c in range(2):
            self.chips_scroll.grid_columnconfigure(c, weight=1)

    def _on_user_click(self, user_id, nombre):
        """Al pulsar un usuario, pedir contraseña y mostrar su ficha."""
        # Limpiar panel derecho si había algo
        for w in self.detail_container.winfo_children():
            w.destroy()

        password = show_password_dialog(
            self.winfo_toplevel(),
            titulo="Autenticar",
            mensaje=f"Introduce la contraseña de {nombre}:"
        )

        if not password:
            self._show_placeholder()
            return

        if self.auth_service.validate_user_password(user_id, password):
            self.selected_user = {"id": user_id, "nombre": nombre}
            self._show_user_detail()
        else:
            show_warning(self.winfo_toplevel(), "ERROR", "Contraseña incorrecta")
            self._show_placeholder()

    def _show_placeholder(self):
        for w in self.detail_container.winfo_children():
            w.destroy()
        self.lbl_placeholder = ctk.CTkLabel(
            self.detail_container, 
            text="SELECCIONA UN USUARIO\nPARA FICHAR",
            font=get_font("label"),
            text_color="#666666"
        )
        self.lbl_placeholder.pack(expand=True)

    def _show_user_detail(self):
        """Muestra el estado actual y el botón de fichar para el usuario seleccionado."""
        uid = self.selected_user["id"]
        nombre = self.selected_user["nombre"]
        
        estado = self.presencia_service.get_estado_usuario(uid)
        
        # Nombre Usuario
        ctk.CTkLabel(self.detail_container, text=nombre, font=get_font("title")).pack(pady=(0, 10))
        
        # Estado Actual
        color_estado = "#00FF00" if estado["trabajando"] else "#FF0000"
        ctk.CTkLabel(
            self.detail_container, 
            text=f"ESTADO: {estado['texto']}", 
            font=get_font("label"),
            text_color=color_estado
        ).pack(pady=5)
        
        if estado["desde"]:
            ctk.CTkLabel(
                self.detail_container, 
                text=f"Desde: {estado['desde']}", 
                font=get_font("default"),
                text_color="#AAAAAA"
            ).pack(pady=2)

        # Botón Fichar
        texto_boton = "FICHAR SALIDA" if estado["trabajando"] else "FICHAR ENTRADA"
        estilo_boton = "action_error" if estado["trabajando"] else "action_success"
        
        btn_fichar = ButtonFactory.create_button(
            parent=self.detail_container,
            text=texto_boton,
            style_key=estilo_boton,
            command=self._on_fichar_click
        )
        btn_fichar.pack(pady=30, padx=20, fill="x")
        
        # Historial Reciente
        ctk.CTkLabel(self.detail_container, text="ÚLTIMOS MOVIMIENTOS", font=get_font("default"), text_color="#666666").pack(pady=(20, 5))
        historial = self.presencia_service.get_historial(uid)
        
        for h in historial:
            entrada = h['entrada']
            salida = h['salida'] or "..."
            txt = f"{entrada} -> {salida}"
            ctk.CTkLabel(self.detail_container, text=txt, font=("Courier New", 10), text_color="#888888").pack()

    def _on_fichar_click(self):
        """Ejecuta la acción de fichar."""
        if not self.selected_user:
            return
            
        uid = self.selected_user["id"]
        res = self.presencia_service.fichar(uid)
        
        if res["success"]:
            tipo = "ENTRADA" if res["tipo"] == "entrada" else "SALIDA"
            ToastWidget.show(self.winfo_toplevel(), f"{tipo} REGISTRADA CORRECTAMENTE", tipo="success")
            # Recargar detalle
            self._show_user_detail()
        else:
            ToastWidget.show(self.winfo_toplevel(), f"ERROR AL FICHAR: {res.get('error')}", tipo="error")
