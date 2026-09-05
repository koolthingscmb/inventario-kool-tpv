"""Shopify module orchestrator (BaseModuleView pattern).

Provee una vista base que integra en la navegación principal del TPV.
"""
from typing import Optional
import logging
import json
from kool_tpv.paths import CONFIG_DIR

import unicodedata

import customtkinter as ctk
import tkinter as tk

from kool_tpv.utils.templates.base_module_view import BaseModuleView


class ShopifyView(BaseModuleView):
    """ShopifyView usando la plantilla `BaseModuleView`.

    Reusa la estética del sidebar y enlaza las acciones definidas en
    `buttons_menu.json` a métodos `show_*`.
    """

    def __init__(self, parent, db, keyboard_manager=None):
        # Initialize base template with module key 'shopify'
        super().__init__(parent, config_section='shopify')
        
        try:
            self.keyboard_mgr = keyboard_manager
        except Exception:
            self.keyboard_mgr = None
            
        try:
            self._module_key = 'shopify'
            self.module_name = 'shopify'
        except Exception:
            pass
            
        try:
            self.actualizar_ruta('SHOPIFY')
        except Exception:
            pass
            
        self.parent = parent
        self.db = db

        # Rebind menu buttons to local handlers based on buttons_menu.json
        try:
            cfg_file = CONFIG_DIR / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)
            menu = cfg.get('shopify', {}) if isinstance(cfg, dict) else {}
            buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
        except Exception:
            logging.exception('Error leyendo buttons_menu.json en ShopifyView')
            buttons = []

        # Map action names to methods
        action_map = {
            'show_config': self.show_config,
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
                            if action in action_map:
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
                            break
                    except Exception:
                        logging.exception("Error inspeccionando child en ShopifyView")
        except Exception:
            logging.exception('Error enlazando botones en ShopifyView')

        self.breadcrumb_callbacks = {
            'SHOPIFY': self.show_config, # Por ahora solo config
            'CONFIG': self.show_config,
        }

    def _on_power(self):
        """Gestionar botón Power con stack de navegación."""
        try:
            # Si hay algo en el área central, dejar que la plantilla base lo limpie
            return super()._on_power()
        except Exception:
            logging.exception('Error en _on_power')
            return False

    def show_config(self):
        """Muestra el tab de configuración de Shopify."""
        try:
            logging.info("Abriendo configuración de Shopify...")
            self.actualizar_ruta('CONFIG')
            
            from kool_tpv.modulos.shopify.services.shopify_config_service import ShopifyConfigService
            from kool_tpv.modulos.shopify.ui.config_tab import ShopifyConfigTab
            
            service = ShopifyConfigService(self.db)
            config_tab = ShopifyConfigTab(self.central_area, service)
            self.set_central_content(config_tab)
            
        except Exception:
            logging.exception("Error en show_config")

    def destruir(self):
        """Limpieza al cerrar el módulo."""
        try:
            self.sidebar.destroy()
            self.main_frame.destroy()
        except Exception:
            pass
