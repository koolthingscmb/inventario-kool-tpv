"""
Acción: seleccionar y autenticar cajero.

Simplemente lanza la subvista CajeroSubView que gestiona todo el flujo.
"""
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.subviews.cajero_subview import CajeroSubView


class CajeroAction:
    """Acción para mostrar selección de cajero.
    
    La lógica completa de autenticación está en CajeroSubView.
    Esta clase es un thin wrapper para integración con el controller.
    """

    def __init__(self, view, db: Database):
        """
        Args:
            view: TpvView (para acceder a center_area y carrito_service)
            db: Database instance
        """
        self.view = view
        self.db = db

    def ejecutar(self) -> None:
        """Mostrar subvista de selección de cajero."""
        subview = CajeroSubView(
            parent=self.view.center_area,
            db=self.db,
            carrito_service=self.view.carrito_service,
            view=self.view
        )
        self.view.push_subview(subview, "CAJERO")
