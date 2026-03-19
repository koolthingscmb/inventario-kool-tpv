"""
Generador de tickets de venta.

Hereda de BaseTicketGenerator y usa sus helpers comunes.
"""
from decimal import Decimal
import logging
from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class VentaTicketGenerator(BaseTicketGenerator):
    """Generador de tickets de venta.

    Hereda de BaseTicketGenerator y utiliza sus helpers comunes.
    """

    def generate(self, config, ticket_data, items, cliente_data=None):
        """Genera el texto del ticket.

        Args:
            config (dict): 'nombre_negocio', 'direccion', 'nif', 'pie_texto'
            ticket_data (dict): fecha, hora, cajero, num_ticket, subtotal,
                iva_desglose, total, forma_pago, entregado, cambio, tesoro_data
            items (list): lista de items
            cliente_data (dict|None): {'nombre', 'nivel', 'grafismo', 'level_num'}

        Returns:
            str: contenido del ticket formateado
        """

        lines = []

        # Determinar tipo de ticket (venta / devolucion)
        is_devolucion = False
        try:
            tipo_flag = str(ticket_data.get('tipo', '') or '')
            if tipo_flag.lower() in ('devolucion', 'devolución'):
                is_devolucion = True
        except Exception:
            pass
        if not is_devolucion:
            for it_check in (items or []):
                try:
                    if str(it_check.get('line_tipo', '')).lower() == 'devolucion':
                        is_devolucion = True
                        break
                except Exception:
                    continue

        tipo = 'devolucion' if is_devolucion else 'venta'

        # Construir contexto para placeholders
        fecha = ticket_data.get('fecha', '')
        hora = ticket_data.get('hora', '')
        cajero = ticket_data.get('cajero', '')
        num = ticket_data.get('num_ticket', '')
        context = {
            'fecha': fecha,
            'hora': hora,
            'cajero': cajero,
            'num_ticket': num,
            'total': self._format_currency(ticket_data.get('total', 0)),
            'forma_pago': ticket_data.get('forma_pago', ''),
        }
        if cliente_data:
            try:
                context['cliente'] = cliente_data.get('nombre', '')
            except Exception:
                context['cliente'] = ''

        # Encabezado: soporte plantillas por tipo con fallback al header genérico
        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"
        # Debug temporal: loggear keys y valores relacionados para diagnóstico
        try:
            logging.info(f"DEBUG: tipo={tipo}")
            logging.info(f"DEBUG: header_key={header_key}")
            logging.info(f"DEBUG: config keys={list(config.keys())}")
            logging.info(f"DEBUG: header_val={config.get(header_key)}")
        except Exception:
            pass
        header_val = config.get(header_key)
        try:
            logging.info(f"DEBUG GENERATOR: tipo={tipo}")
            logging.info(f"DEBUG GENERATOR: header_key={header_key}")
            logging.info(f"DEBUG GENERATOR: header_val={header_val}")
        except Exception:
            pass

        # Enhanced debug for header selection and fallback
        try:
            logging.info(f"DEBUG GEN: header_key={header_key}, header_val={header_val}, bool={bool(header_val)}")
        except Exception:
            pass

        if header_val:
            lines.extend(self._render_template(header_val, context))
        else:
            lines.extend(self._format_header(config))

        lines.append(self.DIVIDER)
        if is_devolucion:
            lines.append('TICKET DEVOLUCIÓN'.center(self.WIDTH))
        else:
            lines.append('FACTURA SIMPLIFICADA'.center(self.WIDTH))
        lines.append(self.DIVIDER)

        # Formato solicitado: dos líneas con alineación mixta
        # Línea 1: {fecha} {hora} (izq) ... "CAJERO:" (der)
        # Línea 2: "TICKET {num_ticket}" (izq) ... {nombre_cajero} (der)
        fecha_hora = f"{fecha} {hora}".strip()
        nombre_cajero = '' if ticket_data.get('cajero') is None else str(ticket_data.get('cajero'))
        num_ticket = '' if ticket_data.get('num_ticket') is None else str(ticket_data.get('num_ticket'))

        # Eliminar apariciones literales no deseadas
        fecha_hora = fecha_hora.replace('- None -', '').strip()
        nombre_cajero = nombre_cajero.replace('- None -', '').strip()
        num_ticket = num_ticket.replace('- None -', '').strip()

        right1 = 'CAJERO:'
        left1 = fecha_hora
        space1 = self.WIDTH - len(left1) - len(right1)
        if space1 < 1:
            space1 = 1
        line1 = (left1 + (' ' * space1) + right1)[: self.WIDTH]

        left2 = f"TICKET {num_ticket}".strip()
        right2 = nombre_cajero
        space2 = self.WIDTH - len(left2) - len(right2)
        if space2 < 1:
            space2 = 1
        line2 = (left2 + (' ' * space2) + right2)[: self.WIDTH]

        lines.append(line1)
        lines.append(line2)
        lines.append(self.DIVIDER)

        # Cuerpo (cabecera de columnas eliminada intencionadamente)

        # Función para formatear cada linea de ítem respetando WIDTH
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

            # nombre
            nombre_item = it.get('nombre') or it.get('descripcion') or ''

            # precios
            pvp_val = it.get('precio') if 'precio' in it else it.get('pvp', 0)
            total_val = it.get('total') if 'total' in it else None
            try:
                pvp_s = self._format_currency(pvp_val)
            except Exception:
                pvp_s = self._format_currency(0)

            if total_val is None:
                try:
                    total_calc = Decimal(pvp_val) * Decimal(cant_int)
                except Exception:
                    total_calc = Decimal('0')
                total_s = self._format_currency(total_calc)
            else:
                total_s = self._format_currency(total_val)

            # detectar si la línea es de devolución
            line_is_devol = False
            try:
                line_is_devol = str(it.get('line_tipo', '')).lower() == 'devolucion'
            except Exception:
                line_is_devol = False

            # preparar cadenas de presentación (no alterar los valores reales)
            if line_is_devol:
                pvp_display = f"-{pvp_s}"
                total_display = f"-{total_s}"
                prefix = f"-{cant_int}x "
            else:
                pvp_display = pvp_s
                total_display = total_s
                prefix = f"{cant_int}x "

            # Bracketed unit price for final line
            pvp_bracket = f"[{pvp_display}]"

            # Build right-side block (bracketed unit price + space + total)
            right_block = f"{pvp_bracket} {total_display}".strip()

            # Word-wrap product name without cutting words.
            # Available width for name on wrapped lines (excluding prefix on first line):
            name_width = self.WIDTH - len(prefix)
            if name_width < 10:
                name_width = max(10, self.WIDTH - len(prefix))

            words = []
            try:
                # split preserving existing whitespace semantics
                words = [w for w in str(nombre_item).split() if w is not None]
            except Exception:
                words = [str(nombre_item or '')]

            # Greedy fill lines for the name (each line max length = name_width)
            name_lines = []
            current = ''
            for w in words:
                if not current:
                    candidate = w
                else:
                    candidate = current + ' ' + w
                if len(candidate) <= name_width:
                    current = candidate
                else:
                    # flush current (may be empty if single word longer than width)
                    if current:
                        name_lines.append(current)
                        current = w
                    else:
                        # single long word: place it on its own line (do not cut)
                        name_lines.append(w)
                        current = ''
            if current:
                name_lines.append(current)

            # If name fits in a single line together with right_block, render on one line
            single_line_space = self.WIDTH - len(prefix) - len(right_block) - 1
            if single_line_space >= len(nome := (' '.join(words))):
                # Single-line: prefix + name + padding + right_block
                left_text = prefix + (nome)
                pad = self.WIDTH - len(left_text) - len(right_block)
                if pad < 1:
                    pad = 1
                line = left_text + (' ' * pad) + right_block
                lines.append(line[: self.WIDTH])
            else:
                # Multi-line: first line with prefix + first name line
                if name_lines:
                    first = name_lines[0]
                else:
                    first = ''
                lines.append((prefix + first)[: self.WIDTH])

                # middle continuation lines (if any), indented to align with name start
                indent = ' ' * len(prefix)
                for mid in name_lines[1:-1]:
                    lines.append((indent + mid)[: self.WIDTH])

                # last line: indent + last name fragment + padding + right_block
                last_name = name_lines[-1] if name_lines else ''
                left_last = indent + last_name
                pad_last = self.WIDTH - len(left_last) - len(right_block)
                if pad_last < 1:
                    pad_last = 1
                last_line = left_last + (' ' * pad_last) + right_block
                lines.append(last_line[: self.WIDTH])

        # Línea de descuento (si existe) - debe mostrarse antes del canje
        try:
            if ticket_data.get('descuento_euros'):
                descuento_euros = Decimal(str(ticket_data.get('descuento_euros', 0)))
                if descuento_euros > 0:
                    descuento_tipo = ticket_data.get('descuento_tipo', '')
                    descuento_valor = ticket_data.get('descuento_valor', 0)
                    if descuento_tipo == 'directo':
                        texto_desc = '>> Descuento Directo:'
                    elif descuento_tipo == 'porcentaje':
                        texto_desc = f'>> Descuento -{descuento_valor}%:'
                    else:
                        texto_desc = '>> Descuento:'

                    linea_desc = self._format_line_lr(
                        texto_desc,
                        f"-{self._format_currency(descuento_euros)}"
                    )
                    lines.append(linea_desc)
        except Exception:
            pass

        # Tesoro gastado si aplica
        tesoro = ticket_data.get('tesoro_data') or {}
        tesoro_gastado = tesoro.get('gastado', 0) if isinstance(tesoro, dict) else 0
        try:
            if Decimal(str(tesoro_gastado)) > 0:
                val_s = f"-{self._format_currency(tesoro_gastado)}"
                # Alineamos '>> CANJE PUNTOS' a la izquierda y el valor a la derecha
                line = ">> CANJE PUNTOS".ljust(self.WIDTH - len(val_s)) + val_s
                lines.append(line)
        except Exception:
            pass

        # Resumen financiero
        lines.append(self.DIVIDER)
        subtotal = ticket_data.get('subtotal', 0)
        lines.append(self._format_line_lr("Subtotal:", self._format_currency(subtotal)))

        iva_desglose = ticket_data.get('iva_desglose') or {}
        # soportar dict {tipo: cuota} o lista de tuples
        if isinstance(iva_desglose, dict):
            for tipo, cuota in iva_desglose.items():
                lines.append(self._format_line_lr(f"IVA {tipo}%:", self._format_currency(cuota)))
        elif isinstance(iva_desglose, (list, tuple)):
            for entry in iva_desglose:
                try:
                    tipo, cuota = entry
                    lines.append(self._format_line_lr(f"IVA {tipo}%:", self._format_currency(cuota)))
                except Exception:
                    continue

        lines.append(self.DOUBLE_DIVIDER)
        total = ticket_data.get('total', 0)
        lines.append(self._format_line_lr("TOTAL:", self._format_currency(total)))
        lines.append(self.DOUBLE_DIVIDER)

        # Formato simplificado de pago (reemplaza la tabla antigua)
        forma = (ticket_data.get('forma_pago') or '').strip()
        entr = ticket_data.get('entregado', 0)
        dev = ticket_data.get('cambio', 0)
        importe_efectivo = ticket_data.get('importe_efectivo', 0)
        importe_tarjeta = ticket_data.get('importe_tarjeta', 0)

        def fmt(v):
            return self._format_currency(v)

        # 1) Siempre mostrar tipo de pago
        tipo_line = f"Tipo de pago: {forma}"
        lines.append(tipo_line[: self.WIDTH])

        f_low = forma.lower()
        # 2) Si es tarjeta o web: no mostrar más
        if f_low in ('tarjeta', 'web'):
            pass
        # 3) Si es efectivo: mostrar Entregado / Cambio alineado
        elif f_low in ('efectivo', 'cash'):
            left = f"Entregado: {fmt(entr)}"
            right = f"Cambio: {fmt(dev)}"
            space = self.WIDTH - len(left) - len(right)
            if space < 1:
                space = 1
            lines.append((left + (' ' * space) + right)[: self.WIDTH])
        # 4) Si es mixto/multi: mostrar desglose efectivo / tarjeta
        elif f_low in ('mixto', 'multi'):
            left = f"Cash: {fmt(importe_efectivo)}"
            right = f"Tarjeta: {fmt(importe_tarjeta)}"
            space = self.WIDTH - len(left) - len(right)
            if space < 1:
                space = 1
            lines.append((left + (' ' * space) + right)[: self.WIDTH])
        else:
            # Otros: no añadir líneas adicionales
            pass

        # Fidelización
        if cliente_data:
            nombre_cliente = cliente_data.get('nombre', '')
            nivel = cliente_data.get('nivel', '')
            lines.append(self.DIVIDER)
            # Línea 1: nombre + Lv.X (centrado)
            level_num = cliente_data.get('level_num', '')
            if level_num:
                fame = f"<<<<<<<<<< {nombre_cliente} Lv.{level_num} >>>>>>>>>"
            else:
                fame = f"<<<<<<<<<< {nombre_cliente} >>>>>>>>>"
            if len(fame) > self.WIDTH:
                fame = fame[: self.WIDTH]
            lines.append(fame.center(self.WIDTH))
            # Línea 2: grafismo (izq) + nombre_nivel (der)
            grafismo = cliente_data.get('grafismo', '')
            if grafismo or nivel:
                left_part = grafismo or ''
                right_part = nivel or ''
                espacios = self.WIDTH - len(left_part) - len(right_part)
                if espacios < 0:
                    espacios = 0
                nivel_line = left_part + (' ' * espacios) + right_part
                lines.append(nivel_line[: self.WIDTH])

            # tesoro lines
            gasto_hoy = ticket_data.get('tesoro_data', {}).get('gastado', 0)
            acumulado = ticket_data.get('tesoro_data', {}).get('acumulado', 0)
            ganado = ticket_data.get('tesoro_data', {}).get('ganado', 0)
            total_tesoro = ticket_data.get('tesoro_data', {}).get('total', 0)

            lines.append(self._format_line_lr("Tesoro gastado hoy:", '-' + self._format_currency(gasto_hoy)))
            lines.append(self._format_line_lr("Tesoro acumulado:", self._format_currency(acumulado)))
            lines.append(self._format_line_lr("Tesoro ganado:", self._format_currency(ganado)))
            lines.append(self._format_line_lr("Tesoro Total:", self._format_currency(total_tesoro)))

        # Pie: soporte footer por tipo con fallback al footer genérico
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))
        else:
            lines.extend(self._format_footer(config))

        return "\n".join(lines)
