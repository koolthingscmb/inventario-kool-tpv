import logging
import traceback

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger('TEST')

try:
    import customtkinter as ctk
    from kool_tpv.base_datos.db_wrapper import Database
    from kool_tpv.modulos.clientes.clientes_view import ClientesView

    # Connect DB
    db = Database('kool_tpv/base_datos/kool_bd.db')
    db.connect()
    logger.info('DB connected')

    # Create minimal CTk root
    root = ctk.CTk()
    logger.info('CTk root created')

    # Instantiate ClientesView and show búsqueda
    view = ClientesView(root, db)
    logger.info('ClientesView instantiated')
    try:
        view.show_busqueda()
        logger.info('Called show_busqueda()')
    except Exception:
        logger.exception('Error calling show_busqueda')

    # Simulate double-click on client id=3
    try:
        view.show_editar_cliente(3)
        logger.info('Called show_editar_cliente(3)')
    except Exception:
        logger.exception('Error calling show_editar_cliente(3)')

    # Destroy root
    try:
        root.destroy()
    except Exception:
        pass

except Exception:
    logger.error('Fatal test error')
    traceback.print_exc()
