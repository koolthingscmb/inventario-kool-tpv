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

    def validate_admin_password(self, password: str):
        """Valida contraseña contra CUALQUIER usuario con rol='admin'.

        Args:
            password: Contraseña en texto plano

        Returns:
            Tuple `(is_valid: bool, user_obj: dict | None)` donde `user_obj` tiene
            al menos `id` y `nombre` del admin autenticado. Mantiene compatibilidad
            con consumidores que solo evaluaban truthiness (devuelven tuple, que
            es truthy cuando is_valid True).
        """
        try:
            # Hash del password ingresado
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            # Buscar usuarios admin
            query = """
                SELECT id, nombre, password
                FROM usuarios
                WHERE LOWER(rol) = 'admin'
            """

            admins = self.db.fetch_all(query) or []

            if not admins:
                logging.warning('No hay usuarios admin en la BD')
                return (False, None)

            # Verificar si alguno coincide
            for admin in admins:
                try:
                    # fetch_all devuelve tuplas/Rows: índices 0=id, 1=nombre, 2=password
                    stored_hash = admin[2] if len(admin) > 2 else ''
                    admin_id = admin[0] if len(admin) > 0 else None
                    admin_nombre = admin[1] if len(admin) > 1 else 'desconocido'

                    if stored_hash and stored_hash.lower() == password_hash.lower():
                        user_obj = {'id': admin_id, 'nombre': admin_nombre}
                        logging.info('Autenticación admin exitosa para: %s', admin_nombre)
                        return (True, user_obj)
                except Exception:
                    logging.exception('Error procesando admin en validación')
                    continue

            logging.warning('Password admin incorrecto')
            return (False, None)

        except Exception:
            logging.exception('Error validando password admin')
            return (False, None)

    def get_admin_users(self) -> List[Dict[str, Any]]:
        """Obtener lista de usuarios admin (sin passwords).

        Returns:
            Lista de dicts con id y nombre
        """
        try:
            query = """
                SELECT id, nombre
                FROM usuarios
                WHERE LOWER(rol) = 'admin'
            """
            rows = self.db.fetch_all(query) or []
            # Normalizar salida: solo id y nombre
            return [{'id': r[0] if len(r) > 0 else None, 'nombre': r[1] if len(r) > 1 else None} for r in rows]
        except Exception:
            logging.exception('Error obteniendo usuarios admin')
            return []

    def validate_user_password(self, user_id: int, password: str) -> bool:
        """Valida contraseña de un usuario específico.

        Args:
            user_id: ID del usuario en tabla usuarios
            password: Contraseña en texto plano

        Returns:
            True si password correcto, False si no
        """
        try:
            # Hash del password ingresado
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            # Obtener hash almacenado para este usuario
            query = "SELECT password FROM usuarios WHERE id = ?"
            row = self.db.fetch_one(query, (user_id,))

            if not row:
                logging.warning(f'Usuario {user_id} no encontrado en BD')
                return False

            # fetch_one devuelve tupla/Row: acceder por índice
            stored_hash = row[0] if len(row) > 0 else ''

            if not stored_hash:
                logging.warning(f'Usuario {user_id} tiene password vacío')
                return False

            # Comparar hashes (case-insensitive)
            return password_hash.lower() == stored_hash.lower()

        except Exception:
            logging.exception(f'Error validando password para usuario {user_id}')
            return False
