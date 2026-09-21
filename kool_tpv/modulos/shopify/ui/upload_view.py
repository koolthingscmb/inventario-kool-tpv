"""Subvista SUBIDA: crea y edita productos en Shopify desde el TPV.

Flujo: rellenar datos del diseño -> GENERAR CONTENIDO (IA) -> revisar/editar ->
SUBIR A SHOPIFY (productSet, imágenes, precios por variante).
"""
import logging
import threading
import re
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Any, Optional, List

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository
from ..services.shopify_product_service import ShopifyProductService
from .shopify_actualiza_sku import ShopifyActualizaSku
from ..services.producto_content_service import ProductoContentService, slugify_diseno
from ..services.producto_prompts import TONO_POR_DEFECTO
from ..services.shopify_config_service import ShopifyConfigService

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


_slugify = slugify_diseno


class ShopifyUploadView:
    """Vista de subida/edición de camisetas a Shopify."""

    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.product_service = ShopifyProductService(db)
        self.content_service = ProductoContentService(db)
        self.config_service = ShopifyConfigService(db)

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
        self._imagenes: List[Dict[str, Any]] = []   # {path, alt, thumb}
        self._imagenes_web: List[Dict[str, Any]] = []  # {url, alt} existentes
        self._search_results: List[Dict[str, Any]] = []
        self._entries: Dict[str, Any] = {}
        self._body_boxes: Dict[str, Any] = {}
        self._tipo_service = TipoService(db)
        self._tipos: List[Dict[str, Any]] = []
        self._variantes_disponibles: List[Dict[str, Any]] = []
        self._thumb_refs = []

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

        self._field(form, "beneficio", "BENEFICIO", "Algodón premium, diseño exclusivo", 0, 2)
        self._field(form, "tono", "TONO", TONO_POR_DEFECTO, 0, 3)
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
            rows = self.db.fetch_all("SELECT id, nombre, categoria_id FROM tipos WHERE activo = 1 AND web_activo = 1 ORDER BY nombre")
            self._tipos = [{"id": r[0], "nombre": r[1], "categoria_id": r[2]} for r in (rows or [])]
        except Exception:
            self._tipos = []

        self._tipo_combo = SearchableCombo(
            cell_tipo,
            options=[(t["id"], t["nombre"]) for t in self._tipos],
            command=lambda _v: self._on_tipo_change(),
            placeholder="Escribe para buscar...",
            width=240, module_name='shopify')
        self._tipo_combo.pack(fill="x")

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
        img_top = tk.Frame(scroll, bg=self._bg)
        img_top.pack(fill="x", padx=10)
        ctk.CTkButton(img_top, text="SELECCIONAR ARCHIVOS", width=200, height=34,
                      fg_color=self._secondary, command=self._add_images).pack(side="left")
        self._img_list = tk.Frame(scroll, bg=self._bg)
        self._img_list.pack(fill="x", padx=10, pady=5)

        # --- Contenido IA ---
        self._section("CONTENIDO (IA)")
        ctk.CTkButton(scroll, text="GENERAR CONTENIDO", width=220, height=40,
                      fg_color=self._primary, text_color="#000",
                      font=("Helvetica", 13, "bold"),
                      command=self._generar_contenido).pack(padx=10, pady=5, anchor="w")

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

        tipo_id = self._tipo_combo.get_id()
        if tipo_id:
            try:
                rows = self.db.fetch_all(
                    "SELECT id, nombre FROM tipos_variantes WHERE tipo_id = ? AND activo = 1 AND sync_web = 1 ORDER BY orden, nombre",
                    (tipo_id,)
                )
                self._variantes_disponibles = [{"id": r[0], "nombre": r[1]} for r in (rows or [])]
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
        for i, v in enumerate(self._variantes_disponibles):
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
            e.delete(0, "end")
        self._seo_box.delete("1.0", "end")
        self._tipo_combo.clear()
        self._variantes_disponibles = []
        self._actualizar_label_variantes()
        self._rebuild_body_boxes()
        self._imagenes.clear()
        self._imagenes_web.clear()
        self._render_images()
        self._status_menu.set("ACTIVE")
        self._status("")

    # ------------------------------------------------------------------
    # Imágenes
    # ------------------------------------------------------------------

    def _add_images(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona imágenes",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")]
        )
        for p in paths:
            self._imagenes.append({"path": p, "alt": ""})
        self._render_images()

    def _render_images(self):
        for child in self._img_list.winfo_children():
            child.destroy()
        self._thumb_refs.clear()

        for idx, img in enumerate(self._imagenes):
            row_f = tk.Frame(self._img_list, bg=self._bg_medium)
            row_f.pack(fill="x", pady=3)
            if PIL_OK:
                try:
                    pil = Image.open(img["path"]); pil.thumbnail((56, 56))
                    thumb = ImageTk.PhotoImage(pil)
                    self._thumb_refs.append(thumb)
                    tk.Label(row_f, image=thumb, bg=self._bg_medium).pack(side="left", padx=8)
                except Exception:
                    pass
            name = img["path"].split("/")[-1]
            tk.Label(row_f, text=name, fg="#FFF", bg=self._bg_medium,
                     font=("Helvetica", 10), width=30, anchor="w").pack(side="left", padx=5)
            alt = ctk.CTkEntry(row_f, placeholder_text="alt text", width=220, height=28)
            alt.insert(0, img["alt"])
            alt.bind("<FocusOut>", lambda e, i=idx, w=alt: self._imagenes[i].update(alt=w.get()))
            alt.pack(side="left", padx=8)
            ctk.CTkButton(row_f, text="✕", width=30, height=28, fg_color="#8b1a1a",
                          command=lambda i=idx: self._del_image(i)).pack(side="right", padx=8)

        for idx, img in enumerate(self._imagenes_web):
            row_f = tk.Frame(self._img_list, bg=self._bg_medium)
            row_f.pack(fill="x", pady=3)
            tk.Label(row_f, text=f"☁ {img['url'].split('/')[-1][:40]}", fg="#8cf",
                     bg=self._bg_medium, font=("Helvetica", 10), anchor="w").pack(side="left", padx=8)
            tk.Label(row_f, text="(ya en Shopify)", fg="#666", bg=self._bg_medium,
                     font=("Helvetica", 9, "italic")).pack(side="left", padx=5)
            ctk.CTkButton(row_f, text="✕", width=30, height=28, fg_color="#8b1a1a",
                          command=lambda i=idx: self._del_web_image(i)).pack(side="right", padx=8)

    def _del_image(self, idx):
        self._imagenes.pop(idx)
        self._render_images()

    def _del_web_image(self, idx):
        self._imagenes_web.pop(idx)
        self._render_images()

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

        def work():
            full = self.product_service.cargar_producto(prod["id"])
            self.frame.after(0, lambda: self._fill_edit(full))
        threading.Thread(target=work, daemon=True).start()

    def _fill_edit(self, prod):
        if not prod:
            self._status("Error cargando el producto")
            return
        self._edit_product = prod
        self._entries["titulo"].delete(0, "end")
        self._entries["titulo"].insert(0, prod.get("title", ""))
        self._entries["tags"].delete(0, "end")
        self._entries["tags"].insert(0, ", ".join(prod.get("tags") or []))
        self._seo_box.delete("1.0", "end")
        self._seo_box.insert("1.0", (prod.get("seo") or {}).get("description") or "")
        self._status_menu.set(prod.get("status", "DRAFT"))
        if prod.get("productType"):
            self._tipo_combo.set(prod["productType"])
            self._on_tipo_change()
        for box in self._body_boxes.values():
            box.delete("1.0", "end")
        if self._body_boxes:
            next(iter(self._body_boxes.values())).insert(
                "1.0", prod.get("descriptionHtml") or "")
        self._imagenes_web = [{"url": m["image"]["url"], "alt": m.get("alt") or ""}
                              for m in prod.get("media", {}).get("nodes", [])
                              if m.get("image")]
        self._render_images()
        self._status(f"Cargado: {prod.get('handle')}")

    def _abrir_skus(self):
        """Abre la subvista de edición de SKUs para el producto cargado."""
        if not self._edit_product:
            show_error(self.frame, "Carga primero un producto")
            return
        tipo_nombre = self._tipo_combo.get().strip()
        tipo_id = self._tipo_combo.get_id()
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
            on_volver=lambda: self.frame.pack(fill="both", expand=True))
        sku_view.frame.pack(fill="both", expand=True)

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
        template_suffix = ""
        if tipo and tipo.get("template_suffix"):
            template_suffix = tipo["template_suffix"].strip()
        if not template_suffix:
            template_suffix = cfg.get("template_suffix") or ""

        base = {
            "tags": [t.strip() for t in self._entries["tags"].get().split(",") if t.strip()],
            "seo_desc": seo_desc,
            "seo_title": titulo[:70],
            "status": status,
            "codigo_categoria": self._entries["codigo_categoria"].get().strip().upper(),
            "product_type": product_type,
            "taxonomy_gid": taxonomy_gid,
            "template_suffix": template_suffix,
            "recargo_tallas": cfg.get("recargo_tallas") or 0,
            "recargo_grupo_id": cfg.get("recargo_grupo_id"),
        }

        if self._modo == "EDITAR":
            if not self._edit_product:
                show_error(self.frame, "Carga primero un producto")
                return
            self._subir_edicion(base)
        else:
            self._subir_nuevo(base)

        self._btn_upload.configure(state="disabled")

    def _subir_nuevo(self, base):
        titulo = self._entries["titulo"].get().strip()
        iniciales = self.product_service.iniciales_diseno(titulo)
        cfg = self.config_service.get_config()
        tipo_nombre = self._tipo_combo.get().strip()
        tipo_code = _slugify(tipo_nombre).upper()[:4] or "PROD"
        es_camiseta = tipo_nombre.lower() == "camiseta"

        if not self._variantes_disponibles:
            self._btn_upload.configure(state="normal")
            show_error(self.frame, "El tipo seleccionado no tiene variantes activas para web")
            return

        trabajos = []
        for v_info in self._variantes_disponibles:
            variante_id = v_info["id"]
            variante = v_info["nombre"]
            variantes = self.product_service.get_variantes_stock(variante_id)
            if not variantes:
                continue

            # Asegurar cantidad entera en cada variante real
            for v in variantes:
                v["cantidad"] = int(v.get("cantidad") or 0)

            # Color "Sorpresa": solo en camisetas, una opción extra por talla
            if es_camiseta:
                tallas = sorted({v["talla"] for v in variantes})
                sorpresa_qty = int(cfg.get("stock_sorpresa") or 50) if cfg.get("stock_sorpresa") else 50
                sorpresa_precio = cfg.get("precio_sorpresa")
                if sorpresa_precio:
                    sorpresa_precio = float(sorpresa_precio.replace(',', '.').replace('€', '').strip())
                else:
                    sorpresa_precio = None

                for talla in tallas:
                    v_sorpresa = {
                        "sku": f"{tipo_code}-SORPRESA-{_slugify(variante).upper()}-{talla}",
                        "color": "Sorpresa",
                        "talla": talla,
                        "cantidad": sorpresa_qty,
                    }
                    if sorpresa_precio is not None:
                        v_sorpresa["precio"] = sorpresa_precio
                    variantes.append(v_sorpresa)

            body_box = self._body_boxes.get(variante)
            datos = dict(base)
            tipo_id = self._tipo_combo.get_id()
            datos.update({
                "title": f"{titulo} | {variante}",
                "handle": f"{_slugify(titulo)}-{_slugify(variante)}",
                "description_html": body_box.get("1.0", "end-1c") if body_box else "",
                "seo_title": self.content_service.seo_title_for(titulo, variante, tipo_id=tipo_id),
                "tags": base["tags"] + [variante],
                "variantes": variantes,
                "iniciales": iniciales,
                "imagenes": [dict(i) for i in self._imagenes],
                "vendor": cfg.get("marca") or "Kool Things",
                "diseno_codigo": _slugify(titulo),
                "variante_nombre": variante,
            })
            trabajos.append(datos)

        if not trabajos:
            self._btn_upload.configure(state="normal")
            show_error(self.frame, "No hay stock para las variantes seleccionadas")
            return

        self._status(f"Subiendo {len(trabajos)} productos...")

        def work():
            mensajes = []
            for datos in trabajos:
                r = self.product_service.product_set(datos)
                mensajes.append(f"{datos['variante_nombre']}: {'OK' if r['success'] else r['message']}")
            self.frame.after(0, lambda: self._fin_upload(mensajes))
        threading.Thread(target=work, daemon=True).start()

    def _subir_edicion(self, base):
        prod = self._edit_product
        variantes_input = []
        for v in prod.get("variants", {}).get("nodes", []):
            opts = [{"optionName": o["name"], "name": o["value"]}
                    for o in v.get("selectedOptions", [])]
            variantes_input.append({"sku": v.get("sku") or "", "price": str(v.get("price") or "0"),
                                    "optionValues": opts})
        product_options = [{"name": o["name"], "values": [{"name": x} for x in o.get("values", [])]}
                           for o in prod.get("options", [])]

        datos = dict(base)
        datos.update({
            "title": self._entries["titulo"].get().strip(),
            "handle": prod.get("handle") or _slugify(self._entries["titulo"].get().strip()),
            "description_html": (next(iter(self._body_boxes.values())).get("1.0", "end-1c")
                                 if self._body_boxes else prod.get("descriptionHtml") or ""),
            "product_id": prod["id"],
            "variantes_input": variantes_input,
            "product_options": product_options,
            "imagenes": [dict(i) for i in self._imagenes],
            "imagenes_url": [dict(i) for i in self._imagenes_web],
        })

        self._status("Actualizando producto...")

        def work():
            r = self.product_service.product_set(datos)
            msg = "Actualizado OK" if r["success"] else f"Error: {r['message']}"
            self.frame.after(0, lambda: self._fin_upload([msg]))
        threading.Thread(target=work, daemon=True).start()

    def _fin_upload(self, mensajes):
        self._btn_upload.configure(state="normal")
        ok = all("OK" in m for m in mensajes)
        self._status("\n".join(mensajes))
        if ok:
            show_success(self.frame, "Subida completada:\n" + "\n".join(mensajes))
        else:
            show_error(self.frame, "Revisa los resultados:\n" + "\n".join(mensajes))

    def _status(self, texto):
        try:
            self._status_lbl.configure(text=texto)
        except Exception:
            pass
