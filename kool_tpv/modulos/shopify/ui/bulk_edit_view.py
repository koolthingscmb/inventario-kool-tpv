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
from kool_tpv.utils.dialogs.metaobject_select_dialog import show_reference_select_dialog
from ..services.shopify_product_service import ShopifyProductService
from ..services.shopify_metafields_service import ShopifyMetafieldsService

logger = logging.getLogger(__name__)

class ShopifyBulkEditView:
    """Subvista para la edición masiva de productos en Shopify."""

    ICONOS_ESTADO = {"ACTIVE": "●", "DRAFT": "○", "ARCHIVED": "✕"}

    COLUMNAS = [
        ('id', 60, 'ID'),
        ('title', 300, 'TÍTULO', True),
        ('productType', 120, 'TIPO'),
        ('template', 102, 'PLANTILLA'),
        ('status', 20, '◉'),
        ('pvp_actual', 60, '€€'),
        ('valor_actual', 170, 'VALOR ACTUAL'),
        ('resultado', 380, 'RESULTADO')
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
        self._mf_valores: List[str] = []
        self._mf_valores_nombres: List[str] = []
        self._mf_coleccion = None
        self._vact_token = 0

        try:
            self._colors_cfg = load_colors('shopify')
            self._primary = self._colors_cfg.get('primary', '#00A4DF')
            self._secondary = self._colors_cfg.get('secondary', '#3498db')
            self._accent = self._colors_cfg.get('accent', '#5DADE2')
            self._bg = self._colors_cfg.get('background', '#000000')
            self._bg_medium = self._colors_cfg.get('bg_medium', '#1a1a1a')
        except Exception:
            self._primary, self._secondary, self._accent = '#00A4DF', '#3498db', '#5DADE2'
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
        ctk.CTkButton(row_pvp, text="1) PULSAR PARA PREPARAR LOS CAMBIOS", width=320, height=28, fg_color=self._accent, text_color="#000", command=self._on_aplicar).pack(side="left", padx=15)

        # Fila 3: Cambio de metacampo
        row_mf = tk.Frame(filter_frame, bg=self._bg_medium)
        row_mf.pack(fill="x", padx=20, pady=(0, 15))

        tk.Label(row_mf, text="CAMBIO DE METACAMPO:", font=("Helvetica", 10, "bold"), fg=self._secondary, bg=self._bg_medium).pack(side="left", padx=(0, 10))
        self._mf_combo = SearchableCombo(row_mf, width=220, placeholder="Elige metacampo...",
                                         module_name="shopify", command=self._on_meta_seleccionado)
        self._mf_combo.pack(side="left", padx=5)
        self._mf_val_frame = tk.Frame(row_mf, bg=self._bg_medium)
        self._mf_val_frame.pack(side="left", padx=5)
        self._mf_modo_var = tk.StringVar(value="AÑADIR")
        self._mf_radios = {t: ctk.CTkRadioButton(row_mf, text=t, variable=self._mf_modo_var, value=t, width=90,
                                                 font=("Helvetica", 10), state="disabled",
                                                 command=self._on_modo_cambiado)
                           for t in ("AÑADIR", "CAMBIAR", "QUITAR")}
        for r in self._mf_radios.values():
            r.pack(side="left", padx=(15, 0))
        self._mf_val_widget = None
        self._construir_valor_meta(None)

        # Fila 4: cambios preparados; cada uno es una etiqueta que se quita con un clic.
        # Se muestra solo cuando hay algo preparado (ver _refrescar_chips).
        self._row_chips = tk.Frame(filter_frame, bg=self._bg_medium)
        tk.Label(self._row_chips, text="CAMBIOS PREPARADOS (clic para quitar):", font=("Helvetica", 10, "bold"),
                 fg=self._secondary, bg=self._bg_medium).pack(side="left", padx=(0, 10))
        self._chips_frame = tk.Frame(self._row_chips, bg=self._bg_medium)
        self._chips_frame.pack(side="left")

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
        
        self._btn_save = ctk.CTkButton(footer, text="2) ACTUALIZAR EN SHOPIFY", fg_color="#27ae60", width=260,
                                       font=("Helvetica", 13, "bold"), state="disabled", command=self._on_guardar)
        self._btn_save.pack(side="right")

        # Cargar tipos y metacampos iniciales
        self._cargar_tipos()
        self._cargar_metacampos()

    def _cargar_metacampos(self):
        def work():
            try:
                defs = self.mf_service.obtener_definiciones_custom()
                S = ShopifyMetafieldsService
                validas = [d for d in defs if d["type"]["name"] in S.TIPOS_MASIVOS + S.TIPOS_COLECCION
                           + S.TIPOS_METAOBJETO + S.TIPOS_METAOBJETO_UNICO
                           or (d["type"]["name"] in S.TIPOS_LISTA and S.opciones_lista(d))]
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
        self._cargar_valores_actuales()

    def _cargar_valores_actuales(self):
        """Rellena la columna VALOR ACTUAL con lo que tiene hoy cada producto en el metacampo elegido.

        Lee de Shopify en un hilo (solo lectura). Si cambia el metacampo o la lista mientras se lee,
        el resultado antiguo se descarta.
        """
        self._vact_token += 1
        token = self._vact_token
        d = self._mf_defs.get(self._mf_nombre_actual or "")
        items = list(self._items_tabla)
        for item in items:
            item["valor_actual"] = "…" if d else ""
        self.nav_list.refresh()
        if not d or not items:
            return
        ids = [i["_node"]["id"] for i in items]
        namespace, key, tipo = d["namespace"], d["key"], d["type"]["name"]

        def work():
            try:
                valores = self.service.leer_valores_metacampo(ids, namespace, key, tipo)
            except Exception:
                logger.exception("Error leyendo el valor actual de %s.%s", namespace, key)
                valores = None
            try:
                self.frame.after(0, lambda: self._aplicar_valores_actuales(token, items, valores))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _aplicar_valores_actuales(self, token, items, valores):
        """'—' = sin valor; '?' = no se pudo leer ese producto."""
        if token != self._vact_token:
            return
        if valores is None:
            show_error(self.frame, "No se pudo leer el valor actual del metacampo")
        for item in items:
            v = (valores or {}).get(item["_node"]["id"])
            item["valor_actual"] = "?" if v is None else (v or "—")
        self.nav_list.refresh()

    def _construir_valor_meta(self, tipo, nombre=None):
        """Muestra el control de valor adecuado al tipo del metacampo elegido."""
        for w in self._mf_val_frame.winfo_children():
            w.destroy()
        self._mf_tipo_actual = tipo
        self._mf_nombre_actual = nombre
        self._mf_valores = []
        self._mf_valores_nombres = []
        self._mf_valor_unico = None
        self._mf_valor_unico_nombre = ""
        self._mf_coleccion = None
        es_lista = tipo in ShopifyMetafieldsService.TIPOS_LISTA + ShopifyMetafieldsService.TIPOS_METAOBJETO
        es_familia = tipo in ShopifyMetafieldsService.TIPOS_COLECCION
        # AÑADIR solo tiene sentido en listas y familia; en un valor único, CAMBIAR es asignar el valor.
        # QUITAR borra el metacampo y vale para todo salvo familia (que tiene su propia lógica de colecciones).
        self._mf_modo_var.set("AÑADIR" if (es_lista or es_familia) else "CAMBIAR")
        self._mf_radios["AÑADIR"].configure(state="normal" if (es_lista or es_familia) else "disabled")
        self._mf_radios["CAMBIAR"].configure(state="normal" if tipo else "disabled")
        self._mf_radios["QUITAR"].configure(state="normal" if (tipo and not es_familia) else "disabled")
        if tipo in ShopifyMetafieldsService.TIPOS_COLECCION:
            self._mf_val_widget = ctk.CTkButton(self._mf_val_frame, text="ELEGIR COLECCIÓN", width=200, height=28,
                                                fg_color=self._secondary, command=self._elegir_coleccion)
            self._mf_val_widget.pack(side="left")
            return
        if tipo in ShopifyMetafieldsService.TIPOS_LISTA:
            self._mf_val_widget = ctk.CTkButton(self._mf_val_frame, text="ELEGIR VALORES (0)", width=170, height=28,
                                                fg_color=self._secondary, command=self._elegir_valores_lista)
            self._mf_val_widget.pack(side="left")
            return
        if tipo in ShopifyMetafieldsService.TIPOS_METAOBJETO:
            self._mf_val_widget = ctk.CTkButton(self._mf_val_frame, text="ELEGIR VALORES (0)", width=170, height=28,
                                                fg_color=self._secondary, command=self._elegir_metaobjetos)
            self._mf_val_widget.pack(side="left")
            return
        if tipo in ShopifyMetafieldsService.TIPOS_METAOBJETO_UNICO:
            self._mf_val_widget = ctk.CTkButton(self._mf_val_frame, text="ELEGIR VALOR", width=170, height=28,
                                                fg_color=self._secondary, command=self._elegir_metaobjeto_unico)
            self._mf_val_widget.pack(side="left")
            return
        if tipo == "boolean":
            self._mf_val_widget = ctk.CTkOptionMenu(self._mf_val_frame, values=["SÍ", "NO"], width=100, height=28)
        else:
            self._mf_val_widget = ctk.CTkEntry(self._mf_val_frame, width=220, height=28,
                                               placeholder_text="Valor..." if tipo else "Elige metacampo primero...")
        self._mf_val_widget.pack(side="left")

    def _elegir_valores_lista(self):
        """Abre el selector de casillas con las opciones definidas en Shopify para la lista."""
        d = self._mf_defs.get(self._mf_nombre_actual)
        if not d:
            return
        opciones = [{"id": o, "text": o} for o in ShopifyMetafieldsService.opciones_lista(d)]
        res = show_reference_select_dialog(self.frame, f"SELECCIONAR {self._mf_nombre_actual}", opciones,
                                           self._mf_valores, multi_select=True, agrupar=False)
        if res is not None:
            self._mf_valores = [o["id"] for o in opciones if o["id"] in res]
            self._mf_val_widget.configure(text=f"ELEGIR VALORES ({len(self._mf_valores)})")

    def _elegir_metaobjetos(self):
        """Trae las entradas del metaobjeto en un hilo y abre el selector en el hilo principal."""
        d = self._mf_defs.get(self._mf_nombre_actual)
        if not d:
            return
        definition_id = next((v.get("value") for v in d.get("validations", [])
                              if v.get("name") == "metaobject_definition_id"), None)
        if not definition_id:
            show_error(self.frame, "No se encontró la definición del metaobjeto en Shopify")
            return
        self._load_status_lbl.configure(text="Cargando opciones...", fg=self._primary)

        def work():
            tipo_meta = self.mf_service.obtener_tipo_metaobjeto_por_definicion(definition_id)
            entradas = self.mf_service.obtener_entradas_metaobjeto(tipo_meta) if tipo_meta else []
            self.frame.after(0, lambda: self._mostrar_selector_metaobjetos(entradas))

        threading.Thread(target=work, daemon=True).start()

    def _mostrar_selector_metaobjetos(self, entradas):
        self._load_status_lbl.configure(text="")
        if not entradas:
            show_error(self.frame, "No hay entradas creadas para este metaobjeto en Shopify")
            return
        opciones = [{"id": e["id"], "text": e.get("displayName") or e["id"]} for e in entradas]
        res = show_reference_select_dialog(self.frame, f"SELECCIONAR {self._mf_nombre_actual}", opciones,
                                           list(self._mf_valores), multi_select=True, agrupar=False)
        if res is not None:
            self._mf_valores = [o["id"] for o in opciones if o["id"] in res]
            self._mf_valores_nombres = [o["text"] for o in opciones if o["id"] in res]
            self._mf_val_widget.configure(text=f"ELEGIR VALORES ({len(self._mf_valores)})")

    def _elegir_metaobjeto_unico(self):
        """Metaobjeto de valor único: mismo origen de datos, selector de una opción."""
        d = self._mf_defs.get(self._mf_nombre_actual)
        if not d:
            return
        definition_id = next((v.get("value") for v in d.get("validations", [])
                              if v.get("name") == "metaobject_definition_id"), None)
        if not definition_id:
            show_error(self.frame, "No se encontró la definición del metaobjeto en Shopify")
            return
        self._load_status_lbl.configure(text="Cargando opciones...", fg=self._primary)

        def work():
            tipo_meta = self.mf_service.obtener_tipo_metaobjeto_por_definicion(definition_id)
            entradas = self.mf_service.obtener_entradas_metaobjeto(tipo_meta) if tipo_meta else []
            self.frame.after(0, lambda: self._mostrar_selector_metaobjeto_unico(entradas))

        threading.Thread(target=work, daemon=True).start()

    def _mostrar_selector_metaobjeto_unico(self, entradas):
        self._load_status_lbl.configure(text="")
        if not entradas:
            show_error(self.frame, "No hay entradas creadas para este metaobjeto en Shopify")
            return
        opciones = [{"id": e["id"], "text": e.get("displayName") or e["id"]} for e in entradas]
        res = show_reference_select_dialog(self.frame, f"SELECCIONAR {self._mf_nombre_actual}", opciones,
                                           self._mf_valor_unico, multi_select=False, agrupar=False)
        if res is not None:
            self._mf_valor_unico = res
            self._mf_valor_unico_nombre = next(
                (o["text"] for o in opciones if o["id"] == res), "")
            self._mf_val_widget.configure(text=self._mf_valor_unico_nombre.upper()[:30])

    def _on_modo_cambiado(self):
        """Con QUITAR no hay que elegir valor: el control de valor se apaga."""
        if self._mf_tipo_actual not in ShopifyMetafieldsService.TIPOS_COLECCION \
                and self._mf_val_widget is not None:
            self._mf_val_widget.configure(state="disabled" if self._mf_modo_var.get() == "QUITAR" else "normal")

    def _elegir_coleccion(self):
        """Pide las colecciones a Shopify en un hilo y abre el selector en el hilo principal."""
        self._load_status_lbl.configure(text="Cargando colecciones...", fg=self._primary)

        def work():
            cols = self.mf_service.obtener_colecciones()
            self.frame.after(0, lambda: self._mostrar_selector_coleccion(cols))

        threading.Thread(target=work, daemon=True).start()

    def _mostrar_selector_coleccion(self, cols):
        self._load_status_lbl.configure(text="")
        if not cols:
            show_error(self.frame, "No se encontraron colecciones en Shopify")
            return
        opciones = [{"id": c["id"], "text": c["title"]} for c in cols]
        actual = self._mf_coleccion["id"] if self._mf_coleccion else None
        res = show_reference_select_dialog(self.frame, "SELECCIONAR FAMILIA", opciones, actual,
                                           multi_select=False, agrupar=False)
        if res:
            titulo = next((o["text"] for o in opciones if o["id"] == res), res)
            self._mf_coleccion = {"id": res, "title": titulo}
            self._mf_val_widget.configure(text=titulo.upper()[:26])

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
        self._vact_token += 1
        self._all_products = []
        self._items_tabla = []
        self.nav_list.clear_items()
        self._actualizar_estado_guardar()
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
            "status": self.ICONOS_ESTADO.get(node["status"], "?"),
            "pvp_actual": f"{pvp:.2f}€",
            "_pvp_numeric": pvp,
            "pvp_propuesto": "",
            "_pvp_propuesto_numeric": None,
            "_mf_lista": [],
            "valor_actual": "",
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
            return
        if self._mf_nombre_actual:
            self._cargar_valores_actuales()

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
                self._cargar_valores_actuales()
                show_error(self.frame, "Escribe el valor del metacampo y pulsa APLICAR otra vez")
                return
            if tipo in ShopifyMetafieldsService.TIPOS_COLECCION:
                if not self._mf_coleccion:
                    show_error(self.frame, "Elige la colección de familia")
                    return
                modo = "añadir" if self._mf_modo_var.get() == "AÑADIR" else "cambiar"
                mf = {"namespace": d["namespace"], "key": d["key"], "type": tipo,
                      "modo": modo, "coleccion": self._mf_coleccion["id"],
                      "coleccion_nombre": self._mf_coleccion["title"]}
            elif self._mf_modo_var.get() == "QUITAR" and tipo not in (
                    ShopifyMetafieldsService.TIPOS_LISTA + ShopifyMetafieldsService.TIPOS_METAOBJETO):
                # valor único o escalar: se borra el metacampo de los productos que lo tengan
                mf = {"namespace": d["namespace"], "key": d["key"], "type": tipo, "modo": "quitar"}
            elif tipo in ShopifyMetafieldsService.TIPOS_METAOBJETO_UNICO:
                if not self._mf_valor_unico:
                    show_error(self.frame, "Elige un valor para el metacampo")
                    return
                mf = {"namespace": d["namespace"], "key": d["key"], "type": tipo,
                      "value": self._mf_valor_unico, "nombres": [self._mf_valor_unico_nombre]}
            elif tipo in (ShopifyMetafieldsService.TIPOS_LISTA
                          + ShopifyMetafieldsService.TIPOS_METAOBJETO):
                eleccion = self._mf_modo_var.get()
                if eleccion != "QUITAR" and not self._mf_valores:
                    show_error(self.frame, "Elige al menos un valor para la lista")
                    return
                modo = {"AÑADIR": "añadir", "CAMBIAR": "sustituir", "QUITAR": "vaciar"}[eleccion]
                mf = {"namespace": d["namespace"], "key": d["key"], "type": tipo, "modo": modo,
                      "valores": [] if modo == "vaciar" else list(self._mf_valores)}
                if tipo in ShopifyMetafieldsService.TIPOS_METAOBJETO:
                    mf["nombres"] = [] if modo == "vaciar" else list(self._mf_valores_nombres)
            else:
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
                item["_tpl_propuesta"] = tpl

        if mf:
            if mf.get("modo") == "quitar":
                meta = f"{mf['key']}: QUITAR"
                confirmacion = (f"Metacampo `{mf['key']}`: QUITAR (se borrará su valor en los productos "
                                "seleccionados que lo tengan)")
            elif mf["type"] == "collection_reference":
                nombre = mf["coleccion_nombre"]
                if mf["modo"] == "añadir":
                    meta = f"{mf['key']}: AÑADIR {nombre}"
                    confirmacion = f"Familia (`{mf['key']}`): AÑADIR `{nombre}` (solo a los productos sin familia)"
                else:
                    meta = f"{mf['key']}: CAMBIAR a {nombre}"
                    confirmacion = f"Familia (`{mf['key']}`): CAMBIAR a `{nombre}` (sale de su familia anterior)"
            elif mf["type"] in ShopifyMetafieldsService.TIPOS_METAOBJETO_UNICO:
                nombre = (mf.get("nombres") or [mf["value"]])[0]
                meta = f"{mf['key']} = {nombre}"
                confirmacion = f"Metacampo `{mf['key']}`: asignar `{nombre}` a los productos seleccionados"
            elif mf.get("modo") == "vaciar":
                meta = f"{mf['key']}: QUITAR"
                confirmacion = f"Metacampo `{mf['key']}`: QUITAR (se quitarán TODOS los valores)"
            elif "valores" in mf:
                visibles = mf.get("nombres") or mf["valores"]
                lista = ", ".join(visibles)
                signo, accion = ("+", "AÑADIR") if mf["modo"] == "añadir" else ("=", "CAMBIAR a")
                meta = f"{mf['key']} {signo} {lista}"
                confirmacion = f"Metacampo `{mf['key']}`: {accion} " + ", ".join(f"`{v}`" for v in visibles)
            else:
                visible = {"true": "SÍ", "false": "NO"}.get(mf["value"], mf["value"]) if mf["type"] == "boolean" else mf["value"]
                meta = f"{mf['key']} = {visible}"
                confirmacion = f"Metacampo `{mf['key']}` = `{visible}`"
            clave = (mf["namespace"], mf["key"])
            for item in self._items_tabla:
                # varios metacampos por producto: repetir uno solo reemplaza ese
                previos = [e for e in item.get("_mf_lista") or []
                           if (e["mf"]["namespace"], e["mf"]["key"]) != clave]
                previos.append({"mf": mf, "texto": meta, "confirm": confirmacion})
                item["_mf_lista"] = previos

        for item in self._items_tabla:
            self._refrescar_resultado(item)
        self.nav_list.set_items(self._items_tabla)
        self._actualizar_estado_guardar()

    def _calcular_nuevo_pvp(self, actual, op, val):
        nuevo = actual
        if op == "PRECIO FIJO": nuevo = val
        elif op == "SUBIR %": nuevo = actual * (1 + val/100)
        elif op == "BAJAR %": nuevo = actual * (1 - val/100)
        elif op == "SUBIR €": nuevo = actual + val
        elif op == "BAJAR €": nuevo = actual - val
        return max(0, nuevo)

    def _row_styler(self, item, idx):
        if item.get("_pvp_propuesto_numeric") is not None or item.get("_mf_lista"):
            return {'bg': '#1b2a20', 'fg': '#2ECC71'}
        return None

    @staticmethod
    def _refrescar_resultado(item):
        """Texto único de RESULTADO: precio nuevo, plantilla y metacampo preparados para esta fila."""
        partes = []
        if item.get("_pvp_propuesto_numeric") is not None:
            partes.append(item["pvp_propuesto"])
        if item.get("_tpl_propuesta"):
            partes.append(f"Plantilla: {item['_tpl_propuesta']}")
        partes.extend(e["texto"] for e in item.get("_mf_lista") or [])
        item["resultado"] = " · ".join(partes)

    def _actualizar_estado_guardar(self):
        """El botón ACTUALIZAR solo se activa cuando hay cambios preparados en la tabla."""
        hay = any(i.get("_pvp_propuesto_numeric") is not None or i.get("_tpl_propuesta") or i.get("_mf_lista")
                  for i in self._items_tabla)
        self._btn_save.configure(state="normal" if hay else "disabled")
        self._refrescar_chips()

    def _cambios_preparados(self):
        """[(texto, quitar)] de lo preparado en la tabla: PVP, plantillas y cada metacampo."""
        cambios = []
        if any(i.get("_pvp_propuesto_numeric") is not None for i in self._items_tabla):
            cambios.append((self._desc_pvp, self._quitar_pvp))
        for tpl in sorted({i["_tpl_propuesta"] for i in self._items_tabla if i.get("_tpl_propuesta")}):
            cambios.append((f"Plantilla: {tpl}", lambda t=tpl: self._quitar_plantilla(t)))
        metas = {}
        for i in self._items_tabla:
            for e in i.get("_mf_lista") or []:
                metas.setdefault((e["mf"]["namespace"], e["mf"]["key"]), e["texto"])
        for clave, texto in metas.items():
            cambios.append((texto, lambda c=clave: self._quitar_metacampo(c)))
        return cambios

    def _refrescar_chips(self):
        """Redibuja la franja de cambios preparados (oculta si no hay ninguno)."""
        if not hasattr(self, "_chips_frame"):
            return
        for w in self._chips_frame.winfo_children():
            w.destroy()
        cambios = self._cambios_preparados()
        for texto, quitar in cambios:
            # el borrado se retrasa para no destruir el botón mientras CTk termina su animación de clic
            ctk.CTkButton(self._chips_frame, text=f"{texto}  ✕", height=26, fg_color="#1b2a20",
                          text_color="#2ECC71", hover_color="#8b1a1a", border_width=1, border_color="#2ECC71",
                          font=("Helvetica", 10),
                          command=lambda q=quitar: self.frame.after(150, q)).pack(side="left", padx=(0, 6))
        if cambios:
            self._row_chips.pack(fill="x", padx=20, pady=(0, 12))
        else:
            self._row_chips.pack_forget()

    def _quitar_pvp(self):
        for i in self._items_tabla:
            i["pvp_propuesto"] = ""
            i["_pvp_propuesto_numeric"] = None
        self._tras_quitar_cambio()

    def _quitar_plantilla(self, tpl):
        for i in self._items_tabla:
            if i.get("_tpl_propuesta") == tpl:
                i["_tpl_propuesta"] = None
        self._tras_quitar_cambio()

    def _quitar_metacampo(self, clave):
        for i in self._items_tabla:
            i["_mf_lista"] = [e for e in i.get("_mf_lista") or []
                              if (e["mf"]["namespace"], e["mf"]["key"]) != clave]
        self._tras_quitar_cambio()

    def _tras_quitar_cambio(self):
        for i in self._items_tabla:
            self._refrescar_resultado(i)
        self.nav_list.set_items(self._items_tabla)
        self._actualizar_estado_guardar()

    def _on_quitar(self):
        indices = self.nav_list.selected_indices
        if not indices: return
        
        # Eliminar de atrás hacia adelante
        for idx in sorted(list(indices), reverse=True):
            if idx < len(self._items_tabla):
                self._items_tabla.pop(idx)
        
        self.nav_list.set_items(self._items_tabla)
        self._load_status_lbl.configure(text=f"Total: {len(self._items_tabla)} productos")
        self._actualizar_estado_guardar()


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
            for e in item.get("_mf_lista") or []:
                updates.append({
                    "product_id": node["id"],
                    "metafield": e["mf"]
                })

        if not updates:
            show_error(self.frame, "No hay cambios pendientes para guardar")
            return

        cambios = []
        if any(i.get("_pvp_propuesto_numeric") is not None for i in self._items_tabla):
            cambios.append(self._desc_pvp)
        for tpl in sorted({i["_tpl_propuesta"] for i in self._items_tabla if i.get("_tpl_propuesta")}):
            cambios.append(f"Plantilla: {tpl}")
        for txt in sorted({e["confirm"] for i in self._items_tabla for e in i.get("_mf_lista") or []}):
            cambios.append(txt)
        detalle = "\n".join(f"- {c}" for c in cambios)

        if not show_warning(self.frame, "CONFIRMAR EDICIÓN MASIVA",
                            f"Vas a aplicar cambios masivos en {len(self._items_tabla)} productos de Shopify:\n{detalle}\n¿Estás seguro?",
                            confirm=True):
            return

        self._btn_save.configure(state="disabled", text="GUARDANDO...")
        
        def work():
            res = self.service.actualizar_productos_lote(updates)
            
            def done():
                self._btn_save.configure(text="2) ACTUALIZAR EN SHOPIFY")
                if res["success"]:
                    omitidos = res.get("omitidos", 0)
                    show_success(self.frame, "Actualización masiva completada"
                                 + (f" ({omitidos} omitidos: no hacía falta cambiarlos)" if omitidos else ""))
                    # Limpiar propuestas tras éxito
                    for item in self._items_tabla:
                        if item.get("_pvp_propuesto_numeric") is not None:
                            item["pvp_actual"] = item["pvp_propuesto"]
                            item["_pvp_numeric"] = item["_pvp_propuesto_numeric"]
                            item["pvp_propuesto"] = ""
                            item["_pvp_propuesto_numeric"] = None
                        if item.get("_tpl_propuesta") is not None:
                            item["_tpl_propuesta"] = None
                        item["_mf_lista"] = []
                        item["resultado"] = "OK"
                    self.nav_list.set_items(self._items_tabla)
                    if res.get("avisos"):
                        show_warning(self.frame, "AVISO", "\n".join(res["avisos"]))
                else:
                    detalle = "\n".join(res.get("errores", [])[:6]) or res["message"]
                    show_error(self.frame, f"Hubo algunos errores:\n{detalle}")
                    if res.get("avisos"):
                        show_warning(self.frame, "AVISO", "\n".join(res["avisos"]))
            
            # tras guardar (con o sin errores) se vuelve a leer, para ver el resultado real en VALOR ACTUAL
            self.frame.after(0, lambda: (done(), self._actualizar_estado_guardar(),
                                         self._cargar_valores_actuales()))

        threading.Thread(target=work, daemon=True).start()

    def _status(self, txt):
        self._load_status_lbl.configure(text=txt)
