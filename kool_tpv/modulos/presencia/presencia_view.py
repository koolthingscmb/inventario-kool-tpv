"""PresenciaView: Orquestador del módulo de control de presencia."""
import logging
from kool_tpv.utils.templates.base_module_view import BaseModuleView
from .ui.presencia_ui import PresenciaUI

class PresenciaView(BaseModuleView):
    def __init__(self, parent, db, keyboard_manager=None):
        # Inicializar plantilla base con clave 'presencia'
        super().__init__(parent, config_section='presencia')
        self.db = db
        self.keyboard_mgr = keyboard_manager
        self.module_name = 'presencia'
        
        # Actualizar breadcrumb
        try:
            self.actualizar_ruta('PRESENCIA')
        except Exception:
            pass
            
        # Mostrar la UI de fichajes por defecto
        self.show_fichajes()

    def show_fichajes(self):
        """Muestra la interfaz principal de fichajes."""
        try:
            ui = PresenciaUI(self.central_area, db=self.db, view=self)
            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('PRESENCIA / FICHAJES')
                except Exception:
                    pass
            logging.info('Módulo Presencia: Abriendo fichajes...')
        except Exception:
            logging.exception('Error abriendo fichajes en PresenciaView')

    def _on_power(self):
        """Gestiona el botón Power. 
        En este módulo, al ser simple, permitimos que se cierre directamente.
        """
        return False # Permitir que main.py cierre el módulo y vuelva al menú
