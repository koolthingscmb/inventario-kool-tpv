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
        tipo_recompensa = nivel_data.get('tipo_recompensa', '')
        detalle_recompensa = nivel_data.get('detalle_recompensa', '')
        nombre_producto = nivel_data.get('nombre_producto', '')

        # Intenta formatear total_acumulado (XP) sin símbolo de moneda
        try:
            total_acumulado = self._format_number(total_acumulado_raw)
        except Exception:
            total_acumulado = str(total_acumulado_raw)

        tipo = 'nivel'
        # Calcular valor de recompensa según tipo
        if tipo_recompensa == 'Descuento' and detalle_recompensa:
            recompensa = detalle_recompensa
        elif tipo_recompensa == 'Artículo' and nombre_producto:
            recompensa = nombre_producto
        else:
            recompensa = ''

        context = {
            'fecha': fecha,
            'hora': hora,
            'cliente': cliente,
            'nivel_anterior': nivel_anterior,
            'nivel_nuevo': nivel_nuevo,
            'total_acumulado': total_acumulado,
            'recompensa': recompensa,
        }

        # 1. Lore del nivel (si existe) - Intro narrativa antes del header
        lore = nivel_data.get('lore_recompensa', '')
        if lore:
            lines.append(self.DIVIDER)
            lore_lines = lore.split('|||')
            for line in lore_lines:
                lines.append(f"{{{{FONTB_ON}}}}{line.strip()}{{{{FONTB_OFF}}}}".center(self.WIDTH))
            lines.append(self.DIVIDER)
            lines.append('') # Espacio extra tras la caja

        # 2. Header por tipo con fallback
        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"
        header_val = config.get(header_key)
        if header_val:
            lines.extend(self._render_template(header_val, context))
        else:
            lines.extend(self._format_header(config))

        # 3. Footer por tipo con fallback
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))
        else:
            lines.extend(self._format_footer(config))

        return "\n".join(lines)
