"""
Generador de ticket para cierres (resumen de caja / Cierre Z).

Proporciona un formato compacto listando tickets incluidos en el cierre,
con número de ventas por ticket, totales parciales y el total del cierre.
"""
from decimal import Decimal
from kool_tpv.modulos.impresion.base_ticket_generator import BaseTicketGenerator


class CierreTicketGenerator(BaseTicketGenerator):
    """Generador de tickets de cierre.

    Contrato:
      - `config`: dict con datos del comercio (nombre_negocio, direccion, nif, pie_texto)
      - `cierre_data`: dict con 'fecha', 'hora', 'usuario', 'cierre_id' (opcionales)
      - `tickets`: lista de dicts con {'id', 'num_ventas', 'total'} donde `total` debe ser
        un `Decimal` expresando euros (no float). El generador trabaja internamente con
        `Decimal` para todos los importes.
      - `totals` (opcional): dict con totales y desgloses; sus valores monetarios
        también deben ser `Decimal` (euros). El generador convertirá entradas no-Decimal
        cuando sea posible, pero la interfaz preferida es `Decimal`.

    Devuelve el texto completo del ticket de cierre.
    """

    def generate(self, config, cierre_data, tickets, totals: dict = None):
        from decimal import Decimal as _D

        def _to_decimal(v):
            if isinstance(v, Decimal):
                return v
            try:
                return _D(str(v))
            except Exception:
                return _D('0')

        lines = []

        # Construir contexto para placeholders de cierre
        fecha = cierre_data.get('fecha', '') if cierre_data else ''
        hora = cierre_data.get('hora', '') if cierre_data else ''
        usuario = cierre_data.get('usuario', '') if cierre_data else ''
        cierre_id = cierre_data.get('cierre_id', '') if cierre_data else ''
        cierre_text = cierre_data.get('cierre_text', '') if cierre_data else ''
        context = {
            'fecha': fecha,
            'hora': hora,
            'usuario': usuario,
            'cierre_id': cierre_id,
            'cierre_text': cierre_text,
        }

        header_key = 'ticket_header_cierre'
        footer_key = 'ticket_footer_cierre'
        header_val = config.get(header_key)
        if header_val:
            lines.extend(self._render_template(header_val, context))
        else:
            lines.extend(self._format_header(config))

        lines.append(self.DOUBLE_DIVIDER)

        info = f"{fecha} {hora}  Usuario: {usuario}"
        # Mostrar fecha/hora y usuario en la primera línea (no incluir aquí cierre_text)
        lines.append(info[: self.WIDTH])
        # El identificador del cierre en su propia línea; incluir primero cierre_text, luego el id
        # Mostrar solo el `cierre_text` (el código humano). No añadir el id numérico final.
        if cierre_text:
            lines.append(f"Cierre ID: {cierre_text}"[: self.WIDTH])
        lines.append(self.DIVIDER)

        # BLOQUE DE VENTAS: renderizado reemplazado.
        # Se conserva el cálculo de totales y la separación en filas para uso
        # posterior; el renderizado de filas ha sido eliminado y se añadirá
        # un nuevo bloque aquí cuando se indique.
        total_general = Decimal('0')
        total_ventas = 0
        ventas_rows = []
        devoluciones_rows = []
        for t in tickets or []:
            try:
                tid = str(t.get('id') or '')
                nventas = int(t.get('num_ventas') or 0)
                total = _to_decimal(t.get('total', _D('0')))
            except Exception:
                tid = str(t.get('id', ''))
                nventas = 0
                total = _to_decimal(0)

            total_general += total
            total_ventas += nventas

            entry = (tid, nventas, total)
            if total < 0:
                devoluciones_rows.append(entry)
            else:
                ventas_rows.append(entry)

        # Nuevo bloque 'VENTAS' (Facturas Simplificadas, Devoluciones y TOTAL)
        try:
            # Preferir los agregados pasados en `totals` (calculados por el processor)
            ventas_count = None
            devoluciones_count = None
            total_facturas_amt = None
            total_devoluciones_amt = None
            total_ventas_net = None

            if totals and isinstance(totals, dict):
                ventas_count = totals.get('ventas_count')
                devoluciones_count = totals.get('devoluciones_count')
                total_facturas_amt = totals.get('total_facturas')
                total_devoluciones_amt = totals.get('total_devoluciones')
                total_ventas_net = totals.get('total_ventas_net')

            # Fallback a cálculo local si no se proporcionaron valores
            if ventas_count is None:
                ventas_count = len(ventas_rows)
            if devoluciones_count is None:
                devoluciones_count = len(devoluciones_rows)
            if total_facturas_amt is None:
                # sumar solo filas de ventas (valores positivos)
                try:
                    total_facturas_amt = sum([v[2] for v in ventas_rows], Decimal('0'))
                except Exception:
                    total_facturas_amt = Decimal('0')
            if total_devoluciones_amt is None:
                try:
                    total_devoluciones_amt = sum([abs(d[2]) for d in devoluciones_rows], Decimal('0'))
                except Exception:
                    total_devoluciones_amt = Decimal('0')
            if total_ventas_net is None:
                try:
                    # Los descuentos YA están incluidos en total_facturas_amt
                    # Solo restar devoluciones, no restar descuentos de nuevo
                    total_ventas_net = total_facturas_amt - total_devoluciones_amt
                except Exception:
                    total_ventas_net = Decimal('0')

            lines.append('VENTAS:'.center(self.WIDTH))

            # Facturas Simplificadas: cuenta a la izquierda, suma a la derecha
            fs_left = f"Facturas Simplificadas: {ventas_count}"
            fs_right = self._format_currency(total_facturas_amt)
            space = self.WIDTH - len(fs_left) - len(fs_right)
            if space < 1:
                lines.append((fs_left + ' ' + fs_right)[: self.WIDTH])
            else:
                lines.append(fs_left + (' ' * space) + fs_right)

            # Devoluciones: mostrar recuento sin signo y total negativo a la derecha
            if devoluciones_count:
                left = f"Devoluciones: {devoluciones_count}"
                right = f"-{self._format_currency(total_devoluciones_amt)}"
                lines.append(self._format_line_lr(left, right))

            # Total Descuentos (si existe)
            if totals and isinstance(totals, dict):
                td = totals.get('total_descuentos')
                if td and _to_decimal(td) > _D('0'):
                    lines.append(self._format_line_lr('Descuentos:', f"-{self._format_currency(_to_decimal(td))}"))

            # Separador y total neto de ventas
            lines.append(self.DIVIDER)
            lines.append(self._format_line_lr('TOTAL VENTAS:', self._format_currency(total_ventas_net)))
        except Exception:
            # No fallar la generación del ticket por este bloque
            pass

        # Separador y título del bloque resumen/totales
        lines.append(self.DOUBLE_DIVIDER)
        lines.append('RESUMEN FINANCIERO'.center(self.WIDTH))
        lines.append(self._format_line_lr('Tickets incluidos:', str(len(tickets or []))))

        # Nota: el importe total de devoluciones se muestra únicamente en el
        # bloque 'VENTAS' (línea "Devoluciones: <count>    -<importe>").
        # No repetirlo en el RESUMEN FINANCIERO. (Cálculos ya realizados arriba.)

        # Mostrar totales por forma de pago si se proporcionan en `totals`
        try:
            if totals and isinstance(totals, dict):
                te = _to_decimal(totals.get('total_efectivo', _D('0')))
                tt = _to_decimal(totals.get('total_tarjeta', _D('0')))
                tw = _to_decimal(totals.get('total_web', _D('0')))
                if te != _D('0'):
                    lines.append(self._format_line_lr('Total Efectivo:', self._format_currency(te)))
                if tt != _D('0'):
                    lines.append(self._format_line_lr('Total Tarjeta:', self._format_currency(tt)))
                if tw != _D('0'):
                    lines.append(self._format_line_lr('Total Web:', self._format_currency(tw)))
                # Añadir separador sencillo entre los totales por forma de pago y el total general
                lines.append(self.DIVIDER)
        except Exception:
            pass

        # Nota: el importe total de devoluciones se muestra únicamente en el
        # bloque 'VENTAS' (línea "Devoluciones: <count>    -<importe>").
        # No repetirlo en el RESUMEN FINANCIERO.

        # Mostrar total neto bajo la etiqueta 'Total Formas de Pago' (incluye descuentos y devoluciones)
        total_mostrar = total_ventas_net if total_ventas_net is not None else total_general
        lines.append(self._format_line_lr('Total Formas de Pago:', self._format_currency(total_mostrar)))
        lines.append(self.DOUBLE_DIVIDER)

        # Secciones adicionales: ventas por forma de pago, por cajero y por categoría
        # 'Ventas por forma de pago' eliminado intencionalmente — no mostrar.

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
                        total_str = self._format_currency(_to_decimal(total_val))
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
                        total_str = self._format_currency(_to_decimal(total_val))
                        line = f"{nombre} - {cnt} - {total_str}"
                        lines.append(line[: self.WIDTH])
                    except Exception:
                        continue
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # DEVOLUCIONES POR CATEGORÍA: mostrar solo si existen devoluciones agrupadas
        try:
            devol_cat = None
            if totals and isinstance(totals, dict):
                devol_cat = totals.get('devoluciones_por_categoria')
            if devol_cat:
                lines.append('DEVOLUCIONES POR CATEGORÍA'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in devol_cat:
                    try:
                        nombre = str(entry[0] or '')
                        cnt = int(entry[1] or 0)
                        total_val = entry[2] or 0
                        # Mostrar importe de devoluciones con signo negativo
                        total_str = f"-{self._format_currency(_to_decimal(total_val))}"
                        line = f"{nombre} - {cnt} - {total_str}"
                        lines.append(line[: self.WIDTH])
                    except Exception:
                        continue
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # VENTAS POR TIPO: igual formato que VENTAS POR CATEGORÍA (solo ventas)
        try:
            vpt = None
            if totals and isinstance(totals, dict):
                vpt = totals.get('ventas_por_tipo')
            if vpt:
                lines.append('VENTAS POR TIPO'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in vpt:
                    try:
                        nombre = str(entry[0] or '')
                        cnt = int(entry[1] or 0)
                        total_val = entry[2] or 0
                        total_str = self._format_currency(_to_decimal(total_val))
                        line = f"{nombre} - {cnt} - {total_str}"
                        lines.append(line[: self.WIDTH])
                    except Exception:
                        continue
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # DEVOLUCIONES POR TIPO: mostrar solo si existen devoluciones agrupadas por tipo
        try:
            dpt = None
            if totals and isinstance(totals, dict):
                dpt = totals.get('devoluciones_por_tipo')
            if dpt:
                lines.append('DEVOLUCIONES POR TIPO'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in dpt:
                    try:
                        nombre = str(entry[0] or '')
                        cnt = int(entry[1] or 0)
                        total_val = entry[2] or 0
                        total_str = f"-{self._format_currency(_to_decimal(total_val))}"
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
                    lines.append(self._format_line_lr('Base 21%:', self._format_currency(_to_decimal(base21))))
                    lines.append(self._format_line_lr('IVA 21%:', self._format_currency(_to_decimal(iva21))))
                if 'base_4' in totals or 'iva_4' in totals:
                    base4 = totals.get('base_4', 0)
                    iva4 = totals.get('iva_4', 0)
                    lines.append(self._format_line_lr('Base 4%:', self._format_currency(_to_decimal(base4))))
                    lines.append(self._format_line_lr('IVA 4%:', self._format_currency(_to_decimal(iva4))))
                # totales
                if 'total_base_imponible' in totals:
                    lines.append(self._format_line_lr('Base Imponible:', self._format_currency(_to_decimal(totals.get('total_base_imponible', 0)))))
                if 'total_iva' in totals:
                    lines.append(self._format_line_lr('Total IVA:', self._format_currency(_to_decimal(totals.get('total_iva', 0)))))
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
                        total_p = self._format_currency(_to_decimal(p[3] or 0))
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

        # (Sección de Categorías removida: usar `ventas_por_categoria` / `devoluciones_por_categoria`)

        # (Sección de Tipos removida: usar `ventas_por_tipo` / `devoluciones_por_tipo`)

        # Footer para cierre: solo añadir si existe la clave específica en config
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))

        # Nota: si no hay footer específico, mantener comportamiento actual

        return "\n".join(lines)
