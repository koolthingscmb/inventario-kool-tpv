"""
Clase base abstracta para generadores de tickets.

Proporciona helpers comunes (formato, alineación, encabezado/pie)
para todos los tipos de tickets.
"""
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from kool_tpv.utils.formatter_service import FormatterService


class BaseTicketGenerator(ABC):
    """Generador base para tickets en formato texto plano."""

    WIDTH = 42
    DIVIDER = "-" * WIDTH
    DOUBLE_DIVIDER = "=" * WIDTH

    def _format_currency(self, val):
        """Formatear valor monetario a string con 2 decimales."""
        try:
            # Usar FormatterService para asegurar política de truncado/formateo
            fmt = FormatterService()
            return fmt.format_precio(val)
        except Exception:
            try:
                dec = Decimal(val)
            except (InvalidOperation, TypeError, ValueError):
                try:
                    dec = Decimal(str(val))
                except Exception:
                    dec = Decimal('0')
            dec = dec.quantize(Decimal('0.01'))
            return f"{dec:.2f}"

    def _format_line_lr(self, label, valor, label_width=30):
        """Formatear línea con label (izq) y valor (der) alineados.

        Args:
            label: Texto a la izquierda
            valor: Valor a la derecha (ya formateado como string)
            label_width: Ancho reservado para label (default 30)

        Returns:
            String formateado de ancho WIDTH
        """
        valor_width = self.WIDTH - label_width
        return f"{label:<{label_width}}{valor:>{valor_width}}"

    def _format_header(self, config):
        """Generar encabezado común (nombre, dirección, NIF).

        Args:
            config: dict con 'nombre_negocio', 'direccion', 'nif'

        Returns:
            Lista de líneas de texto
        """
        lines = []
        nombre = config.get('nombre_negocio', '')
        direccion = config.get('direccion', '')
        nif = config.get('nif', '')

        if nombre:
            lines.append(nombre.center(self.WIDTH))
        if direccion:
            lines.append(direccion.center(self.WIDTH))
        if nif:
            lines.append(nif.center(self.WIDTH))

        return lines

    def _format_footer(self, config):
        """Generar pie común (IVA incluido, texto personalizado).

        Args:
            config: dict con 'pie_texto'

        Returns:
            Lista de líneas de texto
        """
        lines = [self.DIVIDER]
        lines.append('I.V.A Incluido'.center(self.WIDTH))
        pie = config.get('pie_texto', '')
        if pie:
            lines.append(pie.center(self.WIDTH))
        return lines

    @abstractmethod
    def generate(self, config, **kwargs):
        """Generar ticket completo.

        Método abstracto que cada tipo de ticket debe implementar.

        Args:
            config: dict con configuración del negocio
            **kwargs: parámetros específicos del tipo de ticket

        Returns:
            str: contenido del ticket formateado
        """
        pass
