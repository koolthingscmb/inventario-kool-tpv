import customtkinter as ctk
import sys
import logging
import os
import json
import tkinter.font as tkfont
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

# Componentes propios
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.db_init import initialize_database
from kool_tpv.utils.keyboard_manager import KeyboardManager
from kool_tpv.utils.factories.button_factory import ButtonFactory
from PIL import Image

# Configuración de logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/application.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

def load_json_config(filename: str) -> dict:
    base = Path(__file__).resolve().parents[0]
    config_path = base / "kool_tpv" / "config" / filename
    if not config_path.exists():
        logging.error(f"CRÍTICO: Archivo de configuración no encontrado: {config_path}")
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"CRÍTICO: Error de sintaxis en {filename}: {e}")
        return {}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Cargar configuraciones
        self.layout_cfg = load_json_config("layout_config.json")
        self.colors_cfg = load_json_config("colors_config.json")
        self.fonts_cfg = load_json_config("font_config.json")
        self.buttons_cfg = load_json_config("buttons_config.json")

        # 2. Configuración Ventana
        ctk.set_appearance_mode("dark")
        win_cfg = self.layout_cfg.get("global", {}).get("window", {})
        width = win_cfg.get("width", 1600)
        height = win_cfg.get("height", 960)

        self.title("Kool TPV")

        # --- FIX GEOMETRÍA ---
        self.geometry(f"{width}x{height}")
        self.minsize(win_cfg.get("min_width", 1024), win_cfg.get("min_height", 768))
        self.resizable(True, True) 

        def freeze_window():
            self.geometry(f"{width}x{height}")
            self.resizable(False, False)
            self.update_idletasks()

        self.after(200, freeze_window)
        # ---------------------

        # Fondo
        app_bg = self.colors_cfg.get("global", {}).get("layout", {}).get("app_background", "#222831")
        self.configure(fg_color=app_bg)

        # 3. Base de Datos
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "kool_tpv", "base_datos", "kool_bd.db")
        initialize_database(db_path)
        self.db = Database(db_path)
        self.db.connect()

        # 4. Managers Globales
        self.keyboard_mgr = KeyboardManager(self)
        self.nav_buttons = {}
        self.current_view = None
        self._power_handler = None 

        # 5. UI - Estructura Principal
        self._init_ui_structure()
        self._create_navigation_menu()
        self._create_floating_power_button()

        logging.info("Aplicación iniciada correctamente.")

    def _init_ui_structure(self):
        sidebar_cfg = self.layout_cfg.get("modules", {}).get("sidebar", {})
        layout_colors = self.colors_cfg.get("global", {}).get("layout", {})

        # Sidebar
        self.nav_frame = ctk.CTkFrame(self, width=sidebar_cfg.get("width", 220), corner_radius=0, fg_color=layout_colors.get("sidebar_background", "#393E46"))
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        # Contenedor Menú
        self.menu_container = ctk.CTkFrame(self.nav_frame, fg_color="transparent", height=600)

        mm_layout = self.layout_cfg.get("global", {}).get("main_menu_layout", {})
        placement = mm_layout.get("placement", "pack")

        if placement == "place":
            offset_y = mm_layout.get("offset_y", 100)
            self.menu_container.place(x=0, y=offset_y, relwidth=1.0)
        else:
            self.menu_container.pack(side="top", fill="both", expand=True, pady=20)

        # Footer
        ctk.CTkLabel(self.nav_frame, text="KOOL TPV V1.0", text_color=layout_colors.get("text_primary", "#FFFFFF")).pack(side="bottom", pady=10)

        # Main Content
        self.main_frame = ctk.CTkFrame(self, fg_color=self.cget("fg_color"))
        self.main_frame.pack(side="right", fill="both", expand=True)

    def _create_navigation_menu(self):
        main_menu_items = self.buttons_cfg.get("main_menu", [])
        styles_map = self.layout_cfg.get("global", {}).get("main_menu_styles", {})
        colors_map = self.colors_cfg.get("main_menu", {})

        # LEER FUENTES DEL CONFIG
        fonts_menu_map = self.fonts_cfg.get("main_menu", {})

        for item in main_menu_items:
            style_key = item.get("style_key")
            style_data = styles_map.get(style_key, {})
            color_data = colors_map.get(style_key, {})

            # 1. LEER FUENTE ESPECÍFICA (NO INVENTADA)
            font_data = fonts_menu_map.get(style_key, {})
            if font_data:
                # Si está en el config, se usa
                font_tuple = (
                    font_data.get("family", "Courier New"),
                    int(font_data.get("size", 20)),
                    font_data.get("weight", "bold")
                )
            else:
                # Si NO está, fallback
                font_tuple = ("Courier New", 20, "bold")

            cmd_func = getattr(self, item.get("command", ""), None)

            btn = ButtonFactory.create_button(
                parent=self.menu_container,
                text=item.get("text", "ITEM"),
                command=cmd_func,
                width=style_data.get("width", 220),
                height=style_data.get("height", 56),
                color=color_data.get("bg"),
                hover_color=color_data.get("hover"),
                text_color=color_data.get("text"),
                font=font_tuple,  # APLICAR FUENTE
                corner_radius=style_data.get("corner_radius", 10),
                border_color=color_data.get("border"),
                border_width=2 if color_data.get("border") else 0
            )
            btn.pack(pady=10, padx=10)
            self.nav_buttons[item.get("text")] = btn

    def _create_floating_power_button(self):
        # 1. Carga Configuración del Botón (Tamaño e Imagen)
        global_btns = self.buttons_cfg.get("global_buttons", [])
        power_cfg = next((b for b in global_btns if b.get("id") == "power"), {})

        style_key = power_cfg.get("style_key", "power_btn")
        colors = self.colors_cfg.get("global_buttons", {}).get(style_key, {})

        # TAMAÑO: Lo lee de buttons_config.json
        btn_width = power_cfg.get("width", 100)
        btn_height = power_cfg.get("height", 100)

        # POSICIÓN: La lee de layout_config.json -> global -> power
        power_layout = self.layout_cfg.get("global", {}).get("power", {})
        pos_x = power_layout.get("offset_x", 12) 
        pos_y = power_layout.get("offset_y", 12)

        # Imagen
        img_path = power_cfg.get("image")
        ctk_image = None
        if img_path:
            try:
                full_path = Path(__file__).resolve().parents[0] / "kool_tpv" / img_path
                pil_img = Image.open(full_path)
                img_size = (int(btn_width) - 20, int(btn_height) - 20)
                ctk_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=img_size)
            except Exception:
                pass

        # Frame Flotante
        self.power_floating = ctk.CTkFrame(self, fg_color="transparent", width=btn_width, height=btn_height)

        # AQUÍ APLICAMOS LA POSICIÓN DEL CONFIG
        self.power_floating.place(x=pos_x, y=pos_y)

        self.btn_power = ButtonFactory.create_button(
            parent=self.power_floating,
            text="",
            command=self._dispatch_power,
            width=btn_width,
            height=btn_height,
            color=colors.get("bg", "red"),
            hover_color=colors.get("hover", "darkred"),
            image=ctk_image,
            corner_radius=15
        )
        self.btn_power.pack()
        self.power_floating.lift()
        self.power_floating_btn = self.btn_power

    # --- Power Handler System ---
    def register_power_handler(self, handler: Callable, owner: Any = None):
        self._power_handler = handler

    def unregister_power_handler(self, handler: Callable = None, owner: Any = None):
        self._power_handler = None

    def _dispatch_power(self):
        if self._power_handler and self._power_handler():
            return 
        self.close_app() 

    # --- Navegación ---
    def load_tpv(self):
        self._clear_main()
        from kool_tpv.modulos.tpv.tpv_view_new import TpvView
        # En TPV sí mostramos barra lateral (según tu diseño original)
        self.nav_frame.pack(side="left", fill="y")
        self.main_frame.pack(side="right", fill="both", expand=True)

        self.tpv_view = TpvView(self.main_frame, db=self.db)
        self.tpv_view.pack(fill="both", expand=True)
        self.current_view = "tpv"

    def open_almacen(self):
        # Ocultar menú principal
        self.nav_frame.pack_forget() 
        self.main_frame.pack_forget()

        from kool_tpv.modulos.almacen.almacen_view import AlmacenView
        # SOLO crear la vista (ella misma se empaqueta en __init__)
        self.almacen_view = AlmacenView(self, db=self.db, keyboard_manager=self.keyboard_mgr)

    def open_clientes(self):
        self.nav_frame.pack_forget()
        self.main_frame.pack_forget()

        from kool_tpv.modulos.clientes.clientes_view import ClientesView
        self.clientes_view = ClientesView(self, db=self.db, keyboard_manager=self.keyboard_mgr)

    def open_informes(self):
        self.nav_frame.pack_forget()
        self.main_frame.pack_forget()

        from kool_tpv.modulos.informes.informes_view import InformesView
        self.informes_view = InformesView(self, db=self.db, keyboard_manager=self.keyboard_mgr)

    def open_config(self):
        self.nav_frame.pack_forget()
        self.main_frame.pack_forget()

        from kool_tpv.modulos.configuracion.config_view import ConfigView
        self.config_view = ConfigView(self, db=self.db, keyboard_manager=self.keyboard_mgr)

    def close_app(self):
        # 1. Si estamos en TPV, salir al menú principal
        if self.current_view == "tpv":
            self.current_view = None
            self._clear_main()
            if not self.nav_frame.winfo_ismapped():
                self.nav_frame.pack(side="left", fill="y")
            return

        # 2. Si hay otros módulos abiertos, preguntarles si gestionan el Power
        modules = ['almacen_view', 'clientes_view', 'informes_view', 'config_view']

        for mod_name in modules:
            if hasattr(self, mod_name):
                view = getattr(self, mod_name)

                # Preguntar al módulo si tiene método _on_power
                if view and hasattr(view, '_on_power'):
                    try:
                        # Llamar a _on_power() del módulo
                        handled = view._on_power()
                        if handled:
                            # El módulo gestionó el Power (cerró sub-vista)
                            return  # NO destruir el módulo
                    except Exception:
                        logging.exception(f'Error llamando a _on_power en {mod_name}')

                # Si _on_power devolvió False (o no existe), destruir el módulo
                if view:
                    # FIX: Ocultar los frames internos del módulo (sidebar y main_frame)
                    try:
                        if hasattr(view, 'sidebar'):
                            view.sidebar.pack_forget()
                    except Exception:
                        pass

                    try:
                        if hasattr(view, 'main_frame'):
                            view.main_frame.pack_forget()
                    except Exception:
                        pass

                    # Destruir el módulo completo
                    if hasattr(view, 'winfo_exists'):
                        try:
                            if view.winfo_exists():
                                view.destroy()
                        except Exception:
                            pass

                    # Limpiar referencia
                    delattr(self, mod_name)

                # Restaurar Menú Principal
                self.nav_frame.pack(side="left", fill="y")
                self.main_frame.pack(side="right", fill="both", expand=True)
                self._clear_main()
                return

        # 3. Si estamos en el menú principal, CERRAR APP DE VERDAD
        if self.db: 
            try:
                self.db.close_connection()
            except Exception:
                pass
        self.destroy()
        sys.exit(0)

    def _clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def reserve_power_space(self, container, margin=12):
        # Leer tamaño reservado desde layout_config.json -> global -> power
        power_cfg = self.layout_cfg.get("global", {}).get("power", {}) if getattr(self, 'layout_cfg', None) else {}

        def _to_int(v):
            try:
                if v is None:
                    return None
                return int(v)
            except Exception:
                return None

        reserved_w = _to_int(power_cfg.get("reserved_width"))
        reserved_h = _to_int(power_cfg.get("reserved_height"))

        # Si alguno es None o no válido, intentar usar el tamaño del botón power
        if (reserved_w is None or reserved_w <= 0) or (reserved_h is None or reserved_h <= 0):
            try:
                btn = getattr(self, 'btn_power', None) or getattr(self, 'power_floating_btn', None)
                if btn is not None:
                    try:
                        btn.update_idletasks()
                    except Exception:
                        pass
                    try:
                        bw = btn.winfo_reqwidth() or btn.winfo_width()
                        bh = btn.winfo_reqheight() or btn.winfo_height()
                        if reserved_w is None or reserved_w <= 0:
                            reserved_w = int(bw) if bw and bw > 0 else reserved_w
                        if reserved_h is None or reserved_h <= 0:
                            reserved_h = int(bh) if bh and bh > 0 else reserved_h
                    except Exception:
                        pass
            except Exception:
                pass

        # Fallback por defecto si sigue sin resolverse
        if reserved_w is None or reserved_w <= 0:
            reserved_w = 100
        if reserved_h is None or reserved_h <= 0:
            reserved_h = 100

        spacer = ctk.CTkFrame(container, width=reserved_w, height=reserved_h, fg_color="transparent")
        spacer.pack_propagate(False)
        return spacer

if __name__ == "__main__":
    app = App()
    app.mainloop()