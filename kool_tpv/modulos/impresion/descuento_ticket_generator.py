from decimal import Decimal
import logging

from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class DescuentoTicketGenerator(BaseTicketGenerator):
    """Generador para tickets de descuento que sigue el formato de venta.

    Imprime los artículos (si se pasan) y, tras ellos, una línea con el
    descuento en el formato solicitado:

    << Descuento -x%:                -Y.YY

    donde el importe del descuento va justificado a la derecha y se muestra
    como negativo.
    """

    def generate(self, config, data, items=None, cliente_data=None):
        lines = []

        # Encabezado (usar plantilla si existe)
        header_val = config.get('ticket_header_venta') or None
        context = {
            'fecha': data.get('fecha', ''),
            'hora': data.get('hora', ''),
            'cajero': data.get('cajero', ''),
            'num_ticket': data.get('num_ticket', ''),
            'total': self._format_currency(data.get('total', 0)),
            'forma_pago': data.get('forma_pago', ''),
        }
        try:
            if header_val:
                lines.extend(self._render_template(header_val, context))
            else:
                lines.extend(self._format_header(config))
        except Exception:
            logging.exception('Error generando encabezado de descuento')

        lines.append(self.DIVIDER)
        lines.append('TICKET DESCUENTO'.center(self.WIDTH))
        lines.append(self.DIVIDER)

        # Fecha / cajero / num ticket similar a VentaTicketGenerator
        fecha = data.get('fecha', '')
        hora = data.get('hora', '')
        cajero = data.get('cajero', '')
        num_ticket = data.get('num_ticket', '')

        fecha_hora = f"{fecha} {hora}".strip()
        right1 = 'CAJERO:'
        left1 = fecha_hora
        space1 = self.WIDTH - len(left1) - len(right1)
        if space1 < 1:
            space1 = 1
        lines.append((left1 + (' ' * space1) + right1)[: self.WIDTH])

        left2 = f"TICKET {num_ticket}".strip()
        right2 = '' if cajero is None else str(cajero)
        space2 = self.WIDTH - len(left2) - len(right2)
        if space2 < 1:
            space2 = 1
        lines.append((left2 + (' ' * space2) + right2)[: self.WIDTH])
        lines.append(self.DIVIDER)

        # Items: reutilizar la lógica de VentaTicketGenerator (simplificada)
        try:
            from decimal import Decimal as _D
            for it in items or []:
                # cantidad
                cant = None
                for k in ("cantidad", "cant", "qty", "cantidad_articulo"):
                    if k in it:
                        cant = it[k]
                        break
                if cant is None:
                    cant = it.get('cantidad', 1)
                try:
                    cant_int = int(cant)
                except Exception:
                    cant_int = 1

                nombre_item = it.get('nombre') or it.get('descripcion') or ''
                pvp_val = it.get('precio') if 'precio' in it else it.get('pvp', 0)
                total_val = it.get('total') if 'total' in it else None

                try:
                    pvp_s = self._format_currency(pvp_val)
                except Exception:
                    pvp_s = self._format_currency(0)

                if total_val is None:
                    try:
                        total_calc = _D(str(pvp_val)) * _D(cant_int)
                    except Exception:
                        try:
                            total_calc = _D(pvp_val) * _D(cant_int)
                        except Exception:
                            total_calc = _D('0')
                    total_s = self._format_currency(total_calc)
                else:
                    try:
                        total_s = self._format_currency(total_val)
                    except Exception:
                        total_s = self._format_currency(0)

                # presentación simple: "<cant>x <nombre>" then right block "[pvp] total"
                prefix = f"{cant_int}x "
                pvp_bracket = f"[{pvp_s}]"
                right_block = f"{pvp_bracket} {total_s}".strip()

                name_width = self.WIDTH - len(prefix)
                words = [w for w in str(nombre_item).split() if w]
                nome = ' '.join(words)
                indent = ' ' * len(prefix)

                if len(prefix) + len(nome) <= self.WIDTH:
                    lines.append((prefix + nome)[: self.WIDTH])
                    pad_last = self.WIDTH - len(indent) - len(right_block)
                    if pad_last < 1:
                        pad_last = 1
                    last_line = indent + (' ' * pad_last) + right_block
                    lines.append(last_line[: self.WIDTH])
                else:
                    # simple wrap: first line prefix + first fragment, then remaining name, then prices
                    lines.append((prefix + nome)[: self.WIDTH])
                    pad_last = self.WIDTH - len(indent) - len(right_block)
                    if pad_last < 1:
                        pad_last = 1
                    last_line = indent + (' ' * pad_last) + right_block
                    lines.append(last_line[: self.WIDTH])
        except Exception:
            logging.exception('Error generando líneas de items en ticket de descuento')

        # Línea de descuento solicitada: mostrar tras artículos
        try:
            # Datos esperados en `data`: 'descuento_tipo', 'descuento_valor', 'descuento_euros' (o 'importe')
            descuento_euros = data.get('descuento_euros') or data.get('importe') or 0
            # normalizar Decimal/string
            try:
                descuento_euros_dec = Decimal(str(descuento_euros))
            except Exception:
                descuento_euros_dec = Decimal('0')

            if descuento_euros_dec > 0:
                descuento_tipo = data.get('descuento_tipo') or data.get('tipo') or ''
                descuento_valor = data.get('descuento_valor') or data.get('valor') or ''
                if descuento_tipo == 'porcentaje':
                    texto_desc = f'<< Descuento -{descuento_valor}%:'
                elif descuento_tipo == 'directo' or descuento_tipo in ('euros', '€'):
                    texto_desc = f'<< Descuento -{descuento_valor}€:'
                else:
                    texto_desc = '<< Descuento:'

                linea_desc = self._format_line_lr(
                    texto_desc,
                    f"-{self._format_currency(descuento_euros_dec)}"
                )
                lines.append(linea_desc)
        except Exception:
            logging.exception('Error generando línea de descuento')

        # Pie y totales simples (delegar a helpers si es posible)
        lines.append(self.DOUBLE_DIVIDER)
        footer = config.get('pie_texto')
        if footer:
            lines.append(footer)

        return "\n".join([l for l in lines if l is not None])
