"""Subvista SUBIDA: crea y edita productos en Shopify desde el TPV.

Flujo: rellenar datos del diseño -> GENERAR CONTENIDO (IA) -> revisar/editar ->
SUBIR A SHOPIFY (productSet, imágenes, precios por variante).
"""
import logging
import threading
import re
import tkinter as tk
from typing import Dict, Any, Optional, List

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from ..services.shopify_product_service import ShopifyProductService
from .shopify_actualiza_sku import ShopifyActualizaSku
from .shopify_metafields_ui import ShopifyMetafieldsUI
from ..services.producto_content_service import ProductoContentService, slugify_diseno
from ..services.producto_prompts import TONO_POR_DEFECTO
from ..services.shopify_config_service import ShopifyConfigService
from ..services.shopify_upload_builder import ShopifyUploadBuilder
from .subida.componentes.selector_imagenes import SelectorImagenes

logger = logging.getLogger(__name__)


_slugify = slugify_diseno


class ShopifyUploadView:
    """Vista de subida/edición de camisetas a Shopify."""

    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.product_service = ShopifyProductService(db)
        self.content_service = ProductoContentService(db)
        self.config_service = ShopifyConfigService(db)
        self.upload_builder = ShopifyUploadBuilder(db)

        try:
            self._colors_cfg = load_colors('shopify')
            self._primary = self._colors_cfg.get('primary', '#00A4DF')
            self._secondary = self._colors_cfg.get('secondary', '#3498db')
            self._bg = self._colors_cfg.get('background', '#000000')
            self._bg_medium = self._colors_cfg.get('bg_medium', '#1a1a1a')
        except Exception:
            self._primary, self._secondary = '#00A4DF', '#3498db'
            self._bg, self._bg_medium = '#000000', '#1a1a1a'

        self._modo = "NUEVO"
        self._edit_product: Optional[Dict[str, Any]] = None
        self._search_results: List[Dict[str, Any]] = []
        self._entries: Dict[str, Any] = {}
        self._body_boxes: Dict[str, Any] = {}
        self._tipo_service = TipoService(db)
        self._tipos: List[Dict[str, Any]] = []
        self._variantes_disponibles: List[Dict[str, Any]] = []
        self._skus_preparados: Optional[Dict[str, Any]] = None
        self._metafields_preparados: List[Dict[str, Any]] = []

        self.frame = tk.Frame(parent, bg=self._bg)
        self._build()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        self._content = scroll

        # --- Header con título + botón SUBIR a la derecha ---
        head = tk.Frame(scroll, bg=self._bg)
        head.pack(fill="x", pady=(14, 8))
        tk.Label(head, text="SUBIDA DE PRODUCTOS A SHOPIFY",
                 font=("Helvetica", 13, "bold"), fg=self._primary,
                 bg=self._bg, anchor="w").pack(side="left")
        accent_btn = (self._colors_cfg.get("buttons") or {}).get("accent", {})
        self._btn_upload = ctk.CTkButton(
            head, text="SUBIR A SHOPIFY", width=240, height=40,
            fg_color=accent_btn.get("bg", "#81F0FF"),
            hover_color=accent_btn.get("hover", "#4FB1E6"),
            text_color=accent_btn.get("text", "#000000"),
            font=("Helvetica", 13, "bold"), command=self._subir)
        self._btn_upload.pack(side="right")
        tk.Frame(head, bg=self._primary, height=2).pack(
            side="left", fill="x", expand=True, padx=(12, 12), pady=(2, 0))

        # --- Modo ---
        modo_frame = tk.Frame(scroll, bg=self._bg)
        modo_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._btn_nuevo = self._modo_btn(modo_frame, "NUEVO PRODUCTO", "NUEVO")
        self._btn_editar = self._modo_btn(modo_frame, "EDITAR EXISTENTE", "EDITAR")

        # Status bajo los botones de modo
        self._status_lbl = tk.Label(scroll, text="", fg="#888", bg=self._bg,
                                    font=("Helvetica", 11), anchor="w", justify="left")
        self._status_lbl.pack(fill="x", padx=10, pady=(0, 5))

        # --- Panel EDITAR ---
        self._edit_frame = tk.Frame(scroll, bg=self._bg_medium)
        tk.Label(self._edit_frame, text="Buscar producto en Shopify:", fg="#FFF",
                 bg=self._bg_medium, font=("Helvetica", 11)).pack(side="left", padx=10, pady=10)
        self._search_entry = ctk.CTkEntry(self._edit_frame, width=280, height=34,
                                          placeholder_text="título, handle o SKU...")
        self._search_entry.pack(side="left", padx=5)
        self._search_entry.bind("<Return>", lambda e: self._buscar_producto())
        ctk.CTkButton(self._edit_frame, text="BUSCAR", width=90, height=34,
                      fg_color=self._secondary, command=self._buscar_producto).pack(side="left", padx=5)
        self._search_combo = ctk.CTkOptionMenu(self._edit_frame, values=["—"], width=350, height=34,
                                               command=self._on_pick_result)
        self._search_combo.pack(side="left", padx=10)
        ctk.CTkButton(self._edit_frame, text="CARGAR", width=90, height=34,
                      fg_color=self._primary, text_color="#000",
                      command=self._cargar_producto_sel).pack(side="left", padx=5)
        self._btn_skus = ctk.CTkButton(
            self._edit_frame, text="SKUS", width=90, height=34,
            fg_color=self._secondary, text_color="#FFF",
            font=("Helvetica", 11, "bold"), command=self._abrir_skus)
        self._btn_skus.pack(side="left", padx=5)
        
        self._skus_status_lbl = tk.Label(self._edit_frame, text="", fg="#7CFC90", bg=self._bg_medium,
                                         font=("Helvetica", 9, "bold"))
        self._skus_status_lbl.pack(side="left", padx=5)

        self._meta_status_lbl = tk.Label(self._edit_frame, text="", fg="#7CFC90", bg=self._bg_medium,
                                         font=("Helvetica", 9, "bold"))
        self._meta_status_lbl.pack(side="left", padx=5)

        # --- Formulario ---
        self._section("DATOS DEL DISEÑO")
        form = tk.Frame(scroll, bg=self._bg)
        form.pack(fill="x", padx=10)
        for c in range(4):
            form.columnconfigure(c, weight=1)

        self._field(form, "titulo", "TÍTULO BASE", "Camiseta X | Tema", 0, 0)

        # Tags con botón GENERAR
        cell_tags = tk.Frame(form, bg=self._bg)
        cell_tags.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tags, text="TAGS", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        tags_row = tk.Frame(cell_tags, bg=self._bg)
        tags_row.pack(fill="x")
        self._entries["tags"] = ctk.CTkEntry(tags_row, placeholder_text="anime, friki, regalo",
                                             height=34, font=("Helvetica", 12))
        self._entries["tags"].pack(side="left", fill="x", expand=True)
        self._btn_tags = ctk.CTkButton(tags_row, text="GENERAR", width=80, height=34,
                                       fg_color=self._secondary, font=("Helvetica", 10, "bold"),
                                       command=self._generar_tags)
        self._btn_tags.pack(side="left", padx=(6, 0))

        # Beneficio como SearchableCombo
        cell_ben = tk.Frame(form, bg=self._bg)
        cell_ben.grid(row=0, column=2, sticky="ew", padx=6, pady=4)
        tk.Label(cell_ben, text="BENEFICIO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        
        try:
            r_ben = self.db.fetch_all("SELECT texto FROM shopify_beneficios ORDER BY id")
            ben_opts = [r[0] for r in (r_ben or [])]
        except Exception:
            ben_opts = []

        self._ben_combo = SearchableCombo(cell_ben, values=ben_opts, placeholder="Elegir beneficio...", 
                                          width=200, module_name='shopify')
        self._ben_combo.pack(fill="x")
        self._entries["beneficio"] = self._ben_combo

        # Tono como SearchableCombo (cargado de BD)
        cell_tono = tk.Frame(form, bg=self._bg)
        cell_tono.grid(row=0, column=3, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tono, text="TONO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        
        try:
            r_tonos = self.db.fetch_all("SELECT nombre FROM shopify_tonos ORDER BY nombre")
            tonos_opts = [r[0] for r in (r_tonos or [])]
        except Exception:
            tonos_opts = []
            
        self._tono_combo = SearchableCombo(cell_tono, values=tonos_opts, placeholder="Tono...", 
                                           width=150, module_name='shopify')
        self._tono_combo.pack(fill="x")
        self._tono_combo.set(TONO_POR_DEFECTO)
        self._entries["tono"] = self._tono_combo

        self._field(form, "codigo_categoria", "SUFIJO SKU", "FRI (opcional)", 1, 0)

        cell_estado = tk.Frame(form, bg=self._bg)
        cell_estado.grid(row=1, column=1, sticky="w", padx=6, pady=4)
        tk.Label(cell_estado, text="ESTADO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        self._status_menu = ctk.CTkOptionMenu(cell_estado, values=["ACTIVE", "DRAFT"],
                                              width=160, height=34)
        self._status_menu.set("ACTIVE")
        self._status_menu.pack(anchor="w")

        # Tipo de producto: combo buscable con los tipos de la BD
        cell_tipo = tk.Frame(form, bg=self._bg)
        cell_tipo.grid(row=1, column=2, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tipo, text="TIPO PRODUCTO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        try:
            todos = self._tipo_service.get_all_tipos()
            self._tipos = [t for t in todos if t.get("activo") == 1 and t.get("web_activo") == 1]
        except Exception:
            self._tipos = []

        self._tipo_combo = SearchableCombo(
            cell_tipo,
            options=[(t["id"], t["nombre"]) for t in self._tipos],
            command=lambda _v: self._on_tipo_change(),
            placeholder="Escribe para buscar...",
            width=240, module_name='shopify')
        self._tipo_combo.pack(fill="x")

        # Nueva celda: VARIANTE TPV
        cell_variante = tk.Frame(form, bg=self._bg)
        cell_variante.grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        tk.Label(cell_variante, text="VARIANTE TPV", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")

        self._variante_combo = SearchableCombo(
            cell_variante,
            options=[],
            command=lambda _v: self._rebuild_body_boxes(),
            placeholder="Selecciona variante...",
            width=240, module_name='shopify')
        self._variante_combo.pack(fill="x")

        # Variantes activas del tipo: se suben todas las que tengan sync_web = 1
        cell_vars = tk.Frame(form, bg=self._bg)
        cell_vars.grid(row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=4)
        tk.Label(cell_vars, text="VARIANTES A SUBIR:", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(side="left")
        self._variantes_lbl = tk.Label(cell_vars, text="", fg=self._primary, bg=self._bg,
                                       font=("Helvetica", 10, "bold"), anchor="w")
        self._variantes_lbl.pack(side="left", padx=(10, 0))

        # --- Imágenes ---
        self._section("IMÁGENES")
        self._selector_imagenes = SelectorImagenes(scroll, self._bg, self._bg_medium, self._secondary)
        self._selector_imagenes.frame.pack(fill="x")

        # --- Contenido IA ---
        self._section("CONTENIDO (IA)")
        
        ia_row = tk.Frame(scroll, bg=self._bg)
        ia_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(ia_row, text="GENERAR CONTENIDO", width=220, height=40,
                      fg_color=self._primary, text_color="#000",
                      font=("Helvetica", 13, "bold"),
                      command=self._generar_contenido).pack(side="left")
                      
        tk.Label(ia_row, text="TÍTULO SEO:", fg="#888", bg=self._bg,
                 font=("Helvetica", 10, "bold")).pack(side="left", padx=(20, 10))
        self._seo_title_entry = ctk.CTkEntry(ia_row, placeholder_text="Título para Google...",
                                             height=34, font=("Helvetica", 12))
        self._seo_title_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._btn_meta = ctk.CTkButton(
            ia_row, text="METACAMPOS", width=120, height=34,
            fg_color=self._secondary, text_color="#FFF",
            font=("Helvetica", 11, "bold"), command=self._abrir_metafields)
        self._btn_meta.pack(side="left", padx=(10, 0))

        self._meta_nuevo_status_lbl = tk.Label(ia_row, text="", fg="#7CFC90", bg=self._bg,
                                               font=("Helvetica", 9, "bold"))
        self._meta_nuevo_status_lbl.pack(side="left", padx=5)

        cont_grid = tk.Frame(scroll, bg=self._bg)
        cont_grid.pack(fill="both", expand=True, padx=10)
        cont_grid.columnconfigure(0, weight=1)
        cont_grid.columnconfigure(1, weight=1)

        def _content_cell(row, col, titulo, height):
            cell = tk.Frame(cont_grid, bg=self._bg)
            cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            tk.Label(cell, text=titulo, fg="#888", bg=self._bg,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(anchor="w")
            box = ctk.CTkTextbox(cell, height=height, font=("Consolas", 11),
                                 fg_color=self._bg_medium, text_color="#e0e0e0",
                                 border_width=1, border_color=self._primary)
            box.pack(fill="both", expand=True)
            return box

        self._seo_box = _content_cell(0, 0, "META DESCRIPCIÓN SEO", 90)
        self._bodies_frame = tk.Frame(cont_grid, bg=self._bg)
        self._bodies_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=4, pady=4)



        self._set_modo("NUEVO")

        # Tipo por defecto: Camiseta si existe
        camiseta = next((t for t in self._tipos if t["nombre"] == "Camiseta"), None)
        if camiseta:
            self._tipo_combo.set_by_id(camiseta["id"])
            self._on_tipo_change()

    def _section(self, text):
        f = tk.Frame(self._content, bg=self._bg)
        f.pack(fill="x", pady=(14, 8))
        tk.Label(f, text=text, font=("Helvetica", 13, "bold"), fg=self._primary,
                 bg=self._bg, anchor="w").pack(side="left")
        tk.Frame(f, bg=self._primary, height=2).pack(side="left", fill="x", expand=True,
                                                    padx=(12, 0), pady=(2, 0))

    def _modo_btn(self, parent, text, modo):
        b = ctk.CTkButton(parent, text=text, width=180, height=36,
                          command=lambda: self._set_modo(modo))
        b.pack(side="left", padx=(0, 8))
        return b

    def _field(self, parent, key, label, placeholder, row, col):
        cell = tk.Frame(parent, bg=self._bg)
        cell.grid(row=row, column=col, sticky="ew", padx=6, pady=4)
        tk.Label(cell, text=label, fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        e = ctk.CTkEntry(cell, placeholder_text=placeholder, height=34, font=("Helvetica", 12))
        e.pack(fill="x")
        self._entries[key] = e

    # ------------------------------------------------------------------
    # Tipo / variantes dinámicas
    # ------------------------------------------------------------------

    def _on_tipo_change(self):
        """Al cambiar el tipo: cargar sus variantes activas marcadas para web."""
        self._variantes_disponibles = []
        
        # Limpiar combo de variante específica
        if hasattr(self, '_variante_combo'):
            self._variante_combo.clear()

        tipo_id = self._tipo_combo.get_id()
        if tipo_id:
            try:
                rows = self.db.fetch_all(
                    "SELECT id, nombre FROM tipos_variantes WHERE tipo_id = ? AND activo = 1 AND sync_web = 1 ORDER BY orden, nombre",
                    (tipo_id,)
                )
                self._variantes_disponibles = [{"id": r[0], "nombre": r[1]} for r in (rows or [])]
                
                # Rellenar combo de variante específica (para modo EDITAR)
                if hasattr(self, '_variante_combo'):
                    self._variante_combo.set_options([(v["id"], v["nombre"]) for v in self._variantes_disponibles])
            except Exception:
                logger.exception("Error cargando variantes del tipo")
        self._actualizar_label_variantes()
        self._rebuild_body_boxes()

    def _actualizar_label_variantes(self):
        """Muestra las variantes que se van a subir para el tipo elegido."""
        if not self._variantes_lbl:
            return
        if self._variantes_disponibles:
            nombres = ", ".join(v["nombre"].upper() for v in self._variantes_disponibles)
            self._variantes_lbl.configure(text=nombres)
        else:
            self._variantes_lbl.configure(text="NINGUNA (revisa CONFIG → TIPOS)")

    def _rebuild_body_boxes(self):
        """Una caja BODY HTML por cada variante activa del tipo (conserva el texto)."""
        textos = {n: b.get("1.0", "end-1c") for n, b in self._body_boxes.items()}
        for child in self._bodies_frame.winfo_children():
            child.destroy()
        self._body_boxes = {}

        # Determinar si agrupamos según el tipo seleccionado
        agrupar = False
        tipo_id = self._tipo_combo.get_id()
        if tipo_id:
            try:
                res = self.db.fetch_one("SELECT shopify_agrupar_variantes FROM tipos WHERE id = ?", (tipo_id,))
                agrupar = bool(res[0]) if res else False
            except: pass

        # Determinar qué variantes mostrar
        variantes_a_mostrar = self._variantes_disponibles
        if agrupar:
            # Si agrupamos, solo mostramos una caja genérica
            variantes_a_mostrar = [{"id": None, "nombre": "General"}]
        elif self._modo == "EDITAR" and hasattr(self, '_variante_combo'):
            sel = self._variante_combo.get().strip()
            if sel:
                # Mostrar solo la variante seleccionada
                variantes_a_mostrar = [v for v in self._variantes_disponibles if v["nombre"] == sel]
                if not variantes_a_mostrar:
                    # Fallback por si la variante no está en la lista de activas
                    variantes_a_mostrar = [{"id": None, "nombre": sel}]

        for i, v in enumerate(variantes_a_mostrar):
            nombre = v["nombre"]
            cell = tk.Frame(self._bodies_frame, bg=self._bg)
            cell.grid(row=i, column=0, sticky="ew", pady=(0, 6))
            self._bodies_frame.columnconfigure(0, weight=1)
            tk.Label(cell, text=f"BODY HTML — {nombre.upper()}", fg="#888", bg=self._bg,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(anchor="w")
            box = ctk.CTkTextbox(cell, height=90, font=("Consolas", 11),
                                 fg_color=self._bg_medium, text_color="#e0e0e0",
                                 border_width=1, border_color=self._primary)
            box.pack(fill="both", expand=True)
            self._body_boxes[nombre] = box
            if nombre in textos:
                box.insert("1.0", textos[nombre])

    def _set_modo(self, modo):
        self._modo = modo
        for btn, m in ((self._btn_nuevo, "NUEVO"), (self._btn_editar, "EDITAR")):
            btn.configure(fg_color=self._primary if m == modo else self._secondary,
                          text_color="#000" if m == modo else "#FFF")
        
        # UI del campo variante según modo
        if hasattr(self, '_variante_combo'):
            if modo == "EDITAR":
                self._variante_combo.entry.configure(state="normal")
            else:
                self._variante_combo.entry.configure(state="disabled")

        if modo == "EDITAR":
            self._edit_frame.pack(fill="x", padx=10, pady=5, after=self._content.winfo_children()[1])
            self._btn_upload.configure(text="ACTUALIZAR PRODUCTO")
        else:
            self._edit_frame.pack_forget()
            self._edit_product = None
            self._btn_upload.configure(text="SUBIR A SHOPIFY")
            self._limpiar_formulario()

    def _limpiar_formulario(self):
        """Vacía todos los campos al pasar a modo NUEVO."""
        for e in self._entries.values():
            if hasattr(e, "delete"):
                e.delete(0, "end")
            elif hasattr(e, "clear"):
                e.clear()
        self._seo_box.delete("1.0", "end")
        if hasattr(self, '_seo_title_entry'):
            self._seo_title_entry.delete(0, "end")
        self._tipo_combo.clear()
        if hasattr(self, '_variante_combo'):
            self._variante_combo.clear()
        self._variantes_disponibles = []
        self._actualizar_label_variantes()
        self._rebuild_body_boxes()
        self._selector_imagenes.limpiar()
        self._status_menu.set("ACTIVE")
        self._status("")
        self._skus_preparados = None
        self._metafields_preparados = []
        if hasattr(self, '_skus_status_lbl'):
            self._skus_status_lbl.configure(text="")

    # ------------------------------------------------------------------
    # Modo EDITAR
    # ------------------------------------------------------------------

    def _buscar_producto(self):
        texto = self._search_entry.get().strip()
        if not texto:
            return
        self._status("Buscando...")

        def work():
            results = self.product_service.buscar_productos(texto)
            self.frame.after(0, lambda: self._fill_results(results))
        threading.Thread(target=work, daemon=True).start()

    def _fill_results(self, results):
        self._search_results = results
        if not results:
            self._search_combo.configure(values=["Sin resultados"])
            self._search_combo.set("Sin resultados")
            self._status("")
            return
        self._search_combo.configure(values=[r["title"] for r in results])
        self._search_combo.set(results[0]["title"])
        self._status(f"{len(results)} productos encontrados")

    def _on_pick_result(self, _):
        pass

    def _cargar_producto_sel(self):
        titulo = self._search_combo.get()
        prod = next((r for r in self._search_results if r["title"] == titulo), None)
        if not prod:
            show_error(self.frame, "Selecciona un producto de la lista")
            return
        self._status("Cargando producto...")
        self._skus_preparados = None
        self._metafields_preparados = []
        self._selector_imagenes.limpiar()
        if hasattr(self, '_skus_status_lbl'):
            self._skus_status_lbl.configure(text="")

        def work():
            full = self.product_service.cargar_producto(prod["id"])
            self.frame.after(0, lambda: self._fill_edit(full))
        threading.Thread(target=work, daemon=True).start()

    def _fill_edit(self, prod):
        if not prod:
            self._status("Error cargando el producto")
            return
        self._edit_product = prod
        self._entries["tags"].delete(0, "end")
        self._entries["tags"].insert(0, ", ".join(prod.get("tags") or []))
        self._seo_box.delete("1.0", "end")
        self._seo_box.insert("1.0", (prod.get("seo") or {}).get("description") or "")
        self._status_menu.set(prod.get("status", "DRAFT"))

        # Resolución inteligente de Tipo y Variante TPV
        p_type = prod.get("productType", "")
        tipo_id = None
        variante_id = None
        variante_nombre = None

        # 1. Intentar por mapeo explícito en BD (shopify_product_id)
        # Esto es lo más fiable para productos subidos/editados con la nueva versión
        mapping = self.product_service.repo.get_diseno_mapping_by_shopify_id(prod["id"])
        if mapping and mapping.get("genero"):
            v_info = self._tipo_service.get_variante_by_nombre(mapping["genero"])
            if v_info:
                tipo_id = v_info["tipo_id"]
                variante_id = v_info["id"]
                variante_nombre = v_info["nombre"]

        # 2. Si no hay mapeo, intentar resolver por el productType de Shopify
        if not tipo_id and p_type:
            # ¿Es un nombre de tipo directo?
            t_info = self._tipo_service.get_tipo_by_nombre(p_type)
            if t_info:
                tipo_id = t_info["id"]
            else:
                # ¿Es un nombre de variante? (ej: Riñonera)
                v_info = self._tipo_service.get_variante_by_nombre(p_type)
                if v_info:
                    tipo_id = v_info["tipo_id"]
                    variante_id = v_info["id"]
                    variante_nombre = v_info["nombre"]

        # Aplicar a la UI
        if tipo_id:
            self._tipo_combo.set_by_id(tipo_id)
            self._on_tipo_change()  # Rellena el combo de variantes
            if variante_id:
                self._variante_combo.set_by_id(variante_id)
            # Forzar reconstrucción de cajas de texto con la variante ya seleccionada
            self._rebuild_body_boxes()
        else:
            # Fallback: poner el texto tal cual si no reconocemos el tipo
            self._tipo_combo.set(p_type)
            self._on_tipo_change()
            self._rebuild_body_boxes()

        # Separar el título base de la variante cuando Shopify lo tiene como "Base | Variante"
        full_title = prod.get("title", "")
        base_title = full_title
        if not variante_nombre:
            variante_nombre = self._variante_combo.get().strip()

        if variante_nombre and full_title.endswith(f" | {variante_nombre}"):
            base_title = full_title[:-(len(f" | {variante_nombre}"))]
        elif " | " in full_title:
            # Fallback: si el sufijo coincide con alguna variante activa del tipo, la usamos
            partes = full_title.rsplit(" | ", 1)
            nombres_variantes = {v["nombre"] for v in self._variantes_disponibles}
            if partes[1] in nombres_variantes:
                base_title = partes[0]
                variante_nombre = partes[1]
                # Sincronizar el combo con el sufijo detectado
                self._variante_combo.set(variante_nombre)
                self._rebuild_body_boxes()

        # 1. Borrar labels de metacampos
        if hasattr(self, '_meta_status_lbl'):
            self._meta_status_lbl.configure(text="")
        if hasattr(self, '_meta_nuevo_status_lbl'):
            self._meta_nuevo_status_lbl.configure(text="")
            
        self._entries["titulo"].delete(0, "end")
        self._entries["titulo"].insert(0, base_title)

        if hasattr(self, '_seo_title_entry'):
            self._seo_title_entry.delete(0, "end")
            self._seo_title_entry.insert(0, (prod.get("seo") or {}).get("title") or "")

        for box in self._body_boxes.values():
            box.delete("1.0", "end")
        if self._body_boxes:
            next(iter(self._body_boxes.values())).insert(
                "1.0", prod.get("descriptionHtml") or "")
        self._selector_imagenes.set_web([{"url": m["image"]["url"], "alt": m.get("alt") or ""}
                                         for m in prod.get("media", {}).get("nodes", [])
                                         if m.get("image")])

        # Log de metacampos para depuración (Paso 1)
        metafields = prod.get("metafields", {}).get("nodes", [])
        if metafields:
            logger.info(f"Metacampos cargados para {prod.get('handle')}:")
            for mf in metafields:
                val_desc = mf.get('value')
                if mf.get('reference') and mf['reference'].get('image'):
                    val_desc = f"[REF ARCHIVO: {mf['reference']['image']['url']}]"
                logger.info(f"  - {mf.get('namespace')}.{mf.get('key')} ({mf.get('type')}): {val_desc}")
            self._status(f"Cargado: {prod.get('handle')} ({len(metafields)} metacampos)")
        else:
            self._status(f"Cargado: {prod.get('handle')}")

    def _abrir_skus(self):
        """Abre la subvista de edición de SKUs para el producto cargado."""
        if not self._edit_product:
            show_error(self.frame, "Carga primero un producto")
            return
        tipo_nombre = self._tipo_combo.get().strip()
        tipo_id = self._tipo_combo.get_id()
        variante_nombre = self._variante_combo.get().strip()
        variante_id = self._variante_combo.get_id()

        if tipo_id is None and tipo_nombre:
            try:
                tipo = self._tipo_service.get_tipo_by_nombre(tipo_nombre)
                if tipo:
                    tipo_id = tipo.get("id")
            except Exception:
                logger.exception("Error resolviendo tipo para SKUs")

        self.frame.pack_forget()
        sku_view = ShopifyActualizaSku(
            self.frame.master, self.db, self._edit_product,
            tipo_id=tipo_id, tipo_nombre=tipo_nombre,
            variante_id=variante_id, variante_nombre=variante_nombre,
            on_volver=lambda: self.frame.pack(fill="both", expand=True),
            on_aceptar=self._on_skus_preparados)
        sku_view.frame.pack(fill="both", expand=True)

    def _on_skus_preparados(self, datos):
        """Recibe los SKUs preparados desde la subvista."""
        self._skus_preparados = datos
        n = len(datos.get("variantes") or [])
        if n > 0:
            self._skus_status_lbl.configure(text=f"✓ {n} SKUS LISTOS")
        else:
            self._skus_status_lbl.configure(text="")

    def _abrir_metafields(self):
        """Abre la subvista de edición de Metacampos para el producto cargado o nuevo."""
        prod_data = self._edit_product or {}
        if not self._edit_product:
            # Modo NUEVO: pasamos el título actual y los metacampos que hayamos preparado
            prod_data = {
                "title": self._entries["titulo"].get().strip() or "NUEVO PRODUCTO",
                "metafields_list": self._metafields_preparados
            }
            
        self.frame.pack_forget()
        meta_view = ShopifyMetafieldsUI(
            self.frame.master, self.db, prod_data,
            on_volver=lambda: self.frame.pack(fill="both", expand=True),
            on_aceptar=self._on_metafields_preparados)
        meta_view.frame.pack(fill="both", expand=True)

    def _on_metafields_preparados(self, metafields):
        """Recibe la lista de metacampos desde la subvista (para modo NUEVO o EDITAR)."""
        self._metafields_preparados = metafields
        # Contamos cuántos tienen valor para informar al usuario en la barra de estado
        n = len([m for m in metafields if str(m.get("value", "")).strip()])
        
        status_text = f"✓ {n} METACAMPOS LISTOS" if n > 0 else ""
        
        if hasattr(self, '_meta_status_lbl'):
            self._meta_status_lbl.configure(text=status_text)
        if hasattr(self, '_meta_nuevo_status_lbl'):
            self._meta_nuevo_status_lbl.configure(text=status_text)
            
        if n > 0:
            self._status(f"✓ {n} METACAMPOS PREPARADOS")
        else:
            self._status("Metacampos actualizados")

    # ------------------------------------------------------------------
    # Generar contenido IA
    # ------------------------------------------------------------------

    def _generar_tags(self):
        titulo = self._entries["titulo"].get().strip()
        if not titulo:
            show_error(self.frame, "Rellena primero el título base")
            return
        self._status("Generando tags...")
        tipo_id = self._tipo_combo.get_id()

        def work():
            tipo_producto = self._tipo_combo.get().strip()
            tags, err = self.content_service.generar_tags(titulo, tipo_producto, tipo_id=tipo_id)
            def done():
                if tags:
                    self._entries["tags"].delete(0, "end")
                    self._entries["tags"].insert(0, tags)
                    self._status("Tags generados — revísalos")
                else:
                    self._status(f"Error tags: {err}")
            self.frame.after(0, done)
        threading.Thread(target=work, daemon=True).start()

    def _generar_contenido(self):
        titulo = self._entries["titulo"].get().strip()
        tags = self._entries["tags"].get().strip()
        beneficio = self._entries["beneficio"].get().strip()
        tono = self._entries["tono"].get().strip()
        if not titulo:
            show_error(self.frame, "Rellena al menos el título base")
            return
        variantes = [v["nombre"] for v in self._variantes_disponibles]
        if not variantes:
            show_error(self.frame, "El tipo seleccionado no tiene variantes activas para web")
            return
        tipo_id = self._tipo_combo.get_id()

        self._status("Generando contenido con IA...")

        def work():
            res = self.content_service.generar_todo(titulo, tags, beneficio, tono, variantes, tipo_id=tipo_id)
            self.frame.after(0, lambda: self._fill_content(res, tipo_id))
        threading.Thread(target=work, daemon=True).start()

    def _fill_content(self, res, tipo_id: Optional[int] = None):
        if res.get("seo_desc"):
            self._seo_box.delete("1.0", "end")
            self._seo_box.insert("1.0", res["seo_desc"])
        
        titulo = self._entries["titulo"].get().strip()

        # Rellenar SEO Title con la variante adecuada:
        # en modo editar usamos la variante cargada del producto, no la primera del tipo.
        variante_seo = ""
        if self._modo == "EDITAR" and hasattr(self, '_variante_combo'):
            variante_seo = self._variante_combo.get().strip()
        if not variante_seo and self._variantes_disponibles:
            variante_seo = self._variantes_disponibles[0]["nombre"]

        if variante_seo and hasattr(self, '_seo_title_entry'):
            beneficio = self._entries["beneficio"].get().strip()
            seo_title = self.content_service.seo_title_for(titulo, variante_seo, beneficio=beneficio, tipo_id=tipo_id)
            self._seo_title_entry.delete(0, "end")
            self._seo_title_entry.insert(0, seo_title)
            
        todas = [v["nombre"] for v in self._variantes_disponibles]
        for genero, body in res.get("bodies", {}).items():
            html = self.content_service.montar_html(body, genero, titulo, todas, tipo_id=tipo_id)
            if genero in self._body_boxes:
                self._body_boxes[genero].delete("1.0", "end")
                self._body_boxes[genero].insert("1.0", html)
        if res.get("errores"):
            self._status("Errores: " + " | ".join(res["errores"]))
        else:
            self._status("Contenido generado. Revísalo antes de subir.")

    # ------------------------------------------------------------------
    # Subir / actualizar
    # ------------------------------------------------------------------

    def _subir(self):
        titulo = self._entries["titulo"].get().strip()
        if not titulo:
            show_error(self.frame, "Falta el título base")
            return

        cfg = self.config_service.get_config()
        seo_desc = self._seo_box.get("1.0", "end-1c").strip()
        status = self._status_menu.get()
        product_type = self._tipo_combo.get().strip()
        tipo_id = self._tipo_combo.get_id()

        # Taxonomía Shopify desde la categoría del tipo
        taxonomy_gid = None
        try:
            tipo = next((t for t in self._tipos if t["id"] == tipo_id), None)
            if tipo is None and product_type:
                tipo = self._tipo_service.get_tipo_by_nombre(product_type)
            if tipo and tipo.get("categoria_id"):
                cat = CategoriaRepository(self.db).get_by_id(tipo["categoria_id"])
                if cat:
                    taxonomy_gid = cat.get("shopify_taxonomy")
        except Exception:
            logger.exception('Error obteniendo taxonomy_gid')

        tipo = next((t for t in self._tipos if t["id"] == tipo_id), None)
        use_variant_as_type = False
        agrupar_variantes = False
        if tipo:
            use_variant_as_type = bool(tipo.get("shopify_use_variant_as_type"))
            agrupar_variantes = bool(tipo.get("shopify_agrupar_variantes"))

        template_suffix = ""
        if tipo and tipo.get("template_suffix"):
            template_suffix = tipo["template_suffix"].strip()

        def _safe_float(val, default=0.0):
            if val is None or str(val).lower() == 'none' or str(val).strip() == '':
                return default
            try:
                # Limpiar el valor antes de procesar (quitar € y arreglar comas)
                clean_val = str(val).replace('€', '').replace(',', '.').strip()
                # Usar adaptadores de moneda para precisión exacta
                return float(read_from_db(prepare_for_db(clean_val)))
            except:
                return default

        seo_title = self._seo_title_entry.get().strip() if hasattr(self, '_seo_title_entry') else ""
        if not seo_title:
            seo_title = titulo[:70]

        base = {
            "tags": [t.strip() for t in self._entries["tags"].get().split(",") if t.strip()],
            "seo_desc": seo_desc,
            "seo_title": seo_title,
            "status": status,
            "codigo_categoria": self._entries["codigo_categoria"].get().strip().upper(),
            "product_type": product_type,
            "taxonomy_gid": taxonomy_gid,
            "template_suffix": template_suffix,
            "recargo_tallas": _safe_float(cfg.get("recargo_tallas")),
            "recargo_grupo_id": cfg.get("recargo_grupo_id"),
            "use_variant_as_type": use_variant_as_type,
            "agrupar_variantes": agrupar_variantes,
            "metafields": self._metafields_preparados,
        }

        if self._modo == "EDITAR":
            if not self._edit_product:
                show_error(self.frame, "Carga primero un producto")
                return
            self._subir_edicion(base)
        else:
            self._subir_nuevo(base)

    def _subir_nuevo(self, base):
        titulo = self._entries["titulo"].get().strip()
        iniciales = self.product_service.iniciales_diseno(titulo)
        cfg = self.config_service.get_config()
        tipo_nombre = self._tipo_combo.get().strip()
        con_sorpresa = self.upload_builder.aplica_sorpresa(tipo_nombre)

        if not self._variantes_disponibles:
            show_error(self.frame, "El tipo seleccionado no tiene variantes activas para web")
            return

        trabajos = []
        todas_las_variantes_stock = []
        agrupar = base.get("agrupar_variantes", False)

        for v_info in self._variantes_disponibles:
            variante_id = v_info["id"]
            variante = v_info["nombre"]
            variantes = self.product_service.get_variantes_stock(variante_id)
            if not variantes:
                continue

            # Asegurar cantidad entera en cada variante real
            for v in variantes:
                v["cantidad"] = int(v.get("cantidad") or 0)
                # Si agrupamos, el nombre de la variante TPV se convierte en una opción de Shopify (ej: Talla o Género)
                if agrupar:
                    # Guardamos el nombre del género para identificarlo luego
                    v["tpv_variante_nombre"] = variante

            # Color "Sorpresa": solo en camisetas, una opción extra por talla (sin control de inventario)
            if con_sorpresa:
                variantes.extend(self.upload_builder.variantes_sorpresa(
                    tipo_nombre, variante, [v["talla"] for v in variantes], marcar_variante_tpv=agrupar))

            if agrupar:
                todas_las_variantes_stock.extend(variantes)
            else:
                # Flujo normal: un producto por variante
                body_box = self._body_boxes.get(variante)
                datos = dict(base)
                if base.get("use_variant_as_type"):
                    datos["product_type"] = variante

                tipo_id = self._tipo_combo.get_id()
                beneficio = self._entries["beneficio"].get().strip()
                datos.update({
                    "title": f"{titulo} | {variante}",
                    "handle": f"{_slugify(titulo)}-{_slugify(variante)}",
                    "description_html": body_box.get("1.0", "end-1c") if body_box else "",
                    "seo_title": self.content_service.seo_title_for(titulo, variante, beneficio=beneficio, tipo_id=tipo_id),
                    "tags": base["tags"] + [variante],
                    "variantes": variantes,
                    "iniciales": iniciales,
                    "imagenes": self._selector_imagenes.obtener_locales(),
                    "vendor": cfg.get("marca") or "Kool Things",
                    "diseno_codigo": _slugify(titulo),
                    "genero": variante,
                })
                trabajos.append(datos)

        # Si agrupamos, creamos UN SOLO TRABAJO con todas las variantes
        if agrupar and todas_las_variantes_stock:
            # En modo agrupado, el nombre de la variante TPV se añade como el valor de la opción 'Talla'
            for v in todas_las_variantes_stock:
                orig_talla = v.get("talla") or ""
                tpv_var = v.get("tpv_variante_nombre") or ""
                
                # Forzamos que requiera talla para que el motor cree la opción en Shopify
                v["requiere_talla"] = 1
                v["requiere_color"] = 0 # Normalmente las láminas no tienen opción color
                
                # Si la talla está vacía o es igual al nombre de la variante, usamos el nombre de la variante
                if not orig_talla or orig_talla.upper() == "ÚNICA":
                    v["talla"] = tpv_var
                else:
                    # Si ya tiene talla, las combinamos (ej: Lámina - A4)
                    v["talla"] = f"{tpv_var} {orig_talla}"

            # Usar la primera descripción disponible o una genérica
            desc = ""
            if self._body_boxes:
                desc = next(iter(self._body_boxes.values())).get("1.0", "end-1c")

            tipo_id = self._tipo_combo.get_id()
            beneficio = self._entries["beneficio"].get().strip()
            
            datos_unico = dict(base)
            datos_unico.update({
                "title": titulo,
                "handle": _slugify(titulo),
                "description_html": desc,
                "seo_title": self.content_service.seo_title_for(titulo, "", beneficio=beneficio, tipo_id=tipo_id),
                "tags": base["tags"],
                "variantes": todas_las_variantes_stock,
                "iniciales": iniciales,
                "imagenes": self._selector_imagenes.obtener_locales(),
                "vendor": cfg.get("marca") or "Kool Things",
                "diseno_codigo": _slugify(titulo),
                "genero": "Pack", # Genérico para el mapeo
            })
            trabajos.append(datos_unico)

        if not trabajos:
            show_error(self.frame, "No hay stock para las variantes seleccionadas")
            return

        self._status(f"Subiendo {len(trabajos)} productos...")
        self._btn_upload.configure(state="disabled")

        def work():
            mensajes = []
            for datos in trabajos:
                genero = datos.get('genero', 'Producto')
                try:
                    r = self.product_service.product_set(datos)
                    mensajes.append(f"{genero}: {'OK' if r['success'] else r['message']}")
                except Exception as e:
                    logger.exception(f"Error inesperado subiendo {genero}")
                    mensajes.append(f"{genero}: Error inesperado ({type(e).__name__}), revisa la terminal")
            self.frame.after(0, lambda: self._fin_upload(mensajes))
        threading.Thread(target=work, daemon=True).start()

    def _subir_edicion(self, base):
        prod = self._edit_product
        variantes_input = []
        
        # Si tenemos SKUs preparados desde la subvista, usarlos (prioridad máxima)
        # Esto permite crear colores nuevos y actualizar stock/precios/skus de golpe
        if self._skus_preparados:
            variantes_preparadas = list(self._skus_preparados.get("variantes") or [])
            variante_nombre = self._skus_preparados.get("genero") or self._variante_combo.get().strip()
            diseno = self._skus_preparados.get("diseno")
            diseno_codigo = diseno.codigo if diseno else (prod.get("handle") or _slugify(self._entries["titulo"].get().strip()))

            # Color "Sorpresa": conserva el SKU/precio que ya tenga en Shopify y va sin control de inventario
            tipo_nombre = self._tipo_combo.get().strip()
            if self.upload_builder.aplica_sorpresa(tipo_nombre):
                variantes_preparadas.extend(self.upload_builder.variantes_sorpresa(
                    tipo_nombre, variante_nombre, [v["talla"] for v in variantes_preparadas],
                    existentes=self.upload_builder.sorpresas_existentes(prod)))

            # En SKUs preparados, usamos 'variantes' para que product_set las procese
            # y 'variantes_input' debe ser None para que entre en la lógica de construcción
            variantes_input = None 
            base_variantes = variantes_preparadas
            # Evitar que product_set vuelva a construir el SKU (ya vienen listos)
            base["codigo_categoria"] = ""
            base["iniciales"] = ""
        else:
            # Flujo estándar: solo lo que ya tiene Shopify
            variantes_existentes = []
            for v in prod.get("variants", {}).get("nodes", []):
                # Extraer info para que product_set pueda procesarlo
                v_talla, v_color = "", ""
                for opt in v.get("selectedOptions", []):
                    if opt["name"].upper() == "TALLA": v_talla = opt["value"]
                    if opt["name"].upper() == "COLOR": v_color = opt["value"]
                
                variantes_existentes.append({
                    "sku": v.get("sku") or "",
                    "precio": str(v.get("price") or "0"),
                    "color": v_color,
                    "talla": v_talla,
                    "cantidad": -1, # No tocar stock si no pasamos por SKUs
                    # El precio viene de Shopify tal cual: no sumarle el recargo otra vez
                    "precio_ya_final": True,
                    # Sorpresa sin control de inventario también al editar sin pasar por SKUs
                    "tracked": not self.upload_builder.es_color_sorpresa(v_color),
                })
            variante_nombre = self._variante_combo.get().strip()
            diseno_codigo = prod.get("handle") or _slugify(self._entries["titulo"].get().strip())
            base_variantes = variantes_existentes
            variantes_input = None

        # Reconstruir las opciones del producto para Shopify
        product_options = []
        for o in prod.get("options", []):
            values = []
            for x in o.get("values", []):
                if isinstance(x, dict):
                    values.append({"name": x.get("name", "")})
                else:
                    values.append({"name": x})
            product_options.append({"name": o["name"], "values": values})

        datos = dict(base)

        # Si el tipo usa variantes como tipo, el product_type es el nombre de la variante
        if base.get("use_variant_as_type") and variante_nombre:
            datos["product_type"] = variante_nombre

        # Reconstruir el título igual que en modo nuevo: base + variante
        titulo_base = self._entries["titulo"].get().strip()
        title = titulo_base
        if not base.get("agrupar_variantes", False) and variante_nombre:
            title = f"{titulo_base} | {variante_nombre}"

        datos.update({
            "title": title,
            "handle": prod.get("handle") or _slugify(titulo_base),
            "description_html": (next(iter(self._body_boxes.values())).get("1.0", "end-1c")
                                 if self._body_boxes else prod.get("descriptionHtml") or ""),
            "product_id": prod["id"],
            "variantes_input": variantes_input,
            "variantes": base_variantes,
            "product_options": product_options,
            "imagenes": self._selector_imagenes.obtener_locales(),
            "imagenes_url": self._selector_imagenes.obtener_web(),
            "diseno_codigo": diseno_codigo,
            "genero": variante_nombre,
        })

        self._status("Actualizando producto...")
        self._btn_upload.configure(state="disabled")

        def work():
            try:
                r = self.product_service.product_set(datos)
                msg = "Actualizado OK" if r["success"] else f"Error: {r['message']}"
            except Exception as e:
                logger.exception("Error inesperado actualizando el producto")
                msg = f"Error inesperado ({type(e).__name__}), revisa la terminal"
            self.frame.after(0, lambda: self._fin_upload([msg]))
        threading.Thread(target=work, daemon=True).start()

    def _fin_upload(self, mensajes):
        self._btn_upload.configure(state="normal")
        ok = all("OK" in m for m in mensajes)
        status_txt = "\n".join(mensajes)
        if ok and self._modo == "NUEVO":
            # Tras una subida nueva 100% correcta, dejar el formulario limpio para el siguiente producto
            self._limpiar_formulario()
        self._status(status_txt)
        
        if ok:
            logger.info(f"Subida completada con éxito: {status_txt}")
            show_success(self.frame, "Subida completada:\n" + status_txt)
        else:
            logger.error(f"Fallo en la subida: {status_txt}")
            show_error(self.frame, "Revisa los resultados:\n" + status_txt)

    def _status(self, texto):
        try:
            self._status_lbl.configure(text=texto)
        except Exception:
            pass
