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
    
    # Factura y datos
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # NOTA: número de ticket lo dejamos fijo por ahora (más adelante será secuencial)
    lineas.append("FACTURA Nº: 12345")
    lineas.append(f"Fecha: {ahora}")
    lineas.append(f"Cajero: {cajero}")
    lineas.append("-" * 30)
    
    # Productos
    for item in carrito:
        nombre = item['nombre'][:20]
        cantidad = item['cantidad']
        precio = item['precio']
        subtotal = cantidad * precio
        
        # Formato: "2x Nombre (20)      40.00"
        # Mostramos precio unitario entre paréntesis si es entero, o con decimales si no
        if precio == int(precio):
            precio_str = f"({int(precio)})"
        else:
            precio_str = f"({precio:.2f})"
        
        linea_base = f"{cantidad}x {nombre} {precio_str}"
        # Alinear precio total a la derecha (posición 25 en adelante)
        if len(linea_base) > 25:
            linea_base = linea_base[:25]
        linea_final = linea_base.ljust(25) + f"{subtotal:>7.2f}"
        lineas.append(linea_final)
    
    lineas.append("-" * 30)
    
    # Totales
    total_pagar = sum(item['cantidad'] * item['precio'] for item in carrito)

    # Prefer using centralized service for tax breakdown when ticket_id is given
    iva_desglose_map = {}
    try:
        if ticket_id is not None:
            from modulos.tpv.cierre_service import CierreService
            svc = CierreService()
            impuestos = svc.desglose_impuestos_ticket(ticket_id)
            for imp in impuestos:
                iva_desglose_map[imp['iva']] = imp['cuota']
            total_base = sum(imp.get('base', 0.0) for imp in impuestos)
        else:
            iva_desglose = {}
            for item in carrito:
                tipo_iva = item['iva']
                subtotal = item['cantidad'] * item['precio']
                divisor = 1 + (tipo_iva / 100)
                iva_item = subtotal - (subtotal / divisor)
                if tipo_iva not in iva_desglose:
                    iva_desglose[tipo_iva] = 0.0
                iva_desglose[tipo_iva] += iva_item
            iva_desglose_map = iva_desglose
            total_base = total_pagar - sum(iva_desglose_map.values())

    except Exception:
        # fallback to local calc
        iva_desglose_map = {}
        for item in carrito:
            tipo_iva = item['iva']
            subtotal = item['cantidad'] * item['precio']
            divisor = 1 + (tipo_iva / 100)
            iva_item = subtotal - (subtotal / divisor)
            if tipo_iva not in iva_desglose_map:
                iva_desglose_map[tipo_iva] = 0.0
            iva_desglose_map[tipo_iva] += iva_item
        total_base = total_pagar - sum(iva_desglose_map.values())

    lineas.append(f"Subtotal:".ljust(23) + f"{total_base:>7.2f}")
    for tipo in sorted(iva_desglose_map.keys()):
        lineas.append(f"IVA ({int(tipo)}%):".ljust(23) + f"{iva_desglose_map[tipo]:>7.2f}")
    lineas.append(f"TOTAL:".ljust(23) + f"{total_pagar:>7.2f}")
    lineas.append("-" * 30)
    
    # Pago
    lineas.append(f"EFECTIVO:".ljust(23) + f"{efectivo:>7.2f}")
    lineas.append(f"CAMBIO:".ljust(23) + f"{cambio:>7.2f}")
    lineas.append("-" * 30)
    lineas.append("")
    lineas.append("¡Gracias por tu compra!")
    lineas.append("")
    lineas.append("")  # Para margen antes del corte
    
    return "\n".join(lineas)