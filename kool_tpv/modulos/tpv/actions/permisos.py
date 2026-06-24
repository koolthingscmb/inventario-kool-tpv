"""Helper centralizado para comprobar permisos del cajero logueado.

Uso:
    from kool_tpv.modulos.tpv.actions.permisos import check_permiso
    if not check_permiso(carrito_service, 'permiso_descuento', parent):
        return
"""
import logging

logger = logging.getLogger(__name__)


def check_permiso(carrito_service, permiso: str, parent=None) -> bool:
    """Comprobar si el cajero logueado tiene un permiso.

    Args:
        carrito_service: Instancia de CarritoService con get_cajero().
        permiso: Nombre del permiso a comprobar (ej: 'permiso_descuento').
        parent: Widget padre para el Toast.

    Returns:
        True si hay cajero logueado y tiene el permiso.
        False si no hay cajero o no tiene permiso (muestra Toast error).
    """
    try:
        from kool_tpv.utils.widgets.notificaciones import ToastWidget

        cajero = None
        if carrito_service and hasattr(carrito_service, 'get_cajero'):
            cajero = carrito_service.get_cajero()

        if not cajero:
            ToastWidget.show(parent, 'DEBES LOGUEARTE COMO CAJERO', tipo='error')
            return False

        valor = cajero.get(permiso, 0)
        try:
            valor = int(valor)
        except Exception:
            valor = 0

        if not valor:
            ToastWidget.show(parent, 'NO TIENES PERMISO', tipo='error')
            return False

        return True
    except Exception:
        logging.exception('Error en check_permiso')
        return False
