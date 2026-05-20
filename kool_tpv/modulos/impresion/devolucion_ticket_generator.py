from __future__ import annotations
from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator


class DevolucionTicketGenerator(VentaTicketGenerator):
    """Generador de tickets de devolución.

    Hereda toda la lógica de VentaTicketGenerator (precios negativos,
    encabezado "TICKET DEVOLUCIÓN", etc.) y fuerza motivo='devolucion'
    en tesoro_data para que la sección de fidelización muestre sólo
    el saldo actual del cliente (Tesoro Total), sin ganado/gastado/acumulado.
    """

    def generate(self, config, ticket_data, items, cliente_data=None):
        td = dict(ticket_data) if ticket_data else {}
        if cliente_data is not None:
            tesoro = dict(td.get('tesoro_data') or {})
            tesoro['motivo'] = 'devolucion'
            td['tesoro_data'] = tesoro
        return super().generate(config, td, items, cliente_data)
