"""Tab de configuración de colores del taller."""
import tkinter as tk
from tkinter import colorchooser
import customtkinter as ctk
from typing import Optional

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList


class ConfigTabColores:
    """Sub-pestaña COLORES: lista + formulario CRUD."""

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
        self._nav = None
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Lista (izquierda) ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = [
            ("nombre", 200, "NOMBRE"),
            ("codigo_hex", 120, "HEX"),
        ]
        self._nav = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

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

        self._cargar_lista()

    def _cargar_lista(self):
        colores = self.service.obtener_todos_colores()
        items = [{"id": c.id, "nombre": c.nombre, "codigo_hex": c.codigo_hex or ""} for c in colores]
        self._nav.set_items(items)

    def _on_selected(self, data):
        self._color_id_edit = data.get("id")
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, data.get("nombre", ""))
        self._entry_hex.delete(0, tk.END)
        self._entry_hex.insert(0, data.get("codigo_hex", ""))
        self._actualizar_preview()

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
            self._cargar_lista()

    def _limpiar(self):
        self._color_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._entry_hex.delete(0, tk.END)
        self._preview.configure(fg_color="#FFFFFF")

    def _eliminar(self):
        if self._color_id_edit:
            self.service.eliminar_color(self._color_id_edit)
            self._limpiar()
            self._cargar_lista()

    def refresh_nav(self):
        if self._nav and hasattr(self._nav, '_refresh_ui'):
            self._nav.update_idletasks()
            self._nav._refresh_ui()
