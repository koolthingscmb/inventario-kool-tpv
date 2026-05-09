"""Compatibility shim for older imports expecting ticket_processor module.

Re-exports the processors defined in the package-level `kool_tpv.modulos.ticket`.
"""
from kool_tpv.modulos.ticket import (
    VentaProcessor,
    VentaFidelizacionProcessor,
    DevolucionProcessor,
    DescuentoProcessor,
    CierreCajaProcessor,
    SubidaNivelProcessor,
)

__all__ = [
    'VentaProcessor',
    'VentaFidelizacionProcessor',
    'DevolucionProcessor',
    'DescuentoProcessor',
    'CierreCajaProcessor',
    'SubidaNivelProcessor',
]
