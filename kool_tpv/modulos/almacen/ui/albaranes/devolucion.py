"""UI de Devolución."""
import logging
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX

logger = logging.getLogger(__name__)

class DevolucionUI:
    def __init__(self, parent, db=None):
        self.parent = parent
        self.db = db
        self.container = ctk.CTkFrame(parent, fg_color=COLOR_BG_TERMINAL)

        lbl = ctk.CTkLabel(self.container, text='DEVOLUCIÓN - En construcción',
                           text_color=COLOR_MATRIX)
        lbl.pack(expand=True)

    def get_widget(self):
        return self.container
