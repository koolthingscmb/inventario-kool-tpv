"""Acción para abrir el panel de clientes y vincular la selección al carrito.

Provee la clase `ClienteAction` que centraliza la creación/mostrar del
overlay de selección de clientes y la asignación del cliente elegido
al `CarritoService` actualmente en uso.
"""
from __future__ import annotations
from typing import Any, Optional, Dict
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.ui_clientes import UIClientes


class ClienteAction:
    """Orquesta la apertura del panel de clientes y asigna la selección al carrito.

    Args:
        view: instancia de `TpvView` (o similar) que contiene `carrito_ui`.
        db: instancia de `Database` conectada.
        carrito_service: servicio del carrito con método `set_cliente(dict)`.
    """

    def __init__(self, view: Any, db: Database, carrito_service: Any) -> None:
        self.view = view
        self.db = db
        self.carrito_service = carrito_service
        self._panel: Optional[UIClientes] = None

    def ejecutar(self) -> None:
        """Mostrar el overlay de clientes. Reutiliza la instancia si ya existe."""
        try:
            if self._panel is None:
                self._panel = UIClientes(self.view, self.db, on_cliente_selected=self._on_cliente_selected)
            else:
                # Asegurar callback actualizado
                self._panel.on_cliente_selected = self._on_cliente_selected

            # Mostrar el panel (UIClientes.show maneja posicionamiento)
            try:
                self._panel.show()
            except Exception:
                logging.exception("ClienteAction: fallo mostrando panel de clientes")
        except Exception:
            logging.exception("ClienteAction: error al ejecutar acción")

    def _on_cliente_selected(self, cliente: Dict[str, Any]) -> None:
        """Callback que se ejecuta cuando el usuario confirma un cliente.

        Realiza:
        - Asignar el cliente al `CarritoService`.
        - Forzar refresco visual del carrito mediante `carrito_ui.update_display()`.
        - Registrar en logs.

        Nota: Asegurarse que `carrito_ui.update_display()` muestre el nombre
        del cliente en la UI (pendiente de implementación si aún no lo hace).
        """
        try:
            # Asignar cliente al carrito (se asume que set_cliente acepta un dict)
            try:
                self.carrito_service.set_cliente(cliente)
            except Exception:
                logging.exception("ClienteAction: fallo asignando cliente al carrito")

            # Forzar actualización visual del carrito
            try:
                if getattr(self.view, "carrito_ui", None) is not None:
                    self.view.carrito_ui.update_display()
                else:
                    logging.debug("ClienteAction: carrito_ui no disponible en la vista para refrescar")
            except Exception:
                logging.exception("ClienteAction: error refrescando carrito_ui")

            # Log de auditoría
            try:
                logging.info("Cliente vinculado a la venta: %s", cliente)
            except Exception:
                pass

            # Recordatorio: implementar en `carrito_ui.update_display()` la visualización
            # del nombre del cliente si aún no existe.
        except Exception:
            logging.exception("ClienteAction: error en on_cliente_selected")
