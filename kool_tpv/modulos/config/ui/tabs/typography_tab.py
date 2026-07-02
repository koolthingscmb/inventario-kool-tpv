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

    def _render_tokens(self, parent, data: Dict[str, Any], prefix: str = ""):
        """Renderiza recursivamente todos los tokens de fuente encontrados."""
        for key, value in data.items():
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

    def _font_row(self, parent, key: str, font_data: Dict[str, Any]):
        family = font_data.get("family", "Courier New")
        size = font_data.get("size", 14)
        weight = font_data.get("weight", "normal")

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=3)

        tk.Label(
            row, text=key, font=("Helvetica", 10), fg=self._fg,
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
        "components.action_button": "ACCIÓN",
        "components.dialog.title": "Diálogo",
        "components.dialog.message": "Mensaje del diálogo",
        "components.dialog.button": "Aceptar",
        "components.dialog.input": "Escriba aquí...",
        "components.nav_list.header": "Cabecera lista",
        "components.nav_list.row": "Fila de la lista",
        "modules.config.label": "Config label",
        "modules.config.entry": "Config entry",
        "modules.tpv.search_button": "BUSCAR",
        "modules.tpv.grid_button": "PRODUCTO",
        "modules.tpv.favorite_chip": "★ Favorito",
        "modules.tpv.ticket_carrito.header_info": "Ticket #1234",
        "modules.tpv.ticket_carrito.header_cliente": "Cliente: Anónimo",
        "modules.tpv.ticket_carrito.body_header": "Cant  Producto  Total",
        "modules.tpv.ticket_carrito.nav_producto": "2x Camiseta  20.00€",
        "modules.tpv.ticket_carrito.footer_labels": "TOTAL",
        "modules.tpv.ticket_carrito.footer_totales": "45.00€",
        "modules.tpv.payment_controllers.titulo": "PAGO EN EFECTIVO",
        "modules.tpv.payment_controllers.label": "Importe recibido:",
        "modules.tpv.payment_controllers.entry": "0.00€",
        "modules.tpv.payment_controllers.cambio": "Cambio: 5.00€",
        "modules.tpv.payment_controllers.button": "CONFIRMAR",
        "modules.tpv.payment_controllers.error": "Importe insuficiente",
        "modules.tpv.buscar_overlay.main_buttons": "CATEGORÍAS",
        "modules.tpv.buscar_overlay.category_buttons": "Camisetas",
        "modules.tpv.buscar_overlay.article_buttons": "Camiseta Negra XL",
        "modules.presencia.nombre": "EGON",
        "modules.presencia.accion": "ENTRADA",
        "modules.presencia.estado": "ACTIVO",
        "modules.presencia.desde": "Desde 09:15",
        "modules.presencia.historial_header": "Historial",
        "modules.presencia.historial_row": "09:15 - Entrada",
        "modules.presencia.placeholder": "Selecciona un empleado",
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
