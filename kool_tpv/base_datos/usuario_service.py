"""Servicio de usuarios (cajeros) - CRUD y utilidades."""
import logging
from datetime import datetime
import hashlib


class UsuarioService:
    def __init__(self, db):
        self.db = db

    def get_all_usuarios(self) -> list:
        try:
            # Tabla `usuarios` en la BD contiene las columnas:
            # id, nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets
            query = """
                SELECT id, nombre, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets,
                       created_at, telefono, email
                FROM usuarios
                ORDER BY nombre
            """
            rows = self.db.fetch_all(query) or []
            usuarios = []
            for r in rows:
                usuarios.append({
                    'id': r[0],
                    'nombre': r[1] or '',
                    'rol': r[2] or '',
                    'permiso_cierre': int(r[3] or 0),
                    'permiso_descuento': int(r[4] or 0),
                    'permiso_devolucion': int(r[5] or 0),
                    'permiso_tickets': int(r[6] or 0),
                    'created_at': r[7] or None,
                    'telefono': r[8] or '',
                    'email': r[9] or '',
                })
            return usuarios
        except Exception:
            logging.exception('Error obteniendo usuarios')
            return []

    def get_usuario(self, user_id: int) -> dict:
        try:
            query = "SELECT * FROM usuarios WHERE id = ?"
            row = self.db.fetch_one(query, (user_id,))
            if not row:
                return None
            # Map columns according to actual schema (including optional email/telefono/created_at)
            return {
                'id': row[0],
                'nombre': row[1] or '',
                'password': row[2] or '',
                'rol': row[3] or '',
                'permiso_cierre': int(row[4] or 0),
                'permiso_descuento': int(row[5] or 0),
                'permiso_devolucion': int(row[6] or 0),
                'permiso_tickets': int(row[7] or 0),
                'created_at': row[8] if len(row) > 8 else None,
                'telefono': row[9] if len(row) > 9 else '',
                'email': row[10] if len(row) > 10 else '',
            }
        except Exception:
            logging.exception(f'Error obteniendo usuario {user_id}')
            return None

    def save_usuario(self, nombre, email='', telefono='', password='', rol='Cajero',
                     permiso_cierre=0, permiso_descuento=0, permiso_devolucion=0, permiso_tickets=0) -> bool:
        try:
            if not nombre:
                logging.warning('UsuarioService.save_usuario: nombre vacío')
                return False
            password_hash = self.hash_password(password or '')

            created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
            query = """
                INSERT INTO usuarios
                (nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets, created_at, telefono, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db.execute_query(query, (nombre, password_hash, rol, int(permiso_cierre), int(permiso_descuento), int(permiso_devolucion), int(permiso_tickets), created_at, telefono, email))
            return True
        except Exception:
            logging.exception('Error guardando usuario')
            return False

    def update_usuario(self, user_id, **kwargs) -> bool:
        try:
            if not user_id:
                return False

            # Prepare allowed fields
            allowed = ['nombre', 'email', 'telefono', 'password', 'rol',
                       'permiso_cierre', 'permiso_descuento', 'permiso_devolucion', 'permiso_tickets']

            updates = []
            params = []
            for k, v in kwargs.items():
                if k not in allowed:
                    continue
                if k == 'password':
                    # If empty string provided -> skip updating password
                    if not v:
                        continue
                    v = self.hash_password(v)
                if k.startswith('permiso_'):
                    v = int(bool(v))
                updates.append(f"{k} = ?")
                params.append(v)

            if not updates:
                logging.debug('UsuarioService.update_usuario: nada que actualizar')
                return True

            params.append(user_id)
            query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
            self.db.execute_query(query, tuple(params))
            return True
        except Exception:
            logging.exception(f'Error actualizando usuario {user_id}')
            return False

    def delete_usuario(self, user_id: int) -> bool:
        try:
            query = "DELETE FROM usuarios WHERE id = ?"
            self.db.execute_query(query, (user_id,))
            return True
        except Exception:
            logging.exception(f'Error eliminando usuario {user_id}')
            return False

    def hash_password(self, password: str) -> str:
        try:
            return hashlib.sha256(password.encode('utf-8')).hexdigest()
        except Exception:
            logging.exception('Error hasheando password')
            return ''
