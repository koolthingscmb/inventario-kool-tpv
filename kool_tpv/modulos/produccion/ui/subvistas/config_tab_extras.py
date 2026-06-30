"""Tab de configuración de extras de producción."""
import tkinter as tk
import customtkinter as ctk
from typing import Optional, List

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.modulos.produccion.services.produccion_extras_service import ProduccionExtrasService, ProduccionExtra
from kool_tpv.base_datos.money_adapter import read_from_db, prepare_for_db
from kool_tpv.utils.custom_dialog import show_warning, show_error

class ConfigTabExtras:
    """Sub-pestaña EXTRAS: chips + formulario CRUD."""

    def __init__(self, parent, db, config, colors, km, layout_config):
        self.parent = parent
        self.db = db
        self.service = ProduccionExtrasService(db)
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._text_sec = colors.get("secondary", "#bdc3c7")
        self._km = km
        self._layout_config = layout_config
        
        self._extra_seleccionado: Optional[ProduccionExtra] = None
        self._extras_cache: List[ProduccionExtra] = []

        self.build()

    def build(self):
        self.content = tk.Frame(self.parent, bg=self._bg)
        self.content.pack(fill=tk.BOTH, expand=True)

        # --- Contenedor de Chips (Superior) ---
        chips_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        chips_frame.pack(fill="x", padx=20, pady=(10, 20))

        tk.Label(chips_frame, text="EXTRAS REGISTRADOS", font=get_font(self.config, "label"),
                 fg=self._text_sec, bg=self._bg).pack(anchor="w", pady=(0, 10))

        self._frame_chips = ctk.CTkFrame(chips_frame, fg_color="#34495e", height=100)
        self._frame_chips.pack(fill="x")
        
        # --- Formulario (Inferior) ---
        self._frame_form = ctk.CTkFrame(self.content, fg_color="#34495e", corner_radius=12)
        self._frame_form.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Título del formulario
        self._lbl_form_title = ctk.CTkLabel(
            self._frame_form, text="CREAR NUEVO EXTRA", 
            font=get_font(self.config, "title"),
            text_color=self._text
        )
        self._lbl_form_title.pack(pady=20)

        # Grid para campos
        grid_frame = ctk.CTkFrame(self._frame_form, fg_color="transparent")
        grid_frame.pack(fill="x", padx=40)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        # Fila 1: Nombre y Coste
        self._entry_nombre = ctk.CTkEntry(grid_frame, placeholder_text="Nombre (ej. MIXTA)", height=45)
        self._entry_nombre.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")

        self._entry_coste = ctk.CTkEntry(grid_frame, placeholder_text="Coste extra (€)", height=45)
        self._entry_coste.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="ew")

        # Fila 2: Descripción (colspan 2)
        self._entry_desc = ctk.CTkEntry(grid_frame, placeholder_text="Descripción corta", height=45)
        self._entry_desc.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        # Fila 3: Activo
        self._switch_activo = ctk.CTkSwitch(grid_frame, text="Extra Activo", font=get_font(self.config, "label"))
        self._switch_activo.grid(row=2, column=0, pady=10, sticky="w")
        self._switch_activo.select()

        # Botones de Acción
        btn_frame = ctk.CTkFrame(self._frame_form, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=30)

        self._btn_guardar = ctk.CTkButton(
            btn_frame, text="GUARDAR EXTRA", 
            fg_color="#27ae60", hover_color="#2ecc71",
            height=50, font=get_font(self.config, "label"),
            command=self._guardar
        )
        self._btn_guardar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._btn_nuevo = ctk.CTkButton(
            btn_frame, text="AÑADIR EXTRA", 
            fg_color="#2980b9", hover_color="#3498db",
            height=50, font=get_font(self.config, "label"),
            command=self._limpiar
        )
        self._btn_nuevo.pack(side="left", fill="x", expand=True, padx=10)

        self._btn_eliminar = ctk.CTkButton(
            btn_frame, text="ELIMINAR EXTRA", 
            fg_color="#e74c3c", hover_color="#c0392b",
            height=50, font=get_font(self.config, "label"),
            command=self._eliminar
        )
        self._btn_eliminar.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self._cargar_y_renderizar_chips()

    def _cargar_y_renderizar_chips(self):
        """Carga los extras de la BD y los dibuja como chips."""
        self._extras_cache = self.service.get_todos()
        
        for w in self._frame_chips.winfo_children():
            w.destroy()

        # Config de chips desde config_produccion.json
        chips_cfg = self.config.get("chips", {}).get("diseno", {})
        default_cfg = chips_cfg.get("default", {})
        selected_cfg = chips_cfg.get("selected", {})

        container = ctk.CTkFrame(self._frame_chips, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        for extra in self._extras_cache:
            is_selected = (self._extra_seleccionado and self._extra_seleccionado.id == extra.id)
            
            bg_color = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
            text_color = selected_cfg.get("text", "#ffffff") if is_selected else default_cfg.get("text", "#e0e0e0")
            border_color = selected_cfg.get("border", "#C77BFF") if is_selected else default_cfg.get("border", "#552583")
            hover_color = selected_cfg.get("hover", "#8e44ad") if is_selected else default_cfg.get("hover", "#C77BFF")

            chip = ctk.CTkButton(
                container,
                text=f"{extra.nombre} (+{read_from_db(extra.coste):.2f}€)",
                width=0,
                height=36,
                corner_radius=18,
                fg_color=bg_color,
                text_color=text_color,
                border_color=border_color,
                border_width=2 if is_selected else 1,
                hover_color=hover_color,
                font=get_font(self.config, "label"),
                command=lambda e=extra: self._on_chip_click(e)
            )
            chip.pack(side="left", padx=6, pady=4)

    def _on_chip_click(self, extra: ProduccionExtra):
        """Al pulsar un chip, cargar sus datos en el formulario."""
        self._extra_seleccionado = extra
        self._lbl_form_title.configure(text=f"EDITANDO EXTRA: {extra.nombre}")
        
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, extra.nombre)
        
        self._entry_coste.delete(0, tk.END)
        self._entry_coste.insert(0, f"{read_from_db(extra.coste):.2f}")
        
        self._entry_desc.delete(0, tk.END)
        self._entry_desc.insert(0, extra.descripcion or "")
        
        if extra.activo:
            self._switch_activo.select()
        else:
            self._switch_activo.deselect()
            
        self._cargar_y_renderizar_chips()

    def _limpiar(self):
        """Limpia el formulario para crear uno nuevo."""
        self._extra_seleccionado = None
        self._lbl_form_title.configure(text="CREAR NUEVO EXTRA")
        
        self._entry_nombre.delete(0, tk.END)
        self._entry_coste.delete(0, tk.END)
        self._entry_desc.delete(0, tk.END)
        self._switch_activo.select()
        
        self._cargar_y_renderizar_chips()

    def _guardar(self):
        nombre = self._entry_nombre.get().strip()
        coste_str = self._entry_coste.get().strip().replace(",", ".")
        desc = self._entry_desc.get().strip()
        activo = 1 if self._switch_activo.get() else 0

        if not nombre:
            show_error(self.content, "Error", "El nombre es obligatorio")
            return

        try:
            coste_val = float(coste_str) if coste_str else 0.0
            coste_cents = prepare_for_db(coste_val)
        except ValueError:
            show_error(self.content, "Error", "El coste debe ser un número válido")
            return

        extra = self._extra_seleccionado or ProduccionExtra()
        extra.nombre = nombre
        extra.coste = coste_cents
        extra.descripcion = desc
        extra.activo = activo

        ok = self.service.guardar_extra(extra)
        if ok:
            self._limpiar()
            self._cargar_y_renderizar_chips()
        else:
            show_error(self.content, "Error", "No se pudo guardar el extra (nombre duplicado?)")

    def _eliminar(self):
        if not self._extra_seleccionado:
            return
            
        def _confirmar():
            ok = self.service.eliminar_extra(self._extra_seleccionado.id)
            if ok:
                self._limpiar()
            else:
                show_error(self.content, "Error", "No se pudo eliminar")

        show_warning(self.content, "Confirmar", f"¿Eliminar el extra '{self._extra_seleccionado.nombre}'?", callback=_confirmar)
