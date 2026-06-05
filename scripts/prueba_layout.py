import customtkinter as ctk
import json
from pathlib import Path
from typing import Optional, Dict

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent 
CONFIG_DIR = BASE_DIR / "kool_tpv" / "config"

# --- FUNCIONES DE CARGA ---
def load_config(filename: str) -> dict:
    try:
        with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando {filename}: {e}")
        return {}

# --- WIDGET BREADCRUMB (Adaptado para prueba) ---
class ClickableBreadcrumb(ctk.CTkFrame):
    def __init__(self, parent, font=None, text_color="white", bg_color="transparent", **kwargs):
        super().__init__(parent, fg_color=bg_color, **kwargs)
        self.parts = []
        self.custom_font = font
        self.text_color = text_color

    def update_parts(self, parts: list):
        # Limpiar anterior
        for widget in self.winfo_children():
            widget.destroy()

        self.parts = parts

        for i, (text, callback) in enumerate(parts):
            # Separador "/"
            if i > 0:
                ctk.CTkLabel(self, text='/', text_color=self.text_color, font=self.custom_font).pack(side='left', padx=4)

            is_last = (i == len(parts) - 1)

            if is_last or callback is None:
                # Texto normal (último nivel)
                ctk.CTkLabel(self, text=text, text_color=self.text_color, font=self.custom_font).pack(side='left', padx=2)
            else:
                # Botón clickeable
                btn = ctk.CTkButton(
                    self,
                    text=text,
                    text_color=self.text_color,
                    fg_color='transparent',
                    hover_color='#333333',
                    font=self.custom_font,
                    command=callback,
                    width=len(text) * 12,
                    height=28,
                    corner_radius=4,
                    cursor='hand2'
                )

                # Efecto Hover (Subrayado simulado cambiando fuente si se pudiera, aquí simple)
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

# --- APP PRINCIPAL ---
class AppPrueba(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Cargar Configuraciones
        self.layout_cfg = load_config("layout_config.json")
        self.buttons_cfg = load_config("buttons_config.json")
        self.colors_cfg = load_config("colors_config.json")
        self.font_cfg = load_config("font_config.json")

        # 2. Configurar Ventana
        w = self.layout_cfg.get("global", {}).get("window", {}).get("width", 1600)
        h = self.layout_cfg.get("global", {}).get("window", {}).get("height", 960)
        self.geometry(f"{w}x{h}")
        self.title("Prueba Layout - Breadcrumb Activo")

        # 3. Dimensiones
        tpv_layout = self.layout_cfg.get("modules", {}).get("tpv", {})
        sidebar_w = tpv_layout.get("sidebar_width", 220)
        right_w = 520 

        # ================= LAYOUT PRINCIPAL =================

        # A) Sidebar
        self.sidebar = ctk.CTkFrame(self, width=sidebar_w, corner_radius=0, fg_color="#2B2B2B")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # B) Ticket
        self.right_panel = ctk.CTkFrame(self, width=right_w, corner_radius=0, fg_color="#1a1a1a")
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False)
        try:
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            self.ticket_widget = TicketCarrito(self.right_panel)
            self.ticket_widget.pack(fill="both", expand=True)
        except ImportError:
            ctk.CTkLabel(self.right_panel, text="[ NO TICKET WIDGET ]", text_color="red").pack(expand=True)

        # C) Centro
        self.center_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#222831")
        self.center_area.pack(side="left", fill="both", expand=True)

        # C.1) Breadcrumb (INTEGRACIÓN NUEVA)
        # Extraer estilo del config
        bread_font_cfg = self.font_cfg.get("breadcrumb", {})
        bread_font = (bread_font_cfg.get("family", "Courier New"), bread_font_cfg.get("size", 20), "bold")
        bread_color = self.colors_cfg.get("global", {}).get("text_matrix", "#00FF00") # Verde Matrix por defecto

        self.breadcrumb = ClickableBreadcrumb(
            self.center_area, 
            font=bread_font, 
            text_color=bread_color,
            height=50
        )
        self.breadcrumb.pack(side="top", fill="x", padx=20, pady=10)

        # Simular navegación
        self.breadcrumb.update_parts([
            ("INICIO", lambda: print("Ir a Inicio")),
            ("VENTAS", lambda: print("Ir a Ventas")),
            ("TPV", None) # Último nivel no clickeable
        ])

        # C.2) Grid
        self.grid_frame = ctk.CTkFrame(self.center_area, fg_color="transparent")
        self.grid_frame.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        self._build_grid_buttons()

    def _build_grid_buttons(self):
        # 1. Configurar Grid
        cols = 4
        rows = 4
        for i in range(cols):
            self.grid_frame.grid_columnconfigure(i, weight=1, uniform="mid_grid")
        for i in range(rows):
            self.grid_frame.grid_rowconfigure(i, weight=1)

        # 2. Datos
        buttons_list = self.buttons_cfg.get("buttons", [])
        colors_map = self.colors_cfg.get("tpv", {}).get("grid_buttons", {})
        f_data = self.font_cfg.get("modules", {}).get("tpv", {}).get("grid_button", {})
        font_grid = (f_data.get("family", "Arial"), f_data.get("size", 20), f_data.get("weight", "bold"))

        for index, btn_data in enumerate(buttons_list):
            grid_info = btn_data.get("grid", {})
            if grid_info:
                row = grid_info.get("row", 0)
                col = grid_info.get("col", 0)
                colspan = grid_info.get("colspan", 1)
                rowspan = grid_info.get("rowspan", 1)
            else:
                row = index // cols
                col = index % cols
                colspan = 1
                rowspan = 1

            key = btn_data.get("color_key")
            style = colors_map.get(key, {"bg": "#555", "hover": "#666", "text": "white"})
            b_color = style.get("border")
            b_width = style.get("border_width")
            if b_color and not b_width: b_width = 2

            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=btn_data.get("label", "???"),
                color=style.get("bg"),
                hover_color=style.get("hover"),
                text_color=style.get("text"),
                font=font_grid,
                corner_radius=18,
                border_color=b_color,
                border_width=b_width if b_width else 0
            )

            btn.grid(row=row, column=col, columnspan=colspan, rowspan=rowspan, padx=10, pady=10, sticky="nsew")

if __name__ == "__main__":
    app = AppPrueba()
    app.mainloop()