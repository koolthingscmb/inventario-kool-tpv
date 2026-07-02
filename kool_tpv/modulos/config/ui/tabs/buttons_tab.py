"""Tab BOTONES del panel de configuración UI."""
import tkinter as tk
from tkinter import colorchooser
from typing import Any, Dict, List

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class ButtonsTab:
    """Muestra y edita los estilos de botones desde button_styles.json y buttons_config.json."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data_styles: Dict[str, Any] = {}
        self._data_config: Dict[str, Any] = {}
        self._tokens: Dict[str, str] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._preview_btns: Dict[str, ctk.CTkButton] = {}
        self._style_rows: Dict[str, tk.Frame] = {}
        self._system_styles: set = set()
        self._preview_test_btn: ctk.CTkButton = None
        self._preview_style_var = None
        self._build()

    def _build(self):
        self._data_styles = self.service.cargar_json("button_styles")
        self._data_config = self.service.cargar_json("buttons_config")
        self._tokens = self._load_tokens()
        self._system_styles = self._load_system_styles()

        main = tk.Frame(self.parent, bg=self._bg)
        main.pack(fill=tk.BOTH, expand=True)

        left = ctk.CTkScrollableFrame(main, fg_color=self._bg, width=550)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(main, bg=self._bg, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        header_frame = tk.Frame(left, bg=self._bg)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        section_title(header_frame, "Botones — button_styles.json", self._bg).pack(
            side="left"
        )

        ctk.CTkButton(
            header_frame, text="+ NUEVO ESTILO", width=120, height=28,
            fg_color="#2ecc71", hover_color="#27ae60",
            font=("Helvetica", 11, "bold"),
            command=self._nuevo_estilo
        ).pack(side="right")

        self._styles_container = left
        self._render_styles(left)

        self._separator(left)

        section_title(left, "Configuración — buttons_config.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        self._render_config(left)

        self._render_preview_panel(right)

    def _load_tokens(self) -> Dict[str, str]:
        tokens_data = self.service.cargar_json("design_tokens")
        flat: Dict[str, str] = {}
        self._flatten_tokens(flat, "", tokens_data)
        return flat

    def _flatten_tokens(self, out: Dict[str, str], prefix: str, data: Dict[str, Any]):
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and value.startswith("#"):
                out[key] = value
            elif isinstance(value, dict):
                self._flatten_tokens(out, full, value)

    def _render_preview_panel(self, parent):
        self._render_save_bar(parent)

        section_title(parent, "PREVIEW DE BOTÓN", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        tk.Label(
            parent, text="Selecciona un estilo:", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(5, 2))

        style_names = sorted(self._data_styles.keys())
        self._preview_style_var = tk.StringVar(value=style_names[0] if style_names else "")

        ctk.CTkOptionMenu(
            parent, variable=self._preview_style_var,
            values=style_names, width=260
        ).pack(fill="x", padx=10, pady=2)

        tk.Label(
            parent, text="Texto del botón:", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        text_var = tk.StringVar(value="BOTÓN DE PRUEBA")
        ctk.CTkEntry(parent, textvariable=text_var, width=260).pack(
            fill="x", padx=10, pady=2
        )

        preview_area = tk.Frame(parent, bg=self._bg, height=200)
        preview_area.pack(fill="x", padx=10, pady=10)
        preview_area.pack_propagate(False)

        self._preview_test_btn = ctk.CTkButton(preview_area, text="BOTÓN DE PRUEBA")
        self._preview_test_btn.place(relx=0.5, rely=0.5, anchor="center")

        info_lbl = tk.Label(
            parent, text="", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w", justify="left"
        )
        info_lbl.pack(fill="x", padx=10, pady=5)

        def _refresh_preview(*_):
            name = self._preview_style_var.get()
            if not name or name not in self._data_styles:
                return
            self._update_test_preview(name)
            style = self._data_styles[name]
            info_parts = []
            for f in ["type", "width", "height", "corner_radius", "border_width", "font_size"]:
                if f in style:
                    info_parts.append(f"{f}: {style[f]}")
            info_lbl.configure(text="\n".join(info_parts))

        def _update_text(*_):
            if self._preview_test_btn:
                self._preview_test_btn.configure(text=text_var.get())

        self._preview_style_var.trace_add("write", _refresh_preview)
        text_var.trace_add("write", _update_text)
        _refresh_preview()

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
            style_name = parts[0]
            field = parts[-1]
            if style_name not in self._data_styles:
                continue
            new_val = var.get().strip()
            if field in ["width", "height", "corner_radius", "border_width", "font_size"]:
                try:
                    new_val = int(float(new_val))
                except ValueError:
                    continue
            elif field in ["bg_token", "text_token", "hover_token", "border_token"]:
                if not new_val:
                    new_val = None
            if field in self._data_styles[style_name] or new_val is not None:
                self._data_styles[style_name][field] = new_val
        self.service.aplicar_cambio("button_styles", self._data_styles)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _update_test_preview(self, name: str):
        btn = self._preview_test_btn
        if not btn:
            return

        def _val(key):
            v = self._values.get(f"{name}.{key}")
            return v.get().strip() if v else ""

        bg_tok = _val("bg_token")
        fg_tok = _val("text_token")
        hover_tok = _val("hover_token")
        border_tok = _val("border_token")

        bg = self._token_color(bg_tok)
        fg = self._token_color(fg_tok)
        hover = self._token_color(hover_tok)
        border = self._token_color(border_tok) if border_tok else bg

        try:
            w = min(int(_val("width") or 100), 260)
        except ValueError:
            w = 100
        try:
            h = min(int(_val("height") or 36), 80)
        except ValueError:
            h = 36
        try:
            cr = int(_val("corner_radius") or 8)
        except ValueError:
            cr = 8
        try:
            bw = int(_val("border_width") or 0)
        except ValueError:
            bw = 0
        try:
            fs = min(int(_val("font_size") or 14), 24)
        except ValueError:
            fs = 14

        try:
            btn.configure(
                width=w, height=h, corner_radius=cr,
                fg_color=bg, text_color=fg,
                border_width=bw if border_tok else 0,
                border_color=border,
                hover_color=hover,
                font=("Courier New", fs, "bold")
            )
        except tk.TclError:
            pass

    def _load_system_styles(self) -> set:
        refs = set()
        cfg = self._data_config
        for section in ["buttons", "main_menu", "global_buttons"]:
            items = cfg.get(section, [])
            if isinstance(items, list):
                for item in items:
                    sk = item.get("style_key") or item.get("color_key")
                    if sk:
                        refs.add(sk)
        buscar = cfg.get("buscar_overlay", {})
        for k, v in buscar.items():
            if isinstance(v, list):
                for item in v:
                    sk = item.get("style_key") or item.get("color_key")
                    if sk:
                        refs.add(sk)
        return refs

    def _token_color(self, token_name: str) -> str:
        if token_name and token_name in self._tokens:
            return self._tokens[token_name]
        return "#444444"

    def _render_styles(self, parent):
        for name, style in self._data_styles.items():
            self._style_row(parent, name, style)

    def _nuevo_estilo(self):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Nuevo estilo de botón")
        dialog.geometry("360x140")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(
            dialog, text="Nombre del estilo:",
            font=("Helvetica", 12), fg=self._fg, bg=self._bg
        ).pack(pady=(20, 5))

        entry = ctk.CTkEntry(dialog, width=220, font=("Helvetica", 12))
        entry.pack(pady=5)
        entry.focus_set()

        error_lbl = tk.Label(dialog, text="", font=("Helvetica", 9), fg="#e74c3c", bg=self._bg)
        error_lbl.pack(pady=2)

        def _confirmar():
            nombre = entry.get().strip()
            if not nombre:
                error_lbl.configure(text="El nombre no puede estar vacío")
                return
            if nombre in self._data_styles:
                error_lbl.configure(text="Ya existe un estilo con ese nombre")
                return
            self._data_styles[nombre] = {
                "type": "outline",
                "bg_token": "black_base",
                "text_token": "white_base",
                "border_token": "gray_medium",
                "hover_token": "gray_light",
                "width": 120,
                "height": 40,
                "corner_radius": 8,
                "border_width": 2,
                "font_size": 14,
            }
            self.service.aplicar_cambio("button_styles", self._data_styles)
            self._style_row(self._styles_container, nombre, self._data_styles[nombre])
            dialog.destroy()

        def _on_enter(e):
            _confirmar()

        entry.bind("<Return>", _on_enter)

        ctk.CTkButton(
            dialog, text="CREAR", width=100, height=30,
            fg_color="#2ecc71", hover_color="#27ae60",
            command=_confirmar
        ).pack(pady=5)

    _TOKEN_NAMES: List[str] = []

    def _style_row(self, parent, name: str, style: Dict[str, Any]):
        outer = tk.Frame(parent, bg=self._bg)
        outer.pack(fill="x", padx=10, pady=4)
        self._style_rows[name] = outer

        header = tk.Frame(outer, bg=self._bg)
        header.pack(fill="x")

        tk.Label(
            header, text=name, font=("Helvetica", 11, "bold"),
            fg="#3498db", bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 8))

        type_var = tk.StringVar(value=str(style.get("type", "outline")))
        self._values[f"{name}.type"] = type_var
        ctk.CTkOptionMenu(
            header, variable=type_var, values=["outline", "solid"], width=80
        ).pack(side="left", padx=(0, 6))

        if name in self._system_styles:
            tk.Label(
                header, text="SISTEMA", font=("Helvetica", 8),
                fg="#7f8c8d", bg=self._bg
            ).pack(side="left", padx=(0, 6))
        else:
            ctk.CTkButton(
                header, text="✕", width=28, height=24,
                fg_color="#e74c3c", hover_color="#c0392b",
                font=("Helvetica", 11, "bold"),
                command=lambda n=name: self._eliminar_estilo(n)
            ).pack(side="right")

        fields_frame = tk.Frame(outer, bg=self._bg)
        fields_frame.pack(fill="x", padx=(0, 0), pady=2)

        token_names = sorted(self._tokens.keys())

        color_fields = [
            ("bg_token", "bg_color", style.get("bg_token", "")),
            ("text_token", "fg_color", style.get("text_token", "")),
            ("hover_token", "hover_color", style.get("hover_token", "")),
            ("border_token", "border_color", style.get("border_token", "")),
        ]

        col = 0
        for json_key, label, val in color_fields:
            var = tk.StringVar(value=str(val) if val else "")
            self._values[f"{name}.{json_key}"] = var

            tk.Label(
                fields_frame, text=label, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).grid(row=0, column=col, sticky="w", padx=(0, 4))

            ctk.CTkOptionMenu(
                fields_frame, variable=var, values=token_names, width=120
            ).grid(row=1, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
            col += 1

        num_fields = [
            ("border_width", style.get("border_width", 0)),
            ("corner_radius", style.get("corner_radius", 8)),
            ("width", style.get("width", style.get("min_width", 100))),
            ("height", style.get("height", 36)),
            ("font_size", style.get("font_size", 14)),
        ]

        for json_key, val in num_fields:
            var = tk.StringVar(value=str(val))
            self._values[f"{name}.{json_key}"] = var

            tk.Label(
                fields_frame, text=json_key, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).grid(row=0, column=col, sticky="w", padx=(0, 4))

            tk.Spinbox(
                fields_frame, from_=0, to=200, increment=1,
                textvariable=var, width=4, font=("Helvetica", 9), justify="right"
            ).grid(row=1, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
            col += 1

        preview_frame = tk.Frame(outer, bg=self._bg)
        preview_frame.pack(fill="x", pady=(2, 0))

        preview_btn = ctk.CTkButton(preview_frame, text=name.replace("_", " ").upper())
        preview_btn.pack(side="left", padx=(0, 4))
        self._preview_btns[name] = preview_btn

        def _update_preview(*_):
            self._update_style_preview(name)
            if self._preview_style_var and self._preview_style_var.get() == name:
                self._update_test_preview(name)
        for v in [type_var]:
            v.trace_add("write", _update_preview)
        for fk in [f"{name}.{k}" for k, _ in color_fields] + [f"{name}.{k}" for k, _ in num_fields]:
            sv = self._values.get(fk)
            if sv:
                sv.trace_add("write", _update_preview)

        self._update_style_preview(name)

    def _eliminar_estilo(self, name: str):
        if name in self._system_styles:
            return

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Eliminar estilo")
        dialog.geometry("380x120")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(
            dialog, text=f"¿Eliminar el estilo \"{name}\"?",
            font=("Helvetica", 12), fg=self._fg, bg=self._bg
        ).pack(pady=(20, 5))

        tk.Label(
            dialog, text="Esta acción no se puede deshacer.",
            font=("Helvetica", 9), fg="#e74c3c", bg=self._bg
        ).pack(pady=2)

        btns = tk.Frame(dialog, bg=self._bg)
        btns.pack(pady=10)

        def _confirmar():
            if name in self._data_styles:
                del self._data_styles[name]
            for suffix in ["type", "bg_token", "text_token", "hover_token", "border_token",
                           "border_width", "corner_radius", "width", "height", "font_size"]:
                self._values.pop(f"{name}.{suffix}", None)
            self._preview_btns.pop(name, None)
            row = self._style_rows.pop(name, None)
            if row:
                row.destroy()
            self.service.aplicar_cambio("button_styles", self._data_styles)
            dialog.destroy()

        ctk.CTkButton(
            btns, text="CANCELAR", width=90, height=28,
            fg_color="#555555", hover_color="#444444",
            command=dialog.destroy
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btns, text="ELIMINAR", width=90, height=28,
            fg_color="#e74c3c", hover_color="#c0392b",
            command=_confirmar
        ).pack(side="left", padx=4)

    def _update_style_preview(self, name: str):
        btn = self._preview_btns.get(name)
        if not btn:
            return

        def _val(key):
            v = self._values.get(f"{name}.{key}")
            return v.get().strip() if v else ""

        bg_tok = _val("bg_token")
        fg_tok = _val("text_token")
        hover_tok = _val("hover_token")
        border_tok = _val("border_token")

        bg = self._token_color(bg_tok)
        fg = self._token_color(fg_tok)
        hover = self._token_color(hover_tok)
        border = self._token_color(border_tok) if border_tok else bg

        try:
            w = min(int(_val("width") or 100), 150)
        except ValueError:
            w = 100
        try:
            h = min(int(_val("height") or 36), 60)
        except ValueError:
            h = 36
        try:
            cr = int(_val("corner_radius") or 8)
        except ValueError:
            cr = 8
        try:
            bw = int(_val("border_width") or 0)
        except ValueError:
            bw = 0
        try:
            fs = min(int(_val("font_size") or 14), 18)
        except ValueError:
            fs = 14

        try:
            btn.configure(
                width=w, height=h, corner_radius=cr,
                fg_color=bg, text_color=fg,
                border_width=bw if border_tok else 0,
                border_color=border,
                hover_color=hover,
                font=("Courier New", fs, "bold")
            )
        except tk.TclError:
            pass

    def _render_config(self, parent):
        for section_name in ["buttons", "main_menu", "global_buttons"]:
            if section_name not in self._data_config:
                continue
            tk.Label(
                parent, text=f"[{section_name}]",
                font=("Helvetica", 11, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(fill="x", padx=10, pady=(8, 2))

            items = self._data_config[section_name]
            if isinstance(items, list):
                for item in items:
                    self._config_item_row(parent, item)
            elif isinstance(items, dict):
                for k, v in items.items():
                    tk.Label(
                        parent, text=f"  {k}: {v}",
                        font=("Helvetica", 10), fg=self._fg, bg=self._bg, anchor="w"
                    ).pack(fill="x", padx=10, pady=1)

        buscar = self._data_config.get("buscar_overlay", {})
        if buscar:
            tk.Label(
                parent, text="[buscar_overlay]",
                font=("Helvetica", 11, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(fill="x", padx=10, pady=(8, 2))
            for k, v in buscar.items():
                if isinstance(v, list):
                    for item in v:
                        self._config_item_row(parent, item)
                else:
                    tk.Label(
                        parent, text=f"  {k}: {v}",
                        font=("Helvetica", 10), fg=self._fg, bg=self._bg, anchor="w"
                    ).pack(fill="x", padx=10, pady=1)

    def _config_item_row(self, parent, item: Dict[str, Any]):
        label = item.get("label", item.get("text", item.get("id", "?")))
        style_key = item.get("style_key", item.get("color_key", ""))
        command = item.get("command", "")
        grid = item.get("grid", {})

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=1)

        tk.Label(
            row, text=f"  {label}", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=20
        ).pack(side="left", padx=(0, 6))

        tk.Label(
            row, text=f"style: {style_key}", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w", width=20
        ).pack(side="left", padx=(0, 6))

        if grid:
            tk.Label(
                row, text=f"grid: r{grid.get('row','?')},c{grid.get('col','?')}",
                font=("Helvetica", 9), fg="#7f8c8d", bg=self._bg, anchor="w"
            ).pack(side="left", padx=(0, 6))

        tk.Label(
            row, text=f"cmd: {command}", font=("Helvetica", 9),
            fg="#7f8c8d", bg=self._bg, anchor="w"
        ).pack(side="left")

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=15)
