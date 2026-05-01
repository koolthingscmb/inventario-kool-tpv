"""
Acción: seleccionar y autenticar cajero.

Muestra lista de cajeros, valida password con SHA-256 y actualiza sesión.
"""
import logging
from typing import Dict, List, Optional

from kool_tpv.utils.custom_dialog import show_warning, show_password_dialog
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.subviews.cajero_subview import CajeroSubView


class CajeroAction:
    """Acción para seleccionar y autenticar cajero."""

    def __init__(self, view, db: Database):
        """
        Args:
            view: TpvView (para actualizar visor)
            db: Database instance
        """
        self.view = view
        self.db = db
        try:
            self.auth_service = AuthService(db)
        except Exception:
            self.auth_service = None

    def ejecutar(self) -> None:
        from kool_tpv.modulos.tpv.subviews.cajero_subview import CajeroSubView

        subview = CajeroSubView(
            parent=self.view.center_area,
            db=self.db,
            carrito_service=self.view.carrito_service,
            view=self.view
        )
        self.view.push_subview(subview, "CAJERO")

    def obtener_cajeros(self) -> List[Dict]:
        """Obtener lista de cajeros desde tabla usuarios.

        Returns:
            Lista de dicts con {id, nombre, rol}
        """
        try:
            rows = self.db.fetch_all(
                "SELECT id, nombre, rol FROM usuarios ORDER BY nombre"
            )
            cajeros: List[Dict] = []
            if not rows:
                return cajeros
            for row in rows:
                cajeros.append({
                    "id": row[0],
                    "nombre": row[1],
                    "rol": row[2],
                })
            return cajeros
        except Exception:
            logging.exception("Error obteniendo cajeros desde BD")
            return []

    

    def _on_cajero_selected(self, cajero_data: Dict) -> None:
        """Callback interno cuando se selecciona un cajero.

        Args:
            cajero_data: Dict con {id, nombre, rol}
        """
        try:
            # Obtener ventana padre correcta para diálogos (usar widget real `self.view.parent`)
            parent = None
            if self.view is not None:
                try:
                    parent = self.view.parent.winfo_toplevel()
                except Exception:
                    try:
                        parent = self.view.parent
                    except Exception:
                        parent = self.view

            # Pedir contraseña enmascarada con CustomInputDialog
            nombre = cajero_data.get("nombre", "Cajero")
            password = show_password_dialog(
                parent,
                titulo="Autenticación",
                mensaje=f"Introduce la contraseña de {nombre}:"
            )

            # Si canceló o dejó vacío, salir
            if password is None or password == "":
                return

            # Validar password
            cajero_id = cajero_data.get("id")
            if cajero_id is None:
                logging.warning("_cajero_selected: cajero_data sin id")
                return

            if self.auth_service and self.auth_service.validate_user_password(cajero_id, password):
                # ✅ Password correcto
                self._actualizar_sesion(cajero_data)
            else:
                # ❌ Password incorrecto - usar callback para retry DESPUÉS de cerrar warning
                show_warning(
                    parent,
                    "CÓDIGO NO VÁLIDO",
                    "La contraseña introducida es incorrecta.\nInténtalo de nuevo.",
                    callback=lambda: self._on_cajero_selected(cajero_data)
                )

        except Exception:
            logging.exception("Error en _on_cajero_selected")

    def _actualizar_sesion(self, cajero_data: Dict) -> None:
        """Actualizar sesión con cajero autenticado.

        Args:
            cajero_data: Dict con {id, nombre, rol}
        """
        try:
            nombre = cajero_data.get("nombre", "")

            # Guardar cajero activamente SOLO en el CarritoService
            try:
                carrito_service = getattr(self.view, 'carrito_service', None)
                if carrito_service and getattr(carrito_service, 'set_cajero', None):
                    carrito_service.set_cajero({
                        'nombre': nombre,
                        'id': cajero_data.get('id'),
                        'rol': cajero_data.get('rol')
                    })
            except Exception:
                logging.exception('Error guardando cajero en CarritoService')

            # Actualizar visualmente el widget de ticket si existe
            try:
                if self.view is not None and getattr(self.view, 'ticket_widget', None):
                    try:
                        self.view.ticket_widget.update_cajero(nombre)
                    except Exception:
                        logging.exception('Error llamando ticket_widget.update_cajero')
            except Exception:
                logging.exception('Error actualizando widget de ticket tras autenticación')

            # Forzar actualización del visor inmediatamente (mantener compatibilidad con vistas que implementen _update_clock)
            try:
                if hasattr(self.view, '_update_clock') and callable(self.view._update_clock):
                    self.view._update_clock()
            except Exception:
                logging.exception('Error actualizando visor tras autenticación')

            logging.info(f"Cajero autenticado: {nombre} (ID: {cajero_data.get('id')}, Rol: {cajero_data.get('rol')})")

        except Exception:
            logging.exception("Error actualizando sesión de cajero")


if __name__ == "__main__":
    # Helper para testing desde consola (opcional)
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))

    db_path = repo_root / "kool_tpv" / "base_datos" / "kool_bd.db"
    db = Database(str(db_path))
    try:
        db.connect()
    except Exception:
        logging.exception("No se pudo conectar a la BD de prueba")

    action = CajeroAction(None, db)

    # Test: listar cajeros
    cajeros = action.obtener_cajeros()
    print("\n📋 Cajeros en BD:")
    for c in cajeros:
        print(f"  - {c['nombre']} ({c['rol']})")

    # Test: validar password
    print("\n🔐 Test validación password:")
    try:
        test_password = input("Introduce password de EGON para test: ")
        valido = action.auth_service.validate_user_password(1, test_password) if getattr(action, 'auth_service', None) else False
        print(f"  Resultado: {'✅ VÁLIDO' if valido else '❌ INVÁLIDO'}")
    except Exception:
        logging.exception("Error en test de password")

    try:
        db.close_connection()
    except Exception:
        pass
