"""Paquete de acciones relacionadas con cierres de caja.

Nota: `CierreUI` fue removido del código. Exportamos únicamente el
`CierreController` para evitar import errors en tiempo de ejecución.
"""
from .cierre_controller import CierreController

__all__ = ["CierreController"]
