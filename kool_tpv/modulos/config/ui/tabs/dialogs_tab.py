"""Tab DIÁLOGOS del panel de configuración UI."""
import tkinter as tk
from typing import Any, Dict
import logging
import shutil
from pathlib import Path
from PIL import Image

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.utils.dialogs.config_loader import reload_dialog_config
from kool_tpv.utils.dialogs.message_dialog import MessageDialog
from kool_tpv.utils.dialogs.input_dialog import InputDialog


class DialogsTab:
    """Muestra y edita la configuración de diálogos desde ui_dialogs.json."""

    _SUBTABS = ["GLOBAL", "INFO", "SUCCESS", "WARNING", "ERROR", "PASSWORD", "INPUT"]
    _TYPE_META = {
        "global": {"color": "#3498db", "icon": "⚙"},
        "info": {"color": "#3498db", "icon": "ℹ"},
        "success": {"color": "#2ecc71", "icon": "✓"},
        "warning": {"color": "#f39c12", "icon": "⚠"},
        "error": {"color": "#e74c3c", "icon": "✕"},
        "password": {"color": "#9b59b6", "icon": "🔒"},
        "input": {"color": "#3498db", "icon": "✎"},
    }

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._current_subtab: str = ""
        self._subtab_btns: Dict[str, tk.Label] = {}
        self._status_label: tk.Label = None
        self._preview_frame: tk.Frame = None
        self._preview_widgets: Dict[str, Any] = {}
        self._build()

    def _build(self):
        self._data = self.service.cargar_json("ui_dialogs")

        self.main_container = tk.Frame(self.parent, bg=self._bg)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Barra de subpestañas
        self.tab_bar = tk.Frame(self.main_container, bg="#1a1a1a", height=45)
        self.tab_bar.pack(fill="x", side=tk.TOP)
        self.tab_bar.pack_propagate(False)
        self._render_subtabs()

        # 2. Layout principal (Izquierda: Config, Derecha: Preview)
        self.layout_frame = tk.Frame(self.main_container, bg=self._bg)
        self.layout_frame.pack(fill=tk.BOTH, expand=True)

        self.config_side = tk.Frame(self.layout_frame, bg=self._bg, width=600)
        self.config_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.config_side.pack_propagate(False)

        self.preview_side = tk.Frame(self.layout_frame, bg="#1a1a1a", width=350)
        self.preview_side.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(2, 0))
        self.preview_side.pack_propagate(False)

        self.content_container = ctk.CTkScrollableFrame(self.config_side, fg_color=self._bg)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # 3. Barra inferior APLICAR
        self._render_save_bar(self.main_container)

        self._render_preview_panel()
        self._switch_subtab("GLOBAL")

    def _render_subtabs(self):
        for label in self._SUBTABS:
            btn = tk.Label(
                self.tab_bar, text=label,
                font=("Helvetica", 10, "bold"),
                fg="#7f8c8d", bg="#1a1a1a",
                padx=20, cursor="hand2"
            )
            btn.pack(side=tk.LEFT, fill="y")
            btn.bind("<Button-1>", lambda e, c=label: self._switch_subtab(c))
            self._subtab_btns[label] = btn

    def _switch_subtab(self, code: str):
        for c, btn in self._subtab_btns.items():
            if c == code:
                btn.configure(fg="#3498db", bg="#2c3e50")
            else:
                btn.configure(fg="#7f8c8d", bg="#1a1a1a")
        self._current_subtab = code

        for w in self.content_container.winfo_children():
            w.destroy()
        
        # Nota: No limpiamos self._values para permitir previsualización de cambios no aplicados
        # Pero solo renderizamos los controles del subtab actual.
        
        dlg_key = code.lower()
        if dlg_key == "global":
            self._render_global_config()
        else:
            self._render_type_config(dlg_key)
        
        self._update_preview()

    def _render_global_config(self):
        prefix = "common"
        config = self._data.get(prefix, {})
        accent = "#3498db"
        
        self._render_section_title("ESTILO GLOBAL (Ventana y Geometría)", accent)
        if "window" in config:
            self._render_window_section(self.content_container, f"{prefix}.window", config["window"], accent)
        
        self._render_section_title("ESPACIADO Y DISTANCIAS", accent)
        if "spacing" in config:
            self._render_spacing_section(self.content_container, f"{prefix}.spacing", config["spacing"], accent)
            
        self._render_section_title("BOTONES POR DEFECTO", accent)
        if "buttons" in config:
            self._render_buttons_section(self.content_container, f"{prefix}.buttons", config["buttons"], accent)

        self._render_section_title("FUENTES GLOBALES", accent)
        if "fonts" in config:
            self._render_fonts_section(self.content_container, f"{prefix}.fonts", config["fonts"], accent)

    def _render_type_config(self, dlg_key: str):
        prefix = f"dialogs.{dlg_key}"
        config = self._data.get("dialogs", {}).get(dlg_key, {})
        meta = self._TYPE_META.get(dlg_key, {"color": "#3498db", "icon": "?"})
        accent = meta["color"]

        self._render_section_title(f"ESTILO ESPECÍFICO: {dlg_key.upper()}", accent)
        
        # Colores (Siempre mostrados)
        if "colors" in config:
            self._render_colors_section(self.content_container, f"{prefix}.colors", config["colors"], accent)

        # Icono (Nuevo: Gestión de iconos)
        self._render_icon_section(self.content_container, dlg_key, accent)

        # Botón para añadir overrides si no existen
        tk.Label(
            self.content_container, text="\nLos demás parámetros se heredan de GLOBAL.\nUsa el botón TEST para ver el resultado final.",
            font=("Helvetica", 9, "italic"), fg="#95a5a6", bg=self._bg
        ).pack(pady=10)

        ctk.CTkButton(
            self.content_container, text="ABRIR TEST REAL", width=150, height=35,
            fg_color=accent, hover_color=accent,
            font=("Helvetica", 11, "bold"),
            command=lambda dt=dlg_key, ac=accent: self._test_dialog(dt, ac)
        ).pack(pady=5)

    def _render_section_title(self, text: str, accent: str):
        tk.Label(
            self.content_container, text=text,
            font=("Helvetica", 12, "bold"),
            fg=accent, bg=self._bg, anchor="w", justify="left"
        ).pack(fill="x", padx=10, pady=(15, 5))

    def _render_preview_panel(self):
        """Dibuja un esquema del diálogo que se actualiza en tiempo real."""
        tk.Label(
            self.preview_side, text="PREVISUALIZACIÓN",
            font=("Helvetica", 10, "bold"),
            fg="#95a5a6", bg="#1a1a1a"
        ).pack(pady=10)

        # Contenedor centralizado para el diálogo falso
        self.mock_dialog_bg = tk.Frame(self.preview_side, bg="#1a1a1a")
        self.mock_dialog_bg.pack(fill=tk.BOTH, expand=True)

        # El diálogo falso (un Frame)
        self.mock_dialog = tk.Frame(self.mock_dialog_bg, relief="solid", bd=2)
        self.mock_dialog.place(relx=0.5, rely=0.4, anchor="center")

        # Barra de título falsa
        self.mock_header = tk.Frame(self.mock_dialog, height=25)
        self.mock_header.pack(fill="x", side="top")
        self.mock_header.pack_propagate(False)
        
        self.mock_title = tk.Label(self.mock_header, text="DIÁLOGO", font=("Helvetica", 8, "bold"))
        self.mock_title.pack(side="left", padx=5)

        # Cuerpo falso
        self.mock_body = tk.Frame(self.mock_dialog)
        self.mock_body.pack(fill="both", expand=True)

        self.mock_msg = tk.Label(self.mock_body, text="Mensaje de ejemplo\ncon varias líneas", font=("Helvetica", 8))
        self.mock_msg.pack(pady=10, padx=10)

        # Botones falsos
        self.mock_btns = tk.Frame(self.mock_body)
        self.mock_btns.pack(side="bottom", pady=10)

        self.mock_btn_ok = tk.Label(self.mock_btns, text="ACEPTAR", font=("Helvetica", 7, "bold"), width=8, relief="raised")
        self.mock_btn_ok.pack(side="left", padx=3)
        
        self.mock_btn_cancel = tk.Label(self.mock_btns, text="CANCELAR", font=("Helvetica", 7), width=8, relief="raised")
        self.mock_btn_cancel.pack(side="left", padx=3)

    def _update_preview(self, *args):
        """Actualiza el mock del diálogo basado en los valores actuales de self._values."""
        dlg_key = self._current_subtab.lower()
        if dlg_key == "global": dlg_key = "info" # Usar info como base para preview de global
        
        prefix = f"dialogs.{dlg_key}"
        common_p = "common"
        
        def _get(key, default=""):
            # Intentar primero override del tipo, luego global, luego default
            v = self._values.get(f"{prefix}.{key}")
            if v: return v.get()
            v = self._values.get(f"{common_p}.{key}")
            if v: return v.get()
            return default

        def _int(key, default=0):
            try: return int(float(_get(key, str(default))))
            except: return default

        # Aplicar colores
        bg = _get("colors.bg", "#000000")
        border = _get("colors.border", "#3498db")
        tb_bg = _get("colors.title_bar_bg", border)
        tb_text = _get("colors.title_bar_text", "#FFFFFF")
        msg_text = _get("colors.message_text", "#FFFFFF")
        btn_bg = _get("colors.button_bg", border)
        btn_text = _get("colors.button_text", "#FFFFFF")
        
        # Aplicar dimensiones (proporcionales para el preview)
        scale = 0.5
        w = _int("window.width", 400) * scale
        h = _int("window.height", 300) * scale
        cr = _int("window.corner_radius", 15) // 2
        bw = _int("window.border_width", 2)
        tbh = _int("window.title_bar_height", 50) * scale
        
        self.mock_dialog.configure(width=w, height=h, bg=bg, highlightbackground=border, highlightthickness=bw)
        self.mock_dialog.pack_propagate(False)
        
        self.mock_header.configure(height=tbh, bg=tb_bg)
        self.mock_title.configure(bg=tb_bg, fg=tb_text, text=dlg_key.upper())
        
        self.mock_body.configure(bg=bg)
        self.mock_msg.configure(bg=bg, fg=msg_text)
        
        self.mock_btns.configure(bg=bg)
        self.mock_btn_ok.configure(bg=btn_bg, fg=btn_text)
        
        # Actualizar cada 100ms si hay cambios (vía trace ya se hace)

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
        """Guarda todos los valores actuales (globales y específicos) en el JSON."""
        for key, var in self._values.items():
            parts = key.split(".")
            new_val = var.get().strip()
            
            # Convertir a int si es un campo numérico conocido
            numeric_fields = [
                "width", "height", "corner_radius", "border_width",
                "padding_x", "padding_y", "title_bar_height", "icon_size",
                "button_width", "button_height", "entry_width", "entry_height",
                "size", "font_size", "icon_top", "icon_bottom", "title_bottom",
                "message_bottom", "entry_bottom", "focus_border_width"
            ]
            
            if parts[-1] in numeric_fields:
                try:
                    new_val = int(float(new_val))
                except ValueError:
                    continue
            
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

    def _test_dialog(self, dlg_type: str, accent: str):
        """Abre un diálogo REAL de la aplicación usando los valores actuales (incluyendo cambios no guardados)."""
        # 1. Recopilar todos los valores actuales de la UI para crear un ui_data temporal
        ui_data = self._build_ui_data_from_vars()
        
        # 2. Actualizar el cache global de configuración (en memoria) para que el diálogo lo use
        reload_dialog_config(ui_data)
        
        # 3. Lanzar el diálogo real según el tipo
        if dlg_type in ['input', 'password']:
            InputDialog(
                self.parent, 
                tipo=dlg_type, 
                titulo="DIÁLOGO DE PRUEBA", 
                mensaje=f"ESTE ES UN DIÁLOGO REAL DE TIPO {dlg_type.upper()}",
                password=(dlg_type == 'password')
            )
        else:
            MessageDialog(
                self.parent, 
                tipo=dlg_type, 
                titulo="DIÁLOGO DE PRUEBA", 
                mensaje=f"ESTE ES UN DIÁLOGO REAL DE TIPO {dlg_type.upper()}\nCON ICONO Y ESTILOS ACTUALES.",
                confirm=(dlg_type == 'warning') # Simular confirmación en warning
            )

    def _build_ui_data_from_vars(self) -> dict:
        """Construye un diccionario con la estructura de ui_dialogs.json a partir de los campos de la UI."""
        # Clonar la data actual para mantener campos que no están en la UI si los hubiera
        temp_data = dict(self._data)
        
        for key, var in self._values.items():
            parts = key.split(".")
            val = var.get().strip()
            
            # Convertir a int si es numérico
            numeric_fields = [
                "width", "height", "corner_radius", "border_width",
                "padding_x", "padding_y", "title_bar_height", "icon_size",
                "button_width", "button_height", "entry_width", "entry_height",
                "size", "font_size", "icon_top", "icon_bottom", "title_bottom",
                "message_bottom", "entry_bottom", "focus_border_width"
            ]
            if parts[-1] in numeric_fields:
                try: val = int(float(val))
                except: continue
                
            self._set_nested(temp_data, parts, val)
        return temp_data

    def _render_icon_section(self, parent, dlg_type: str, accent: str):
        self._section_header(parent, "ICONO DEL DIÁLOGO", accent)
        
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=15, pady=5)
        
        # 1. Mostrar icono actual
        icon_container = tk.Frame(row, bg="#1a1a1a", width=60, height=60)
        icon_container.pack(side="left", padx=(0, 15))
        icon_container.pack_propagate(False)
        
        lbl_icon = tk.Label(icon_container, bg="#1a1a1a")
        lbl_icon.pack(expand=True)
        
        def _load_current_icon():
            try:
                base = Path(__file__).resolve().parents[4]
                icon_path = base / "assets" / "dialogs" / f"dialog_{dlg_type}.png"
                if not icon_path.exists():
                    icon_path = base / "assets" / "dialogs" / "dialog_error.png"
                
                if icon_path.exists():
                    from PIL import ImageTk
                    img = Image.open(icon_path)
                    img = img.resize((40, 40), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    lbl_icon.configure(image=photo)
                    lbl_icon.image = photo
                else:
                    lbl_icon.configure(text="?", fg="#ecf0f1", font=("Helvetica", 20, "bold"))
            except Exception as e:
                logging.error(f"Error cargando icono para preview: {e}")
                lbl_icon.configure(text="!", fg="#e74c3c", font=("Helvetica", 20, "bold"))

        _load_current_icon()
        
        # 2. Información y botones
        info_col = tk.Frame(row, bg=self._bg)
        info_col.pack(side="left", fill="both", expand=True)
        
        tk.Label(
            info_col, text=f"dialog_{dlg_type}.png",
            font=("Courier New", 10), fg="#95a5a6", bg=self._bg, anchor="w"
        ).pack(fill="x")
        
        btn_row = tk.Frame(info_col, bg=self._bg)
        btn_row.pack(fill="x", pady=(5, 0))
        
        def _on_change_icon():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Seleccionar Nuevo Icono (PNG)",
                filetypes=[("Imágenes PNG", "*.png")]
            )
            if file_path:
                try:
                    base = Path(__file__).resolve().parents[4]
                    dest_dir = base / "assets" / "dialogs"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / f"dialog_{dlg_type}.png"
                    
                    # Copiar el archivo
                    shutil.copy2(file_path, dest_path)
                    
                    # Refrescar preview
                    _load_current_icon()
                    self._status_label.configure(text=f"✓ Icono {dlg_type} actualizado", fg="#2ecc71")
                except Exception as e:
                    logging.exception("Error al cambiar icono")
                    self._status_label.configure(text="✕ Error al guardar icono", fg="#e74c3c")

        ctk.CTkButton(
            btn_row, text="CAMBIAR ICONO", width=120, height=28,
            fg_color="#34495e", hover_color="#2c3e50",
            font=("Helvetica", 10, "bold"),
            command=_on_change_icon
        ).pack(side="left")

    def _section_header(self, parent, label: str, accent: str):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 11, "bold"),
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
            var.trace_add("write", self._update_preview)
            self._values[f"{prefix}.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=3, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 10),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=1000, increment=1,
                textvariable=var, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    def _render_colors_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "COLORS", accent)
        for key, value in data.items():
            if not isinstance(value, str):
                continue
            full_key = f"{prefix}.{key}"
            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=4, pady=1)

            tk.Label(
                row, text=key, font=("Helvetica", 11),
                fg=self._fg, bg=self._bg, anchor="w", width=18
            ).pack(side="left", padx=(0, 4))

            var = tk.StringVar(value=str(value))
            var.trace_add("write", self._update_preview)
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
            row.pack(fill="x", padx=4, pady=2)

            tk.Label(
                row, text=font_key, font=("Helvetica", 11, "bold"),
                fg="#95a5a6", bg=self._bg, anchor="w", width=10
            ).pack(side="left", padx=(0, 4))

            for field, default in [("family", "Courier New"), ("size", 14), ("weight", "bold")]:
                val = font_data.get(field, default)
                var = tk.StringVar(value=str(val))
                var.trace_add("write", self._update_preview)
                self._values[f"{prefix}.{font_key}.{field}"] = var

                if field == "family":
                    ctk.CTkEntry(row, textvariable=var, width=100).pack(side="left", padx=(0, 4))
                elif field == "size":
                    tk.Spinbox(
                        row, from_=6, to=72, increment=1,
                        textvariable=var, width=4, font=("Helvetica", 11), justify="right"
                    ).pack(side="left", padx=(0, 4))
                elif field == "weight":
                    ctk.CTkOptionMenu(
                        row, variable=var, values=["normal", "bold"], width=70
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
            var.trace_add("write", self._update_preview)
            self._values[f"{prefix}.{field}"] = var

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=3, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 10),
                fg="#95a5a6", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=200, increment=1,
                textvariable=var, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    def _render_buttons_section(self, parent, prefix: str, data: Dict[str, Any], accent: str):
        self._section_header(parent, "BUTTONS", accent)
        for btn_key in ["accept", "cancel"]:
            btn_data = data.get(btn_key)
            if not isinstance(btn_data, dict):
                continue

            row = tk.Frame(parent, bg=self._bg)
            row.pack(fill="x", padx=4, pady=2)

            tk.Label(
                row, text=btn_key.upper(), font=("Helvetica", 11, "bold"),
                fg=accent, bg=self._bg, anchor="w", width=8
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
                var.trace_add("write", self._update_preview)
                self._values[f"{prefix}.{btn_key}.{field}"] = var

                col = tk.Frame(row, bg=self._bg)
                col.pack(side="left", padx=2)

                tk.Label(
                    col, text=label, font=("Helvetica", 9),
                    fg="#95a5a6", bg=self._bg, anchor="w"
                ).pack(anchor="w")
                tk.Spinbox(
                    col, from_=0, to=500, increment=1,
                    textvariable=var, width=4, font=("Helvetica", 11), justify="right"
                ).pack(anchor="w", pady=(1, 0))

            if "style_key" in btn_data:
                sk_var = tk.StringVar(value=str(btn_data["style_key"]))
                sk_var.trace_add("write", self._update_preview)
                self._values[f"{prefix}.{btn_key}.style_key"] = sk_var
                col = tk.Frame(row, bg=self._bg)
                col.pack(side="left", padx=4)
                tk.Label(
                    col, text="style_key", font=("Helvetica", 7),
                    fg="#95a5a6", bg=self._bg, anchor="w"
                ).pack(anchor="w")
                ctk.CTkEntry(col, textvariable=sk_var, width=100).pack(anchor="w", pady=(1, 0))

