"""UI de Salida Manual de albaranes.

Wrapper que reutiliza EntradaManualUI con tipo='SALIDA'.
"""
import logging
from .entrada_manual import EntradaManualUI

logger = logging.getLogger(__name__)


class SalidaManualUI:
    """Salida manual - resta stock del almacén."""

    def __init__(self, parent, db=None, module_name: str = 'almacen', keyboard_manager=None):
        # Delegar a EntradaManualUI con tipo='SALIDA'
        self._delegate = EntradaManualUI(parent, db=db, tipo='SALIDA', module_name=module_name, keyboard_manager=keyboard_manager)

    def get_widget(self):
        return self._delegate.get_widget()

    def has_unsaved_changes(self):
        return self._delegate.has_unsaved_changes()

