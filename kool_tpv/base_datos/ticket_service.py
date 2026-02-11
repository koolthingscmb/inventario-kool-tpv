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

        # puntos gastados (canjeados) provienen del carrito
        puntos_gastados = Decimal('0')
        try:
            if carrito_service is not None and getattr(carrito_service, 'get_puntos_canjeados', None):
                puntos_gastados = carrito_service.get_puntos_canjeados() or Decimal('0')
        except Exception:
            logging.exception('Error obteniendo puntos canjeados del carrito; se asume 0')
            puntos_gastados = Decimal('0')

        # separar items de venta y de devolución para calcular puntos por separado
        puntos_otorgar = Decimal('0')
        puntos_restar = Decimal('0')
        try:
            items_venta = []
            items_devol = []
            for it in carrito_items or []:
                # construir estructura mínima esperada por calcular_puntos_ganados
                item_repr = {
                    'id': it.get('id'),
                    'pvp': str(it.get('pvp', '0')),
                    'cantidad': it.get('cantidad', 0)
                }
                if str(it.get('line_tipo', 'venta')) == 'devolucion':
                    items_devol.append(item_repr)
                else:
                    items_venta.append(item_repr)

            if fidelizacion_service is not None:
                try:
                    # Aplicar reducción proporcional por canje solo a los puntos de ventas
                    puntos_otorgar = fidelizacion_service.calcular_puntos_ganados(items_venta, puntos_canjeados=puntos_gastados) or Decimal('0')
                except Exception:
                    logging.exception('Error calculando puntos otorgar; se asume 0')
                    puntos_otorgar = Decimal('0')
                try:
                    # Para devoluciones no aplicamos factor de canje (se restan los puntos correspondientes)
                    puntos_restar = fidelizacion_service.calcular_puntos_ganados(items_devol, puntos_canjeados=Decimal('0')) or Decimal('0')
                except Exception:
                    logging.exception('Error calculando puntos restar; se asume 0')
                    puntos_restar = Decimal('0')
        except Exception:
            logging.exception('Error separando items por tipo para fidelización')
            puntos_otorgar = Decimal('0')
            puntos_restar = Decimal('0')

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
                        str(puntos_otorgar),
                        str(puntos_restar + puntos_gastados),
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
            # include `line_tipo` so lines can be 'venta'|'devolucion'|'intercambio'
            line_tipo = str(item.get('line_tipo', 'venta'))
            insert_line_q = (
                "INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva, line_tipo) VALUES (?, ?, ?, ?, ?, ?, ?)"
            )
            cur.execute(insert_line_q, (ticket_id, sku, nombre, cantidad, str(precio), tipo_iva, line_tipo))
            line_id = cur.lastrowid

            # update producto stock and ventas if prod_id provided
            if prod_id is not None:
                try:
                    # determine stock and ventas change depending on line type
                    if line_tipo == 'devolucion':
                        stock_change = cantidad  # devolución = entrada al stock
                        ventas_change = -cantidad
                    else:
                        stock_change = -cantidad  # venta = salida del stock
                        ventas_change = cantidad

                    cur.execute('UPDATE productos SET stock_actual = COALESCE(stock_actual,0) + ?, ventas_totales = COALESCE(ventas_totales,0) + ? WHERE id = ?', (stock_change, ventas_change, prod_id))
                    # optional: check new stock and log
                    cur.execute('SELECT stock_actual FROM productos WHERE id = ?', (prod_id,))
                    new_stock = cur.fetchone()
                    if new_stock and new_stock[0] is not None and new_stock[0] < 0:
                        logging.warning(f'Producto id {prod_id} stock negativo tras operación: {new_stock[0]}')

                    # insert stock_movements record if table exists
                    try:
                        cur.execute(
                            "INSERT INTO stock_movements (producto_id, cantidad, motivo, ticket_line_id) VALUES (?, ?, ?, ?)",
                            (prod_id, stock_change, f"ticket:{ticket_id}", line_id),
                        )
                    except Exception:
                        # table may not exist yet; ignore but log
                        logging.debug('stock_movements table not present or insert failed')
                except Exception:
                    logging.exception('Error actualizando stock/ventas para producto %s', prod_id)

        # commit
        # --- Insertar registros de pagos y auditoría dentro de la misma transacción ---
            # Insertar pagos desglosados si la tabla existe (se ignora si no existe)
            try:
                if importe_efectivo_val and importe_efectivo_val != 0:
                    cur.execute(
                        "INSERT INTO payments (ticket_id, metodo, importe, created_at) VALUES (?, ?, ?, ?)",
                        (ticket_id, 'efectivo', str(importe_efectivo_val), created_at),
                    )
                if importe_tarjeta_val and importe_tarjeta_val != 0:
                    cur.execute(
                        "INSERT INTO payments (ticket_id, metodo, importe, created_at) VALUES (?, ?, ?, ?)",
                        (ticket_id, 'tarjeta', str(importe_tarjeta_val), created_at),
                    )
            except Exception:
                logging.debug('payments table not present or insert failed')

            # Registrar un entry de auditoría con resumen mínimo (si la tabla existe)
            try:
                detalles = f"num_ticket={num_ticket} total={total} pagado={pagado} cambio={cambio} cajero={cajero}"
                cur.execute(
                    "INSERT INTO audit_logs (created_at, ticket_id, usuario, accion, detalles) VALUES (?, ?, ?, ?, ?)",
                    (created_at, ticket_id, cajero if cajero else None, 'save_ticket', detalles),
                )
            except Exception:
                logging.debug('audit_logs table not present or insert failed')

        # --- Actualizar cliente con puntos dentro de la misma transacción ---
        try:
            if cliente_id:
                # neto de puntos: otorgar (ventas) - restar (devoluciones) - canjeados
                try:
                    neto_puntos = (puntos_otorgar - puntos_restar - puntos_gastados).quantize(Decimal('0.01'))
                except Exception:
                    neto_puntos = Decimal('0')

                # Insertar movimiento de puntos (si la tabla existe)
                try:
                    cur.execute(
                        "INSERT INTO points_movements (cliente_id, puntos, motivo, ticket_id, usuario_id) VALUES (?, ?, ?, ?, ?)",
                        (cliente_id, float(neto_puntos), 'ticket', ticket_id, None),
                    )
                except Exception:
                    logging.debug('points_movements table not present or insert failed')

                # Actualizar cliente: aplicar cambios en tesoro_total y tesoro_historico
                try:
                    cur.execute(
                        """
                        UPDATE clientes SET
                            tesoro_total = COALESCE(tesoro_total, 0) + ? - ?,
                            tesoro_historico = COALESCE(tesoro_historico, 0) + ? - ?,
                            tesoro_gastado_total = COALESCE(tesoro_gastado_total, 0) + ?
                        WHERE id = ?
                        """,
                        (
                            str(puntos_otorgar),
                            str(puntos_restar + puntos_gastados),
                            str(puntos_otorgar),
                            str(puntos_restar),
                            str(puntos_gastados),
                            cliente_id,
                        ),
                    )
                except Exception:
                    logging.exception('Error actualizando cliente con puntos; rollback')
                    conn.rollback()
                    raise

                # Recalcular nivel automáticamente según tesoro_historico
                try:
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
                    logging.exception('Error recalculando nivel de fidelidad')
        except Exception:
            logging.exception('Error procesando actualización de cliente')
            conn.rollback()
            raise

        conn.commit()
        logging.info(f'Ticket guardado id={ticket_id} num_ticket={num_ticket}')
        return ticket_id, num_ticket
    except Exception:
        conn.rollback()
        logging.exception('Error guardando ticket, transaction rolled back')
        raise
