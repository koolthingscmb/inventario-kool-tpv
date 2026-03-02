"""kool_tpv.modulos.tpv.tpv_view

Vista estática y receptiva del módulo TPV.

Características principales:
- `BUTTON_CONFIG` editable en la parte superior para texto y color.
- Botón de búsqueda (botón ancho, no entrada) con tamaño base ~1000x60 pero responsive.
- Grid de 4x3 botones grandes (texto en mayúsculas).
- Comportamiento responsive: los botones y las fuentes escalan al redimensionar.
- `show()` construye la vista, `teardown()` cancela tareas y unbinds.

Diseñado para ser legible y modificable; no incluye lógica de negocio.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json
from pathlib import Path
from decimal import Decimal
try:
    from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
except Exception:
    ImpresoraService = None

import customtkinter as ctk
from kool_tpv.utils.widgets.tpv_layout_base import TpvLayoutBase
import tkinter as tk
from kool_tpv.utils.custom_dialog import show_error, show_success, show_info, show_warning
from kool_tpv.modulos.tpv.actions.descuento import DescuentoAction


def _load_tpv_theme():
    """Load TPV-related colors, fonts and buttons config from project config files.

    Returns a dict with keys: 'colors', 'fonts', 'buttons_cfg'. Each may be empty
    dict if the corresponding file is missing or invalid.
    """
    base = Path(__file__).resolve().parents[2]
    cfg_dir = base / "config"
    colors = {}
    fonts = {}
    buttons_cfg = {}
    try:
        cfile = cfg_dir / "colors_config.json"
        if cfile.exists():
            with cfile.open("r", encoding="utf-8") as fh:
                all_colors = json.load(fh)
                colors = all_colors.get("tpv", {}) or {}
    except Exception:
        logging.exception("Error leyendo colors_config.json para TPV")

    try:
        ffile = cfg_dir / "font_config.json"
        if ffile.exists():
            with ffile.open("r", encoding="utf-8") as fh:
                all_fonts = json.load(fh)
                fonts = all_fonts.get("tpv", {}) or {}
    except Exception:
        logging.exception("Error leyendo font_config.json para TPV")

    try:
        bfile = cfg_dir / "buttons_config.json"
        if bfile.exists():
            with bfile.open("r", encoding="utf-8") as fh:
                buttons_cfg = json.load(fh) or {}
    except Exception:
        logging.exception("Error leyendo buttons_config.json para TPV")

    return {"colors": colors, "fonts": fonts, "buttons_cfg": buttons_cfg}


# Load once at import time
TPV_THEME = _load_tpv_theme()


def load_layout_config():
    try:
        base = Path(__file__).resolve().parents[2]
        config_path = base / "config" / "layout_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_button_config_from_json() -> Dict:
    """Return a dict with keys 'search_button' and 'buttons'.

    - 'search_button' is a dict with label, command, color, hover_color, text_color, font
    - 'buttons' is a list of dicts with text, command, color, hover_color, font
    """
    result = {"search_button": {}, "buttons": []}
    try:
        data = TPV_THEME.get("buttons_cfg") or {}

        # Prepare search button
        sb = data.get("search_button") or {"label": "BUSCAR ARTÍCULO", "command": None}
        sb_colors = TPV_THEME.get("colors", {}).get("search_button", {}) or {}
        sb_font_cfg = TPV_THEME.get("fonts", {}).get("search_button", {}) or {}
        sb_font = (sb_font_cfg.get("family"), int(sb_font_cfg.get("size"))) if sb_font_cfg.get("family") and sb_font_cfg.get("size") else None

        result["search_button"] = {
            "label": sb.get("label"),
            "command": sb.get("command"),
            "color": sb_colors.get("bg"),
            "hover_color": sb_colors.get("hover"),
            "text_color": sb_colors.get("text"),
            "corner_radius": sb_colors.get("corner_radius"),
            "font": sb_font,
        }

        # Prepare grid buttons
        buttons = data.get("buttons") or []
        grid_colors = TPV_THEME.get("colors", {}).get("grid_buttons", {}) or {}
        grid_font_cfg = TPV_THEME.get("fonts", {}).get("grid_button", {}) or {}
        grid_font = (grid_font_cfg.get("family"), int(grid_font_cfg.get("size"))) if grid_font_cfg.get("family") and grid_font_cfg.get("size") else None

        for b in buttons:
            key = b.get("color_key")
            color_spec = grid_colors.get(key, {}) if key else {}
            parsed = {
                "text": b.get("label"),
                "command": b.get("command"),
                "color": color_spec.get("bg"),
                "hover_color": color_spec.get("hover"),
                "text_color": color_spec.get("text"),
                "font": grid_font,
            }
            result["buttons"].append(parsed)

        # If no buttons defined, fallback to empty list (caller may repeat)
        return result
    except Exception:
        logging.exception("Error procesando configuración de botones TPV")
        return result

# Tamaños base / constantes
RIGHT_WIDTH = 420
INFO_BAR_HEIGHT = 90
# Hover color shared with main navigation (use theme values when available)


class ButtonFactory:
    """Factory simple para crear botones reutilizables en TPV.

    - Convierte `text` a mayúsculas automáticamente.
    - Todos los parámetros de estilo son modificables desde el llamador.
    """

    @staticmethod
    def create_button(
        parent,
        text: str,
        command=None,
        font=None,
        color=None,
        text_color=None,
        hover_color=None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        corner_radius: int = 12,
        **kwargs,
    ) -> ctk.CTkButton:
        # Use shared HOVER_COLOR when none provided
        _hover = hover_color if hover_color is not None else None
        params = dict(
            master=parent,
            text=(text or "").upper(),
            command=command,
            fg_color=color,
            hover_color=_hover,
            text_color=text_color,
            font=font,
            corner_radius=corner_radius,
        )
        # Only include width/height when explicitly provided (avoid passing None)
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height

        params.update(kwargs)
        return ctk.CTkButton(**params)


class TpvView:
    """Vista TPV responsiva y limpia.

    Uso:
        view = TpvView(parent_frame, db=optional_db)
        view.show()
        view.teardown()  # al cerrar la vista
    """

    def __init__(self, parent: ctk.CTkFrame, db: Optional[object] = None):
        self.parent = parent
        self.db = db
        self._clock_job = None
        self._destroy_bound = False
        self.info_label: Optional[ctk.CTkLabel] = None
        self._resize_bound = False

        # Referencias a widgets que necesitamos actualizar/teardown
        self.action_panel: Optional[ctk.CTkFrame] = None
        self.right_container: Optional[ctk.CTkFrame] = None
        self.grid_frame: Optional[ctk.CTkFrame] = None
        self.search_button: Optional[ctk.CTkButton] = None
        self.grid_buttons: List[ctk.CTkButton] = []
        # Sesión de cajero
        self.cajero_nombre = None
        self.cajero_id = None
        self.cajero_rol = None

    def _dispatch_action(self, name: str) -> None:
        """Dispatch string-named actions to concrete handlers (robust to rebinding order).

        Supports at least: 'Abrir Tickets' -> open TicketsUI overlay.
        """
        try:
            nm = (name or '').strip()
            logging.info(f"Acción '{nm}' pulsada")
            if not nm:
                return
            # Normalize common commands
            if nm.lower() in ('abrir tickets', 'tickets', 'ticket', 'abrir ticket'):
                if getattr(self, '_tickets_ui', None) is not None:
                    try:
                        self._tickets_ui.show()
                        return
                    except Exception:
                        logging.exception('Error mostrando TicketsUI desde dispatcher')
                else:
                    logging.info('TicketsUI no disponible al despachar acción')
                    return
            # Fallback: log only (existing rebinding logic handles other commands)
        except Exception:
            logging.exception('Error en _dispatch_action (TpvView)')

    def _on_producto_stock_selected(self, producto: Dict) -> None:
        """Callback cuando se selecciona producto desde StockUI (doble clic o Aceptar).

        Añade el producto al carrito automáticamente.

        Args:
            producto: Dict con datos del producto
        """
        try:
            if not producto or not producto.get('id'):
                logging.warning('Producto inválido recibido en callback stock')
                return

            # Añadir al carrito usando carrito_service
            if hasattr(self, 'carrito_service') and self.carrito_service is not None:
                try:
                    self.carrito_service.add_item(producto)
                    logging.info(f"Producto añadido desde STOCK: {producto.get('nombre')}")

                    # Actualizar display del carrito
                    if hasattr(self, 'carrito_ui') and self.carrito_ui is not None:
                        try:
                            self.carrito_ui.update_display()
                        except Exception:
                            logging.exception('Error actualizando carrito_ui tras añadir desde stock')
                except Exception:
                    logging.exception('Error añadiendo producto al carrito desde stock')

        except Exception:
            logging.exception('Error en _on_producto_stock_selected')

    def _open_cajero_overlay(self) -> None:
        """Abrir el overlay/acción de Cajero para autenticación.

        Intenta reutilizar la instancia de `CajeroAction` si existe,
        o instanciarla como fallback.
        """
        try:
            if getattr(self, '_cajero_action', None) is not None:
                try:
                    # `ejecutar` es el método usado por los botones para abrir el overlay
                    self._cajero_action.ejecutar()
                    return
                except Exception:
                    logging.exception('Error ejecutando _cajero_action.ejecutar()')

            # Fallback: intentar instanciar y ejecutar
            try:
                from kool_tpv.modulos.tpv.actions.cajero import CajeroAction
                caj = CajeroAction(self, self.db)
                try:
                    caj.ejecutar()
                except Exception:
                    logging.exception('Error ejecutando CajeroAction fallback')
            except Exception:
                logging.exception('No se pudo abrir overlay de Cajero (no disponible)')
        except Exception:
            logging.exception('Error en _open_cajero_overlay')
    # Ticket viewer methods removed in rollback: Stock→Consultar→Volver (sin visor)

    # ---------------------- Reloj y teardown ----------------------
    def _update_clock(self, cashier_name: str = None) -> None:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Usar cajero actual si está autenticado, sino usar el pasado por parámetro
            cajero_actual = getattr(self, 'cajero_nombre', None) or cashier_name or "Sin cajero"

            info_text = f"KOOL TPV V1.0 - {now_str}\nCajero: {cajero_actual}"
            # Only update label if it still exists
            try:
                if self.info_label and getattr(self.info_label, 'winfo_exists', None) and self.info_label.winfo_exists():
                    self.info_label.configure(text=info_text)
            except tk.TclError:
                # widget destroyed between check and configure; ignore
                pass

            # programar siguiente actualización solo si el parent aún existe
            try:
                if self.parent is not None and getattr(self.parent, 'winfo_exists', None) and self.parent.winfo_exists():
                    self._clock_job = self.parent.after(1000, lambda: self._update_clock())
                else:
                    self._clock_job = None
            except Exception:
                self._clock_job = None
        except Exception:
            logging.exception("Error actualizando reloj TPV")

    def teardown(self) -> None:
        # Cancelar after() y desbind si es necesario
        try:
            if self._clock_job and self.parent is not None:
                self.parent.after_cancel(self._clock_job)
                self._clock_job = None
        except Exception:
            logging.exception("Error cancelando reloj TPV")

        # Unbind destroy handler if we bound one
        try:
            if self._destroy_bound and self.parent is not None:
                try:
                    self.parent.unbind("<Destroy>")
                except Exception:
                    pass
                self._destroy_bound = False
        except Exception:
            logging.exception("Error unbinding destroy handler TPV")

        try:
            if self._resize_bound and self.parent is not None:
                self.parent.unbind("<Configure>")
                self._resize_bound = False
        except Exception:
            logging.exception("Error desbind resize TPV")

    # ---------------------- Responsive resizing ----------------------
    def _on_resize(self, event=None) -> None:
        """Recalcula tamaños y fuentes de los botones para comportamiento responsive."""
        try:
            total_w = max(1, self.parent.winfo_width())
            total_h = max(1, self.parent.winfo_height())

            # espacio reservado para columnas fijas (sidebar + derecha)
            sidebar_w = getattr(self.tpv_layout, 'sidebar_width', 220) if getattr(self, 'tpv_layout', None) is not None else 220
            right_w = getattr(self.tpv_layout, 'right_width', 420) if getattr(self, 'tpv_layout', None) is not None else RIGHT_WIDTH
            action_w = max(200, total_w - sidebar_w - right_w)

            # grid layout: read values set when `show()` ran (fallback to defaults)
            cols = getattr(self, '_tpv_cols', 4)
            rows = getattr(self, '_tpv_rows', 3)
            spacing = getattr(self, '_tpv_spacing', 12)
            min_btn_size = getattr(self, '_tpv_min_btn_size', 120)
            max_btn_size = getattr(self, '_tpv_max_btn_size', 400)

            horizontal_padding = spacing * (cols + 1)
            vertical_padding = spacing * (rows + 1)

            # espacio disponible para botones
            available_w = max(100, action_w - horizontal_padding)
            available_h = max(100, total_h - INFO_BAR_HEIGHT - vertical_padding - 120)

            btn_w = int(available_w / cols)
            btn_h = int(available_h / rows)

            # elegir tamaño cuadrado para botones, limitado por min/max desde config
            btn_size = max(min_btn_size, min(btn_w, btn_h, max_btn_size))

            # Tamaño del search button: ancho completo del action panel menos márgenes
            search_h = int(max(40, min(80, total_h * 0.07)))
            search_w = max(300, action_w - 40)

            # Tamaños de fuente heurísticos
            btn_font_size = max(12, int(btn_size * 0.20))
            search_font_size = max(14, int(search_h * 0.45))

            # Aplicar al botón de búsqueda
            if self.search_button:
                try:
                    self.search_button.configure(width=search_w, height=search_h, font=("Roboto-SemiBold", search_font_size))
                except Exception:
                    logging.exception("Error ajustando search_button")

            # Aplicar a botones de la grid
            for b in self.grid_buttons:
                try:
                    b.configure(width=btn_size, height=btn_size, font=("Roboto-SemiBold", btn_font_size))
                except Exception:
                    logging.exception("Error ajustando grid button")

            # Ensure grid cells don't squash buttons: set minsize for columns/rows
            try:
                for c in range(cols):
                    self.grid_frame.grid_columnconfigure(c, minsize=btn_size + spacing)
                for r in range(rows):
                    self.grid_frame.grid_rowconfigure(r, minsize=btn_size + spacing)
            except Exception:
                pass
        except Exception:
            logging.exception("Error en _on_resize TPV")

    # ---------------------- Construcción de la vista ----------------------
    def show(self) -> None:
        # Limpiar contenedor
        for w in list(self.parent.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        # Left action panel -> integrado en TpvLayoutBase
        layout_cfg = load_layout_config()
        sidebar_w = layout_cfg.get("modules", {}).get("sidebar", {}).get("width", 220)
        ticket_w = layout_cfg.get("modules", {}).get("tpv", {}).get("ticket_carrito", {}).get("width", 420)

        self.tpv_layout = TpvLayoutBase(
            self.parent,
            sidebar_width=sidebar_w,
            right_width=ticket_w
        )
        self.tpv_layout.pack(fill="both", expand=True)

        # Action panel ahora es el centro del layout
        panel_bg = TPV_THEME.get("colors", {}).get("panel_bg")
        self.action_panel = ctk.CTkFrame(self.tpv_layout.get_center_frame(), fg_color=panel_bg) if panel_bg is not None else ctk.CTkFrame(self.tpv_layout.get_center_frame())
        self.tpv_layout.set_center_content(self.action_panel)

        # Read layout config for search button geometry
        layout_cfg = load_layout_config()
        search_cfg = (
            layout_cfg
            .get("modules", {})
            .get("tpv", {})
            .get("center", {})
            .get("search_button", {})
        )

        search_height = search_cfg.get("height", 80)
        search_corner = search_cfg.get("corner_radius", 18)

        # Search button (style from config)
        btn_cfg = load_button_config_from_json().get("search_button", {})
        sb_font = btn_cfg.get("font")
        self.search_button = ButtonFactory.create_button(
            parent=self.action_panel,
            text=btn_cfg.get("label") or "BUSCAR ARTÍCULO",
            command=btn_cfg.get("command"),
            font=sb_font,
            color=btn_cfg.get("color"),
            text_color=btn_cfg.get("text_color"),
            hover_color=btn_cfg.get("hover_color"),
            corner_radius=search_corner,
            height=search_height,
        )
        self.search_button.pack(pady=(18, 8), padx=20)

        # Load layout config for TPV grid (columns/rows/spacing/sizes)
        layout_cfg = load_layout_config()
        grid_cfg = (
            layout_cfg
            .get("modules", {})
            .get("tpv", {})
            .get("center", {})
            .get("grid", {})
        )

        cols = grid_cfg.get("columns", 4)
        rows = grid_cfg.get("rows", 3)
        spacing = grid_cfg.get("spacing", 12)
        min_btn_size = grid_cfg.get("min_button_size", 120)
        max_btn_size = grid_cfg.get("max_button_size", 400)

        # Store on instance so _on_resize can use them
        self._tpv_cols = cols
        self._tpv_rows = rows
        self._tpv_spacing = spacing
        self._tpv_min_btn_size = min_btn_size
        self._tpv_max_btn_size = max_btn_size

        # Grid frame for buttons
        self.grid_frame = ctk.CTkFrame(self.action_panel, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=spacing, pady=spacing)

        # Create buttons from JSON (or fallback); ensure we have cols*rows entries
        self.grid_buttons = []
        cfg_bundle = load_button_config_from_json()
        cfg_list = cfg_bundle.get("buttons", []) or []
        total = cols * rows
        if len(cfg_list) < total:
            times = (total + len(cfg_list) - 1) // max(1, len(cfg_list)) if cfg_list else total
            cfg_list = (cfg_list * times)[:total]

        for idx in range(total):
            cfg = cfg_list[idx]
            row = idx // cols
            col = idx % cols
            # derive font tuple
            font = cfg.get("font")
            hover = cfg.get("hover_color")
            # Create button without fixed pixel width/height so it can be
            # resized responsively in `_on_resize`.
            cmd_name = cfg.get("command", cfg.get("text"))
            def _btn_cmd(name=cmd_name):
                try:
                    # Use dispatcher which will log and try to open known overlays
                    self._dispatch_action(name)
                except Exception:
                    logging.exception("Error ejecutando comando de grid button")

            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=cfg.get("text", f"BTN{idx+1}"),
                command=_btn_cmd,
                font=font,
                color=cfg.get("color"),
                text_color=cfg.get("text_color"),
                hover_color=hover,
                corner_radius=28,
            )
            # place button centered in its cell; sizing handled in _on_resize
            btn.grid(row=row, column=col, padx=spacing, pady=spacing)
            self.grid_frame.grid_columnconfigure(col, weight=1)
            self.grid_frame.grid_rowconfigure(row, weight=1)
            # store base font size so _on_resize can scale relative to it
            try:
                btn._base_font_size = int(font[1]) if font and len(font) > 1 and font[1] is not None else 36
            except Exception:
                btn._base_font_size = 36
            self.grid_buttons.append(btn)

        # Right container ahora va en la zona derecha del layout
        self.right_container = ctk.CTkFrame(self.tpv_layout.get_right_frame())
        self.tpv_layout.set_right_content(self.right_container)

        # Info bar (blanca) encima del cart_view
        info_bar = ctk.CTkFrame(self.right_container, height=INFO_BAR_HEIGHT)
        info_bar.pack(side="top", fill="x")
        info_bar.pack_propagate(False)

        # Recuperar nombre del cajero si está disponible
        cashier_name = "Nombre Cajero"
        try:
            if self.db is not None:
                getter = getattr(self.db, "get_active_cashier", None)
                if callable(getter):
                    result = getter()
                    if isinstance(result, str) and result:
                        cashier_name = result
                    elif isinstance(result, dict) and result.get("name"):
                        cashier_name = result.get("name")
        except Exception:
            logging.exception("Error recuperando nombre cajero")

        # Info label (actualizable)
        self.info_label = ctk.CTkLabel(
            info_bar,
            text="",
            font=None,
            text_color=None,
            anchor="center",
            justify="center",
        )
        self.info_label.pack(fill="both", expand=True)

        # Cart view (negra) - keep as attribute for external wiring
        self.cart_view = ctk.CTkFrame(self.right_container)
        self.cart_view.pack(side="top", fill="both", expand=True)
        self.cart_view.pack_propagate(False)

        # no debug overlay

        # Cart view placeholder for carrito and ticket display (ticket_display created after carrito)
        # Instantiate carrito service + UI
        try:
            from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
            from kool_tpv.modulos.tpv.carrito.carrito_ui import CarritoUI
            from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
            self.carrito_service = CarritoService()

            # TicketCarrito nuevo (reemplaza CarritoUI)
            self.ticket_carrito = TicketCarrito(
                parent=self.cart_view,
                carrito_service=self.carrito_service,
                keyboard_manager=None  # Por ahora None, luego conectaremos
            )
            self.ticket_carrito.pack(fill="both", expand=True)

            # Mantener referencia como carrito_ui para compatibilidad con código existente
            self.carrito_ui = self.ticket_carrito

            # ticket_display removed in rollback — no widget created here

            # Instanciar servicio de fidelización
            try:
                from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService
                try:
                    self.fidelizacion_service = FidelizacionService(self.db)
                except Exception:
                    logging.exception('Error instanciando FidelizacionService')
                    self.fidelizacion_service = None
            except Exception:
                logging.exception('Error importando FidelizacionService')
                self.fidelizacion_service = None
            # ClienteAction: conectar botón CLIENTE con el panel de selección
            try:
                from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
                try:
                    self._cliente_action = ClienteAction(self, self.db, self.carrito_service)
                except Exception:
                    self._cliente_action = None
            except Exception:
                self._cliente_action = None
            # Instanciar CajeroAction
            try:
                from kool_tpv.modulos.tpv.actions.cajero import CajeroAction
                try:
                    self._cajero_action = CajeroAction(self, self.db)
                except Exception:
                    logging.exception('Error instanciando CajeroAction')
                    self._cajero_action = None
            except Exception:
                logging.exception('Error importando CajeroAction')
                self._cajero_action = None
            # Instanciar DescuentoAction
            try:
                try:
                    self.descuento_action = DescuentoAction(self, self.carrito_service)
                except Exception:
                    logging.exception('Error instanciando DescuentoAction')
                    self.descuento_action = None
            except Exception:
                logging.exception('Error creando DescuentoAction')
                self.descuento_action = None
            # Instanciar DevolucionAction
            try:
                try:
                    from kool_tpv.modulos.tpv.actions.devolucion import DevolucionAction
                    self._devolucion_action = DevolucionAction(self, self.db, self.carrito_service)
                except Exception:
                    logging.exception('Error instanciando DevolucionAction')
                    self._devolucion_action = None
            except Exception:
                logging.exception('Error creando DevolucionAction')
                self._devolucion_action = None
            # Instanciar StockUI — intentar varias rutas posibles para compatibilidad
            try:
                StockUI = None
                try:
                    # ruta actual tras mover archivos
                    from kool_tpv.modulos.tpv.actions.Stock.stock_ui import StockUI
                except Exception:
                    try:
                        # posible ruta antigua/alternativa
                        from kool_tpv.modulos.tpv.ui.stock_ui import StockUI
                    except Exception:
                        StockUI = None

                if StockUI is not None:
                    try:
                        self._stock_ui = StockUI(self, self.db, on_selection_callback=self._on_producto_stock_selected)
                    except Exception:
                        logging.exception('Error instanciando StockUI')
                        self._stock_ui = None
                else:
                    logging.exception('Error importando StockUI: no se encontró el módulo en rutas esperadas')
                    self._stock_ui = None
            except Exception:
                logging.exception('Error creando StockUI (unexpected)')
                self._stock_ui = None
            # Instanciar CierreUI (cierres de caja)
            try:
                from kool_tpv.modulos.tpv.actions.cierres.cierre_ui import CierreUI
                try:
                    self._cierre_ui = CierreUI(self, self.db)
                except Exception:
                    logging.exception('Error instanciando CierreUI')
                    self._cierre_ui = None
            except Exception:
                # not critical if cierres action not available
                self._cierre_ui = None
            # Instanciar TicketsUI (tickets)
            try:
                from kool_tpv.modulos.tpv.actions.tickets.tickets_ui import TicketsUI
                try:
                    self._tickets_ui = TicketsUI(self, self.db)
                except Exception:
                    logging.exception('Error instanciando TicketsUI')
                    self._tickets_ui = None
            except Exception:
                # not critical if tickets action not available
                self._tickets_ui = None
            # attach cash controller UI (entry + CASH button)
            try:
                from kool_tpv.modulos.tpv.actions.cash import CashController
                # on_finalize: simple default that clears carrito and refreshes UI
                def _on_finalize(efectivo, forma_pago='Efectivo', importe_efectivo=None, importe_tarjeta=None):
                    """Finalize wrapper used by payment controllers.

                    If `efectivo` is None (used for non-cash payments), treat pagado as
                    the total amount so ticket fields remain numeric.
                    """
                    # Guard: do not allow finalizing when cart is empty
                    try:
                        try:
                            empty = False
                            if getattr(self.carrito_service, 'is_empty', None) and callable(self.carrito_service.is_empty):
                                empty = self.carrito_service.is_empty()
                            else:
                                empty = (self.carrito_service.get_item_count() == 0)
                        except Exception:
                            empty = True
                        if empty:
                            try:
                                show_warning(self.parent if hasattr(self, 'parent') else None, 'Carrito vacío', 'No se puede realizar una venta sin artículos.')
                            except Exception:
                                logging.exception('Error mostrando warning carrito vacío')
                            return
                    except Exception:
                        logging.exception('Error comprobando carrito vacío en on_finalize')

                    success = False
                    try:
                        # Persist the ticket, lines and update stock in DB
                        from kool_tpv.base_datos.ticket_service import save_ticket
                        resumen = self.carrito_service.get_resumen_financiero()
                        # Capturar items antes de cualquier limpieza para impresión
                        try:
                            items_to_print = list(self.carrito_service.get_items() or [])
                        except Exception:
                            items_to_print = []

                        # Capturar puntos canjeados ANTES de save_ticket (clear resetea a 0)
                        try:
                            puntos_canjeados_capturados = self.carrito_service.get_puntos_canjeados() or Decimal('0')
                        except Exception:
                            puntos_canjeados_capturados = Decimal('0')
                        cajero = getattr(self, 'cajero_nombre', None) or None

                        # Recuperar cliente desde CarritoService (si existe)
                        cliente_info = None
                        cliente_nombre = None
                        cliente_id = None
                        try:
                            cliente_info = self.carrito_service.get_cliente()
                            if cliente_info:
                                cliente_nombre = cliente_info.get('nombre') or cliente_info.get('name') or None
                                cliente_id = cliente_info.get('id') or cliente_info.get('cliente_id') or None
                        except Exception:
                            logging.exception('Error obteniendo cliente desde CarritoService')

                        # Prepare importe_efectivo / importe_tarjeta as Decimals (or 0)
                        try:
                            importe_efectivo_val = Decimal(str(importe_efectivo)) if importe_efectivo is not None else Decimal('0')
                        except Exception:
                            importe_efectivo_val = Decimal('0')
                        try:
                            importe_tarjeta_val = Decimal(str(importe_tarjeta)) if importe_tarjeta is not None else Decimal('0')
                        except Exception:
                            importe_tarjeta_val = Decimal('0')

                        # Determine pagado value: if efectivo is None (card), use total
                        try:
                            if efectivo is None:
                                total_val = resumen.get('total', 0.0)
                                pagado_val = Decimal(str(total_val))
                            else:
                                pagado_val = Decimal(str(efectivo))

                            # Obtener descuento si existe
                            try:
                                descuento_data = None
                                try:
                                    descuento_data = self.carrito_service.get_descuento()
                                except Exception:
                                    descuento_data = None
                            except Exception:
                                descuento_data = None

                            # Si existe un flujo de Devolución activo y tiene líneas, delegar la confirmación
                            save_res = None
                            try:
                                devol_svc = None
                                if getattr(self, '_devolucion_action', None) is not None:
                                    devol_svc = getattr(self._devolucion_action, 'devolucion_service', None)
                                if devol_svc is not None and callable(getattr(devol_svc, 'listar_lineas', None)) and len(devol_svc.listar_lineas()) > 0:
                                    # Delegar la persistencia a DevolucionService (convierte/valida internamente)
                                    save_res = devol_svc.confirmar_devolucion(usuario=cajero, cliente_id=cliente_id, efectivo=pagado_val, forma_pago=forma_pago, importe_efectivo=importe_efectivo_val, importe_tarjeta=importe_tarjeta_val, descuento_data=descuento_data)
                                else:
                                    save_res = save_ticket(
                                        self.db,
                                        self.carrito_service.get_items(),
                                        resumen,
                                        pagado_val,
                                        cajero=cajero,
                                        cliente=cliente_nombre,
                                        cliente_id=cliente_id,
                                        forma_pago=forma_pago,
                                        importe_efectivo=importe_efectivo_val,
                                        importe_tarjeta=importe_tarjeta_val,
                                        descuento_data=descuento_data,
                                        carrito_service=self.carrito_service,
                                        fidelizacion_service=getattr(self, 'fidelizacion_service', None),
                                    )
                            except Exception:
                                # fallback to direct save_ticket if devolucion confirm fails
                                logging.exception('Error delegando a DevolucionService; intentando save_ticket directo')
                                save_res = save_ticket(
                                    self.db,
                                    self.carrito_service.get_items(),
                                    resumen,
                                    pagado_val,
                                    cajero=cajero,
                                    cliente=cliente_nombre,
                                    cliente_id=cliente_id,
                                    forma_pago=forma_pago,
                                    importe_efectivo=importe_efectivo_val,
                                    importe_tarjeta=importe_tarjeta_val,
                                    descuento_data=descuento_data,
                                    carrito_service=self.carrito_service,
                                    fidelizacion_service=getattr(self, 'fidelizacion_service', None),
                                )
                            # soportar distintos retornos: (id,num) o (id,num,tesoro_dict)
                            ticket_id = None
                            num_ticket = None
                            try:
                                if isinstance(save_res, (list, tuple)):
                                    if len(save_res) >= 2:
                                        ticket_id, num_ticket = save_res[0], save_res[1]
                            except Exception:
                                # dejar ticket_id/num_ticket como None si unpack falla
                                ticket_id = None
                                num_ticket = None

                            logging.info(f'Ticket guardado id={ticket_id} num={num_ticket} forma_pago={forma_pago} Efectivo: {importe_efectivo_val} Tarjeta: {importe_tarjeta_val}')
                            success = True
                        except Exception as e:
                            logging.exception('Error guardando ticket en DB')
                            # try to surface DB path and error to the user
                            try:
                                db_path = getattr(self.db, 'db_path', 'unknown')
                            except Exception:
                                db_path = 'unknown'
                            msg = f"Error guardando ticket en la base de datos.\nDB: {db_path}\nDetalle: {e}"
                            try:
                                show_error(self.parent if hasattr(self, 'parent') else None, 'Error guardando ticket', msg)
                            except Exception:
                                logging.exception('No se pudo mostrar el diálogo de error')
                    except Exception:
                        logging.exception('Error en on_finalize wrapper')
                        try:
                            show_error(self.parent if hasattr(self, 'parent') else None, 'Error', 'Se produjo un error interno al finalizar la operación de cobro.')
                        except Exception:
                            pass

                    # Only clear carrito if persistence succeeded
                    if success:
                        try:
                            self.carrito_service.clear()
                            self.carrito_ui.update_display()
                            try:
                                show_success(self.parent if hasattr(self, 'parent') else None, 'Venta guardada', f'Ticket guardado correctamente (#{num_ticket})')
                            except Exception:
                                pass
                        except Exception:
                            logging.exception('Error limpiando carrito tras guardar ticket')

                        # Ensure devolucion mode is ended if it was active (idempotent)
                        try:
                            if getattr(self, '_devolucion_action', None) is not None:
                                ds = getattr(self._devolucion_action, 'devoluciones_service', None) or getattr(self._devolucion_action, 'devolucion_service', None)
                                if ds is not None and hasattr(ds, 'end_devolucion'):
                                    try:
                                        ds.end_devolucion()
                                    except Exception:
                                        logging.exception('Error finalizando devolucion tras guardar ticket')
                                # also hide panel if still open to refresh UI
                                try:
                                    panel = getattr(self._devolucion_action, '_panel', None)
                                    if panel is not None:
                                        try:
                                            panel.hide()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                        except Exception:
                            logging.exception('Error comprobando/terminando estado de devolucion')

                        # Intentar imprimir ticket (simulación) sin bloquear flujo
                        try:
                            if getattr(self, 'impresora_service', None) is not None:
                                try:
                                    # Prefer printed snapshot stored in DB
                                    printed_text = None
                                    try:
                                        if getattr(self, 'db', None) is not None and ticket_id is not None:
                                            row = self.db.fetch_one("SELECT ticket_text FROM tickets WHERE id = ?", (ticket_id,))
                                            if row and row[0]:
                                                printed_text = row[0]
                                    except Exception:
                                        printed_text = None

                                    if printed_text:
                                        # Simulated print of stored snapshot
                                        print("\n" + "="*50)
                                        print(" IMPRIMIENDO TICKET (snapshot) ")
                                        print("="*50 + "\n")
                                        print(printed_text)
                                        print("\n" + "="*50 + "\n")
                                        try:
                                            self.impresora_service.logger.info("Ticket impreso (snapshot) id=%s", ticket_id)
                                        except Exception:
                                            pass
                                    else:
                                        # Fallback: generate from DB and print
                                        try:
                                            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                                            impresora = ImpresoraService(self.db)
                                            texto_imp = impresora.generar_ticket_desde_id(ticket_id)
                                            if texto_imp:
                                                print("\n" + "="*50)
                                                print(" IMPRIMIENDO TICKET ")
                                                print("="*50 + "\n")
                                                print(texto_imp)
                                                print("\n" + "="*50 + "\n")
                                                try:
                                                    impresora.logger.info("Ticket impreso (simulado) id=%s", ticket_id)
                                                except Exception:
                                                    pass
                                        except Exception:
                                            logging.exception('Error imprimiendo ticket desde BD')
                                except Exception:
                                    logging.exception('ImpresoraService no disponible o error al llamar imprimir_ticket')
                        except Exception:
                            logging.exception('Error en bloque de impresión de ticket')

                self._cash_controller = CashController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
            except Exception:
                pass
            # MultiPago controller (mixed payments)
            try:
                from kool_tpv.modulos.tpv.actions.multi_s import MultiPagoController
                try:
                    self._multi_controller = MultiPagoController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
                except Exception:
                    self._multi_controller = None
            except Exception:
                self._multi_controller = None
            # Direct payment controllers: Tarjeta (card) and Web
            try:
                from kool_tpv.modulos.tpv.actions.tarjeta import DirectPaymentController
                try:
                    self._tarjeta_controller = DirectPaymentController(self.carrito_ui, self.carrito_service, on_finalize=_on_finalize)
                except Exception:
                    self._tarjeta_controller = None

                try:
                        self._web_controller = DirectPaymentController(
                        self.carrito_ui,
                        self.carrito_service,
                        on_finalize=_on_finalize,
                        payment_method='Web',
                        banner_text='Finalizar venta WEB?',
                        banner_color=None,
                        help_bg_color=None,
                    )
                except Exception:
                    self._web_controller = None
            except Exception:
                # if import fails, ensure safe defaults
                self._tarjeta_controller = None
                self._web_controller = None
            # initial display (comentado hasta conectar update_carrito)
            # try:
            #     self.carrito_ui.update_display()
            # except Exception:
            #     pass
            # Instantiate impresora service (simulada) for printing tickets
            try:
                if ImpresoraService is not None:
                    try:
                        self.impresora_service = ImpresoraService(db=self.db)
                    except Exception:
                        self.impresora_service = None
                else:
                    self.impresora_service = None
            except Exception:
                self.impresora_service = None
            # Rebind big 'COBRAR' grid button (if present) to trigger cash action
            try:
                for btn in self.grid_buttons:
                    try:
                        txt = (btn.cget('text') or '').strip().upper()
                        # Bind CLIENTE button to ClienteAction if available
                        if txt == 'CLIENTE' and getattr(self, '_cliente_action', None) is not None:
                            btn.configure(command=lambda act=self._cliente_action: act.ejecutar())
                            logging.info('Grid button CLIENTE bound to ClienteAction')
                        if txt == 'CAJERO' and getattr(self, '_cajero_action', None) is not None:
                            btn.configure(command=lambda act=self._cajero_action: act.ejecutar())
                            logging.info('Grid button CAJERO bound to CajeroAction')
                        if txt in ('COBRAR', 'CASH') and getattr(self, '_cash_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._cash_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to CashController')
                        if txt == 'STOCK' and getattr(self, '_stock_ui', None) is not None:
                            btn.configure(command=(lambda ui=self._stock_ui: ui.show()))
                            logging.info('Grid button STOCK bound to StockUI')
                        if txt in ('CIERRE', 'CIERRES') and getattr(self, '_cierre_ui', None) is not None:
                            btn.configure(command=(lambda ui=self._cierre_ui: ui.show()))
                            logging.info('Grid button CIERRES bound to CierreUI')
                        if txt in ('TICKETS', 'TICKET') and getattr(self, '_tickets_ui', None) is not None:
                            # Wrap with a placeholder permission check (to implement later)
                            def _open_tickets(ui=self._tickets_ui, parent=self):
                                try:
                                    allowed = True
                                    try:
                                        checker = getattr(parent, '_check_tickets_permission', None)
                                        if callable(checker):
                                            allowed = bool(checker())
                                    except Exception:
                                        allowed = True
                                    if not allowed:
                                        try:
                                            show_error(parent.parent if getattr(parent, 'parent', None) is not None else None, 'Sin permiso', 'Acceso no autorizado a TICKETS')
                                        except Exception:
                                            logging.exception('Acceso denegado a TICKETS')
                                        return
                                    ui.show()
                                except Exception:
                                    logging.exception('Error abriendo TicketsUI')

                            btn.configure(command=_open_tickets)
                            logging.info('Grid button TICKETS bound to TicketsUI')
                        if txt == 'DESCUENTO' and getattr(self, 'descuento_action', None) is not None:
                            btn.configure(command=lambda act=self.descuento_action: act.ejecutar())
                            logging.info('Grid button DESCUENTO bound to DescuentoAction')
                        if txt in ('DEVOLUCIÓN', 'DEVOLUCION', 'REALIZAR DEVOLUCIÓN', 'REALIZAR DEVOLUCION') and getattr(self, '_devolucion_action', None) is not None:
                            # Guard: if there's an active sale (venta) in the carrito, block opening devoluciones
                            def _attempt_devol(act=self._devolucion_action, parent=(self.parent if hasattr(self, 'parent') else None), carrito=self.carrito_service):
                                try:
                                    sale_active = False
                                    try:
                                        if carrito is not None and hasattr(carrito, 'get_items'):
                                            for it in (carrito.get_items() or []):
                                                try:
                                                    if str(it.get('line_tipo', '')).lower() != 'devolucion' and int(it.get('cantidad', 0)) > 0:
                                                        sale_active = True
                                                        break
                                                except Exception:
                                                    continue
                                    except Exception:
                                        sale_active = False

                                    if sale_active:
                                        try:
                                            from kool_tpv.utils.custom_dialog import show_error
                                            show_error(parent, 'Operación no permitida', 'No se puede devolver si hay una venta en curso')
                                        except Exception:
                                            logging.exception('Error mostrando diálogo al bloquear Devolución')
                                        return

                                    act.ejecutar()
                                except Exception:
                                    logging.exception('Error al intentar abrir Devolución')

                            btn.configure(command=_attempt_devol)
                            logging.info('Grid button DEVOLUCIÓN bound to guarded DevolucionAction')
                        if any(k in txt for k in ('MULTI', 'MIXTO')) and getattr(self, '_multi_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._multi_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to MultiPagoController')
                        if txt in ('TARJETA', 'CARD') and getattr(self, '_tarjeta_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._tarjeta_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to DirectPaymentController (Tarjeta)')
                        if txt == 'WEB' and getattr(self, '_web_controller', None) is not None:
                            btn.configure(command=lambda ctl=self._web_controller: ctl._on_action())
                            logging.info(f'Grid button {txt} bound to DirectPaymentController (Web)')
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error rebinding grid buttons to payment controllers')
        except Exception:
            logging.exception("Error instanciando CarritoService/CarritoUI")

        # Si no hay cajero autenticado, mostrar warning que abre overlay de Cajeros
        try:
            active = None
            if self.db is not None:
                getter = getattr(self.db, 'get_active_cashier', None)
                if callable(getter):
                    try:
                        active = getter()
                    except Exception:
                        active = None

            has_cajero = False
            if active:
                if isinstance(active, dict):
                    nombre = active.get('name') or active.get('nombre')
                    if nombre:
                        self.cajero_nombre = nombre
                        self.cajero_id = active.get('id') or active.get('cajero_id')
                        has_cajero = True
                elif isinstance(active, str):
                    self.cajero_nombre = active
                    has_cajero = True

            if not has_cajero:
                try:
                    parent_win = self.parent if hasattr(self, 'parent') else None
                    show_warning(
                        parent_win,
                        'Cajero no autenticado',
                        'No hay cajero autenticado. Pulsa Aceptar para abrir el panel de cajeros y autenticar uno.',
                        callback=lambda: self._open_cajero_overlay(),
                    )
                except Exception:
                    logging.exception('Error mostrando diálogo de cajero no autenticado')
        except Exception:
            logging.exception('Error comprobando sesión de cajero')

        # Iniciar reloj
        try:
            self._update_clock(cashier_name)
        except Exception:
            logging.exception("Error iniciando reloj")
        # Bind to parent destroy to ensure teardown is called and after() cancelled
        try:
            if not self._destroy_bound and self.parent is not None:
                try:
                    self.parent.bind("<Destroy>", lambda e: self.teardown())
                    self._destroy_bound = True
                except Exception:
                    logging.exception('Error binding destroy handler TPV')
        except Exception:
            logging.exception('Error setting destroy bind for TPV')
        # Conectar controlador de acciones (buscar artículo, etc.)
        try:
            from kool_tpv.modulos.tpv.tpv_controller import TpvController
            # guardar referencia para teardown si es necesario
            self.controller = TpvController(self)
        except Exception:
            logging.exception("Error inicializando TpvController")

        # Bind resize para comportamiento responsive
        try:
            if not self._resize_bound:
                self.parent.bind("<Configure>", lambda e: self._on_resize(e))
                self._resize_bound = True
            # ajuste inicial
            self._on_resize()
        except Exception:
            logging.exception("Error bind resize TPV")


# Export limpio
__all__ = ["TpvView", "ButtonFactory", "BUTTON_CONFIG"]

