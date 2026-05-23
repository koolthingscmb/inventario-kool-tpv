"""
Generador de ticket para cierres (resumen de caja / Cierre Z).

Proporciona un formato compacto listando tickets incluidos en el cierre,
con número de ventas por ticket, totales parciales y el total del cierre.
"""
from decimal import Decimal
from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class CierreTicketGenerator(BaseTicketGenerator):
    """Generador de tickets de cierre.

    Método `generate` espera:
      - config: dict con datos del comercio (nombre_negocio, direccion, nif, pie_texto)
      - cierre_data: dict con 'fecha', 'hora', 'usuario', 'cierre_id' (opcionales)
      - tickets: lista de dicts con {'id', 'num_ventas', 'total'}

    Devuelve el texto completo del ticket de cierre.
    """

    def generate(self, config, cierre_data, tickets, totals: dict = None):
        lines = []

        # Construir contexto para placeholders de cierre
        fecha = cierre_data.get('fecha', '') if cierre_data else ''
        hora = cierre_data.get('hora', '') if cierre_data else ''
        usuario = cierre_data.get('usuario', '') if cierre_data else ''
        cierre_id = cierre_data.get('cierre_id', '') if cierre_data else ''
        context = {
            'fecha': fecha,
            'hora': hora,
            'usuario': usuario,
            'cierre_id': cierre_id,
        }

        # Soportar header por tipo 'cierre' con fallback al header genérico
        header_key = 'ticket_header_cierre'
        footer_key = 'ticket_footer_cierre'
        header_val = config.get(header_key)
        if header_val:
            lines.extend(self._render_template(header_val, context))
        else:
            lines.extend(self._format_header(config))

        lines.append(self.DOUBLE_DIVIDER)
        lines.append('CIERRE DE CAJA'.center(self.WIDTH))
        lines.append(self.DIVIDER)

        fecha = cierre_data.get('fecha', '') if cierre_data else ''
        hora = cierre_data.get('hora', '') if cierre_data else ''
        usuario = cierre_data.get('usuario', '') if cierre_data else ''
        cierre_id = cierre_data.get('cierre_id', '') if cierre_data else ''

        info = f"{fecha} {hora}  Usuario: {usuario}"
        if cierre_id:
            info = f"{info}  ID:{cierre_id}"
        lines.append(info[: self.WIDTH])
        lines.append(self.DIVIDER)

        # Cabecera de tabla interna
        header = f"{'ID':<8}{'Ventas':<10}{'Total':>{self.WIDTH-18}}"
        lines.append(header[: self.WIDTH])
        lines.append(self.DIVIDER)

        total_general = Decimal('0')
        total_ventas = 0
        # separar ventas y devoluciones para presentar en secciones distintas
        ventas_rows = []
        devoluciones_rows = []
        for t in tickets or []:
            try:
                tid = str(t.get('id') or '')
                nventas = int(t.get('num_ventas') or 0)
                total = Decimal(str(t.get('total') or 0))
            except Exception:
                tid = str(t.get('id', ''))
                nventas = 0
                total = Decimal('0')

            total_general += total
            total_ventas += nventas

            entry = (tid, nventas, total)
            if total < 0:
                devoluciones_rows.append(entry)
            else:
                ventas_rows.append(entry)

        # renderizar ventas (excluir devoluciones)
        for tid, nventas, total in ventas_rows:
            left = f"{tid:<8}{nventas:<10}"
            right = self._format_currency(total)
            # rellenar hasta WIDTH
            space = self.WIDTH - len(left) - len(right)
            if space < 1:
                line = (left + ' ' + right)[: self.WIDTH]
            else:
                line = left + (' ' * space) + right
            lines.append(line)
        # Sección Devoluciones (mostrar separadas si existen) - situada justo tras las ventas
        try:
            if devoluciones_rows:
                lines.append(self.DIVIDER)
                lines.append('DEVOLUCIONES'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for tid, nventas, total in devoluciones_rows:
                    # Mostrar importe en negativo tal cual
                    display_total = f"-{self._format_currency(abs(total))}"
                    left = f"{tid:<8}{nventas:<10}"
                    space = self.WIDTH - len(left) - len(display_total)
                    if space < 1:
                        line = (left + ' ' + display_total)[: self.WIDTH]
                    else:
                        line = left + (' ' * space) + display_total
                    lines.append(line)
        except Exception:
            pass

        # Separador y título del bloque resumen/totales
        lines.append(self.DOUBLE_DIVIDER)
        lines.append('RESUMEN FINANCIERO'.center(self.WIDTH))
        lines.append(self._format_line_lr('Tickets incluidos:', str(len(tickets or []))))
        lines.append(self._format_line_lr('Unidades/ líneas vendidas:', str(total_ventas)))

        # Devoluciones totales: mostrar sólo el recuento aquí
        try:
            devol_count = len(devoluciones_rows)
            devol_sum = sum([d[2] for d in devoluciones_rows], Decimal('0')) if devol_count else Decimal('0')
            if devol_count:
                lines.append(self._format_line_lr('Devoluciones totales:', str(devol_count)))
        except Exception:
            devol_count = 0
            devol_sum = Decimal('0')

        # Mostrar totales por forma de pago si se proporcionan en `totals`
        try:
            if totals and isinstance(totals, dict):
                te = totals.get('total_efectivo', 0) or 0
                tt = totals.get('total_tarjeta', 0) or 0
                tw = totals.get('total_web', 0) or 0
                if te and float(te) != 0:
                    lines.append(self._format_line_lr('Total Efectivo:', self._format_currency(te)))
                if tt and float(tt) != 0:
                    lines.append(self._format_line_lr('Total Tarjeta:', self._format_currency(tt)))
                if tw and float(tw) != 0:
                    lines.append(self._format_line_lr('Total Web:', self._format_currency(tw)))
                # Mostrar total de descuentos si existe
                td = totals.get('total_descuentos', 0) if isinstance(totals, dict) else 0
                try:
                    if td and float(td) != 0:
                        lines.append(self._format_line_lr('Total Descuentos:', f"-{self._format_currency(td)}"))
                except Exception:
                    pass
        except Exception:
            pass

        # Mostrar importe total de devoluciones (negativo) si existen devoluciones
        try:
            if devol_count and float(devol_sum) != 0:
                lines.append(self._format_line_lr('Total Devoluciones:', f"-{self._format_currency(abs(devol_sum))}"))
        except Exception:
            pass

        lines.append(self._format_line_lr('Total cierre:', self._format_currency(total_general)))
        lines.append(self.DOUBLE_DIVIDER)

        # Secciones adicionales: ventas por forma de pago, por cajero y por categoría
        try:
            # 1) Ventas por forma de pago
            vpf = None
            if totals and isinstance(totals, dict):
                vpf = totals.get('ventas_por_forma_pago')
            if vpf:
                lines.append('VENTAS POR FORMA DE PAGO'.center(self.WIDTH))
                try:
                    # Mostrar claves conocidas con labels legibles
                    ef = int(vpf.get('efectivo', 0) or 0) if isinstance(vpf, dict) else 0
                    ta = int(vpf.get('tarjeta', 0) or 0) if isinstance(vpf, dict) else 0
                    web = int(vpf.get('web', 0) or 0) if isinstance(vpf, dict) else 0
                except Exception:
                    ef = ta = web = 0
                lines.append(self._format_line_lr('Ventas Efectivo:', str(ef)))
                lines.append(self._format_line_lr('Ventas Tarjeta:', str(ta)))
                lines.append(self._format_line_lr('Ventas Web:', str(web)))
                lines.append(self.DIVIDER)
        except Exception:
            pass

        try:
            # 2) Ventas por cajero
            vpc = None
            if totals and isinstance(totals, dict):
                vpc = totals.get('ventas_por_cajero')
            if vpc:
                lines.append('VENTAS POR CAJERO'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in vpc:
                    try:
                        nombre = str(entry[0] or '')
                        cnt = int(entry[1] or 0)
                        total_val = entry[2] or 0
                        total_str = self._format_currency(total_val)
                        line = f"{nombre} - {cnt} - {total_str}"
                        lines.append(line[: self.WIDTH])
                    except Exception:
                        continue
                lines.append(self.DIVIDER)
        except Exception:
            pass

        try:
            # 3) Ventas por categoría
            vpcat = None
            if totals and isinstance(totals, dict):
                vpcat = totals.get('ventas_por_categoria')
            if vpcat:
                lines.append('VENTAS POR CATEGORÍA'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in vpcat:
                    try:
                        nombre = str(entry[0] or '')
                        cnt = int(entry[1] or 0)
                        total_val = entry[2] or 0
                        total_str = self._format_currency(total_val)
                        line = f"{nombre} - {cnt} - {total_str}"
                        lines.append(line[: self.WIDTH])
                    except Exception:
                        continue
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # Desglose IVA si se proporcionan totales
        try:
            if totals and isinstance(totals, dict):
                lines.append('DESGLOSE IVA'.center(self.WIDTH))
                # soportar claves base_21, iva_21, base_4, iva_4
                if 'base_21' in totals or 'iva_21' in totals:
                    base21 = totals.get('base_21', 0)
                    iva21 = totals.get('iva_21', 0)
                    lines.append(self._format_line_lr('Base 21%:', self._format_currency(base21)))
                    lines.append(self._format_line_lr('IVA 21%:', self._format_currency(iva21)))
                if 'base_4' in totals or 'iva_4' in totals:
                    base4 = totals.get('base_4', 0)
                    iva4 = totals.get('iva_4', 0)
                    lines.append(self._format_line_lr('Base 4%:', self._format_currency(base4)))
                    lines.append(self._format_line_lr('IVA 4%:', self._format_currency(iva4)))
                # totales
                if 'total_base_imponible' in totals:
                    lines.append(self._format_line_lr('Base Imponible:', self._format_currency(totals.get('total_base_imponible', 0))))
                if 'total_iva' in totals:
                    lines.append(self._format_line_lr('Total IVA:', self._format_currency(totals.get('total_iva', 0))))
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # Sección de Productos (opcional) si se proporcionó detalle en totals
        try:
            productos = None
            if totals and isinstance(totals, dict):
                productos = totals.get('productos')
            if productos:
                lines.append('VENTAS POR PRODUCTO'.center(self.WIDTH))
                # productos expected as iterable of (nombre, tickets_count, uds, total)
                for p in productos:
                    try:
                        nombre = str(p[0] or '')
                        tickets_cnt = int(p[1] or 0)
                        uds = int(p[2] or 0)
                        total_p = self._format_currency(p[3] or 0)
                        left = f"{nombre}: {tickets_cnt} ({uds}uds)"
                        # pad so total lines up on the right
                        space = self.WIDTH - len(left) - len(total_p)
                        if space < 1:
                            line = (left + ' ' + total_p)[: self.WIDTH]
                        else:
                            line = left + (' ' * space) + total_p
                        lines.append(line)
                    except Exception:
                        # Fallback simple join
                        try:
                            lines.append(f"{p[0]} - {p[1]} - {p[2]} - {p[3]}")
                        except Exception:
                            pass
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # Sección de Categorías (igual formato que productos)
        try:
            categorias = None
            if totals and isinstance(totals, dict):
                categorias = totals.get('categorias')
            if categorias:
                lines.append('VENTAS POR CATEGORÍA'.center(self.WIDTH))
                for c in categorias:
                    try:
                        nombre = str(c[0] or '')
                        tickets_cnt = int(c[1] or 0)
                        uds = int(c[2] or 0)
                        total_c = self._format_currency(c[3] or 0)
                        left = f"{nombre}: {tickets_cnt} ({uds}uds)"
                        space = self.WIDTH - len(left) - len(total_c)
                        if space < 1:
                            line = (left + ' ' + total_c)[: self.WIDTH]
                        else:
                            line = left + (' ' * space) + total_c
                        lines.append(line)
                    except Exception:
                        try:
                            lines.append(f"{c[0]} - {c[1]} - {c[2]} - {c[3]}")
                        except Exception:
                            pass
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # Sección de Tipos (igual formato que productos)
        try:
            tipos = None
            if totals and isinstance(totals, dict):
                tipos = totals.get('tipos')
            if tipos:
                lines.append('VENTAS POR TIPO'.center(self.WIDTH))
                for t in tipos:
                    try:
                        nombre = str(t[0] or '')
                        tickets_cnt = int(t[1] or 0)
                        uds = int(t[2] or 0)
                        total_t = self._format_currency(t[3] or 0)
                        left = f"{nombre}: {tickets_cnt} ({uds}uds)"
                        space = self.WIDTH - len(left) - len(total_t)
                        if space < 1:
                            line = (left + ' ' + total_t)[: self.WIDTH]
                        else:
                            line = left + (' ' * space) + total_t
                        lines.append(line)
                    except Exception:
                        try:
                            lines.append(f"{t[0]} - {t[1]} - {t[2]} - {t[3]}")
                        except Exception:
                            pass
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # Footer para cierre: solo añadir si existe la clave específica en config
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))

        # Nota: si no hay footer específico, mantener comportamiento actual

        return "\n".join(lines)
