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

        # --- GEOMETRÍA: maximizado para adaptarse a cualquier resolución ---
        self.minsize(win_cfg.get("min_width", 1024), win_cfg.get("min_height", 768))
        self.resizable(True, True)

        def maximize_window():
            try:
                self.state('zoomed')  # Windows / Linux
            except Exception:
                try:
                    self.attributes('-zoomed', True)  # Algunos Linux
                except Exception:
                    self.geometry(f"{width}x{height}")  # Fallback
            self.update_idletasks()

        self.after(100, maximize_window)
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
        # Exponer alias `keyboard_manager` para compatibilidad con código que usa ese atributo
        self.keyboard_manager = self.keyboard_mgr
        self.nav_buttons = {}
        self.current_view = None
        self._power_stack = []  # Stack de handlers (LIFO - último registrado tiene prioridad) 

        # 5. UI - Estructura Principal
        self._init_ui_structure()
        self._create_navigation_menu()
        self._create_floating_power_button()

        # Esc → botón Power (exclusivo y global)
        self.bind('<Escape>', lambda e: self._dispatch_power())

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

        # (test button removed)

    def _create_navigation_menu(self):
        main_menu_items = self.buttons_cfg.get("main_menu", [])
        styles_map = self.layout_cfg.get("global", {}).get("main_menu_styles", {})
        colors_map = self.colors_cfg.get("main_menu", {})

        # LEER FUENTES DEL CONFIG (omitir tamaños desde font_config para que
        # button_styles.json controle el tamaño de fuente)
        for item in main_menu_items:
            style_key = item.get("style_key")
            style_data = styles_map.get(style_key, {})
            color_data = colors_map.get(style_key, {})
            # Nota: el tamaño de fuente provendrá exclusivamente de
            # `button_styles.json` a través de `style_key`.

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
                style_key=style_key,
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

        # TAMAÑO/POSICIÓN/ESTILO: Leer todo desde layout_config.json -> global -> power_layout
        power_layout = self.layout_cfg.get("global", {}).get("power_layout", {})
        # Preferir width/height definidos en layout; si no existen, fallback a buttons_cfg
        btn_width = int(power_layout.get("width") or power_cfg.get("width") or 100)
        btn_height = int(power_layout.get("height") or power_cfg.get("height") or 100)

        pos_x = int(power_layout.get("offset_x") or 0)
        pos_y = int(power_layout.get("offset_y") or 0)

        # Cargar imágenes normal/hover (preferir carpeta kool_tpv-assets en la raíz)
        self.power_img_normal = None
        self.power_img_hover = None
        try:
            repo_root = Path(__file__).resolve().parents[0]
            # Preferir carpeta kool_tpv-assets en la raíz del repo
            normal_path = repo_root / "kool_tpv-assets" / "power.png"
            hover_path = repo_root / "kool_tpv-assets" / "power_hover.png"
            # Fallback a los assets dentro de kool_tpv
            if not normal_path.exists():
                normal_path = repo_root / "kool_tpv" / "assets" / "power.png"
            if not hover_path.exists():
                hover_path = repo_root / "kool_tpv" / "assets" / "power_hover.png"

            if normal_path.exists():
                pil_img = Image.open(normal_path)
                img_size = (int(btn_width), int(btn_height))
                self.power_img_normal = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=img_size)

            if hover_path.exists():
                pil_img_h = Image.open(hover_path)
                img_size_h = (int(btn_width), int(btn_height))
                self.power_img_hover = ctk.CTkImage(light_image=pil_img_h, dark_image=pil_img_h, size=img_size_h)
        except Exception:
            # Si falla, dejar imágenes en None (se mostrará texto/blank)
            self.power_img_normal = None
            self.power_img_hover = None

        # Frame Flotante (sin fondo)
        self.power_floating = ctk.CTkFrame(self, fg_color="transparent", width=btn_width, height=btn_height)
        self.power_floating.place(x=pos_x, y=pos_y)

        # Resolver visual attrs desde layout (interpretar 'transparent' como "use sidebar background")
        layout_colors = self.colors_cfg.get("global", {}).get("layout", {})
        sidebar_bg = layout_colors.get("sidebar_background", self.cget("fg_color"))

        raw_bg = power_layout.get("bg_color")
        raw_hover = power_layout.get("hover_color")

        bg = sidebar_bg if (raw_bg == "transparent" or raw_bg is None) else raw_bg
        hover = sidebar_bg if (raw_hover == "transparent" or raw_hover is None) else raw_hover

        self.btn_power = ButtonFactory.create_button(
            parent=self.power_floating,
            text="",
            command=self._on_power_click,
            width=btn_width,
            height=btn_height,
            color=bg,
            hover_color=hover,
            border_width=power_layout.get("border_width"),
            corner_radius=power_layout.get("corner_radius"),
            image=self.power_img_normal,
        )

        # Hover: intercambiar imagenes (si han cargado)
        try:
            if self.power_img_hover is not None and self.power_img_normal is not None:
                self.btn_power.bind("<Enter>", lambda e: self.btn_power.configure(image=self.power_img_hover))
                self.btn_power.bind("<Leave>", lambda e: self.btn_power.configure(image=self.power_img_normal))
        except Exception:
            pass

        # Posicionar el botón con place() usando valores del layout
        try:
            self.btn_power.place(x=pos_x, y=pos_y, width=btn_width, height=btn_height)
        except Exception:
            # Fallback si place falla, dejar pack como último recurso
            self.btn_power.pack()

        self.power_floating.lift()
        self.power_floating_btn = self.btn_power

    # --- Power Handler System ---
    def register_power_handler(self, handler: Callable, owner: Any = None):
        """Registrar power handler con prioridad (último = mayor prioridad).
        
        Args:
            handler: Función a ejecutar cuando se presiona Power X
            owner: Widget/objeto dueño del handler (para identificación)
        """
        # Evitar duplicados del mismo owner
        if owner is not None:
            self._power_stack = [h for h in self._power_stack if h.get('owner') != owner]
        
        # Añadir al stack (último = mayor prioridad)
        owner_name = owner.__class__.__name__ if owner and hasattr(owner, '__class__') else 'unknown'
        self._power_stack.append({
            'handler': handler,
            'owner': owner,
            'name': owner_name
        })
        
        logging.info(f"Power handler registrado: {owner_name}")
        logging.info(f"Stack actual: {[h['name'] for h in self._power_stack]}")

    def unregister_power_handler(self, handler: Callable = None, owner: Any = None):
        """Desregistrar power handler específico del owner.
        
        Args:
            handler: (Ignorado, se mantiene por compatibilidad)
            owner: Widget/objeto dueño del handler a eliminar
        """
        if owner is not None:
            before_count = len(self._power_stack)
            self._power_stack = [h for h in self._power_stack if h.get('owner') != owner]
            after_count = len(self._power_stack)
            
            if before_count > after_count:
                owner_name = owner.__class__.__name__ if hasattr(owner, '__class__') else str(owner)
                logging.info(f"Power handler desregistrado: {owner_name}")
                logging.info(f"Stack actual: {[h['name'] for h in self._power_stack]}")

    def _dispatch_power(self):
        """Ejecutar handler con mayor prioridad (último del stack).
        
        Itera desde el final del stack (mayor prioridad) hacia el inicio.
        Si un handler retorna True, se considera procesado.
        Si ningún handler procesa o el stack está vacío, cierra la app.
        """
        # Copiar stack para iterar (evita problemas si handler modifica stack)
        handlers_to_try = list(self._power_stack)
        
        # Iterar desde el final (mayor prioridad)
        while handlers_to_try:
            entry = handlers_to_try.pop()
            handler = entry.get('handler')
            handler_name = entry.get('name', 'unknown')
            
            try:
                # Ejecutar handler - si retorna True, fue procesado
                result = handler()
                if result is True:
                    logging.info(f"Power procesado por: {handler_name}")
                    return
                else:
                    logging.debug(f"Power NO procesado por {handler_name} (retornó {result})")
            except Exception:
                logging.exception(f"Error ejecutando power handler: {handler_name}")
                # Continuar con siguiente handler
                continue
        
        # No hay handlers o ninguno procesó - cerrar app
        logging.info("Power no procesado por ningún handler - cerrando app")
        self.close_app() 

    def _on_power_click(self):
        """Handler directo vinculado al botón Power (wrapper)."""
        try:
            return self._dispatch_power()
        except Exception:
            logging.exception('Error en _on_power_click')
            return None

    # --- Navegación ---
    def load_tpv(self):
        self._clear_main()
        from kool_tpv.modulos.tpv.tpv_view_new import TpvView

        # Entrar en TPV: ocultar únicamente los botones del menú principal
        # (menu_container) para mantener la sidebar con el botón Power.
        try:
            # menu_container puede haber sido colocado con place()
            # usar place_forget() para ocultarlo correctamente
            self.menu_container.place_forget()
        except Exception:
            try:
                self.menu_container.pack_forget()
            except Exception:
                pass

        # Crear la vista TPV dentro de main_frame (no tocar nav_frame ni main_frame)
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
            # Restaurar menu_container de forma simétrica según layout_config
            try:
                mm_layout = self.layout_cfg.get("global", {}).get("main_menu_layout", {})
                placement = mm_layout.get("placement", "pack")
                if placement == "place":
                    offset_x = mm_layout.get("offset_x", 0)
                    offset_y = mm_layout.get("offset_y", 100)
                    relwidth = mm_layout.get("relwidth", 1.0)
                    try:
                        self.menu_container.place(x=offset_x, y=offset_y, relwidth=relwidth)
                    except Exception:
                        pass
                else:
                    side = mm_layout.get("side", "top")
                    fill = mm_layout.get("fill", "both")
                    pady = mm_layout.get("pady", 20)
                    try:
                        self.menu_container.pack(side=side, fill=fill, expand=True, pady=pady)
                    except Exception:
                        pass
            except Exception:
                pass
            if not self.nav_frame.winfo_ismapped():
                self.nav_frame.pack(side="left", fill="y")
            return

        # 2. Si hay otros módulos abiertos Y VISIBLES, preguntarles si gestionan el Power
        modules = ['almacen_view', 'clientes_view', 'informes_view', 'config_view']

        for mod_name in modules:
            if hasattr(self, mod_name):
                view = getattr(self, mod_name)
                
                # Verificar si el módulo está visible (sidebar mapeado)
                is_visible = False
                try:
                    if view and hasattr(view, 'sidebar') and view.sidebar.winfo_ismapped():
                        is_visible = True
                except Exception:
                    pass
                
                # Solo procesar módulos visibles
                if not is_visible:
                    continue

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

                # Si _on_power devolvió False (o no existe), ocultar el módulo (igual que TPV)
                if view:
                    # Ocultar frames del módulo (NO destruir - handler permanece en stack)
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