# modulos/impresion/impresora.py

import sys

def imprimir_ticket_y_abrir_cajon(ticket_texto):
    if sys.platform.startswith('win'):
        _imprimir_en_windows_por_nombre(ticket_texto)
    else:
        print("\n[IMPRESIÓN SIMULADA - SISTEMA NO WINDOWS]")
        print("Ticket que se imprimiría:")
        print("-" * 40)
        print(ticket_texto)
        print("-" * 40)
        print("[FIN SIMULACIÓN]\n")

def _imprimir_en_windows_por_nombre(ticket_texto):
    """
    Imprime usando el nombre de la impresora registrado en Windows.
    """
    try:
        import win32print
        import win32api

        nombre_impresora = "POS-90"  

        # Verificar que la impresora existe
        impresoras = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
        if nombre_impresora not in impresoras:
            print(f"[ERROR] Impresora '{nombre_impresora}' no encontrada.")
            print("Impresoras disponibles:")
            for p in impresoras:
                print(f"  - {p}")
            return

        # Comando ESC/POS para abrir cajón
        comando_cajon = b'\x1B\x70\x00\x10\xFF'

        # Preparar datos: ticket + corte + cajón
        datos_a_imprimir = (
            ticket_texto.encode('cp850', errors='replace') +
            b'\n\n' +
            comando_cajon +
            b'\x1D\x56\x00'          
        )

        # Enviar a impresora
        hprinter = win32print.OpenPrinter(nombre_impresora)
        try:
            hjob = win32print.StartDocPrinter(hprinter, 1, ("Ticket KOOL THINGS", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, datos_a_imprimir)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

        print("[ÉXITO] Ticket enviado a la impresora y cajón abierto.")

    except Exception as e:
        print(f"[ERROR IMPRESIÓN WINDOWS] {e}")
        print("Asegúrate de tener instalado 'pywin32' y que la impresora esté encendida.")