"""Tab COLORES del panel de configuración UI."""
import tkinter as tk
from tkinter import colorchooser
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


_NON_COLOR_KEYS = {"description", "border_width", "use_zebra", "row_selected_border"}

_LABEL_MAP = {
    "global.background": "Fondo App",
    "global.bg_dark": "Fondo Oscuro",
    "global.bg_medium": "Fondo Medio",
    "global.bg_sidebar": "Fondo Sidebar",
    "global.dialog_bg": "Fondo Diálogos",
    "global.bg_terminal": "Fondo Terminal",
    "global.layout.app_background": "Fondo App (layout)",
    "global.layout.sidebar_background": "Fondo Sidebar (layout)",
    "global.layout.print_on_button.border": "Borde Print Button",
    "global.text_white": "Texto Blanco",
    "global.text_gray": "Texto Gris",
    "global.text_disabled": "Texto Disabled",
    "global.dialog_text": "Texto Diálogos",
    "global.text_matrix": "Texto Matrix",
    "global.success": "Verde Success",
    "global.success_hover": "Verde Success Hover",
    "global.error": "Rojo Error",
    "global.error_hover": "Rojo Error Hover",
    "global.warning": "Naranja Warning",
    "global.warning_hover": "Naranja Warning Hover",
    "global.info": "Azul Info",
    "global.info_hover": "Azul Info Hover",
}

_SUFFIX_LABELS = {
    "bg": "Fondo", "text": "Texto", "hover": "Hover", "border": "Borde",
    "primary": "Primario", "secondary": "Secundario", "accent": "Acento",
    "light": "Claro", "background": "Fondo", "warning": "Warning", "error": "Error",
    "text_white": "Texto Blanco", "text_gray": "Texto Gris",
    "text_disabled": "Texto Disabled", "text_matrix": "Texto Matrix",
    "bg_dark": "Fondo Oscuro", "bg_medium": "Fondo Medio",
    "row_normal_bg": "Fondo Fila", "row_normal_text": "Texto Fila",
    "row_zebra_bg": "Fondo Zebra", "row_hover_bg": "Fondo Hover",
    "row_hover_text": "Texto Hover", "row_selected_bg": "Fondo Selección",
    "row_selected_text": "Texto Selección", "title_text": "Texto Título",
    "message_text": "Texto Mensaje", "button_bg": "Fondo Botón",
    "button_hover": "Hover Botón", "button_text": "Texto Botón",
    "cancel_bg": "Fondo Cancelar", "cancel_hover": "Hover Cancelar",
    "button_focus_border": "Borde Focus", "border_hover": "Borde Hover",
    "text_titulo": "Texto Título", "text_label": "Texto Label",
    "text_cambio": "Texto Cambio", "text_error": "Texto Error",
    "text_info": "Texto Info", "text_cliente": "Texto Cliente",
    "text_tesoro": "Texto Tesoro", "header_text": "Texto Header",
    "bg_active_efectivo": "BG Activo Efectivo", "bg_active_tarjeta": "BG Activo Tarjeta",
    "bg_active_web": "BG Activo Web", "text_totales": "Texto Totales",
    "categories_area_bg": "Fondo Categorías", "articles_area_bg": "Fondo Artículos",
    "text_hover": "Texto Hover", "text_active": "Texto Activo",
    "bg_active": "Fondo Activo", "text_selected": "Texto Selección",
    "bg_selected": "Fondo Selección",
}

_MODULE_NAMES = {
    "tpv": "TPV", "almacen": "Almacén", "clientes": "Clientes",
    "produccion": "Producción", "informes": "Informes", "config": "Config",
}

_TPV_SECTIONS = [
    ("Grid Buttons", "grid_buttons"),
    ("Nav List", "nav_list"),
    ("Carrito Nav List", "carrito_nav_list"),
    ("Ticket Carrito", "ticket_carrito"),
    ("Payment Controllers", "payment_controllers"),
    ("Buscar Overlay", "buscar_overlay"),
]

_BTN_LABELS = {
    "buscar_articulo": "Buscar Artículo", "print_on": "Imprimir",
    "config": "Config", "stock": "Stock", "multi": "Multi",
    "web": "Web", "cierre": "Cierre", "descuento": "Descuento",
    "cliente": "Cliente", "tarjeta": "Tarjeta", "tickets": "Tickets",
    "devolucion": "Devolución", "cajero": "Cajero", "cash": "Cash",
}

_DESC_MAP = {
    "global.background": "Fondo de toda la aplicación",
    "global.bg_dark": "Paneles secundarios y fondos oscuros",
    "global.bg_medium": "Paneles intermedios",
    "global.bg_sidebar": "Barra lateral del menú principal",
    "global.dialog_bg": "Fondo de diálogos y popups",
    "global.bg_terminal": "Fondo estilo terminal (matriz)",
    "global.layout.app_background": "Fondo de la app (token layout)",
    "global.layout.sidebar_background": "Fondo del sidebar (token layout)",
    "global.layout.print_on_button.border": "Borde del botón Imprimir",
    "global.text_white": "Texto principal en toda la app",
    "global.text_gray": "Texto secundario y atenuado",
    "global.text_disabled": "Texto de elementos deshabilitados",
    "global.dialog_text": "Texto dentro de diálogos",
    "global.text_matrix": "Texto estilo terminal (verde)",
    "global.success": "Mensajes de éxito (✓)",
    "global.success_hover": "Hover de botones de éxito",
    "global.error": "Mensajes de error (✕)",
    "global.error_hover": "Hover de botones de error",
    "global.warning": "Mensajes de aviso (⚠)",
    "global.warning_hover": "Hover de botones de aviso",
    "global.info": "Mensajes informativos (ℹ)",
    "global.info_hover": "Hover de botones informativos",
}


class ColorsTab:
    """Muestra la paleta principal en 3 columnas con preview en vivo."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data_colors: Dict[str, Any] = {}
        self._data_tokens: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._build()

    def _build(self):
        self._data_colors = self.service.cargar_json("colors_config")
        self._data_tokens = self.service.cargar_json("design_tokens")

        main = tk.Frame(self.parent, bg=self._bg)
        main.pack(fill=tk.BOTH, expand=True)

        col1 = self._make_scrollable(main)
        col2 = self._make_scrollable(main)
        right = tk.Frame(main, bg=self._bg, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        self._render_core(col1)
        self._separator(col1)
        self._render_semantic(col1)

        self._render_tpv(col2)
        self._separator(col2)
        self._render_modules(col2)

        self._render_preview(right)
        self._render_save_bar(right)

    def _make_scrollable(self, parent) -> tk.Frame:
        container = tk.Frame(parent, bg=self._bg)
        container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        canvas = tk.Canvas(container, bg=self._bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self._bg)

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        return inner

    def _make_label(self, key: str) -> str:
        if key in _LABEL_MAP:
            return _LABEL_MAP[key]
        parts = key.split(".")
        suffix = parts[-1]
        if suffix in _SUFFIX_LABELS:
            return _SUFFIX_LABELS[suffix]
        return suffix.replace("_", " ").title()

    def _make_desc(self, key: str, context: str) -> str:
        if key in _DESC_MAP:
            return _DESC_MAP[key]
        parts = key.split(".")
        suffix = parts[-1]
        _type = {"bg": "Fondo", "text": "Texto", "hover": "Hover",
                 "border": "Borde", "primary": "Primario",
                 "secondary": "Secundario", "accent": "Acento",
                 "light": "Claro", "background": "Fondo",
                 "warning": "Warning", "error": "Error"}.get(suffix, suffix.replace("_", " ").title())
        if "grid_buttons" in key:
            btn = _BTN_LABELS.get(parts[-2], parts[-2].replace("_", " ").title())
            return f"{_type} del botón {btn} en el grid del TPV"
        if "carrito_nav_list" in key:
            _ln = {"line_normal": "línea normal", "line_descuento": "línea de descuento",
                   "line_devolucion": "línea de devolución",
                   "line_tesoro": "línea de tesoro",
                   "line_tesoro_visual": "línea tesoro visual"}.get(parts[-2], parts[-2].replace("_", " "))
            return f"{_type} — {_ln} del carrito"
        if "ticket_carrito" in key:
            _sec = {"header": "cabecera del ticket", "body": "cuerpo del ticket",
                    "footer": "pie del ticket"}.get(parts[-2], parts[-2].replace("_", " "))
            return f"{_type} — {_sec}"
        if "payment_controllers" in key:
            _ctrl = {"efectivo": "pago en efectivo", "tarjeta": "pago con tarjeta",
                     "web": "pago web", "multi": "pago multi",
                     "resumen": "resumen de pago"}.get(parts[-2], parts[-2])
            if "button" in key:
                return f"Botón de {_ctrl}: {_type}"
            return f"{_type} del panel de {_ctrl}"
        if "buscar_overlay" in key:
            _area = {"breadcrumb": "migas de pan", "main_buttons": "botones principales",
                     "category_buttons": "botones de categoría",
                     "article_buttons": "botones de artículo"}.get(parts[-2], parts[-2].replace("_", " "))
            return f"{_type} — {_area} del overlay de búsqueda"
        if "nav_list" in key:
            _nl = {"row_normal_bg": "Fondo de filas normales",
                   "row_normal_text": "Texto de filas normales",
                   "row_zebra_bg": "Fondo alternativo (zebra)",
                   "row_hover_bg": "Fondo al pasar ratón",
                   "row_hover_text": "Texto al pasar ratón",
                   "row_selected_bg": "Fondo de fila seleccionada",
                   "row_selected_text": "Texto de fila seleccionada"}.get(suffix)
            if _nl:
                return f"{_nl} en listas de {context}"
        if "buttons" in key and len(parts) >= 4:
            _btn_type = parts[-2]
            return f"Botón {_btn_type} de {context}: {_type}"
        if len(parts) == 2:
            return f"Color {_type} del módulo {context}"
        return f"{context} — {_type}"

    def _sub_header(self, parent, text: str):
        tk.Label(
            parent, text=f"  {text}",
            font=("Helvetica", 10, "bold"),
            fg="#aaa", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

    def _color_row(self, parent, key: str, label: str, hex_color: str,
                    desc: str = ""):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=1)

        line1 = tk.Frame(row, bg=self._bg)
        line1.pack(fill="x")

        tk.Label(
            line1, text=label, font=("Helvetica", 9), fg=self._fg,
            bg=self._bg, width=28, anchor="w"
        ).pack(side="left", padx=(0, 6))

        var = tk.StringVar(value=hex_color)
        self._values[key] = var

        swatch = tk.Label(line1, text="", bg=hex_color, width=3, height=1, relief="solid", bd=1)
        swatch.pack(side="left", padx=(0, 6))

        hex_entry = tk.Entry(line1, textvariable=var, width=10, font=("Helvetica", 9),
                             bg="#1a1a1a", fg=self._fg, insertbackground=self._fg,
                             relief="flat", highlightthickness=1, highlightbackground="#555")
        hex_entry.pack(side="left", padx=(0, 6))

        if desc:
            tk.Label(
                row, text=f"  {desc}",
                font=("Helvetica", 7), fg="#888",
                bg=self._bg, anchor="w"
            ).pack(fill="x", padx=(8, 0))

        def _update_swatch(color: str):
            try:
                swatch.configure(bg=color)
            except tk.TclError:
                swatch.configure(bg="#000000")

        def _choose_color():
            color = colorchooser.askcolor(initialcolor=var.get())[1]
            if color:
                var.set(color.upper())
                _update_swatch(color)

        def _validate_hex(*_):
            text = var.get().strip().upper()
            if text.startswith("#") and len(text) in (4, 7):
                _update_swatch(text)
            self._refresh_preview()

        swatch.bind("<Button-1>", lambda _: _choose_color())
        hex_entry.bind("<FocusOut>", _validate_hex)
        hex_entry.bind("<Return>", _validate_hex)

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=15)

    def _render_core(self, parent):
        section_title(parent, "CORE — Fondos y Textos", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for key, value in self._core_colors().items():
            self._color_row(parent, key, self._make_label(key), value,
                            self._make_desc(key, "Global"))

    def _core_colors(self) -> Dict[str, str]:
        g = self._data_colors.get("global", {})
        layout = g.get("layout", {})
        core: Dict[str, str] = {}
        for k in ["background", "bg_dark", "bg_medium", "bg_sidebar", "dialog_bg", "bg_terminal"]:
            if k in g:
                core[f"global.{k}"] = g[k]
        if "app_background" in layout:
            core["global.layout.app_background"] = layout["app_background"]
        if "sidebar_background" in layout:
            core["global.layout.sidebar_background"] = layout["sidebar_background"]
        for k in ["text_white", "text_gray", "text_disabled", "dialog_text", "text_matrix"]:
            if k in g:
                core[f"global.{k}"] = g[k]
        pob = layout.get("print_on_button", {})
        if "border" in pob:
            core["global.layout.print_on_button.border"] = pob["border"]
        return core

    def _render_semantic(self, parent):
        section_title(parent, "SEMÁNTICA — Success/Warning/Error/Info", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for key, value in self._semantic_colors().items():
            self._color_row(parent, key, self._make_label(key), value,
                            self._make_desc(key, "Global"))

    def _semantic_colors(self) -> Dict[str, str]:
        g = self._data_colors.get("global", {})
        sem: Dict[str, str] = {}
        for k in ["success", "success_hover", "error", "error_hover",
                  "warning", "warning_hover", "info", "info_hover"]:
            if k in g:
                sem[f"global.{k}"] = g[k]
        return sem

    def _render_tpv(self, parent):
        section_title(parent, "TPV — Sub-secciones", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        tpv_data = self._data_colors.get("tpv", {})
        for label, section_key in _TPV_SECTIONS:
            section_data = tpv_data.get(section_key, {})
            if not section_data:
                continue
            self._sub_header(parent, label)
            flat: Dict[str, str] = {}
            self._flatten_colors(flat, f"tpv.{section_key}", section_data)
            for key, value in flat.items():
                self._color_row(parent, key, self._make_label(key), value,
                                self._make_desc(key, f"TPV > {label}"))

    def _render_modules(self, parent):
        section_title(parent, "MÓDULOS — Paletas por módulo", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        for name in ["almacen", "clientes", "produccion", "informes", "config"]:
            data = self._data_colors.get(name, {})
            if not data:
                continue
            display_name = _MODULE_NAMES.get(name, name.title())
            self._sub_header(parent, display_name)
            flat: Dict[str, str] = {}
            self._flatten_colors(flat, name, data)
            for key, value in flat.items():
                self._color_row(parent, key, self._make_label(key), value,
                                self._make_desc(key, display_name))

    def _flatten_colors(self, out: Dict[str, str], prefix: str, data: Dict[str, Any]):
        for key, value in data.items():
            if key in _NON_COLOR_KEYS:
                continue
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and value.startswith("#"):
                out[full] = value
            elif isinstance(value, dict):
                self._flatten_colors(out, full, value)

    def _get_val(self, key: str, fallback: str = "#000000") -> str:
        var = self._values.get(key)
        if var:
            v = var.get().strip()
            if v.startswith("#") and len(v) in (4, 7):
                return v
        return fallback

    def _render_preview(self, parent):
        section_title(parent, "PREVIEW EN VIVO", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        self._preview_bg = tk.Label(parent, text="Fondo App", font=("Helvetica", 11),
                                     width=25, height=2, relief="solid", bd=1)
        self._preview_bg.pack(fill="x", padx=10, pady=4)

        self._preview_label = tk.Label(parent, text="Texto principal",
                                        font=("Helvetica", 12, "bold"))
        self._preview_label.pack(fill="x", padx=10, pady=4)

        self._preview_label2 = tk.Label(parent, text="Texto secundario",
                                         font=("Helvetica", 10))
        self._preview_label2.pack(fill="x", padx=10, pady=4)

        self._sub_header(parent, "TPV")

        self._preview_btn_primary = ctk.CTkButton(parent, text="Buscar Artículo",
                                                  width=200, height=35)
        self._preview_btn_primary.pack(pady=6, padx=10)

        self._preview_btn_secondary = ctk.CTkButton(parent, text="Config",
                                                    width=200, height=35)
        self._preview_btn_secondary.pack(pady=6, padx=10)

        self._preview_btn_danger = ctk.CTkButton(parent, text="Cierre",
                                                 width=200, height=35)
        self._preview_btn_danger.pack(pady=6, padx=10)

        self._sub_header(parent, "Módulos")

        self._preview_btn_almacen = ctk.CTkButton(parent, text="Almacén",
                                                   width=200, height=30)
        self._preview_btn_almacen.pack(pady=4, padx=10)

        self._preview_btn_clientes = ctk.CTkButton(parent, text="Clientes",
                                                    width=200, height=30)
        self._preview_btn_clientes.pack(pady=4, padx=10)

        self._preview_btn_produccion = ctk.CTkButton(parent, text="Producción",
                                                      width=200, height=30)
        self._preview_btn_produccion.pack(pady=4, padx=10)

        self._sub_header(parent, "Semántica")

        self._preview_success = tk.Label(parent, text="✓ Success",
                                          font=("Helvetica", 11, "bold"), width=25, height=1)
        self._preview_success.pack(fill="x", padx=10, pady=4)

        self._preview_warning = tk.Label(parent, text="⚠ Warning",
                                          font=("Helvetica", 11, "bold"), width=25, height=1)
        self._preview_warning.pack(fill="x", padx=10, pady=4)

        self._preview_error = tk.Label(parent, text="✕ Error",
                                        font=("Helvetica", 11, "bold"), width=25, height=1)
        self._preview_error.pack(fill="x", padx=10, pady=4)

        self._preview_info = tk.Label(parent, text="ℹ Info",
                                       font=("Helvetica", 11, "bold"), width=25, height=1)
        self._preview_info.pack(fill="x", padx=10, pady=4)

        self._refresh_preview()

    def _refresh_preview(self):
        bg = self._get_val("global.background", self._bg)
        text_white = self._get_val("global.text_white", self._fg)
        text_gray = self._get_val("global.text_gray", "#CCCCCC")
        success = self._get_val("global.success", "#2ecc71")
        warning = self._get_val("global.warning", "#f39c12")
        error = self._get_val("global.error", "#e74c3c")
        info = self._get_val("global.info", "#3498db")

        btn_primary_bg = self._get_val("tpv.grid_buttons.buscar_articulo.bg", success)
        btn_primary_text = self._get_val("tpv.grid_buttons.buscar_articulo.text", "#000000")
        btn_secondary_bg = self._get_val("tpv.grid_buttons.config.bg", info)
        btn_secondary_text = self._get_val("tpv.grid_buttons.config.text", "#FFFFFF")
        btn_danger_bg = self._get_val("tpv.grid_buttons.cierre.bg", error)
        btn_danger_text = self._get_val("tpv.grid_buttons.cierre.text", "#FFFFFF")

        alm_bg = self._get_val("almacen.primary", "#00FF00")
        alm_text = self._get_val("almacen.buttons.primary.text", "#00FF00")
        cli_bg = self._get_val("clientes.primary", "#FFD700")
        cli_text = self._get_val("clientes.buttons.primary.text", "#000000")
        prod_bg = self._get_val("produccion.primary", "#552583")
        prod_text = self._get_val("produccion.buttons.primary.text", "#FFFFFF")

        try:
            self._preview_bg.configure(bg=bg, fg=text_white)
            self._preview_label.configure(bg=bg, fg=text_white)
            self._preview_label2.configure(bg=bg, fg=text_gray)
            self._preview_success.configure(bg=bg, fg=success)
            self._preview_warning.configure(bg=bg, fg=warning)
            self._preview_error.configure(bg=bg, fg=error)
            self._preview_info.configure(bg=bg, fg=info)
            self._preview_btn_primary.configure(fg_color=btn_primary_bg, text_color=btn_primary_text)
            self._preview_btn_secondary.configure(fg_color=btn_secondary_bg, text_color=btn_secondary_text)
            self._preview_btn_danger.configure(fg_color=btn_danger_bg, text_color=btn_danger_text)
            self._preview_btn_almacen.configure(fg_color=alm_bg, text_color=alm_text)
            self._preview_btn_clientes.configure(fg_color=cli_bg, text_color=cli_text)
            self._preview_btn_produccion.configure(fg_color=prod_bg, text_color=prod_text)
        except tk.TclError:
            pass

    def _render_save_bar(self, parent):
        bar = tk.Frame(parent, bg=self._bg)
        bar.pack(fill="x", side=tk.BOTTOM, padx=10, pady=10)

        self._status_label = tk.Label(
            bar, text="", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        )
        self._status_label.pack(side=tk.LEFT, padx=(0, 8))

        ctk.CTkButton(
            bar, text="APLICAR", width=100, height=32,
            fg_color="#2ecc71", hover_color="#27ae60",
            command=self._on_aplicar
        ).pack(side=tk.RIGHT)

    def _on_aplicar(self):
        color_prefixes = ("global.", "tpv.", "almacen.", "produccion.", "clientes.", "informes.", "config.")
        for key, var in self._values.items():
            parts = key.split(".")
            new_val = var.get().strip().upper()
            if not (new_val.startswith("#") and len(new_val) in (4, 7)):
                continue
            if key.startswith(color_prefixes):
                self._set_nested(self._data_colors, parts, new_val)
            else:
                self._set_nested(self._data_tokens, parts, new_val)
        self.service.aplicar_cambio("colors_config", self._data_colors)
        self.service.aplicar_cambio("design_tokens", self._data_tokens)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _set_nested(self, data: Dict[str, Any], keys: list, value: str):
        d = data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                return
            d = d[k]
        if keys[-1] in d:
            d[keys[-1]] = value
