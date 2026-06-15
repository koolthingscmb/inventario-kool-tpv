"""Toast widget — notificación flotante con auto-desaparición."""
import tkinter as tk
from typing import Literal, Callable, Optional
from kool_tpv.config.notificaciones_config import load_notificaciones_config

ToastType = Literal['success', 'info', 'warning', 'error']

_ICONOS = {'success': '✅', 'info': 'ℹ', 'warning': '⚠', 'error': '✕'}
_COLORES_BG = {
    'success': 'toast_success_bg',
    'info': 'toast_info_bg',
    'warning': 'toast_warning_bg',
    'error': 'toast_error_bg',
}


class ToastWidget:
    """Toast flotante no-modal. Uso: ToastWidget.show(parent, 'mensaje', tipo='success')"""

    _instancias: list = []

    def __init__(self, parent, mensaje: str, tipo: ToastType = 'info',
                 duracion_ms: Optional[int] = None, al_cerrar: Optional[Callable] = None):
        self.cfg = load_notificaciones_config()
        self.parent = parent
        self.tipo = tipo
        self.mensaje = mensaje
        self.duracion_ms = duracion_ms or self.cfg['toast_duracion_ms']
        self.al_cerrar = al_cerrar
        self._after_id = None
        self._win = None

    @classmethod
    def show(cls, parent, mensaje: str, tipo: ToastType = 'info',
             duracion_ms: Optional[int] = None, al_cerrar: Optional[Callable] = None):
        toast = cls(parent, mensaje, tipo, duracion_ms, al_cerrar)
        toast._mostrar()
        return toast

    def cerrar(self):
        self._destruir()

    def _mostrar(self):
        if self._win is not None:
            return

        cfg = self.cfg
        w = int(cfg['toast_ancho'])
        h = int(cfg['toast_alto'])
        bg = cfg[_COLORES_BG.get(self.tipo, 'toast_info_bg')]
        fg = cfg['toast_text_color']
        px = int(cfg['toast_padding_x'])

        # Ventana Toplevel pura — sin decoración, tamaño fijo
        root = self.parent.winfo_toplevel()
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes('-topmost', True)
        self._win.attributes('-alpha', float(cfg['toast_max_opacity']))
        self._win.geometry(f"{w}x{h}")   # tamaño fijo ANTES de añadir widgets
        self._win.configure(bg=bg)
        self._win.resizable(False, False)

        # Canvas para esquinas redondeadas
        radius = int(cfg['toast_corner_radius'])
        canvas = tk.Canvas(self._win, width=w, height=h, bg=bg,
                           highlightthickness=0, bd=0)
        canvas.place(x=0, y=0)
        self._draw_rounded(canvas, 0, 0, w, h, radius, bg)

        # Icono + mensaje en una sola línea centrada verticalmente
        icono = _ICONOS.get(self.tipo, '')
        texto = f"  {icono}  {self.mensaje}"
        lbl = tk.Label(self._win, text=texto, bg=bg, fg=fg,
                       font=('Helvetica', 11, 'bold'),
                       anchor='w', padx=px)
        lbl.place(x=0, y=0, width=w, height=h)
        lbl.bind('<Button-1>', lambda e: self._destruir())
        self._win.bind('<Button-1>', lambda e: self._destruir())

        # Posición
        self._posicionar(w, h)

        self._after_id = self._win.after(self.duracion_ms, self._destruir)
        ToastWidget._instancias.append(self)

    def _draw_rounded(self, canvas, x1, y1, x2, y2, r, color):
        canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, fill=color, outline=color)
        canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, fill=color, outline=color)
        canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, fill=color, outline=color)
        canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, fill=color, outline=color)
        canvas.create_rectangle(x1+r, y1, x2-r, y2, fill=color, outline=color)
        canvas.create_rectangle(x1, y1+r, x2, y2-r, fill=color, outline=color)

    def _posicionar(self, w, h):
        cfg = self.cfg
        ox = int(cfg['toast_offset_x'])
        oy = int(cfg['toast_offset_y'])
        pos = cfg['toast_posicion']
        try:
            root = self.parent.winfo_toplevel()
            rx, ry = root.winfo_x(), root.winfo_y()
            rw, rh = root.winfo_width(), root.winfo_height()
        except Exception:
            rx = ry = 0
            rw = self._win.winfo_screenwidth()
            rh = self._win.winfo_screenheight()
        if pos == 'bottom-right':
            x, y = rx + rw - w - ox, ry + rh - h - oy
        elif pos == 'bottom-left':
            x, y = rx + ox, ry + rh - h - oy
        elif pos == 'top-right':
            x, y = rx + rw - w - ox, ry + oy
        else:
            x, y = rx + ox, ry + oy
        self._win.geometry(f"{w}x{h}+{x}+{y}")

    def _destruir(self):
        if self._win is None:
            return
        if self._after_id:
            try:
                self._win.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._win.destroy()
        except Exception:
            pass
        self._win = None
        if self in ToastWidget._instancias:
            ToastWidget._instancias.remove(self)
        if self.al_cerrar:
            try:
                self.al_cerrar()
            except Exception:
                pass
