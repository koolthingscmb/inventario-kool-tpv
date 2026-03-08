"""Plantilla PaginaConVisorTickets - Layout con grid izquierda y ticket_carrito a la derecha.

Estructura mínima:
  - container: contenedor principal (grid 2 columnas)
  - breadcrumb_frame: fila superior con breadcrumbs clicables
  - left_container: columna izquierda (header + grid_scroll + footer)
    - header
    - grid_scroll
    - footer
  - ticket_carrito: columna derecha (visor fijo o con minsize según config)

Carga colores/temas desde `load_colors` y toma `ticket_carrito.width` desde `layout_config.json`.
"""
import logging
import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Any, Dict

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.clickable_breadcrumb import ClickableBreadcrumb

logger = logging.getLogger(__name__)


def load_layout_config() -> Dict[str, Any]:
    try:
        base = Path(__file__).resolve().parents[2]
        config_path = base / "config" / "layout_config.json"
        with open(config_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


class PaginaConVisorTickets:
    """Plantilla base para páginas con listado a la izquierda y ticket_carrito a la derecha.

    Uso: heredar y sobreescribir `_build_header`, `_build_grid`, `_build_footer`.
    """

    def __init__(self, parent, db: Optional[Any] = None, module_name: str = 'tpv'):
        self.parent = parent
        self.db = db
        self.module_name = module_name

        # colores del módulo
        try:
            self.colors = load_colors(module_name)
        except Exception:
            logger.exception('Error cargando colores; usando fallback')
            self.colors = {}

        # Container principal
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#000000'))

        # Breadcrumbs (fila 0)
        self.container.grid_columnconfigure(0, weight=7)
        self.container.grid_columnconfigure(1, weight=3)
        # Reserve rows: 0 breadcrumb (fixed), 1 content (expandible)
        self.container.grid_rowconfigure(0, weight=0)
        self.container.grid_rowconfigure(1, weight=1)

        # Breadcrumb widget (reuses shared ClickableBreadcrumb implementation)
        self.breadcrumb = ClickableBreadcrumb(self.container, module_name=self.module_name)
        self.breadcrumb.grid(row=0, column=0, columnspan=2, sticky='ew', padx=12, pady=(8, 6))

        # Column sizes / ticket width desde config
        cfg = load_layout_config()
        ticket_w = cfg.get('modules', {}).get('tpv', {}).get('ticket_carrito', {}).get('width', 420)

        # Left container (row 1, col 0)
        self.left_container = ctk.CTkFrame(self.container, fg_color='transparent')
        self.left_container.grid(row=1, column=0, sticky='nsew', padx=(12, 6), pady=12)

        # Header, grid_scroll, footer inside left_container
        self.header = ctk.CTkFrame(self.left_container, fg_color=self.colors.get('bg_dark', '#0d0d0d'))
        self.header.pack(side='top', fill='x', pady=(0, 12))

        self.grid_scroll = ctk.CTkScrollableFrame(self.left_container, fg_color=self.colors.get('background', '#000000'))
        self.grid_scroll.pack(side='top', fill='both', expand=True)

        self.footer = ctk.CTkFrame(self.left_container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', pady=(12, 0))

        # Right: ticket_carrito frame (row 1, col 1)
        self.ticket_carrito = ctk.CTkFrame(self.container, width=ticket_w, fg_color=self.colors.get('bg_dark', '#0d0d0d'))
        # asegurar al menos ticket_w como minsize de columna
        try:
            # set minsize but allow expansion if window larger
            self.container.grid_columnconfigure(1, minsize=int(ticket_w))
        except Exception:
            pass

        self.ticket_carrito.grid(row=1, column=1, sticky='nsew', padx=(6, 12), pady=12)
        self.ticket_carrito.pack_propagate(False)

        # Hooks to be implemented by subclasses
        try:
            self._build_header()
        except Exception:
            logger.exception('Error en _build_header')

        try:
            self._build_grid()
        except Exception:
            logger.exception('Error en _build_grid')

        try:
            self._build_footer()
        except Exception:
            logger.exception('Error en _build_footer')

        logger.info('PaginaConVisorTickets inicializada')

    # --- Hooks ---
    def _build_header(self):
        return None

    def _build_grid(self):
        return None

    def _build_footer(self):
        return None

    # --- Breadcrumb helpers ---
    def set_breadcrumbs(self, crumbs: List[Tuple[str, Optional[Callable]]]):
        """Establece breadcrumbs clicables usando `ClickableBreadcrumb`.

        crumbs: lista de (label, callback). Si callback no es callable, se pasa como None
        para que `ClickableBreadcrumb` renderice la última parte como texto.
        """
        try:
            if not hasattr(self, 'breadcrumb') or self.breadcrumb is None:
                return

            parts = []
            for label, cb in crumbs:
                parts.append((label, cb if callable(cb) else None))

            try:
                self.breadcrumb.update_parts(parts)
            except Exception:
                logger.exception('Error actualizando ClickableBreadcrumb desde PaginaConVisorTickets')
        except Exception:
            logger.exception('Error setting breadcrumbs')

    def get_widget(self):
        return self.container
