"""
Generador de ticket para cierres (resumen de caja / Cierre Z).

Proporciona un formato compacto listando tickets incluidos en el cierre,
con número de ventas por ticket, totales parciales y el total del cierre.
"""

from decimal import Decimal
import logging
import textwrap
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

    def _format_entry(self, left: str, right: str) -> str:
        """Formatear línea de desglose: left con wrap + right alineado a la derecha.

        Si left + right no caben en WIDTH, se hace word-wrap de left a líneas
        adicionales. El importe (right) queda alineado a la derecha en la
        última línea.
        """
        right = right.rjust(len(right))
        space = self.WIDTH - len(right)
        if space <= 0:
            return right[-self.WIDTH:]
        if len(left) <= space:
            return f"{left:<{space}}{right}"

        # Wrap de left: las líneas no-finales usan WIDTH completo,
        # la última línea usa 'space' para dejar sitio a right.
        wrapped = textwrap.wrap(left, width=self.WIDTH)
        if not wrapped:
            return f"{'':<{space}}{right}"

        if len(wrapped[-1]) <= space:
            result = wrapped[:-1] + [f"{wrapped[-1]:<{space}}{right}"]
            return "\n".join(result)

        # La última línea no cabe en 'space': re-wrap para que quepa
        last = wrapped.pop()
        sub = textwrap.wrap(last, width=space)
        if sub:
            result = wrapped + sub[:-1] + [f"{sub[-1]:<{space}}{right}"]
        else:
            result = wrapped + [f"{'':<{space}}{right}"]
        return "\n".join(result)

    def generate(self, config, cierre_data, tickets, totals: dict = None, print_options: dict = None):
        """Generador de tickets de cierre.

        print_options (dict): Opcional. Claves "4", "6", "7", "8", "9", "11", "12" como booleanos.
        """
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
        # Backwards compatibility and robust keys: try 'usuario' then 'cajero'
        usuario = ''
        if cierre_data:
            usuario = cierre_data.get('usuario') or cierre_data.get('cajero') or ''
        
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
                total_ventas_net = total_facturas_amt
            else:
                # Override: no restar devoluciones (doble conteo)
                total_ventas_net = total_facturas_amt

            lines.append('VENTAS:'.center(self.WIDTH))

            # Facturas Simplificadas: cuenta a la izquierda, suma a la derecha
            fs_left = f"Facturas Simplificadas: {ventas_count}"
            fs_right = self._format_currency(total_facturas_amt)
            space = self.WIDTH - len(fs_left) - len(fs_right)
            if space < 1:
                lines.append((fs_left + ' ' + fs_right)[: self.WIDTH])
            else:
                lines.append(fs_left + (' ' * space) + fs_right)

            # Total Descuentos (si existe)
            if totals and isinstance(totals, dict):
                td = totals.get('total_descuentos')
                if td and _to_decimal(td) > _D('0'):
                    lines.append(self._format_line_lr('Descuentos:', f"-{self._format_currency(_to_decimal(td))}"))

            # Separador y total neto de ventas
            lines.append(self.DIVIDER)
            lines.append(self._format_line_lr('TOTAL VENTAS:', self._format_currency(total_ventas_net)))

            # Sección informativa de devoluciones (no afecta a totales)
            if devoluciones_count:
                lines.append(self.DIVIDER)
                lines.append('DEVOLUCIONES (INFORMATIVO)'.center(self.WIDTH))
                left = f"Devoluciones: {devoluciones_count}"
                right = f"-{self._format_currency(total_devoluciones_amt)}"
                lines.append(self._format_line_lr(left, right))
        except Exception:
            pass

        # --- BLOQUE 10: DESGLOSE IVA ---
        try:
            if totals and isinstance(totals, dict):
                lines.append(self.DIVIDER)
                lines.append('DESGLOSE IVA'.center(self.WIDTH))
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
                if 'total_base_imponible' in totals:
                    lines.append(self._format_line_lr('Base Imponible:', self._format_currency(_to_decimal(totals.get('total_base_imponible', 0)))))
                if 'total_iva' in totals:
                    lines.append(self._format_line_lr('Total IVA:', self._format_currency(_to_decimal(totals.get('total_iva', 0)))))
        except Exception:
            pass

        # --- BLOQUE 4: RESUMEN FINANCIERO (MANDATORIO) ---
        try:
            lines.append(self.DOUBLE_DIVIDER)
            lines.append('RESUMEN FINANCIERO'.center(self.WIDTH))
            lines.append(self._format_line_lr('Tickets incluidos:', str(len(tickets or []))))

            if totals and isinstance(totals, dict):
                te = _to_decimal(totals.get('total_efectivo', _D('0')))
                tt = _to_decimal(totals.get('total_tarjeta', _D('0')))
                tw = _to_decimal(totals.get('total_web', _D('0')))
                td = _to_decimal(totals.get('total_devoluciones', _D('0')))
                if te != _D('0'):
                    lines.append(self._format_line_lr('Total Efectivo:', self._format_currency(te)))
                if tt != _D('0'):
                    lines.append(self._format_line_lr('Total Tarjeta:', self._format_currency(tt)))
                if tw != _D('0'):
                    lines.append(self._format_line_lr('Total Web:', self._format_currency(tw)))
                lines.append(self.DIVIDER)
        except Exception:
            pass

        total_mostrar = total_ventas_net if total_ventas_net is not None else total_general
        lines.append(self._format_line_lr('Total Formas de Pago:', self._format_currency(total_mostrar)))
        lines.append(self.DOUBLE_DIVIDER)

        # --- BLOQUE 5: VENTAS POR CAJERO (OBLIGATORIO) ---
        try:
            vpc = totals.get('ventas_por_cajero') if totals else None
            if vpc:
                lines.append('VENTAS POR CAJERO'.center(self.WIDTH))
                lines.append(self.DIVIDER)
                for entry in vpc:
                    try:
                        nombre = str(entry[0] or '')
                        v_cnt = int(entry[1] or 0)
                        v_total = entry[2] or 0
                        d_cnt = int(entry[3] or 0) if len(entry) > 3 else 0
                        d_total = entry[4] if len(entry) > 4 else 0
                        v_str = self._format_currency(_to_decimal(v_total))
                        lines.append(self._format_entry(f"{nombre}: {v_cnt}", v_str))
                        if d_cnt > 0:
                            d_str = f"-{self._format_currency(_to_decimal(d_total))}"
                            lines.append(self._format_entry(f"{nombre} Devoluciones: {d_cnt}", d_str))
                            neto = _to_decimal(v_total) - _to_decimal(d_total)
                            neto_str = self._format_currency(neto)
                            lines.append(self._format_entry(f"{nombre} Total:", neto_str))
                    except Exception:
                        continue
                lines.append(self.DOUBLE_DIVIDER)
        except Exception:
            pass

        # --- BLOQUE 6: VENTAS POR CATEGORÍA ---
        show_block_6 = print_options.get("6", True) if print_options else True
        if show_block_6:
            try:
                vpcat = totals.get('ventas_por_categoria') if totals else None
                if vpcat:
                    lines.append('VENTAS POR CATEGORÍA'.center(self.WIDTH))
                    lines.append(self.DIVIDER)
                    for entry in vpcat:
                        try:
                            nombre = str(entry[0] or '')
                            cnt = int(entry[1] or 0)
                            total_val = entry[2] or 0
                            total_str = self._format_currency(_to_decimal(total_val))
                            left = f"{nombre}: {cnt}"
                            lines.append(self._format_entry(left, total_str))
                        except Exception:
                            continue
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 7: DEVOLUCIONES POR CATEGORÍA ---
        show_block_7 = print_options.get("7", True) if print_options else True
        if show_block_7:
            try:
                devol_cat = totals.get('devoluciones_por_categoria') if totals else None
                if devol_cat:
                    lines.append('DEVOLUCIONES POR CATEGORÍA'.center(self.WIDTH))
                    lines.append(self.DIVIDER)
                    for entry in devol_cat:
                        try:
                            nombre = str(entry[0] or '')
                            cnt = int(entry[1] or 0)
                            total_val = entry[2] or 0
                            total_str = f"-{self._format_currency(_to_decimal(total_val))}"
                            left = f"{nombre}: {cnt}"
                            lines.append(self._format_entry(left, total_str))
                        except Exception:
                            continue
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 8: VENTAS POR TIPO ---
        show_block_8 = print_options.get("8", True) if print_options else True
        if show_block_8:
            try:
                vpt = totals.get('ventas_por_tipo') if totals else None
                if vpt:
                    lines.append('VENTAS POR TIPO'.center(self.WIDTH))
                    lines.append(self.DIVIDER)
                    for entry in vpt:
                        try:
                            nombre = str(entry[0] or '')
                            cnt = int(entry[1] or 0)
                            total_val = entry[2] or 0
                            total_str = self._format_currency(_to_decimal(total_val))
                            left = f"{nombre}: {cnt}"
                            lines.append(self._format_entry(left, total_str))
                        except Exception:
                            continue
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 9: DEVOLUCIONES POR TIPO ---
        show_block_9 = print_options.get("9", True) if print_options else True
        if show_block_9:
            try:
                dpt = totals.get('devoluciones_por_tipo') if totals else None
                if dpt:
                    lines.append('DEVOLUCIONES POR TIPO'.center(self.WIDTH))
                    lines.append(self.DIVIDER)
                    for entry in dpt:
                        try:
                            nombre = str(entry[0] or '')
                            cnt = int(entry[1] or 0)
                            total_val = entry[2] or 0
                            total_str = f"-{self._format_currency(_to_decimal(total_val))}"
                            left = f"{nombre}: {cnt}"
                            lines.append(self._format_entry(left, total_str))
                        except Exception:
                            continue
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 11: VENTAS POR PRODUCTO ---
        show_block_11 = print_options.get("11", True) if print_options else True
        if show_block_11:
            try:
                productos = totals.get('productos') if totals else None
                if productos:
                    lines.append('VENTAS POR PRODUCTO'.center(self.WIDTH))
                    for p in productos:
                        try:
                            nombre = str(p[0] or '')
                            tickets_cnt = int(p[1] or 0)
                            uds = int(p[2] or 0)
                            total_p = self._format_currency(_to_decimal(p[3] or 0))
                            left = f"{nombre}: {tickets_cnt} ({uds}uds)"
                            lines.append(self._format_entry(left, total_p))
                        except Exception:
                            try:
                                lines.append(f"{p[0]} - {p[1]} - {p[2]} - {p[3]}")
                            except Exception:
                                pass
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 11b: DEVOLUCIONES POR PRODUCTO ---
        if show_block_11:
            try:
                devol_productos = totals.get('devoluciones_por_producto') if totals else None
                if devol_productos:
                    lines.append('DEVOLUCIONES POR PRODUCTO'.center(self.WIDTH))
                    for p in devol_productos:
                        try:
                            nombre = str(p[0] or '')
                            tickets_cnt = int(p[1] or 0)
                            uds = int(p[2] or 0)
                            total_p = f"-{self._format_currency(_to_decimal(p[3] or 0))}"
                            left = f"{nombre}: {tickets_cnt} ({uds}uds)"
                            lines.append(self._format_entry(left, total_p))
                        except Exception:
                            try:
                                lines.append(f"{p[0]} - {p[1]} - {p[2]} - {p[3]}")
                            except Exception:
                                pass
                    lines.append(self.DOUBLE_DIVIDER)
            except Exception:
                pass

        # --- BLOQUE 12: PUNTOS DE TESORO ---
        show_block_12 = print_options.get("12", True) if print_options else True
        if show_block_12:
            try:
                tesoro_otorgado = _to_decimal(totals.get('tesoro_otorgado', _D('0'))) if totals else _D('0')
                tesoro_gastado = _to_decimal(totals.get('tesoro_gastado', _D('0'))) if totals else _D('0')
                clientes_puntos = totals.get('clientes_puntos', []) if totals else []
                if tesoro_otorgado > _D('0') or tesoro_gastado > _D('0') or clientes_puntos:
                    lines.append('=' * self.WIDTH)
                    lines.append('PUNTOS DE TESORO'.center(self.WIDTH))
                    if tesoro_otorgado > _D('0') or tesoro_gastado > _D('0'):
                        val_ganados = self._format_currency(tesoro_otorgado / _D('100'))
                        val_gastados = f"-{self._format_currency(tesoro_gastado / _D('100'))}"
                        lines.append(self._format_line_lr('Tesoro ganado:', val_ganados))
                        lines.append(self._format_line_lr('Tesoro gastado:', val_gastados))
                    if clientes_puntos:
                        lines.append('-' * self.WIDTH)
                        for cliente in clientes_puntos:
                            try:
                                nombre = cliente.get('cliente_nombre', '')
                                nivel_level = cliente.get('nivel_level', 0)
                                nivel = cliente.get('nivel_nombre', '')
                                g_pts = _to_decimal(cliente.get('puntos_ganados', 0)) / _D('100')
                                s_pts = _to_decimal(cliente.get('puntos_gastados', 0)) / _D('100')
                                g_str = self._format_currency(g_pts)
                                s_str = f"-{self._format_currency(s_pts)}"
                                header = f"{nombre} (Lv {nivel_level} - {nivel}):"
                                lines.append(header[:self.WIDTH])
                                lines.append(self._format_line_lr('  Tesoro ganado:', g_str))
                                if s_pts > _D('0'):
                                    lines.append(self._format_line_lr('  Tesoro gastado:', s_str))
                            except Exception:
                                continue
                    lines.append('=' * self.WIDTH)
            except Exception as e:
                logging.exception(f'Error agregando bloque de tesoro: {e}')

        # Footer para cierre: solo añadir si existe la clave específica en config
        footer_val = config.get(footer_key)
        if footer_val:
            lines.extend(self._render_template(footer_val, context))

        # Nota: si no hay footer específico, mantener comportamiento actual

        logging.info(f"DEBUG RETURN: líneas totales={len(lines)}")
        logging.info(f"DEBUG RETURN: ¿Contiene 'TESORO'? {'TESORO' in '\n'.join(lines)}")
        texto_final = "\n".join(lines)
        logging.info(f"DEBUG RETURN: texto_final length={len(texto_final)}")
        return texto_final
