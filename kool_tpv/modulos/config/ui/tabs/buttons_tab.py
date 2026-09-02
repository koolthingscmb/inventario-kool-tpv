"""Tab BOTONES del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict, List

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.utils.factories.button_factory import ButtonFactory


class ButtonsTab:
    """Muestra y edita los estilos de botones desde button_styles.json y buttons_config.json."""

    _SUBTABS = ["ESTILOS", "MENÚ PRINCIPAL", "BOTONES GLOBALES"]

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        
        # Cargar colores dinámicos del módulo config
        colors = load_colors('config')
        self._TAB_BG_SELECTED = colors.get('buttons', {}).get('primary', {}).get('bg', '#FF9800')
        self._TAB_BG_NORMAL = colors.get('buttons', {}).get('secondary', {}).get('bg', '#643300')
        self._TAB_FG = colors.get('buttons', {}).get('primary', {}).get('text', '#000000')
        
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data_styles: Dict[str, Any] = {}
        self._data_config: Dict[str, Any] = {}
        self._tokens: Dict[str, str] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._preview_btns: Dict[str, ctk.CTkButton] = {}
        self._style_rows: Dict[str, tk.Frame] = {}
        self._system_styles: set = set()
        self._current_subtab: str = ""
        self._subtab_btns: Dict[str, tk.Label] = {}
        self._status_label: tk.Label = None
        self._preview_style_var = None
        self._preview_test_btn = None
        self._styles_container = None
        self._estilo_editor_frame = None
        self._estilo_var = None
        self._build()

    def _build(self):
        self._data_styles = self.service.cargar_json("button_styles")
        self._data_config = self.service.cargar_json("buttons_config")
        self._tokens = self._load_tokens()
        self._system_styles = self._load_system_styles()

        self.main_container = tk.Frame(self.parent, bg=self._bg)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Barra de subpestañas
        self.tab_bar = tk.Frame(self.main_container, bg="#1a1a1a", height=45)
        self.tab_bar.pack(fill="x", side=tk.TOP)
        self.tab_bar.pack_propagate(False)
        self._render_subtabs()

        # 2. Contenedor de contenido
        self.content_container = tk.Frame(self.main_container, bg=self._bg)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # 3. Barra inferior APLICAR
        self._render_save_bar(self.main_container)

        self._switch_subtab("ESTILOS")

    def _render_subtabs(self):
        for label in self._SUBTABS:
            btn = tk.Label(
                self.tab_bar, text=label,
                font=("Helvetica", 10, "bold"),
                fg=self._TAB_FG, bg=self._TAB_BG_NORMAL,
                padx=20, cursor="hand2"
            )
            btn.pack(side=tk.LEFT, fill="y")
            btn.bind("<Button-1>", lambda e, c=label: self._switch_subtab(c))
            self._subtab_btns[label] = btn

    def _switch_subtab(self, code: str):
        for c, btn in self._subtab_btns.items():
            if c == code:
                btn.configure(fg=self._TAB_FG, bg=self._TAB_BG_SELECTED)
            else:
                btn.configure(fg=self._TAB_FG, bg=self._TAB_BG_NORMAL)
        self._current_subtab = code

        for w in self.content_container.winfo_children():
            w.destroy()
        self._values.clear()
        self._preview_btns.clear()
        self._style_rows.clear()

        if code == "ESTILOS":
            self._render_estilos_subtab()
        elif code == "MENÚ PRINCIPAL":
            self._render_menu_subtab()
        elif code == "BOTONES GLOBALES":
            self._render_globales_subtab()

    # ── Subpestaña ESTILOS ──────────────────────────────────────────

    def _render_estilos_subtab(self):
        left = ctk.CTkScrollableFrame(self.content_container, fg_color=self._bg)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(self.content_container, bg=self._bg, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        header = tk.Frame(left, bg=self._bg)
        header.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(
            header, text="Estilos de botón — button_styles.json",
            font=("Helvetica", 14, "bold"), fg=self._TAB_BG_SELECTED, bg=self._bg
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ NUEVO ESTILO", width=120, height=28,
            fg_color=self._TAB_BG_NORMAL, hover_color=self._TAB_BG_SELECTED,
            font=("Helvetica", 11, "bold"),
            command=self._nuevo_estilo
        ).pack(side="right")

        # Combobox para seleccionar estilo
        combo_frame = tk.Frame(left, bg=self._bg)
        combo_frame.pack(fill="x", padx=10, pady=(5, 10))

        tk.Label(
            combo_frame, text="Selecciona un estilo:", font=("Helvetica", 10),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w"
        ).pack(fill="x", pady=(0, 2))

        style_names = sorted(self._data_styles.keys())
        self._estilo_var = tk.StringVar(value=style_names[0] if style_names else "")

        ctk.CTkOptionMenu(
            combo_frame, variable=self._estilo_var,
            values=style_names, width=300,
            fg_color=self._TAB_BG_SELECTED,
            button_color=self._TAB_BG_SELECTED,
            button_hover_color=self._TAB_BG_NORMAL,
            command=self._on_estilo_selected
        ).pack(fill="x")

        # Contenedor para el editor del estilo seleccionado
        self._styles_container = left
        self._estilo_editor_frame = tk.Frame(left, bg=self._bg)
        self._estilo_editor_frame.pack(fill="x", padx=10, pady=5)

        # Renderizar el primer estilo
        if style_names:
            self._on_estilo_selected(style_names[0])

        self._render_preview_panel(right)

    def _on_estilo_selected(self, name: str):
        if not name or name not in self._data_styles:
            return
        for w in self._estilo_editor_frame.winfo_children():
            w.destroy()
        # Limpiar values del estilo anterior
        keys_to_remove = [k for k in self._values if "." in k and k.split(".")[0] not in ("main_menu", "global_buttons")]
        for k in keys_to_remove:
            self._values.pop(k, None)
        self._style_row(self._estilo_editor_frame, name, self._data_styles[name])

    def _render_preview_panel(self, parent):
        tk.Label(
            parent, text="PREVIEW DE BOTÓN",
            font=("Helvetica", 14, "bold"), fg=self._TAB_BG_SELECTED, bg=self._bg
        ).pack(fill="x", pady=(10, 5), padx=10)

        tk.Label(
            parent, text="Selecciona un estilo:", font=("Helvetica", 10),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(5, 2))

        style_names = sorted(self._data_styles.keys())
        self._preview_style_var = tk.StringVar(value=style_names[0] if style_names else "")

        ctk.CTkOptionMenu(
            parent, variable=self._preview_style_var,
            values=style_names, width=260,
            fg_color=self._TAB_BG_SELECTED,
            button_color=self._TAB_BG_SELECTED,
            button_hover_color=self._TAB_BG_NORMAL
        ).pack(fill="x", padx=10, pady=2)

        tk.Label(
            parent, text="Texto del botón:", font=("Helvetica", 10),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w"
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

    def _load_system_styles(self) -> set:
        refs = set()
        cfg = self._data_config
        for section in ["main_menu", "global_buttons"]:
            items = cfg.get(section, [])
            if isinstance(items, list):
                for item in items:
                    sk = item.get("style_key") or item.get("color_key")
                    if sk:
                        refs.add(sk)
        return refs

    def _render_save_bar(self, parent):
        bar = tk.Frame(parent, bg=self._bg)
        bar.pack(fill="x", side=tk.BOTTOM, padx=10, pady=10)

        self._status_label = tk.Label(
            bar, text="", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        )
        self._status_label.pack(side=tk.LEFT, padx=(0, 8))

        ButtonFactory.create_button(
            bar, text="APLICAR", width=100, height=32,
            module="config", palette_key="primary", style_key="action_success",
            command=self._on_aplicar
        ).pack(side=tk.RIGHT)

    def _on_aplicar(self):
        if self._current_subtab == "ESTILOS":
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

        elif self._current_subtab in ("MENÚ PRINCIPAL", "BOTONES GLOBALES"):
            section = "main_menu" if self._current_subtab == "MENÚ PRINCIPAL" else "global_buttons"
            items = self._data_config.get(section, [])
            for key, var in self._values.items():
                parts = key.split(".")
                if len(parts) >= 3 and parts[0] == section:
                    idx = int(parts[1])
                    field = parts[2]
                    if idx < len(items):
                        items[idx][field] = var.get().strip()
            self.service.aplicar_cambio("buttons_config", self._data_config)

        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    # ── Subpestaña MENÚ PRINCIPAL ───────────────────────────────────

    def _render_menu_subtab(self):
        scroll = ctk.CTkScrollableFrame(self.content_container, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            scroll, text="Menú Principal — buttons_config.json → main_menu",
            font=("Helvetica", 14, "bold"), fg=self._TAB_BG_SELECTED, bg=self._bg
        ).pack(fill="x", padx=10, pady=(10, 8))

        tk.Label(
            scroll, text="Estos son los botones de la barra lateral de navegación. "
                         "Cada uno usa un estilo (style_key) definido en la subpestaña ESTILOS.",
            font=("Helvetica", 10), fg=self._TAB_BG_SELECTED, bg=self._bg,
            anchor="w", justify="left", wraplength=600
        ).pack(fill="x", padx=10, pady=(0, 10))

        items = self._data_config.get("main_menu", [])
        style_names = sorted(self._data_styles.keys())

        for i, item in enumerate(items):
            self._config_row(scroll, item, i, style_names, "main_menu")

    # ── Subpestaña BOTONES GLOBALES ─────────────────────────────────

    def _render_globales_subtab(self):
        scroll = ctk.CTkScrollableFrame(self.content_container, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            scroll, text="Botones Globales — buttons_config.json → global_buttons",
            font=("Helvetica", 14, "bold"), fg=self._TAB_BG_SELECTED, bg=self._bg
        ).pack(fill="x", padx=10, pady=(10, 8))

        tk.Label(
            scroll, text="Botones especiales disponibles en toda la app. "
                         "Ej: botón de power (apagar/cerrar), PRINT ON (activar impresión automática).",
            font=("Helvetica", 10), fg=self._TAB_BG_SELECTED, bg=self._bg,
            anchor="w", justify="left", wraplength=600
        ).pack(fill="x", padx=10, pady=(0, 10))

        items = self._data_config.get("global_buttons", [])
        style_names = sorted(self._data_styles.keys())

        for i, item in enumerate(items):
            self._config_row(scroll, item, i, style_names, "global_buttons")

    def _token_color(self, token_name: str) -> str:
        if token_name and token_name in self._tokens:
            return self._tokens[token_name]
        return "#444444"

    def _nuevo_estilo(self):
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Nuevo estilo de botón")
        dialog.geometry("360x180")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(
            dialog, text="Nombre del estilo:",
            font=("Helvetica", 12), fg=self._TAB_BG_SELECTED, bg=self._bg
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
            # Actualizar combobox y seleccionar el nuevo estilo
            style_names = sorted(self._data_styles.keys())
            if hasattr(self, '_estilo_var'):
                self._estilo_var.set(nombre)
            dialog.destroy()

        def _on_enter(e):
            _confirmar()

        entry.bind("<Return>", _on_enter)

        ctk.CTkButton(
            dialog, text="CREAR", width=100, height=30,
            fg_color=self._TAB_BG_NORMAL, hover_color=self._TAB_BG_SELECTED,
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
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 8))

        type_var = tk.StringVar(value=str(style.get("type", "outline")))
        self._values[f"{name}.type"] = type_var
        ctk.CTkOptionMenu(
            header, variable=type_var, values=["outline", "solid"], width=80,
            fg_color=self._TAB_BG_SELECTED,
            button_color=self._TAB_BG_SELECTED,
            button_hover_color=self._TAB_BG_NORMAL
        ).pack(side="left", padx=(0, 6))

        if name in self._system_styles:
            tk.Label(
                header, text="SISTEMA", font=("Helvetica", 8),
                fg=self._TAB_BG_SELECTED, bg=self._bg
            ).pack(side="left", padx=(0, 6))
        else:
            colors = load_colors('config')
            accent_color = colors.get('buttons', {}).get('accent', {}).get('bg', '#FF4300')
            accent_hover = colors.get('buttons', {}).get('accent', {}).get('hover', '#FF6433')
            ctk.CTkButton(
                header, text="✕", width=28, height=24,
                fg_color=accent_color, hover_color=accent_hover,
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
                fields_frame, variable=var, values=token_names, width=120,
                fg_color=self._TAB_BG_SELECTED,
                button_color=self._TAB_BG_SELECTED,
                button_hover_color=self._TAB_BG_NORMAL
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
        for fk in [f"{name}.{k}" for k, *_ in color_fields] + [f"{name}.{k}" for k, _ in num_fields]:
            sv = self._values.get(fk)
            if sv:
                sv.trace_add("write", _update_preview)

        self._update_style_preview(name)

    def _eliminar_estilo(self, name: str):
        if name in self._system_styles:
            return

        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Eliminar estilo")
        dialog.geometry("380x160")
        dialog.resizable(False, False)
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(
            dialog, text=f"¿Eliminar el estilo \"{name}\"?",
            font=("Helvetica", 12), fg=self._TAB_BG_SELECTED, bg=self._bg
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
            # Limpiar editor y seleccionar otro estilo
            for w in self._estilo_editor_frame.winfo_children():
                w.destroy()
            remaining = sorted(self._data_styles.keys())
            if remaining and hasattr(self, '_estilo_var'):
                self._estilo_var.set(remaining[0])
            dialog.destroy()

        colors = load_colors('config')
        accent_color = colors.get('buttons', {}).get('accent', {}).get('bg', '#FF4300')
        accent_hover = colors.get('buttons', {}).get('accent', {}).get('hover', '#FF6433')

        ctk.CTkButton(
            btns, text="CANCELAR", width=90, height=28,
            fg_color=self._TAB_BG_NORMAL, hover_color=self._TAB_BG_SELECTED,
            command=dialog.destroy
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btns, text="ELIMINAR", width=90, height=28,
            fg_color=accent_color, hover_color=accent_hover,
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

    def _config_row(self, parent, item: Dict[str, Any], index: int,
                     style_names: List[str], section: str):
        label = item.get("label", item.get("text", item.get("id", "?")))
        style_key = item.get("style_key", item.get("color_key", ""))
        command = item.get("command", "")

        outer = tk.Frame(parent, bg=self._bg)
        outer.pack(fill="x", padx=10, pady=4)

        row = tk.Frame(outer, bg=self._bg)
        row.pack(fill="x")

        tk.Label(
            row, text=label, font=("Helvetica", 11, "bold"),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w", width=20
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            row, text=f"cmd: {command}", font=("Helvetica", 9),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w"
        ).pack(side="left", padx=(0, 12))

        style_var = tk.StringVar(value=str(style_key) if style_key else "")
        self._values[f"{section}.{index}.style_key"] = style_var

        tk.Label(
            row, text="estilo:", font=("Helvetica", 9),
            fg=self._TAB_BG_SELECTED, bg=self._bg, anchor="w"
        ).pack(side="left", padx=(0, 4))

        ctk.CTkOptionMenu(
            row, variable=style_var, values=style_names, width=180,
            fg_color=self._TAB_BG_SELECTED,
            button_color=self._TAB_BG_SELECTED,
            button_hover_color=self._TAB_BG_NORMAL
        ).pack(side="left", padx=(0, 8))

        # Preview del botón con el estilo seleccionado
        preview_btn = ctk.CTkButton(outer, text=label)
        preview_btn.pack(side="left", pady=(2, 0))
        self._preview_btns[f"{section}.{index}"] = preview_btn

        def _update_preview(*_):
            sk = style_var.get()
            if sk and sk in self._data_styles:
                self._apply_style_to_btn(preview_btn, sk)

        style_var.trace_add("write", _update_preview)
        _update_preview()

    def _apply_style_to_btn(self, btn: ctk.CTkButton, style_name: str):
        style = self._data_styles.get(style_name, {})
        bg = self._token_color(style.get("bg_token", ""))
        fg = self._token_color(style.get("text_token", ""))
        hover = self._token_color(style.get("hover_token", ""))
        border_tok = style.get("border_token")
        border = self._token_color(border_tok) if border_tok else bg

        try:
            w = min(int(style.get("width", style.get("min_width", 100))), 200)
        except (ValueError, TypeError):
            w = 100
        try:
            h = min(int(style.get("height", 36)), 60)
        except (ValueError, TypeError):
            h = 36
        try:
            cr = int(style.get("corner_radius", 8))
        except (ValueError, TypeError):
            cr = 8
        try:
            bw = int(style.get("border_width", 0))
        except (ValueError, TypeError):
            bw = 0
        try:
            fs = min(int(style.get("font_size", 14)), 18)
        except (ValueError, TypeError):
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
