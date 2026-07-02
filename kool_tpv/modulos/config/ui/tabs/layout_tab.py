"""Tab LAYOUT del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class LayoutTab:
    """Muestra y edita la configuración de layout desde layout_config.json."""

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
        self._data = self.service.cargar_json("layout_config")

        main = tk.Frame(self.parent, bg=self._bg)
        main.pack(fill=tk.BOTH, expand=True)

        left = ctk.CTkScrollableFrame(main, fg_color=self._bg, width=550)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(main, bg=self._bg, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        section_title(left, "Layout — layout_config.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        self._render_spacing_editor(left)
        self._separator(left)
        self._render_window_editor(left)
        self._separator(left)
        self._render_navigation_editor(left)
        self._separator(left)
        self._render_nav_list_editor(left)
        self._separator(left)
        self._render_dialog_editor(left)
        self._separator(left)
        self._render_tpv_grid_editor(left)
        self._separator(left)
        self._render_carrito_nav_list_editor(left)
        self._separator(left)
        self._render_favorites_editor(left)
        self._separator(left)

        section_title(left, "RESTO DE CONFIGURACIÓN", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        sections = [
            ("global", "GLOBAL", [
                ("keyboard_navigation", "Keyboard Navigation"),
                ("main_menu_layout", "Main Menu Layout"),
                ("power_layout", "Power Layout"),
            ]),
            ("components", "COMPONENTS", [
                ("print_on_button", "Print On Button"),
            ]),
            ("modules", "MÓDULOS", [
                ("sidebar", "Sidebar"),
                ("almacen", "Almacén"),
                ("clientes", "Clientes"),
                ("shopify", "Shopify"),
                ("config", "Config"),
                ("informes", "Informes"),
            ]),
        ]

        for top_key, top_label, subsections in sections:
            self._separator(left)
            section_title(left, top_label, self._bg).pack(
                fill="x", pady=(10, 5), padx=10
            )
            top_data = self._data.get(top_key, {})
            for sub_key, sub_label in subsections:
                sub_data = top_data.get(sub_key)
                if sub_data is None:
                    continue
                self._render_section(left, f"{top_key}.{sub_key}", sub_label, sub_data)

        self._render_preview_panel(right)
        self._render_save_bar(right)

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
            new_val = var.get().strip()
            try:
                new_val = int(float(new_val))
            except ValueError:
                continue
            self._set_nested(self._data, parts, new_val)
        self.service.aplicar_cambio("layout_config", self._data)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _set_nested(self, data: Dict[str, Any], keys: list, value: Any):
        d = data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                return
            d = d[k]
        if keys[-1] in d:
            d[keys[-1]] = value

    def _render_spacing_editor(self, parent):
        section_title(parent, "SPACING TOKENS", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        spacing = self._data.get("global", {}).get("spacing", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (token, default) in enumerate([("xs", 4), ("sm", 8), ("md", 12), ("lg", 20), ("xl", 32)]):
            val = spacing.get(token, default)
            var = tk.StringVar(value=str(val))
            self._values[f"global.spacing.{token}"] = var

            col_frame = tk.Frame(row, bg=self._bg)
            col_frame.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col_frame, text=token.upper(), font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col_frame, from_=0, to=200, increment=1,
                textvariable=var, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_, v=var, t=token):
                self._refresh_spacing_preview(t, v)
            var.trace_add("write", _on_change)

    def _render_window_editor(self, parent):
        section_title(parent, "WINDOW", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        window = self._data.get("global", {}).get("window", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([("width", "Width"), ("height", "Height"), ("min_width", "Min W"), ("min_height", "Min H")]):
            val = window.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"global.window.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col, from_=100, to=5000, increment=10,
                textvariable=var, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_):
                self._refresh_window_preview()
            var.trace_add("write", _on_change)

    def _render_navigation_editor(self, parent):
        section_title(parent, "NAVIGATION", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        nav = self._data.get("global", {}).get("navigation", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([("button_padx", "Pad X"), ("button_pady", "Pad Y")]):
            val = nav.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"global.navigation.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col, from_=0, to=100, increment=1,
                textvariable=var, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_):
                self._refresh_nav_preview()
            var.trace_add("write", _on_change)

    def _render_nav_list_editor(self, parent):
        section_title(parent, "NAV LIST", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        nav_list = self._data.get("components", {}).get("nav_list", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("row_height", "Row Height"),
            ("header_height", "Header Height"),
            ("wraplength", "Wraplength"),
        ]):
            val = nav_list.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"components.nav_list.{field}"] = var

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

            def _on_change(*_):
                self._refresh_nav_list_preview()
            var.trace_add("write", _on_change)

    def _render_dialog_editor(self, parent):
        section_title(parent, "DIALOG", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        dialog = self._data.get("components", {}).get("dialog", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("width", "Width"),
            ("height", "Height"),
            ("corner_radius", "Corner Radius"),
            ("border_width", "Border Width"),
        ]):
            val = dialog.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"components.dialog.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col, from_=0, to=1000, increment=1,
                textvariable=var, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_):
                self._refresh_dialog_preview()
            var.trace_add("write", _on_change)

    def _render_tpv_grid_editor(self, parent):
        section_title(parent, "TPV GRID", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        grid = self._data.get("modules", {}).get("tpv", {}).get("center", {}).get("grid", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("columns", "Columns"),
            ("rows", "Rows"),
            ("spacing", "Spacing"),
            ("min_button_size", "Min Button"),
            ("max_button_size", "Max Button"),
        ]):
            val = grid.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"modules.tpv.center.grid.{field}"] = var

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

            def _on_change(*_):
                self._refresh_tpv_grid_preview()
            var.trace_add("write", _on_change)

    def _render_carrito_nav_list_editor(self, parent):
        section_title(parent, "CARRITO NAV LIST", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        cnl = self._data.get("modules", {}).get("tpv", {}).get("carrito_nav_list", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("row_height", "Row Height"),
            ("wraplength", "Wraplength"),
        ]):
            val = cnl.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"modules.tpv.carrito_nav_list.{field}"] = var

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

            def _on_change(*_):
                self._refresh_cnl_preview()
            var.trace_add("write", _on_change)

        col_widths = cnl.get("column_widths", {})
        cw_row = tk.Frame(parent, bg=self._bg)
        cw_row.pack(fill="x", padx=10, pady=(6, 4))

        tk.Label(
            cw_row, text="Column Widths:", font=("Helvetica", 9, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x")

        cw_inner = tk.Frame(cw_row, bg=self._bg)
        cw_inner.pack(fill="x", padx=10, pady=2)

        for i, (field, label) in enumerate([
            ("producto", "Producto"),
            ("cantidad", "Cantidad"),
            ("precio", "Precio"),
            ("total", "Total"),
        ]):
            val = col_widths.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"modules.tpv.carrito_nav_list.column_widths.{field}"] = var

            col = tk.Frame(cw_inner, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 8),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=var, width=5, font=("Helvetica", 10), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_):
                self._refresh_cnl_preview()
            var.trace_add("write", _on_change)

    def _render_favorites_editor(self, parent):
        section_title(parent, "FAVORITES", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        fav = self._data.get("modules", {}).get("tpv", {}).get("favorites", {})
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (field, label) in enumerate([
            ("columns", "Columns"),
            ("chip_height", "Chip Height"),
            ("grid_spacing", "Grid Spacing"),
            ("max_chars_line", "Max Chars/Line"),
        ]):
            val = fav.get(field, 0)
            var = tk.StringVar(value=str(val))
            self._values[f"modules.tpv.favorites.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")

            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=var, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

            def _on_change(*_):
                self._refresh_favorites_preview()
            var.trace_add("write", _on_change)

    def _render_preview_panel(self, parent):
        section_title(parent, "PREVIEW LAYOUT", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        tk.Label(
            parent, text="Spacing:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        spacing_frame = tk.Frame(parent, bg=self._bg)
        spacing_frame.pack(fill="x", padx=10, pady=2)

        for token in ["xs", "sm", "md", "lg", "xl"]:
            lbl = tk.Label(
                spacing_frame, text=f"{token.upper()} ▸",
                font=("Helvetica", 10), fg=self._fg, bg=self._bg, anchor="w"
            )
            lbl.pack(fill="x", pady=1)
            self._preview_labels[f"spacing.{token}"] = lbl

        self._separator(parent)

        tk.Label(
            parent, text="Window:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        win_frame = tk.Frame(parent, bg=self._bg, relief="solid", bd=1)
        win_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["window.frame"] = win_frame

        win_lbl = tk.Label(
            win_frame, text="", font=("Helvetica", 10),
            fg=self._fg, bg="#1a1a1a", anchor="center"
        )
        win_lbl.pack(expand=True, fill="both", padx=4, pady=4)
        self._preview_labels["window.label"] = win_lbl

        self._separator(parent)

        tk.Label(
            parent, text="Nav List:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        nl_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        nl_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["nav_list.frame"] = nl_frame

        nl_header = tk.Label(
            nl_frame, text="HEADER", font=("Helvetica", 10, "bold"),
            fg="#3498db", bg="#1a1a1a", anchor="w"
        )
        nl_header.pack(fill="x", padx=4, pady=2)
        self._preview_labels["nav_list.header"] = nl_header

        for i, text in enumerate(["Fila 1 — Producto A", "Fila 2 — Producto B", "Fila 3 — Producto C"]):
            nl_row = tk.Label(
                nl_frame, text=text, font=("Helvetica", 9),
                fg=self._fg, bg="#222831", anchor="w"
            )
            nl_row.pack(fill="x", padx=4, pady=1)
            self._preview_labels[f"nav_list.row.{i}"] = nl_row

        self._separator(parent)

        tk.Label(
            parent, text="Dialog:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        dlg_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=2)
        dlg_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["dialog.frame"] = dlg_frame

        dlg_lbl = tk.Label(
            dlg_frame, text="", font=("Helvetica", 10),
            fg=self._fg, bg="#1a1a1a", anchor="center"
        )
        dlg_lbl.pack(expand=True, fill="both", padx=4, pady=4)
        self._preview_labels["dialog.label"] = dlg_lbl

        self._separator(parent)

        tk.Label(
            parent, text="TPV Grid:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        tg_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        tg_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["tpv_grid.frame"] = tg_frame

        tg_info = tk.Label(parent, text="", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w")
        tg_info.pack(fill="x", padx=10, pady=2)
        self._preview_labels["tpv_grid.info"] = tg_info

        self._separator(parent)

        tk.Label(
            parent, text="Carrito Nav List:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        cnl_frame = tk.Frame(parent, bg="#222831", relief="solid", bd=1)
        cnl_frame.pack(fill="x", padx=10, pady=4)

        cnl_header = tk.Frame(cnl_frame, bg="#1a1a1a")
        cnl_header.pack(fill="x")
        for i, text in enumerate(["Producto", "Cant", "Precio", "Total"]):
            lbl = tk.Label(
                cnl_header, text=text, font=("Helvetica", 8, "bold"),
                fg="#3498db", bg="#1a1a1a", anchor="w"
            )
            lbl.pack(side="left", padx=2)
            self._preview_labels[f"cnl.col.{i}"] = lbl

        cnl_info = tk.Label(parent, text="", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w")
        cnl_info.pack(fill="x", padx=10, pady=2)
        self._preview_labels["cnl.info"] = cnl_info

        self._separator(parent)

        tk.Label(
            parent, text="Favorites:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        fav_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        fav_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["favorites.frame"] = fav_frame

        fav_info = tk.Label(parent, text="", font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w")
        fav_info.pack(fill="x", padx=10, pady=2)
        self._preview_labels["favorites.info"] = fav_info

        self._separator(parent)

        tk.Label(
            parent, text="Navigation:", font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        nav_frame = tk.Frame(parent, bg=self._bg)
        nav_frame.pack(fill="x", padx=10, pady=4)
        self._preview_labels["nav.frame"] = nav_frame

        for text in ["TPV", "ALMACÉN", "CLIENTES"]:
            btn = ctk.CTkButton(nav_frame, text=text, width=100, height=32)
            btn.pack(side="left", padx=2, pady=2)
            self._preview_labels[f"nav.btn.{text}"] = btn

        self._refresh_spacing_preview_all()
        self._refresh_window_preview()
        self._refresh_nav_preview()
        self._refresh_nav_list_preview()
        self._refresh_dialog_preview()
        self._refresh_tpv_grid_preview()
        self._refresh_cnl_preview()
        self._refresh_favorites_preview()

    def _get_val(self, key: str, default: str = "0") -> str:
        v = self._values.get(key)
        return v.get().strip() if v else default

    def _get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(float(self._get_val(key, str(default))))
        except ValueError:
            return default

    def _refresh_spacing_preview(self, token: str = None, var=None):
        for t in ["xs", "sm", "md", "lg", "xl"]:
            if token and t != token:
                continue
            lbl = self._preview_labels.get(f"spacing.{t}")
            if not lbl:
                continue
            val = self._get_int(f"global.spacing.{t}", 0)
            lbl.configure(text=f"{t.upper()} ▸ {val}px  {'█' * max(1, val // 2)}")

    def _refresh_spacing_preview_all(self):
        self._refresh_spacing_preview()

    def _refresh_window_preview(self):
        w = self._get_int("global.window.width", 1600)
        h = self._get_int("global.window.height", 960)
        min_w = self._get_int("global.window.min_width", 1600)
        min_h = self._get_int("global.window.min_height", 960)

        lbl = self._preview_labels.get("window.label")
        if lbl:
            lbl.configure(text=f"{w} × {h}\n(min: {min_w} × {min_h})")

        frame = self._preview_labels.get("window.frame")
        if frame:
            scale = 280 / max(w, 1)
            fw = max(80, int(w * scale))
            fh = max(60, int(h * scale * 0.3))
            try:
                frame.configure(width=fw, height=fh)
            except tk.TclError:
                pass

    def _refresh_nav_preview(self):
        padx = self._get_int("global.navigation.button_padx", 20)
        pady = self._get_int("global.navigation.button_pady", 14)

        for text in ["TPV", "ALMACÉN", "CLIENTES"]:
            btn = self._preview_labels.get(f"nav.btn.{text}")
            if btn:
                try:
                    btn.configure(width=80 + padx * 2, height=20 + pady * 2)
                except tk.TclError:
                    pass

    def _refresh_nav_list_preview(self):
        row_h = self._get_int("components.nav_list.row_height", 35)
        header_h = self._get_int("components.nav_list.header_height", 40)
        wrap = self._get_int("components.nav_list.wraplength", 180)

        frame = self._preview_labels.get("nav_list.frame")
        if frame:
            try:
                frame.configure(height=header_h + row_h * 3 + 8)
            except tk.TclError:
                pass

        header = self._preview_labels.get("nav_list.header")
        if header:
            try:
                header.configure(height=header_h, wraplength=wrap)
            except tk.TclError:
                pass

        for i in range(3):
            row = self._preview_labels.get(f"nav_list.row.{i}")
            if row:
                try:
                    row.configure(height=row_h, wraplength=wrap)
                except tk.TclError:
                    pass

    def _refresh_dialog_preview(self):
        w = self._get_int("components.dialog.width", 400)
        h = self._get_int("components.dialog.height", 300)
        cr = self._get_int("components.dialog.corner_radius", 20)
        bw = self._get_int("components.dialog.border_width", 10)

        frame = self._preview_labels.get("dialog.frame")
        if frame:
            scale = 260 / max(w, 1)
            fw = max(80, int(w * scale))
            fh = max(60, int(h * scale))
            try:
                frame.configure(width=fw, height=fh, corner_radius=cr)
            except tk.TclError:
                pass

        lbl = self._preview_labels.get("dialog.label")
        if lbl:
            try:
                lbl.configure(text=f"{w} × {h}\ncr: {cr}  bw: {bw}")
            except tk.TclError:
                pass

    def _refresh_tpv_grid_preview(self):
        cols = self._get_int("modules.tpv.center.grid.columns", 4)
        rows = self._get_int("modules.tpv.center.grid.rows", 4)
        spacing = self._get_int("modules.tpv.center.grid.spacing", 12)

        frame = self._preview_labels.get("tpv_grid.frame")
        if not frame:
            return
        for w in frame.winfo_children():
            w.destroy()

        scale = 260 / max(cols * 60 + (cols - 1) * spacing, 1)
        btn_w = max(20, int(60 * scale))
        btn_h = max(15, int(40 * scale))
        sp = max(1, int(spacing * scale))

        for r in range(min(rows, 4)):
            for c in range(min(cols, 6)):
                chip = tk.Label(
                    frame, text="", bg="#00FF00", relief="solid", bd=1,
                    width=btn_w // 7, height=btn_h // 14
                )
                chip.grid(row=r, column=c, padx=sp // 2, pady=sp // 2)

        info = self._preview_labels.get("tpv_grid.info")
        if info:
            info.configure(text=f"{cols} cols × {rows} rows\nspacing: {spacing}px")

    def _refresh_cnl_preview(self):
        rh = self._get_int("modules.tpv.carrito_nav_list.row_height", 35)
        pw = self._get_int("modules.tpv.carrito_nav_list.column_widths.producto", 240)
        cw = self._get_int("modules.tpv.carrito_nav_list.column_widths.cantidad", 50)
        prw = self._get_int("modules.tpv.carrito_nav_list.column_widths.precio", 80)
        tw = self._get_int("modules.tpv.carrito_nav_list.column_widths.total", 100)

        for i, (text, w) in enumerate([
            ("Producto A", pw), ("2x", cw), ("10.00€", prw), ("20.00€", tw)
        ]):
            lbl = self._preview_labels.get(f"cnl.col.{i}")
            if lbl:
                try:
                    scale = 260 / max(pw + cw + prw + tw, 1)
                    lbl.configure(width=max(30, int(w * scale) // 7), text=text)
                except tk.TclError:
                    pass

        info = self._preview_labels.get("cnl.info")
        if info:
            info.configure(text=f"row: {rh}px  wrap: {self._get_int('modules.tpv.carrito_nav_list.wraplength', 170)}px")

    def _refresh_favorites_preview(self):
        cols = self._get_int("modules.tpv.favorites.columns", 8)
        chip_h = self._get_int("modules.tpv.favorites.chip_height", 80)
        spacing = self._get_int("modules.tpv.favorites.grid_spacing", 8)

        frame = self._preview_labels.get("favorites.frame")
        if not frame:
            return
        for w in frame.winfo_children():
            w.destroy()

        scale = 260 / max(cols * 40 + (cols - 1) * spacing, 1)
        chip_w = max(15, int(40 * scale))
        ch = max(15, min(int(chip_h * scale * 0.5), 50))
        sp = max(1, int(spacing * scale))

        for c in range(min(cols, 10)):
            chip = tk.Label(
                frame, text="★", bg="#FFD700", fg="#000",
                font=("Helvetica", 8), relief="solid", bd=1,
                width=chip_w // 7, height=ch // 14
            )
            chip.grid(row=0, column=c, padx=sp // 2, pady=sp // 2)

        info = self._preview_labels.get("favorites.info")
        if info:
            info.configure(text=f"{cols} cols  chip: {chip_h}px  spacing: {spacing}px")

    def _render_section(self, parent, prefix: str, label: str, data: Dict[str, Any]):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 11, "bold"),
            fg="#3498db", bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        self._render_dict(parent, prefix, data, indent=1)

    def _render_dict(self, parent, prefix: str, data: Dict[str, Any], indent: int):
        for key, value in data.items():
            full_key = f"{prefix}.{key}"
            pad = 10 + indent * 16

            if isinstance(value, dict):
                tk.Label(
                    parent, text=f"{'  ' * indent}{key}:",
                    font=("Helvetica", 10, "bold"),
                    fg="#95a5a6", bg=self._bg, anchor="w"
                ).pack(fill="x", padx=pad, pady=(4, 1))
                self._render_dict(parent, full_key, value, indent + 1)
            elif isinstance(value, list):
                tk.Label(
                    parent, text=f"{'  ' * indent}{key}: [{len(value)} items]",
                    font=("Helvetica", 10),
                    fg="#7f8c8d", bg=self._bg, anchor="w"
                ).pack(fill="x", padx=pad, pady=1)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._render_dict(parent, f"{full_key}[{i}]", item, indent + 1)
                    else:
                        tk.Label(
                            parent, text=f"{'  ' * (indent+1)}- {item}",
                            font=("Helvetica", 9),
                            fg="#7f8c8d", bg=self._bg, anchor="w"
                        ).pack(fill="x", padx=pad, pady=1)
            elif isinstance(value, (int, float)):
                self._num_row(parent, full_key, key, value, pad)
            elif isinstance(value, str):
                self._str_row(parent, full_key, key, value, pad)
            elif isinstance(value, bool):
                self._bool_row(parent, full_key, key, value, pad)
            elif value is None:
                tk.Label(
                    parent, text=f"{'  ' * indent}{key}: null",
                    font=("Helvetica", 10),
                    fg="#7f8c8d", bg=self._bg, anchor="w"
                ).pack(fill="x", padx=pad, pady=1)

    def _num_row(self, parent, full_key: str, label: str, value: Any, pad: int):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=pad, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 6))

        var = tk.StringVar(value=str(value))
        self._values[full_key] = var

        tk.Spinbox(
            row, from_=0, to=5000, increment=1,
            textvariable=var, width=6, font=("Helvetica", 10), justify="right"
        ).pack(side="left")

    def _str_row(self, parent, full_key: str, label: str, value: str, pad: int):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=pad, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 6))

        var = tk.StringVar(value=str(value))
        self._values[full_key] = var

        ctk.CTkEntry(row, textvariable=var, width=180).pack(side="left")

    def _bool_row(self, parent, full_key: str, label: str, value: bool, pad: int):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=pad, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 6))

        var = tk.StringVar(value=str(value))
        self._values[full_key] = var

        ctk.CTkOptionMenu(
            row, variable=var, values=["True", "False"], width=90
        ).pack(side="left")

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=15)
