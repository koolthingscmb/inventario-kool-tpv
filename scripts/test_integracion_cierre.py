"""Test de integración para validar que close_day persiste total_web correctamente.

Flujo:
- Limpia tickets no cerrados de hoy
- Inserta un ticket de prueba (total=10.0, forma_pago='WEB')
- Llama a close_day(tipo='Z')
- Consulta la última fila de cierres_caja e imprime todas las columnas
- Comprueba si total_web == 10.0
"""
from datetime import datetime
import sqlite3
import sys
import os

# adjust path to import database module
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import connect, DB_PATH, close_day


def run_test():
    fecha = datetime.now().date().isoformat()
    conn = connect()
    cur = conn.cursor()
    try:
        # 1. Limpiar: borrar tickets de hoy que no estén cerrados
        cur.execute("DELETE FROM tickets WHERE date(created_at)=? AND (cierre_id IS NULL)", (fecha,))
        conn.commit()

        # 2. Venta de prueba: insertar ticket manual
        created_at = datetime.now().isoformat()
        cur.execute('''
            INSERT INTO tickets (created_at, total, cajero, forma_pago, pagado, cambio, cliente, ticket_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (created_at, 10.0, 'TEST_USER', 'WEB', 10.0, 0.0, None, 999999))
        conn.commit()

        # 3. Ejecutar cierre
        resumen = close_day(fecha=fecha, tipo='Z')
        print('close_day returned:', resumen)

        # 4. Verificación: seleccionar última fila de cierres_caja
        cur.execute('PRAGMA table_info(cierres_caja)')
        cols = [r[1] for r in cur.fetchall()]
        cur.execute('SELECT * FROM cierres_caja ORDER BY id DESC LIMIT 1')
        row = cur.fetchone()
        if row is None:
            print('❌ FALLO: No hay filas en cierres_caja')
            return 2
        print('\nColumnas en cierres_caja:')
        for c, v in zip(cols, row):
            print(f"- {c}: {v}")

        # 5. Comparación
        # find index for total_web if present
        if 'total_web' in cols:
            idx = cols.index('total_web')
            total_web = float(row[idx] or 0.0)
            if abs(total_web - 10.0) < 1e-6:
                print('\n✅ INTEGRACIÓN CORRECTA')
                return 0
            else:
                print('\n❌ FALLO: El cierre sigue sin persistir la Web (total_web=', total_web, ')')
                return 1
        else:
            print('\n❌ FALLO: La columna total_web no existe en cierres_caja')
            return 3
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)
