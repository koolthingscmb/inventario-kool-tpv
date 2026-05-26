"""
DescuentoAction

Este action es llamado desde el mapper de botones del TPV cuando se
presiona el botón 'DESCUENTO'. Requiere autenticación de administrador
mediante `AuthService.validate_admin_password` antes de abrir la
subvista `DescuentoSubView`.
"""
import logging
from typing import Any

from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning

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

            # Validar carrito no vacío: evitar pedir contraseña si no hay artículos
            try:
                carrito = self.carrito_service or getattr(self.view, 'carrito_service', None)
                if carrito is not None:
                    try:
                        if carrito.is_empty():
                            show_warning(parent, 'Carrito vacío', 'Carrito vacío')
                            return
                    except Exception:
                        # Si is_empty falla, no bloqueamos la acción; continuar
                        pass
            except Exception:
                pass

            # Pedir contraseña admin
            password = show_password_dialog(parent, titulo="Autenticación Admin", mensaje="Introduce contraseña de administrador:")
            if password is None or password == "":
                return

            # Validar contraseña admin
            try:
                is_valid = False
                admin_user = None
                if self.auth_service:
                    try:
                        res = self.auth_service.validate_admin_password(password)
                    except Exception:
                        res = (False, None)

                    if isinstance(res, tuple):
                        is_valid, admin_user = res
                    else:
                        is_valid = bool(res)

                if not is_valid:
                    show_warning(parent, 'ACCESO DENEGADO', 'Contraseña incorrecta.')
                    return
            except Exception:
                self.logger.exception('Error validando contraseña admin')
                show_warning(parent, 'ERROR', 'Fallo validando contraseña admin')
                return

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
