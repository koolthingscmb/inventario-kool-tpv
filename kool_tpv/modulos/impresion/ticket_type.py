from enum import Enum


class TicketType(Enum):
    VENTA = "venta"
    DEVOLUCION = "devolucion"
    CIERRE = "cierre"
    NIVEL = "nivel"
