"""
DEPRECATED: `impresora.py`

This module is deprecated and now delegates all printing functionality
to `modulos.impresion.print_service.ImpresionService`.

Please update imports to use `from modulos.impresion.print_service import ImpresionService`
and call `ImpresionService.imprimir_ticket(...)` directly. This module will be
removed in a future release.
"""

from modulos.impresion.print_service import ImpresionService

# Create a module-level, shared ImpresionService instance so existing callsites
# that import this legacy module still delegate to the new implementation.
_imp = ImpresionService()


def imprimir_ticket_y_abrir_cajon(ticket_texto):
    """Legacy wrapper — delegates to ImpresionService.imprimir_ticket.

    Kept for backward compatibility. All new code should use
    `ImpresionService` directly.
    """
    # Delegate to the centralized print service. Request the cajon open flag
    # so behaviour is consistent with the legacy helper name.
    try:
        return _imp.imprimir_ticket(ticket_texto, abrir_cajon=True)
    except Exception:
        # If anything fails, attempt to print to console for debugging parity
        # with the old behaviour then re-raise.
        try:
            print(ticket_texto)
        finally:
            raise
