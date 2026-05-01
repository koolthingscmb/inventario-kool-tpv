"""
Generador de ticket para subida de nivel.

Implementa `NivelTicketGenerator` que hereda de `BaseTicketGenerator`.
"""
from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class NivelTicketGenerator(BaseTicketGenerator):
    """Generador de tickets para eventos de subida de nivel."""

    def generate(self, config, nivel_data: dict) -> str:
        """Genera el ticket de subida de nivel.

        Args:
            config: dict con configuración del comercio (nombre_negocio, direccion, nif, pie_texto, opcionales headers/footers)
            nivel_data: dict con claves requeridas (ver especificación)

        Returns:
            str: ticket formateado
        """
        lines = []

        # Extraer campos desde nivel_data con fallback
        fecha = nivel_data.get('fecha', '')
        hora = nivel_data.get('hora', '')
        cliente = nivel_data.get('cliente', '')
        nivel_anterior = nivel_data.get('nivel_anterior', '')
        nivel_nuevo = nivel_data.get('nivel_nuevo', '')
        grafismo = nivel_data.get('grafismo', '')
        total_acumulado_raw = nivel_data.get('total_acumulado', '')

        # Intenta formatear total_acumulado si es numérico, sino usar raw
        try:
            total_acumulado = self._format_currency(total_acumulado_raw)
        except Exception:
            total_acumulado = str(total_acumulado_raw)

        tipo = 'nivel'
        context = {
            'fecha': fecha,
            'hora': hora,
            'cliente': cliente,
            'nivel_anterior': nivel_anterior,
            'nivel_nuevo': nivel_nuevo,
            'total_acumulado': total_acumulado,
        }

        # Header por tipo con fallback
        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"
        header_val = config.get(header_key)
        if header_val:
            lines.extend(self._render_template(header_val, context))
        else:
            lines.extend(self._format_header(config))

        # Cuerpo específico
        # Mostrar siempre fecha y hora justo después del header
        dt_line = f"{fecha} {hora}".strip()
        if dt_line:
            if len(dt_line) > self.WIDTH:
                dt_line = dt_line[: self.WIDTH]
            lines.append(dt_line.center(self.WIDTH))

        lines.append(self.DIVIDER)
        lines.append('SUBIDA DE NIVEL'.center(self.WIDTH))
        lines.append(self.DIVIDER)

        if cliente:
            lines.append(str(cliente).center(self.WIDTH))

        # Mostrar niveles "anterior -> nuevo"
        lvl_line = f"{nivel_anterior} -> {nivel_nuevo}" if (nivel_anterior or nivel_nuevo) else ''
        if lvl_line:
            lines.append(lvl_line.center(self.WIDTH))

        if grafismo:
            lines.append(str(grafismo).center(self.WIDTH))

        # Total acumulado
        if total_acumulado:
            left = 'Total acumulado:'
            right = total_acumulado
            # usar formato LR para alinear correctamente
            try:
                lines.append(self._format_line_lr(left, right))
            except Exception:
                lines.append(f"{left} {right}".center(self.WIDTH))

        lines.append(self.DIVIDER)

        # Footer por tipo con fallback
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))
        else:
            lines.extend(self._format_footer(config))

        return "\n".join(lines)
