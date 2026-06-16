"""Toast widget — notificación flotante con auto-desaparición."""
import tkinter as tk
from pathlib import Path
from typing import Literal, Callable, Optional

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

from kool_tpv.config.notificaciones_config import load_notificaciones_config

ToastType = Literal['success', 'info', 'warning', 'error']

_ICONOS = {'success': '✅', 'info': 'ℹ', 'warning': '⚠', 'error': '✕'}
_COLORES_BG = {
    'success': 'toast_success_bg',
    'info': 'toast_info_bg',
    'warning': 'toast_warning_bg',
    'error': 'toast_error_bg',
}
_ICONO_PATHS = {
    'success': 'dialog_success.png',
    'info': 'dialog_info.png',
    'warning': 'dialog_warning.png',
    'error': 'dialog_error.png',
}
_ASSETS_DIR = Path(__file__).resolve().parents[3] / 'assets' / 'dialogs'


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

        # Icono imagen + mensaje
        icon_size = int(cfg.get('toast_icono_size', 20))
        icon_pad = int(cfg.get('toast_icono_padding', 8))
        img = self._cargar_icono(self.tipo, icon_size)

        if img:
            icon_y = (h - icon_size) // 2
            lbl_icon = tk.Label(self._win, image=img, bg=bg)
            lbl_icon.image = img
            lbl_icon.place(x=px, y=icon_y, width=icon_size, height=icon_size)
            text_x = px + icon_size + icon_pad
        else:
            icono = _ICONOS.get(self.tipo, '')
            text_x = px
            self.mensaje = f"{icono}  {self.mensaje}"

        # Botón OK para toast tipo 'info' (persistente hasta clic)
        mostrar_ok = self.tipo == 'info' and cfg.get('toast_info_mostrar_ok', False)
        if mostrar_ok:
            ok_w = int(cfg.get('toast_ok_width', 40))
            ok_h = int(cfg.get('toast_ok_height', 26))
            ok_pad = icon_pad
            ok_bg = self._parse_color(cfg.get('toast_ok_bg', '#FFFFFF'), bg)
            ok_fg = cfg.get('toast_ok_fg', '#FFFFFF')
            ok_hover = self._parse_color(cfg.get('toast_ok_hover', '#E0E0E0'), bg)
            text_w = w - text_x - px - ok_w - ok_pad
        else:
            text_w = w - text_x - px

        lbl = tk.Label(self._win, text=self.mensaje, bg=bg, fg=fg,
                       font=('Helvetica', 11, 'bold'),
                       anchor='w')
        lbl.place(x=text_x, y=0, width=text_w, height=h)
        lbl.bind('<Button-1>', lambda e: self._destruir())
        self._win.bind('<Button-1>', lambda e: self._destruir())

        if mostrar_ok:
            btn_y = (h - ok_h) // 2
            btn_x = w - px - ok_w
            btn = tk.Button(
                self._win, text='OK',
                bg=ok_bg, fg=ok_fg,
                activebackground=ok_hover, activeforeground=ok_fg,
                font=('Helvetica', 9, 'bold'),
                relief='flat', bd=0, highlightthickness=0,
                cursor='hand2', command=self._destruir
            )
            btn.place(x=btn_x, y=btn_y, width=ok_w, height=ok_h)

        # Posición
        self._posicionar(w, h)

        if not mostrar_ok and self.duracion_ms > 0:
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

    def _cargar_icono(self, tipo: str, size: int):
        """Cargar icono PNG redimensionado. Fallback a None si falla."""
        if Image is None or ImageTk is None:
            return None
        filename = _ICONO_PATHS.get(tipo)
        if not filename:
            return None
        path = _ASSETS_DIR / filename
        if not path.exists():
            return None
        try:
            pil_img = Image.open(path).convert('RGBA')
            pil_img = pil_img.resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(pil_img)
        except Exception:
            return None

    def _parse_color(self, color_str: str, bg_color: str) -> str:
        """Convertir rgba(r,g,b,a) a #RRGGBB mezclado con bg_color. Fallback a hex directo."""
        color_str = color_str.strip()
        if not color_str.lower().startswith('rgba('):
            return color_str
        try:
            inner = color_str[5:-1]
            parts = [float(x.strip()) for x in inner.split(',')]
            if len(parts) != 4:
                return color_str
            r, g, b, a = parts
            bg = bg_color.lstrip('#')
            bg_r = int(bg[0:2], 16)
            bg_g = int(bg[2:4], 16)
            bg_b = int(bg[4:6], 16)
            nr = min(255, int(r * a + bg_r * (1 - a)))
            ng = min(255, int(g * a + bg_g * (1 - a)))
            nb = min(255, int(b * a + bg_b * (1 - a)))
            return f'#{nr:02x}{ng:02x}{nb:02x}'
        except Exception:
            return '#FFFFFF'

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
