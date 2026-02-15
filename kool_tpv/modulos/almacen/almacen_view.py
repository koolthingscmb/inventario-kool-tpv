"""Almacen module orchestrator (BaseModuleView pattern).

Provee una vista base que integra en la navegación principal del TPV.
La implementación es mínima: registra menú, provee `open` y `close`, y expone
el servicio maestro para las vistas UI.
"""
from typing import Optional
import logging
import json
from pathlib import Path

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
            'show_compra': self.show_compra,
            'show_tipos': self.show_tipos,
            'show_categorias': self.show_categorias,
            'show_proveedores': self.show_proveedores,
        }

        # Iterate over configured buttons and rebind matching buttons in the UI
        try:
            for b in buttons:
                lbl = (b.get('label') or b.get('text') or '').upper()
                action = b.get('action')
                # find child button in menu_frame with same text
                for child in list(self._menu_frame.winfo_children()):
                    try:
                        txt = child.cget('text') if hasattr(child, 'cget') else None
                        if txt and txt.upper() == lbl:
                            # bind the action if exists
                            if action in action_map:
                                try:
                                    child.configure(command=action_map[action])
                                except Exception:
                                    pass
                            break
                    except Exception:
                        continue
        except Exception:
            logging.exception('Error enlazando botones en AlmacenView')

    # Simple handlers that currently log actions — to be implemented
    def show_crear(self):
        """Instancia y muestra la UI de creación en la zona central."""
        try:
            # update breadcrumb to indicate sub-section
            try:
                self.actualizar_ruta('ALMACEN / CREAR_PRODUCTO')
            except Exception:
                pass
            from .ui.crear_producto_ui import CrearProductoUI

            # Lazy load the UI so we keep state while the module is open
            if not hasattr(self, 'crear_ui') or self.crear_ui is None:
                # pass the module DB so the UI can load options immediately
                self.crear_ui = CrearProductoUI(self.central_area, db=self.db)

            # Prefer using the widget returned by get_widget()
            try:
                widget = self.crear_ui.get_widget() if hasattr(self.crear_ui, 'get_widget') else self.crear_ui
                self.set_central_content(widget)
            except Exception:
                # Fallback: try to pack the UI instance directly
                try:
                    self.crear_ui.pack(fill='both', expand=True)
                except Exception:
                    logging.exception('No fue posible mostrar CrearProductoUI en show_crear')

            logging.info('Abriendo crear...')
        except Exception:
            logging.exception('Error abriendo crear en AlmacenView')

    def show_busqueda(self):
        try:
            self.actualizar_ruta('ALMACEN / BUSQUEDA')
        except Exception:
            pass
        logging.info('Abriendo búsqueda...')

    def show_compra(self):
        try:
            self.actualizar_ruta('ALMACEN / COMPRA')
        except Exception:
            pass
        logging.info('Abriendo compra...')

    def show_tipos(self):
        try:
            self.actualizar_ruta('ALMACEN / TIPOS')
        except Exception:
            pass
        logging.info('Abriendo tipos...')

    def show_categorias(self):
        try:
            self.actualizar_ruta('ALMACEN / CATEGORIAS')
        except Exception:
            pass
        logging.info('Abriendo categorías...')

    def show_proveedores(self):
        try:
            self.actualizar_ruta('ALMACEN / PROVEEDORES')
        except Exception:
            pass
        logging.info('Abriendo proveedores...')

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
