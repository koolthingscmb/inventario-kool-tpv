from enum import Enum


class TicketType(Enum):
    VENTA = "venta"
    VENTA_FIDELIZACION = "venta_fidelizacion"
    DEVOLUCION = "devolucion"
    CIERRE = "cierre"
    NIVEL = "nivel"
