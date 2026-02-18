"""Almacen module orchestrator (BaseModuleView pattern).

Provee una vista base que integra en la navegación principal del TPV.
La implementación es mínima: registra menú, provee `open` y `close`, y expone
el servicio maestro para las vistas UI.
"""
from typing import Optional
import logging
import json
from pathlib import Path
import unicodedata

import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.almacen.services.maestro_service import MaestroService
from kool_tpv.utils.templates.base_module_view import BaseModuleView


class AlmacenView(BaseModuleView):
    """AlmacenView usando la plantilla `BaseModuleView`.

    Reusa la estética del sidebar y enlaza las acciones definidas en
    `buttons_menu.json` a métodos `show_*` simples que por ahora solo loguean.
    """

    def __init__(self, parent, db):
        # Initialize base template with module key 'almacen'
        super().__init__(parent, config_section='almacen')
        # update breadcrumb to module on entry
        try:
            self.actualizar_ruta('ALMACEN')
        except Exception:
            pass
        self.parent = parent
        self.db = db
        self.service = MaestroService(db)

        # Rebind menu buttons to local handlers based on buttons_menu.json
        try:
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)
            menu = cfg.get('almacen', {}) if isinstance(cfg, dict) else {}
            buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
        except Exception:
            logging.exception('Error leyendo buttons_menu.json en AlmacenView')
            buttons = []

        # Map action names to methods
        action_map = {
            'show_crear': self.show_crear,
            'show_busqueda': self.show_busqueda,
            'show_albaranes': self.show_albaranes,
            'show_tipos': self.show_tipos,
            'show_categorias': self.show_categorias,
            'show_proveedores': self.show_proveedores,
        }

        # Iterate over configured buttons and rebind matching buttons in the UI
        try:
            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            for b in buttons:
                lbl = (b.get('label') or b.get('text') or '')
                action = b.get('action')
                norm_lbl = _norm(lbl)
                # find child button in menu_frame with same text
                for child in list(self._menu_frame.winfo_children()):
                    try:
                        txt = child.cget('text') if hasattr(child, 'cget') else None
                        if txt and _norm(txt) == norm_lbl:
                            # bind the action if exists
                            if action in action_map:
                                # wrap to capture exceptions when executing the bound action
                                def _wrap(func):
                                    def _wrapped(*a, **k):
                                        try:
                                            return func(*a, **k)
                                        except Exception:
                                            logging.exception("Error al ejecutar acción %r:", getattr(func, '__name__', str(func)))
                                            raise
                                    return _wrapped
                                try:
                                    child.configure(command=_wrap(action_map[action]))
                                except Exception:
                                    logging.exception("Failed configuring command for %r", lbl)
                            else:
                                logging.warning("  Action %r not found in action_map", action)
                            break
                    except Exception:
                        logging.exception("Error inspeccionando child en AlmacenView")
        except Exception:
            logging.exception('Error enlazando botones en AlmacenView')

    # Simple handlers that currently log actions — to be implemented
    def show_crear(self, producto_id: int = None):
        """Instancia y muestra la UI de creación en la zona central."""
        try:
            # update breadcrumb to indicate sub-section
            try:
                self.actualizar_ruta('ALMACEN / CREAR_PRODUCTO')
            except Exception:
                pass
            from .ui.Productos.crear_producto_ui import CrearProductoUI
            # Always instantiate a fresh UI to avoid using destroyed widgets
            try:
                crear_ui = CrearProductoUI(self.central_area, db=self.db, producto_id=producto_id)
                # Prefer passing the actual widget to set_central_content to avoid
                # ambiguous packing behavior if the instance exposes both
                # get_widget() and pack(). This reduces race conditions with
                # previously destroyed widgets.
                try:
                    widget = crear_ui.get_widget() if hasattr(crear_ui, 'get_widget') else crear_ui
                    self.set_central_content(widget)
                except Exception:
                    # fallback: try passing the instance itself
                    logging.exception('Error obteniendo widget desde CrearProductoUI, intentando pasar la instancia')
                    self.set_central_content(crear_ui)

                # If a producto_id was provided, attempt to prefill the UI using the loader
                if producto_id is not None:
                    try:
                        from .ui.Productos.cargar_producto import CargarProductoUI
                        loader = CargarProductoUI(self.central_area, db=self.db)
                        applied = loader.apply_to_ui(producto_id, crear_ui)
                        if not applied:
                            logging.warning('CrearProductoUI: no se aplicaron datos para producto_id=%s', producto_id)
                    except Exception:
                        logging.exception('Error aplicando datos de producto a CrearProductoUI')
            except Exception:
                logging.exception('No fue posible instanciar/mostrar CrearProductoUI en show_crear')

            logging.info('Abriendo crear...')
        except Exception:
            logging.exception('Error abriendo crear en AlmacenView')

    def show_busqueda(self):
        try:
            try:
                self.actualizar_ruta('ALMACEN / BUSQUEDA')
            except Exception:
                pass
            from .ui.busqueda_ui import BusquedaUI
            try:
                busq = BusquedaUI(self.central_area, db=self.db, owner=self)
                self.set_central_content(busq)
            except Exception:
                logging.exception('No fue posible instanciar BusquedaUI en show_busqueda')
            logging.info('Abriendo búsqueda...')
        except Exception:
            logging.exception('Error abriendo busqueda en AlmacenView')

    def show_albaranes(self):
        try:
            try:
                self.actualizar_ruta('ALMACEN / ALBARANES')
            except Exception:
                pass
            from .ui.albaranes_ui import AlbaranesUI

            try:
                albaranes_ui = AlbaranesUI(self.central_area, db=self.db)
                self.set_central_content(albaranes_ui)
                logging.info('Abriendo albaranes...')
            except Exception:
                logging.exception('Error instanciando AlbaranesUI en show_albaranes')
        except Exception:
            logging.exception('Error abriendo albaranes en AlmacenView')

    def show_tipos(self):
        try:
            try:
                self.actualizar_ruta('ALMACEN / TIPOS')
            except Exception:
                pass
            from .ui.tipos_ui import TiposUI

            # Always create a fresh UI instance to avoid reusing destroyed widgets
            try:
                tipos_ui = TiposUI(self.central_area, db=self.db)
                self.set_central_content(tipos_ui)
                logging.info('Abriendo tipos...')
            except Exception:
                logging.exception('Error instanciando TiposUI en show_tipos')
        except Exception:
            logging.exception('Error abriendo tipos en AlmacenView')

    def show_categorias(self):
        try:
            try:
                self.actualizar_ruta('ALMACEN / CATEGORIAS')
            except Exception:
                pass
            from .ui.categorias_ui import CategoriasUI

            try:
                categorias_ui = CategoriasUI(self.central_area, db=self.db)
                self.set_central_content(categorias_ui)
                logging.info('Abriendo categorías...')
            except Exception:
                logging.exception('Error instanciando CategoriasUI en show_categorias')
        except Exception:
            logging.exception('Error abriendo categorias en AlmacenView')

    def show_proveedores(self):
        try:
            try:
                self.actualizar_ruta('ALMACEN / PROVEEDORES')
            except Exception:
                pass
            from .ui.proveedores_ui import ProveedoresUI

            try:
                proveedores_ui = ProveedoresUI(self.central_area, db=self.db)
                self.set_central_content(proveedores_ui)
                logging.info('Abriendo proveedores...')
            except Exception:
                logging.exception('Error instanciando ProveedoresUI en show_proveedores')
        except Exception:
            logging.exception('Error abriendo proveedores en AlmacenView')

    # attach_to_nav kept for compatibility with main navigation
    def attach_to_nav(self, nav_frame, button_config: dict):
        try:
            from kool_tpv.utils.global_buttons import create_nav_button
            btn = create_nav_button(nav_frame, text=button_config.get('text', 'ALMACÉN'), fg_color=button_config.get('color', '#32CD32'), hover_color=button_config.get('hover_color', '#00A4DF'), command=self.open)
            btn.pack(side='left', padx=6)
            return btn
        except Exception:
            logging.exception('Error attach_to_nav AlmacenView')
            return None
