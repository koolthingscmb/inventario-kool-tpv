"""UI de Devolución de albaranes.

Wrapper que reutiliza EntradaManualUI con tipo='DEVOLUCION'.
"""
import logging
from .entrada_manual import EntradaManualUI

logger = logging.getLogger(__name__)


class DevolucionUI:
    """Devolución a proveedor - resta stock del almacén."""

    def __init__(self, parent, db=None):
        # Delegar a EntradaManualUI con tipo='DEVOLUCION'
        self._delegate = EntradaManualUI(parent, db=db, tipo='DEVOLUCION')

    def get_widget(self):
        return self._delegate.get_widget()

    def has_unsaved_changes(self):
        return self._delegate.has_unsaved_changes()
