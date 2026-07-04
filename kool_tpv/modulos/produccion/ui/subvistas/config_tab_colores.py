"""Tab de configuración de colores del taller."""
import tkinter as tk
from tkinter import colorchooser
import customtkinter as ctk
from typing import Optional

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font


class ConfigTabColores:
    """Sub-pestaña COLORES: chips + formulario CRUD."""

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        self._color_id_edit = None
        self._chip_widgets = {}
        self._colores = {}
        self._colores_order = []
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Chips de colores (izquierda) ---
        frame_chips = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_chips.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(frame_chips, text="COLORES", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(8, 3), padx=8, anchor="w")

        self._chips_scroll = ctk.CTkScrollableFrame(frame_chips, fg_color="#34495e")
        self._chips_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear color", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._entry_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre del color", width=250)
        self._entry_nombre.pack(pady=5, padx=20)

        hex_row = ctk.CTkFrame(frame_form, fg_color="transparent")
        hex_row.pack(pady=5, padx=20, fill=tk.X)

        self._entry_hex = ctk.CTkEntry(hex_row, placeholder_text="Código HEX (#FFFFFF)", width=190)
        self._entry_hex.pack(side=tk.LEFT, padx=(0, 5))

        ctk.CTkButton(hex_row, text="🎨", width=40, fg_color="#8e44ad", hover_color="#9b59b6",
                      command=self._abrir_color_picker).pack(side=tk.LEFT)

        self._preview = ctk.CTkFrame(frame_form, fg_color="#FFFFFF", width=250, height=40, corner_radius=6)
        self._preview.pack(pady=5, padx=20)
        self._entry_hex.bind("<KeyRelease>", lambda e: self._actualizar_preview())

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._guardar).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        self._cargar_chips()

    def _cargar_chips(self):
        for child in self._chips_scroll.winfo_children():
            child.destroy()
        self._chip_widgets = {}
        self._colores = {}
        self._colores_order = []

        colores = self.service.obtener_todos_colores()
        for c in colores:
            self._colores[c.id] = c
            self._colores_order.append(c.id)

        # Configurar grid de 8 columnas
        for c in range(8):
            self._chips_scroll.grid_columnconfigure(c, weight=1)

        # Obtener estilos de chips desde config (igual que produccion_diseno_nuevo)
        chips_cfg = self.config.get("chips", {})
        default_cfg = chips_cfg.get("default", {})
        selected_cfg = chips_cfg.get("selected", {})

        for i, cid in enumerate(self._colores_order):
            color = self._colores[cid]
            row = i // 8
            col = i % 8

            is_selected = (cid == self._color_id_edit)

            bg_color = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
            text_color = selected_cfg.get("text_color", "#ffffff") if is_selected else default_cfg.get("text_color", "#cccccc")
            border_color = selected_cfg.get("border_color", "#8888ff") if is_selected else default_cfg.get("border_color", "#333333")
            border_width = selected_cfg.get("border_width", 2) if is_selected else default_cfg.get("border_width", 1)

            # Usar el codigo_hex como borde si existe
            if color.codigo_hex:
                border_color = color.codigo_hex
                border_width = 2

            chip = ctk.CTkButton(
                self._chips_scroll,
                text=color.nombre,
                font=get_font(self.config, "label"),
                fg_color=bg_color,
                text_color=text_color,
                border_color=border_color,
                border_width=border_width,
                corner_radius=8,
                height=36,
                hover_color=bg_color
            )
            chip.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            chip.bind("<Button-1>", lambda e, c=cid: self._select_chip(c))
            self._chip_widgets[cid] = chip

    def _select_chip(self, color_id):
        self._color_id_edit = color_id
        color = self._colores.get(color_id)
        if color:
            self._entry_nombre.delete(0, tk.END)
            self._entry_nombre.insert(0, color.nombre)
            self._entry_hex.delete(0, tk.END)
            self._entry_hex.insert(0, color.codigo_hex or "")
            self._actualizar_preview()

        # Actualizar estilos de chips sin recargar (evita recursión infinita)
        chips_cfg = self.config.get("chips", {})
        default_cfg = chips_cfg.get("default", {})
        selected_cfg = chips_cfg.get("selected", {})
        for cid, chip in self._chip_widgets.items():
            is_sel = (cid == color_id)
            bg = selected_cfg.get("bg", "#552583") if is_sel else default_cfg.get("bg", "#1a1a2e")
            color = self._colores.get(cid)
            border_color = color.codigo_hex if color and color.codigo_hex else (selected_cfg.get("border_color", "#8888ff") if is_sel else default_cfg.get("border_color", "#333333"))
            chip.configure(
                fg_color=bg,
                text_color=selected_cfg.get("text_color", "#ffffff") if is_sel else default_cfg.get("text_color", "#cccccc"),
                border_color=border_color,
                border_width=2,
                hover_color=bg
            )

    def _actualizar_preview(self):
        hex_code = self._entry_hex.get().strip()
        if hex_code:
            try:
                self._preview.configure(fg_color=hex_code)
            except Exception:
                pass

    def _abrir_color_picker(self):
        hex_actual = self._entry_hex.get().strip() or "#FFFFFF"
        resultado = colorchooser.askcolor(color=hex_actual, title="Seleccionar color")
        if resultado and resultado[1]:
            self._entry_hex.delete(0, tk.END)
            self._entry_hex.insert(0, resultado[1].upper())
            self._actualizar_preview()

    def _guardar(self):
        nombre = self._entry_nombre.get().strip()
        hex_code = self._entry_hex.get().strip()
        if not nombre:
            return
        ok = self.service.guardar_color(nombre, hex_code, self._color_id_edit)
        if ok:
            self._limpiar()
            self._cargar_chips()

    def _limpiar(self):
        self._color_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._entry_hex.delete(0, tk.END)
        self._preview.configure(fg_color="#FFFFFF")
        self._cargar_chips()

    def _eliminar(self):
        if self._color_id_edit:
            self.service.eliminar_color(self._color_id_edit)
            self._limpiar()

    def refresh_nav(self):
        self._cargar_chips()
