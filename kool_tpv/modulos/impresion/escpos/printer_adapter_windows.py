from __future__ import annotations
import logging
from typing import Optional

try:
    import win32print  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    win32print = None  # type: ignore


class WindowsPrinterAdapter:
    """Adapter para enviar bytes RAW a una impresora en Windows.

    Implementa el envío usando `win32print`. Si el paquete no está
    disponible, lanza una excepción controlada y registra el error.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def send_to_printer(self, printer_name: str, data: bytes) -> None:
        """Enviar `data` (bytes) a la impresora indicada.

        Args:
            printer_name: nombre de la impresora tal como Windows la expone.
            data: bytes CRUDO a enviar (modo RAW).

        Raises:
            RuntimeError: si `win32print` no está disponible o ocurre fallo al enviar.
        """
        if win32print is None:
            self.logger.error("win32print no disponible en este entorno; imposible imprimir en Windows")
            raise RuntimeError("win32print no disponible")

        hPrinter = None
        try:
            # Abrir impresora
            hPrinter = win32print.OpenPrinter(printer_name)
            # Document info: nombre del documento y tipo RAW
            doc_info = ("KOOL_TPV", None, "RAW")
            job_id = win32print.StartDocPrinter(hPrinter, 1, doc_info)
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, data)
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        except Exception:
            self.logger.exception("Error enviando datos a la impresora '%s'", printer_name)
            raise
        finally:
            try:
                if hPrinter:
                    win32print.ClosePrinter(hPrinter)
            except Exception:
                # No romper si el cierre falla; ya se ha registrado el error
                self.logger.exception("Error cerrando handle de impresora")

# TODO: Implementar adapter para macOS/CUPS en el futuro (usar cups/lp)
