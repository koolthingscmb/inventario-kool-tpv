from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class DescuentoTicketGenerator(BaseTicketGenerator):
    """Generador simple para tickets de descuento.

    Expects `data` to contain keys: 'motivo', 'importe', 'fecha', 'hora', 'cajero'.
    """

    def generate(self, config, data, items=None, cliente_data=None):
        lines = []
        # Nombre del negocio centrado
        lines.append(str(config.get('nombre_negocio', 'KOOL')).center(self.WIDTH))
        lines.append(self.DIVIDER)
        lines.append('TICKET DESCUENTO'.center(self.WIDTH))
        lines.append(self.DIVIDER)

        motivo = (data or {}).get('motivo', '')
        fecha = (data or {}).get('fecha', '')
        hora = (data or {}).get('hora', '')
        cajero = (data or {}).get('cajero', '')

        if fecha or hora:
            lines.append(f"Fecha: {fecha} {hora}".strip())
        if cajero:
            lines.append(f"Cajero: {cajero}")
        if motivo:
            lines.append(f"Motivo: {motivo}")

        # Mostrar importe como negativo
        importe = (data or {}).get('importe', 0)
        try:
            importe_val = float(importe)
        except Exception:
            try:
                importe_val = float(str(importe))
            except Exception:
                importe_val = 0.0

        # Formato: etiqueta izquierda / importe a la derecha
        lines.append(self._format_line_lr('Importe', f"-{self._format_currency(importe_val)}"))

        lines.append(self.DOUBLE_DIVIDER)
        # Pie de ticket si existe
        footer = config.get('pie_texto')
        if footer:
            lines.append(footer)

        return "\n".join([l for l in lines if l is not None])
