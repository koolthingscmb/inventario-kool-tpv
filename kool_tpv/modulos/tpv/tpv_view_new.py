import customtkinter as ctk
import json
from pathlib import Path

# 1. SERVICIO CARRITO
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService

# 2. IMPORTACIÓN EXACTA (SOLUCIÓN)
from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel

# --- RUTA CONFIG ---
BASE_DIR = Path(__file__).resolve().parents[2] 
CONFIG_DIR = BASE_DIR / "config"

def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        for widget in self.winfo_children(): widget.destroy()
        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)
            if callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(self, text=text, text_color=self.text_color, fg_color='transparent', hover_color='#333333', font=self.custom_font, command=callback, width=len(text) * 12, height=28, corner_radius=4, cursor='hand2')
                btn.pack(side='left', padx=2)

class ButtonFactory:
    @staticmethod
    def create_button(parent, text, command=None, font=None, color=None, text_color=None, hover_color=None, width=None, height=None, corner_radius=12, **kwargs):
        params = dict(master=parent, text=(text or "").upper(), command=command, fg_color=color, hover_color=hover_color, text_color=text_color, font=font, corner_radius=corner_radius)
        if width: params["width"] = width
        if height: params["height"] = height
        params.update(kwargs)
        return ctk.CTkButton(**params)

class TpvView(ctk.CTkFrame):
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.db = db

        # Referencia al contenedor para diálogos (requerido por TpvController)
        self.container = self

        # INICIALIZAR EL SERVICIO
        self.carrito_service = CarritoService()

        # Configs
        self.layout_cfg = load_config("layout_config.json")
        self.buttons_cfg = load_config("buttons_config.json")
        self.colors_cfg = load_config("colors_config.json")
        self.font_cfg = load_config("font_config.json")

        # PANEL DERECHO (TICKET)
        self.right_container = ctk.CTkFrame(self, width=520, corner_radius=0, fg_color="#1a1a1a")
        self.right_container.pack(side="right", fill="y")
        self.right_container.pack_propagate(False)

        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            # Pasamos el servicio al ticket
            self.ticket_widget = TicketCarrito(self.right_container, carrito_service=self.carrito_service)
            self.ticket_widget.pack(fill="both", expand=True)

            # Alias para compatibilidad con TpvController
            self.ticket_carrito = self.ticket_widget
        except ImportError:
            ctk.CTkLabel(self.right_container, text="[ ERROR TICKET ]", text_color="red").pack()

        # PANEL CENTRAL
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        bread_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font = (bread_cfg.get("family", "Courier New"), bread_cfg.get("size", 20), "bold")

        self.breadcrumb = ClickableBreadcrumb(self.center_area, font=bread_font, text_color="#00FF00", height=50)
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)
        self.breadcrumb.update_parts([("INICIO", None), ("VENTAS", None), ("TPV", None)])

        self.grid_frame = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        # Lista para referencias a botones del grid (requerido por button_action_mapper)
        self.grid_buttons = []

        # PANEL DE BÚSQUEDA (Con los datos pasados explícitamente)
        self.panel_buscar = BuscarArticuloPanel(
            self, 
            db=self.db, 
            carrito_service=self.carrito_service
        )

        self._build_grid_buttons()
        # Instanciar controlador (gestiona payment controllers, acciones y rebind de botones)
        try:
            from kool_tpv.modulos.tpv.tpv_controller import TpvController
            self.controller = TpvController(self, db=self.db)
        except Exception:
            # No queremos que la vista deje de inicializarse si el controlador falla
            self.controller = None

        # Crear controlador (gestiona payment controllers, acciones y rebind)

    def _build_grid_buttons(self):
        cols = 4
        rows = 4
        for i in range(cols): self.grid_frame.grid_columnconfigure(i, weight=1)
        for i in range(rows): self.grid_frame.grid_rowconfigure(i, weight=1)

        buttons = self.buttons_cfg.get("buttons", [])
        colors_map = self.colors_cfg.get("tpv", {}).get("grid_buttons", {})
        f_data = self.font_cfg.get("modules", {}).get("tpv", {}).get("grid_button", {})
        font_grid = (f_data.get("family", "Arial"), f_data.get("size", 20), f_data.get("weight", "bold"))

        for index, btn_data in enumerate(buttons):
            grid_info = btn_data.get("grid", {})
            row = grid_info.get("row", index // cols)
            col = grid_info.get("col", index % cols)
            key = btn_data.get("color_key")
            style = colors_map.get(key, {"bg": "#555", "hover": "#666", "text": "white"})

            cmd = self.panel_buscar.show if key == "buscar_articulo" else None

            btn = ButtonFactory.create_button(
                parent=self.grid_frame, text=btn_data.get("label", "???"),
                command=cmd,
                color=style.get("bg"), hover_color=style.get("hover"), text_color=style.get("text"),
                font=font_grid, corner_radius=18,
                border_color=style.get("border"), border_width=style.get("border_width", 0)
            )
            btn.grid(row=row, column=col, columnspan=grid_info.get("colspan", 1), rowspan=grid_info.get("rowspan", 1), padx=10, pady=10, sticky="nsew")
            # Guardar referencia para mapper (lista de widgets, como espera el mapper)
            self.grid_buttons.append(btn)

    def teardown(self):
        pass