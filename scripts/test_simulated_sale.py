#!/usr/bin/env python3
from modulos.tpv.ticket_service import TicketService
from modulos.impresion.ticket_generator import generar_ticket
from modulos.impresion.print_service import ImpresionService
from database import connect

def main():
    conn = connect(); cur = conn.cursor()
    cur.execute('''SELECT p.id, p.sku, p.nombre, p.tipo_iva, pr.pvp FROM productos p JOIN precios pr ON p.id=pr.producto_id WHERE pr.activo=1 ORDER BY p.id LIMIT 3''')
    rows = cur.fetchall()
    cur.close(); conn.close()
    if not rows:
        raise SystemExit('No products found in DB')

    cantidades = [1, 2, 1]
    lineas = []
    for r, qty in zip(rows, cantidades):
        pid, sku, nombre, iva, pvp = r
        lineas.append({'sku': sku, 'nombre': nombre, 'cantidad': qty, 'precio': float(pvp), 'iva': float(iva)})

    total = sum(l['cantidad'] * l['precio'] for l in lineas)
    datos_ticket = {
        'total': float(total),
        'cajero': 'SIM_TEST',
        'cliente': 'CLIENTE TEST',
        'forma_pago': 'EFECTIVO',
        'pagado': float(round(total) + 1),
        'cambio': float((round(total) + 1) - total)
    }

    svc = TicketService()
    print('Saving ticket...')
    tid = svc.guardar_ticket(datos_ticket, lineas)
    print('Saved ticket id:', tid)
    if not tid:
        raise SystemExit('Failed to save ticket')

    full = svc.obtener_ticket_completo(tid)

    ticket_text = generar_ticket(full['lineas'], efectivo=full['meta'].get('pagado') or 0.0, cambio=full['meta'].get('cambio') or 0.0, cajero=full['meta'].get('cajero'), ticket_id=tid, width=50, metodo_pago=full['meta'].get('forma_pago'))

    print('\n--- TICKET TEXT (to be printed) ---\n')
    print(ticket_text)
    print('--- END TICKET TEXT ---\n')

    imp = ImpresionService()
    print('DET: _printer_available =', getattr(imp, '_printer_available', None))
    ok = imp.imprimir_ticket(ticket_text, abrir_cajon=True, no_wrap=True)
    print('imprimir_ticket returned ->', ok)

if __name__ == '__main__':
    main()
