"""Subvista SUBIDA: crea y edita productos en Shopify desde el TPV.

Flujo: rellenar datos del diseño -> GENERAR CONTENIDO (IA) -> revisar/editar ->
SUBIR A SHOPIFY (productSet, imágenes, precios por variante).
"""
import logging
import threading
import tkinter as tk

import customtkinter as ctk

from kool_tpv.utils.widgets.notificaciones import show_error
from .shopify_actualiza_sku import ShopifyActualizaSku
from ..services.shopify_nuevo_builder import ErrorPreparacion
from .subida.componentes.selector_imagenes import SelectorImagenes
from .subida.componentes.formulario_diseno import FormularioDiseno
from .subida.componentes.editor_contenido_ia import EditorContenidoIA
from .subida.subida_base_view import SubidaBaseView

logger = logging.getLogger(__name__)


class ShopifyUploadView(SubidaBaseView):
    """Vista de subida/edición de camisetas a Shopify."""

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
        self._formulario = FormularioDiseno(
            scroll, self.db, self._tipo_service, self._entries,
            bg=self._bg, primary=self._primary, secondary=self._secondary,
            on_tipo_change=self._on_tipo_change,
            on_variante_change=self._rebuild_body_boxes,
            on_generar_tags=self._generar_tags)
        self._btn_tags = self._formulario.btn_tags
        self._ben_combo = self._formulario.ben_combo
        self._tono_combo = self._formulario.tono_combo
        self._status_menu = self._formulario.status_menu
        self._tipos = self._formulario.tipos
        self._tipo_combo = self._formulario.tipo_combo
        self._variante_combo = self._formulario.variante_combo
        self._variantes_lbl = self._formulario.variantes_lbl

        # --- Imágenes ---
        self._section("IMÁGENES")
        self._selector_imagenes = SelectorImagenes(scroll, self._bg, self._bg_medium, self._secondary)
        self._selector_imagenes.frame.pack(fill="x")

        # --- Contenido IA ---
        self._section("CONTENIDO (IA)")
        
        self._editor_ia = EditorContenidoIA(
            scroll, self._bg, self._bg_medium, self._primary, self._secondary,
            on_generar=self._generar_contenido, on_metafields=self._abrir_metafields)
        self._seo_title_entry = self._editor_ia.seo_title_entry
        self._btn_meta = self._editor_ia.btn_meta
        self._meta_nuevo_status_lbl = self._editor_ia.meta_status_lbl
        self._seo_box = self._editor_ia.seo_box
        self._bodies_frame = self._editor_ia.bodies_frame

        self._set_modo("NUEVO")

        # Tipo por defecto: Camiseta si existe
        camiseta = next((t for t in self._tipos if t["nombre"] == "Camiseta"), None)
        if camiseta:
            self._tipo_combo.set_by_id(camiseta["id"])
            self._on_tipo_change()


    def _modo_btn(self, parent, text, modo):
        b = ctk.CTkButton(parent, text=text, width=180, height=36,
                          command=lambda: self._set_modo(modo))
        b.pack(side="left", padx=(0, 8))
        return b


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


    # ------------------------------------------------------------------
    # Subir / actualizar
    # ------------------------------------------------------------------

    def _subir_nuevo(self, base):
        try:
            trabajos = self.nuevo_builder.construir_trabajos(
                base=base,
                titulo=self._entries["titulo"].get().strip(),
                beneficio=self._entries["beneficio"].get().strip(),
                tipo_nombre=self._tipo_combo.get().strip(),
                tipo_id=self._tipo_combo.get_id(),
                variantes_disponibles=self._variantes_disponibles,
                cuerpos={nombre: box.get("1.0", "end-1c") for nombre, box in self._body_boxes.items()},
                imagenes=self._selector_imagenes.obtener_locales(),
            )
        except ErrorPreparacion as e:
            show_error(self.frame, str(e))
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
        datos = self.edicion_builder.construir_datos(
            base=base,
            producto=self._edit_product,
            titulo_base=self._entries["titulo"].get().strip(),
            variante_combo=self._variante_combo.get().strip(),
            tipo_nombre=self._tipo_combo.get().strip(),
            skus_preparados=self._skus_preparados,
            primer_cuerpo=(next(iter(self._body_boxes.values())).get("1.0", "end-1c") if self._body_boxes else None),
            imagenes_locales=self._selector_imagenes.obtener_locales(),
            imagenes_web=self._selector_imagenes.obtener_web(),
        )

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


