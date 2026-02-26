"""
Generador de tickets de venta.

Hereda de BaseTicketGenerator y usa sus helpers comunes.
"""
from decimal import Decimal
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
        header_val = config.get(header_key)
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

        info_line = f"{fecha} {hora} - {cajero} - Ticket: {num}"
        if len(info_line) > self.WIDTH:
            info_line = info_line[: self.WIDTH]
        lines.append(info_line)
        lines.append(self.DIVIDER)

        # Cuerpo
        lines.append("Cant | Articulo               | PVP | Total")

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
                left_part = f"-{cant_int}x {nombre_item}"
            else:
                pvp_display = pvp_s
                total_display = total_s
                left_part = f"{cant_int}x {nombre_item}"

            right_part = f"{pvp_display} {total_display}"

            # compute available space for left_part
            space_for_left = self.WIDTH - len(right_part) - 1
            if space_for_left < 0:
                space_for_left = 0
            if len(left_part) > space_for_left:
                left_part = left_part[:space_for_left]

            line = left_part.ljust(space_for_left) + ' ' + right_part
            lines.append(line)

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

        # Tabla pago: 4 columnas ajustadas para WIDTH=42
        col1_w, col2_w, col3_w, col4_w = 9, 10, 10, 10
        header = f"{'Pago':<{col1_w}}|{'Total':<{col2_w}}|{'Entr.':<{col3_w}}|{'Dev.':<{col4_w}}"
        lines.append(header[: self.WIDTH])

        forma = (ticket_data.get('forma_pago') or '').strip()
        entr = ticket_data.get('entregado', 0)
        dev = ticket_data.get('cambio', 0)
        importe_efectivo = ticket_data.get('importe_efectivo', 0)
        importe_tarjeta = ticket_data.get('importe_tarjeta', 0)

        def fmt(v):
            return self._format_currency(v)

        # Para presentaciones de devolución ajustamos columnas Entr./Dev. (solo presentación)
        if forma.lower() == 'mixto':
            if is_devolucion:
                # Efectivo: mostrar total negativo en Total y en Dev., Entr. = 0
                l1 = f"{'Efectivo':<{col1_w}}|{fmt(importe_efectivo):>{col2_w}}|{fmt(0):>{col3_w}}|{fmt(importe_efectivo):>{col4_w}}"
                lines.append(l1[: self.WIDTH])
                # Tarjeta: idem
                l2 = f"{'Tarjeta':<{col1_w}}|{fmt(importe_tarjeta):>{col2_w}}|{fmt(0):>{col3_w}}|{fmt(importe_tarjeta):>{col4_w}}"
                lines.append(l2[: self.WIDTH])
            else:
                # Linea Efectivo
                l1 = f"{'Efectivo':<{col1_w}}|{fmt(importe_efectivo):>{col2_w}}|{fmt(importe_efectivo):>{col3_w}}|{fmt(0):>{col4_w}}"
                lines.append(l1[: self.WIDTH])
                # Linea Tarjeta
                l2 = f"{'Tarjeta':<{col1_w}}|{fmt(importe_tarjeta):>{col2_w}}|{fmt(importe_tarjeta):>{col3_w}}|{fmt(0):>{col4_w}}"
                lines.append(l2[: self.WIDTH])
        else:
            # Single payment row
            if is_devolucion:
                display_entr = 0
                display_dev = total
            else:
                display_entr = entr
                display_dev = dev
            row = f"{forma[:col1_w]:<{col1_w}}|{fmt(total):>{col2_w}}|{fmt(display_entr):>{col3_w}}|{fmt(display_dev):>{col4_w}}"
            lines.append(row[: self.WIDTH])

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
