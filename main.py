import customtkinter as ctk
import sys
import logging
import os
import json
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from typing import List, Dict
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel
from PIL import Image
from kool_tpv.utils.keyboard_manager import KeyboardManager


def load_layout_config():
    base = Path(__file__).resolve().parents[0]
    config_path = base / "kool_tpv" / "config" / "layout_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_colors_config():
    base = Path(__file__).resolve().parents[0]
    config_path = base / "kool_tpv" / "config" / "colors_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_font_config():
    base = Path(__file__).resolve().parents[0]
    config_path = base / "kool_tpv" / "config" / "font_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Navigation padding and hover values are read from config (no hardcoded globals)

# Asegurar carpeta de logs
os.makedirs("logs", exist_ok=True)

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/application.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Apariencia
        try:
            ctk.set_appearance_mode("dark")
        except Exception:
            pass

        # Tipografías configurables (leídas desde kool_tpv/config/font_config.json)
        font_config = load_font_config()
        app_fonts = font_config.get("app", {})

        def build_font(cfg, default=("Courier New", 18)):
            family = cfg.get("family", default[0])
            size = cfg.get("size", default[1])
            weight = cfg.get("weight", "normal")
            try:
                size = int(size)
            except Exception:
                size = default[1]
            if weight and weight != "normal":
                return (family, size, weight)
            return (family, size)

        self.base_font = build_font(app_fonts.get("base_font", {}))
        self.button_font = build_font(app_fonts.get("nav_button", {}))
        self.tpv_font = build_font(app_fonts.get("tpv_large", {}))

        # Configuración de la ventana principal
        self.title("Kool TPV")
        # Tamaño configurable desde layout_config.json
        layout_config = load_layout_config()
        window_cfg = layout_config.get("global", {}).get("window", {})
        win_width = window_cfg.get("width", 1600)
        win_height = window_cfg.get("height", 960)
        min_width = window_cfg.get("min_width", win_width)
        min_height = window_cfg.get("min_height", win_height)
        self.geometry(f"{win_width}x{win_height}")
        # Forzar aplicación de la geometría antes de mostrar (evita tamaño inicial diminuto)
        try:
            self.update_idletasks()
        except Exception:
            pass
        # Asegurar que no pueda reducirse por debajo de este tamaño (leer minsize desde config)
        self.minsize(min_width, min_height)
        # No redimensionable
        self.resizable(False, False)
        # Fondo oscuro: asegurar tanto el CTk como el Tk nativo (colores desde config)
        colors_cfg = load_colors_config()
        layout_colors = colors_cfg.get("global", {}).get("layout", {})
        app_bg = layout_colors.get("app_background", "#222831")
        try:
            self.configure(fg_color=app_bg)
            # Forzar también el fondo a nivel nativo Tkinter para evitar flashes
            try:
                self.config(background=app_bg)
            except Exception:
                logging.exception('Error aplicando background en config nativa')
        except Exception:
            try:
                self.configure(bg=app_bg)
            except Exception:
                logging.exception('Error aplicando background en CTk')

        # Inicializar y conectar base de datos
        # Ruta al archivo kool_bd.db dentro del paquete `kool_tpv/base_datos`
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "kool_tpv", "base_datos", "kool_bd.db")
        # Ensure DB schema exists before connecting
        from kool_tpv.base_datos.db_init import initialize_database
        initialize_database(db_path)

        self.db = Database(db_path)
        # Fail fast: if the DB can't connect, raise the exception so it is visible
        self.db.connect()
        logging.info("Conexión a la base de datos establecida con éxito.")

        # Inicializar UI
        # Contenedor para referencias a botones de navegación
        self.nav_buttons = {}
        self.current_view = None
        self.tpv_view = None
        # Power handler (dispatcher) - puede ser registrado por vistas/overlays
        self._power_handler = None
        self._power_handler_owner = None

        # Inicializar KeyboardManager global para la aplicación
        try:
            self.keyboard_mgr = KeyboardManager(self)
            # Mantener compatibilidad con código que busca `keyboard_manager` en el root
            try:
                self.keyboard_manager = self.keyboard_mgr
            except Exception:
                pass
            logging.info('KeyboardManager inicializado en App')
        except Exception:
            logging.exception('Error inicializando KeyboardManager en App')

        self.create_navigation()

        # Create a floating power button so it remains visible above overlays.
        try:
            from kool_tpv.utils.global_buttons import create_global_close_button
            try:
                self.update_idletasks()
            except Exception:
                pass

            # Hide the nav_frame packed power button if present (we'll recreate floating)
            try:
                if getattr(self, 'power_button', None) is not None:
                    try:
                        self.power_button.pack_forget()
                    except Exception:
                        try:
                            self.power_button.place_forget()
                        except Exception:
                            pass
            except Exception:
                pass

            # Determine size from existing proxy or use sensible defaults
            try:
                btn_w = getattr(self.power_button, 'winfo_reqwidth')()
                btn_h = getattr(self.power_button, 'winfo_reqheight')()
            except Exception:
                try:
                    # fallback reading buttons_config
                    base = Path(__file__).resolve().parents[0]
                    cfg_file = base / "kool_tpv" / "config" / "buttons_config.json"
                    if cfg_file.exists():
                        with cfg_file.open("r", encoding="utf-8") as fh:
                            bcfg = json.load(fh)
                        btn_w = btn_h = None
                        for entry in bcfg.get("global_buttons", []):
                            if entry.get("id") == "power":
                                btn_w = entry.get("width")
                                btn_h = entry.get("height")
                                break
                        if not btn_w: btn_w = 48
                        if not btn_h: btn_h = 48
                    else:
                        btn_w, btn_h = 48, 48
                except Exception:
                    btn_w, btn_h = 48, 48

            try:
                btn_w = int(btn_w)
                btn_h = int(btn_h)
            except Exception:
                btn_w, btn_h = 48, 48

            # Create floating container and place it near top-left (over nav area)
            try:
                self.power_floating = ctk.CTkFrame(self, width=btn_w, height=btn_h, fg_color='transparent')
                try:
                    self.power_floating.pack_propagate(False)
                except Exception:
                    pass
                # Determine placement anchor/offset from layout config (fall back to margin)
                try:
                    layout_cfg = load_layout_config()
                    power_cfg = layout_cfg.get("global", {}).get("power", {})
                    anchor = (power_cfg.get("anchor") or "top-left").lower()
                    offset_x = power_cfg.get("offset_x")
                    offset_y = power_cfg.get("offset_y")
                    if offset_x is None:
                        offset_x = power_cfg.get("margin", 12)
                    if offset_y is None:
                        offset_y = power_cfg.get("margin", 12)
                except Exception:
                    anchor = "top-left"
                    offset_x = 12
                    offset_y = 12

                try:
                    # Try to compute coordinates depending on anchor
                    w = self.winfo_width() or None
                    h = self.winfo_height() or None
                    if anchor in ("top-right", "tr"):
                        try:
                            x = (w - int(btn_w) - int(offset_x)) if w else int(offset_x)
                        except Exception:
                            x = int(offset_x)
                        y = int(offset_y)
                        self.power_floating.place(x=x, y=y)
                    elif anchor in ("bottom-left", "bl"):
                        try:
                            y = (h - int(btn_h) - int(offset_y)) if h else int(offset_y)
                        except Exception:
                            y = int(offset_y)
                        x = int(offset_x)
                        self.power_floating.place(x=x, y=y)
                    elif anchor in ("bottom-right", "br"):
                        try:
                            x = (w - int(btn_w) - int(offset_x)) if w else int(offset_x)
                            y = (h - int(btn_h) - int(offset_y)) if h else int(offset_y)
                        except Exception:
                            x = int(offset_x)
                            y = int(offset_y)
                        self.power_floating.place(x=x, y=y)
                    else:
                        # default: top-left
                        try:
                            self.power_floating.place(x=int(offset_x), y=int(offset_y))
                        except Exception:
                            self.power_floating.place(x=12, y=12)
                except Exception:
                    try:
                        self.power_floating.place(x=12, y=12)
                    except Exception:
                        try:
                            self.power_floating.place(x=0, y=0)
                        except Exception:
                            pass

                # Insert a spacer at the top of the nav_frame so menu buttons keep their previous visual offset
                try:
                    if getattr(self, 'nav_frame', None) is not None:
                        try:
                            # determine spacer height from floating button height
                            spacer_h = btn_h + 8
                        except Exception:
                            spacer_h = btn_h
                        try:
                            spacer = ctk.CTkFrame(self.nav_frame, width=1, height=spacer_h, fg_color='transparent')
                            try:
                                spacer.pack_propagate(False)
                            except Exception:
                                pass
                            # place before first child to keep it at the top
                            children = self.nav_frame.winfo_children()
                            if children:
                                try:
                                    spacer.pack(side='top', before=children[0])
                                except Exception:
                                    spacer.pack(side='top')
                            else:
                                spacer.pack(side='top')
                        except Exception:
                            pass
                except Exception:
                    pass

                # create the actual button inside floating container and delegate to dispatcher
                try:
                    self.power_floating_btn = create_global_close_button(self.power_floating, command=self._dispatch_power)
                    if getattr(self, 'power_floating_btn', None) is not None:
                        try:
                            self.power_floating_btn.pack(expand=True)
                        except Exception:
                            pass
                except Exception:
                    logging.exception('Error creando boton power flotante')

                try:
                    self.power_floating.lift()
                except Exception:
                    pass
            except Exception:
                logging.exception('Error creando power_floating')
        except Exception:
            logging.exception('Error importando create_global_close_button para power_floating')

        # Log de inicialización exitosa
        logging.info("Aplicación iniciada correctamente.")

    def create_navigation(self):
        # Frame lateral (barra de navegación)
        # Barra lateral más ancha para botones táctiles
        layout_config = load_layout_config()
        # Navigation padding from layout config
        nav_layout = layout_config.get("global", {}).get("navigation", {})
        nav_padx = nav_layout.get("button_padx", 20)
        nav_pady = nav_layout.get("button_pady", 14)
        # Main menu packing layout (global override)
        main_menu_layout = layout_config.get("global", {}).get("main_menu_layout", {})
        pack_side = main_menu_layout.get("side", "top")
        pack_padx = main_menu_layout.get("padx", nav_padx)
        pack_pady = main_menu_layout.get("pady", nav_pady)
        pack_fill = main_menu_layout.get("fill", "x")
        pack_button_width = main_menu_layout.get("button_width")
        # Expose to instance for other methods (restore packing etc.)
        self.nav_padx = nav_padx
        self.nav_pady = nav_pady
        sidebar_width = (
            layout_config
            .get("modules", {})
            .get("sidebar", {})
            .get("width", 220)
        )
        # Load sidebar colors from colors_config (fail fast if config invalid)
        colors_cfg = load_colors_config()
        layout_colors = colors_cfg.get("global", {}).get("layout", {})
        sidebar_bg = layout_colors.get("sidebar_background", "#393E46")
        text_primary = layout_colors.get("text_primary", "#FFFFFF")

        self.nav_frame = ctk.CTkFrame(self, width=sidebar_width, corner_radius=0, fg_color=sidebar_bg)
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        # Create an inner container for main menu buttons so the whole group
        # can be positioned (packed or placed) according to layout config.
        try:
            menu_container = ctk.CTkFrame(self.nav_frame, fg_color='transparent')
            menu_container.pack_propagate(False)

            # Read placement config with safe defaults
            main_menu_layout = layout_config.get("global", {}).get("main_menu_layout", {})
            placement = (main_menu_layout.get("placement") or "pack").lower()
            try:
                offset_x = int(main_menu_layout.get("offset_x") or 0)
            except Exception:
                offset_x = 0
            try:
                offset_y = int(main_menu_layout.get("offset_y") or 0)
            except Exception:
                offset_y = 0
            anchor = main_menu_layout.get("anchor") or "nw"

            if placement == "place":
                # Interpret offsets as window-relative coordinates and convert
                # to nav_frame-local coordinates so the placement behaves as
                # absolute within the application window (option B).
                try:
                    self.update_idletasks()
                except Exception:
                    pass
                try:
                    nav_x = int(self.nav_frame.winfo_x())
                    nav_y = int(self.nav_frame.winfo_y())
                except Exception:
                    nav_x = 0
                    nav_y = 0
                rel_x = offset_x - nav_x
                rel_y = offset_y - nav_y
                try:
                    # Ensure the menu_container has an explicit size when placed,
                    # otherwise it may collapse to (1x1) and hide children.
                    try:
                        cm_cfg = main_menu_layout or {}
                        container_h = cm_cfg.get('container_height')
                        container_w = cm_cfg.get('container_width')
                    except Exception:
                        container_h = None
                        container_w = None

                    # Fallback to nav_frame dimensions if not provided
                    try:
                        if not container_h:
                            container_h = max(1, self.nav_frame.winfo_height() - int(rel_y))
                    except Exception:
                        container_h = None
                    try:
                        if not container_w:
                            container_w = max(1, self.nav_frame.winfo_width())
                    except Exception:
                        container_w = None

                    try:
                        if container_w is not None or container_h is not None:
                            menu_container.configure(width=(container_w or menu_container.winfo_width()), height=(container_h or menu_container.winfo_height()))
                            try:
                                menu_container.pack_propagate(False)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    menu_container.place(x=rel_x, y=rel_y, anchor=anchor)
                except Exception:
                    try:
                        menu_container.place(x=rel_x, y=rel_y)
                    except Exception:
                        menu_container.pack(side="top")

                # Debug: placement info
                try:
                    logging.info(
                        "MENU_CONTAINER placement=place (window->nav) "
                        f"anchor={anchor} offset_x={offset_x} offset_y={offset_y} rel_x={rel_x} rel_y={rel_y}"
                    )
                    logging.info(f"nav_frame pos: x={nav_x} y={nav_y} size: w={self.nav_frame.winfo_width()} h={self.nav_frame.winfo_height()}")
                    logging.info(f"menu_container pos: x={menu_container.winfo_x()} y={menu_container.winfo_y()} w={menu_container.winfo_width()} h={menu_container.winfo_height()}")
                except Exception:
                    logging.exception('Error logging menu_container geometry')
            else:
                # default: pack at top of nav_frame
                try:
                    # Allow the menu container to expand vertically so all
                    # buttons are visible when packed.
                    menu_container.pack(side="top", fill="both", expand=True)
                except Exception:
                    try:
                        menu_container.pack(fill="both", expand=True)
                    except Exception:
                        menu_container.pack()

                # Debug: pack placement info
                try:
                    self.update_idletasks()
                    logging.info(
                        "MENU_CONTAINER placement=pack "
                        f"side={main_menu_layout.get('side')} padx={main_menu_layout.get('padx')} pady={main_menu_layout.get('pady')}"
                    )
                    logging.info(f"nav_frame size: w={self.nav_frame.winfo_width()} h={self.nav_frame.winfo_height()}")
                    logging.info(f"menu_container pos(pack): x={menu_container.winfo_x()} y={menu_container.winfo_y()} w={menu_container.winfo_width()} h={menu_container.winfo_height()}")
                except Exception:
                    logging.exception('Error logging menu_container pack geometry')
        except Exception:
            logging.exception('Error creando menu_container dentro de nav_frame')

        # Importar función global para el botón power/close
        try:
            from kool_tpv.utils.global_buttons import create_global_close_button
            # Mantener el comportamiento histórico: el botón global llama a
            # `close_app` por defecto. El dispatcher aún está disponible
            # mediante `register_power_handler` si se desea activar.
            self.power_button = create_global_close_button(self.nav_frame, command=self.close_app)
            if self.power_button is not None:
                try:
                    self.power_button.pack(pady=(12, 20))
                except Exception:
                    pass
        except Exception:
            logging.exception("Error creando botón global power desde utils.global_buttons")

    
        # Cargar configuración de botones del menú principal desde JSON
        base = Path(__file__).resolve().parents[0]
        cfg_file = base / "kool_tpv" / "config" / "buttons_config.json"
        main_menu: List[Dict] = []
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            main_menu = data.get("main_menu") or []

            # Import ButtonFactory lazily to avoid circular imports on startup
            try:
                from kool_tpv.modulos.tpv.tpv_view import ButtonFactory
            except Exception:
                ButtonFactory = None

            for item in main_menu:
                text = item.get("text") or item.get("label") or ""
                color = item.get("color")
                hover = item.get("hover_color")
                cmd_name = (item.get("command") or "").strip()
                text_color = item.get("text_color")
                font_family = item.get("font_family")
                font_size = item.get("font_size")
                font_weight = item.get("font_weight")
                font_fallback = item.get("font_fallback")
                width = item.get("width")
                height = item.get("height")
                corner_radius = item.get("corner_radius")
                border_color = item.get("border_color")
                border_width = item.get("border_width")

                # map known commands to methods
                if cmd_name.lower() in ("tpv", "load_tpv", "load_tpv()"):
                    cmd = self.load_tpv
                elif cmd_name.lower() in ("open_almacen", "almacen", "open_almacen()"):
                    cmd = self.open_almacen
                elif cmd_name.lower() in ("open_clientes", "clientes", "open_clientes()"):
                    cmd = self.open_clientes
                elif cmd_name.lower() in ("open_informes", "informes", "open_informes()"):
                    cmd = self.open_informes
                
                
                elif cmd_name.lower() in ("open_config", "config", "open_config()"):
                    cmd = self.open_config
                else:
                    # default: log action
                    cmd = (lambda name=cmd_name or text: logging.info(f"Nav action: {name}"))

                # Create button using factory when available, passing through JSON parameters
                try:
                    # Build font object using fallback list/weight if provided
                    font_obj = None
                    try:
                        font_obj = self._build_font(font_family=font_family, size=font_size, weight=font_weight, fallback=font_fallback)
                    except Exception:
                        font_obj = (font_family, font_size) if font_family and font_size else None

                    parent_for_button = menu_container if 'menu_container' in locals() else self.nav_frame

                    # If button style key provided in JSON, allow layout_config to
                    # override width/height/corner_radius for that style.
                    try:
                        style_key = item.get('style_key') if isinstance(item, dict) else None
                        mm_styles = layout_config.get('global', {}).get('main_menu_styles', {}) if isinstance(layout_config, dict) else {}
                        style_cfg = mm_styles.get(style_key, {}) if style_key else {}
                        if style_cfg:
                            if not width:
                                width = style_cfg.get('width')
                            if not height:
                                height = style_cfg.get('height')
                            if not corner_radius:
                                corner_radius = style_cfg.get('corner_radius')
                    except Exception:
                        pass
                    if ButtonFactory is not None:
                        btn = ButtonFactory.create_button(
                            parent=parent_for_button,
                            text=text,
                            color=color,
                            hover_color=hover,
                            command=cmd,
                            text_color=text_color,
                            font=font_obj,
                            width=width,
                            height=height,
                            corner_radius=corner_radius,
                            border_color=border_color,
                            border_width=border_width,
                        )
                    else:
                        btn = self.create_nav_button(
                            text=text,
                            color=color,
                            height=height,
                            command=cmd,
                            hover_color=hover,
                            text_color=text_color,
                            font=font_obj,
                            width=width,
                            corner_radius=corner_radius,
                            border_color=border_color,
                            border_width=border_width,
                            parent=parent_for_button,
                        )
                    # pack using layout config or fallback constants
                    pack_kwargs = dict(pady=pack_pady, padx=pack_padx, fill=pack_fill)
                    try:
                        btn.pack(side=pack_side, **pack_kwargs)
                    except Exception:
                        btn.pack(pady=self.nav_pady, padx=self.nav_padx, fill="x")
                    # Debug: log button geometry after packing
                    try:
                        self.update_idletasks()
                        bx, by = btn.winfo_x(), btn.winfo_y()
                        bw, bh = btn.winfo_width(), btn.winfo_height()
                        logging.info(f"Nav button created: '{text}' pos=({bx},{by}) size=({bw}x{bh})")
                        # report container children count
                        try:
                            children = parent_for_button.winfo_children()
                            logging.info(f"menu_container children count: {len(children)}")
                        except Exception:
                            pass
                    except Exception:
                        logging.exception('Error logging created nav button geometry')
                    try:
                        self.nav_buttons[text] = btn
                    except Exception:
                        pass
                except Exception:
                    logging.exception("Error creando botón del menú desde JSON")

        

        # Footer con versión
        footer = ctk.CTkLabel(self.nav_frame, text="KOOL TPV V1.0", text_color=text_primary, font=self.base_font)
        footer.pack(side="bottom", pady=10)

        # Frame principal para cargar contenido dinámico (usar color desde config)
        try:
            # app_bg may have been read earlier from colors_cfg
            app_bg = locals().get('app_bg') or globals().get('app_bg')
        except Exception:
            app_bg = None
        if app_bg is None:
            try:
                colors_cfg = load_colors_config()
                app_bg = colors_cfg.get("global", {}).get("layout", {}).get("app_background", "#222831")
            except Exception:
                app_bg = "#222831"

        self.main_frame = ctk.CTkFrame(self, fg_color=app_bg)
        self.main_frame.pack(side="right", fill="both", expand=True)

    def create_nav_button(
        self,
        text,
        color,
        height=56,
        command=None,
        hover_color=None,
        text_color=None,
        font=None,
        font_family=None,
        font_size=None,
        width=None,
        corner_radius=None,
        border_color=None,
        border_width=None,
        parent=None,
    ):
        """Crea un `CTkButton` para la navegación usando parámetros pasados (idealmente desde JSON).

        Todos los parámetros de estilo provienen del JSON y se aplican directamente.
        Esta función NO hace `pack()` — el llamador debe decidir el layout.
        """
        # If an explicit font object was provided, use it
        if font is not None:
            btn_font = font
        else:
            # Construir la tupla de font si se proporcionó
            if font_family and font_size:
                btn_font = (font_family, int(font_size))
            else:
                # Ensure default is a tuple (family, size)
                default_font = getattr(self, "button_font", ("Roboto-SemiBold", 24))
                if isinstance(default_font, (list, tuple)):
                    btn_font = (default_font[0], int(default_font[1]))
                else:
                    btn_font = default_font

        params = dict(
            master=(parent or self.nav_frame),
            text=(text or "").upper(),
            fg_color=color,
            command=command,
        )

        if hover_color is not None:
            params["hover_color"] = hover_color
        if text_color is not None:
            params["text_color"] = text_color
        if btn_font is not None:
            params["font"] = btn_font
        if height is not None:
            params["height"] = height
        if width is not None:
            params["width"] = width
        if corner_radius is not None:
            params["corner_radius"] = corner_radius
        if border_color is not None:
            params["border_color"] = border_color
        if border_width is not None:
            params["border_width"] = border_width

        btn = ctk.CTkButton(**params)

        # Guardar referencia para poder ocultar/mostrar desde otras vistas
        try:
            self.nav_buttons[text] = btn
        except Exception:
            pass
        return btn

    def _build_font(self, font_family=None, size=None, weight=None, fallback=None):
        """Return a tkfont.Font or a (family, size) tuple.

        - `fallback` can be a list of families (preferred order) or a single family string.
        - If no available family is found, returns a tuple using `font_family` or the app default.
        """
        try:
            # Normalize fallback to list
            candidates = []
            if fallback:
                if isinstance(fallback, str):
                    candidates = [fallback]
                elif isinstance(fallback, (list, tuple)):
                    candidates = list(fallback)
            # Add explicit font_family at end if provided
            if font_family:
                candidates.append(font_family)

            available = []
            try:
                available = list(tkfont.families())
            except Exception:
                # If families() fails (rare), fallback to defaults
                available = []

            chosen = None
            for fam in candidates:
                if fam and fam in available:
                    chosen = fam
                    break

            if not chosen:
                # Final fallback: use the first available common monospace
                for common in ("Courier New", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Consolas"):
                    if common in available:
                        chosen = common
                        break

            if not chosen:
                # give up and use app default family
                try:
                    chosen = getattr(self, "button_font", ("Roboto-SemiBold", 24))[0]
                except Exception:
                    chosen = "TkDefaultFont"

            if size is None:
                size = getattr(self, "button_font", (None, 24))[1]

            # Create a tkfont.Font object
            # Return a tuple accepted by CustomTkinter, e.g. (family, size) or (family, size, weight)
            if weight:
                return (chosen, int(size), weight)
            return (chosen, int(size))
        except Exception:
            # Return simple tuple as fallback
            if font_family and size:
                return (font_family, size)
            return getattr(self, "button_font", ("Roboto-SemiBold", 24))

    def _font_from_cfg(self, cfg, default=("Courier New", 12)):
        """Build a (family, size) or (family, size, weight) tuple from a small config dict."""
        try:
            if not cfg:
                return default
            family = cfg.get("family", default[0])
            size = cfg.get("size", default[1])
            try:
                size = int(size)
            except Exception:
                size = default[1]
            weight = cfg.get("weight", "normal")
            if weight and weight != "normal":
                return (family, size, weight)
            return (family, size)
        except Exception:
            return default

    def register_power_handler(self, handler, owner=None):
        """Registrar un handler para la acción global de power.

        `handler` debe ser callable y devolver True si gestionó la acción.
        `owner` es opcional y se usa para desregistrar por propietario.
        """
        try:
            if handler is None:
                return
            if not callable(handler):
                return
            self._power_handler = handler
            self._power_handler_owner = owner
            logging.info('Power handler registrado por %s', repr(owner))
        except Exception:
            logging.exception('Error registrando power handler')

    def unregister_power_handler(self, handler=None, owner=None):
        """Desregistrar el handler registrado. Si no se pasan argumentos, se limpia todo."""
        try:
            if handler is None and owner is None:
                self._power_handler = None
                self._power_handler_owner = None
                return
            if handler is not None and self._power_handler == handler:
                self._power_handler = None
                self._power_handler_owner = None
                return
            if owner is not None and getattr(self, '_power_handler_owner', None) == owner:
                self._power_handler = None
                self._power_handler_owner = None
                return
        except Exception:
            logging.exception('Error desregistrando power handler')

    def _dispatch_power(self):
        """Despachador que se ejecuta al pulsar el botón power global.

        Llama al handler registrado (si existe). Si el handler devuelve True
        se considera la acción atendida; en caso contrario se ejecuta el
        fallback por defecto (`close_app`).
        """
        try:
            handler = getattr(self, '_power_handler', None)
            if callable(handler):
                try:
                    handled = handler()
                    if handled:
                        return
                except Exception:
                    logging.exception('Error ejecutando power handler registrado')

            # Fallback: comportamiento por defecto de la app
            try:
                self.close_app()
            except Exception:
                logging.exception('Error en close_app desde _dispatch_power')
        except Exception:
            logging.exception('Error en _dispatch_power')

    def reserve_power_space(self, container, margin: int = 12):
        """Reserve a transparent spacer frame with the same size as the global
        power button plus `margin` pixels. Returns the spacer frame (not
        packed); caller should place/pack it inside `container`.
        """
        try:
            # Read layout-config margin if present
            layout_cfg = load_layout_config() or {}
            power_cfg = layout_cfg.get("global", {}).get("power", {})
            cfg_margin = power_cfg.get("margin")
            cfg_extra = power_cfg.get("extra_padding") or 0
            if cfg_margin is None:
                cfg_margin = margin or 12

            # Prefer actual button size to avoid deforming the asset
            try:
                self.update_idletasks()
            except Exception:
                pass

            btn = getattr(self, 'power_button', None)
            w = h = None
            if btn is not None:
                try:
                    w = btn.winfo_reqwidth()
                    h = btn.winfo_reqheight()
                except Exception:
                    w = h = None

            # If button not present or size unknown, try config fallback
            if (not w or not h):
                try:
                    base = Path(__file__).resolve().parents[0]
                    cfg_file = base / "kool_tpv" / "config" / "buttons_config.json"
                    if cfg_file.exists():
                        with cfg_file.open("r", encoding="utf-8") as fh:
                            bcfg = json.load(fh)
                        for entry in bcfg.get("global_buttons", []):
                            if entry.get("id") == "power":
                                w = w or entry.get("reserved_width")
                                h = h or entry.get("reserved_height")
                                break
                except Exception:
                    pass

            # Final fallbacks: ensure numeric width/height for spacer
            try:
                w = int(w) if w else 48
                h = int(h) if h else 48
            except Exception:
                w, h = 48, 48

            # Add configured extra padding and margin to reserved size
            try:
                total_w = max(1, int(w) + int(cfg_extra or 0) + int(cfg_margin or 0))
                total_h = max(1, int(h) + int(cfg_extra or 0) + int(cfg_margin or 0))
            except Exception:
                total_w, total_h = w, h

            try:
                spacer = ctk.CTkFrame(container, width=total_w, height=total_h, fg_color='transparent')
                try:
                    spacer.pack_propagate(False)
                except Exception:
                    pass
            except Exception:
                logging.exception('Error creando spacer para power')
                return None

            return spacer
        except Exception:
            logging.exception('Error reservando espacio para power')
            return None

    def load_tpv(self):
        """Carga TPV en el main_frame (placeholder).

        Importa el módulo de vista `kool_tpv.modulos.tpv.tpv_view` sin crear
        elementos gráficos; muestra un placeholder indicando que el módulo
        se ha cargado correctamente.
        """
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        try:
            from kool_tpv.modulos.tpv.tpv_view_new import TpvView

            # Ocultar botones de navegación (mantener visible el power_button)
            try:
                for k, btn in list(self.nav_buttons.items()):
                    btn.pack_forget()
            except Exception:
                pass

            # Mostrar el botón PRINT ON solamente dentro de TPV
            try:
                if getattr(self, "print_on_button", None) is not None:
                    self.print_on_button.pack(pady=(0, 12))
            except Exception:
                logging.exception("Error mostrando PRINT ON en TPV")

            view = TpvView(self.main_frame, db=getattr(self, "db", None))
            # Guardar referencia para poder gestionar el teardown del reloj
            self.tpv_view = view
            self.current_view = "tpv"
            view.pack(fill="both", expand=True)  # Vista ya está construida en __init__
        except Exception:
            logging.exception("Error cargando módulo TPV")
            # Fallback sencillo si hay algún error al importar/mostrar la vista
            label = ctk.CTkLabel(
                self.main_frame,
                text="Módulo TPV cargado correctamente",
                font=self.base_font,
                text_color="white",
            )
            label.pack(expand=True)

    def close_app(self):
        """Salir/volver atrás (actualmente solo cerrar).

        Si estamos dentro del módulo TPV, vuelve a la navegación principal
        en lugar de cerrar la app. En otro caso, cierra la aplicación.
        """

        # Si estamos en TPV, comprobar carrito antes de hacer teardown y volver a la navegación
        if getattr(self, "current_view", None) == "tpv":
            tpv = getattr(self, "tpv_view", None)
            # Si hay un TPV activo, revisar si el carrito contiene artículos
            if tpv is not None:
                try:
                    carrito = getattr(tpv, 'carrito_service', None)
                    if carrito is not None:
                        try:
                            # Preferir método is_empty si existe
                            if getattr(carrito, 'is_empty', None) and callable(carrito.is_empty):
                                empty = carrito.is_empty()
                            else:
                                try:
                                    empty = (carrito.get_item_count() == 0)
                                except Exception:
                                    empty = (len(carrito.get_items() or []) == 0)
                        except Exception:
                            empty = True

                        if not empty:
                            try:
                                from kool_tpv.utils.custom_dialog import show_error
                                show_error(self, 'Carrito no vacío', 'No se puede salir del TPV con artículos en el carrito. Finaliza la tarea.')
                            except Exception:
                                logging.exception('Error mostrando diálogo carrito no vacío')
                            return
                except Exception:
                    logging.exception('Error comprobando estado del carrito antes de cerrar TPV')

                try:
                    tpv.teardown()
                except Exception:
                    pass
                try:
                    del self.tpv_view
                except Exception:
                    pass

            try:
                for w in list(self.main_frame.winfo_children()):
                    try:
                        w.destroy()
                    except Exception:
                        pass
            except Exception:
                pass

            self.current_view = None

            # Restaurar botones de navegación
            try:
                # Ocultar el botón PRINT ON al salir del TPV
                try:
                    if getattr(self, "print_on_button", None) is not None:
                        self.print_on_button.pack_forget()
                except Exception:
                    pass

                for key, btn in list(self.nav_buttons.items()):
                    try:
                        btn.pack(pady=getattr(self, 'nav_pady', 14), padx=getattr(self, 'nav_padx', 20), fill="x")
                    except Exception:
                        pass
            except Exception:
                pass

            return

        # Si no estamos en TPV, cerrar conexión a BD y salir
        try:
            if getattr(self, "db", None):
                try:
                    self.db.close_connection()
                except Exception:
                    logging.exception("Error cerrando la conexión a la base de datos")
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

    def open_almacen(self):
        """Open Almacén module: hide main nav and main_frame, instantiate AlmacenView.

        The back callback destroys the almacen view and restores the original
        navigation and main frame packing.
        """
        try:
            # Hide existing navigation and main content
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            # Lazy import to avoid startup circular imports
            try:
                from kool_tpv.modulos.almacen.almacen_view import AlmacenView
            except Exception:
                logging.exception('Error importando AlmacenView')
                return

            # Instantiate almacen view attached to the root (self)
            try:
                self.almacen_view = AlmacenView(self, db=getattr(self, 'db', None), keyboard_manager=getattr(self, 'keyboard_mgr', None))
            except Exception:
                logging.exception('Error instanciando AlmacenView')
                # restore UI
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            # Define back callback to destroy almacen view and restore frames
            def _on_back():
                try:
                    # Delegar a _on_power para verificar cambios sin guardar
                    if hasattr(self, 'almacen_view') and self.almacen_view:
                        try:
                            if not self.almacen_view._on_power():
                                return  # Usuario canceló, no proceder
                        except Exception:
                            logging.exception('Error llamando a almacen_view._on_power')
                            return

                    # Usuario aceptó o no hay cambios: limpiar referencias
                    try:
                        if getattr(self, 'almacen_view', None):
                            try:
                                del self.almacen_view
                            except Exception:
                                pass
                    except Exception:
                        logging.exception('Error limpiando almacen_view en _on_back')

                except Exception:
                    logging.exception('Error en callback de volver desde Almacen')

            # Bind power button in the almacen sidebar to act as 'back'
            try:
                if getattr(self, 'almacen_view', None) and getattr(self.almacen_view, 'power_button', None):
                    try:
                        self.almacen_view.power_button.configure(command=_on_back)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error en open_almacen')

    def open_clientes(self):
        """Open Clientes module: hide main nav and main_frame, instantiate ClientesView."""
        try:
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            try:
                from kool_tpv.modulos.clientes.clientes_view import ClientesView
            except Exception:
                logging.exception('Error importando ClientesView')
                return

            try:
                self.clientes_view = ClientesView(self, db=getattr(self, 'db', None), keyboard_manager=getattr(self, 'keyboard_mgr', None))
            except Exception:
                logging.exception('Error instanciando ClientesView')
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            def _on_back_clientes():
                try:
                    if hasattr(self, 'clientes_view') and self.clientes_view:
                        if self.clientes_view._on_power():
                            try:
                                del self.clientes_view
                            except Exception:
                                pass
                except Exception:
                    logging.exception('Error en callback volver Clientes')

            try:
                if getattr(self, 'clientes_view', None) and getattr(self.clientes_view, 'power_button', None):
                    try:
                        self.clientes_view.power_button.configure(command=_on_back_clientes)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error abriendo clientes')

    def open_informes(self):
        """Open Informes module: hide main nav and main_frame, instantiate InformesView."""
        try:
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            try:
                from kool_tpv.modulos.informes.informes_view import InformesView
            except Exception:
                logging.exception('Error importando InformesView')
                # restore UI
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            try:
                self.informes_view = InformesView(self, db=getattr(self, 'db', None), keyboard_manager=getattr(self, 'keyboard_mgr', None))
            except Exception:
                logging.exception('Error instanciando InformesView')
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            def _on_back_informes():
                try:
                    if hasattr(self, 'informes_view') and self.informes_view:
                        if self.informes_view._on_power():
                            try:
                                del self.informes_view
                            except Exception:
                                pass
                except Exception:
                    logging.exception('Error en callback volver Informes')

            try:
                if getattr(self, 'informes_view', None) and getattr(self.informes_view, 'power_button', None):
                    try:
                        self.informes_view.power_button.configure(command=_on_back_informes)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error en open_informes')

    def open_config(self):
        """Open Config module: hide main nav and main_frame, instantiate ConfigView."""
        try:
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            try:
                from kool_tpv.modulos.configuracion.config_view import ConfigView
            except Exception:
                logging.exception('Error importando ConfigView')
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            try:
                self.config_view = ConfigView(self, db=getattr(self, 'db', None), keyboard_manager=getattr(self, 'keyboard_mgr', None))
            except Exception:
                logging.exception('Error instanciando ConfigView')
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            def _on_back_config():
                try:
                    if hasattr(self, 'config_view') and self.config_view:
                        if self.config_view._on_power():
                            try:
                                del self.config_view
                            except Exception:
                                pass
                except Exception:
                    logging.exception('Error en callback volver Config')

            try:
                if getattr(self, 'config_view', None) and getattr(self.config_view, 'power_button', None):
                    try:
                        self.config_view.power_button.configure(command=_on_back_config)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error en open_config')


if __name__ == "__main__":
    app = App()
    app.mainloop()
