"""Tab de configuración de Variantes de tipos de producción.

UI con chips de tipos (izquierda) y lista de variantes del tipo seleccionado (derecha).
Los tipos provienen de los menús configurados, ordenados por menú y tipo.
"""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import List, Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font, get_chip_config, get_chip_style
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.tipos_variantes_metodos_service import TiposVariantesMetodosService
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db


class ConfigTabVariantes:
    """Pestaña VARIANTES: chips de tipos (izq) | variantes del tipo (der)."""

    _CHIP_NORMAL = "#34495e"
    _CHIP_SELECTED = "#27ae60"

    def __init__(self, parent, config_service, config, colors, km, layout_config):
        self.parent = parent
        self.config_service = config_service
        self.db = config_service.db
        self.service = ProduccionTiposVariantesService(self.db)
        self.metodos_service = TiposVariantesMetodosService(self.db)

        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config

        self._all_tipos = []
        self._tipo_selected_id = None
        self._tipo_chips = {}
        self._variante_id_edit = None
        self._variante_rows = {}
        self._metodo_vars = {} # {metodo_id: BooleanVar}
        self._grupos_tallas = {} # {nombre: id}
       
        self._chip_cfg = get_chip_config(config, "producto")

        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: chips de tipos (40%) ---
        frame_left = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tk.Label(frame_left, text="TIPOS (de menús)", font=get_font(self.config, "label"),
                 fg="#FFFFFF", bg="#34495e").pack(pady=(8, 4))

        self._tipos_scroll = ctk.CTkScrollableFrame(frame_left, fg_color="#2c3e50")
        self._tipos_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # --- DERECHA: variantes del tipo seleccionado (60%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        
        # Configurar grid para las 3 zonas (35% / 30% / 35%)
        frame_right.rowconfigure(0, weight=35) # Chips variantes
        frame_right.rowconfigure(1, weight=30) # Formulario datos
        frame_right.rowconfigure(2, weight=35) # Métodos impresión
        frame_right.columnconfigure(0, weight=1)

        # ZONA 1: Chips de variantes
        self._zona_variantes = tk.Frame(frame_right, bg="#34495e")
        self._zona_variantes.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        header_v = tk.Frame(self._zona_variantes, bg="#34495e")
        header_v.pack(fill="x", pady=(5, 2))
        self._lbl_tipo_nombre = tk.Label(header_v, text="Selecciona un tipo →",
                                          font=get_font(self.config, "label"),
                                          fg="#FFFFFF", bg="#34495e")
        self._lbl_tipo_nombre.pack(side=tk.LEFT)
        
        ButtonFactory.create_button(header_v, text="+ AÑADIR", 
                                  module="produccion", palette_key="secondary", style_key="action_confirm",
                                  width=80, height=28, command=self._nuevo_registro).pack(side=tk.RIGHT)

        self._variantes_scroll = ctk.CTkScrollableFrame(self._zona_variantes, fg_color="#2c3e50")
        self._variantes_scroll.pack(fill=tk.BOTH, expand=True, pady=(2, 5))

        # ZONA 2: Formulario de datos
        self._zona_form = tk.Frame(frame_right, bg="#1a252f", bd=1, relief="solid")
        self._zona_form.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self._build_formulario()

        # ZONA 3: Métodos de impresión
        self._frame_metodos = tk.Frame(frame_right, bg="#34495e")
        self._frame_metodos.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        tk.Label(self._frame_metodos, text="MÉTODOS DE IMPRESIÓN DISPONIBLES", 
                 font=get_font(self.config, "label"), fg="#FFFFFF", bg="#34495e").pack(pady=(8, 4))
        
        self._metodos_container = tk.Frame(self._frame_metodos, bg="#34495e")
        self._metodos_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._lbl_no_variante = tk.Label(self._metodos_container, text="Selecciona una variante para asignar métodos",
                                         font=get_font(self.config, "label"), fg="#95a5a6", bg="#34495e")
        self._lbl_no_variante.pack(pady=20)

        # Cargar tipos
        self._cargar_tipos()

    def _build_formulario(self):
        """Construye los widgets del formulario de edición/creación."""
        container = tk.Frame(self._zona_form, bg="#1a252f", padx=15, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Fila 1: Nombre
        f1 = tk.Frame(container, bg="#1a252f")
        f1.pack(fill="x", pady=2)
        tk.Label(f1, text="NOMBRE:", font=get_font(self.config, "label"), fg=self._text, bg="#1a252f", width=10, anchor="w").pack(side=tk.LEFT)
        self._ent_nombre = ctk.CTkEntry(f1, placeholder_text="Nombre de la variante...", height=32)
        self._ent_nombre.pack(side=tk.LEFT, fill="x", expand=True, padx=(5, 0))

        # Fila 2: Coste y PVPR
        f2 = tk.Frame(container, bg="#1a252f")
        f2.pack(fill="x", pady=4)
        
        tk.Label(f2, text="COSTE (€):", font=get_font(self.config, "label"), fg=self._text, bg="#1a252f", width=10, anchor="w").pack(side=tk.LEFT)
        self._ent_coste = ctk.CTkEntry(f2, placeholder_text="0.00", width=80, height=32)
        self._ent_coste.pack(side=tk.LEFT, padx=(5, 15))
        
        tk.Label(f2, text="PVPR (€):", font=get_font(self.config, "label"), fg=self._text, bg="#1a252f", width=8, anchor="w").pack(side=tk.LEFT)
        self._ent_pvp = ctk.CTkEntry(f2, placeholder_text="0.00", width=80, height=32)
        self._ent_pvp.pack(side=tk.LEFT, padx=(5, 0))

        # Fila 3: Checkboxes + Shopify
        f3 = tk.Frame(container, bg="#1a252f")
        f3.pack(fill="x", pady=4)
        
        self._var_talla = tk.BooleanVar()
        self._chk_talla = ctk.CTkCheckBox(f3, text="REQ. TALLA", variable=self._var_talla, 
                                          font=get_font(self.config, "label"), height=24, checkbox_width=20, checkbox_height=20)
        self._chk_talla.pack(side=tk.LEFT, padx=(0, 15))
        
        self._var_color = tk.BooleanVar()
        self._chk_color = ctk.CTkCheckBox(f3, text="REQ. COLOR", variable=self._var_color,
                                          font=get_font(self.config, "label"), height=24, checkbox_width=20, checkbox_height=20)
        self._chk_color.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(f3, text="GRUPO:", font=get_font(self.config, "label"), fg=self._text, bg="#1a252f", width=6, anchor="w").pack(side=tk.LEFT)
        self._combo_grupo = ctk.CTkComboBox(f3, values=["NINGUNO"], height=30, width=150)
        self._combo_grupo.pack(side=tk.LEFT, padx=(5, 15))

        self._ent_shopify = ctk.CTkEntry(f3, placeholder_text="Shopify ID...", height=30)
        self._ent_shopify.pack(side=tk.LEFT, fill="x", expand=True)

        # Fila 4: Botones
        f4 = tk.Frame(container, bg="#1a252f")
        f4.pack(fill="x", pady=(10, 0))
        
        self._btn_guardar = ButtonFactory.create_button(f4, text="GUARDAR", 
                                                      module="produccion", palette_key="primary", style_key="action_confirm",
                                                      height=36, command=self._guardar_edicion)
        self._btn_guardar.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        
        self._btn_eliminar = ButtonFactory.create_button(f4, text="ELIMINAR", 
                                                       module="produccion", palette_key="accent", style_key="action_confirm",
                                                       height=36, command=self._confirmar_eliminar)
        self._btn_eliminar.pack(side=tk.LEFT, fill="x", expand=True, padx=(5, 0))

    def _cargar_tipos(self):
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipo_chips = {}

        # Cargar grupos de tallas para el combo
        grupos = self.config_service.obtener_todos_grupos_tallas()
        self._grupos_tallas = {g.nombre: g.id for g in grupos}
        self._combo_grupo.configure(values=["NINGUNO"] + sorted(self._grupos_tallas.keys()))

        self._all_tipos = self.config_service.obtener_tipos_de_menus_ordenados(solo_con_stock=False)

        if not self._all_tipos:
            tk.Label(self._tipos_scroll, text="No hay tipos en ningún menú",
                     font=get_font(self.config, "label"),
                     fg="#95a5a6", bg="#2c3e50").pack(pady=20)
            return

        cols = self._chip_cfg.get("columns", 2)
        default_style = get_chip_style(self._chip_cfg, "default")
        font_family = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])
        chip_height = self._chip_cfg.get("height", 40)
        corner_radius = self._chip_cfg.get("corner_radius", 8)

        grid_frame = tk.Frame(self._tipos_scroll, bg="#2c3e50")
        grid_frame.pack(fill="x", expand=True)

        for idx, tipo in enumerate(self._all_tipos):
            is_selected = tipo.id == self._tipo_selected_id
            chip = ctk.CTkButton(
                grid_frame,
                text=tipo.nombre,
                width=100,
                height=32,
                corner_radius=8,
                font=chip_font,
                fg_color=default_style.get("bg", "#1a1a2e"),
                text_color=default_style.get("text", "#e0e0e0"),
                border_color=default_style.get("border", "#552583"),
                border_width=1,
                hover_color=default_style.get("hover", "#C77BFF"),
                command=lambda tid=tipo.id: self._select_tipo(tid)
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self._tipo_chips[tipo.id] = chip

        for j in range(cols):
            grid_frame.columnconfigure(j, weight=1)

        for i in range(cols):
            self._tipos_scroll.columnconfigure(i, weight=1)

    def _select_tipo(self, tipo_id):
        self._tipo_selected_id = tipo_id
        default_style = get_chip_style(self._chip_cfg, "default")
        selected_style = get_chip_style(self._chip_cfg, "selected")
        for tid, chip in self._tipo_chips.items():
            is_sel = (tid == tipo_id)
            chip.configure(
                fg_color=selected_style.get("bg", "#552583") if is_sel else default_style.get("bg", "#1a1a2e"),
                text_color=selected_style.get("text", "#ffffff") if is_sel else default_style.get("text", "#e0e0e0"),
                border_color=selected_style.get("border", "#C77BFF") if is_sel else default_style.get("border", "#552583"),
                border_width=2 if is_sel else 1
            )
        self._cargar_variantes()

    def _cargar_variantes(self):
        for child in self._variantes_scroll.winfo_children():
            child.destroy()
        self._variante_rows = {}
        self._variante_id_edit = None
        
        # Resetear formulario
        self._ent_nombre.delete(0, tk.END)
        self._ent_coste.delete(0, tk.END)
        self._ent_pvp.delete(0, tk.END)
        self._ent_shopify.delete(0, tk.END)
        self._var_talla.set(False)
        self._var_color.set(False)

        # Resetear sección de métodos al placeholder
        for child in self._metodos_container.winfo_children():
            child.destroy()
        self._metodo_vars = {}
        self._lbl_no_variante = tk.Label(self._metodos_container, text="Selecciona una variante para asignar métodos",
                                         font=get_font(self.config, "label"), fg="#95a5a6", bg="#34495e")
        self._lbl_no_variante.pack(pady=20)

        if not self._tipo_selected_id:
            self._lbl_tipo_nombre.configure(text="Selecciona un tipo →")
            return

        tipo = next((t for t in self._all_tipos if t.id == self._tipo_selected_id), None)
        tipo_nombre = tipo.nombre if tipo else "???"
        self._lbl_tipo_nombre.configure(text=f"Variantes de: {tipo_nombre}")

        variantes = self.service.obtener_por_tipo(self._tipo_selected_id, solo_activos=False)

        if not variantes:
            tk.Label(self._variantes_scroll, text="No hay variantes para este tipo",
                     font=get_font(self.config, "label"),
                     fg="#95a5a6", bg="#2c3e50").pack(pady=20)
            return

        # Configuración de chips de variantes (6 columnas)
        cols = 6
        padx = 4
        pady = 4
        corner_radius = 8
        
        default_style = get_chip_style(self._chip_cfg, "default")
        font_family = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        chip_font = (font_family[0], 11, font_family[2])

        grid_frame = tk.Frame(self._variantes_scroll, bg="#2c3e50")
        grid_frame.pack(fill="x", expand=True)

        for i, v in enumerate(variantes):
            btn = ctk.CTkButton(
                grid_frame,
                text=v.nombre,
                width=80,
                height=32,
                corner_radius=corner_radius,
                font=chip_font,
                fg_color=default_style.get("bg", "#1a1a2e"),
                text_color=default_style.get("text", "#e0e0e0"),
                border_color=default_style.get("border", "#552583"),
                border_width=1,
                command=lambda vid=v.id: self._select_variante(vid)
            )
            row = i // cols
            col = i % cols
            btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="ew")
            self._variante_rows[v.id] = btn

        for j in range(cols):
            grid_frame.columnconfigure(j, weight=1)

    def _select_variante(self, variante_id):
        self._variante_id_edit = variante_id
        
        selected_style = get_chip_style(self._chip_cfg, "selected")
        default_style = get_chip_style(self._chip_cfg, "default")

        for vid, btn in self._variante_rows.items():
            is_sel = (vid == variante_id)
            btn.configure(
                fg_color=selected_style.get("bg", "#552583") if is_sel else default_style.get("bg", "#1a1a2e"),
                border_color=selected_style.get("border", "#C77BFF") if is_sel else default_style.get("border", "#552583"),
                border_width=2 if is_sel else 1
            )
        
        # Cargar datos en el formulario
        v = self.service.obtener_por_id(variante_id)
        if v:
            self._ent_nombre.delete(0, tk.END)
            self._ent_nombre.insert(0, v.nombre)
            
            self._ent_coste.delete(0, tk.END)
            self._ent_coste.insert(0, f"{read_from_db(v.coste_base):.2f}")
            
            self._ent_pvp.delete(0, tk.END)
            self._ent_pvp.insert(0, f"{read_from_db(v.precio_recomendado):.2f}")
            
            self._ent_shopify.delete(0, tk.END)
            self._ent_shopify.insert(0, v.shopify_variant_id or "")
            
            self._var_talla.set(bool(v.requiere_talla))
            self._var_color.set(bool(v.requiere_color))
            
            # Seleccionar grupo en combo
            if v.grupo_talla_id:
                nombre_grupo = next((n for n, gid in self._grupos_tallas.items() if gid == v.grupo_talla_id), "NINGUNO")
                self._combo_grupo.set(nombre_grupo)
            else:
                self._combo_grupo.set("NINGUNO")

        # Ocultar label de aviso si existe y sigue vivo
        if hasattr(self, '_lbl_no_variante') and self._lbl_no_variante.winfo_exists():
            self._lbl_no_variante.pack_forget()

        self._cargar_metodos_variante(variante_id)

    def _nuevo_registro(self):
        """Prepara el formulario para crear una nueva variante."""
        if not self._tipo_selected_id:
            ToastWidget.show(self.parent, "Selecciona un tipo primero", tipo="warning")
            return
            
        self._variante_id_edit = None
        # Deseleccionar chips
        default_style = get_chip_style(self._chip_cfg, "default")
        for btn in self._variante_rows.values():
            btn.configure(
                fg_color=default_style.get("bg", "#1a1a2e"),
                border_color=default_style.get("border", "#552583"),
                border_width=1
            )
            
        # Limpiar formulario
        self._ent_nombre.delete(0, tk.END)
        self._ent_coste.delete(0, tk.END)
        self._ent_pvp.delete(0, tk.END)
        self._ent_shopify.delete(0, tk.END)
        self._var_talla.set(False)
        self._var_color.set(False)
        
        self._ent_nombre.focus_set()
        ToastWidget.show(self.parent, "Introduce datos para nueva variante", tipo="info")

    def _confirmar_eliminar(self):
        if not self._variante_id_edit:
            return
            
        if tk.messagebox.askyesno("Eliminar", "¿Estás seguro de eliminar esta variante?"):
            if self.service.eliminar(self._variante_id_edit):
                ToastWidget.show(self.parent, "Variante eliminada", tipo="success")
                self._cargar_variantes()
            else:
                ToastWidget.show(self.parent, "Error al eliminar", tipo="error")

    def _cargar_metodos_variante(self, variante_id):
        """Cargar los métodos de la variante y mostrarlos como chips interactivos."""
        for child in self._metodos_container.winfo_children():
            child.destroy()
        
        self._metodo_states = {} # {metodo_id: bool}
        self._metodo_chips = {}  # {metodo_id: ctk.CTkButton}

        todos = self.metodos_service.obtener_metodos_activos()
        asignados = self.metodos_service.obtener_metodos_por_variante(variante_id)
        asignados_ids = {m["id"] for m in asignados}

        if not todos:
            tk.Label(self._metodos_container, text="No hay métodos activos en la BD",
                     font=get_font(self.config, "label"), fg="#e74c3c", bg="#34495e").pack(pady=10)
            return

        # Configuración de chips
        cols = self._chip_cfg.get("columns", 5)
        padx = self._chip_cfg.get("padx", 6)
        pady = self._chip_cfg.get("pady", 6)
        chip_height = 36 # Más compacto para el taller
        corner_radius = self._chip_cfg.get("corner_radius", 16)
        
        default_style = get_chip_style(self._chip_cfg, "default")
        selected_style = get_chip_style(self._chip_cfg, "selected")
        font_family = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        chip_font = (font_family[0], 12, font_family[2]) # Fuente algo más pequeña

        # Frame contenedor
        grid_frame = tk.Frame(self._metodos_container, bg="#34495e")
        grid_frame.pack(pady=5, fill="x")

        for i, m in enumerate(todos):
            is_selected = m["id"] in asignados_ids
            self._metodo_states[m["id"]] = is_selected
            
            btn = ctk.CTkButton(
                grid_frame,
                text=m["nombre"],
                width=100,
                height=chip_height,
                corner_radius=corner_radius,
                font=chip_font,
                fg_color=selected_style.get("bg", "#552583") if is_selected else default_style.get("bg", "#1a1a2e"),
                text_color=selected_style.get("text", "#ffffff") if is_selected else default_style.get("text", "#e0e0e0"),
                border_color=selected_style.get("border", "#C77BFF") if is_selected else default_style.get("border", "#552583"),
                border_width=2 if is_selected else 1,
                hover_color=selected_style.get("hover", "#8e44ad") if is_selected else default_style.get("hover", "#C77BFF"),
                command=lambda mid=m["id"]: self._toggle_metodo(mid)
            )
            row = i // cols
            col = i % cols
            btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="ew")
            self._metodo_chips[m["id"]] = btn

        for j in range(cols):
            grid_frame.columnconfigure(j, weight=1)

    def _toggle_metodo(self, metodo_id):
        """Alternar estado de selección de un método."""
        new_state = not self._metodo_states[metodo_id]
        self._metodo_states[metodo_id] = new_state
        
        btn = self._metodo_chips[metodo_id]
        default_style = get_chip_style(self._chip_cfg, "default")
        selected_style = get_chip_style(self._chip_cfg, "selected")
        
        if new_state:
            btn.configure(
                fg_color=selected_style.get("bg", "#552583"),
                text_color=selected_style.get("text", "#ffffff"),
                border_color=selected_style.get("border", "#C77BFF"),
                border_width=2
            )
        else:
            btn.configure(
                fg_color=default_style.get("bg", "#1a1a2e"),
                text_color=default_style.get("text", "#e0e0e0"),
                border_color=default_style.get("border", "#552583"),
                border_width=1
            )

    def _guardar_edicion(self):
        """Guarda los cambios de una variante existente o crea una nueva."""
        if not self._tipo_selected_id:
            return

        nombre = self._ent_nombre.get().strip()
        if not nombre:
            ToastWidget.show(self.parent, "El nombre es obligatorio", tipo="warning")
            return

        # Refrescar grupos antes de guardar para asegurar que el mapeo está al día
        grupos = self.config_service.obtener_todos_grupos_tallas()
        self._grupos_tallas = {g.nombre: g.id for g in grupos}

        try:
            coste_val = float(self._ent_coste.get().replace(",", ".") or "0")
            pvp_val = float(self._ent_pvp.get().replace(",", ".") or "0")
            coste_cents = prepare_for_db(coste_val)
            pvp_cents = prepare_for_db(pvp_val)
        except ValueError:
            ToastWidget.show(self.parent, "Coste y PVPR deben ser numéricos", tipo="error")
            return

        shopify_id = self._ent_shopify.get().strip() or None
        req_talla = 1 if self._var_talla.get() else 0
        req_color = 1 if self._var_color.get() else 0
        
        grupo_nombre = self._combo_grupo.get()
        grupo_id = self._grupos_tallas.get(grupo_nombre)
        
        logging.info(f"Guardando variante: '{nombre}' | Grupo: '{grupo_nombre}' -> ID: {grupo_id}")

        if self._variante_id_edit:
            # ACTUALIZAR EXISTENTE
            ok = self.service.actualizar(
                self._variante_id_edit, self._tipo_selected_id, nombre,
                coste_cents, pvp_cents, 1, shopify_id, req_talla, req_color,
                grupo_id
            )
            
            # Sincronizar métodos
            metodos_seleccionados = [mid for mid, val in self._metodo_states.items() if val]
            self.metodos_service.sincronizar_metodos(self._variante_id_edit, metodos_seleccionados)
            
            if ok:
                ToastWidget.show(self.parent, "Variante actualizada", tipo="success")
                self._cargar_variantes()
                self._select_variante(self._variante_id_edit)
            else:
                ToastWidget.show(self.parent, "Error al actualizar", tipo="error")
        else:
            # CREAR NUEVA
            res_id = self.service.crear(
                self._tipo_selected_id, nombre, coste_cents, pvp_cents,
                shopify_id, req_talla, req_color, grupo_id
            )
            if res_id:
                ToastWidget.show(self.parent, "Nueva variante creada", tipo="success")
                self._cargar_variantes()
                self._select_variante(res_id)
            else:
                ToastWidget.show(self.parent, "Error al crear variante", tipo="error")

    def refresh_nav(self):
        pass
