import logging
from typing import Any, Dict

from kool_tpv.utils.custom_dialog import show_error, show_warning


class DescuentoAction:
    """Controlador para aplicar descuentos desde el TPV.

    Realiza validaciones de permisos y estado del carrito antes de abrir
    el overlay de descuentos (`UIDescuento`).
    """

    def __init__(self, view: Any, carrito_service: Any):
        self.view = view
        self.carrito_service = carrito_service
        self.logger = logging.getLogger(self.__class__.__name__)

    def ejecutar(self) -> None:
        """Validar permisos y estado del carrito; abrir overlay si OK."""
        try:
            # Validar rol del cajero
            cajero_rol = getattr(self.view, 'cajero_rol', None)
            if not cajero_rol:
                show_warning(self.view.parent if hasattr(self.view, 'parent') else None,
                             'ACCESO DENEGADO', 'Debe autenticarse como cajero')
                self.logger.warning('Intento de descuento sin cajero autenticado')
                return

            if str(cajero_rol) != 'admin':
                cajero_id = getattr(self.view, 'cajero_id', None)
                permiso = 0
                try:
                    if getattr(self.view, 'db', None) is not None and cajero_id is not None:
                        row = self.view.db.fetch_one(
                            'SELECT permiso_descuento FROM usuarios WHERE id = ?',
                            (cajero_id,)
                        )
                        if row:
                            # row can be tuple or dict
                            if isinstance(row, dict):
                                permiso = int(row.get('permiso_descuento', 0) or 0)
                            else:
                                permiso = int(row[0] or 0)
                except Exception:
                    self.logger.exception('Error consultando permiso_descuento en BD')
                    permiso = 0

                if permiso != 1:
                    show_warning(self.view.parent if hasattr(self.view, 'parent') else None,
                                 'SIN PERMISOS', 'No tiene permisos para aplicar descuentos')
                    self.logger.warning('Cajero %s sin permiso_descuento', cajero_id)
                    return

            # Validar carrito no vacío
            try:
                items = self.carrito_service.get_items()
            except Exception:
                items = None

            if not items:
                show_warning(self.view.parent if hasattr(self.view, 'parent') else None,
                             'CARRITO VACÍO', 'Añada productos antes de aplicar descuentos')
                self.logger.warning('Intento de descuento con carrito vacío')
                return

            # Validar que no exista ya un descuento aplicado
            try:
                descuento_actual = self.carrito_service.get_descuento()
            except Exception:
                descuento_actual = None

            if descuento_actual is not None:
                show_warning(self.view.parent if hasattr(self.view, 'parent') else None,
                             'DESCUENTO EXISTENTE', 'Ya hay un descuento aplicado. Elimínelo primero.')
                self.logger.warning('Intento de nuevo descuento cuando ya existe: %s', descuento_actual)
                return

            # Si ya hay puntos canjeados, avisar y no abrir el overlay
            try:
                puntos = self.carrito_service.get_puntos_canjeados()
                try:
                    from decimal import Decimal
                    puntos_dec = Decimal(str(puntos))
                except Exception:
                    puntos_dec = puntos
                if puntos_dec > Decimal('0.00'):
                    show_error(self.view.parent if hasattr(self.view, 'parent') else None,
                               'PUNTOS CANJEADOS', 'Hay puntos canjeados en este ticket. Elimine el canje antes de aplicar un descuento.')
                    self.logger.warning('Intento de descuento cuando hay puntos canjeados: %s', puntos_dec)
                    return
            except Exception:
                self.logger.exception('Error comprobando puntos canjeados antes de abrir overlay descuento')

            # Abrir overlay de descuentos (lazy import para evitar dependencia en import-time)
            try:
                try:
                    from kool_tpv.modulos.tpv.ui.descuento_ui import UIDescuento
                except Exception:
                    UIDescuento = None

                if UIDescuento is None:
                    show_error(self.view.parent if hasattr(self.view, 'parent') else None,
                               'ERROR', 'Interfaz de descuento no disponible')
                    self.logger.error('UIDescuento no disponible')
                    return

                # Pass the TpvView (self.view) so SelectionOverlayTemplate can
                # access `right_container` and compute the correct overlay width.
                overlay = UIDescuento(self.view, self.view.db, self._on_descuento_aplicado)
                overlay.show()
            except Exception:
                self.logger.exception('Error abriendo UIDescuento')

        except Exception:
            self.logger.exception('Error en ejecución de DescuentoAction')

    def _on_descuento_aplicado(self, descuento_data: Dict[str, Any]) -> None:
        """Callback cuando se aplica un descuento desde el overlay."""
        try:
            # Intentar aplicar descuento en el servicio
            self.carrito_service.aplicar_descuento(descuento_data)

            # Si OK, actualizar UI
            try:
                if getattr(self.view, 'carrito_ui', None) is not None:
                    self.view.carrito_ui.update_display()
            except Exception:
                self.logger.exception('Error actualizando carrito_ui tras descuento')

            # Loguear
            self.logger.info(f"Descuento aplicado: {descuento_data}")

        except ValueError as e:
            # Capturar errores de validación del servicio: mostrar como WARNING
            try:
                parent = self.view.parent.winfo_toplevel() if hasattr(self.view, 'parent') else None
                show_warning(parent, 'ERROR AL APLICAR DESCUENTO', str(e))
            except Exception:
                self.logger.exception('Error mostrando diálogo de warning por ValueError')
            self.logger.warning(f'Error al aplicar descuento: {e}')

        except Exception as e:
            # Capturar cualquier otro error
            try:
                parent = self.view.parent.winfo_toplevel() if hasattr(self.view, 'parent') else None
                show_error(parent, 'ERROR INESPERADO', f'No se pudo aplicar el descuento: {str(e)}')
            except Exception:
                self.logger.exception('Error mostrando diálogo de error inesperado')
            self.logger.error(f'Error inesperado al aplicar descuento: {e}', exc_info=True)
