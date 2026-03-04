"""kool_tpv.modulos.tpv.tpv_view

Vista del módulo TPV heredando de PaginaVisorCarrito.

Características:
- Hereda estructura grid izq + TicketCarrito derecha
- Override _build_header() → search button
- Override _build_grid() → grid 4×3 botones responsivos
- Conecta carrito_service, acciones, payment controllers vía controller
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json
from pathlib import Path

import customtkinter as ctk

from kool_tpv.utils.templates.pagina_visor_carrito import PaginaVisorCarrito
from kool_tpv.utils.custom_dialog import show_warning

logger = logging.getLogger(__name__)


def _load_tpv_theme():
    """Load TPV colors, fonts and buttons from config files."""
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
        logger.exception("Error leyendo colors_config.json para TPV")

    try:
        ffile = cfg_dir / "font_config.json"
        if ffile.exists():
            with ffile.open("r", encoding="utf-8") as fh:
                all_fonts = json.load(fh)
                fonts = all_fonts.get("tpv", {}) or {}
    except Exception:
        logger.exception("Error leyendo font_config.json para TPV")

    try:
        bfile = cfg_dir / "buttons_config.json"
        if bfile.exists():
            with bfile.open("r", encoding="utf-8") as fh:
                buttons_cfg = json.load(fh) or {}
    except Exception:
        logger.exception("Error leyendo buttons_config.json para TPV")

    return {"colors": colors, "fonts": fonts, "buttons_cfg": buttons_cfg}


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
    """Return dict with 'search_button' and 'buttons' from config."""
    result = {"search_button": {}, "buttons": []}

    try:
        data = TPV_THEME.get("buttons_cfg") or {}

        # Search button
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

        # Grid buttons
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

        return result
    except Exception:
        logger.exception("Error procesando configuración de botones TPV")
        return result


class ButtonFactory:
    """Factory para crear botones reutilizables en TPV."""

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
        params = dict(
            master=parent,
            text=(text or "").upper(),
            command=command,
            fg_color=color,
            hover_color=hover_color,
            text_color=text_color,
            font=font,
            corner_radius=corner_radius,
        )
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height

        params.update(kwargs)
        return ctk.CTkButton(**params)


class TpvView(PaginaVisorCarrito):
    """Vista TPV con grid botones 4×3 + TicketCarrito derecha."""

    def __init__(self, parent: ctk.CTkFrame, db: Optional[object] = None):
        # Atributos de sesión cajero
        self.cajero_nombre = None
        self.cajero_id = None
        self.cajero_rol = None

        # Referencias para teardown
        self._clock_job = None
        self._resize_bound = False
        self._destroy_bound = False

        # Listas widgets
        self.grid_buttons: List[ctk.CTkButton] = []
        self.search_button: Optional[ctk.CTkButton] = None

        # Layout config grid
        self._tpv_cols = 4
        self._tpv_rows = 3
        self._tpv_spacing = 12
        self._tpv_min_btn_size = 120
        self._tpv_max_btn_size = 400

        # Frame principal del grid
        self.grid_frame: Optional[ctk.CTkFrame] = None

        # Llamar super → crea estructura base (header, grid_scroll, ticket_carrito)
        super().__init__(parent, db=db, module_name='tpv')

        # Conectar carrito_service al ticket_carrito de la plantilla
        try:
            from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
            self.carrito_service = CarritoService()
            if self.ticket_carrito is not None:
                self.ticket_carrito.carrito_service = self.carrito_service
        except Exception:
            logger.exception("Error instanciando CarritoService")
            self.carrito_service = None

        # Alias para compatibilidad
        self.carrito_ui = self.ticket_carrito

        # Instanciar controller (hace TODOS los setups)
        from kool_tpv.modulos.tpv.tpv_controller import TpvController
        self.controller = TpvController(self, db)

        # Comprobar cajero autenticado
        self._check_cajero()

        # Iniciar reloj
        self._update_clock()

        # Bind eventos
        self._bind_events()

        # Resize inicial
        self._on_resize()

        logger.info("TpvView inicializado")

    def _build_header(self):
        """Override: añadir search button al header."""
        try:
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

            btn_cfg = load_button_config_from_json().get("search_button", {})
            sb_font = btn_cfg.get("font")

            self.search_button = ButtonFactory.create_button(
                parent=self.header,
                text=btn_cfg.get("label") or "BUSCAR ARTÍCULO",
                command=btn_cfg.get("command"),
                font=sb_font,
                color=btn_cfg.get("color"),
                text_color=btn_cfg.get("text_color"),
                hover_color=btn_cfg.get("hover_color"),
                corner_radius=search_corner,
                height=search_height,
            )
            # Reduce top space so the button stays glued to the top of the header
            self.search_button.pack(pady=(0, 6), padx=20, anchor='n')

        except Exception:
            logger.exception("Error en _build_header")

    def _build_grid(self):
        """Override: crear grid 4×3 botones (NO usar grid_scroll scrollable)."""
        try:
            # Leer configuración grid
            layout_cfg = load_layout_config()
            grid_cfg = (
                layout_cfg
                .get("modules", {})
                .get("tpv", {})
                .get("center", {})
                .get("grid", {})
            )

            self._tpv_cols = grid_cfg.get("columns", 4)
            self._tpv_rows = grid_cfg.get("rows", 3)
            self._tpv_spacing = grid_cfg.get("spacing", 12)
            self._tpv_min_btn_size = grid_cfg.get("min_button_size", 120)
            self._tpv_max_btn_size = grid_cfg.get("max_button_size", 400)

            # Destruir grid_scroll (es scrollable, no lo necesitamos)
            try:
                if self.grid_scroll is not None:
                    self.grid_scroll.destroy()
            except Exception:
                pass

            # Crear frame NO scrollable para grid fijo
            self.grid_frame = ctk.CTkFrame(self.left_container, fg_color="transparent")
            self.grid_frame.pack(fill="both", expand=True, padx=self._tpv_spacing, pady=self._tpv_spacing)

            # Cargar botones desde config
            cfg_bundle = load_button_config_from_json()
            cfg_list = cfg_bundle.get("buttons", []) or []
            total = self._tpv_cols * self._tpv_rows

            # Rellenar lista si faltan botones
            if len(cfg_list) < total:
                times = (total + len(cfg_list) - 1) // max(1, len(cfg_list)) if cfg_list else total
                cfg_list = (cfg_list * times)[:total]

            # Crear botones 4×3
            for idx in range(total):
                cfg = cfg_list[idx]
                row = idx // self._tpv_cols
                col = idx % self._tpv_cols

                font = cfg.get("font")
                hover = cfg.get("hover_color")
                cmd_name = cfg.get("command", cfg.get("text"))

                def _btn_cmd(name=cmd_name):
                    logger.info(f"Botón '{name}' pulsado (placeholder)")

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

                btn.grid(row=row, column=col, padx=self._tpv_spacing, pady=self._tpv_spacing, sticky="nsew")

                # Configurar peso de filas/columnas para expansión
                self.grid_frame.grid_columnconfigure(col, weight=1)
                self.grid_frame.grid_rowconfigure(row, weight=1)

                # Guardar tamaño base de fuente para resize
                try:
                    btn._base_font_size = int(font[1]) if font and len(font) > 1 and font[1] is not None else 36
                except Exception:
                    btn._base_font_size = 36

                self.grid_buttons.append(btn)

        except Exception:
            logger.exception("Error en _build_grid")

    def _check_cajero(self):
        """Comprobar si hay cajero autenticado; si no, mostrar warning."""
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
                    show_warning(
                            self.container,
                            'Cajero no autenticado',
                            'No hay cajero autenticado. Pulsa Aceptar para abrir el panel de cajeros.',
                            callback=lambda *_: self._open_cajero_overlay(),
                        )
                except Exception:
                    logger.exception('Error mostrando diálogo cajero no autenticado')

        except Exception:
            logger.exception('Error comprobando sesión cajero')

    def _open_cajero_overlay(self) -> None:
        """Abrir overlay de Cajero."""
        try:
            if getattr(self, '_cajero_action', None) is not None:
                try:
                    self._cajero_action.ejecutar()
                    return
                except Exception:
                    logger.exception('Error ejecutando _cajero_action.ejecutar()')

        except Exception:
            logger.exception('Error en _open_cajero_overlay')

    def _bind_events(self):
        """Bind eventos resize y destroy."""
        try:
            if not self._destroy_bound and self.container is not None:
                try:
                    self.container.bind("<Destroy>", lambda e: self.teardown())
                    self._destroy_bound = True
                except Exception:
                    logger.exception('Error binding destroy handler')
        except Exception:
            logger.exception('Error setting destroy bind')

        try:
            if not self._resize_bound and self.container is not None:
                self.container.bind("<Configure>", lambda e: self._on_resize(e))
                self._resize_bound = True
        except Exception:
            logger.exception("Error bind resize TPV")

    def _update_clock(self, cashier_name: str = None) -> None:
        """Actualizar reloj en TicketCarrito."""
        try:
            now_str = datetime.now().strftime("%H:%M:%S")

            cajero_actual = getattr(self, 'cajero_nombre', None) or cashier_name or "Sin cajero"

            # Actualizar en TicketCarrito
            if self.ticket_carrito is not None:
                try:
                    self.ticket_carrito.update_hora(now_str)
                    self.ticket_carrito.update_cajero(cajero_actual)
                except Exception:
                    pass

            # Programar siguiente actualización
            try:
                if self.container is not None and getattr(self.container, 'winfo_exists', None) and self.container.winfo_exists():
                    self._clock_job = self.container.after(1000, lambda: self._update_clock())
                else:
                    self._clock_job = None
            except Exception:
                self._clock_job = None

        except Exception:
            logger.exception("Error actualizando reloj TPV")

    def _on_resize(self, event=None) -> None:
        """Recalcular tamaños responsivos de botones."""
        try:
            total_w = max(1, self.container.winfo_width())
            total_h = max(1, self.container.winfo_height())

            # Espacio reservado
            cfg = load_layout_config()
            sidebar_w = cfg.get('modules', {}).get('sidebar', {}).get('width', 220)
            right_w = cfg.get('modules', {}).get('tpv', {}).get('ticket_carrito', {}).get('width', 420)
            action_w = max(200, total_w - sidebar_w - right_w)

            # Grid config
            cols = self._tpv_cols
            rows = self._tpv_rows
            spacing = self._tpv_spacing
            min_btn_size = self._tpv_min_btn_size
            max_btn_size = self._tpv_max_btn_size

            horizontal_padding = spacing * (cols + 1)
            vertical_padding = spacing * (rows + 1)

            available_w = max(100, action_w - horizontal_padding)
            available_h = max(100, total_h - 120 - vertical_padding - 120)

            btn_w = int(available_w / cols)
            btn_h = int(available_h / rows)

            btn_size = max(min_btn_size, min(btn_w, btn_h, max_btn_size))

            # Search button tamaño
            search_h = int(max(40, min(80, total_h * 0.07)))
            search_w = max(300, action_w - 40)

            # Font sizes
            btn_font_size = max(12, int(btn_size * 0.20))
            search_font_size = max(14, int(search_h * 0.45))

            # Aplicar a search button
            if self.search_button:
                try:
                    self.search_button.configure(width=search_w, height=search_h, font=("Roboto-SemiBold", search_font_size))
                except Exception:
                    logger.exception("Error ajustando search_button")

            # Aplicar a grid buttons
            for b in self.grid_buttons:
                try:
                    b.configure(width=btn_size, height=btn_size, font=("Roboto-SemiBold", btn_font_size))
                except Exception:
                    logger.exception("Error ajustando grid button")

            # Set minsize for grid cells
            try:
                if self.grid_frame is not None:
                    for c in range(cols):
                        self.grid_frame.grid_columnconfigure(c, minsize=btn_size + spacing)
                    for r in range(rows):
                        self.grid_frame.grid_rowconfigure(r, minsize=btn_size + spacing)
            except Exception:
                pass

        except Exception:
            logger.exception("Error en _on_resize TPV")

    def teardown(self) -> None:
        """Cancelar tareas pendientes y unbind eventos."""
        try:
            if self._clock_job and self.container is not None:
                self.container.after_cancel(self._clock_job)
                self._clock_job = None
        except Exception:
            logger.exception("Error cancelando reloj TPV")

        try:
            if self._destroy_bound and self.container is not None:
                try:
                    self.container.unbind("<Destroy>")
                except Exception:
                    pass
                self._destroy_bound = False
        except Exception:
            logger.exception("Error unbinding destroy handler TPV")

        try:
            if self._resize_bound and self.container is not None:
                self.container.unbind("<Configure>")
                self._resize_bound = False
        except Exception:
            logger.exception("Error desbind resize TPV")


__all__ = ["TpvView", "ButtonFactory"]
