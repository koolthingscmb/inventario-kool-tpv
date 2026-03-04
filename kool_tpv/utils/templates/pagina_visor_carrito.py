"""Plantilla base con grid izquierda y TicketCarrito derecha.

Estructura:
- Columna izquierda: header (con breadcrumb) + grid_scroll (sin footer)
- Columna derecha: TicketCarrito (widget completo funcionando)

Las subclases deben implementar:
- _build_header(): añadir widgets al header
- _build_grid(): añadir widgets al grid_scroll

Expone:
- self.ticket_carrito: referencia al widget TicketCarrito
- update_breadcrumb(parts): actualizar navegación
"""
import logging
from typing import List, Any

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors, load_layout_config
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.clickable_breadcrumb import ClickableBreadcrumb
from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito

logger = logging.getLogger(__name__)


class PaginaVisorCarrito(ctk.CTkFrame):
    """Base template: left grid + TicketCarrito on the right.

    Public attributes (required):
    - container, left_container, header, grid_scroll, breadcrumb,
      ticket_carrito_container, ticket_carrito, colors, db, module_name
    """

    def __init__(self, parent, db=None, module_name=None, **kwargs):
        # Save basics
        self.db = db
        self.module_name = module_name

        # Load colors with sensible defaults
        try:
            colors = load_colors(module_name) or {}
        except Exception:
            colors = {}
        # Ensure expected nested structure and defaults
        colors.setdefault('background', '#0a0a0a')
        if 'header' not in colors or not isinstance(colors.get('header'), dict):
            colors['header'] = {'bg': '#1a1a1a'}
        else:
            colors['header'].setdefault('bg', '#1a1a1a')
        if 'grid' not in colors or not isinstance(colors.get('grid'), dict):
            colors['grid'] = {'bg': '#0d0d0d'}
        else:
            colors['grid'].setdefault('bg', '#0d0d0d')

        self.colors = colors

        # Load layout config (ticket width)
        try:
            layout = load_layout_config() or {}
        except Exception:
            layout = {}
        try:
            ticket_width = (
                layout.get('modules', {})
                .get('tpv', {})
                .get('ticket_carrito', {})
                .get('width', 420)
            )
        except Exception:
            ticket_width = 420

        # Initialize base frame with module background
        super().__init__(parent, fg_color=self.colors.get('background'), **kwargs)

        # Main container where we place the two-column layout
        self.container = ctk.CTkFrame(self, fg_color=self.colors.get('background'))
        self.container.pack(fill='both', expand=True)

        # Grid config: two columns, left expands, right fixed
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=0)
        self.container.grid_rowconfigure(0, weight=1)

        # Left column: header + grid_scroll (no footer)
        # Use same padding conventions as PaginaConVisor so TPV layout matches ClientesTickets
        self.left_container = ctk.CTkFrame(self.container, fg_color='transparent')
        self.left_container.grid(row=0, column=0, sticky='nsew', padx=(12, 6), pady=12)

        # Header frame inside left_container
        header_bg = self.colors.get('header', {}).get('bg', '#1a1a1a')
        self.header = ctk.CTkFrame(self.left_container, fg_color=header_bg)
        # Header: let it adapt to its content (no fixed height).
        # Pack with bottom padding like PaginaConVisor so spacing matches ClientesTickets
        self.header.pack(side='top', fill='x', padx=12, pady=(0, 12))
        try:
            # Ensure propagation is enabled so header height follows its children
            self.header.pack_propagate(True)
        except Exception:
            pass

        # Breadcrumb inside header (create but don't pack yet).
        # We defer packing so subclasses can add header widgets (e.g. a
        # prominent search button) which should appear above the breadcrumb.
        try:
            self.breadcrumb = ClickableBreadcrumb(self.header, module_name=self.module_name)
        except Exception:
            # Keep attribute even if construction fails
            self.breadcrumb = None

        # Grid scroll area (anchored to top so buttons don't "fall")
        grid_bg = self.colors.get('grid', {}).get('bg', '#0d0d0d')
        self.grid_scroll = ctk.CTkScrollableFrame(self.left_container, fg_color=grid_bg)
        # Pack as top-fill expand (same as PaginaConVisor)
        self.grid_scroll.pack(side='top', fill='both', expand=True)

        # Build hooks for subclasses
        try:
            self._build_header()
        except Exception:
            logger.exception('Error in _build_header')

        # Now pack the breadcrumb so it appears under any header widgets
        # added by subclasses (avoids breadcrumb occupying the top space).
        try:
            if self.breadcrumb is not None:
                self.breadcrumb.pack(fill='x', anchor='n', pady=0)
        except Exception:
            logger.exception('Error packing breadcrumb')

        try:
            self._build_grid()
        except Exception:
            logger.exception('Error in _build_grid')

        # Right column: ticket carrito container with fixed width
        self.ticket_carrito_container = ctk.CTkFrame(self.container, fg_color='transparent', width=ticket_width)
        # Prevent container from shrinking to contents
        try:
            self.ticket_carrito_container.grid_propagate(False)
        except Exception:
            pass
        # Match padding used in PaginaConVisor so ticket area aligns with left column
        self.ticket_carrito_container.grid(row=0, column=1, sticky='nsew', padx=(6, 12), pady=12)

        # Instantiate TicketCarrito inside the container
        try:
            self.ticket_carrito = TicketCarrito(
                parent=self.ticket_carrito_container,
                carrito_service=None,
                keyboard_manager=None
            )
            self.ticket_carrito.pack(fill='both', expand=True)
        except Exception:
            logger.exception('Error instantiating TicketCarrito')
            self.ticket_carrito = None

    # Public API
    def get_widget(self) -> ctk.CTkFrame:
        return self.container

    def update_breadcrumb(self, parts: List[Any]):
        try:
            if self.breadcrumb is not None:
                self.breadcrumb.update_parts(parts)
        except Exception:
            logger.exception('Error updating breadcrumb')

    # Hooks for subclasses
    def _build_header(self):
        """Override in subclasses to add widgets into `self.header`."""
        return

    def _build_grid(self):
        """Override in subclasses to populate `self.grid_scroll`."""
        return
