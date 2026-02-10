"""
Acción: seleccionar y autenticar cajero.

Muestra lista de cajeros, valida password con SHA-256 y actualiza sesión.
"""
import hashlib
import logging
from typing import Dict, List, Optional

from kool_tpv.utils.custom_dialog import show_warning, show_input_dialog
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.ui.cajero_ui import UICajero


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

    def ejecutar(self) -> None:
        """Mostrar UI de selección de cajero."""
        try:
            # Crear y mostrar overlay
            overlay = UICajero(
                self.view,
                self.db,
                on_selection_callback=self._on_cajero_selected
            )
            overlay.show()
        except Exception:
            logging.exception('Error ejecutando CajeroAction')

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

    def validar_password(self, cajero_id: int, password_plain: str) -> bool:
        """Validar contraseña ingresada contra hash en BD.

        Args:
            cajero_id: ID del cajero
            password_plain: Contraseña en texto plano

        Returns:
            True si password es correcto, False si no
        """
        try:
            # Obtener hash desde BD
            row = self.db.fetch_one(
                "SELECT password FROM usuarios WHERE id = ?",
                (cajero_id,),
            )

            if not row:
                logging.warning(f"Cajero {cajero_id} no encontrado en BD")
                return False

            hash_bd: Optional[str] = row[0]
            if not hash_bd:
                logging.warning(f"Cajero {cajero_id} tiene password vacío en BD")
                return False

            # Hashear input con SHA-256
            hash_input = hashlib.sha256(password_plain.encode("utf-8")).hexdigest()

            # Comparar (case-insensitive por seguridad)
            return hash_input.lower() == hash_bd.lower()

        except Exception:
            logging.exception(f"Error validando password para cajero {cajero_id}")
            return False

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

            # Pedir contraseña con CustomInputDialog
            nombre = cajero_data.get("nombre", "Cajero")
            password = show_input_dialog(
                parent,
                titulo="Autenticación",
                mensaje=f"Introduce la contraseña de {nombre}:",
                tipo="info",
            )

            # Si canceló o dejó vacío, salir
            if password is None or password == "":
                return

            # Validar password
            cajero_id = cajero_data.get("id")
            if cajero_id is None:
                logging.warning("_cajero_selected: cajero_data sin id")
                return

            if self.validar_password(cajero_id, password):
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

            # Guardar en TpvView
            if self.view is not None:
                setattr(self.view, "cajero_nombre", nombre)
                setattr(self.view, "cajero_id", cajero_data.get("id"))
                setattr(self.view, "cajero_rol", cajero_data.get("rol"))

            # Forzar actualización del visor inmediatamente
            try:
                if hasattr(self.view, '_update_clock') and callable(self.view._update_clock):
                    self.view._update_clock()
            except Exception:
                logging.exception('Error actualizando visor tras autenticación')

            logging.info(
                f"Cajero autenticado: {nombre} (ID: {cajero_data.get('id')}, Rol: {cajero_data.get('rol')})"
            )

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
        valido = action.validar_password(1, test_password)
        print(f"  Resultado: {'✅ VÁLIDO' if valido else '❌ INVÁLIDO'}")
    except Exception:
        logging.exception("Error en test de password")

    try:
        db.close_connection()
    except Exception:
        pass
