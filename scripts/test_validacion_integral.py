"""
Script de validación integral del flujo de venta.

Resetea cliente, simula venta, valida persistencia y cálculos.
Muestra tabla comparativa en terminal.
"""
import sys
from pathlib import Path
from decimal import Decimal, ROUND_DOWN
from datetime import datetime

# Añadir repo al path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.ticket_service import save_ticket
from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService

# ============================================================================
# CONFIGURACIÓN DEL TEST
# ============================================================================

DB_PATH = repo_root / "kool_tpv" / "base_datos" / "kool_bd.db"
CLIENTE_ID = 1  # Ajustar según BD
CAJERO = "TEST_CAJERO"

# Productos de prueba (ajustar IDs según tu BD)
PRODUCTOS_TEST = [
    {'id': 2, 'nombre': 'MRK-Llavero', 'pvp': '3.90', 'tipo_iva': 21, 'cantidad': 2},
    {'id': 1, 'nombre': 'BK-Yihad Butleriana', 'pvp': '10.95', 'tipo_iva': 4, 'cantidad': 1}
]

# Canje de puntos (0 para test sin canje)
PUNTOS_CANJEAR = Decimal('0.00')


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def resetear_cliente(db: Database, cliente_id: int):
    """Resetear cliente a estado inicial (0 puntos, nivel NULL)."""
    print(f"\n🔄 Reseteando cliente {cliente_id}…")
    try:
        db.execute_query(
            """
            UPDATE clientes SET
                tesoro_total = 0.0,
                tesoro_historico = 0.0,
                tesoro_gastado_total = 0.0,
                id_nivel = NULL
            WHERE id = ?
            """,
            (cliente_id,),
        )
        # execute_query commits automatically in Database wrapper
        print("✅ Cliente reseteado a 0")
    except Exception as e:
        print(f"❌ Error reseteando cliente: {e}")
        raise


def obtener_stock_inicial(db: Database, producto_id: int):
    """Obtener stock y ventas antes de la venta."""
    row = db.fetch_one("SELECT stock_actual, ventas_totales FROM productos WHERE id = ?", (producto_id,))
    if row:
        return {'stock': row[0] or 0, 'ventas': row[1] or 0}
    return {'stock': 0, 'ventas': 0}


def calcular_esperado(productos, puntos_canjeados, porcentaje_fide=Decimal('5')):
    """Calcular valores esperados según reglas de negocio."""
    subtotal = Decimal('0')
    iva_21 = Decimal('0')
    iva_4 = Decimal('0')

    for prod in productos:
        pvp = Decimal(str(prod['pvp']))
        cant = Decimal(str(prod['cantidad']))
        tipo_iva = int(prod['tipo_iva'])

        # Precio sin IVA
        factor_iva = Decimal('1') + (Decimal(tipo_iva) / Decimal('100'))
        precio_sin_iva = (pvp / factor_iva).quantize(Decimal('0.01'), ROUND_DOWN)
        iva_linea = (pvp - precio_sin_iva) * cant

        subtotal += precio_sin_iva * cant

        if tipo_iva == 21:
            iva_21 += iva_linea
        elif tipo_iva == 4:
            iva_4 += iva_linea

    # Truncar
    subtotal = subtotal.quantize(Decimal('0.01'), ROUND_DOWN)
    iva_21 = iva_21.quantize(Decimal('0.01'), ROUND_DOWN)
    iva_4 = iva_4.quantize(Decimal('0.01'), ROUND_DOWN)
    total_iva = (iva_21 + iva_4).quantize(Decimal('0.01'), ROUND_DOWN)
    total = (subtotal + total_iva).quantize(Decimal('0.01'), ROUND_DOWN)

    # Puntos ganados: porcentaje sobre neto pagado (después de canje)
    neto_pagado = total - Decimal(puntos_canjeados)
    if neto_pagado < 0:
        neto_pagado = Decimal('0')

    factor_pago = (neto_pagado / total) if total > 0 else Decimal('0')
    puntos_ganados = (subtotal * (porcentaje_fide / Decimal('100')) * factor_pago).quantize(Decimal('0.01'), ROUND_DOWN)

    return {
        'subtotal': subtotal,
        'iva_21': iva_21,
        'iva_4': iva_4,
        'total_iva': total_iva,
        'total': total,
        'puntos_ganados': puntos_ganados
    }


def imprimir_comparacion(esperado: dict, real: dict, titulo: str):
    """Imprimir tabla comparativa compacta."""
    print('\n' + '=' * 60)
    print(f" {titulo}")
    print('=' * 60)
    print(f"{'Campo':<25} | {'Esperado':>12} | {'Real':>12} | {'OK?':<5}")
    print('-' * 60)

    for campo, valor_esp in esperado.items():
        valor_real = real.get(campo, 'N/A')
        match = '✅' if str(valor_esp) == str(valor_real) else '❌'
        print(f"{campo:<25} | {str(valor_esp):>12} | {str(valor_real):>12} | {match}")
    print('=' * 60 + '\n')


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================


def main():
    print('\n' + '=' * 60)
    print(' VALIDACIÓN INTEGRAL - KOOL TPV V2')
    print('=' * 60)

    # Conectar a BD
    db = Database(str(DB_PATH))
    db.connect()
    print(f"✅ Conectado a: {DB_PATH}")

    # 1. Resetear cliente
    resetear_cliente(db, CLIENTE_ID)

    # 2. Obtener stock/ventas inicial
    stocks_inicial = {}
    for prod in PRODUCTOS_TEST:
        stocks_inicial[prod['id']] = obtener_stock_inicial(db, prod['id'])

    print('\n📦 Stock inicial:')
    for pid, data in stocks_inicial.items():
        print(f"   Producto {pid}: Stock={data['stock']}, Ventas={data['ventas']}")

    # 3. Calcular esperado
    esperado = calcular_esperado(PRODUCTOS_TEST, PUNTOS_CANJEAR)

    # 4. Simular venta con CarritoService
    print('\n🛒 Simulando venta...')
    carrito = CarritoService()

    # Añadir items
    for prod in PRODUCTOS_TEST:
        for _ in range(int(prod['cantidad'])):
            carrito.add_item(prod)

    # Aplicar canje si procede
    if PUNTOS_CANJEAR > 0:
        carrito.set_puntos_canjeados(PUNTOS_CANJEAR)

    # Asignar cliente
    cliente_data = db.fetch_one("SELECT id, nombre, tesoro_total, id_nivel FROM clientes WHERE id = ?", (CLIENTE_ID,))
    if cliente_data:
        carrito.set_cliente({
            'id': cliente_data[0],
            'nombre': cliente_data[1],
            'tesoro_total': cliente_data[2],
            'id_nivel': cliente_data[3]
        })

    resumen = carrito.get_resumen_financiero()

    # 5. Persistir con save_ticket
    print('💾 Guardando ticket...')
    fidelizacion = FidelizacionService(db)

    try:
        res = save_ticket(
            db,
            carrito.get_items(),
            resumen,
            esperado['total'],
            cajero=CAJERO,
            cliente='Eduard',
            cliente_id=CLIENTE_ID,
            forma_pago='Efectivo',
            importe_efectivo=esperado['total'],
            importe_tarjeta=Decimal('0'),
            carrito_service=carrito,
            fidelizacion_service=fidelizacion
        )
        # soportar distintos retornos
        if isinstance(res, (list, tuple)) and len(res) >= 2:
            ticket_id, num_ticket = res[0], res[1]
        else:
            ticket_id = res
            num_ticket = None
        print(f"✅ Ticket guardado: ID={ticket_id}, NUM={num_ticket}")
    except Exception as e:
        print(f"❌ ERROR guardando ticket: {e}")
        db.close_connection()
        sys.exit(1)

    # 6. Validar ticket en BD
    print('\n🔍 Validando persistencia...')

    ticket = db.fetch_one("SELECT total, forma_pago, tesoro_ganado, tesoro_gastado FROM tickets WHERE id = ?", (ticket_id,))
    real_ticket = {
        'total': Decimal(str(ticket[0])),
        'forma_pago': ticket[1],
        'tesoro_ganado': Decimal(str(ticket[2])),
        'tesoro_gastado': Decimal(str(ticket[3]))
    }

    esperado_ticket = {
        'total': esperado['total'],
        'forma_pago': 'Efectivo',
        'tesoro_ganado': esperado['puntos_ganados'],
        'tesoro_gastado': PUNTOS_CANJEAR
    }

    imprimir_comparacion(esperado_ticket, real_ticket, "VALIDACIÓN TICKET")

    # 7. Validar líneas
    print('📝 Validando líneas del ticket...')
    lines = db.fetch_all("SELECT sku, nombre, cantidad, precio, iva FROM ticket_lines WHERE ticket_id = ?", (ticket_id,))
    print(f"   Líneas encontradas: {len(lines)}")
    esperado_lines = sum(int(p['cantidad']) for p in PRODUCTOS_TEST)
    if len(lines) == esperado_lines:
        print(f"   ✅ Cantidad de líneas correcta ({esperado_lines})")
    else:
        print(f"   ❌ Se esperaban {esperado_lines} líneas, se encontraron {len(lines)}")

    # 8. Validar stock y ventas
    print('\n📦 Validando stock y ventas...')
    for prod in PRODUCTOS_TEST:
        pid = prod['id']
        inicial = stocks_inicial[pid]
        actual = obtener_stock_inicial(db, pid)

        stock_exp = inicial['stock'] - prod['cantidad']
        ventas_exp = inicial['ventas'] + prod['cantidad']

        stock_ok = '✅' if actual['stock'] == stock_exp else '❌'
        ventas_ok = '✅' if actual['ventas'] == ventas_exp else '❌'

        print(f"   Producto {pid} ({prod['nombre']}):")
        print(f"      Stock:  {inicial['stock']} → {actual['stock']} (esperado {stock_exp}) {stock_ok}")
        print(f"      Ventas: {inicial['ventas']} → {actual['ventas']} (esperado {ventas_exp}) {ventas_ok}")

    # 9. Validar cliente
    print('\n👤 Validando cliente...')
    cliente_after = db.fetch_one("SELECT tesoro_total, tesoro_historico, tesoro_gastado_total, id_nivel FROM clientes WHERE id = ?", (CLIENTE_ID,))

    real_cliente = {
        'tesoro_total': Decimal(str(cliente_after[0])),
        'tesoro_historico': Decimal(str(cliente_after[1])),
        'tesoro_gastado_total': Decimal(str(cliente_after[2])),
        'id_nivel': cliente_after[3]
    }

    esperado_cliente = {
        'tesoro_total': esperado['puntos_ganados'] - PUNTOS_CANJEAR,
        'tesoro_historico': esperado['puntos_ganados'],
        'tesoro_gastado_total': PUNTOS_CANJEAR,
        'id_nivel': 1  # Forastero (gasto_minimo=0) - ajustar si necesario
    }

    imprimir_comparacion(esperado_cliente, real_cliente, "VALIDACIÓN CLIENTE")

    # 10. Resumen final
    print('\n' + '=' * 60)
    print('  RESUMEN FINAL')
    print('=' * 60)
    print('✅ Script completado (revisar salidas para posibles discrepancias)')
    print(f"📊 Ticket #{num_ticket} procesado")
    print(f"💰 Total venta: {esperado['total']} €")
    print(f"⭐ Puntos ganados: {esperado['puntos_ganados']}")
    print('=' * 60 + '\n')

    db.close_connection()


if __name__ == '__main__':
    main()
