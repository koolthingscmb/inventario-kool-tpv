"""Tab DIÁLOGOS del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class DialogsTab:
    """Muestra y edita la configuración de diálogos desde ui_dialogs.json."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._build()

    def _build(self):
        self._data = self.service.cargar_json("ui_dialogs")

        scroll = ctk.CTkScrollableFrame(self.parent, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        section_title(scroll, "Diálogos — ui_dialogs.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        dialogs = self._data.get("dialogs", {})
        type_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "success": "#2ecc71",
            "password": "#9b59b6",
            "input": "#2ecc71",
        }
        type_icons = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✕",
            "success": "✓",
            "password": "🔒",
            "input": "✎",
        }

        for dlg_type, dlg_config in dialogs.items():
            color = type_colors.get(dlg_type, "#3498db")
            icon = type_icons.get(dlg_type, "?")
            self._render_dialog(scroll, dlg_type, dlg_config, color, icon)
            self._separator(scroll)

        self._render_save_bar(scroll)

    def _render_save_bar(self, parent):
        bar = tk.Frame(parent, bg=self._bg)
        bar.pack(fill="x", padx=10, pady=10)

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
            new_val = var.get().strip()
            for field in ["width", "height", "corner_radius", "border_width",
                          "padding_x", "padding_y", "title_bar_height", "icon_size",
                          "button_width", "button_height", "entry_width", "entry_height",
                          "size", "font_size"]:
                if parts[-1] == field:
                    try:
                        new_val = int(float(new_val))
                    except ValueError:
                        continue
                    break
            self._set_nested(self._data, parts, new_val)
        self.service.aplicar_cambio("ui_dialogs", self._data)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _set_nested(self, data: Dict[str, Any], keys: list, value: Any):
        d = data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                return
            d = d[k]
        if keys[-1] in d:
            d[keys[-1]] = value

    def _render_dialog(self, parent, dlg_type: str, config: Dict[str, Any],
                       accent_color: str, icon: str):
        outer = tk.Frame(parent, bg=self._bg)
        outer.pack(fill="x", padx=10, pady=4)

        header = tk.Frame(outer, bg=self._bg)
        header.pack(fill="x")

        tk.Label(
            header, text=f"{icon}  {dlg_type.upper()}",
            font=("Helvetica", 12, "bold"),
            fg=accent_color, bg=self._bg, anchor="w"
        ).pack(side="left")

        ctk.CTkButton(
            header, text="TEST", width=60, height=24,
            fg_color=accent_color, hover_color=accent_color,
            font=("Helvetica", 9, "bold"),
            command=lambda dt=dlg_type, ac=accent_color: self._test_dialog(dt, ac)
        ).pack(side="right")

        prefix = f"dialogs.{dlg_type}"

        if "window" in config:
            self._render_window_section(outer, f"{prefix}.window", config["window"], accent_color)
        if "colors" in config:
            self._render_colors_section(outer, f"{prefix}.colors", config["colors"], accent_color)
        if "fonts" in config:
            self._render_fonts_section(outer, f"{prefix}.fonts", config["fonts"], accent_color)
        if "spacing" in config:
            self._render_spacing_section(outer, f"{prefix}.spacing", config["spacing"], accent_color)
        if "buttons" in config:
            self._render_buttons_section(outer, f"{prefix}.buttons", config["buttons"], accent_color)

    def _test_dialog(self, dlg_type: str, accent: str):
        p = f"dialogs.{dlg_type}"

        def _val(key):
            v = self._values.get(f"{p}.{key}")
            return v.get().strip() if v else ""

        def _int(key, default=0):
            try:
                return int(float(_val(key)))
            except ValueError:
                return default

        w = _int("window.width", 400)
        h = _int("window.height", 300)
        cr = _int("window.corner_radius", 20)
        bw = _int("window.border_width", 10)
        tbh = _int("window.title_bar_height", 50)
        px = _int("window.padding_x", 10)
        py = _int("window.padding_y", 10)

        bg = _val("colors.bg") or "#000000"
        border_c = _val("colors.border") or accent
        title_c = _val("colors.title_text") or "#00FF00"
        msg_c = _val("colors.message_text") or accent
        btn_bg = _val("colors.button_bg") or accent
        btn_hover = _val("colors.button_hover") or accent
        btn_text_c = _val("colors.button_text") or "#000000"
        cancel_bg = _val("colors.cancel_bg") or accent
        cancel_hover = _val("colors.cancel_hover") or accent
        tb_bg = _val("colors.title_bar_bg") or accent
        tb_text = _val("colors.title_bar_text") or "#000000"

        title_fam = _val("fonts.title.family") or "Courier New"
        title_sz = _int("fonts.title.size", 20)
        title_wt = _val("fonts.title.weight") or "bold"
        msg_fam = _val("fonts.message.family") or "Courier New"
        msg_sz = _int("fonts.message.size", 14)
        msg_wt = _val("fonts.message.weight") or "bold"
        btn_fam = _val("fonts.button.family") or "Courier New"
        btn_sz = _int("fonts.button.size", 14)
        btn_wt = _val("fonts.button.weight") or "bold"

        accept_w = _int("buttons.accept.width", 160)
        accept_h = _int("buttons.accept.height", 55)
        accept_cr = _int("buttons.accept.corner_radius", 12)
        accept_bw = _int("buttons.accept.border_width", 10)
        accept_fs = _int("buttons.accept.font_size", 20)

        cancel_w = _int("buttons.cancel.width", 100)
        cancel_h = _int("buttons.cancel.height", 40)
        cancel_cr = _int("buttons.cancel.corner_radius", 12)
        cancel_bw = _int("buttons.cancel.border_width", 5)
        cancel_fs = _int("buttons.cancel.font_size", 12)

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(f"TEST — {dlg_type}")
        dialog.geometry(f"{w}x{h}")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.configure(fg_color=bg)

        try:
            dialog.after(50, lambda: dialog.overrideredirect(True))
        except tk.TclError:
            pass

        title_bar = tk.Frame(dialog, bg=tb_bg, height=tbh)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar, text=dlg_type.upper(),
            font=(title_fam, title_sz, title_wt),
            fg=tb_text, bg=tb_bg
        ).pack(side="left", padx=px, pady=5)

        body = tk.Frame(dialog, bg=bg)
        body.pack(fill="both", expand=True, padx=bw, pady=(0, bw))

        tk.Label(
            body, text="Título de prueba",
            font=(title_fam, title_sz, title_wt),
            fg=title_c, bg=bg
        ).pack(pady=(py + 10, 5))

        tk.Label(
            body, text="Este es un mensaje de prueba para\nver cómo se ve el diálogo.",
            font=(msg_fam, msg_sz, msg_wt),
            fg=msg_c, bg=bg, justify="center"
        ).pack(pady=5)

        if dlg_type in ("input", "password"):
            show = "*" if dlg_type == "password" else None
            ctk.CTkEntry(
                body, width=_int("window.entry_width", 300),
                height=_int("window.entry_height", 35),
                show=show, fg_color=bg, text_color=msg_c
            ).pack(pady=5)

        btns = tk.Frame(body, bg=bg)
        btns.pack(side="bottom", pady=py + 5)

        ctk.CTkButton(
            btns, text="ACEPTAR",
            width=accept_w, height=accept_h,
            corner_radius=accept_cr, border_width=accept_bw,
            fg_color=btn_bg, hover_color=btn_hover, text_color=btn_text_c,
            font=(btn_fam, accept_fs, btn_wt),
            command=dialog.destroy
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btns, text="CANCELAR",
            width=cancel_w, height=cancel_h,
            corner_radius=cancel_cr, border_width=cancel_bw,
            fg_color=cancel_bg, hover_color=cancel_hover, text_color=btn_text_c,
            font=(btn_fam, cancel_fs, btn_wt),
            command=dialog.destroy
        ).pack(side="left", padx=6)

    def _section_header(self, parent, label: str, accent: str):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 10, "bold"),
            fg=accent, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(6, 2))

    def _render_window_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "WINDOW", accent)
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=2)

        fields = [
            ("width", "Width"), ("height", "Height"),
            ("corner_radius", "Corner R"), ("border_width", "Border W"),
            ("padding_x", "Pad X"), ("padding_y", "Pad Y"),
            ("title_bar_height", "Title H"), ("icon_size", "Icon"),
            ("button_width", "Btn W"), ("button_height", "Btn H"),
            ("entry_width", "Entry W"), ("entry_height", "Entry H"),
        ]
        for i, (field, label) in enumerate(fields):
            if field not in data:
                continue
            val = data[field]
            var = tk.StringVar(value=str(val))
            self._values[f"{prefix}.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=3, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=1000, increment=1,
                textvariable=var, width=5, font=("Helvetica", 10), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    def _render_colors_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "COLORS", accent)
        for key, value in data.items():
            if not isinstance(value, str):
                continue
            full_key = f"{prefix}.{key}"
            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=20, pady=1)

            tk.Label(
                row, text=key, font=("Helvetica", 10),
                fg=self._fg, bg=self._bg, anchor="w", width=22
            ).pack(side="left", padx=(0, 4))

            var = tk.StringVar(value=str(value))
            self._values[full_key] = var

            if value.startswith("#") and len(value) in (4, 7):
                swatch = tk.Label(row, text="", bg=value, width=3, relief="solid", bd=1)
                swatch.pack(side="left", padx=(0, 4))

                entry = ctk.CTkEntry(row, textvariable=var, width=80)
                entry.pack(side="left")

                def _update_sw(*_, v=var, s=swatch):
                    val = v.get().strip()
                    if val.startswith("#") and len(val) in (4, 7):
                        try:
                            s.configure(bg=val)
                        except tk.TclError:
                            pass
                var.trace_add("write", _update_sw)
            else:
                ctk.CTkEntry(row, textvariable=var, width=120).pack(side="left")

    def _render_fonts_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "FONTS", accent)
        for font_key, font_data in data.items():
            if not isinstance(font_data, dict):
                continue
            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=20, pady=2)

            tk.Label(
                row, text=font_key, font=("Helvetica", 10, "bold"),
                fg="#95a5a6", bg=self._bg, anchor="w", width=12
            ).pack(side="left", padx=(0, 4))

            for field, default in [("family", "Courier New"), ("size", 14), ("weight", "bold")]:
                val = font_data.get(field, default)
                var = tk.StringVar(value=str(val))
                self._values[f"{prefix}.{font_key}.{field}"] = var

                if field == "family":
                    ctk.CTkEntry(row, textvariable=var, width=120).pack(side="left", padx=(0, 4))
                elif field == "size":
                    tk.Spinbox(
                        row, from_=6, to=72, increment=1,
                        textvariable=var, width=4, font=("Helvetica", 10), justify="right"
                    ).pack(side="left", padx=(0, 4))
                elif field == "weight":
                    ctk.CTkOptionMenu(
                        row, variable=var, values=["normal", "bold"], width=80
                    ).pack(side="left", padx=(0, 4))

    def _render_spacing_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "SPACING", accent)
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=2)

        for i, (field, label) in enumerate([
            ("icon_top", "Icon Top"), ("icon_bottom", "Icon Bot"),
            ("title_bottom", "Title Bot"), ("message_bottom", "Msg Bot"),
            ("entry_bottom", "Entry Bot"),
        ]):
            if field not in data:
                continue
            val = data[field]
            var = tk.StringVar(value=str(val))
            self._values[f"{prefix}.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=3, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=200, increment=1,
                textvariable=var, width=5, font=("Helvetica", 10), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    def _render_buttons_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "BUTTONS", accent)
        for btn_key in ["accept", "cancel"]:
            btn_data = data.get(btn_key)
            if not isinstance(btn_data, dict):
                continue

            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=20, pady=2)

            tk.Label(
                row, text=btn_key.upper(), font=("Helvetica", 9, "bold"),
                fg=accent, bg=self._bg, anchor="w", width=10
            ).pack(side="left", padx=(0, 4))

            for field, label in [
                ("width", "W"), ("height", "H"),
                ("corner_radius", "CR"), ("border_width", "BW"),
                ("font_size", "FS"),
            ]:
                if field not in btn_data:
                    continue
                val = btn_data[field]
                var = tk.StringVar(value=str(val))
                self._values[f"{prefix}.{btn_key}.{field}"] = var

                col = tk.Frame(row, bg=self._bg)
                col.pack(side="left", padx=2)

                tk.Label(
                    col, text=label, font=("Helvetica", 7),
                    fg="#95a5a6", bg=self._bg, anchor="w"
                ).pack(anchor="w")
                tk.Spinbox(
                    col, from_=0, to=500, increment=1,
                    textvariable=var, width=4, font=("Helvetica", 9), justify="right"
                ).pack(anchor="w", pady=(1, 0))

            if "style_key" in btn_data:
                sk_var = tk.StringVar(value=str(btn_data["style_key"]))
                self._values[f"{prefix}.{btn_key}.style_key"] = sk_var
                col = tk.Frame(row, bg=self._bg)
                col.pack(side="left", padx=4)
                tk.Label(
                    col, text="style_key", font=("Helvetica", 7),
                    fg="#95a5a6", bg=self._bg, anchor="w"
                ).pack(anchor="w")
                ctk.CTkEntry(col, textvariable=sk_var, width=100).pack(anchor="w", pady=(1, 0))

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=10)
