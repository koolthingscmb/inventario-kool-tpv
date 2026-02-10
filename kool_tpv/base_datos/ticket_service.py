"""
Ticket persistence service.

Provides a function to save a ticket, its lines and update product stock/ventas
in a single atomic transaction using the `Database` wrapper.

This is intentionally minimal: it writes the fields required by the current
schema and logs warnings if stock goes negative.
"""
from datetime import datetime
import logging
from decimal import Decimal
from kool_tpv.modulos.clientes.fidelizacion_service import FidelizacionService


def save_ticket(db, carrito_items, resumen, efectivo, cajero=None, cliente=None, cliente_id=None, forma_pago='Efectivo', importe_efectivo=0.0, importe_tarjeta=0.0, descuento_data=None, carrito_service=None, fidelizacion_service=None):
    """
    Persist a ticket and its lines and update product stock/ventas.

    Args:
        db: Database wrapper (kool_tpv.base_datos.db_wrapper.Database) with .connection
        carrito_items: list of item dicts from CarritoService.get_items()
        resumen: dict returned by carrito_service.get_resumen_financiero()
        efectivo: Decimal or numeric amount given by customer
        cajero: optional cashier name
        cliente: optional client identifier/name
        forma_pago: payment method string

    Returns: (ticket_id, num_ticket)
    """
    if db is None or db.connection is None:
        raise RuntimeError('Database connection is not available')

    # Log which database file we're using to help diagnose GUI vs headless differences
    try:
        db_path = getattr(db, 'db_path', None) or getattr(db, 'database', None) or 'unknown'
        logging.info(f'Usando archivo de base de datos: {db_path}')
    except Exception:
        logging.exception('No se pudo obtener la ruta de la base de datos')
    conn = db.connection
    cur = conn.cursor()
    try:
        logging.info('Iniciando persistencia de ticket')
        # Begin explicit transaction
        cur.execute('BEGIN')

        # --- Calcular puntos de fidelización y puntos canjeados ---
        try:
            if fidelizacion_service is None:
                fidelizacion_service = FidelizacionService(db)
        except Exception:
            logging.exception('No se pudo instanciar FidelizacionService; se asumirá 0 puntos')
            fidelizacion_service = None

        puntos_gastados = Decimal('0')
        try:
            if carrito_service is not None and getattr(carrito_service, 'get_puntos_canjeados', None):
                puntos_gastados = carrito_service.get_puntos_canjeados() or Decimal('0')
        except Exception:
            logging.exception('Error obteniendo puntos canjeados del carrito; se asume 0')
            puntos_gastados = Decimal('0')

        puntos_ganados = Decimal('0')
        try:
            if fidelizacion_service is not None:
                puntos_ganados = fidelizacion_service.calcular_puntos_ganados(carrito_items, puntos_canjeados=puntos_gastados) or Decimal('0')
        except Exception:
            logging.exception('Error calculando puntos ganados; se asume 0')
            puntos_ganados = Decimal('0')

        # determine next num_ticket
        cur.execute('SELECT MAX(num_ticket) FROM tickets')
        row = cur.fetchone()
        last = row[0] if row and row[0] is not None else 0
        num_ticket = int(last) + 1

        created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
        # Use Decimal for monetary values to keep precision and avoid float rounding
        total = Decimal(str(resumen.get('total', '0')))

        # Extraer datos de descuento si existe
        descuento_euros = Decimal('0')
        descuento_tipo = None
        descuento_valor = None
        try:
            if descuento_data:
                try:
                    descuento_euros = Decimal(str(descuento_data.get('euros', 0)))
                except Exception:
                    descuento_euros = Decimal('0')
                try:
                    descuento_tipo = descuento_data.get('tipo')
                except Exception:
                    descuento_tipo = None
                try:
                    # guardar valor numérico (porcentaje o importe)
                    descuento_valor = float(descuento_data.get('valor')) if descuento_data.get('valor') is not None else None
                except Exception:
                    descuento_valor = None
        except Exception:
            logging.exception('Error procesando descuento_data; se usarán valores por defecto')

        # Determine breakdown of payments
        try:
            importe_efectivo_val = Decimal(str(importe_efectivo)) if importe_efectivo is not None else Decimal('0')
        except Exception:
            importe_efectivo_val = Decimal('0')
        try:
            importe_tarjeta_val = Decimal(str(importe_tarjeta)) if importe_tarjeta is not None else Decimal('0')
        except Exception:
            importe_tarjeta_val = Decimal('0')

        # If no explicit split provided, infer from forma_pago
        if (importe_efectivo_val == 0) and (importe_tarjeta_val == 0):
            if (forma_pago or '').strip().lower() == 'efectivo':
                importe_efectivo_val = total
            elif (forma_pago or '').strip().lower() in ('tarjeta', 'card', 'web'):
                importe_tarjeta_val = total

        # pagado remains as provided (efectivo param) when present, otherwise sum of parts
        if efectivo is None:
            pagado = importe_efectivo_val + importe_tarjeta_val
        else:
            pagado = Decimal(str(efectivo))

        cambio = pagado - total

        # insert ticket
        insert_ticket_q = (
            "INSERT INTO tickets (created_at, cajero, cliente, cliente_id, num_ticket, forma_pago, total, pagado, cambio, importe_efectivo, importe_tarjeta, descuento_euros, descuento_tipo, descuento_valor, tesoro_ganado, tesoro_gastado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        # Use provided cliente_id (if any) instead of hardcoded None
        cur.execute(
            insert_ticket_q,
            (
                created_at,
                cajero,
                cliente if cliente else None,
                cliente_id if cliente_id else None,
                num_ticket,
                forma_pago,
                str(total),
                str(pagado),
                str(cambio),
                str(importe_efectivo_val),
                str(importe_tarjeta_val),
                str(descuento_euros),
                descuento_tipo,
                descuento_valor,
                str(puntos_ganados),
                str(puntos_gastados),
            ),
        )
        ticket_id = cur.lastrowid

        # insert ticket lines and update product stock/ventas
        for item in carrito_items:
            prod_id = item.get('id')
            nombre = item.get('nombre')
            # quantities are integer units; prices and iva keep Decimal/int types
            cantidad = int(item.get('cantidad', 0))
            precio = Decimal(str(item.get('pvp', '0')))
            tipo_iva = int(item.get('tipo_iva', 0))

            # resolve SKU only (avoid reading unused columns)
            sku = None
            if prod_id is not None:
                cur.execute('SELECT sku FROM productos WHERE id = ?', (prod_id,))
                p = cur.fetchone()
                if p:
                    sku = p[0]

            # insert ticket line (store numeric fields as strings to avoid implicit float conversion)
            insert_line_q = (
                "INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?, ?, ?, ?, ?, ?)"
            )
            cur.execute(insert_line_q, (ticket_id, sku, nombre, cantidad, str(precio), tipo_iva))

            # update producto stock and ventas if prod_id provided
            if prod_id is not None:
                try:
                    # update stock_actual (allow negative but log)
                    cur.execute('UPDATE productos SET stock_actual = COALESCE(stock_actual,0) - ?, ventas_totales = COALESCE(ventas_totales,0) + ? WHERE id = ?', (cantidad, cantidad, prod_id))
                    # optional: check new stock and log
                    cur.execute('SELECT stock_actual FROM productos WHERE id = ?', (prod_id,))
                    new_stock = cur.fetchone()
                    if new_stock and new_stock[0] is not None and new_stock[0] < 0:
                        logging.warning(f'Producto id {prod_id} stock negativo tras venta: {new_stock[0]}')
                except Exception:
                    logging.exception('Error actualizando stock/ventas para producto %s', prod_id)

        # commit
        # --- Actualizar cliente con puntos dentro de la misma transacción ---
        try:
            if cliente_id:
                # Actualizar cliente: sumar puntos ganados, restar puntos gastados,
                # acumular puntos ganados en histórico y acumular puntos gastados.
                cur.execute(
                    """
                    UPDATE clientes SET
                        tesoro_total = COALESCE(tesoro_total, 0) + ? - ?,
                        tesoro_historico = COALESCE(tesoro_historico, 0) + ?,
                        tesoro_gastado_total = COALESCE(tesoro_gastado_total, 0) + ?
                    WHERE id = ?
                    """,
                    (
                        str(puntos_ganados),
                        str(puntos_gastados),
                        str(puntos_ganados),
                        str(puntos_gastados),
                        cliente_id,
                    ),
                )
                # Recalcular nivel automáticamente según tesoro_historico
                cur.execute(
                    """
                    UPDATE clientes
                    SET id_nivel = (
                        SELECT id FROM niveles_fidelidad
                        WHERE gasto_minimo <= (SELECT tesoro_historico FROM clientes WHERE id = ?)
                        ORDER BY gasto_minimo DESC
                        LIMIT 1
                    )
                    WHERE id = ?
                    """,
                    (cliente_id, cliente_id),
                )
        except Exception:
            logging.exception('Error actualizando cliente con puntos; rollback')
            conn.rollback()
            raise

        conn.commit()
        logging.info(f'Ticket guardado id={ticket_id} num_ticket={num_ticket}')
        return ticket_id, num_ticket
    except Exception:
        conn.rollback()
        logging.exception('Error guardando ticket, transaction rolled back')
        raise
