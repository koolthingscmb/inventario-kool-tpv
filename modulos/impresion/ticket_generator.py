# modulos/impresion/ticket_generator.py

def generar_ticket(carrito, efectivo, cambio, nombre_tienda="KOOL DREAMS", cajero="EGON", ticket_id: int = None):
    from datetime import datetime
    lineas = []
    
    # Cabecera fija
    lineas.append(nombre_tienda)
    lineas.append("C/Juan Sebastián Elcano, 2")
    lineas.append("43850 Cambrils")
    lineas.append("NIF: 39887072N")
    lineas.append("-" * 30)
    
    import textwrap
    from datetime import datetime


    def generar_ticket(carrito, efectivo, cambio, nombre_tienda="KOOL DREAMS", cajero="EGON", ticket_id: int = None, width: int = 50):
        """Genera el texto del ticket y lo envuelve al ancho `width`.
        - `carrito` debe ser lista de dicts con keys: `nombre`, `cantidad`, `precio`, `iva`.
        - `efectivo` y `cambio` son numéricos.
        - `width` controla el máximo de caracteres por línea (por defecto 50).
        """
        lineas = []

        # Cabecera fija
        lineas.append(nombre_tienda)
        lineas.append("C/Juan Sebastián Elcano, 2")
        lineas.append("43850 Cambrils")
        lineas.append("NIF: 39887072N")
        lineas.append("-" * 30)

        # Factura y datos
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        # NOTA: número de ticket lo dejamos fijo por ahora (más adelante será secuencial)
        lineas.append("FACTURA Nº: 12345")
        lineas.append(f"Fecha: {ahora}")
        lineas.append(f"Cajero: {cajero}")
        lineas.append("-" * 30)

        # Productos
        for item in carrito:
            nombre = item.get('nombre', '')[:20]
            cantidad = item.get('cantidad', 0)
            precio = item.get('precio', 0.0)
            subtotal = cantidad * precio

            if isinstance(precio, (int, float)) and precio == int(precio):
                precio_str = f"({int(precio)})"
            else:
                try:
                    precio_str = f"({precio:.2f})"
                except Exception:
                    precio_str = f"({precio})"

            linea_base = f"{cantidad}x {nombre} {precio_str}"
            if len(linea_base) > 25:
                linea_base = linea_base[:25]
            linea_final = linea_base.ljust(25) + f"{subtotal:>7.2f}"
            lineas.append(linea_final)
# modulos/impresion/ticket_generator.py

from datetime import datetime
import textwrap
import logging


def generar_ticket(carrito, efectivo, cambio, nombre_tienda="KOOL DREAMS", cajero="EGON", ticket_id: int = None, width: int = 50, metodo_pago: str = 'EFECTIVO'):
    """Genera el texto del ticket y lo envuelve al ancho `width`.

    - `carrito` debe ser lista de dicts con keys: `nombre`, `cantidad`, `precio`, `iva`.
    - `efectivo` y `cambio` son numéricos.
    - `width` controla el máximo de caracteres por línea (por defecto 50).
    """
    try:
        lineas = []

        # Cabecera
        lineas.append(nombre_tienda)
        lineas.append("C/Juan Sebastián Elcano, 2")
        lineas.append("43850 Cambrils")
        lineas.append("NIF: 39887072N")
        lineas.append("-" * min(30, width))

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        if ticket_id is None:
            ticket_str = "FACTURA Nº: --"
        else:
            ticket_str = f"FACTURA Nº: {ticket_id}"
        lineas.append(ticket_str)
        lineas.append(f"Fecha: {ahora}")
        lineas.append(f"Cajero: {cajero}")
        lineas.append("-" * min(30, width))

        # Productos
        total_pagar = 0.0
        total_base = 0.0
        iva_desglose_map = {}

        # layout columns
        price_col = 10  # space reserved for numeric subtotal at right
        desc_col = max(10, width - price_col)

        for item in carrito:
            try:
                if isinstance(item, dict):
                    nombre = str(item.get('nombre', ''))
                    cantidad = item.get('cantidad', 0)
                    precio = float(item.get('precio', 0.0) or 0.0)
                    iva = item.get('iva', 0)
                else:
                    # allow tuple/list-like rows: (id, nombre, cantidad, precio, iva)
                    nombre = str(item[1]) if len(item) > 1 else ''
                    cantidad = item[2] if len(item) > 2 else 0
                    precio = float(item[3]) if len(item) > 3 else 0.0
                    iva = item[4] if len(item) > 4 else 0
            except Exception:
                nombre = ''
                cantidad = 0
                precio = 0.0
                iva = 0

            try:
                cantidad_num = float(cantidad)
                if cantidad_num.is_integer():
                    cantidad_display = str(int(cantidad_num))
                else:
                    cantidad_display = f"{cantidad_num:.2f}"
            except Exception:
                cantidad_display = str(cantidad)

            subtotal = (float(cantidad or 0) * float(precio or 0.0))
            total_pagar += subtotal

            # compute base and iva portions for reporting
            try:
                divisor = 1 + (float(iva) / 100) if iva else 1.0
                base_amount = subtotal / divisor if divisor else subtotal
                iva_amount = subtotal - base_amount
            except Exception:
                base_amount = subtotal
                iva_amount = 0.0
            total_base += base_amount
            iva_desglose_map[iva] = iva_desglose_map.get(iva, 0.0) + iva_amount

            # Build product description column and align price on the right
            precio_str = f"{subtotal:,.2f}".rjust(price_col)
            desc = f"{cantidad_display}x {nombre}"
            if len(desc) > desc_col:
                desc = desc[:desc_col-3] + '...'
            line = desc.ljust(desc_col) + precio_str
            lineas.append(line)

        lineas.append("-" * min(30, width))

        # Totales y desglose IVA
        try:
            # If ticket_id provided, try to obtain authoritative breakdown
            if ticket_id is not None:
                from modulos.tpv.cierre_service import CierreService
                svc = CierreService()
                impuestos = svc.desglose_impuestos_ticket(ticket_id)
                # Only accept external breakdown if it returns data
                if impuestos:
                    iva_map = {imp['iva']: imp.get('cuota', 0.0) for imp in impuestos}
                    total_base_ext = sum(imp.get('base', 0.0) for imp in impuestos)
                    if total_base_ext and total_base_ext > 0:
                        iva_desglose_map = iva_map
                        total_base = total_base_ext
        except Exception:
            # fallback: we already computed totals incrementally
            pass

        # format totals with columns similar to product lines
        totals_desc_col = desc_col
        totals_price_col = price_col
        lineas.append("Subtotal:".ljust(totals_desc_col) + f"{total_base:>{totals_price_col}.2f}")
        for tipo in sorted(iva_desglose_map.keys()):
            lineas.append(f"IVA ({int(tipo)}%):".ljust(totals_desc_col) + f"{iva_desglose_map[tipo]:>{totals_price_col}.2f}")
        lineas.append(f"TOTAL:".ljust(totals_desc_col) + f"{total_pagar:>{totals_price_col}.2f}")
        lineas.append("-" * min(30, width))

        # Pago
        metodo = (metodo_pago or 'EFECTIVO').upper()
        lineas.append(f"PAGO:".ljust(desc_col) + metodo.rjust(price_col))
        if metodo == 'EFECTIVO':
            lineas.append(f"EFECTIVO:".ljust(desc_col) + f"{efectivo:>{price_col}.2f}")
            lineas.append(f"CAMBIO:".ljust(desc_col) + f"{cambio:>{price_col}.2f}")
        lineas.append("-" * min(30, width))
        lineas.append("")
        lineas.append("¡Gracias por tu compra!")
        lineas.append("")

        # Wrap to width
        out_lines = []
        for line in lineas:
            if not line.strip():
                out_lines.append('')
                continue
            wrapped = textwrap.wrap(line, width=width, replace_whitespace=False)
            if not wrapped:
                out_lines.append('')
            else:
                out_lines.extend(wrapped)

        return "\n".join(out_lines) + "\n"
    except Exception as e:
        logging.exception('Error generando ticket: %s', e)
        return "TICKET\n(Detalle no disponible)\n"