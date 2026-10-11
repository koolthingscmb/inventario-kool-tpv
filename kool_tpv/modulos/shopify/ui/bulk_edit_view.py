"""BulkEditView: Edición masiva de productos de Shopify.

Permite filtrar por tipo, tag y estado, previsualizar cambios y aplicar
actualizaciones de PVP y plantilla en lote de forma asíncrona.
"""
import logging
import threading
import tkinter as tk
from typing import List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.utils.dialogs.helpers import show_warning
from ..services.shopify_product_service import ShopifyProductService
from ..services.shopify_metafields_service import ShopifyMetafieldsService

logger = logging.getLogger(__name__)

class ShopifyBulkEditView:
    """Subvista para la edición masiva de productos en Shopify."""

    COLUMNAS = [
        ('id', 60, 'ID'),
        ('title', 300, 'TÍTULO', True),
        ('productType', 120, 'TIPO'),
        ('template', 180, 'PLANTILLA'),
        ('status', 100, 'ESTADO'),
        ('pvp_actual', 64, '€€'),
        ('pvp_propuesto', 120, '€€NEW'),
        ('meta', 170, 'META'),
        ('resultado', 120, 'RESULTADO')
    ]

    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.service = ShopifyProductService(db)
        self.mf_service = ShopifyMetafieldsService(db)
        self._mf_defs: Dict[str, Dict[str, Any]] = {}
        self._mf_tipo_actual = None
        self._mf_nombre_actual = None
        self._desc_pvp = ""

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
        row1.pack(fill="x", padx=20, pady=(15, 15))

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

        self._excluir_borradores_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text="EXCLUIR BORRADORES", variable=self._excluir_borradores_var,
                        font=("Helvetica", 10), text_color="#AAA").pack(side="left", padx=(15, 10))

        self._excluir_archivados_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text="EXCLUIR ARCHIVADOS", variable=self._excluir_archivados_var,
                        font=("Helvetica", 10), text_color="#AAA").pack(side="left")

        self._load_status_lbl = tk.Label(row1, text="", font=("Helvetica", 10), fg="#888", bg=self._bg_medium)
        self._load_status_lbl.pack(side="right", padx=10)

        # Fila 2: Cambios de PVP y plantilla
        row_pvp = tk.Frame(filter_frame, bg=self._bg_medium)
        row_pvp.pack(fill="x", padx=20, pady=(0, 10))
        
        tk.Label(row_pvp, text="CAMBIO DE PVP:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg_medium).pack(side="left", padx=(0, 10))
        
        self._op_pvp = ctk.CTkOptionMenu(row_pvp, values=["PRECIO FIJO", "SUBIR %", "BAJAR %", "SUBIR €", "BAJAR €"], width=130)
        self._op_pvp.pack(side="left", padx=5)
        
        self._val_pvp = ctk.CTkEntry(row_pvp, width=80, height=28, placeholder_text="Valor...")
        self._val_pvp.pack(side="left", padx=5)
        


        tk.Label(row_pvp, text="CAMBIO DE PLANTILLA:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg_medium).pack(side="left", padx=(30, 10))
        self._tpl_entry = ctk.CTkEntry(row_pvp, width=200, height=28, placeholder_text="Nombre de plantilla...")
        self._tpl_entry.pack(side="left", padx=5)
        ctk.CTkButton(row_pvp, text="APLICAR", width=120, height=28, fg_color=self._secondary, command=self._on_aplicar).pack(side="left", padx=15)

        # Fila 3: Cambio de metacampo
        row_mf = tk.Frame(filter_frame, bg=self._bg_medium)
        row_mf.pack(fill="x", padx=20, pady=(0, 15))

        tk.Label(row_mf, text="CAMBIO DE METACAMPO:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg_medium).pack(side="left", padx=(0, 10))
        self._mf_combo = SearchableCombo(row_mf, width=220, placeholder="Elige metacampo...",
                                         module_name="shopify", command=self._on_meta_seleccionado)
        self._mf_combo.pack(side="left", padx=5)
        self._mf_val_frame = tk.Frame(row_mf, bg=self._bg_medium)
        self._mf_val_frame.pack(side="left", padx=5)
        self._mf_val_widget = None
        self._construir_valor_meta(None)

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

        # Cargar tipos y metacampos iniciales
        self._cargar_tipos()
        self._cargar_metacampos()

    def _cargar_metacampos(self):
        def work():
            try:
                defs = self.mf_service.obtener_definiciones_custom()
                validas = [d for d in defs if d["type"]["name"] in ShopifyMetafieldsService.TIPOS_MASIVOS]
                mapa = {d["name"]: d for d in sorted(validas, key=lambda d: d["name"].lower())}
                opts = [(i, nombre) for i, nombre in enumerate(mapa)]

                def apply():
                    self._mf_defs = mapa
                    self._mf_combo.set_options(opts)
                self.frame.after(0, apply)
            except Exception:
                logger.exception("Error cargando definiciones de metacampos")

        threading.Thread(target=work, daemon=True).start()

    def _on_meta_seleccionado(self, nombre):
        nombre = (nombre or "").strip()
        if nombre == self._mf_nombre_actual:
            return  # El combo también avisa al perder el foco: no recrear el campo de valor
        d = self._mf_defs.get(nombre)
        self._construir_valor_meta(d["type"]["name"] if d else None, nombre)

    def _construir_valor_meta(self, tipo, nombre=None):
        """Muestra el control de valor adecuado al tipo del metacampo elegido."""
        for w in self._mf_val_frame.winfo_children():
            w.destroy()
        self._mf_tipo_actual = tipo
        self._mf_nombre_actual = nombre
        if tipo == "boolean":
            self._mf_val_widget = ctk.CTkOptionMenu(self._mf_val_frame, values=["SÍ", "NO"], width=100, height=28)
        else:
            self._mf_val_widget = ctk.CTkEntry(self._mf_val_frame, width=220, height=28,
                                               placeholder_text="Valor..." if tipo else "Elige metacampo primero...")
        self._mf_val_widget.pack(side="left")

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
            if not show_warning(self.frame, "CARGAR TODOS LOS PRODUCTOS",
                                "¿Quieres cargar TODOS los productos de la web?\n\n(Esto puede tardar unos segundos si tienes muchos)",
                                confirm=True):
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
            "meta": "",
            "_mf_propuesto": None,
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

    def _on_aplicar(self):
        """Aplica a la tabla los cambios rellenados (PVP, plantilla y/o metacampo)."""
        val_raw = self._val_pvp.get().replace(',', '.').strip()
        tpl = self._tpl_entry.get().strip()
        mf_nombre = self._mf_combo.get().strip()
        mf = None

        if mf_nombre:
            d = self._mf_defs.get(mf_nombre)
            if not d:
                show_error(self.frame, "Metacampo no válido: elígelo de la lista")
                return
            tipo = d["type"]["name"]
            if mf_nombre != self._mf_nombre_actual:
                self._construir_valor_meta(tipo, mf_nombre)
                show_error(self.frame, "Escribe el valor del metacampo y pulsa APLICAR otra vez")
                return
            valor, err = ShopifyMetafieldsService.validar_valor_masivo(tipo, self._mf_val_widget.get())
            if err:
                show_error(self.frame, err)
                return
            mf = {"namespace": d["namespace"], "key": d["key"], "type": tipo, "value": valor}

        if not val_raw and not tpl and not mf:
            show_error(self.frame, "No hay cambios que aplicar: escribe un precio, una plantilla o elige un metacampo")
            return

        if val_raw:
            try:
                val = float(val_raw)
            except ValueError:
                show_error(self.frame, "Valor de precio inválido")
                return
            op = self._op_pvp.get()
            self._desc_pvp = f"Precio: {op} {val_raw}"
            for item in self._items_tabla:
                nuevo = self._calcular_nuevo_pvp(item["_pvp_numeric"], op, val)
                item["pvp_propuesto"] = f"{nuevo:.2f}€"
                item["_pvp_propuesto_numeric"] = nuevo

        if tpl:
            for item in self._items_tabla:
                item["resultado"] = f"Plantilla: {tpl}"
                item["_tpl_propuesta"] = tpl

        if mf:
            visible = {"true": "SÍ", "false": "NO"}.get(mf["value"], mf["value"]) if mf["type"] == "boolean" else mf["value"]
            for item in self._items_tabla:
                item["meta"] = f"{mf['key']} = {visible}"
                item["_mf_propuesto"] = mf

        self.nav_list.set_items(self._items_tabla)

    def _calcular_nuevo_pvp(self, actual, op, val):
        nuevo = actual
        if op == "PRECIO FIJO": nuevo = val
        elif op == "SUBIR %": nuevo = actual * (1 + val/100)
        elif op == "BAJAR %": nuevo = actual * (1 - val/100)
        elif op == "SUBIR €": nuevo = actual + val
        elif op == "BAJAR €": nuevo = actual - val
        return max(0, nuevo)

    def _row_styler(self, item, idx):
        if item.get("_pvp_propuesto_numeric") is not None or item.get("_mf_propuesto"):
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

            # Metacampo
            if item.get("_mf_propuesto"):
                updates.append({
                    "product_id": node["id"],
                    "metafield": item["_mf_propuesto"]
                })

        if not updates:
            show_error(self.frame, "No hay cambios pendientes para guardar")
            return

        cambios = []
        if any(i.get("_pvp_propuesto_numeric") is not None for i in self._items_tabla):
            cambios.append(self._desc_pvp)
        for tpl in sorted({i["_tpl_propuesta"] for i in self._items_tabla if i.get("_tpl_propuesta")}):
            cambios.append(f"Plantilla: {tpl}")
        for meta in sorted({i["meta"] for i in self._items_tabla if i.get("_mf_propuesto")}):
            clave, _, valor = meta.partition(" = ")
            cambios.append(f"Metacampo `{clave}` = `{valor}`")
        detalle = "\n".join(f"- {c}" for c in cambios)

        if not show_warning(self.frame, "CONFIRMAR EDICIÓN MASIVA",
                            f"Vas a aplicar cambios masivos en {len(self._items_tabla)} productos de Shopify:\n{detalle}\n¿Estás seguro?",
                            confirm=True):
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
                        if item.get("_mf_propuesto"):
                            item["_mf_propuesto"] = None
                            item["meta"] = ""
                        item["resultado"] = "OK"
                    self.nav_list.set_items(self._items_tabla)
                else:
                    show_error(self.frame, f"Hubo algunos errores:\n{res['message']}")
            
            self.frame.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _status(self, txt):
        self._load_status_lbl.configure(text=txt)
