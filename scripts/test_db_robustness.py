import tempfile
import os
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.db_init import initialize_database
from kool_tpv.base_datos.ticket_service import save_ticket

logging.basicConfig(level=logging.INFO)


def _prepare_products(db: Database, count=10, stock=100):
    ids = []
    with db.transaction() as cur:
        for i in range(count):
            sku = f"TESTSKU{i}"
            nombre = f"Producto {i}"
            cur.execute("INSERT INTO productos (nombre, nombre_boton, sku, categoria, tipo, proveedor_id, tipo_iva, stock_actual, stock_minimo, activo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (nombre, nombre, sku, 1, 1, None, 21, stock, 0, 1))
            pid = cur.lastrowid
            cur.execute("INSERT INTO precios (producto_id, pvp, coste, activo) VALUES (?, ?, ?, 1)", (pid, 10.0, 5.0))
            ids.append(pid)
    return ids


def test_save_and_rollback():
    # create temp file DB to ensure persistence across connections
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    path = tf.name
    try:
        initialize_database(path)
        db = Database(path)
        db.connect()

        # prepare products
        pids = _prepare_products(db, count=10, stock=100)

        # build carrito: each product qty 2
        carrito = []
        for pid in pids:
            carrito.append({
                'id': pid,
                'nombre': f'Producto',
                'cantidad': 2,
                'pvp': '10.00',
                'tipo_iva': 21,
            })

        resumen = {'subtotal': 200.0, 'total': 200.0, 'iva_desglose': {}}

        # save ticket
        tid, num = save_ticket(db, carrito, resumen, efectivo=200.0, cajero='test')
        logging.info(f"Ticket guardado: id={tid} num={num}")

        # verify stock decreased by 2
        for pid in pids:
            row = db.fetch_one("SELECT stock_actual FROM productos WHERE id = ?", (pid,))
            assert row is not None
            stock_after = int(row[0])
            assert stock_after == 98, f"Stock incorrecto para {pid}: {stock_after}"

        logging.info('Stock actualizado correctamente después de save_ticket')

        # Now test rollback behaviour: perform multiple updates and raise
        try:
            with db.transaction() as cur:
                # reduce stock by 1 for first 3 products
                for pid in pids[:3]:
                    cur.execute('UPDATE productos SET stock_actual = stock_actual - 1 WHERE id = ?', (pid,))
                # force an error
                cur.execute('INSERT INTO tabla_que_no_existe (a) VALUES (1)')
        except Exception:
            logging.info('Se produjo excepción dentro de la transacción, comprobando rollback')

        # verify stock for first 3 products left unchanged (should be 98)
        for pid in pids[:3]:
            row = db.fetch_one("SELECT stock_actual FROM productos WHERE id = ?", (pid,))
            assert row is not None
            assert int(row[0]) == 98, f"Rollback fallido para {pid}: {row[0]}"

        logging.info('Rollback verificado: cambios no persistieron')

    finally:
        try:
            db.close_connection()
        except Exception:
            pass
        try:
            os.unlink(path)
        except Exception:
            pass


if __name__ == '__main__':
    test_save_and_rollback()
    print('OK')
