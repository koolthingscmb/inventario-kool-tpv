import hashlib
import logging
from typing import List, Dict, Any


class AuthService:
    """Servicio centralizado de autenticación.

    Valida contraseñas contra usuarios con SHA-256.
    Reutilizable en protección de módulos sensibles.
    """

    def __init__(self, db):
        self.db = db

    def validate_admin_password(self, password: str) -> bool:
        """Valida contraseña contra CUALQUIER usuario con rol='admin'.

        Args:
            password: Contraseña en texto plano

        Returns:
            True si coincide con algún admin, False si no
        """
        try:
            # Hash del password ingresado
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            # Buscar usuarios admin
            query = """
                SELECT id, nombre, password
                FROM usuarios
                WHERE rol = 'admin'
            """

            admins = self.db.fetch_all(query) or []

            if not admins:
                logging.warning('No hay usuarios admin en la BD')
                return False

            # Verificar si alguno coincide
            for admin in admins:
                stored_hash = admin.get('password', '')
                if stored_hash == password_hash:
                    logging.info('Autenticación admin exitosa para: %s', admin.get('nombre'))
                    return True

            logging.warning('Password admin incorrecto')
            return False

        except Exception:
            logging.exception('Error validando password admin')
            return False

    def get_admin_users(self) -> List[Dict[str, Any]]:
        """Obtener lista de usuarios admin (sin passwords).

        Returns:
            Lista de dicts con id y nombre
        """
        try:
            query = """
                SELECT id, nombre
                FROM usuarios
                WHERE rol = 'admin'
            """
            rows = self.db.fetch_all(query) or []
            # Normalizar salida: solo id y nombre
            return [{'id': r.get('id'), 'nombre': r.get('nombre')} for r in rows]
        except Exception:
            logging.exception('Error obteniendo usuarios admin')
            return []
