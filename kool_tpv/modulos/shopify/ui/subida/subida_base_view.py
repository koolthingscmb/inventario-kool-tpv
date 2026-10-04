"""Base común de las pantallas de SUBIDA a Shopify (nuevo y editar).

Contiene el estado, los servicios y la lógica compartida: cambio de tipo, cajas BODY, tags,
contenido IA, metacampos, preparación de datos comunes y fin de subida.
Las subclases construyen su interfaz (_build) y aportan _subir_nuevo / _subir_edicion.
"""
import logging
import threading
import tkinter as tk
from typing import Dict, Any, Optional, List

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.notificaciones import show_success, show_error
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from kool_tpv.modulos.shopify.services.shopify_product_service import ShopifyProductService
from kool_tpv.modulos.shopify.services.producto_content_service import ProductoContentService
from kool_tpv.modulos.shopify.services.shopify_config_service import ShopifyConfigService
from kool_tpv.modulos.shopify.services.shopify_upload_builder import ShopifyUploadBuilder
from kool_tpv.modulos.shopify.services.shopify_nuevo_builder import ShopifyNuevoBuilder
from kool_tpv.modulos.shopify.services.shopify_edicion_builder import ShopifyEdicionBuilder
from kool_tpv.modulos.shopify.ui.shopify_metafields_ui import ShopifyMetafieldsUI

logger = logging.getLogger(__name__)


class SubidaBaseView:
    """Lógica común de las pantallas de subida."""

    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.product_service = ShopifyProductService(db)
        self.content_service = ProductoContentService(db)
        self.config_service = ShopifyConfigService(db)
        self.upload_builder = ShopifyUploadBuilder(db)
        self.nuevo_builder = ShopifyNuevoBuilder(db, self.product_service, self.content_service, self.upload_builder)
        self.edicion_builder = ShopifyEdicionBuilder(db, self.upload_builder)

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

    def _section(self, text):
        f = tk.Frame(self._content, bg=self._bg)
        f.pack(fill="x", pady=(14, 8))
        tk.Label(f, text=text, font=("Helvetica", 13, "bold"), fg=self._primary,
                 bg=self._bg, anchor="w").pack(side="left")
        tk.Frame(f, bg=self._primary, height=2).pack(side="left", fill="x", expand=True,
                                                    padx=(12, 0), pady=(2, 0))

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

        self._body_boxes = self._editor_ia.reconstruir_cajas(
            self._body_boxes, [v["nombre"] for v in variantes_a_mostrar])

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

    def _build(self):
        raise NotImplementedError

    def _subir_nuevo(self, base):
        raise NotImplementedError

    def _subir_edicion(self, base):
        raise NotImplementedError
