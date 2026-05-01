"""UI de Exportar Albarán."""
import logging
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors

logger = logging.getLogger(__name__)

class ExportarAlbaranUI:
    def __init__(self, parent, db=None):
        self.parent = parent
        self.db = db
        try:
            self.colors = load_colors('almacen')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}
        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        lbl = ctk.CTkLabel(self.container, text='EXPORTAR ALBARÁN - En construcción',
                           text_color=self.colors.get('text', COLOR_MATRIX))
        lbl.pack(expand=True)

    def get_widget(self):
        return self.container
