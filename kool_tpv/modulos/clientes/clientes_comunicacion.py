import logging
from typing import Optional

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.utils import COLOR_BG_TERMINAL


class ClientesComunicacionView:
    """Vista placeholder para la funcionalidad de comunicación de clientes.

    Diseñada como componente independiente que expone `get_widget()` y puede
    montarse en `ClientesView` usando `set_central_content()`.
    """

    def __init__(self, parent, db: Optional[object] = None, owner: Optional[object] = None,
                 module_name: str = 'clientes', keyboard_manager: Optional[object] = None):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = module_name
        self.keyboard_manager = keyboard_manager

        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            logging.exception('Error cargando paleta de colores para ClientesComunicacionView')
            self.colors = {'text': '#FFFFFF', 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        center = ctk.CTkFrame(self.container, fg_color='transparent')
        center.pack(fill='both', expand=True)

        from kool_tpv.utils.font_loader import get_font
        label = ctk.CTkLabel(
            center,
            text='COMUNICACIÓN CLIENTE',
            font=get_font('title', module='clientes'),
            text_color=self.colors.get('text', '#FFFFFF'),
            fg_color='transparent'
        )
        label.pack(expand=True)

    def get_widget(self):
        return self.container
