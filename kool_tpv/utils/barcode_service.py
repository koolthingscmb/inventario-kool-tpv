"""BarcodeService - Captura global de códigos de barras desde lector USB HID.

El lector actúa como teclado: envía caracteres rápidamente + Enter.
Este servicio los discrimina del teclado normal por velocidad (< THRESHOLD_MS entre teclas)
y dispara un callback con el código completo cuando detecta el Enter final.
"""
import logging
import time
import tkinter as tk
from typing import Callable, Optional

logger = logging.getLogger(__name__)

THRESHOLD_MS = 80
MIN_CODE_LENGTH = 3


class BarcodeService:
    """Captura global de códigos de barras para lector USB HID.

    Uso:
        svc = BarcodeService(root_widget, on_barcode=self._handle_barcode)
        svc.attach()
        # cuando ya no se necesite:
        svc.detach()
    """

    def __init__(self, root_widget: tk.Misc, on_barcode: Callable[[str], None]):
        self.root = root_widget
        self.on_barcode = on_barcode
        self._buffer: list[str] = []
        self._last_key_time: float = 0.0
        self._attached = False

    def attach(self):
        """Registrar captura global de teclas en el root widget."""
        if self._attached:
            return
        try:
            self.root.bind_all('<KeyPress>', self._on_key, add='+')
            self._attached = True
            logger.info('BarcodeService: captura de teclado activada')
        except Exception:
            logger.exception('BarcodeService: error al registrar binding')

    def detach(self):
        """Eliminar captura global de teclas."""
        try:
            self.root.unbind_all('<KeyPress>')
            self._attached = False
            self._buffer.clear()
            logger.info('BarcodeService: captura de teclado desactivada')
        except Exception:
            logger.exception('BarcodeService: error al eliminar binding')

    def _is_typing_in_entry(self) -> bool:
        """True si el foco está en un widget de entrada de texto."""
        try:
            focused = self.root.focus_get()
            if focused is None:
                return False
            cls = focused.__class__.__name__.lower()
            return any(w in cls for w in ('entry', 'text', 'textbox', 'ctkentry', 'ctktextbox', 'spinbox', 'combobox'))
        except Exception:
            return False

    def _on_key(self, event: tk.Event):
        """Handler global de KeyPress."""
        try:
            now = time.monotonic() * 1000

            char = event.char
            keysym = event.keysym

            # Detectar Enter: fin de código de barras
            if keysym in ('Return', 'KP_Enter'):
                elapsed = now - self._last_key_time
                if self._buffer and elapsed < THRESHOLD_MS * 3:
                    code = ''.join(self._buffer).strip()
                    self._buffer.clear()
                    self._last_key_time = 0.0
                    if len(code) >= MIN_CODE_LENGTH:
                        logger.info(f'BarcodeService: código detectado -> {code}')
                        try:
                            self.on_barcode(code)
                        except Exception:
                            logger.exception('BarcodeService: error en callback on_barcode')
                else:
                    self._buffer.clear()
                return

            # Ignorar teclas especiales (flechas, F1-F12, etc.)
            if not char or len(char) != 1 or not char.isprintable():
                return

            elapsed = now - self._last_key_time

            # Si el tiempo entre teclas es mayor al threshold, es un humano escribiendo
            # Reiniciar buffer para no mezclar con lo que escribe el usuario
            if self._buffer and elapsed > THRESHOLD_MS:
                self._buffer.clear()

            # Si el foco está en un Entry Y la velocidad es lenta, ignorar
            # (si es muy rápido podría ser el escáner incluso con foco en Entry)
            if self._is_typing_in_entry() and elapsed > THRESHOLD_MS:
                return

            self._buffer.append(char)
            self._last_key_time = now

        except Exception:
            logger.exception('BarcodeService: error en _on_key')
