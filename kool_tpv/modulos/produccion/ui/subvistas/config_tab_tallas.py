"""Tab de configuración de tallas del taller."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font


class ConfigTabTallas:
    """Sub-pestaña TALLAS: chips horizontales + formulario."""

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        self._talla_id_edit = None
        self._chip_widgets = {}
        self._tallas = {}
        self._tallas_order = []
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Chips de tallas (izquierda) ---
        frame_chips = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_chips.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(frame_chips, text="TALLAS", font=get_font(self.config, "label"),
                 fg="#FFFFFF", bg="#34495e").pack(pady=(8, 3), padx=8, anchor="w")

        self._chips_scroll = ctk.CTkScrollableFrame(frame_chips, fg_color="#34495e")
        self._chips_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear talla", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._entry_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre (S, M, L, XL...)", width=250)
        self._entry_nombre.pack(pady=5, padx=20)

        self._var_activo = ctk.IntVar(value=1)
        
        # Obtener color primario para el checkbox
        module_colors = ButtonFactory.get_module_colors("produccion")
        primary_color = module_colors.get("primary", "#552583")
        
        ctk.CTkCheckBox(frame_form, text="Activo", variable=self._var_activo,
                        fg_color=primary_color, 
                        hover_color=primary_color,
                        text_color=self._text).pack(pady=5, padx=20, anchor="w")

        frame_reorder = tk.Frame(frame_form, bg="#34495e")
        frame_reorder.pack(pady=(5, 0), padx=20, fill=tk.X)
        self.btn_izq = ButtonFactory.create_button(
            frame_reorder, text="◀ IZQUIERDA", 
            command=lambda: self._mover(-1),
            module="produccion",
            palette_key="secondary",
            style_key="action_confirm"
        )
        self.btn_izq.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        self.btn_der = ButtonFactory.create_button(
            frame_reorder, text="DERECHA ▶", 
            command=lambda: self._mover(1),
            module="produccion",
            palette_key="secondary",
            style_key="action_confirm"
        )
        self.btn_der.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        self.btn_guardar = ButtonFactory.create_button(
            frame_btns, text="GUARDAR", 
            command=self._guardar,
            module="produccion",
            palette_key="primary",
            style_key="action_confirm"
        )
        self.btn_guardar.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        self.btn_nuevo = ButtonFactory.create_button(
            frame_btns, text="NUEVO", 
            command=self._limpiar,
            module="produccion",
            palette_key="primary",
            style_key="action_confirm"
        )
        self.btn_nuevo.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        self.btn_eliminar = ButtonFactory.create_button(
            frame_form, text="ELIMINAR", 
            command=self._eliminar,
            module="produccion",
            palette_key="accent",
            style_key="action_confirm"
        )
        self.btn_eliminar.pack(pady=(0, 10), padx=20, fill=tk.X)

        # --- Añadir múltiples tallas ---
        tk.Label(frame_form, text="Añadir varias\n(separadas por coma):",
                 font=get_font(self.config, "small"), fg=self._text, bg="#34495e", justify="left").pack(pady=(5, 2), padx=20, anchor="w")
        self._entry_bulk = ctk.CTkEntry(frame_form, placeholder_text="S, M, L, XL, XXL...", width=250)
        self._entry_bulk.pack(pady=2, padx=20, fill=tk.X)
        self._entry_bulk.bind('<Return>', lambda e: self._anadir_bulk())
        
        self.btn_bulk = ButtonFactory.create_button(
            frame_form, text="AÑADIR VARIAS", 
            command=self._anadir_bulk,
            module="produccion",
            palette_key="primary",
            style_key="action_confirm"
        )
        self.btn_bulk.pack(pady=(2, 15), padx=20, fill=tk.X)

        self._cargar_chips()

    def _cargar_chips(self, select_id=None):
        for child in self._chips_scroll.winfo_children():
            child.destroy()
        self._chip_widgets = {}
        self._tallas = {}
        self._tallas_order = []

        tallas = self.service.obtener_todas_tallas()
        for t in tallas:
            self._tallas[t.id] = t
            self._tallas_order.append(t.id)

        # Configurar grid de 8 columnas
        for c in range(8):
            self._chips_scroll.grid_columnconfigure(c, weight=1)

        # Estilos chips unificados
        self._chip_style_default = {
            "bg": "#1a1a2e",
            "text": "#cccccc",
            "border": "#333333",
            "hover": "#C77BFF"
        }
        self._chip_style_selected = {
            "bg": "#552583",
            "text": "#ffffff",
            "border": "#C77BFF",
            "hover": "#8E44AD"
        }

        for i, tid in enumerate(self._tallas_order):
            talla = self._tallas[tid]
            row = i // 8
            col = i % 8
            
            is_selected = (tid == self._talla_id_edit)
            style = self._chip_style_selected if is_selected else self._chip_style_default
            
            chip = ctk.CTkButton(
                self._chips_scroll,
                text=talla.nombre,
                font=get_font(self.config, "label"),
                fg_color=style["bg"],
                text_color=style["text"],
                border_color=style["border"],
                border_width=2 if is_selected else 1,
                corner_radius=8,
                height=36,
                hover_color=style["hover"]
            )
            chip.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            chip.bind("<Button-1>", lambda e, t=tid: self._select_chip(t))
            self._chip_widgets[tid] = chip

    def _select_chip(self, talla_id):
        self._talla_id_edit = talla_id
        talla = self._tallas.get(talla_id)
        if talla:
            self._entry_nombre.delete(0, tk.END)
            self._entry_nombre.insert(0, talla.nombre)
            self._var_activo.set(talla.activo)

        # Actualizar estilos de chips
        for tid, chip in self._chip_widgets.items():
            is_sel = (tid == talla_id)
            style = self._chip_style_selected if is_sel else self._chip_style_default
            chip.configure(
                fg_color=style["bg"],
                text_color=style["text"],
                border_color=style["border"],
                border_width=2 if is_sel else 1,
                hover_color=style["hover"]
            )

    def _mover(self, direccion: int):
        if not self._talla_id_edit:
            return
        talla_id = self._talla_id_edit
        ok = self.service.mover_talla(talla_id, direccion)
        if ok:
            self._cargar_chips(select_id=talla_id)

    def _guardar(self):
        nombre = self._entry_nombre.get().strip()
        if not nombre:
            return
        activo = self._var_activo.get()
        ok = self.service.guardar_talla(nombre, 0, activo, self._talla_id_edit)
        if ok:
            self._limpiar()
            self._cargar_chips()

    def _limpiar(self):
        self._talla_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._var_activo.set(1)
        chips_cfg = self.config.get("chips", {})
        default_cfg = chips_cfg.get("default", {})
        for tid, chip in self._chip_widgets.items():
            chip.configure(
                fg_color=default_cfg.get("bg", "#1a1a2e"),
                text_color=default_cfg.get("text_color", "#cccccc"),
                border_color=default_cfg.get("border_color", "#333333"),
                border_width=default_cfg.get("border_width", 1),
                hover_color=default_cfg.get("bg", "#1a1a2e")
            )

    def _anadir_bulk(self):
        texto = self._entry_bulk.get().strip()
        if not texto:
            return
        nombres = [n.strip().upper() for n in texto.split(",") if n.strip()]
        if not nombres:
            return
        for nombre in nombres:
            self.service.guardar_talla(nombre, 0, 1, None)
        self._entry_bulk.delete(0, tk.END)
        self._limpiar()
        self._cargar_chips()

    def _eliminar(self):
        if self._talla_id_edit:
            self.service.tallas_repo.eliminar(self._talla_id_edit)
            self._limpiar()
            self._cargar_chips()

    def refresh_nav(self):
        self._cargar_chips()
