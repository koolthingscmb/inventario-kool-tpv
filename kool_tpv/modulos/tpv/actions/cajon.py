"""Acción para abrir el cajón del dinero vía comando ESC/POS estándar.

El comando ESC p m t1 t2 (\x1b\x70\x00\x30\x30) es universal para
impresoras térmicas POS (Epson, Star, Bixolon, Xprinter, etc.).
"""
import logging

logger = logging.getLogger(__name__)

# Comando ESC/POS estándar para abrir cajón (pin 0, ~50ms pulso)
CAJON_CMD = b"\x1b\x70\x00\x30\x30"


def abrir_cajon(db=None):
    """Enviar comando ESC/POS para abrir el cajón del dinero.

    Lee el nombre de la impresora desde la tabla 'configuracion'
    (clave 'printer_name') y envía los bytes RAW usando
    WindowsPrinterAdapter.

    Args:
        db: Instancia de la base de datos con fetch_one.
    """
    if db is None:
        logger.warning("abrir_cajon: sin conexión a BD, no se puede obtener printer_name")
        return

    try:
        row = db.fetch_one("SELECT valor FROM configuracion WHERE clave = 'printer_name'")
        if not row or not row[0]:
            logger.warning("abrir_cajon: no hay printer_name configurado")
            return

        printer_name = row[0]
        logger.info("abrir_cajon: enviando comando a '%s'", printer_name)

        from kool_tpv.modulos.impresion.escpos.printer_adapter_windows import WindowsPrinterAdapter
        adapter = WindowsPrinterAdapter()
        adapter.send_to_printer(printer_name, CAJON_CMD)

        logger.info("abrir_cajon: comando enviado correctamente a '%s'", printer_name)

    except Exception:
        logger.exception("abrir_cajon: error al abrir el cajón")
