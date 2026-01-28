#!/usr/bin/env python3
"""
scripts/migracion_usuarios.py

Crear la tabla `usuarios` y añadir usuarios iniciales de forma idempotente.
"""
from database import connect
import hashlib


def hash_password(plain: str) -> str:
    """Return SHA-256 hex digest for the given plain password."""
    if plain is None:
        plain = ''
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()


def main():
    conn = connect()
    cur = conn.cursor()
    added = []
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                password TEXT,
                rol TEXT,
                permiso_cierre INTEGER DEFAULT 0,
                permiso_descuento INTEGER DEFAULT 0,
                permiso_devolucion INTEGER DEFAULT 0,
                permiso_configuracion INTEGER DEFAULT 0
            )
        ''')

        # check if table empty
        cur.execute('SELECT COUNT(*) FROM usuarios')
        r = cur.fetchone()
        count = r[0] if r and r[0] is not None else 0
        if count == 0:
            # insert initial users
            users = [
                # EGON: admin, all permissions = 1
                ('EGON', '1234', 'admin', 1, 1, 1, 1),
                # Andrea: empleado, permiso_cierre=1, permiso_descuento=1, others 0
                ('Andrea', '4321', 'empleado', 1, 1, 0, 0),
            ]
            for nombre, pwd, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion in users:
                hp = hash_password(pwd)
                cur.execute(
                    'INSERT INTO usuarios (nombre, password, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion) VALUES (?,?,?,?,?,?,?)',
                    (nombre, hp, rol, permiso_cierre, permiso_descuento, permiso_devolucion, permiso_configuracion)
                )
                added.append(nombre)
            conn.commit()
        else:
            # table not empty — do nothing
            pass

    except Exception as e:
        print('Error durante la migración de usuarios:', e)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    if added:
        print('Usuarios añadidos:', ', '.join(added))
    else:
        print('No se añadieron usuarios: la tabla ya contiene datos o no se requirió inserción.')


if __name__ == '__main__':
    main()
