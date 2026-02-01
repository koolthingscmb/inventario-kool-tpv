#!/usr/bin/env python3
"""Genera un ticket real aleatorio usando la BD del proyecto y lo muestra.

Inserta en `tickets` y `ticket_lines` siguiendo el esquema de `database.py`.
Si existe `modulos.tpv.ticket_service.TicketService` lo usa, si no hace INSERT directo.
"""
import os
import sys
import random
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import connect
try:
    from modulos.impresion.ticket_generator import generar_ticket
except Exception:
    generar_ticket = None


def pick_products(conn, n):
    cur = conn.cursor()
    # try to get products with active price
    try:
        cur.execute("SELECT p.id, p.nombre, p.sku, pr.pvp, p.tipo_iva FROM productos p JOIN precios pr ON pr.producto_id=p.id AND pr.activo=1 ORDER BY RANDOM() LIMIT ?", (n,))
        rows = cur.fetchall()
        if rows:
            return rows
    except Exception:
        pass
    # fallback to productos only
    try:
        cur.execute("SELECT id, nombre, sku, NULL as pvp, tipo_iva FROM productos ORDER BY RANDOM() LIMIT ?", (n,))
        return cur.fetchall()
    except Exception:
        return []


def next_ticket_no(conn):
    cur = conn.cursor()
    try:
        cur.execute('SELECT MAX(ticket_no) FROM tickets')
        r = cur.fetchone()
        return (r[0] or 0) + 1
    except Exception:
        return None


def main():
    conn = connect()
    conn.row_factory = None
    cur = conn.cursor()

    productos = pick_products(conn, random.randint(1, 5))
    if not productos:
        print('No se encontraron productos en la base de datos.')
        return

    # intentar elegir un cajero desde tickets existentes (campo cajero)
    cajero = 'Desconocido'
    try:
        cur.execute("SELECT cajero FROM tickets WHERE cajero IS NOT NULL ORDER BY RANDOM() LIMIT 1")
        r = cur.fetchone()
        if r:
            cajero = r[0]
    except Exception:
        pass

    lineas = []
    total = 0.0
    for p in productos:
        # row may be tuple: (id, nombre, sku, pvp, tipo_iva)
        try:
            pid = p[0]
            nombre = p[1] or ''
            sku = p[2] if len(p) > 2 else None
            precio = float(p[3]) if (len(p) > 3 and p[3] is not None) else round(random.uniform(1.0, 20.0), 2)
            iva = float(p[4]) if (len(p) > 4 and p[4] is not None) else 21.0
        except Exception:
            pid = None
            nombre = str(p)
            sku = None
            precio = round(random.uniform(1.0, 20.0), 2)
            iva = 21.0
        cantidad = random.randint(1, 3)
        subtotal = round(precio * cantidad, 2)
        total += subtotal
        lineas.append({'sku': sku, 'nombre': nombre, 'cantidad': cantidad, 'precio': precio, 'iva': iva})

    total = round(total, 2)
    created_at = datetime.now().isoformat()

    # compute ticket_no
    ticket_no = next_ticket_no(conn)

    # insert ticket
    try:
        cur.execute('''INSERT INTO tickets (created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio) VALUES (?,?,?,?,?,?,?,?)''', (
            created_at, total, cajero, 'cliente_aleatorio', ticket_no, 'Efectivo', total, 0.0
        ))
        ticket_id = cur.lastrowid
        for li in lineas:
            try:
                cur.execute('''INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)''', (
                    ticket_id, li.get('sku'), li.get('nombre'), li.get('cantidad'), li.get('precio'), li.get('iva')
                ))
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        conn.rollback()
        print('Error insertando ticket:', e)
        return

    print(f'Ticket creado con id {ticket_id}, total {total:.2f}, cajero: {cajero}')

    # mostrar ticket real usando generar_ticket si está disponible
    if generar_ticket:
        try:
            # preparar carrito en formato que acepta generar_ticket: lista de dicts con nombre,cantidad,precio,iva
            carrito = [{'nombre': li['nombre'], 'cantidad': li['cantidad'], 'precio': li['precio'], 'iva': li['iva']} for li in lineas]
            texto = generar_ticket(carrito=carrito, efectivo=total, cambio=0.0, nombre_tienda='', cajero=cajero, ticket_id=ticket_id, width=50, metodo_pago='EFECTIVO')
            print('\n--- TICKET GENERADO (REAL) ---\n')
            print(texto)
            print('\n--- FIN TICKET ---\n')
        except Exception as e:
            print('Error generando ticket de texto:', e)
    else:
        print('\n--- TICKET SIMPLIFICADO ---\n')
        for li in lineas:
            print(f"{li['cantidad']} x {li['nombre']} @ {li['precio']:.2f} = {li['cantidad']*li['precio']:.2f}")
        print(f"\nTOTAL: {total:.2f}\nTicket id: {ticket_id}\nCajero: {cajero}\n")

    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


if __name__ == '__main__':
    main()
