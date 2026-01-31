# modulos/impresion/print_service.py

import sys
import configparser
import platform
import subprocess
import os
import inspect
import logging
import textwrap


class ImpresionService:
    def __init__(self, config_file='Configuracion/config.ini'):
        # Resolve config_file relative to executable when frozen, or project root otherwise
        if config_file == 'Configuracion/config.ini':
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(sys.executable)
            else:
                # project root is two levels up from this module (modulos/impresion)
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            config_file = os.path.join(base, 'Configuracion', 'config.ini')
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.nombre_impresora = None
        self.ticket_width = None
        self._cargar_configuracion()
        # simulation flag: when True, printing is simulated to console/logs.
        # Keep available for explicit developer override, but printer detection
        # will force simulation when no physical printer is available.
        self.SIMULACION = False

        # detect at init whether any printer is available; this drives
        # whether printing attempts go to a physical device or fallback to terminal.
        try:
            self._printer_available = self._detect_printer()
        except Exception:
            self._printer_available = False

    def _cargar_configuracion(self):
        """Carga configuraciones desde config.ini."""
        try:
            if not os.path.exists(self.config_file):
                # ensure parent exists and create minimal structure
                parent = os.path.dirname(self.config_file) or '.'
                try:
                    os.makedirs(parent, exist_ok=True)
                except Exception:
                    pass
                self.config['impresion'] = {'nombre_impresora': '', 'ticket_width': '80mm'}
                try:
                    with open(self.config_file, 'w') as f:
                        self.config.write(f)
                except Exception:
                    # ignore write errors for now
                    pass
            self.config.read(self.config_file)
            self.nombre_impresora = self.config.get('impresion', 'nombre_impresora', fallback='')
            self.ticket_width = self.config.get('impresion', 'ticket_width', fallback='80mm')
        except Exception:
            self.nombre_impresora = ''
            self.ticket_width = '80mm'

    def guardar_configuracion(self, nombre_impresora, ancho_ticket):
        """Guarda la configuración de la impresora en config.ini."""
        self.config['impresion'] = {
            'nombre_impresora': nombre_impresora,
            'ticket_width': ancho_ticket
        }
        parent = os.path.dirname(self.config_file) or '.'
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception:
            pass
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        # refresh in-memory
        self._cargar_configuracion()

    def listar_impresoras(self):
        """Devuelve una lista de impresoras disponibles en el sistema."""
        try:
            system = platform.system().lower()
            if system.startswith('win'):
                import win32print
                return [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            else:
                # Try lpstat (CUPS) as a fallback on Unix-like systems
                try:
                    out = subprocess.check_output(['lpstat', '-p'], stderr=subprocess.DEVNULL, text=True)
                    lines = [l.strip() for l in out.splitlines() if l.strip()]
                    names = []
                    for l in lines:
                        # lines like: "printer NAME is idle."
                        parts = l.split()
                        if len(parts) >= 2 and parts[0] == 'printer':
                            names.append(parts[1])
                    return names
                except Exception:
                    return []
        except Exception:
            return []

    def _detect_printer(self) -> bool:
        """Detecta si hay impresoras disponibles según la plataforma y la config.

        Devuelve True si hay al menos una impresora o si `nombre_impresora` existe
        en el sistema. False en caso contrario.
        """
        try:
            printers = self.listar_impresoras()
            if self.nombre_impresora:
                # check configured printer exists in the system list
                try:
                    return self.nombre_impresora in printers
                except Exception:
                    return bool(printers)
            return bool(printers)
        except Exception:
            return False

    def abrir_cajon(self):
        """Enviar comando para abrir cajón (solo si la impresora/driver lo soporta)."""
        # ESC p 0 16 255 as bytes
        comando_cajon = b'\x1B\x70\x00\x10\xFF'
        try:
            self._send_raw(comando_cajon)
        except Exception:
            # best-effort; ignore if not supported
            pass

    def imprimir_ticket(self, texto, abrir_cajon=False, no_wrap=False):
        """Imprime el ticket a la impresora configurada.

        En Windows usa win32print; en Unix intenta `lp`/`lpr`.
        """
        # If there is no detected physical printer, or simulation explicitly
        # requested, show ticket in terminal and return success.
        if (not getattr(self, '_printer_available', True)) or getattr(self, 'SIMULACION', False):
            # determine caller info
            try:
                stack = inspect.stack()
                # find the first caller outside this module
                caller = None
                for fr in stack[1:6]:
                    mod = inspect.getmodule(fr.frame)
                    if mod and mod.__name__ != __name__:
                        caller = f"{mod.__name__}.{fr.function}"
                        break
                if not caller:
                    caller = stack[1].function
            except Exception:
                caller = 'unknown'
            logging.info(f"[SIMULACIÓN IMPRESIÓN] llamada desde: {caller}; abrir_cajon={abrir_cajon}")
            print('\n[IMPRESIÓN EN TERMINAL]')
            print(f'Llamada desde: {caller} -- abrir_cajon={abrir_cajon}')
            print('-' * 30)
            print(texto)
            print('-' * 30 + '\n')
            if abrir_cajon:
                print('[SIMULACIÓN] abrir cajón de dinero (comando no enviado)')
            return True
        if not texto:
            raise Exception('Texto de ticket vacío')

        # normalize width according to config (wrap lines to target chars)
        try:
            if not no_wrap:
                texto = self._normalize_ticket_width(texto)
        except Exception:
            pass

        system = platform.system().lower()
        if system.startswith('win'):
            # Import here to avoid failing on non-windows systems
            try:
                import win32print
            except Exception as e:
                # If win32print isn't available, fallback to terminal output
                logging.exception('win32print no disponible: %s', e)
                print('\n[ADVERTENCIA] win32print no disponible, imprimiendo en terminal:')
                print(texto)
                return True

            nombre = (self.nombre_impresora or '').strip()
            if not nombre:
                try:
                    nombre = win32print.GetDefaultPrinter()
                except Exception:
                    nombre = ''
            if not nombre:
                # no configured or default printer available; fallback to terminal
                logging.warning('No hay impresora configurada en Windows; salida por terminal')
                print('\n[ADVERTENCIA] No se encontró impresora configurada; imprimiendo en terminal:')
                print(texto)
                return True

            hprinter = None
            try:
                hprinter = win32print.OpenPrinter(nombre)
                job = win32print.StartDocPrinter(hprinter, 1, ("Ticket", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                # encode using cp850 to keep classic POS charset compatibility
                data = texto.encode('cp850', errors='replace')
                # send main data
                win32print.WritePrinter(hprinter, data)

                # send margin lines before cut
                margin_lines = self._cut_margin_lines()
                if margin_lines:
                    win32print.WritePrinter(hprinter, margin_lines)

                # send cut command (GS V 0)
                try:
                    cut_cmd = b'\x1D\x56\x00'
                    win32print.WritePrinter(hprinter, cut_cmd)
                except Exception:
                    # try ESC i as alternative
                    try:
                        win32print.WritePrinter(hprinter, b'\x1B\x69')
                    except Exception:
                        pass

                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                if hprinter:
                    try:
                        win32print.ClosePrinter(hprinter)
                    except Exception:
                        pass
            # abrir cajon if requested (after printing)
            if abrir_cajon:
                try:
                    self.abrir_cajon()
                except Exception:
                    pass
            return True
        else:
            # Unix-like: try piping to lpr or lp
            try:
                # Prefer lp, then lpr
                if shutil_which('lp'):
                    p = subprocess.Popen(['lp', '-d', self.nombre_impresora] if self.nombre_impresora else ['lp'], stdin=subprocess.PIPE)
                    p.communicate(input=texto.encode('utf-8'))
                    return p.returncode == 0
                elif shutil_which('lpr'):
                    p = subprocess.Popen(['lpr', '-P', self.nombre_impresora] if self.nombre_impresora else ['lpr'], stdin=subprocess.PIPE)
                    p.communicate(input=texto.encode('utf-8'))
                    return p.returncode == 0
                else:
                    # fallback: write to stdout (no lp/lpr available)
                    print('\n[ADVERTENCIA] lp/lpr no disponible; imprimiendo en terminal]')
                    print(texto)
                    print('[FIN SALIDA]\n')
                    return True
            except Exception as e:
                # On Unix printing failure, fallback to terminal output
                logging.exception('Error imprimiendo en Unix: %s', e)
                print('\n[ADVERTENCIA] Error imprimiendo en sistema Unix; imprimiendo en terminal]')
                print(texto)
                return True

    def _send_raw(self, data_bytes):
        """Envía bytes RAW a la impresora configurada (Windows).

        Implementación mínima: usa win32print si está disponible.
        """
        system = platform.system().lower()
        if system.startswith('win'):
            import win32print
            if not self.nombre_impresora:
                return
            hprinter = win32print.OpenPrinter(self.nombre_impresora)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("RAW", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, data_bytes)
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
        else:
            # Not implemented for Unix raw; attempt via lpr
            if shutil_which('lp'):
                p = subprocess.Popen(['lp', '-d', self.nombre_impresora] if self.nombre_impresora else ['lp'], stdin=subprocess.PIPE)
                p.communicate(input=data_bytes)
            elif shutil_which('lpr'):
                p = subprocess.Popen(['lpr', '-P', self.nombre_impresora] if self.nombre_impresora else ['lpr'], stdin=subprocess.PIPE)
                p.communicate(input=data_bytes)

    def _cut_margin_lines(self):
        """Return bytes with blank lines before the cut, according to config.

        Default leave 6 blank lines (approx. 5-10 recommended).
        """
        try:
            # allow ticket_width to also contain margin setting later; keep simple fixed count
            lines = 6
            return (b"\n" * lines)
        except Exception:
            return b"\n\n\n\n\n\n"

    def _normalize_ticket_width(self, texto: str) -> str:
        """Wrap lines to the configured ticket width in characters.

        Uses `self.ticket_width` (like '80mm' or '58mm') to decide a chars-per-line value.
        """
        try:
            tw = (self.ticket_width or '80mm').lower()
            if '58' in tw:
                width = 32
            else:
                # default to 80mm behaviour
                width = 48
            # wrap each paragraph/line preserving existing newlines in a simple way
            out_lines = []
            for line in texto.splitlines():
                if not line.strip():
                    out_lines.append('')
                    continue
                wrapped = textwrap.wrap(line, width=width, replace_whitespace=False)
                if not wrapped:
                    out_lines.append('')
                else:
                    out_lines.extend(wrapped)
            return "\n".join(out_lines) + "\n"
        except Exception:
            return texto


def shutil_which(cmd):
    """Helper lightweight which replacement using shutil if available."""
    try:
        import shutil
        return shutil.which(cmd)
    except Exception:
        return None
