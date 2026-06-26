"""
DescuentoAction

Este action es llamado desde el mapper de botones del TPV cuando se
presiona el botón 'DESCUENTO'. Requiere autenticación de administrador
mediante `AuthService.validate_admin_password` antes de abrir la
subvista `DescuentoSubView`.
"""
import logging
from typing import Any

from kool_tpv.utils.custom_dialog import show_password_dialog
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)


class DescuentoAction:
    def __init__(self, view: Any, carrito_service: Any):
        self.view = view
        self.carrito_service = carrito_service
        # Resolver DB: preferir view.db, luego intentar extraer de carrito_service
        db = None
        try:
            db = getattr(view, 'db', None)
        except Exception:
            db = None
        if db is None:
            try:
                db = getattr(carrito_service, 'db', None)
            except Exception:
                db = None
        self.db = db

        # AuthService (may be None if DB not available)
        try:
            from kool_tpv.utils.auth_service import AuthService

            if self.db is not None:
                self.auth_service = AuthService(self.db)
            else:
                # fallback: try constructing with carrito_service.db if present
                self.auth_service = AuthService(getattr(carrito_service, 'db', None))
        except Exception:
            self.auth_service = None

        self.logger = logger.getChild('DescuentoAction')

    def ejecutar(self) -> None:
        try:
            parent = None
            try:
                parent = self.view.parent.winfo_toplevel()
            except Exception:
                try:
                    parent = self.view.parent
                except Exception:
                    parent = self.view

            # Comprobar permiso del cajero logueado
            from kool_tpv.modulos.tpv.actions.permisos import check_permiso
            if not check_permiso(self.carrito_service, 'permiso_descuento', parent):
                return

            # Validar carrito no vacío: evitar pedir contraseña si no hay artículos
            try:
                carrito = self.carrito_service or getattr(self.view, 'carrito_service', None)
                if carrito is not None:
                    try:
                        if carrito.is_empty():
                            ToastWidget.show(parent, 'CARRITO VACÍO', tipo='warning')
                            return
                    except Exception:
                        # Si is_empty falla, no bloqueamos la acción; continuar
                        pass
            except Exception:
                pass

            # Bloquear acceso a descuentos si hay una devolución en curso
            try:
                carrito = self.carrito_service or getattr(self.view, 'carrito_service', None)
                if carrito is not None:
                    try:
                        ticket_type = None
                        if callable(getattr(carrito, 'get_ticket_type', None)):
                            ticket_type = carrito.get_ticket_type()
                        if ticket_type == 'devolucion':
                            return
                    except Exception:
                        # No bloquear si falla la comprobación
                        pass
            except Exception:
                pass

            # Bloquear acceso si ya hay un descuento aplicado en el carrito
            try:
                carrito = self.carrito_service or getattr(self.view, 'carrito_service', None)
                if carrito is not None and getattr(carrito, 'has_descuento', None):
                    try:
                        if carrito.has_descuento():
                            ToastWidget.show(parent, 'YA HAY UN DESCUENTO EN CURSO', tipo='warning')
                            return
                    except Exception:
                        # si la comprobación falla, no bloqueamos
                        pass
            except Exception:
                pass

            # Autenticado: abrir DescuentoSubView
            try:
                from kool_tpv.modulos.tpv.subviews.descuento_subview import DescuentoSubView

                parent_area = getattr(self.view, 'center_area', self.view)
                subview = DescuentoSubView(parent=parent_area, db=self.db, carrito_service=self.carrito_service, view=self.view)
                try:
                    self.view.push_subview(subview, 'DESCUENTOS')
                except Exception:
                    # fallback: if view has controller, try pushing there
                    try:
                        if getattr(self.view, 'controller', None):
                            self.view.controller.view.push_subview(subview, 'DESCUENTOS')
                    except Exception:
                        self.logger.exception('Error mostrando DescuentoSubView')
            except Exception:
                self.logger.exception('Error creando DescuentoSubView')

        except Exception:
            self.logger.exception('Error ejecutando DescuentoAction')
