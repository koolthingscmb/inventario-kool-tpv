"""Servicio de usuarios (cajeros) - CRUD y utilidades."""
import logging
from datetime import datetime
import hashlib
from kool_tpv.base_datos.audit_service import AuditService


class UsuarioService:
    def __init__(self, db):
        self.db = db
        self.audit = AuditService(db)

    def get_all_usuarios(self) -> list:
        try:
            # Tabla `usuarios` en la BD contiene las columnas:
            # id, nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets
            query = """
                SELECT id, nombre, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets,
                       created_at, telefono, email, permiso_cajon, ui_color, banner_path
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
                    'permiso_cajon': int(r[10] or 0),
                    'ui_color': r[11] or '#00FF00',
                    'banner_path': r[12] or None,
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
            
            # Map columns by name if possible, or position (id=0, nombre=1, password=2, rol=3, ..., ui_color=12, banner_path=13)
            # The schema order is: id, nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets, created_at, telefono, email, permiso_cajon, ui_color, banner_path
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
                'permiso_cajon': int(row[11]) if len(row) > 11 and row[11] is not None else 0,
                'ui_color': row[12] if len(row) > 12 else '#00FF00',
                'banner_path': row[13] if len(row) > 13 else None,
            }
        except Exception:
            logging.exception(f'Error obteniendo usuario {user_id}')
            return None

    def save_usuario(self, nombre, email='', telefono='', password='', rol='Cajero',
                     permiso_cierre=0, permiso_descuento=0, permiso_devolucion=0, permiso_tickets=0,
                     permiso_cajon=0, ui_color='#00FF00', banner_path=None, responsable_id=None) -> bool:
        try:
            if not nombre:
                logging.warning('UsuarioService.save_usuario: nombre vacío')
                return False
            password_hash = self.hash_password(password or '')

            try:
                from kool_tpv.utils.time_utils import now_utc_str
                created_at = now_utc_str()
            except Exception:
                created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
            
            with self.db.transaction() as cur:
                query = """
                    INSERT INTO usuarios
                    (nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_tickets, created_at, telefono, email, permiso_cajon, ui_color, banner_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cur.execute(query, (nombre, password_hash, rol, int(permiso_cierre), int(permiso_descuento), int(permiso_devolucion), int(permiso_tickets), created_at, telefono, email, int(permiso_cajon), ui_color, banner_path))
                new_user_id = cur.lastrowid

                # Auditoría de creación
                self.audit.registrar(
                    entidad='usuarios',
                    entidad_id=new_user_id,
                    accion='CREACION_USUARIO',
                    usuario_id=responsable_id,
                    datos_nuevos=f"Usuario: {nombre} - Rol: {rol}",
                    cur=cur
                )
            return True
        except Exception:
            logging.exception('Error guardando usuario')
            return False

    def update_usuario(self, user_id, responsable_id=None, **kwargs) -> bool:
        try:
            if not user_id:
                return False

            # Prepare allowed fields
            allowed = ['nombre', 'email', 'telefono', 'password', 'rol',
                       'permiso_cierre', 'permiso_descuento', 'permiso_devolucion', 'permiso_tickets',
                       'permiso_cajon', 'ui_color', 'banner_path']

            updates = []
            params = []
            cambios_audit = []
            
            # Obtener datos antiguos para auditoría
            old_data = self.get_usuario(user_id)
            if not old_data:
                return False

            for k, v in kwargs.items():
                if k not in allowed:
                    continue
                
                old_val = old_data.get(k)
                
                if k == 'password':
                    # If empty string provided -> skip updating password
                    if not v:
                        continue
                    new_hash = self.hash_password(v)
                    if new_hash != old_val:
                        updates.append(f"{k} = ?")
                        params.append(new_hash)
                        cambios_audit.append("password cambiado")
                    continue

                if k.startswith('permiso_'):
                    v = int(bool(v))
                
                if str(v) != str(old_val):
                    updates.append(f"{k} = ?")
                    params.append(v)
                    cambios_audit.append(f"{k}: {old_val} -> {v}")

            if not updates:
                logging.debug('UsuarioService.update_usuario: nada que actualizar')
                return True

            params.append(user_id)
            query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
            
            with self.db.transaction() as cur:
                cur.execute(query, tuple(params))
                
                # Auditoría de actualización
                self.audit.registrar(
                    entidad='usuarios',
                    entidad_id=user_id,
                    accion='ACTUALIZACION_USUARIO',
                    usuario_id=responsable_id,
                    datos_nuevos=" | ".join(cambios_audit),
                    cur=cur
                )
            return True
        except Exception:
            logging.exception(f'Error actualizando usuario {user_id}')
            return False

    def delete_usuario(self, user_id: int, responsable_id=None) -> bool:
        try:
            # Obtener nombre para auditoría antes de borrar
            user = self.get_usuario(user_id)
            nombre = user.get('nombre', 'Desconocido') if user else 'Desconocido'
            
            with self.db.transaction() as cur:
                query = "DELETE FROM usuarios WHERE id = ?"
                cur.execute(query, (user_id,))
                
                # Auditoría de eliminación
                self.audit.registrar(
                    entidad='usuarios',
                    entidad_id=user_id,
                    accion='ELIMINACION_USUARIO',
                    usuario_id=responsable_id,
                    datos_nuevos=f"Usuario eliminado: {nombre}",
                    cur=cur
                )
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
