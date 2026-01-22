#!/usr/bin/env python3
import sqlite3
from database import DB_PATH

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # ensure tables empty and sqlite_sequence cleared
    cur.execute('DELETE FROM ticket_lines')
    cur.execute('DELETE FROM tickets')
    cur.execute('DELETE FROM cierres')
    conn.commit()
    try:
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('ticket_lines','tickets','cierres')")
        conn.commit()
    except Exception:
        pass
    # compute next_ticket_no and insert as patched code
    cur.execute('SELECT COALESCE(MAX(ticket_no),0)+1 FROM tickets')
    next_ticket_no = cur.fetchone()[0] or 1
    cur.execute('INSERT INTO tickets (created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio) VALUES (?,?,?,?,?,?,?,?)', ('2026-01-22T13:00:00', 9.9, 'EGON', None, next_ticket_no, 'EFECTIVO', 10.0, 0.1))
    conn.commit()
    cur.execute('SELECT id, ticket_no FROM tickets')
    rows = cur.fetchall()
    cur.execute('SELECT name, seq FROM sqlite_sequence')
    seq = cur.fetchall()
    cur.close()
    conn.close()
    print('rows:', rows)
    print('sqlite_sequence:', seq)

if __name__ == '__main__':
    run()
