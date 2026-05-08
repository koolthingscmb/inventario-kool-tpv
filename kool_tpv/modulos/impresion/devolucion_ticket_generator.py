from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator
from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator


class DevolucionTicketGenerator(BaseTicketGenerator):
    """Generador especializado para tickets de devolución."""

    def generate(self, config, ticket_data, items, cliente_data=None):
        # Reutilizar el generador de venta pero asegurando marca de devolución
        venta_gen = VentaTicketGenerator()

        # Crear copia defensiva de ticket_data y garantizar totales negativos
        td = dict(ticket_data or {})
        td['tipo'] = 'devolucion'

        # Forzar totales negativos (si vienen como positivos en algunos callers)
        try:
            td['subtotal'] = -abs(td.get('subtotal', 0))
        except Exception:
            pass
        try:
            td['total'] = -abs(td.get('total', 0))
        except Exception:
            pass
        try:
            iva = td.get('iva_desglose') or {}
            if isinstance(iva, dict):
                iva_neg = {k: -abs(v) for k, v in iva.items()}
                td['iva_desglose'] = iva_neg
        except Exception:
            pass

        # Asegurar que las líneas se marquen como devolución para la presentación
        its = []
        for it in (items or []):
            copy_it = dict(it)
            copy_it['line_tipo'] = 'devolucion'
            its.append(copy_it)

        # No mostrar fidelización en devoluciones: forzamos cliente_data a None
        return venta_gen.generate(config, td, its, cliente_data=None)
