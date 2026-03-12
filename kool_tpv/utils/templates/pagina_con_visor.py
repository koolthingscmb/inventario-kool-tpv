"""Plantilla PaginaConVisor - Layout con grid izquierda y visor derecha.

Estructura:
┌────────────────────────────────────────────────────────────┐
│ HEADER (filtros, buscador) │ TICKET DISPLAY │
├─────────────────────────────────────────┤ (altura │
│ GRID SCROLL (izquierda 70%) │ completa) │
│ - Filas de información │ │
│ - Scroll automático │ │
├─────────────────────────────────────────┤ │
│ FOOTER (botones acción) │ │
└────────────────────────────────────────────────────────────┘

Uso:
class TicketsUI(PaginaConVisor):
    def _build_header(self):
        # Crear filtros

    def _build_grid(self):
        # Crear filas

    def _build_footer(self):
        # Crear botones

"""
import logging
from typing import Optional, Any, Dict

import customtkinter as ctk

from kool_tpv.utils.widgets.ticket_display import TicketDisplay
from kool_tpv.utils.config_loader import load_colors

logger = logging.getLogger(__name__)


class PaginaConVisor:
    """Plantilla base para páginas con grid izquierda + visor derecha."""

    def __init__(self, parent, db: Optional[Any] = None, module_name: str = 'clientes'):
        """Inicializar plantilla con estructura completa.

        Args:
            parent: Widget padre donde se monta la UI
            db: Conexión a base de datos (opcional)
            module_name: Nombre del módulo para cargar colores
        """
        self.parent = parent
        self.db = db
        self.module_name = module_name

        # Cargar paleta de colores del módulo (load_colors ya devuelve fallbacks)
        try:
            self.colors: Dict[str, str] = load_colors(module_name)
        except Exception:
            logger.exception('Error cargando paleta de colores; usando valores por defecto')
            self.colors = {
                'background': '#000000',
                'bg_dark': '#0d0d0d',
                'primary': '#00FF00',
                'secondary': '#32CD32',
            }

        # Container principal (usa background del módulo)
        self.container = ctk.CTkFrame(
            parent,
            fg_color=self.colors.get('background', '#000000')
        )

        # === ESTRUCTURA 2 COLUMNAS: IZQUIERDA (info) + DERECHA (visor) ===
        self.container.grid_columnconfigure(0, weight=7)  # 70% izquierda
        self.container.grid_columnconfigure(1, weight=3)  # 30% derecha
        self.container.grid_rowconfigure(0, weight=1)

        # === COLUMNA IZQUIERDA (header + grid + footer) ===
        self.left_container = ctk.CTkFrame(self.container, fg_color='transparent')
        self.left_container.grid(row=0, column=0, sticky='nsew', padx=(12, 6), pady=12)

        # ZONA 1: HEADER (filtros, buscador)
        self.header = ctk.CTkFrame(
            self.left_container,
            fg_color=self.colors.get('bg_dark', '#0d0d0d'),
            corner_radius=8,
        )
        self.header.pack(side='top', fill='x', pady=(0, 12))

        # ZONA 2: GRID SCROLL (centro expansible)
        # customtkinter usa nombres específicos para colores de scrollbar en versiones recientes;
        # si alguna opción no existe en la versión del usuario, CTkScrollableFrame la ignorará.
        self.grid_scroll = ctk.CTkScrollableFrame(
            self.left_container,
            fg_color=self.colors.get('background', '#000000'),
            scrollbar_button_color=self.colors.get('primary', '#00FF00'),
            scrollbar_button_hover_color=self.colors.get('secondary', '#32CD32')
        )
        self.grid_scroll.pack(side='top', fill='both', expand=True)

        # ZONA 3: FOOTER (botones acción)
        self.footer = ctk.CTkFrame(self.left_container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', pady=(12, 0))

        # === COLUMNA DERECHA (visor altura completa) ===
        try:
            self.ticket_display = TicketDisplay(self.container, module_name=module_name)
            self.ticket_display.grid(row=0, column=1, sticky='nsew', padx=(6, 12), pady=12)
        except Exception:
            logger.exception('Error inicializando TicketDisplay')
            # Crear placeholder ligero para evitar crash
            self.ticket_display = ctk.CTkFrame(self.container, fg_color=self.colors.get('bg_dark', '#0d0d0d'))
            self.ticket_display.grid(row=0, column=1, sticky='nsew', padx=(6, 12), pady=12)

        # === HOOKS: Métodos que hijas deben implementar ===
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

        logger.info(f'PaginaConVisor inicializada para módulo: {module_name}')

    # --- Hooks (por defecto no hacen nada) ---
    def _build_header(self):
        """Hook: Implementar filtros/buscador en clase hija.

        Example:
            ctk.CTkLabel(self.header, text='FILTROS:', ...).pack(...)
            ctk.CTkEntry(self.header, ...).pack(...)
        """
        return None

    def _build_grid(self):
        """Hook: Implementar filas de información en clase hija.

        Example:
            for item in items:
                fila = ctk.CTkFrame(self.grid_scroll, ...)
                fila.pack(fill='x', padx=6, pady=3)
        """
        return None

    def _build_footer(self):
        """Hook: Implementar botones de acción en clase hija.

        Example:
            from kool_tpv.utils.config_loader import create_action_button
            btn = create_action_button(self.footer, 'imprimir', self._on_imprimir)
            btn.pack(side='left', padx=8)
        """
        return None

    # --- Utilidades para el visor ---
    def update_visor(self, contenido: str):
        """Actualizar contenido del visor derecha.

        Args:
            contenido: Texto del ticket/documento formateado
        """
        try:
            if hasattr(self.ticket_display, 'set_content'):
                self.ticket_display.set_content(contenido)
            else:
                # Si ticket_display es un frame placeholder, loggear
                logger.debug('TicketDisplay no expone set_content; no se actualiza')
            logger.debug('Visor actualizado con nuevo contenido')
        except Exception:
            logger.exception('Error actualizando visor')

    def clear_visor(self):
        """Limpiar contenido del visor."""
        try:
            if hasattr(self.ticket_display, 'clear'):
                self.ticket_display.clear()
            else:
                logger.debug('TicketDisplay no expone clear; nada que limpiar')
            logger.debug('Visor limpiado')
        except Exception:
            logger.exception('Error limpiando visor')

    def get_widget(self):
        """Retorna widget principal para integración."""
        return self.container
