"""Tab TIPOGRAFÍA del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict, List, Tuple

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class TypographyTab:
    """Muestra y edita la configuración de fuentes desde font_config.json."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._preview_labels: Dict[str, tk.Label] = {}
        self._build()

    def _build(self):
        self._data = self.service.cargar_json("font_config")

        main = tk.Frame(self.parent, bg=self._bg)
        main.pack(fill=tk.BOTH, expand=True)

        left = ctk.CTkScrollableFrame(main, fg_color=self._bg, width=550)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(main, bg=self._bg, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        section_title(left, "Tipografía — font_config.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )
        self._render_tokens(left, self._data)

        self._render_preview_panel(right)

    _SKIP_KEYS = {"components", "scale"}

    def _render_tokens(self, parent, data: Dict[str, Any], prefix: str = ""):
        """Renderiza recursivamente todos los tokens de fuente encontrados."""
        for key, value in data.items():
            if key in self._SKIP_KEYS:
                continue
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                has_font_keys = any(
                    k in value for k in ("family", "size", "weight")
                )
                if has_font_keys:
                    self._font_row(parent, full_key, value)
                else:
                    tk.Label(
                        parent, text=full_key,
                        font=("Helvetica", 11, "bold"),
                        fg="#3498db", bg=self._bg, anchor="w", justify="left"
                    ).pack(fill="x", padx=10, pady=(8, 2))
                    self._render_tokens(parent, value, full_key)
            elif isinstance(value, (int, float)):
                tk.Label(
                    parent, text=f"{full_key}: {value}",
                    font=("Helvetica", 10), fg=self._fg, bg=self._bg,
                    anchor="w", justify="left"
                ).pack(fill="x", padx=10, pady=1)
            elif isinstance(value, list):
                tk.Label(
                    parent, text=f"{full_key}: {', '.join(str(v) for v in value)}",
                    font=("Helvetica", 10), fg=self._fg, bg=self._bg,
                    anchor="w", justify="left"
                ).pack(fill="x", padx=10, pady=1)

    _FONT_FAMILIES = sorted({
        "Courier New", "Menlo", "DejaVu Sans Mono", "Arial", "Helvetica",
        "Times New Roman", "Georgia", "Verdana", "Tahoma", "Trebuchet MS",
        "Monaco", "Consolas", "Liberation Mono", "Ubuntu Mono",
    })

    _WEIGHTS = ["normal", "bold"]

    _TOKEN_DESC = {
        "default": "Fuente base de toda la app. Si cambias esta, se refleja en todos los textos que no tengan un token específico.",
        "label": "Etiquetas de formularios en todos los módulos (Almacén, Clientes, Config...). Ej: 'Nombre', 'SKU', 'Precio'.",
        "entry": "Campos de entrada de texto en formularios. Ej: donde escribes el nombre de un producto o cliente.",
        "title": "Títulos principales de cada vista. Ej: 'ALMACÉN', 'CLIENTES', 'TPV' en la cabecera.",
        "subtitle": "Subtítulos de sección dentro de las vistas. Ej: 'Crear producto', 'Búsqueda avanzada'.",
        "breadcrumb": "Migas de pan de navegación. Ej: 'Inicio > TPV > Buscar artículo'.",
        "caption": "Texto pequeño de ayuda o notas informativas bajo campos y botones.",
        "large": "Texto grande destacado. Ej: mensajes de confirmación, totales en informes.",
        "button": "Texto de botones genéricos en toda la app. Ej: 'Guardar', 'Cancelar', 'Aceptar'.",
        "app.base_font": "Fuente base de la app (override del default). Afecta a todos los textos generales.",
        "app.nav_button": "Botones de navegación lateral (barra izquierda). Ej: 'TPV', 'ALMACÉN', 'CONFIG'.",
        "app.tpv_large": "Número grande del total en el TPV. Ej: '60,00 €' en el ticket.",
        "app.print_on": "Texto del botón 'IMPRIMIR' en el TPV.",
    }

    def _font_row(self, parent, key: str, font_data: Dict[str, Any]):
        family = font_data.get("family", "Courier New")
        size = font_data.get("size", 14)
        weight = font_data.get("weight", "normal")

        container = tk.Frame(parent, bg=self._bg)
        container.pack(fill="x", padx=10, pady=5)

        row = tk.Frame(container, bg=self._bg)
        row.pack(fill="x")

        tk.Label(
            row, text=key, font=("Helvetica", 10, "bold"), fg="#3498db",
            bg=self._bg, width=35, anchor="w"
        ).pack(side="left", padx=(0, 8))

        fam_var = tk.StringVar(value=str(family))
        size_var = tk.StringVar(value=str(size))
        weight_var = tk.StringVar(value=str(weight))

        self._values[f"{key}.family"] = fam_var
        self._values[f"{key}.size"] = size_var
        self._values[f"{key}.weight"] = weight_var

        ctk.CTkOptionMenu(
            row, variable=fam_var, values=self._FONT_FAMILIES, width=140
        ).pack(side="left", padx=(0, 6))

        size_spin = tk.Spinbox(
            row, from_=6, to=72, increment=1, textvariable=size_var,
            width=5, font=("Helvetica", 10), justify="right"
        )
        size_spin.pack(side="left", padx=(0, 6))

        ctk.CTkOptionMenu(
            row, variable=weight_var, values=self._WEIGHTS, width=80
        ).pack(side="left", padx=(0, 6))

        preview_lbl = tk.Label(row, text="AaBbCc", fg=self._fg, bg=self._bg, width=12)
        preview_lbl.pack(side="left")

        desc = self._TOKEN_DESC.get(key, "")
        if desc:
            tk.Label(
                container, text=desc,
                font=("Helvetica", 9), fg="#95a5a6", bg=self._bg,
                anchor="w", justify="left", wraplength=520
            ).pack(fill="x", padx=(0, 5), pady=(2, 0))

        def _update_preview(*_):
            f = fam_var.get()
            s = size_var.get()
            w = weight_var.get()
            try:
                sz = int(float(s))
                preview_lbl.configure(font=(f, sz, w))
            except (tk.TclError, ValueError):
                preview_lbl.configure(font=("Courier New", 14, "normal"))

        fam_var.trace_add("write", _update_preview)
        size_var.trace_add("write", _update_preview)
        weight_var.trace_add("write", _update_preview)
        _update_preview()

        def _update_panel(*_):
            self._refresh_preview_panel(key, fam_var, size_var, weight_var)
        fam_var.trace_add("write", _update_panel)
        size_var.trace_add("write", _update_panel)
        weight_var.trace_add("write", _update_panel)

    _PREVIEW_TEXTS = {
        "default": "El rápido zorro marrón salta sobre el perro perezoso.",
        "label": "Etiqueta de ejemplo",
        "entry": "Texto de entrada...",
        "title": "TÍTULO PRINCIPAL",
        "subtitle": "Subtítulo de sección",
        "breadcrumb": "Inicio > TPV > Buscar",
        "caption": "Texto pequeño de ayuda",
        "large": "TEXTO GRANDE",
        "button": "BOTÓN",
        "app.base_font": "Fuente base de la app",
        "app.nav_button": "NAVEGACIÓN",
        "app.tpv_large": "60€",
        "app.print_on": "IMPRIMIR",
    }

    def _render_preview_panel(self, parent):
        section_title(parent, "PREVIEW DE TOKENS", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        scroll = ctk.CTkScrollableFrame(parent, fg_color=self._bg, height=500)
        scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._render_save_bar(parent)

        for key in self._values:
            if not key.endswith(".family"):
                continue
            token_key = key.rsplit(".", 1)[0]
            text = self._PREVIEW_TEXTS.get(token_key, token_key)

            row = tk.Frame(scroll, bg=self._bg)
            row.pack(fill="x", padx=5, pady=4)

            tk.Label(
                row, text=token_key, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w", width=30
            ).pack(fill="x")

            lbl = tk.Label(row, text=text, fg=self._fg, bg=self._bg, anchor="w", wraplength=270, justify="left")
            lbl.pack(fill="x", padx=(0, 5))
            self._preview_labels[token_key] = lbl

        self._refresh_all_previews()

    def _refresh_all_previews(self):
        for token_key, lbl in self._preview_labels.items():
            fam_var = self._values.get(f"{token_key}.family")
            size_var = self._values.get(f"{token_key}.size")
            weight_var = self._values.get(f"{token_key}.weight")
            if fam_var and size_var and weight_var:
                self._apply_font(lbl, fam_var.get(), size_var.get(), weight_var.get())

    def _refresh_preview_panel(self, token_key: str, fam_var, size_var, weight_var):
        lbl = self._preview_labels.get(token_key)
        if lbl:
            self._apply_font(lbl, fam_var.get(), size_var.get(), weight_var.get())

    def _apply_font(self, lbl, family, size_str, weight):
        try:
            sz = int(float(size_str))
            lbl.configure(font=(family, sz, weight))
        except (tk.TclError, ValueError):
            lbl.configure(font=("Courier New", 14, "normal"))

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
        for key, var in self._values.items():
            parts = key.split(".")
            field = parts[-1]
            token_parts = parts[:-1]
            new_val = var.get().strip()
            if field == "size":
                try:
                    new_val = int(float(new_val))
                except ValueError:
                    continue
            self._set_nested(self._data, token_parts, field, new_val)
        self.service.aplicar_cambio("font_config", self._data)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _set_nested(self, data: Dict[str, Any], token_parts: list, field: str, value: Any):
        d = data
        for k in token_parts:
            if k not in d or not isinstance(d[k], dict):
                return
            d = d[k]
        if isinstance(d, dict) and field in d:
            d[field] = value
