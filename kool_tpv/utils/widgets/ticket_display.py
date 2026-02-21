"""TicketDisplay - Widget visor de tickets con estilo impresora térmica.

Características:

    Fondo negro terminal
    Texto monoespacio (Courier New)
    Scroll automático si contenido largo
    Adaptable a colores de módulo
    Métodos set_content() y clear()
"""
import logging
from typing import Optional, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors

logger = logging.getLogger(__name__)


class TicketDisplay(ctk.CTkFrame):
    """Widget para mostrar tickets/documentos con formato de impresora."""

    def __init__(self, parent, module_name: str = 'clientes', **kwargs):
        """Inicializar visor de tickets.

        Args:
            parent: Widget padre
            module_name: Módulo para cargar colores (clientes, almacen, etc.)
            **kwargs: Argumentos adicionales para CTkFrame
        """
        # Cargar colores del módulo (load_colors maneja fallbacks)
        try:
            self.colors: Dict[str, Any] = load_colors(module_name)
        except Exception:
            logger.exception('Error cargando paleta de colores; usando valores por defecto')
            self.colors = {
                'background': '#000000',
                'bg_dark': '#0d0d0d',
                'primary': '#00FF00',
                'text': '#00FF00',
            }

        # Configurar frame principal con colores del módulo
        super().__init__(
            parent,
            fg_color=self.colors.get('background', '#000000'),
            border_color=self.colors.get('primary', '#00FF00'),
            border_width=2,
            corner_radius=8,
            **kwargs
        )

        # Header del visor
        self.header = ctk.CTkLabel(
            self,
            text='VISTA PREVIA TICKET',
            font=('Courier New', 14, 'bold'),
            text_color=self.colors.get('text', '#00FF00'),
            fg_color='transparent',
            anchor='center'
        )
        self.header.pack(side='top', fill='x', padx=8, pady=(8, 4))

        # Separador
        separador = ctk.CTkFrame(
            self,
            height=2,
            fg_color=self.colors.get('primary', '#00FF00')
        )
        separador.pack(side='top', fill='x', padx=8, pady=(0, 8))

        # Textbox para contenido del ticket (con scroll)
        # Algunas versiones de customtkinter aceptan activate_scrollbars; intentamos y hacemos fallback.
        try:
            self.textbox = ctk.CTkTextbox(
                self,
                font=('Courier New', 13),
                text_color=self.colors.get('text', '#00FF00'),
                fg_color=self.colors.get('bg_dark', '#0d0d0d'),
                wrap='none',
                activate_scrollbars=True
            )
        except TypeError:
            self.textbox = ctk.CTkTextbox(
                self,
                font=('Courier New', 13),
                text_color=self.colors.get('text', '#00FF00'),
                fg_color=self.colors.get('bg_dark', '#0d0d0d'),
                wrap='none'
            )

        self.textbox.pack(side='top', fill='both', expand=True, padx=8, pady=(0, 8))

        # Mensaje por defecto
        self._set_placeholder()

        logger.debug(f'TicketDisplay inicializado para módulo: {module_name}')

    def _set_placeholder(self):
        """Mostrar mensaje por defecto cuando no hay contenido."""
        try:
            self.textbox.configure(state='normal')
            self.textbox.delete('1.0', 'end')
            placeholder = """


            ┌─────────────────┐
            │                 │
            │   SELECCIONA    │
            │   UN TICKET     │
            │   PARA VER      │
            │   DETALLES      │
            │                 │
            └─────────────────┘

        """
            self.textbox.insert('1.0', placeholder)
            self.textbox.configure(state='disabled')
        except Exception:
            logger.exception('Error configurando placeholder')

    def set_content(self, contenido: Optional[str]):
        """Actualizar contenido del visor con texto del ticket.

        Args:
            contenido: Texto formateado del ticket (estilo impresora)
        """
        try:
            self.textbox.configure(state='normal')
            self.textbox.delete('1.0', 'end')

            if contenido and contenido.strip():
                self.textbox.insert('1.0', contenido)
            else:
                self._set_placeholder()
                return

            self.textbox.configure(state='disabled')
            logger.debug('Contenido actualizado en TicketDisplay')
        except Exception:
            logger.exception('Error actualizando contenido TicketDisplay')

    def clear(self):
        """Limpiar contenido y mostrar placeholder."""
        try:
            self._set_placeholder()
            logger.debug('TicketDisplay limpiado')
        except Exception:
            logger.exception('Error limpiando TicketDisplay')

    def get_content(self) -> str:
        """Obtener contenido actual del visor.

        Returns:
            Texto actual del visor (vacío si es placeholder)
        """
        try:
            content = self.textbox.get('1.0', 'end-1c')
            # Detectar si es placeholder
            if 'SELECCIONA' in content and 'UN TICKET' in content:
                return ''
            return content
        except Exception:
            logger.exception('Error obteniendo contenido TicketDisplay')
            return ''
