import customtkinter as ctk
# Prefer experimental BuscarArticuloPanelV2 if available (safe fallback to BuscarArticuloPanel)
try:
    # Prefer a dedicated v2 module if present
    from kool_tpv.modulos.tpv.actions.buscar_articulo_v2 import BuscarArticuloPanel
except Exception:
    try:
        import importlib
        _mod = importlib.import_module('kool_tpv.modulos.tpv.actions.buscar_articulo')
        BuscarArticuloPanel = getattr(_mod, 'BuscarArticuloPanelV2', getattr(_mod, 'BuscarArticuloPanel', None))
        if BuscarArticuloPanel is None:
            from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel
    except Exception:
        from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel
import json
from pathlib import Path
from typing import Optional, Dict

# --- RUTA CONFIG ---
BASE_DIR = Path(__file__).resolve().parents[2] 
CONFIG_DIR = BASE_DIR / "config"

def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# --- BREADCRUMB ---
class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.parts = []
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        for widget in self.winfo_children():
            widget.destroy()
        self.parts = parts
        for i, (text, callback) in enumerate(parts):
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)
            is_last = (i == len(parts) - 1)
            if is_last or callback is None:
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                btn = ctk.CTkButton(
                    self, text=text, text_color=self.text_color, fg_color='transparent',
                    hover_color='#333333', font=self.custom_font, command=callback,
                    width=len(text) * 12, height=28, corner_radius=4, cursor='hand2'
                )
                btn.pack(side='left', padx=2)

# --- BUTTON FACTORY ---
class ButtonFactory:
    @staticmethod
    def create_button(parent, text: str, command=None, font=None, color=None, 
                      text_color=None, hover_color=None, width: Optional[int] = None, 
                      height: Optional[int] = None, corner_radius: int = 12, **kwargs):
        params = dict(master=parent, text=(text or "").upper(), command=command, 
                      fg_color=color, hover_color=hover_color, text_color=text_color, 
                      font=font, corner_radius=corner_radius)
        if width: params["width"] = width
        if height: params["height"] = height
        params.update(kwargs)
        return ctk.CTkButton(**params)

# --- CLASE TPV VIEW (CORREGIDA) ---
class TpvView(ctk.CTkFrame):
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.db = db

        # 1. Cargar Configs
        self.layout_cfg = load_config("layout_config.json")
        self.buttons_cfg = load_config("buttons_config.json")
        self.colors_cfg = load_config("colors_config.json")
        self.font_cfg = load_config("font_config.json")

        # 2. Layout
        tpv_layout = self.layout_cfg.get("modules", {}).get("tpv", {})
        right_w = 520 

        # A) Ticket Derecha
        self.right_panel = ctk.CTkFrame(self, width=right_w, corner_radius=0, fg_color="#1a1a1a")
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)
        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            self.ticket_widget = TicketCarrito(self.right_panel)
            self.ticket_widget.pack(fill="both", expand=True)
        except ImportError:
            ctk.CTkLabel(self.right_panel, text="[ ERROR TICKET ]", text_color="red").pack()

        # B) Centro
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        # B.1) Breadcrumb
        bread_font_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font = (bread_font_cfg.get("family", "Courier New"), bread_font_cfg.get("size", 20), "bold")
        bread_color = self.colors_cfg.get("global", {}).get("text_matrix", "#00FF00")

        self.breadcrumb = ClickableBreadcrumb(self.center_area, font=bread_font, text_color=bread_color, height=50)
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)
        self.breadcrumb.update_parts([("INICIO", None), ("VENTAS", None), ("TPV", None)])

        # B.2) Grid
        self.grid_frame = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        # Crear panel de búsqueda (oculto por defecto)
        self.panel_buscar = BuscarArticuloPanel(self)
        
        self._build_grid_buttons()

        
    def _build_grid_buttons(self):
        cols = 4
        rows = 4
        for i in range(cols):
            self.grid_frame.grid_columnconfigure(i, weight=1, uniform="mid_grid")
        for i in range(rows):
            self.grid_frame.grid_rowconfigure(i, weight=1)

        buttons_list = self.buttons_cfg.get("buttons", [])
        colors_map = self.colors_cfg.get("tpv", {}).get("grid_buttons", {})
        f_data = self.font_cfg.get("modules", {}).get("tpv", {}).get("grid_button", {})
        font_grid = (f_data.get("family", "Arial"), f_data.get("size", 20), f_data.get("weight", "bold"))

        for index, btn_data in enumerate(buttons_list):
            grid_info = btn_data.get("grid", {})
            row = grid_info.get("row", index // cols)
            col = grid_info.get("col", index % cols)
            colspan = grid_info.get("colspan", 1)
            rowspan = grid_info.get("rowspan", 1)

            key = btn_data.get("color_key")
            style = colors_map.get(key, {"bg": "#555", "hover": "#666", "text": "white"})

            # Detectar si es el botón de búsqueda y asignarle el comando correcto
            if key == "buscar_articulo":
                cmd = self.panel_buscar.show
            else:
                cmd = None
            
            btn = ButtonFactory.create_button(
                parent=self.grid_frame, text=btn_data.get("label", "???"),
                command=cmd,
                color=style.get("bg"), hover_color=style.get("hover"), text_color=style.get("text"),
                font=font_grid, corner_radius=18,
                border_color=style.get("border"), border_width=style.get("border_width", 0)
            )
            btn.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, padx=10, pady=10, sticky="nsew")