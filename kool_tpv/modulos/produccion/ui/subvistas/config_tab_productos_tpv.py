"""Tab de configuración para vincular Variantes de Producción con Productos del TPV.

Permite que el stock se incremente automáticamente al finalizar una orden de producción.
"""
import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Optional

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

        # Estado
        self._tipo_selected_id = None
        self._variante_selected_id = None
        self._link_actual = None
        self._tipo_chips = {}
        self._variante_chips = {}

        # Configuración de chips (reutilizando estilo de diseno)
        self._chip_cfg = self.config.get("chips", {}).get("diseno", {})
        
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: Selección de Variante y Resultado (40%) ---
        self.frame_left = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        self.frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # 1. Chips de Tipos
        tk.Label(self.frame_left, text="1. SELECCIONA TIPO", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(8, 4))
        
        self._tipos_scroll = ctk.CTkScrollableFrame(self.frame_left, fg_color="#2c3e50", height=150)
        self._tipos_scroll.pack(fill="x", padx=6, pady=(0, 6))

        # 2. Chips de Variantes
        tk.Label(self.frame_left, text="2. SELECCIONA VARIANTE", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(8, 4))
        
        self._variantes_scroll = ctk.CTkScrollableFrame(self.frame_left, fg_color="#2c3e50", height=150)
        self._variantes_scroll.pack(fill="x", padx=6, pady=(0, 6))

        # 3. Resultado de Vinculación
        tk.Label(self.frame_left, text="VINCULACIÓN ACTUAL", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(pady=(20, 4))
        
        self._resultado_container = tk.Frame(self.frame_left, bg="#2c3e50", height=80)
        self._resultado_container.pack(fill="x", padx=6, pady=5)
        self._resultado_container.pack_propagate(False)
        
        self._render_link_actual()

        # Footer Izquierda: Botón eliminar
        self.footer_left = tk.Frame(self.frame_left, bg="#34495e", height=50)
        self.footer_left.pack(side=tk.BOTTOM, fill="x", padx=6, pady=10)
        
        self.btn_eliminar = ctk.CTkButton(
            self.footer_left, text="ELIMINAR VINCULACIÓN",
            fg_color="#e74c3c", hover_color="#c0392b",
            font=get_font(self.config, "button"),
            command=self._on_eliminar_link
        )
        self.btn_eliminar.pack(fill="x")

        # --- DERECHA: Buscador de Productos TPV (60%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Cabecera Derecha: Buscador
        header_right = tk.Frame(frame_right, bg="#34495e")
        header_right.pack(fill="x", padx=10, pady=(8, 4))
        
        tk.Label(header_right, text="BUSCAR PRODUCTO TPV", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(side=tk.LEFT)

        self._search_entry = ctk.CTkEntry(
            frame_right, placeholder_text="Nombre, EAN o SKU...",
            font=get_font(self.config, "entry")
        )
        self._search_entry.pack(fill="x", padx=10, pady=5)
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        # Lista de Productos TPV
        columns = [
            ("sku", 120, "SKU/EAN"),
            ("nombre", 300, "Producto"),
            ("pvp", 80, "PVP"),
            ("stock_actual", 80, "Stock")
        ]
        
        self._nav_list = VirtualNavList(
            frame_right,
            columns=columns,
            module_name="produccion",
            keyboard_manager=self._km,
            on_double_click=self._on_producto_double_click,
            layout_config=self._layout_config
        )
        self._nav_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Cargar datos iniciales
        self._cargar_tipos()

    def _cargar_tipos(self):
        """Renderizar chips de tipos de producción."""
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipo_chips = {}

        tipos = self.config_service.obtener_tipos_de_menus_ordenados(solo_con_stock=False)
        if not tipos:
            tk.Label(self._tipos_scroll, text="No hay tipos configurados", bg="#2c3e50", fg=self._text_sec).pack(pady=20)
            return

        cols = 3
        default_cfg = self._chip_cfg.get("default", {})
        selected_cfg = self._chip_cfg.get("selected", {})
        
        for idx, t in enumerate(tipos):
            is_selected = (t.id == self._tipo_selected_id)
            bg = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
            
            chip = ctk.CTkButton(
                self._tipos_scroll, text=t.nombre,
                width=0, height=32, corner_radius=16,
                fg_color=bg,
                command=lambda tid=t.id: self._on_tipo_click(tid)
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self._tipo_chips[t.id] = chip

        for i in range(cols):
            self._tipos_scroll.columnconfigure(i, weight=1)

    def _on_tipo_click(self, tipo_id):
        self._tipo_selected_id = tipo_id
        self._variante_selected_id = None
        self._link_actual = None
        
        # Actualizar colores de chips de tipos
        default_cfg = self._chip_cfg.get("default", {})
        selected_cfg = self._chip_cfg.get("selected", {})
        for tid, chip in self._tipo_chips.items():
            bg = selected_cfg.get("bg", "#552583") if tid == tipo_id else default_cfg.get("bg", "#1a1a2e")
            chip.configure(fg_color=bg)

        self._cargar_variantes(tipo_id)
        self._render_link_actual()

    def _cargar_variantes(self, tipo_id):
        """Renderizar chips de variantes del tipo seleccionado."""
        for child in self._variantes_scroll.winfo_children():
            child.destroy()
        self._variante_chips = {}

        variantes = self.variantes_service.obtener_por_tipo(tipo_id, solo_activos=True)
        if not variantes:
            tk.Label(self._variantes_scroll, text="No hay variantes activas", bg="#2c3e50", fg=self._text_sec).pack(pady=20)
            return

        cols = 3
        default_cfg = self._chip_cfg.get("default", {})
        selected_cfg = self._chip_cfg.get("selected", {})

        for idx, v in enumerate(variantes):
            is_selected = (v.id == self._variante_selected_id)
            bg = selected_cfg.get("bg", "#552583") if is_selected else default_cfg.get("bg", "#1a1a2e")
            
            chip = ctk.CTkButton(
                self._variantes_scroll, text=v.nombre,
                width=0, height=32, corner_radius=16,
                fg_color=bg,
                command=lambda vid=v.id: self._on_variante_click(vid)
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self._variante_chips[v.id] = chip

        for i in range(cols):
            self._variantes_scroll.columnconfigure(i, weight=1)

    def _on_variante_click(self, variante_id):
        self._variante_selected_id = variante_id
        
        # Actualizar colores de chips de variantes
        default_cfg = self._chip_cfg.get("default", {})
        selected_cfg = self._chip_cfg.get("selected", {})
        for vid, chip in self._variante_chips.items():
            bg = selected_cfg.get("bg", "#552583") if vid == variante_id else default_cfg.get("bg", "#1a1a2e")
            chip.configure(fg_color=bg)

        # Buscar si ya tiene vinculación
        self._link_actual = self.link_service.get_por_variante(variante_id)
        self._render_link_actual()

    def _render_link_actual(self):
        """Muestra el chip del producto vinculado o un aviso."""
        for child in self._resultado_container.winfo_children():
            child.destroy()

        if not self._variante_selected_id:
            tk.Label(self._resultado_container, text="Selecciona una variante...", 
                     bg="#2c3e50", fg=self._text_sec, font=get_font(self.config, "label")).pack(expand=True)
            return

        if self._link_actual:
            nombre = self._link_actual.producto_nombre or f"Producto ID {self._link_actual.producto_id}"
            selected_cfg = self._chip_cfg.get("selected", {})
            chip_bg = selected_cfg.get("bg", "#27ae60")
            
            # Usar CTkButton para que sea un chip real consistente
            chip = ctk.CTkButton(
                self._resultado_container,
                text=f"✓ {nombre}",
                font=get_font(self.config, "label"),
                fg_color=chip_bg,
                hover_color="#e74c3c", # Rojo al pasar el ratón para indicar que se puede eliminar
                height=40,
                corner_radius=20,
                command=self._on_eliminar_link
            )
            chip.pack(expand=True, padx=10)
            
            # Tooltip simple vía bind para explicar que clic elimina
            chip.bind("<Enter>", lambda e: chip.configure(text=f"✕ DESVINCULAR"))
            chip.bind("<Leave>", lambda e: chip.configure(text=f"✓ {nombre}"))
        else:
            tk.Label(self._resultado_container, text="SIN VINCULACIÓN", 
                     bg="#2c3e50", fg="#e67e22", font=get_font(self.config, "label")).pack(expand=True)

    def _on_search(self):
        filtro = self._search_entry.get().strip()
        if not filtro:
            self._nav_list.clear_items()
            return
        
        productos = self.tpv_service.listar_productos(filtro)
        # Normalizar para VirtualNavList (que usa keys de dict)
        items = []
        for p in productos:
            pvp_val = p.get('pvp', 0)
            if hasattr(pvp_val, '__float__'):
                pvp_str = f"{float(pvp_val):.2f}€"
            else:
                pvp_str = str(pvp_val)
            items.append({
                "id": p.get('id', ''),
                "sku": p.get('sku', ''),
                "nombre": p.get('nombre', ''),
                "pvp": pvp_str,
                "stock_actual": p.get('stock_actual', 0)
            })
        self._nav_list.set_items(items)

    def _on_producto_double_click(self, item_data: dict):
        """Vincular producto a la variante seleccionada."""
        if not self._tipo_selected_id or not self._variante_selected_id:
            ToastWidget.show(self.parent, "SELECCIONA TIPO Y VARIANTE PRIMERO", tipo="error")
            return

        producto_id = item_data["id"]
        producto_nombre = item_data["nombre"]

        if self.link_service.guardar_mapeo(self._variante_selected_id, producto_id):
            ToastWidget.show(self.parent, f"VINCULADO A: {producto_nombre}", tipo="success")
            self._link_actual = self.link_service.get_por_variante(self._variante_selected_id)
            self._render_link_actual()
        else:
            ToastWidget.show(self.parent, "ERROR AL VINCULAR PRODUCTO", tipo="error")

    def _on_eliminar_link(self):
        """Eliminar la vinculación actual."""
        if not self._link_actual:
            ToastWidget.show(self.parent, "NO HAY VINCULACIÓN QUE ELIMINAR", tipo="warning")
            return

        if self.link_service.eliminar_mapeo(self._link_actual.id):
            ToastWidget.show(self.parent, "VINCULACIÓN ELIMINADA", tipo="success")
            self._link_actual = None
            self._render_link_actual()
        else:
            ToastWidget.show(self.parent, "ERROR AL ELIMINAR VINCULACIÓN", tipo="error")

    def refresh_nav(self):
        """Método requerido por ProduccionConfigView."""
        pass
