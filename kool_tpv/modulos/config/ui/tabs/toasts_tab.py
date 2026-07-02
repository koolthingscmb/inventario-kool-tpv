"""Tab TOASTS del panel de configuración UI."""
import tkinter as tk
from tkinter import filedialog
import shutil
from pathlib import Path
from typing import Any, Dict

import customtkinter as ctk

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class ToastsTab:
    """Muestra y edita la configuración de toasts desde notificaciones_config.json."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._data: Dict[str, Any] = {}
        self._values: Dict[str, tk.StringVar] = {}
        self._build()

    def _build(self):
        self._data = self.service.cargar_json("notificaciones_config")

        scroll = ctk.CTkScrollableFrame(self.parent, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        section_title(scroll, "Toasts — notificaciones_config.json", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        test_bar = tk.Frame(scroll, bg=self._bg)
        test_bar.pack(fill="x", padx=10, pady=(4, 8))

        self._toast_type_var = tk.StringVar(value="success")

        tk.Label(
            test_bar, text="Tipo:", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        ).pack(side="left", padx=(0, 4))

        ctk.CTkOptionMenu(
            test_bar, variable=self._toast_type_var,
            values=["success", "info", "warning", "error"],
            width=100
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            test_bar, text="MOSTRAR TOAST DE PRUEBA", width=200, height=30,
            fg_color="#e67e22", hover_color="#d35400",
            font=("Helvetica", 10, "bold"),
            command=self._test_toast
        ).pack(side="left")

        self._render_position_animacion(scroll)
        self._separator(scroll)
        self._render_tamano_forma(scroll)
        self._separator(scroll)
        self._render_tiempos(scroll)
        self._separator(scroll)
        self._render_iconos(scroll)
        self._separator(scroll)
        self._render_colores_tipo(scroll)
        self._separator(scroll)
        self._render_boton_ok(scroll)
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
            "toast_ancho", "toast_alto", "toast_padding_x", "toast_padding_y",
            "toast_corner_radius", "toast_duracion_ms", "toast_fade_step_ms",
            "toast_offset_x", "toast_offset_y", "toast_icono_size",
            "toast_icono_padding", "toast_info_duracion_ms",
            "toast_ok_width", "toast_ok_height",
        }
        float_fields = {"toast_max_opacity"}
        bool_fields = {
            "toast_animar_aparicion", "toast_animar_desaparicion",
            "toast_info_mostrar_ok",
        }

        for key, var in self._values.items():
            new_val = var.get().strip()
            if key in int_fields:
                try:
                    new_val = int(float(new_val))
                except ValueError:
                    continue
            elif key in float_fields:
                try:
                    new_val = float(new_val)
                except ValueError:
                    continue
            elif key in bool_fields:
                new_val = new_val == "True"
            self._data[key] = new_val

        self.service.aplicar_cambio("notificaciones_config", self._data)
        self._status_label.configure(text="✓ Guardado", fg="#2ecc71")

    def _test_toast(self):
        tipo = self._toast_type_var.get()

        def _val(key):
            v = self._values.get(key)
            return v.get().strip() if v else ""

        def _int(key, default=0):
            try:
                return int(float(_val(key)))
            except ValueError:
                return default

        def _float(key, default=0.95):
            try:
                return float(_val(key))
            except ValueError:
                return default

        w = _int("toast_ancho", 400)
        h = _int("toast_alto", 44)
        cr = _int("toast_corner_radius", 25)
        px = _int("toast_padding_x", 16)
        py = _int("toast_padding_y", 12)
        icon_sz = _int("toast_icono_size", 40)
        icon_pad = _int("toast_icono_padding", 8)
        dur = _int("toast_duracion_ms", 3000)
        opacity = _float("toast_max_opacity", 0.95)

        bg_map = {
            "success": _val("toast_success_bg") or "#2D7D46",
            "info": _val("toast_info_bg") or "#1F6AA5",
            "warning": _val("toast_warning_bg") or "#B8870B",
            "error": _val("toast_error_bg") or "#C0392B",
        }
        fg = _val("toast_text_color") or "#FFFFFF"
        bg = bg_map.get(tipo, "#1F6AA5")

        icons = {"success": "✅", "info": "ℹ", "warning": "⚠", "error": "✕"}
        icon_emoji = icons.get(tipo, "ℹ")

        # Intentar cargar el PNG real desde config
        icon_photo = None
        if Image is not None and ImageTk is not None:
            icon_file = _val(f"toast_icono_{tipo}") or f"dialog_{tipo}.png"
            icon_path = self._ASSETS_DIR / icon_file
            if icon_path.exists():
                try:
                    pil_img = Image.open(icon_path).convert('RGBA')
                    pil_img = pil_img.resize((icon_sz, icon_sz), Image.Resampling.LANCZOS)
                    icon_photo = ImageTk.PhotoImage(pil_img)
                except Exception:
                    icon_photo = None

        root = self.parent.winfo_toplevel()
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", opacity)
        win.geometry(f"{w}x{h}")
        win.configure(bg=bg)
        win.resizable(False, False)

        canvas = tk.Canvas(win, width=w, height=h, bg=bg,
                           highlightthickness=0, bd=0)
        canvas.place(x=0, y=0)
        self._draw_rounded(canvas, 0, 0, w, h, cr, bg)

        if icon_photo:
            icon_y = (h - icon_sz) // 2
            canvas.create_image(px, icon_y, anchor="nw", image=icon_photo)
            canvas.image = icon_photo
            msg = f"Toast de prueba — tipo {tipo}"
            text_x = px + icon_sz + icon_pad
        else:
            msg = f"{icon_emoji}  Toast de prueba — tipo {tipo}"
            text_x = px + icon_sz + icon_pad

        canvas.create_text(
            text_x, h // 2,
            text=msg, fill=fg, font=("Helvetica", 12, "bold"),
            anchor="w"
        )

        mostrar_ok = tipo == "info" and _val("toast_info_mostrar_ok") == "True"
        if mostrar_ok:
            ok_w = _int("toast_ok_width", 40)
            ok_h = _int("toast_ok_height", 26)
            ok_bg = _val("toast_ok_bg") or "#FFFFFF"
            ok_fg = _val("toast_ok_fg") or "#FFFFFF"
            ok_x = w - px - ok_w
            ok_y = (h - ok_h) // 2
            canvas.create_rectangle(ok_x, ok_y, ok_x + ok_w, ok_y + ok_h,
                                    fill=ok_bg, outline="")
            canvas.create_text(ok_x + ok_w // 2, ok_y + ok_h // 2,
                               text="OK", fill=ok_fg,
                               font=("Helvetica", 9, "bold"))

        rx = root.winfo_x()
        ry = root.winfo_y()
        rw = root.winfo_width()
        rh = root.winfo_height()
        ox = _int("toast_offset_x", 30)
        oy = _int("toast_offset_y", 60)
        pos = _val("toast_posicion") or "bottom-right"

        if "right" in pos:
            x = rx + rw - w - ox
        elif "left" in pos:
            x = rx + ox
        else:
            x = rx + (rw - w) // 2

        if "bottom" in pos:
            y = ry + rh - h - oy
        elif "top" in pos:
            y = ry + oy
        else:
            y = ry + (rh - h) // 2

        win.geometry(f"+{x}+{y}")

        if dur > 0 and not mostrar_ok:
            win.after(dur, win.destroy)
        else:
            win.bind("<Button-1>", lambda e: win.destroy())

    def _draw_rounded(self, canvas, x1, y1, x2, y2, r, color):
        canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=color, outline=color)
        canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=color, outline=color)
        canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=color, outline=color)
        canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=color, outline=color)
        canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=color, outline=color)
        canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=color, outline=color)

    # ── POSICIÓN Y ANIMACIÓN ─────────────────────────────────────

    def _render_position_animacion(self, parent):
        self._section_header(parent, "POSICIÓN Y ANIMACIÓN", "#2ecc71")

        field = "toast_posicion"
        val = self._data.get(field, "bottom-right")
        var = tk.StringVar(value=str(val))
        self._values[field] = var

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        tk.Label(
            row, text="Posición:", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=15
        ).pack(side="left", padx=(0, 6))

        ctk.CTkOptionMenu(
            row, variable=var,
            values=["top-left", "top-right", "bottom-left", "bottom-right",
                    "top-center", "bottom-center"],
            width=140
        ).pack(side="left")

        offset_row = tk.Frame(parent, bg=self._bg)
        offset_row.pack(fill="x", padx=10, pady=4)

        for i, (f, label) in enumerate([
            ("toast_offset_x", "Offset X"),
            ("toast_offset_y", "Offset Y"),
        ]):
            val = self._data.get(f, 16)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(offset_row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#2ecc71", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=500, increment=1,
                textvariable=v, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

        for f, label in [
            ("toast_animar_aparicion", "Animar Aparición"),
            ("toast_animar_desaparicion", "Animar Desaparición"),
        ]:
            self._bool_row(parent, f, label, self._data.get(f, True))

        fade_row = tk.Frame(parent, bg=self._bg)
        fade_row.pack(fill="x", padx=10, pady=4)

        for i, (f, label) in enumerate([
            ("toast_fade_step_ms", "Fade Step ms"),
        ]):
            val = self._data.get(f, 20)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(fade_row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#2ecc71", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=1, to=500, increment=1,
                textvariable=v, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    # ── TAMAÑO Y FORMA ───────────────────────────────────────────

    def _render_tamano_forma(self, parent):
        self._section_header(parent, "TAMAÑO Y FORMA", "#3498db")
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (f, label) in enumerate([
            ("toast_ancho", "Ancho"),
            ("toast_alto", "Alto"),
            ("toast_corner_radius", "Corner R"),
            ("toast_padding_x", "Pad X"),
            ("toast_padding_y", "Pad Y"),
        ]):
            val = self._data.get(f, 0)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#3498db", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=10000, increment=1,
                textvariable=v, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    # ── TIEMPOS ──────────────────────────────────────────────────

    def _render_tiempos(self, parent):
        self._section_header(parent, "TIEMPOS", "#9b59b6")
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (f, label, to, inc) in enumerate([
            ("toast_duracion_ms", "Duración ms", 60000, 100),
            ("toast_max_opacity", "Max Opacity", 1.0, 0.05),
        ]):
            val = self._data.get(f, 0)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#9b59b6", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=to, increment=inc,
                textvariable=v, width=6, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

    # ── ICONOS ───────────────────────────────────────────────────

    _ICON_TYPES = [
        ("success", "Success", "#2D7D46"),
        ("info", "Info", "#1F6AA5"),
        ("warning", "Warning", "#B8870B"),
        ("error", "Error", "#C0392B"),
    ]
    _ASSETS_DIR = Path(__file__).resolve().parents[4] / 'assets' / 'dialogs'

    def _render_iconos(self, parent):
        self._section_header(parent, "ICONOS", "#f39c12")

        # --- Sub-sección: Dimensiones ---
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (f, label) in enumerate([
            ("toast_icono_size", "Icono Size"),
            ("toast_icono_padding", "Icono Padding"),
        ]):
            val = self._data.get(f, 0)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 9, "bold"),
                fg="#f39c12", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=200, increment=1,
                textvariable=v, width=5, font=("Helvetica", 11), justify="right"
            ).pack(anchor="w", pady=(2, 0))

        # --- Sub-sección: Icono por tipo ---
        self._section_header(parent, "ICONO POR TIPO", "#f39c12")

        for tipo, label, accent in self._ICON_TYPES:
            self._icon_row(parent, tipo, label, accent)

    def _icon_row(self, parent, tipo: str, label: str, accent: str):
        field = f"toast_icono_{tipo}"
        filename = self._data.get(field, f"dialog_{tipo}.png")
        var = tk.StringVar(value=filename)
        self._values[field] = var

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=3)

        tk.Label(
            row, text=label, font=("Helvetica", 10, "bold"),
            fg=accent, bg=self._bg, width=10, anchor="w"
        ).pack(side="left", padx=(0, 8))

        # Miniatura del PNG actual
        thumb_frame = tk.Frame(row, bg=self._bg, width=32, height=32)
        thumb_frame.pack(side="left", padx=(0, 8))
        thumb_frame.pack_propagate(False)

        thumb_label = tk.Label(thumb_frame, bg=self._bg)
        thumb_label.pack(expand=True)

        self._load_thumbnail(thumb_label, filename, 28)

        # Nombre del archivo
        name_label = tk.Label(
            row, textvariable=var, font=("Helvetica", 9),
            fg="#95a5a6", bg=self._bg, anchor="w", width=22
        )
        name_label.pack(side="left", padx=(0, 8))

        # Botón Cambiar
        ctk.CTkButton(
            row, text="Cambiar", width=70, height=24,
            fg_color="#f39c12", hover_color="#d68910",
            font=("Helvetica", 9, "bold"),
            command=lambda t=tipo, v=var, tl=thumb_label: self._cambiar_icono(t, v, tl)
        ).pack(side="left")

    def _load_thumbnail(self, label: tk.Label, filename: str, size: int):
        if Image is None or ImageTk is None:
            label.configure(text="(PIL?)", font=("Helvetica", 7), fg="#888")
            return
        path = self._ASSETS_DIR / filename
        if not path.exists():
            label.configure(text="(?)", font=("Helvetica", 7), fg="#888")
            return
        try:
            img = Image.open(path).convert('RGBA')
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo, text="")
            label.image = photo
        except Exception:
            label.configure(text="(!)", font=("Helvetica", 7), fg="#e74c3c")

    def _cambiar_icono(self, tipo: str, var: tk.StringVar, thumb_label: tk.Label):
        path = filedialog.askopenfilename(
            title=f"Seleccionar icono para {tipo}",
            filetypes=[("Imágenes PNG", "*.png"), ("Imágenes JPG", "*.jpg *.jpeg"), ("Todos", "*.*")]
        )
        if not path:
            return
        src = Path(path)
        dest_name = f"dialog_{tipo}.png"
        dest = self._ASSETS_DIR / dest_name
        try:
            shutil.copy2(str(src), str(dest))
            var.set(dest_name)
            self._load_thumbnail(thumb_label, dest_name, 28)
        except Exception:
            pass

    # ── COLORES POR TIPO ─────────────────────────────────────────

    def _render_colores_tipo(self, parent):
        self._section_header(parent, "COLORES POR TIPO", "#e74c3c")

        color_fields = [
            ("toast_success_bg", "Success BG", "#2D7D46"),
            ("toast_info_bg", "Info BG", "#1F6AA5"),
            ("toast_warning_bg", "Warning BG", "#B8870B"),
            ("toast_error_bg", "Error BG", "#C0392B"),
            ("toast_text_color", "Text Color", "#FFFFFF"),
        ]

        for f, label, default in color_fields:
            val = self._data.get(f, default)
            self._color_row(parent, f, label, val)

    # ── BOTÓN OK ─────────────────────────────────────────────────

    def _render_boton_ok(self, parent):
        self._section_header(parent, "BOTÓN OK", "#1abc9c")

        self._bool_row(parent, "toast_info_mostrar_ok", "Mostrar Botón OK (info)",
                       self._data.get("toast_info_mostrar_ok", False))

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        for i, (f, label) in enumerate([
            ("toast_info_duracion_ms", "Info Duración ms"),
            ("toast_ok_width", "OK Width"),
            ("toast_ok_height", "OK Height"),
        ]):
            val = self._data.get(f, 0)
            v = tk.StringVar(value=str(val))
            self._values[f] = v

            col = tk.Frame(row, bg=self._bg)
            col.grid(row=0, column=i, padx=4, sticky="w")

            tk.Label(
                col, text=label, font=("Helvetica", 8),
                fg="#1abc9c", bg=self._bg, anchor="w"
            ).pack(anchor="w")
            tk.Spinbox(
                col, from_=0, to=60000, increment=1,
                textvariable=v, width=5, font=("Helvetica", 10), justify="right"
            ).pack(anchor="w", pady=(2, 0))

        for f, label in [
            ("toast_ok_bg", "OK BG"),
            ("toast_ok_fg", "OK FG"),
            ("toast_ok_hover", "OK Hover"),
        ]:
            val = self._data.get(f, "")
            self._color_or_str_row(parent, f, label, val)

    # ── HELPERS ──────────────────────────────────────────────────

    def _section_header(self, parent, label: str, accent: str):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 11, "bold"),
            fg=accent, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

    def _color_row(self, parent, field: str, label: str, value: str):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=20, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=18
        ).pack(side="left", padx=(0, 4))

        var = tk.StringVar(value=str(value))
        self._values[field] = var

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

    def _color_or_str_row(self, parent, field: str, label: str, value: str):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=20, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=18
        ).pack(side="left", padx=(0, 4))

        var = tk.StringVar(value=str(value))
        self._values[field] = var
        ctk.CTkEntry(row, textvariable=var, width=140).pack(side="left")

    def _bool_row(self, parent, field: str, label: str, value: bool):
        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=20, pady=1)

        tk.Label(
            row, text=label, font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w", width=25
        ).pack(side="left", padx=(0, 4))

        var = tk.StringVar(value=str(value))
        self._values[field] = var

        ctk.CTkOptionMenu(
            row, variable=var, values=["True", "False"], width=90
        ).pack(side="left")

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=10)
