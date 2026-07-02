"""Tab NAV LIST del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class NavListTab:
    """Muestra y edita la configuración de nav_list desde 3 JSONs:
    layout_config.json, colors_config.json, font_config.json.
    """

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._layout: Dict[str, Any] = {}
        self._colors: Dict[str, Any] = {}
        self._fonts: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._build()

    def _build(self):
        self._layout = self.service.cargar_json("layout_config")
        self._colors = self.service.cargar_json("colors_config")
        self._fonts = self.service.cargar_json("font_config")

        scroll = ctk.CTkScrollableFrame(self.parent, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        section_title(scroll, "Nav List — 3 archivos de config", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        self._render_editor(scroll)
        self._separator(scroll)
        self._render_preview(scroll)
        self._separator(scroll)
        self._render_fonts_section(scroll)
        self._separator(scroll)
        self._render_colors_modules(scroll)
        self._separator(scroll)
        self._render_carrito_colors(scroll)
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
        int_fields = {
            "row_height", "header_height", "wraplength", "size",
            "producto", "cantidad", "precio", "total",
        }
        bool_fields = {"use_zebra"}

        for key, var in self._values.items():
            parts = key.split(".")
            new_val = var.get().strip()
            last = parts[-1]

            if last in int_fields:
                try:
                    new_val = int(float(new_val))
                except ValueError:
                    continue
            elif last in bool_fields:
                new_val = new_val == "True"

            if key.startswith("layout."):
                self._set_nested(self._layout, parts[1:], new_val)
            elif key.startswith("colors."):
                self._set_nested(self._colors, parts[1:], new_val)
            elif key.startswith("fonts."):
                self._set_nested(self._fonts, parts[1:], new_val)

        self.service.aplicar_cambio("layout_config", self._layout)
        self.service.aplicar_cambio("colors_config", self._colors)
        self.service.aplicar_cambio("font_config", self._fonts)
        self._status_label.configure(text="✓ Guardado (3 archivos)", fg="#2ecc71")

    def _set_nested(self, data: Dict[str, Any], keys: list, value: Any):
        d = data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                return
            d = d[k]
        if keys[-1] in d:
            d[keys[-1]] = value

    # ── EDITOR ───────────────────────────────────────────────────

    def _render_editor(self, parent):
        self._section_header(parent, "EDITOR", "#3498db")

        # --- Nav List (layout_config.json) ---
        tk.Label(
            parent, text="  Nav List",
            font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(6, 1))

        nav_list = self._layout.get("components", {}).get("nav_list", {})

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("row_height", "Row Height"),
            ("header_height", "Header Height"),
            ("wraplength", "Wraplength"),
        ]):
            val = nav_list.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"layout.components.nav_list.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=var, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

        # --- Carrito Nav List (layout_config.json) ---
        tk.Label(
            parent, text="  Carrito Nav List",
            font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 1))

        cnl = self._layout.get("modules", {}).get("tpv", {}).get("carrito_nav_list", {})

        cnl_row = tk.Frame(parent, bg=self._bg)
        cnl_row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("row_height", "Row Height"),
            ("wraplength", "Wraplength"),
        ]):
            val = cnl.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"layout.modules.tpv.carrito_nav_list.{field}"] = var

            col = tk.Frame(cnl_row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#f39c12", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=var, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

        # --- Column Widths ---
        col_widths = cnl.get("column_widths", {})

        tk.Label(
            parent, text="  Column Widths del Carrito",
            font=("Helvetica", 9, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(6, 1))

        cw_row = tk.Frame(parent, bg=self._bg)
        cw_row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("producto", "Producto"),
            ("cantidad", "Cantidad"),
            ("precio", "Precio"),
            ("total", "Total"),
        ]):
            val = col_widths.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"layout.modules.tpv.carrito_nav_list.column_widths.{field}"] = var

            col = tk.Frame(cw_row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#f39c12", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=var, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    # ── PREVIEW ──────────────────────────────────────────────────

    def _render_preview(self, parent):
        self._section_header(parent, "PREVIEW — MINI TABLA", "#2ecc71")

        preview_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        preview_frame.pack(fill="x", padx=10, pady=4)
        self._preview_frame = preview_frame

        self._preview_info = tk.Label(
            parent, text="", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w"
        )
        self._preview_info.pack(fill="x", padx=10, pady=2)

        self._refresh_preview()

        for key in [
            "layout.modules.tpv.carrito_nav_list.column_widths.producto",
            "layout.modules.tpv.carrito_nav_list.column_widths.cantidad",
            "layout.modules.tpv.carrito_nav_list.column_widths.precio",
            "layout.modules.tpv.carrito_nav_list.column_widths.total",
            "layout.modules.tpv.carrito_nav_list.row_height",
            "layout.modules.tpv.carrito_nav_list.wraplength",
            "layout.components.nav_list.row_height",
            "layout.components.nav_list.header_height",
        ]:
            v = self._values.get(key)
            if v:
                v.trace_add("write", lambda *_: self._refresh_preview())

    def _refresh_preview(self):
        frame = getattr(self, "_preview_frame", None)
        if not frame:
            return
        for w in frame.winfo_children():
            w.destroy()

        def _int(key, default=0):
            v = self._values.get(key)
            try:
                return int(float(v.get().strip())) if v else default
            except ValueError:
                return default

        pw = _int("layout.modules.tpv.carrito_nav_list.column_widths.producto", 240)
        cw = _int("layout.modules.tpv.carrito_nav_list.column_widths.cantidad", 50)
        prw = _int("layout.modules.tpv.carrito_nav_list.column_widths.precio", 80)
        tw = _int("layout.modules.tpv.carrito_nav_list.column_widths.total", 100)
        rh = _int("layout.modules.tpv.carrito_nav_list.row_height", 35)
        hh = _int("layout.components.nav_list.header_height", 40)
        wl = _int("layout.modules.tpv.carrito_nav_list.wraplength", 170)

        total_w = pw + cw + prw + tw
        scale = 280 / max(total_w, 1)

        sp = max(1, int(pw * scale))
        sc = max(1, int(cw * scale))
        spr = max(1, int(prw * scale))
        st = max(1, int(tw * scale))
        srh = max(12, int(rh * scale * 0.5))
        shh = max(12, int(hh * scale * 0.5))

        # Header
        header = tk.Frame(frame, bg="#0d0d0d", height=shh)
        header.pack(fill="x")
        header.pack_propagate(False)

        for text, w, anchor in [
            ("Producto", sp, "w"), ("Cant", sc, "center"),
            ("Precio", spr, "e"), ("Total", st, "e"),
        ]:
            tk.Label(
                header, text=text, font=("Helvetica", 8, "bold"),
                fg="#3498db", bg="#0d0d0d", anchor=anchor, width=w // 7
            ).pack(side="left", padx=1)

        # Dummy rows
        dummy_data = [
            ("Camiseta Negra XL", "2x", "15.00€", "30.00€", False),
            ("Taza personalizada", "1x", "8.50€", "8.50€", True),
            ("Póster A3", "3x", "5.00€", "15.00€", False),
            ("Llavero metálico", "5x", "3.20€", "16.00€", True),
        ]

        for producto, cant, precio, total, zebra in dummy_data:
            bg = "#0D0D0D" if zebra else "#1a1a1a"
            r = tk.Frame(frame, bg=bg, height=srh)
            r.pack(fill="x")
            r.pack_propagate(False)

            for text, w, anchor in [
                (producto, sp, "w"), (cant, sc, "center"),
                (precio, spr, "e"), (total, st, "e"),
            ]:
                display = text if len(text) * 7 <= w else text[:max(1, w // 7 - 1)] + "…"
                tk.Label(
                    r, text=display, font=("Helvetica", 8),
                    fg="#e0e0e0", bg=bg, anchor=anchor, width=w // 7
                ).pack(side="left", padx=1)

        info = getattr(self, "_preview_info", None)
        if info:
            info.configure(
                text=f"Total: {total_w}px (scaled {280}px)  |  Row: {rh}px  Header: {hh}px  Wrap: {wl}px"
            )

    # ── FONTS (font_config.json) ─────────────────────────────────

    def _render_fonts_section(self, parent):
        self._section_header(parent, "FUENTES — font_config.json", "#9b59b6")

        nav_list_fonts = self._fonts.get("components", {}).get("nav_list", {})

        for font_key in ["header", "row"]:
            font_data = nav_list_fonts.get(font_key, {})
            if not isinstance(font_data, dict):
                continue

            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=20, pady=2)

            tk.Label(
                row, text=font_key, font=("Helvetica", 10, "bold"),
                fg="#95a5a6", bg=self._bg, anchor="w", width=12
            ).pack(side="left", padx=(0, 4))

            for field, default in [("family", "Courier New"), ("size", 12), ("weight", "bold")]:
                val = font_data.get(field, default)
                var = tk.StringVar(value=str(val))
                self._values[f"fonts.components.nav_list.{font_key}.{field}"] = var

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

    # ── COLORES POR MÓDULO (colors_config.json) ──────────────────

    def _render_colors_modules(self, parent):
        self._section_header(parent, "COLORES POR MÓDULO — colors_config.json", "#e74c3c")

        module_names = ["almacen", "clientes", "informes", "shopify", "config", "produccion"]

        for mod in module_names:
            mod_colors = self._colors.get(mod, {})
            nav_list_c = mod_colors.get("nav_list", {})
            if not nav_list_c:
                continue

            tk.Label(
                parent, text=f"  {mod.upper()}",
                font=("Helvetica", 10, "bold"),
                fg="#e74c3c", bg=self._bg, anchor="w"
            ).pack(fill="x", padx=10, pady=(6, 1))

            color_fields = [
                ("row_normal_bg", "Normal BG"),
                ("row_normal_text", "Normal Text"),
                ("row_zebra_bg", "Zebra BG"),
                ("row_hover_bg", "Hover BG"),
                ("row_hover_text", "Hover Text"),
                ("row_selected_bg", "Selected BG"),
                ("row_selected_text", "Selected Text"),
            ]

            for field, label in color_fields:
                val = nav_list_c.get(field, "")
                self._color_row(parent, f"colors.{mod}.nav_list.{field}", label, val)

            use_zebra = nav_list_c.get("use_zebra", True)
            self._bool_row(parent, f"colors.{mod}.nav_list.use_zebra", "Use Zebra", use_zebra)

            sel_border = nav_list_c.get("row_selected_border", "primary")
            var = tk.StringVar(value=str(sel_border))
            self._values[f"colors.{mod}.nav_list.row_selected_border"] = var

            br_row = tk.Frame(parent, bg=self._bg)
            br_row.pack(fill="x", padx=20, pady=1)

            tk.Label(
                br_row, text="Selected Border", font=("Helvetica", 10),
                fg=self._fg, bg=self._bg, anchor="w", width=18
            ).pack(side="left", padx=(0, 4))
            ctk.CTkEntry(br_row, textvariable=var, width=100).pack(side="left")

    # ── CARRITO COLORES (colors_config.json) ─────────────────────

    def _render_carrito_colors(self, parent):
        self._section_header(parent, "CARRITO NAV LIST — COLORES", "#1abc9c")

        cnl_colors = self._colors.get("tpv", {}).get("carrito_nav_list", {})

        line_types = {
            "line_normal": ["bg", "text", "hover_bg", "selected_bg", "selected_text", "selected_border"],
            "line_descuento": ["bg", "text"],
            "line_devolucion": ["bg", "text"],
            "line_tesoro": ["bg", "text"],
            "line_tesoro_visual": ["bg", "text"],
        }

        for line_type, fields in line_types.items():
            line_data = cnl_colors.get(line_type, {})
            if not line_data:
                continue

            tk.Label(
                parent, text=f"  {line_type}",
                font=("Helvetica", 10, "bold"),
                fg="#1abc9c", bg=self._bg, anchor="w"
            ).pack(fill="x", padx=10, pady=(6, 1))

            for field in fields:
                val = line_data.get(field, "")
                if not val:
                    continue
                self._color_row(parent, f"colors.tpv.carrito_nav_list.{line_type}.{field}",
                                field.replace("_", " ").title(), val)

    # ── HELPERS ──────────────────────────────────────────────────

    def _section_header(self, parent, label: str, accent: str):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 11, "bold"),
            fg=accent, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

    def _color_row(self, parent, full_key: str, label: str, value: str):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=20, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=18
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
            ctk.CTkEntry(row, textvariable=var, width=100).pack(side="left")

    def _bool_row(self, parent, full_key: str, label: str, value: bool):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=20, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=18
        ).pack(side="left", padx=(0, 4))

        var = tk.StringVar(value=str(value))
        self._values[full_key] = var

        ctk.CTkOptionMenu(
            row, variable=var, values=["True", "False"], width=90
        ).pack(side="left")

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=10)
