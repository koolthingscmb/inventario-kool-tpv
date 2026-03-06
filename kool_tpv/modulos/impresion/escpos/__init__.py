"""Módulo ESC/POS: renderer y adapters.

Exposición pública de componentes ESC/POS.
"""
from .escpos_renderer import EscPosRenderer
from .printer_adapter_windows import WindowsPrinterAdapter

__all__ = ["EscPosRenderer", "WindowsPrinterAdapter"]
