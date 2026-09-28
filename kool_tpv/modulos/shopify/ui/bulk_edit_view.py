"""BulkEditView: Edición masiva de productos de Shopify.

Permite filtrar por tipo, tag y estado, previsualizar cambios y aplicar
actualizaciones de PVP, plantilla y estado en lote de forma asíncrona.
"""
import logging
import threading
import tkinter as tk
from typing import Optional, List, Dict, Any
from decimal import Decimal

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors, load_layout_config
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from ..services.shopify_product_service import ShopifyProductService
from ..services.producto_content_service import slugify_diseno

logger = logging.getLogger(__name__)

class ShopifyBulkEditView:
    """Subvista para la edición masiva de productos en Shopify."""

    COLUMNAS = [
        ('id', 60, 'ID'),
        ('title', 300, 'TÍTULO'),
        ('productType', 120, 'TIPO'),
        ('template', 120, 'PLANTILLA'),
        ('status', 100, 'ESTADO'),
        ('pvp_actual', 64, '€€'),
        ('pvp_propuesto', 120, '€€NEW', True),
        ('resultado', 120, 'RESULTADO')
    ]

    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.service = ShopifyProductService(db)

        try:
            self._colors_cfg = load_colors('shopify')
            self._primary = self._colors_cfg.get('primary', '#00A4DF')
            self._secondary = self._colors_cfg.get('secondary', '#3498db')
            self._bg = self._colors_cfg.get('background', '#000000')
            self._bg_medium = self._colors_cfg.get('bg_medium', '#1a1a1a')
        except Exception:
            self._primary, self._secondary = '#00A4DF', '#3498db'
            self._bg, self._bg_medium = '#000000', '#1a1a1a'

        self._all_products: List[Dict[str, Any]] = []
        self._items_tabla: List[Dict[str, Any]] = []
        self._is_loading = False

        self.frame = tk.Frame(parent, bg=self._bg)
        self._build()

    def _build(self):
        # --- Cabecera de Filtros ---
        filter_frame = ctk.CTkFrame(self.frame, fg_color=self._bg_medium, corner_radius=0)
        filter_frame.pack(fill="x", padx=0, pady=0)

        # Fila 1: Buscador y Tipos
        row1 = tk.Frame(filter_frame, bg=self._bg_medium)
        row1.pack(fill="x", padx=20, pady=(15, 5))

        tk.Label(row1, text="FILTRAR PRODUCTOS:", font=("Helvetica", 11, "bold"),
                 fg=self._primary, bg=self._bg_medium).pack(side="left", padx=(0, 10))

        self._search_entry = ctk.CTkEntry(row1, width=250, height=34, placeholder_text="Título o SKU...")
        self._search_entry.pack(side="left", padx=5)
        self._search_entry.bind("<Return>", lambda e: self._on_buscar())

        tk.Label(row1, text="TIPO EN SHOPIFY:", font=("Helvetica", 10, "bold"),
                 fg="#888", bg=self._bg_medium).pack(side="left", padx=(15, 5))
        self._tipo_combo = SearchableCombo(row1, width=180, placeholder="Todos...", module_name="shopify")
        self._tipo_combo.pack(side="left", padx=5)

        tk.Label(row1, text="TAG:", font=("Helvetica", 10, "bold"),
                 fg="#888", bg=self._bg_medium).pack(side="left", padx=(15, 5))
        self._tag_entry = ctk.CTkEntry(row1, width=150, height=34, placeholder_text="ej: Bryant")
        self._tag_entry.pack(side="left", padx=5)

        ctk.CTkButton(row1, text="BUSCAR LOTES", width=120, height=34,
                      fg_color=self._primary, text_color="#000", font=("Helvetica", 11, "bold"),
                      command=self._on_buscar).pack(side="left", padx=10)

        self._load_status_lbl = tk.Label(row1, text="", font=("Helvetica", 10), fg="#888", bg=self._bg_medium)
        self._load_status_lbl.pack(side="right", padx=10)

        # Fila 2: Checkboxes de seguridad
        row2 = tk.Frame(filter_frame, bg=self._bg_medium)
        row2.pack(fill="x", padx=20, pady=(5, 15))

        self._excluir_borradores_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="EXCLUIR BORRADORES", variable=self._excluir_borradores_var,
                        font=("Helvetica", 10), text_color="#AAA").pack(side="left", padx=(0, 20))

        self._excluir_archivados_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="EXCLUIR ARCHIVADOS", variable=self._excluir_archivados_var,
                        font=("Helvetica", 10), text_color="#AAA").pack(side="left")

        # --- Barra de Acciones (El "Qué hacer") ---
        self._action_frame = ctk.CTkFrame(self.frame, fg_color=self._bg, border_width=1, border_color=self._bg_medium)
        self._action_frame.pack(fill="x", padx=20, pady=10)
        
        # Modo Precio
        row_pvp = tk.Frame(self._action_frame, bg=self._bg)
        row_pvp.pack(fill="x", padx=15, pady=10)
        
        tk.Label(row_pvp, text="CAMBIO DE PVP:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg).pack(side="left", padx=(0, 10))
        
        self._op_pvp = ctk.CTkOptionMenu(row_pvp, values=["PRECIO FIJO", "SUBIR %", "BAJAR %", "SUBIR €", "BAJAR €"], width=130)
        self._op_pvp.pack(side="left", padx=5)
        
        self._val_pvp = ctk.CTkEntry(row_pvp, width=80, height=28, placeholder_text="Valor...")
        self._val_pvp.pack(side="left", padx=5)
        
        self._redondeo_pvp = ctk.CTkOptionMenu(row_pvp, values=["SIN REDONDEO", ".95", ".99", "EURO ENTERO"], width=130)
        self._redondeo_pvp.pack(side="left", padx=5)
        
        ctk.CTkButton(row_pvp, text="SIMULAR", width=100, height=28, fg_color=self._secondary, command=self._on_simular_pvp).pack(side="left", padx=15)

        # Modo Plantilla
        row_tpl = tk.Frame(self._action_frame, bg=self._bg)
        row_tpl.pack(fill="x", padx=15, pady=(0, 15))
        
        tk.Label(row_tpl, text="CAMBIO DE PLANTILLA:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg).pack(side="left", padx=(0, 10))
        
        self._tpl_entry = ctk.CTkEntry(row_tpl, width=200, height=28, placeholder_text="Nombre de plantilla...")
        self._tpl_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(row_tpl, text="APLICAR A TABLA", width=120, height=28, fg_color=self._secondary, command=self._on_simular_plantilla).pack(side="left", padx=15)

        # --- Tabla Virtual ---
        self.nav_list = VirtualNavList(
            self.frame,
            columns=self.COLUMNAS,
            module_name="shopify",
            row_color_callback=self._row_styler,
            multi_select=True
        )
        self.nav_list.pack(fill="both", expand=True, padx=20, pady=5)

        # --- Footer ---
        footer = tk.Frame(self.frame, bg=self._bg)
        footer.pack(fill="x", padx=20, pady=(5, 15))
        
        self._btn_quitar = ctk.CTkButton(footer, text="QUITAR DE LA LISTA", fg_color="#8b1a1a", width=180, command=self._on_quitar)
        self._btn_quitar.pack(side="left")
        
        self._btn_save = ctk.CTkButton(footer, text="ACTUALIZAR EN SHOPIFY", fg_color="#27ae60", width=240, 
                                       font=("Helvetica", 13, "bold"), command=self._on_guardar)
        self._btn_save.pack(side="right")

        # Cargar tipos iniciales
        self._cargar_tipos()

    def _cargar_tipos(self):
        def work():
            try:
                # Obtener los tipos reales directamente desde Shopify
                tipos = self.service.get_all_product_types()
                if tipos:
                    opts = [(t, t) for t in sorted(tipos)]
                    self.frame.after(0, lambda: self._tipo_combo.set_options(opts))
            except Exception:
                logger.exception("Error cargando tipos de Shopify")

        threading.Thread(target=work, daemon=True).start()

    def _on_buscar(self):
        if self._is_loading: return
        
        search = self._search_entry.get().strip()
        tipo = self._tipo_combo.get().strip()
        tag = self._tag_entry.get().strip()
        
        # Seguridad: evitar búsqueda masiva accidental
        if not search and not tipo and not tag:
            if not tk.messagebox.askyesno("Confirmar", "¿Quieres cargar TODOS los productos de la web?\n\n(Esto puede tardar unos segundos si tienes muchos)"):
                return

        filters = {
            "search": search,
            "tipo": tipo,
            "tag": tag,
            "excluir_borradores": self._excluir_borradores_var.get(),
            "excluir_archivados": self._excluir_archivados_var.get()
        }
        
        self._is_loading = True
        self._all_products = []
        self._items_tabla = []
        self.nav_list.clear_items()
        self._load_status_lbl.configure(text="Conectando con Shopify...", fg=self._primary)
        
        def work():
            def on_page(nodes):
                self._all_products.extend(nodes)
                new_items = [self._transform_node(n) for n in nodes]
                self._items_tabla.extend(new_items)
                self.frame.after(0, lambda: self._update_table_partial())

            self.service.buscar_productos_lote(filters, on_page_callback=on_page)
            self.frame.after(0, self._on_finish_search)

        threading.Thread(target=work, daemon=True).start()

    def _transform_node(self, node):
        # Coger el precio de la primera variante como referencia
        variants = node.get("variants", {}).get("nodes", [])
        pvp = float(variants[0].get("price", 0)) if variants else 0.0
        
        return {
            "id": node["id"].split("/")[-1],
            "title": node["title"],
            "productType": node.get("productType", ""),
            "template": node.get("templateSuffix") or "Default",
            "status": node["status"],
            "pvp_actual": f"{pvp:.2f}€",
            "_pvp_numeric": pvp,
            "pvp_propuesto": "",
            "_pvp_propuesto_numeric": None,
            "resultado": "",
            "_node": node
        }

    def _update_table_partial(self):
        self.nav_list.set_items(self._items_tabla, grab_focus=False)
        self._load_status_lbl.configure(text=f"Cargados: {len(self._all_products)}...")

    def _on_finish_search(self):
        self._is_loading = False
        self._load_status_lbl.configure(text=f"Total: {len(self._all_products)} productos", fg="#2ECC71")
        if not self._all_products:
            show_error(self.frame, "No se han encontrado productos")

    def _on_simular_pvp(self):
        op = self._op_pvp.get()
        try:
            val_raw = self._val_pvp.get().replace(',', '.').strip()
            val = float(val_raw) if val_raw else 0.0
        except:
            show_error(self.frame, "Valor de precio inválido")
            return
            
        redondeo = self._redondeo_pvp.get()
        
        for item in self._items_tabla:
            nuevo = self._calcular_nuevo_pvp(item["_pvp_numeric"], op, val, redondeo)
            item["pvp_propuesto"] = f"{nuevo:.2f}€"
            item["_pvp_propuesto_numeric"] = nuevo
            
        self.nav_list.set_items(self._items_tabla)

    def _calcular_nuevo_pvp(self, actual, op, val, redondeo):
        nuevo = actual
        if op == "PRECIO FIJO": nuevo = val
        elif op == "SUBIR %": nuevo = actual * (1 + val/100)
        elif op == "BAJAR %": nuevo = actual * (1 - val/100)
        elif op == "SUBIR €": nuevo = actual + val
        elif op == "BAJAR €": nuevo = actual - val
        
        if redondeo == ".95": nuevo = int(nuevo) + 0.95
        elif redondeo == ".99": nuevo = int(nuevo) + 0.99
        elif redondeo == "EURO ENTERO": nuevo = float(round(nuevo))
        
        return max(0, nuevo)

    def _row_styler(self, item, idx):
        if item.get("_pvp_propuesto_numeric") is not None:
            return {'bg': '#1b2a20', 'fg': '#2ECC71'}
        return None

    def _on_quitar(self):
        indices = self.nav_list.selected_indices
        if not indices: return
        
        # Eliminar de atrás hacia adelante
        for idx in sorted(list(indices), reverse=True):
            if idx < len(self._items_tabla):
                self._items_tabla.pop(idx)
        
        self.nav_list.set_items(self._items_tabla)
        self._load_status_lbl.configure(text=f"Total: {len(self._items_tabla)} productos")

    def _on_simular_plantilla(self):
        tpl = self._tpl_entry.get().strip()
        if not tpl:
            show_error(self.frame, "Escribe el nombre de la plantilla")
            return
            
        for item in self._items_tabla:
            item["resultado"] = f"Plantilla: {tpl}"
            item["_tpl_propuesta"] = tpl
            
        self.nav_list.set_items(self._items_tabla)

    def _on_guardar(self):
        updates = []
        for item in self._items_tabla:
            node = item["_node"]
            
            # PVP
            if item.get("_pvp_propuesto_numeric") is not None:
                variants = node.get("variants", {}).get("nodes", [])
                for v in variants:
                    updates.append({
                        "product_id": node["id"],
                        "variant_id": v["id"],
                        "new_price": item["_pvp_propuesto_numeric"]
                    })
            
            # Plantilla
            if item.get("_tpl_propuesta") is not None:
                updates.append({
                    "product_id": node["id"],
                    "new_template": item["_tpl_propuesta"]
                })

        if not updates:
            show_error(self.frame, "No hay cambios pendientes para guardar")
            return

        if not tk.messagebox.askyesno("Confirmar", f"Vas a aplicar cambios masivos en {len(self._items_tabla)} productos de Shopify.\n\n¿Estás seguro?"):
            return

        self._btn_save.configure(state="disabled", text="GUARDANDO...")
        
        def work():
            res = self.service.actualizar_productos_lote(updates)
            
            def done():
                self._btn_save.configure(state="normal", text="ACTUALIZAR EN SHOPIFY")
                if res["success"]:
                    show_success(self.frame, "Actualización masiva completada")
                    # Limpiar propuestas tras éxito
                    for item in self._items_tabla:
                        if item.get("_pvp_propuesto_numeric") is not None:
                            item["pvp_actual"] = item["pvp_propuesto"]
                            item["_pvp_numeric"] = item["_pvp_propuesto_numeric"]
                            item["pvp_propuesto"] = ""
                            item["_pvp_propuesto_numeric"] = None
                        if item.get("_tpl_propuesta") is not None:
                            item["_tpl_propuesta"] = None
                        item["resultado"] = "OK"
                    self.nav_list.set_items(self._items_tabla)
                else:
                    show_error(self.frame, f"Hubo algunos errores:\n{res['message']}")
            
            self.frame.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _status(self, txt):
        self._load_status_lbl.configure(text=txt)
