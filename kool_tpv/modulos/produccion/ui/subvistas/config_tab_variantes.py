"""Tab de configuración de Variantes de tipos de producción.

UI con chips de tipos (izquierda) y lista de variantes del tipo seleccionado (derecha).
Los tipos provienen de los menús configurados, ordenados por menú y tipo.
"""
import tkinter as tk
import customtkinter as ctk
from typing import List, Optional

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
       
        self._chip_cfg = get_chip_config(config, "producto")

        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: chips de tipos (40%) ---
        frame_left = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tk.Label(frame_left, text="TIPOS (de menús)", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(8, 4))

        self._tipos_scroll = ctk.CTkScrollableFrame(frame_left, fg_color="#2c3e50")
        self._tipos_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # --- DERECHA: variantes del tipo seleccionado (60%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Cabecera derecha: título + botón añadir
        header_right = tk.Frame(frame_right, bg="#34495e")
        header_right.pack(fill="x", padx=10, pady=(8, 4))

        self._lbl_tipo_nombre = tk.Label(header_right, text="Selecciona un tipo →",
                                          font=get_font(self.config, "label"),
                                          fg="#FFD700", bg="#34495e")
        self._lbl_tipo_nombre.pack(side=tk.LEFT)

        ctk.CTkButton(header_right, text="+ AÑADIR", fg_color="#2980b9", hover_color="#3498db",
                      width=100, command=self._mostrar_form_nuevo).pack(side=tk.RIGHT)

        # Separador
        sep = tk.Frame(frame_right, bg="#1a252f", height=2)
        sep.pack(fill="x", padx=10, pady=4)

        # Lista de variantes (scrollable) - SIN expand para que no se coma el espacio de los métodos
        self._variantes_scroll = ctk.CTkScrollableFrame(frame_right, fg_color="#2c3e50", height=200)
        self._variantes_scroll.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 4))

        # --- SECCIÓN MÉTODOS (abajo de variantes) ---
        self._frame_metodos = tk.Frame(frame_right, bg="#34495e")
        self._frame_metodos.pack(fill="x", padx=10, pady=5) # Lo dejamos pack fijo para que se vea
        
        tk.Label(self._frame_metodos, text="MÉTODOS DE IMPRESIÓN DISPONIBLES", 
                 font=get_font(self.config, "label"), fg="#FFD700", bg="#34495e").pack(pady=(8, 4))
        
        self._metodos_container = tk.Frame(self._frame_metodos, bg="#34495e")
        self._metodos_container.pack(fill="x", padx=10, pady=5)

        self._lbl_no_variante = tk.Label(self._metodos_container, text="Selecciona una variante para asignar métodos",
                                         font=get_font(self.config, "label"), fg="#95a5a6", bg="#34495e")
        self._lbl_no_variante.pack(pady=10)

        # Frame para formulario de nueva variante (oculto inicialmente)
        self._form_nuevo = None

        # Botón guardar (para editar existentes)
        self._btn_guardar = ctk.CTkButton(frame_right, text="GUARDAR CAMBIOS",
                                          fg_color="#27ae60", hover_color="#2ecc71",
                                          height=36, font=get_font(self.config, "button"),
                                          command=self._guardar_edicion)
        # No pack aún, se muestra al seleccionar una variante

        # Cargar tipos
        self._cargar_tipos()

    def _cargar_tipos(self):
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipo_chips = {}

        self._all_tipos = self.config_service.obtener_tipos_de_menus_ordenados()

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

        for idx, tipo in enumerate(self._all_tipos):
            chip = tk.Label(
                self._tipos_scroll, text=tipo.nombre,
                font=chip_font, fg=self._text,
                bg=self._CHIP_NORMAL,
                padx=10, pady=5, cursor="hand2"
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            chip.bind("<Button-1>", lambda e, tid=tipo.id: self._select_tipo(tid))
            self._tipo_chips[tipo.id] = chip

        for i in range(cols):
            self._tipos_scroll.columnconfigure(i, weight=1)

    def _select_tipo(self, tipo_id):
        self._tipo_selected_id = tipo_id
        for tid, chip in self._tipo_chips.items():
            chip.configure(bg=self._CHIP_SELECTED if tid == tipo_id else self._CHIP_NORMAL)
        self._cargar_variantes()

    def _cargar_variantes(self):
        for child in self._variantes_scroll.winfo_children():
            child.destroy()
        self._variante_rows = {}
        self._variante_id_edit = None
        self._btn_guardar.pack_forget()
        self._ocultar_form_nuevo()

        # Resetear sección de métodos al placeholder
        for child in self._metodos_container.winfo_children():
            child.destroy()
        self._metodo_vars = {}
        self._lbl_no_variante = tk.Label(self._metodos_container, text="Selecciona una variante para asignar métodos",
                                         font=get_font(self.config, "label"), fg="#95a5a6", bg="#34495e")
        self._lbl_no_variante.pack(pady=10)

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

        for v in variantes:
            coste_medio = self.config_service.obtener_coste_medio_variante(
                self._tipo_selected_id, v.id if v.id else None)
            coste_str = f"{read_from_db(coste_medio):.2f}€" if coste_medio > 0 else "-"
            estado_str = "✓" if v.activo else "✗"

            row_frame = tk.Frame(self._variantes_scroll, bg="#34495e", cursor="hand2")
            row_frame.pack(fill="x", padx=4, pady=2)

            txt = f"{v.nombre}  |  Coste: {coste_str}  |  {estado_str}"
            lbl = tk.Label(row_frame, text=txt, font=get_font(self.config, "label"),
                           fg=self._text, bg="#34495e", anchor="w", cursor="hand2")
            lbl.pack(fill="x", padx=8, pady=6)

            lbl.bind("<Button-1>", lambda e, vid=v.id: self._select_variante(vid))
            row_frame.bind("<Button-1>", lambda e, vid=v.id: self._select_variante(vid))
            self._variante_rows[v.id] = (row_frame, lbl)

    def _select_variante(self, variante_id):
        self._variante_id_edit = variante_id
        for vid, (rf, lbl) in self._variante_rows.items():
            bg = "#1a5274" if vid == variante_id else "#34495e"
            rf.configure(bg=bg)
            lbl.configure(bg=bg)
        
        # Ocultar label de aviso si existe y sigue vivo
        if hasattr(self, '_lbl_no_variante') and self._lbl_no_variante.winfo_exists():
            self._lbl_no_variante.pack_forget()

        # Asegurar que la sección de métodos está visible
        self._frame_metodos.pack(fill="x", padx=10, pady=5)

        self._btn_guardar.pack(fill="x", padx=10, pady=(4, 8))
        self._ocultar_form_nuevo()
        self._cargar_metodos_variante(variante_id)

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

    def _mostrar_form_nuevo(self):
        if not self._tipo_selected_id:
            ToastWidget.show(self.parent, "Selecciona un tipo primero", tipo="warning")
            return

        self._ocultar_form_nuevo()
        self._variante_id_edit = None
        for vid, (rf, lbl) in self._variante_rows.items():
            rf.configure(bg="#34495e")
            lbl.configure(bg="#34495e")
        self._btn_guardar.pack_forget()

        # Resetear sección de métodos al placeholder
        for child in self._metodos_container.winfo_children():
            child.destroy()
        self._metodo_states = {}
        self._metodo_chips = {}
        self._lbl_no_variante = tk.Label(self._metodos_container, text="Selecciona una variante para asignar métodos",
                                         font=get_font(self.config, "label"), fg="#95a5a6", bg="#34495e")
        self._lbl_no_variante.pack(pady=10)

        self._form_nuevo = tk.Frame(self._variantes_scroll, bg="#1a252f", highlightbackground="#2980b9", highlightthickness=1)
        self._form_nuevo.pack(fill="x", padx=4, pady=4)

        tk.Label(self._form_nuevo, text="NUEVA VARIANTE", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#1a252f").pack(anchor="w", padx=8, pady=(4, 2))

        self._entry_nombre_nuevo = ctk.CTkEntry(self._form_nuevo, placeholder_text="Nombre variante...",
                                                 width=200)
        self._entry_nombre_nuevo.pack(fill="x", padx=8, pady=2)

        row_precios = tk.Frame(self._form_nuevo, bg="#1a252f")
        row_precios.pack(fill="x", padx=8, pady=2)

        self._entry_precio_nuevo = ctk.CTkEntry(row_precios, placeholder_text="P. REC (€)", width=100)
        self._entry_precio_nuevo.pack(side=tk.LEFT, padx=(0, 4))

        self._entry_shopify_nuevo = ctk.CTkEntry(row_precios, placeholder_text="Shopify ID (opc.)", width=120)
        self._entry_shopify_nuevo.pack(side=tk.LEFT)

        row_btns = tk.Frame(self._form_nuevo, bg="#1a252f")
        row_btns.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkButton(row_btns, text="CREAR", fg_color="#27ae60", hover_color="#2ecc71",
                      width=80, command=self._crear_variante).pack(side=tk.LEFT, padx=(0, 4))
        ctk.CTkButton(row_btns, text="CANCELAR", fg_color="#e74c3c", hover_color="#c0392b",
                      width=80, command=self._ocultar_form_nuevo).pack(side=tk.LEFT)

        self._entry_nombre_nuevo.focus_set()

    def _ocultar_form_nuevo(self):
        if self._form_nuevo:
            self._form_nuevo.destroy()
            self._form_nuevo = None

    def _crear_variante(self):
        if not self._tipo_selected_id:
            return
        nombre = self._entry_nombre_nuevo.get().strip()
        if not nombre:
            ToastWidget.show(self.parent, "Introduce un nombre", tipo="warning")
            return

        try:
            precio_val = float(self._entry_precio_nuevo.get().replace(",", ".") or "0")
            precio_cents = prepare_for_db(precio_val)
        except ValueError:
            ToastWidget.show(self.parent, "Precio debe ser numérico", tipo="error")
            return

        shopify_id = self._entry_shopify_nuevo.get().strip() or None

        res = self.service.crear(self._tipo_selected_id, nombre, 0, precio_cents, shopify_id, 0, 0)
        if res is not None:
            ToastWidget.show(self.parent, "Variante creada", tipo="success")
            self._ocultar_form_nuevo()
            self._cargar_variantes()
        else:
            ToastWidget.show(self.parent, "Error al crear variante", tipo="error")

    def _guardar_edicion(self):
        if not self._variante_id_edit:
            return
        
        # Guardar ID actual para evitar que se pierda tras el refresh
        variante_id = self._variante_id_edit
        
        variante = self.service.obtener_por_id(variante_id)
        if not variante:
            return

        # 1. Guardar métodos seleccionados
        metodos_seleccionados = [mid for mid, val in self._metodo_states.items() if val]
        ok_metodos = self.metodos_service.sincronizar_metodos(variante_id, metodos_seleccionados)

        # 2. Togglear activo/inactivo (esto se podría mejorar con un checkbox real en la UI)
        # Por ahora lo dejamos como está o lo hacemos más explícito
        nuevo_activo = variante.activo # No cambiar activo a menos que queramos
        
        ok_variante = self.service.actualizar(
            variante_id, variante.tipo_id, variante.nombre,
            variante.coste_base, variante.precio_recomendado,
            nuevo_activo, variante.shopify_variant_id,
            variante.requiere_talla, variante.requiere_color
        )
        
        if ok_metodos and ok_variante:
            ToastWidget.show(self.parent, "Variante y métodos actualizados", tipo="success")
            # Recargar variantes pero re-seleccionar la actual
            self._cargar_variantes()
            self._select_variante(variante_id)
        else:
            ToastWidget.show(self.parent, "Error al actualizar", tipo="error")

    def refresh_nav(self):
        pass
