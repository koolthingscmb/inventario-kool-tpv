"""
REMOVED: Legacy export helper functions.

The export functions previously provided here have been retired and should be
reimplemented using `modulos.exportar_importar.exportar_service.ExportarService`.

This module now raises ImportError to force callers to migrate.
"""

raise ImportError('Legacy export module removed; use ExportarService in modulos.exportar_importar')
