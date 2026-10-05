"""Pantalla SUBIDA para EDITAR un producto existente de Shopify."""
import logging
import threading
import tkinter as tk

import customtkinter as ctk

from kool_tpv.utils.widgets.notificaciones import show_error
from kool_tpv.modulos.shopify.ui.shopify_actualiza_sku import ShopifyActualizaSku
from .subida_base_view import SubidaBaseView

logger = logging.getLogger(__name__)


class SubidaEditarView(SubidaBaseView):
    """Busca un producto en Shopify, lo carga en el formulario y lo actualiza."""

    _modo = "EDITAR"
    TEXTO_BOTON = "ACTUALIZAR PRODUCTO"
    MOSTRAR_VARIANTES_A_SUBIR = False

    def _construir_panel_editar(self, scroll):
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

    def _finalizar_build(self):
        self._variante_combo.entry.configure(state="normal")
        self._btn_upload.configure(text=self.TEXTO_BOTON)
        self._edit_frame.pack(fill="x", padx=10, pady=5, after=self._content.winfo_children()[0])
        self._seleccionar_tipo_por_defecto()

    def _opciones_combo_variante(self, tipo_id):
        """Al editar se puede elegir cualquier variante activa del tipo, esté marcada o no para web."""
        rows = self.db.fetch_all(
            "SELECT id, nombre FROM tipos_variantes WHERE tipo_id = ? AND activo = 1 ORDER BY orden, nombre",
            (tipo_id,))
        return [(r[0], r[1]) for r in (rows or [])]

    def _filtrar_variantes_cajas(self, variantes):
        sel = self._variante_combo.get().strip()
        if not sel:
            return variantes
        # Mostrar solo la variante seleccionada
        filtradas = [v for v in self._variantes_disponibles if v["nombre"] == sel]
        if not filtradas:
            # Fallback por si la variante no está en la lista de activas
            filtradas = [{"id": None, "nombre": sel}]
        return filtradas

    def _variante_seleccionada(self) -> str:
        return self._variante_combo.get().strip()

    def _despachar_subida(self, base):
        if not self._edit_product:
            show_error(self.frame, "Carga primero un producto")
            return
        self._subir_edicion(base)

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
                if not r["success"]:
                    msg = f"Error: {r['message']}"
                elif r.get("stock_ok") is False:
                    msg = "Actualizado, pero el STOCK no se aplicó (revisa la terminal)"
                else:
                    msg = "Actualizado OK"
            except Exception as e:
                logger.exception("Error inesperado actualizando el producto")
                msg = f"Error inesperado ({type(e).__name__}), revisa la terminal"
            self.frame.after(0, lambda: self._fin_upload([msg]))
        threading.Thread(target=work, daemon=True).start()
