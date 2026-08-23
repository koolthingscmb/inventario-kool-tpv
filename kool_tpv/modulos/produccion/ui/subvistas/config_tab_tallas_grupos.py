"""Tab de configuración de grupos de tallas del taller."""
import tkinter as tk
import tkinter.messagebox
import customtkinter as ctk
from typing import List, Dict, Set

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.utils.dialogs.input_dialog import InputDialog
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget

class ConfigTabTallasGrupos:
    """Sub-pestaña GRUPOS TALLAS: chips de tallas (izq) + chips de grupos (der)."""

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        
        self._grupo_id_sel = None
        self._tallas = {} # id -> model
        self._tallas_order = []
        self._grupos = {} # id -> model
        self._grupos_order = []
        
        self._chip_tallas_widgets = {}
        self._chip_grupos_widgets = {}
        self._tallas_seleccionadas = set() # Set de talla_id
        
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- TALLAS (Izquierda 50%) ---
        frame_tallas = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_tallas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(frame_tallas, text="SELECCIONAR TALLAS", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(8, 3), padx=8, anchor="w")

        self._scroll_tallas = ctk.CTkScrollableFrame(frame_tallas, fg_color="#34495e")
        self._scroll_tallas.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # --- GRUPOS (Derecha 50%) ---
        frame_grupos = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_grupos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        header_grupos = tk.Frame(frame_grupos, bg="#34495e")
        header_grupos.pack(fill=tk.X, pady=(8, 3), padx=8)

        tk.Label(header_grupos, text="GRUPOS", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(side=tk.LEFT)

        btn_mas = ctk.CTkButton(header_grupos, text="+ GRUPO", width=80, height=28,
                               fg_color="#27ae60", hover_color="#2ecc71",
                               command=self._crear_grupo)
        btn_mas.pack(side=tk.RIGHT)

        self._scroll_grupos = ctk.CTkScrollableFrame(frame_grupos, fg_color="#34495e")
        self._scroll_grupos.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # --- Footer de la zona derecha ---
        footer_grupos = tk.Frame(frame_grupos, bg="#34495e")
        footer_grupos.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=8)

        self._btn_guardar = ctk.CTkButton(footer_grupos, text="GUARDAR ASOCIACIÓN", 
                                        fg_color="#2980b9", hover_color="#3498db",
                                        state="disabled",
                                        command=self._guardar_asociacion)
        self._btn_guardar.pack(side=tk.RIGHT, padx=(5, 0))

        self._btn_eliminar = ctk.CTkButton(footer_grupos, text="ELIMINAR GRUPO", 
                                         fg_color="#e74c3c", hover_color="#c0392b",
                                         state="disabled",
                                         command=self._eliminar_grupo)
        self._btn_eliminar.pack(side=tk.LEFT)

        self._cargar_datos()

    def _cargar_datos(self, select_grupo_id=None):
        # Limpiar widgets
        for child in self._scroll_tallas.winfo_children(): child.destroy()
        for child in self._scroll_grupos.winfo_children(): child.destroy()
        self._chip_tallas_widgets = {}
        self._chip_grupos_widgets = {}
        
        # Cargar Tallas
        tallas = self.service.obtener_todas_tallas()
        self._tallas = {t.id: t for t in tallas}
        self._tallas_order = [t.id for t in tallas]

        # Cargar Grupos
        grupos = self.service.obtener_todos_grupos_tallas()
        self._grupos = {g.id: g for g in grupos}
        self._grupos_order = [g.id for g in grupos]

        # Estilos chips
        chips_cfg = self.config.get("chips", {})
        self._style_default = chips_cfg.get("default", {"bg": "#1a1a2e", "text_color": "#cccccc", "border_color": "#333333"})
        self._style_selected = chips_cfg.get("selected", {"bg": "#552583", "text_color": "#ffffff", "border_color": "#8888ff"})
        self._style_active = {"bg": "#27ae60", "text_color": "#ffffff", "border_color": "#2ecc71"} # Para tallas marcadas

        # Grid tallas (4 columnas)
        for c in range(4): self._scroll_tallas.grid_columnconfigure(c, weight=1)
        for i, tid in enumerate(self._tallas_order):
            t = self._tallas[tid]
            chip = ctk.CTkButton(self._scroll_tallas, text=t.nombre, font=get_font(self.config, "label"),
                               fg_color=self._style_default["bg"], text_color=self._style_default["text_color"],
                               border_color=self._style_default["border_color"], border_width=1,
                               corner_radius=8, height=36, hover_color=self._style_default["bg"])
            chip.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="nsew")
            chip.bind("<Button-1>", lambda e, t=tid: self._toggle_talla(t))
            self._chip_tallas_widgets[tid] = chip

        # Grid grupos (2 columnas)
        for c in range(2): self._scroll_grupos.grid_columnconfigure(c, weight=1)
        for i, gid in enumerate(self._grupos_order):
            g = self._grupos[gid]
            chip = ctk.CTkButton(self._scroll_grupos, text=g.nombre, font=get_font(self.config, "label"),
                               fg_color=self._style_default["bg"], text_color=self._style_default["text_color"],
                               border_color=self._style_default["border_color"], border_width=1,
                               corner_radius=8, height=36, hover_color=self._style_default["bg"])
            chip.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
            chip.bind("<Button-1>", lambda e, g=gid: self._select_grupo(g))
            self._chip_grupos_widgets[gid] = chip

        if select_grupo_id:
            self._select_grupo(select_grupo_id)
        elif self._grupo_id_sel:
            self._select_grupo(self._grupo_id_sel)

    def _select_grupo(self, grupo_id):
        self._grupo_id_sel = grupo_id
        grupo = self._grupos.get(grupo_id)
        if not grupo: return

        # Actualizar visual grupos
        for gid, chip in self._chip_grupos_widgets.items():
            is_sel = (gid == grupo_id)
            style = self._style_selected if is_sel else self._style_default
            chip.configure(fg_color=style["bg"], text_color=style["text_color"], 
                         border_color=style["border_color"], border_width=2 if is_sel else 1,
                         hover_color=style["bg"])

        # Cargar tallas del grupo
        self._tallas_seleccionadas = set(grupo.talla_ids)
        self._update_tallas_ui()
        
        self._btn_guardar.configure(state="normal")
        self._btn_eliminar.configure(state="normal")

    def _toggle_talla(self, talla_id):
        if not self._grupo_id_sel:
            ToastWidget.show(self.parent, "Selecciona un grupo primero", "warning")
            return
            
        if talla_id in self._tallas_seleccionadas:
            self._tallas_seleccionadas.remove(talla_id)
        else:
            self._tallas_seleccionadas.add(talla_id)
        
        self._update_tallas_ui()

    def _update_tallas_ui(self):
        for tid, chip in self._chip_tallas_widgets.items():
            is_active = (tid in self._tallas_seleccionadas)
            style = self._style_active if is_active else self._style_default
            chip.configure(fg_color=style["bg"], text_color=style["text_color"],
                         border_color=style["border_color"], border_width=2 if is_active else 1,
                         hover_color=style["bg"])

    def _crear_grupo(self):
        d = InputDialog(self.parent, "Nuevo Grupo", "Nombre del grupo (ej: Hombre, Mujer...):")
        nombre = d.get_input()
        if nombre:
            gid = self.service.guardar_grupo_tallas(nombre)
            if gid:
                self._cargar_datos(select_grupo_id=gid)
                ToastWidget.show(self.parent, f"Grupo '{nombre}' creado", "success")

    def _eliminar_grupo(self):
        if not self._grupo_id_sel: return
        grupo = self._grupos.get(self._grupo_id_sel)
        if not grupo: return
        
        if tk.messagebox.askyesno("Confirmar", f"¿Eliminar el grupo '{grupo.nombre}'?"):
            if self.service.eliminar_grupo_tallas(self._grupo_id_sel):
                self._grupo_id_sel = None
                self._btn_guardar.configure(state="disabled")
                self._btn_eliminar.configure(state="disabled")
                self._cargar_datos()
                ToastWidget.show(self.parent, "Grupo eliminado", "success")

    def _guardar_asociacion(self):
        if not self._grupo_id_sel: return
        talla_ids = list(self._tallas_seleccionadas)
        if self.service.guardar_asociaciones_grupo_tallas(self._grupo_id_sel, talla_ids):
            # Actualizar el modelo local
            if self._grupo_id_sel in self._grupos:
                self._grupos[self._grupo_id_sel].talla_ids = talla_ids
            ToastWidget.show(self.parent, "Asociación guardada correctamente", "success")

    def refresh_nav(self):
        self._cargar_datos(self._grupo_id_sel)
