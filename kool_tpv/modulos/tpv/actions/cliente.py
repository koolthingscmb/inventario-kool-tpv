"""Acción para abrir el panel de clientes y vincular la selección al carrito.

Provee la clase `ClienteAction` que centraliza la creación/mostrar del
overlay de selección de clientes y la asignación del cliente elegido
al `CarritoService` actualmente en uso.
"""
from __future__ import annotations
from typing import Any, Optional, Dict
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.subviews.cliente_subview import ClienteSubView
from kool_tpv.utils.custom_dialog import show_warning


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
        # No crear ni usar UIClientes aquí; ClienteSubView se mostrará cuando se ejecute
        self._panel = None

    def ejecutar(self) -> None:
        """Mostrar el overlay de clientes. Reutiliza la instancia si ya existe."""
        try:
            # Bloquear añadir cliente si ya hay un descuento aplicado en el carrito
            try:
                carrito = self.carrito_service or getattr(self.view, 'carrito_service', None)
                if carrito is not None and getattr(carrito, 'has_descuento', None):
                    try:
                        if carrito.has_descuento():
                            parent = None
                            try:
                                parent = self.view.parent.winfo_toplevel()
                            except Exception:
                                parent = getattr(self.view, 'parent', self.view)
                            show_warning(parent, 'No se puede añadir cliente con un descuento en curso', 'No se puede añadir cliente con un descuento en curso')
                            return
                    except Exception:
                        logging.exception('ClienteAction: error comprobando descuento activo')
            except Exception:
                logging.exception('ClienteAction: error comprobando descuento activo (outer)')
            try:
                subview = ClienteSubView(
                    parent=self.view.center_area,
                    db=self.db,
                    carrito_service=self.carrito_service,
                    view=self.view
                )
                # Mostrar sub-vista usando el stack del view
                try:
                    self.view.push_subview(subview, "CLIENTE")
                except Exception:
                    logging.exception("ClienteAction: fallo mostrando ClienteSubView")
            except Exception:
                logging.exception("ClienteAction: error creando ClienteSubView")
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
