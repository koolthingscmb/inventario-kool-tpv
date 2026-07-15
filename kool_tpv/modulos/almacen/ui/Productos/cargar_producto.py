"""UI helper para cargar (prefill) datos de un producto.

Este fichero contiene una implementación mínima que delega en
`ProductoService.get_producto_completo` y devuelve el dict de datos.
La lógica de rellenado de widgets se implementará después.
"""
from typing import Optional
import logging

import customtkinter as ctk

from kool_tpv.base_datos.producto_service import ProductoService


class CargarProductoUI:
    def __init__(self, parent, db=None):
        self.parent = parent
        self.db = db
        self.container = ctk.CTkFrame(self.parent)

    def get_widget(self):
        return self.container

    def load_product(self, producto_id: int) -> Optional[dict]:
        """Devuelve el dict con los datos del producto o None.

        No realiza ningún cambio en la UI; solo devuelve los datos.
        """
        try:
            service = ProductoService(self.db)
            return service.get_producto_completo(producto_id)
        except Exception:
            logging.exception('Error cargando producto %s', producto_id)
            return None

    def apply_to_ui(self, producto_id: int, ui_instance) -> bool:
        """Carga los datos del producto y los aplica sobre los widgets de `ui_instance`.

        Retorna True si se aplicaron datos, False en caso de error o producto no existente.
        El método intenta ser defensivo: verificar la existencia de cada widget antes de asignar
        y añadir opciones en `SearchableCombo` si el nombre no existe aún.
        """
        try:
            data = self.load_product(producto_id)
            if not data:
                return False

            def _set_entry(w, value):
                if w is None:
                    return
                try:
                    if hasattr(w, 'set'):
                        # adapters / widgets with set()
                        w.set('' if value is None else str(value))
                        return
                except Exception:
                    pass
                try:
                    # typical Entry-like widgets
                    if hasattr(w, 'delete') and hasattr(w, 'insert'):
                        w.delete(0, 'end')
                        w.insert(0, '' if value is None else str(value))
                        return
                except Exception:
                    pass
                try:
                    # attempt generic configure
                    w.configure(text='' if value is None else str(value))
                except Exception:
                    pass

            def _set_textbox(w, value):
                if w is None:
                    return
                try:
                    # CTkTextbox or tk.Text
                    if hasattr(w, 'delete') and hasattr(w, 'insert'):
                        try:
                            w.delete('1.0', 'end')
                        except Exception:
                            try:
                                w.delete(0, 'end')
                            except Exception:
                                pass
                        try:
                            w.insert('1.0', '' if value is None else str(value))
                        except Exception:
                            try:
                                w.insert(0, '' if value is None else str(value))
                            except Exception:
                                pass
                        return
                except Exception:
                    pass
                try:
                    _set_entry(w, value)
                except Exception:
                    pass

            # Simple mappings
            try:
                _set_entry(getattr(ui_instance, 'e_id', None), data.get('id'))
                # Ensure bound StringVar for ID (if present) is updated so traces fire
                try:
                    if getattr(ui_instance, 'e_id_var', None) is not None and data.get('id') is not None:
                        try:
                            ui_instance.e_id_var.set(str(data.get('id')))
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass

            _set_entry(getattr(ui_instance, 'e_nombre', None), data.get('nombre'))
            _set_entry(getattr(ui_instance, 'e_nombre_btn', None), data.get('nombre_boton'))
            _set_entry(getattr(ui_instance, 'e_sku', None), data.get('sku'))

            # Combos: set by display name; if name not present, try to append option so mapping resolves
            try:
                # categoria
                cat_name = data.get('categoria_nombre') or ''
                cb = getattr(ui_instance, 'cb_categoria', None)
                if cb is not None:
                    try:
                        # if the name is missing in mapping, append it with its id
                        if getattr(cb, 'get_id', lambda: None)() is None:
                            pass
                    except Exception:
                        pass
                    try:
                        # ensure option exists: access internal mapping if available
                        vals = getattr(cb, 'values', None) or []
                        mapping = getattr(cb, '_mapping', {}) or {}
                        if cat_name and cat_name not in vals:
                            try:
                                opts = [(mapping.get(n), n) for n in vals]
                                # include current product option
                                opts.append((data.get('categoria_id'), cat_name))
                                cb.set_options(opts)
                            except Exception:
                                pass
                        cb.set(cat_name)
                    except Exception:
                        try:
                            cb.set(cat_name)
                        except Exception:
                            pass
            except Exception:
                logging.exception('Error aplicando categoria')

            try:
                tipo_name = data.get('tipo_nombre') or ''
                cb = getattr(ui_instance, 'cb_tipo', None)
                if cb is not None:
                    try:
                        vals = getattr(cb, 'values', None) or []
                        mapping = getattr(cb, '_mapping', {}) or {}
                        if tipo_name and tipo_name not in vals:
                            opts = [(mapping.get(n), n) for n in vals]
                            opts.append((data.get('tipo_id'), tipo_name))
                            cb.set_options(opts)
                    except Exception:
                        pass
                    try:
                        cb.set(tipo_name)
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error aplicando tipo')

            try:
                prov_name = data.get('proveedor_nombre') or ''
                cb = getattr(ui_instance, 'cb_proveedor', None)
                if cb is not None:
                    try:
                        vals = getattr(cb, 'values', None) or []
                        mapping = getattr(cb, '_mapping', {}) or {}
                        if prov_name and prov_name not in vals:
                            opts = [(mapping.get(n), n) for n in vals]
                            opts.append((data.get('proveedor_id'), prov_name))
                            cb.set_options(opts)
                    except Exception:
                        pass
                    try:
                        cb.set(prov_name)
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error aplicando proveedor')

            # IVA combo: display uses str of number
            try:
                iva_val = data.get('tipo_iva')
                cb = getattr(ui_instance, 'cb_iva', None)
                if cb is not None:
                    iva_name = str(iva_val) if iva_val is not None else ''
                    try:
                        vals = getattr(cb, 'values', None) or []
                        mapping = getattr(cb, '_mapping', {}) or {}
                        if iva_name and iva_name not in vals:
                            opts = [(mapping.get(n), n) for n in vals]
                            opts.append((iva_val, iva_name))
                            cb.set_options(opts)
                    except Exception:
                        pass
                    try:
                        cb.set(iva_name)
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error aplicando IVA')

            # Prices and numeric fields
            _set_entry(getattr(ui_instance, 'e_pvp', None), data.get('pvp'))
            _set_entry(getattr(ui_instance, 'e_coste', None), data.get('coste'))

            # checkboxes
            try:
                pv = bool(int(data.get('pvp_variable') or 0))
                chk = getattr(ui_instance, 'chk_pvp_var', None)
                if chk is not None:
                    try:
                        if pv:
                            chk.select()
                        else:
                            chk.deselect()
                    except Exception:
                        try:
                            # fallback: try to set a variable if present
                            var = getattr(ui_instance, 'chk_pvp_var_var', None)
                            if var is not None and hasattr(var, 'set'):
                                var.set(pv)
                        except Exception:
                            pass
            except Exception:
                logging.exception('Error aplicando pvp_variable')

            try:
                fabricado = bool(int(data.get('fabricado_por_nosotros') or 0))
                chk = getattr(ui_instance, 'chk_fabricado', None)
                if chk is not None:
                    try:
                        if fabricado:
                            chk.select()
                        else:
                            chk.deselect()
                    except Exception:
                        try:
                            # fallback: try to set a variable if present
                            var = getattr(ui_instance, 'chk_fabricado_var', None)
                            if var is not None and hasattr(var, 'set'):
                                var.set(fabricado)
                        except Exception:
                            pass
            except Exception:
                logging.exception('Error aplicando fabricado_por_nosotros')

            try:
                activo = bool(int(data.get('activo') or 0))
                var = getattr(ui_instance, 'chk_activo_var', None)
                if var is not None and hasattr(var, 'set'):
                    try:
                        var.set(bool(activo))
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error aplicando activo')

            _set_entry(getattr(ui_instance, 'e_stock_actual', None), data.get('stock_actual'))
            _set_entry(getattr(ui_instance, 'e_stock_min', None), data.get('stock_minimo') or data.get('stock_min'))
            # Prefer updating a bound StringVar for e_ventas if available (readonly UI)
            try:
                ventas_val = data.get('ventas_totales') or 0
                if hasattr(ui_instance, 'e_ventas_var') and getattr(ui_instance, 'e_ventas_var') is not None:
                    try:
                        ui_instance.e_ventas_var.set(str(ventas_val))
                    except Exception:
                        _set_entry(getattr(ui_instance, 'e_ventas', None), ventas_val)
                else:
                    _set_entry(getattr(ui_instance, 'e_ventas', None), ventas_val)
            except Exception:
                logging.exception('Error aplicando ventas')

            # Shopify / text fields
            _set_textbox(getattr(ui_instance, 'txt_description', None), data.get('descripcion_shopify') or '')
            _set_textbox(getattr(ui_instance, 'e_seo_desc', None), data.get('seo_description') or '')
            _set_entry(getattr(ui_instance, 'e_seo_title', None), data.get('titulo') or '')
            _set_entry(getattr(ui_instance, 'e_seo_short', None), data.get('seo_title') or '')
            _set_entry(getattr(ui_instance, 'e_tipo_shop', None), data.get('tipo_shop') or '')
            _set_entry(getattr(ui_instance, 'e_tags', None), data.get('etiquetas') or '')
            _set_entry(getattr(ui_instance, 'e_shop_link', None), data.get('shop_link') or '')

            # taxonomy read-only entry
            try:
                ent = getattr(ui_instance, 'ent_taxonomy', None)
                if ent is not None:
                    try:
                        try:
                            ent.configure(state='normal')
                        except Exception:
                            pass
                        try:
                            if hasattr(ent, 'delete') and hasattr(ent, 'insert'):
                                ent.delete(0, 'end')
                                ent.insert(0, data.get('shopify_taxonomy') or '')
                            else:
                                ent.configure(text=(data.get('shopify_taxonomy') or ''))
                        except Exception:
                            try:
                                ent.configure(text=(data.get('shopify_taxonomy') or ''))
                            except Exception:
                                pass
                        try:
                            ent.configure(state='readonly')
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error aplicando taxonomy')

            # ean CSV -> e_codigos
            try:
                ean = data.get('ean') or ''
                _set_entry(getattr(ui_instance, 'e_codigos', None), ean)
            except Exception:
                logging.exception('Error aplicando EANs')

            return True
        except Exception:
            logging.exception('Error aplicando datos de producto a UI')
            return False
