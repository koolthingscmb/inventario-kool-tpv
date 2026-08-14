"""BarcodeService - Captura global de códigos de barras desde lector USB HID.

El lector actúa como teclado: envía caracteres rápidamente (sin terminador o con Enter/Tab).
Estrategia de disparo:
  1. Si llegan >= EAN_LENGTH caracteres en ráfaga rápida → disparo inmediato
  2. Si llega un terminador (Enter/Tab) con buffer >= MIN_CODE_LENGTH → disparo inmediato
  3. Si no hay terminador ni longitud exacta → NO se usa timer (evita duplicados)
"""
import logging
import time
import tkinter as tk
from typing import Callable

logger = logging.getLogger(__name__)

THRESHOLD_MS = 150       # ms máximo entre teclas para considerarlas del mismo escáner (aumentado de 80)
MIN_CODE_LENGTH = 3
EAN_LENGTH = 13         # longitud estándar EAN-13


class BarcodeService:
    """Captura global de códigos de barras para lector USB HID."""

    def __init__(self, root_widget: tk.Misc, on_barcode: Callable[[str], None] = None):
        self.root = root_widget
        self.on_barcode = on_barcode
        self._buffer: list[str] = []
        self._last_key_time: float = 0.0
        self._attached = False
        self._just_dispatched = False
        self._ignore_return_until: float = 0.0
        self._handler_id = None # ID del binding de Tkinter para limpieza segura

    def set_handler(self, on_barcode: Callable[[str], None]):
        """Establece o elimina el callback que recibirá los códigos detectados."""
        self.on_barcode = on_barcode
        if on_barcode:
            logger.debug("BarcodeService: nuevo handler registrado")
        else:
            logger.debug("BarcodeService: handler eliminado (modo silencioso)")

    def attach(self):
        if self._attached:
            return
        try:
            # Guardamos el ID del binding para poder hacer unbind exacto después
            self._handler_id = self.root.bind_all('<KeyPress>', self._on_key, add='+')
            self._attached = True
            logger.info(f'BarcodeService: captura de teclado activada (id={self._handler_id})')
        except Exception:
            logger.exception('BarcodeService: error al registrar binding')

    def detach(self):
        """Desvincula el servicio globalmente. Solo debe llamarse al cerrar la App."""
        if not self._attached:
            return
        try:
            if self._handler_id:
                self.root.unbind_all('<KeyPress>', self._handler_id)
                self._handler_id = None
            self._attached = False
            self._buffer.clear()
            logger.info('BarcodeService: captura de teclado desactivada completamente')
        except Exception:
            logger.exception('BarcodeService: error al eliminar binding')

    def _is_typing_in_entry(self) -> bool:
        try:
            focused = self.root.focus_get()
            if focused is None:
                return False
            cls = focused.__class__.__name__.lower()
            return any(w in cls for w in ('entry', 'text', 'textbox', 'ctkentry', 'ctktextbox', 'spinbox', 'combobox'))
        except Exception:
            return False

    def get_last_dispatch_time(self) -> float:
        """Devuelve el timestamp (monotonic ms) del último código despachado."""
        return self._ignore_return_until - 300

    def _dispatch(self, source: str):
        """Disparar callback con el código acumulado."""
        code = ''.join(self._buffer).strip()
        self._buffer.clear()
        self._last_key_time = 0.0
        self._just_dispatched = True
        self._ignore_return_until = time.monotonic() * 1000 + 300
        
        if len(code) >= MIN_CODE_LENGTH:
            # SOLO procesamos si hay alguien escuchando activamente
            if self.on_barcode:
                logger.info(f'BarcodeService: código detectado ({source}) -> {code}')
                try:
                    self.on_barcode(code)
                except Exception:
                    logger.exception('BarcodeService: error en callback on_barcode')
            else:
                # Si nadie escucha, registramos en debug por si acaso
                logger.debug(f'BarcodeService: código ignorado (sin handler) -> {code}')

    def _on_key(self, event: tk.Event):
        try:
            now = time.monotonic() * 1000
            char = event.char
            keysym = event.keysym
            
            # Terminador explícito (Enter, Tab, \r)
            is_terminator = keysym in ('Return', 'KP_Enter', 'Tab') or char in ('\r', '\n', '\t')
            if is_terminator:
                if now < self._ignore_return_until or self._just_dispatched:
                    # Consumir el Enter del escáner para que no llegue al CarritoNavList
                    self._just_dispatched = False
                    return 'break'
                
                # Si hay algo en el buffer, disparamos sea cual sea la longitud (min 3)
                if len(self._buffer) >= MIN_CODE_LENGTH:
                    self._dispatch('terminator')
                    return 'break'
                else:
                    self._buffer.clear()
                return

            self._just_dispatched = False

            # Ignorar teclas no imprimibles
            if not char or len(char) != 1 or not char.isprintable():
                return

            elapsed = now - self._last_key_time
            
            # Si es la primera tecla del buffer, no aplicamos filtro de velocidad
            is_first_key = (self._last_key_time == 0.0)

            # Si hay pausa larga entre teclas, resetear buffer
            if self._buffer and elapsed > THRESHOLD_MS:
                self._buffer.clear()

            # Si hay foco en Entry y velocidad lenta → es escritura humana, ignorar
            # EXCEPCIÓN: Si es la primera tecla, la dejamos pasar para iniciar el buffer
            if not is_first_key and self._is_typing_in_entry() and elapsed > THRESHOLD_MS:
                return

            self._buffer.append(char)
            self._last_key_time = now

            # Disparo inmediato al alcanzar longitud EAN-13
            if len(self._buffer) == EAN_LENGTH:
                self._dispatch('ean13')

        except Exception:
            logger.exception('BarcodeService: error en _on_key')
