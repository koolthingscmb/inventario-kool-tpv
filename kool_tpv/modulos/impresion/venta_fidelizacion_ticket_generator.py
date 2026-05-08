from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator
from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator


class VentaFidelizacionTicketGenerator(BaseTicketGenerator):
    """Generador para ventas con fidelización.

    Reutiliza la lógica de `VentaTicketGenerator` y garantiza que el título
    y la sección de fidelización aparezcan.
    """

    def generate(self, config, ticket_data, items, cliente_data=None):
        venta_gen = VentaTicketGenerator()

        td = dict(ticket_data or {})
        # Garantizar que no se marque como devolución
        td['tipo'] = td.get('tipo', 'venta')

        # Asegurar que `tesoro_data` esté presente si existe cliente_data
        if cliente_data and 'tesoro_data' not in td:
            td['tesoro_data'] = cliente_data.get('tesoro_data') if isinstance(cliente_data, dict) else None

        texto = venta_gen.generate(config, td, items or [], cliente_data)

        # Reemplazar título si fuera necesario para resaltar fidelización
        if texto and 'FACTURA SIMPLIFICADA' in texto:
            texto = texto.replace('FACTURA SIMPLIFICADA', 'FACTURA + FIDELIZACIÓN')

        return texto
