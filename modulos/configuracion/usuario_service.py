from typing import Optional, List, Dict, Any
import hashlib

from database import connect


class UsuarioService:
    @staticmethod
    def _hash_password(plain: Optional[str]) -> str:
        if plain is None:
            plain = ''
        return hashlib.sha256(plain.encode('utf-8')).hexdigest()

    @classmethod
    def listar_usuarios(cls) -> List[Dict[str, Any]]:
        conn = None
        cur = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT id, nombre, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets FROM usuarios'
            )
            rows = cur.fetchall()
            usuarios = []
            for r in rows:
                usuarios.append({
                    'id': r[0],
                    'nombre': r[1],
                    'rol': r[2],
                    'permiso_cierre': bool(r[3]),
                    'permiso_descuento': bool(r[4]),
                    'permiso_devolucion': bool(r[5]),
                    'permiso_configuracion': bool(r[6]),
                    'permiso_tickets': bool(r[7]),
                })
            return usuarios
        except Exception:
            return []
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    @classmethod
    def obtener_por_id(cls, usuario_id: int) -> Optional[Dict[str, Any]]:
        conn = None
        cur = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(
                'SELECT id, nombre, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets FROM usuarios WHERE id=?',
                (usuario_id,)
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                'id': r[0],
                'nombre': r[1],
                'rol': r[2],
                'permiso_cierre': bool(r[3]),
                'permiso_descuento': bool(r[4]),
                'permiso_devolucion': bool(r[5]),
                'permiso_configuracion': bool(r[6]),
                'permiso_tickets': bool(r[7]),
            }
        except Exception:
            return None
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    @classmethod
    def guardar_usuario(cls, datos: Dict[str, Any]) -> Optional[int]:
        conn = None
        cur = None
        try:
            nombre = datos.get('nombre')
            if not nombre:
                return None

            rol = datos.get('rol')

            permiso_cierre = 1 if datos.get('permiso_cierre') else 0
            permiso_descuento = 1 if datos.get('permiso_descuento') else 0
            permiso_devolucion = 1 if datos.get('permiso_devolucion') else 0
            permiso_configuracion = 1 if datos.get('permiso_configuracion') else 0
            # permiso_tickets: default depends on role (admin -> 1, empleado -> 0) unless provided
            if 'permiso_tickets' in datos:
                permiso_tickets = 1 if datos.get('permiso_tickets') else 0
            else:
                try:
                    permiso_tickets = 1 if (str(rol or '').lower() == 'admin') else 0
                except Exception:
                    permiso_tickets = 0

            password_plain = datos.get('password')
            conn = connect()
            cur = conn.cursor()

            if 'id' in datos and datos.get('id'):
                # update
                if password_plain:
                    hashed = cls._hash_password(password_plain)
                    cur.execute(
                        'UPDATE usuarios SET nombre=?, password=?, rol=?, permiso_cierre=?, permiso_descuento=?, permiso_devolucion=?, permiso_configuracion=?, permiso_tickets=? WHERE id=?',
                        (nombre, hashed, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets, datos.get('id'))
                    )
                else:
                    cur.execute(
                        'UPDATE usuarios SET nombre=?, rol=?, permiso_cierre=?, permiso_descuento=?, permiso_devolucion=?, permiso_configuracion=?, permiso_tickets=? WHERE id=?',
                        (nombre, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets, datos.get('id'))
                    )
                conn.commit()
                return datos.get('id')
            else:
                # create
                hashed = cls._hash_password(password_plain or '')
                cur.execute(
                    'INSERT INTO usuarios (nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets) VALUES (?,?,?,?,?,?,?,?)',
                    (nombre, hashed, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion, permiso_tickets)
                )
                conn.commit()
                return cur.lastrowid

        except Exception:
            return None
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    @classmethod
    def eliminar_usuario(cls, usuario_id: int) -> bool:
        conn = None
        cur = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('DELETE FROM usuarios WHERE id=?', (usuario_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    @classmethod
    def verificar_credenciales(cls, nombre: str, password: Optional[str]):
        conn = None
        cur = None
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('SELECT id, nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion FROM usuarios WHERE nombre=?', (nombre,))
            r = cur.fetchone()
            if not r:
                return None
            stored_hash = r[2] or ''
            candidate_hash = cls._hash_password(password)
            if stored_hash == candidate_hash:
                return {
                    'id': r[0],
                    'nombre': r[1],
                    'rol': r[3],
                    'permiso_cierre': bool(r[4]),
                    'permiso_descuento': bool(r[5]),
                    'permiso_devolucion': bool(r[6]),
                    'permiso_configuracion': bool(r[7]),
                }
            return None
        except Exception:
            return None
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
