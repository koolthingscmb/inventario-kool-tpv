"""
Generador de tickets (limpieza inicial).

Este archivo ha sido limpiado el 2026-02-01. El contenido original se ha
respaldado en `backups/impresion_ticket_generator.py.backup.2026-02-01`.

Se mantiene la función pública `generar_ticket` con la misma firma, pero
implementada como un stub que devuelve un texto de ticket simple y seguro.
El objetivo es evitar que importaciones y llamadas externas fallen mientras
se reconstruye la lógica real.
"""

import logging
import configparser
from typing import Any, List


def centrar_texto(texto: str, width: int) -> str:
    """Stub de centrado: devuelve texto si width inválido, o lo centra simple."""
    try:
        texto = '' if texto is None else str(texto)
        if not isinstance(width, int) or width <= 0:
            return texto
        if len(texto) >= width:
            return texto
        espacios = (width - len(texto)) // 2
        return ' ' * espacios + texto
    except Exception:
        return str(texto or '')


def generar_ticket(carrito: List[Any], efectivo: float, cambio: float, nombre_tienda: str = "KOOL DREAMS", cajero: str = "EGON", ticket_id: int = None, width: int = 50, metodo_pago: str = 'EFECTIVO', puntos_canjeados: float = 0) -> str:
    """Genera un ticket simulado y seguro.

    Mantiene la misma firma que el antiguo `generar_ticket` para compatibilidad.
    Devuelve una representación textual mínima del ticket para propósitos de
    pruebas y desarrollo mientras se reconstruye la lógica completa.
    """
    try:
        lines = []
        lines.append((nombre_tienda or 'Tienda').upper())
        lines.append('-' * min(30, width))
        lines.append(f"TICKET ID: {ticket_id or '--'}")
        lines.append(f"Cajero: {cajero or '--'}")
        lines.append('-' * min(30, width))
        # Mostrar items básicos si vienen en forma de lista de dicts
        try:
            for it in (carrito or [])[:10]:
                if isinstance(it, dict):
                    nombre = it.get('nombre', '')
                    cant = it.get('cantidad', 1)
                    precio = it.get('precio', 0.0)
                    lines.append(f"{cant}x {nombre} - {float(precio):.2f}")
                else:
                    lines.append(str(it))
        except Exception:
            logging.exception('Error al leer items del carrito (stub)')
        lines.append('-' * min(30, width))
        lines.append(f"TOTAL: {float(efectivo or 0) - float(cambio or 0):.2f}")
        lines.append(f"PAGO: {metodo_pago}")
        lines.append('')
        lines.append('--- FIN DE TICKET (SIMULADO) ---')
        return '\n'.join(lines) + '\n'
    except Exception:
        logging.exception('Error en generar_ticket stub')
        return 'TICKET\n(Detalle no disponible)\n'


__all__ = ['generar_ticket', 'centrar_texto', 'generar_encabezado', 'generar_linea_fija', 'generar_cuerpo', 'generar_resumen_financiero']


def generar_encabezado(config_path: str = 'Configuracion/config.ini', width: int = 50) -> List[str]:
    """Lee y genera el encabezado del ticket desde `config.ini`.

    :param config_path: Ruta al archivo de configuración `config.ini`.
    :param width: Ancho del ticket en caracteres (ej. 50).
    :return: Lista de líneas con el encabezado centrado.
    """
    encabezado: List[str] = []
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        for i in range(1, 5):  # Límite de 4 líneas
            linea = config.get('IMPRESION_ENCABEZADO', f'linea_{i}', fallback='').strip()
            if linea:
                encabezado.append(centrar_texto(linea, width))
    except Exception as e:
        logging.exception('Error leyendo encabezado del ticket: %s', e)
        encabezado.append('Error al cargar encabezado')
    return encabezado


# Nota: pruebas integradas se ejecutan en el bloque __main__ al final del archivo.


def generar_linea_fija(ticket_id: int, fecha: str, cajero: str, width: int = 50) -> List[str]:
    """Genera la línea fija con datos de la venta para el ticket.

    :param ticket_id: Número único del ticket (obligatorio).
    :param fecha: Fecha y hora de la venta (formato DD/MM/AAAA HH:MM).
    :param cajero: Nombre del cajero.
    :param width: Ancho del ticket en caracteres (por defecto 50).
    :return: Lista de líneas listas para incluir en el ticket.
    """
    linea_fija: List[str] = []

    def centrar_guiones(w: int, char: str = "-") -> str:
        guiones = char * min(30, w)
        espacios = (w - len(guiones)) // 2
        return " " * max(0, espacios) + guiones

    titulo = "FACTURA SIMPLIFICADA"

    # Añadir título centrado
    linea_fija.append(centrar_texto(titulo.upper(), width))

    # Añadir separador centrado
    linea_fija.append(centrar_guiones(width))

    # Añadir datos de la venta
    fecha_y_datos = f"{fecha}  Cajero: {cajero or '--'}  T: {ticket_id or '--'}"
    linea_fija.append(centrar_texto(fecha_y_datos, width))

    # Añadir separador final centrado
    linea_fija.append(centrar_guiones(width))

    return linea_fija


def generar_cuerpo(carrito: list, puntos_canjeados: float = 0.00, width: int = 50) -> List[str]:
    """Genera el cuerpo del ticket con los productos vendidos y el tesoro gastado.

    :param carrito: Lista de dicts representando los artículos en el carrito.
    :param puntos_canjeados: Total de puntos gastados por el cliente en euros.
    :param width: Ancho del ticket en caracteres.
    :return: Lista de cadenas formateadas para el cuerpo del ticket.
    """
    cuerpo: List[str] = []
    try:
        for item in (carrito or []):
            try:
                cantidad = int(item.get('cantidad', 1))
            except Exception:
                cantidad = 1
            nombre = str(item.get('nombre', ''))[:15]
            try:
                precio = float(item.get('precio', 0.0))
            except Exception:
                precio = 0.0
            importe = round(cantidad * precio, 2)

            linea = f"{cantidad}x {nombre:<15} {precio:>6.2f} {importe:>8.2f}"
            espacios = (width - len(linea)) // 2
            cuerpo.append(" " * max(0, espacios) + linea)

        # Línea para el tesoro gastado (si aplica)
        if float(puntos_canjeados or 0) > 0:
            tesoro_linea = f"**Tesoro gastado: -{float(puntos_canjeados):.2f}"
            # Centrar la línea respecto al ancho del ticket
            cuerpo.append(centrar_texto(tesoro_linea, width))

    except Exception as e:
        logging.exception('Error generando el cuerpo del ticket: %s', e)

    return cuerpo


def generar_resumen_financiero(subtotal: float, desglose_iva: dict, total: float, forma_pago: dict, width: int = 50) -> List[str]:
    """Genera el Resumen financiero del ticket con Subtotal, IVA desglosado, Total y forma de pago.

    :param subtotal: Precio total sin impuestos.
    :param desglose_iva: Diccionario con porcentajes como claves y valores en euros.
    :param total: Precio final con impuestos.
    :param forma_pago: Diccionario con keys 'pago','total','entregado','devuelto'.
    :param width: Ancho del ticket en caracteres.
    :return: Lista de líneas formateadas para el resumen.
    """
    resumen: List[str] = []
    try:
        separador = "------------------------------"
        resumen.append(separador.center(width))

        # Subtotal (centrado)
        subtotal_line = f"Subtotal: {subtotal:10.2f}"
        resumen.append(subtotal_line.center(width))

        # Desglose de IVA: ordenar por porcentaje numérico descendente cuando sea posible
        try:
            ordered = sorted(desglose_iva.items(), key=lambda kv: float(kv[0].strip('%')) if isinstance(kv[0], str) and kv[0].strip('%').replace('.','',1).isdigit() else 0, reverse=True)
        except Exception:
            ordered = list(desglose_iva.items())
        for porcentaje, valor in ordered:
            iva_line = f"IVA {porcentaje}: {valor:10.2f}"
            resumen.append(iva_line.center(width))

        # Total (centrado)
        total_line = f"Total: {total:10.2f}"
        resumen.append(total_line.center(width))

        resumen.append(separador.center(width))

        # Tabla de forma de pago (4 columnas, 10 chars each) centrada
        tabla_encabezado = f"{'Pago':<10} {'Total':<10} {'Entregado':<10} {'Devuelto':<10}"
        resumen.append(tabla_encabezado.center(width))
        resumen.append(('-' * min(width, len(tabla_encabezado))).center(width))

        pago = str(forma_pago.get('pago', '')).capitalize()
        total_pago = f"{forma_pago.get('total', 0.00):.2f}"
        entregado = forma_pago.get('entregado', 0.00)
        devuelto = forma_pago.get('devuelto', 0.00)

        if isinstance(pago, str) and pago.lower() != 'efectivo':
            entregado_str = "-"
            devuelto_str = "-"
        else:
            try:
                entregado_str = f"{float(entregado):.2f}"
            except Exception:
                entregado_str = "0.00"
            try:
                devuelto_str = f"{float(devuelto):.2f}"
            except Exception:
                devuelto_str = "0.00"

        tabla_contenido = f"{pago:<10} {total_pago:<10} {entregado_str:<10} {devuelto_str:<10}"
        resumen.append(tabla_contenido.center(width))

        resumen.append(separador.center(width))

    except Exception as e:
        logging.exception('Error al generar el resumen financiero: %s', e)
    return resumen


if __name__ == '__main__':
    from datetime import datetime

    # Datos de prueba
    ticket_id = 135
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    cajero = "Andrea"

    # Carrito simulado
    carrito = [
        {"nombre": "Bocadillo", "precio": 1.50, "sku": "B123", "iva": 21.0, "id": 1, "cantidad": 2},
        {"nombre": "Agua 500ml", "precio": 0.90, "sku": "A123", "iva": 10.0, "id": 2, "cantidad": 3},
        {"nombre": "Café", "precio": 1.20, "sku": "C123", "iva": 21.0, "id": 3, "cantidad": 1},
        {"nombre": "Barritas", "precio": 0.75, "sku": "D123", "iva": 10.0, "id": 4, "cantidad": 1},
    ]
    puntos_canjeados = 1.50

    # Generar partes del ticket
    encabezado = generar_encabezado(config_path='Configuracion/config.ini', width=50)
    linea_fija = generar_linea_fija(ticket_id, fecha, cajero, width=50)
    cuerpo = generar_cuerpo(carrito, puntos_canjeados, width=50)

    # Datos para el resumen financiero (prueba)
    subtotal = 6.10  # Suma sin IVA para este caso de prueba
    desglose_iva = {"21%": 2.39, "10%": 0.61}  # IVA desglosado
    total = 10.00  # Total con IVA
    forma_pago = {
        "pago": "efectivo",
        "total": 10.00,
        "entregado": 15.00,
        "devuelto": 5.00
    }

    resumen_financiero = generar_resumen_financiero(subtotal, desglose_iva, total, forma_pago, width=50)

    # Imprimir el ticket completo
    print("\n=== TICKET GENERADO ===")
    for line in encabezado + linea_fija + cuerpo + resumen_financiero:
        print(line)
    print('=== FIN DEL TICKET ===')