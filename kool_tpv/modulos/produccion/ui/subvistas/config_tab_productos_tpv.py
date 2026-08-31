"""Tab de configuración para vincular Variantes de Producción con Productos del TPV.

Permite que el stock se incremente automáticamente al finalizar una orden de producción.
"""
import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font, get_chip_config, get_chip_style
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.variante_producto_service import VarianteProductoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget

logger = logging.getLogger(__name__)

class ConfigTabProductosTpv:
    """Pestaña PRODUCTOS TPV: vincula Variantes -> Productos TPV."""

    def __init__(self, parent, config_service, config, colors, km, layout_config):
        self.parent = parent
        self.config_service = config_service
        self.db = config_service.db
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._text_sec = colors.get("text_secondary", "#95a5a6")
        self._km = km
        self._layout_config = layout_config

        # Servicios
        self.tipos_service = ProduccionTiposService(self.db)
        self.variantes_service = ProduccionTiposVariantesService(self.db)
        self.link_service = VarianteProductoService(self.db)
        self.tpv_service = ProductoService(self.db)
        from kool_tpv.modulos.produccion.services.produccion_extras_service import ProduccionExtrasService
        from kool_tpv.modulos.produccion.services.produccion_config_service import ProduccionConfigService
        self.extras_service = ProduccionExtrasService(self.db)
        self.colecciones_service = ProduccionConfigService(self.db)

        # Estado
        self._tipo_selected_id = None
        self._variantes_selected_ids = set() # Soporta selección múltiple
        self._extra_selected_id = None
        self._coleccion_selected_id = None
        self._producto_selected_data = None  # Almacena el producto del TPV seleccionado
        self._link_actual = None
        
        self._tipo_chips = {}
        self._variante_chips = {}
        self._extra_chips = {}
        self._coleccion_chips = {}

        # Configuración de chips
        self._chip_cfg = self.config.get("chips", {}).get("diseno", {})
        
        self.build()

    def build(self):
        self.main_container = tk.Frame(self.parent, bg=self._bg)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. COLUMNA IZQUIERDA: VINCULACIONES (30%)
        self.frame_links = tk.Frame(self.main_container, bg="#1a1a2e", bd=0)
        self.frame_links.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        tk.Label(self.frame_links, text="VINCULACIONES ACTUALES", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#1a1a2e").pack(pady=(12, 8))

        self.btn_nuevo = ButtonFactory.create_button(
            self.frame_links, text="+ NUEVA VINCULACIÓN",
            module="produccion", palette_key="primary", style_key="action_confirm",
            height=30, command=self._on_nueva_vinculacion
        )
        self.btn_nuevo.pack(fill="x", padx=10, pady=(0, 10))

        # Lista de vinculaciones existentes
        cols_links = [
            ("producto", 250, "Producto TPV"),
            ("produccion", 200, "Configuración")
        ]
        self._links_list = VirtualNavList(
            self.frame_links,
            columns=cols_links,
            module_name="produccion",
            keyboard_manager=self._km,
            on_double_click=self._on_link_double_click,
            layout_config=self._layout_config
        )
        self._links_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=5)

        # 2. COLUMNA CENTRAL: PRODUCTO & TIPO (35%)
        self.frame_center = tk.Frame(self.main_container, bg="#2c3e50", bd=0)
        self.frame_center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        
        # PASO 1: BUSCADOR TPV
        tk.Label(self.frame_center, text="PASO 1: BUSCA UN PRODUCTO", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#2c3e50").pack(pady=(12, 4))
        
        self._search_entry = ctk.CTkEntry(
            self.frame_center, placeholder_text="Nombre o SKU + ENTER...",
            font=get_font(self.config, "entry"),
            height=35
        )
        self._search_entry.pack(fill="x", padx=10, pady=5)
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        self._tpv_list = VirtualNavList(
            self.frame_center,
            columns=[("nombre", 200, "Producto"), ("stock", 60, "Stock")],
            module_name="produccion",
            keyboard_manager=self._km,
            on_double_click=self._on_producto_select,
            layout_config=self._layout_config
        )
        self._tpv_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=5)

        # ZONA DE SELECCIONADO Y GUARDADO
        self.selection_status_frame = tk.Frame(self.frame_center, bg="#1a1a2e", height=100)
        self.selection_status_frame.pack(fill="x", padx=6, pady=5)
        self.selection_status_frame.pack_propagate(False)
        
        self.lbl_prod_sel = tk.Label(self.selection_status_frame, text="Ningún producto seleccionado", 
                                     font=get_font(self.config, "label_small"), fg="#95a5a6", bg="#1a1a2e")
        self.lbl_prod_sel.pack(pady=10)
        
        self.btn_guardar = ButtonFactory.create_button(
            self.selection_status_frame, text="GUARDAR VINCULACIÓN",
            module="produccion", palette_key="primary", style_key="action_confirm",
            height=40, command=self._on_guardar_click
        )
        self.btn_guardar.configure(state="disabled")
        self.btn_guardar.pack(fill="x", padx=20, pady=(0, 10))

        # PASO 2: SELECCIONA UN TIPO (Debajo del buscador)
        tk.Label(self.frame_center, text="PASO 2: SELECCIONA UN TIPO", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#2c3e50").pack(pady=(10, 4))
        
        self._tipos_scroll = ctk.CTkScrollableFrame(self.frame_center, fg_color="#34495e", height=150)
        self._tipos_scroll.pack(fill="x", padx=6, pady=5)

        # 3. COLUMNA DERECHA: PASOS 3, 4, 5 (35%)
        self.frame_right = tk.Frame(self.main_container, bg="#2c3e50", bd=0)
        self.frame_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        # PASO 3: VARIANTES (40%)
        tk.Label(self.frame_right, text="PASO 3: SELECCIONA UNA VARIANTE", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#2c3e50").pack(pady=(12, 4))
        self._variantes_scroll = ctk.CTkScrollableFrame(self.frame_right, fg_color="#34495e", height=200)
        self._variantes_scroll.pack(fill="x", padx=6, pady=5)

        # PASO 4: EXTRAS (20%)
        tk.Label(self.frame_right, text="PASO 4: SELECCIONA UN EXTRA", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#2c3e50").pack(pady=(8, 4))
        self._extras_frame = tk.Frame(self.frame_right, bg="#34495e", height=80)
        self._extras_frame.pack(fill="x", padx=6, pady=5)
        self._extras_frame.pack_propagate(False)

        # PASO 5: COLECCIONES (Resto)
        tk.Label(self.frame_right, text="PASO 5: SELECCIONA UNA COLECCIÓN", font=get_font(self.config, "label_bold"),
                 fg="#FFFFFF", bg="#2c3e50").pack(pady=(8, 4))
        self._colecciones_scroll = ctk.CTkScrollableFrame(self.frame_right, fg_color="#34495e")
        self._colecciones_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=5)

        # Botón Eliminar en el footer derecho
        self.btn_eliminar = ButtonFactory.create_button(
            self.frame_right, text="ELIMINAR VINCULACIÓN ACTUAL",
            module="produccion", palette_key="accent", style_key="action_confirm",
            height=35, command=self._on_eliminar_link
        )
        self.btn_eliminar.configure(state="disabled")
        self.btn_eliminar.pack(fill="x", padx=20, pady=15)

        # Cargar datos iniciales
        self._cargar_vinculaciones()
        self._cargar_tipos()
        self._cargar_extras()
        self._cargar_colecciones()

    def _cargar_vinculaciones(self):
        """Cargar la lista de vinculaciones existentes (siempre todas)."""
        items = self.link_service.get_todos()
        
        rows = []
        for it in items:
            prod_info = it.producto_nombre
            # Construir resumen de producción
            partes = [it.variante_nombre]
            if it.extra_nombre: partes.append(f"+{it.extra_nombre}")
            if it.coleccion_nombre: partes.append(f"({it.coleccion_nombre})")
            
            rows.append({
                "id": it.id,
                "producto": prod_info,
                "produccion": " ".join(partes),
                "_raw": it
            })
        self._links_list.set_items(rows)

    def _cargar_tipos(self):
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipo_chips = {}
        tipos = self.config_service.obtener_tipos_de_menus_ordenados(solo_con_stock=False)
        
        cols = 2
        for idx, t in enumerate(tipos):
            is_sel = (t.id == self._tipo_selected_id)
            chip = ctk.CTkButton(
                self._tipos_scroll, text=t.nombre, height=32, corner_radius=16,
                fg_color=self._get_chip_color(is_sel),
                command=lambda tid=t.id: self._on_tipo_click(tid)
            )
            row, col = divmod(idx, cols)
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self._tipo_chips[t.id] = chip
        for i in range(cols): self._tipos_scroll.columnconfigure(i, weight=1)

    def _on_tipo_click(self, tipo_id):
        self._tipo_selected_id = tipo_id
        self._variantes_selected_ids = set()
        self._link_actual = None
        self._actualizar_chips_seleccion(self._tipo_chips, tipo_id)
        self._cargar_variantes(tipo_id)
        self._check_ready_to_save()

    def _cargar_variantes(self, tipo_id):
        for child in self._variantes_scroll.winfo_children():
            child.destroy()
        self._variante_chips = {}
        variantes = self.variantes_service.obtener_por_tipo(tipo_id, solo_activos=True)
        
        cols = 2
        for idx, v in enumerate(variantes):
            is_sel = (v.id in self._variantes_selected_ids)
            chip = ctk.CTkButton(
                self._variantes_scroll, text=v.nombre, height=32, corner_radius=16,
                fg_color=self._get_chip_color(is_sel),
                command=lambda vid=v.id: self._on_variante_click(vid)
            )
            row, col = divmod(idx, cols)
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self._variante_chips[v.id] = chip
        for i in range(cols): self._variantes_scroll.columnconfigure(i, weight=1)

    def _on_variante_click(self, variante_id):
        # Toggle selection (multi-select)
        if variante_id in self._variantes_selected_ids:
            self._variantes_selected_ids.remove(variante_id)
        else:
            self._variantes_selected_ids.add(variante_id)
            
        self._actualizar_chips_seleccion(self._variante_chips, self._variantes_selected_ids)
        self._check_ready_to_save()

    def _cargar_extras(self):
        for child in self._extras_frame.winfo_children(): child.destroy()
        self._extra_chips = {}
        extras = self.extras_service.get_todos(solo_activos=True)
        for extra in extras:
            is_sel = (extra.id == self._extra_selected_id)
            chip = ctk.CTkButton(
                self._extras_frame, text=extra.nombre, width=80, height=28, corner_radius=14,
                fg_color=self._get_chip_color(is_sel),
                command=lambda eid=extra.id: self._on_extra_click(eid)
            )
            chip.pack(side=tk.LEFT, padx=3, pady=5)
            self._extra_chips[extra.id] = chip

    def _on_extra_click(self, extra_id):
        # Toggle selection
        if self._extra_selected_id == extra_id: self._extra_selected_id = None
        else: self._extra_selected_id = extra_id
        self._actualizar_chips_seleccion(self._extra_chips, self._extra_selected_id)
        self._check_ready_to_save()

    def _cargar_colecciones(self):
        for child in self._colecciones_scroll.winfo_children(): child.destroy()
        self._coleccion_chips = {}
        colecciones = self.colecciones_service.obtener_colecciones()
        cols = 2
        for idx, col_item in enumerate(colecciones):
            is_sel = (col_item.id == self._coleccion_selected_id)
            chip = ctk.CTkButton(
                self._colecciones_scroll, text=col_item.nombre, height=32, corner_radius=16,
                fg_color=self._get_chip_color(is_sel),
                command=lambda cid=col_item.id: self._on_coleccion_click(cid)
            )
            row, col_idx = divmod(idx, cols)
            chip.grid(row=row, column=col_idx, padx=4, pady=4, sticky="ew")
            self._coleccion_chips[col_item.id] = chip
        for i in range(cols): self._colecciones_scroll.columnconfigure(i, weight=1)

    def _on_coleccion_click(self, coleccion_id):
        # Toggle selection
        if self._coleccion_selected_id == coleccion_id: self._coleccion_selected_id = None
        else: self._coleccion_selected_id = coleccion_id
        self._actualizar_chips_seleccion(self._coleccion_chips, self._coleccion_selected_id)
        self._check_ready_to_save()

    def _on_search(self):
        filtro = self._search_entry.get().strip()
        if not filtro:
            self._tpv_list.clear_items()
            return
        productos = self.tpv_service.listar_productos(filtro)
        rows = [{"id": p['id'], "nombre": p['nombre'], "stock": p.get('stock_actual', 0)} for p in productos]
        self._tpv_list.set_items(rows)

    def _on_producto_select(self, item_data: dict):
        """Paso 1: Seleccionar producto de la lista."""
        self._producto_selected_data = item_data
        self.lbl_prod_sel.configure(
            text=f"PRODUCTO: {item_data['nombre']}", 
            fg="#552583"
        )
        self._check_ready_to_save()

    def _on_guardar_click(self):
        """Guardar la vinculación final."""
        if not self._producto_selected_data or not self._variantes_selected_ids:
            ToastWidget.show(self.parent, "SELECCIONA PRODUCTO Y AL MENOS UNA VARIANTE", tipo="error")
            return
        
        ins, els = self.link_service.sincronizar_vinculaciones(
            self._producto_selected_data["id"],
            self._variantes_selected_ids,
            extra_id=self._extra_selected_id,
            coleccion_id=self._coleccion_selected_id
        )
        
        msg = f"VINCULACIÓN ACTUALIZADA: {ins} nuevas"
        if els: msg += f", {els} eliminadas"
        ToastWidget.show(self.parent, msg, tipo="success")
        
        self._cargar_vinculaciones()
        self._check_ready_to_save()

    def _on_link_double_click(self, item_data: dict):
        """Cargar una vinculación existente en los chips y buscador."""
        link = item_data["_raw"]
        
        # 1. Identificar el producto y la combinación (extra/colección)
        self._extra_selected_id = link.extra_id
        self._coleccion_selected_id = link.coleccion_id
        self._producto_selected_data = {"id": link.producto_id, "nombre": link.producto_nombre}
        self.lbl_prod_sel.configure(text=f"PRODUCTO: {link.producto_nombre}", fg="#552583")

        # 2. Buscar TODAS las variantes vinculadas a este producto con esta combinación
        links_comb = self.link_service.get_por_producto_combinacion(
            link.producto_id, link.extra_id, link.coleccion_id
        )
        self._variantes_selected_ids = {l.variante_id for l in links_comb}
        
        # 3. Encontrar el tipo de la variante que se ha pulsado (para cargar la lista de variantes)
        var_obj = self.db.fetch_one("SELECT tipo_id FROM tipos_variantes WHERE id = ?", (link.variante_id,))
        if var_obj:
            self._tipo_selected_id = var_obj[0]
            self._actualizar_chips_seleccion(self._tipo_chips, self._tipo_selected_id)
            self._cargar_variantes(self._tipo_selected_id) # Esto ya usa self._variantes_selected_ids
            self._actualizar_chips_seleccion(self._variante_chips, self._variantes_selected_ids)
            
        self._actualizar_chips_seleccion(self._extra_chips, self._extra_selected_id)
        self._actualizar_chips_seleccion(self._coleccion_chips, self._coleccion_selected_id)
        
        # Mostrar el producto vinculado en el buscador por si quiere cambiarlo
        self._search_entry.delete(0, tk.END)
        self._search_entry.insert(0, link.producto_nombre)
        self._on_search()
        self._check_ready_to_save()

    def _on_nueva_vinculacion(self):
        """Resetear selección para crear una nueva vinculación."""
        self._tipo_selected_id = None
        self._variantes_selected_ids = set()
        self._extra_selected_id = None
        self._coleccion_selected_id = None
        self._producto_selected_data = None
        self._link_actual = None
        
        self.lbl_prod_sel.configure(text="Ningún producto seleccionado", fg="#95a5a6")
        self._actualizar_chips_seleccion(self._tipo_chips, None)
        for child in self._variantes_scroll.winfo_children(): child.destroy()
        self._actualizar_chips_seleccion(self._extra_chips, None)
        self._actualizar_chips_seleccion(self._coleccion_chips, None)
        
        self._search_entry.delete(0, tk.END)
        self._tpv_list.clear_items()
        self._cargar_vinculaciones()
        self._check_ready_to_save()

    def _check_ready_to_save(self):
        """Verificar si se puede guardar y si ya existe la combinación."""
        can_save = (self._producto_selected_data is not None and len(self._variantes_selected_ids) > 0)
        
        if can_save:
            self.btn_guardar.configure(state="normal")
            
            # Buscamos si el producto ya tiene vinculaciones para esta combinación de extra/col
            links_actuales = self.link_service.get_por_producto_combinacion(
                self._producto_selected_data["id"], self._extra_selected_id, self._coleccion_selected_id
            )
            
            if links_actuales:
                self._link_actual = links_actuales[0] # Referencia para el ID si hiciera falta (eliminar total)
                self.btn_guardar.configure(text=f"ACTUALIZAR VINCULACIÓN ({len(self._variantes_selected_ids)} vars)")
                ButtonFactory.apply_style(self.btn_guardar, style_key="action_confirm", module="produccion", palette_key="secondary")
                self.btn_eliminar.configure(state="normal")
            else:
                self._link_actual = None
                self.btn_guardar.configure(text=f"GUARDAR VINCULACIÓN ({len(self._variantes_selected_ids)} vars)")
                ButtonFactory.apply_style(self.btn_guardar, style_key="action_confirm", module="produccion", palette_key="primary")
                self.btn_eliminar.configure(state="disabled")
        else:
            self.btn_guardar.configure(state="disabled", text="GUARDAR VINCULACIÓN")
            ButtonFactory.apply_style(self.btn_guardar, style_key="action_confirm", module="produccion", palette_key="primary")
            self.btn_eliminar.configure(state="disabled")

    def _on_eliminar_link(self):
        """Eliminar todas las vinculaciones del producto para esta combinación."""
        if not self._producto_selected_data: return

        if self.link_service.repo.eliminar_por_producto_combinacion(
            self._producto_selected_data["id"], self._extra_selected_id, self._coleccion_selected_id
        ):
            ToastWidget.show(self.parent, "VINCULACIONES ELIMINADAS", tipo="success")
            self._on_nueva_vinculacion()
        else:
            ToastWidget.show(self.parent, "ERROR AL ELIMINAR", tipo="error")

    def _get_chip_color(self, is_selected):
        default_cfg = self._chip_cfg.get("default", {})
        selected_cfg = self._chip_cfg.get("selected", {})
        return selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")

    def _actualizar_chips_seleccion(self, chips_dict, selected):
        for cid, chip in chips_dict.items():
            if isinstance(selected, (set, list)):
                is_sel = cid in selected
            else:
                is_sel = (cid == selected)
            chip.configure(fg_color=self._get_chip_color(is_sel))

    def refresh_nav(self): self._cargar_vinculaciones()

    def destruir(self): self.main_container.destroy()
