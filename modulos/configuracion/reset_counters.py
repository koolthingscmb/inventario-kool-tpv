"""Funciones para reiniciar contadores relacionados con tickets.

Este módulo expone una función segura y pequeña que borra las entradas
correspondientes en `sqlite_sequence` para que los contadores AUTOINCREMENT
se reinicien (útil en pruebas). No borra datos por defecto.
"""
from database import connect


def reset_ticket_counters():
    """Eliminar filas de `sqlite_sequence` para tablas de tickets.

    Esto hace que, si las tablas están vacías, el siguiente `INSERT`
    vuelva a usar el id 1. No borra datos de tablas; para pruebas más
    agresivas usar `scripts/clear_tickets.py`.
    """
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('ticket_lines','tickets','cierres')")
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
