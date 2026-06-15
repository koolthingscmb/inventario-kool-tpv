"""Toast widget — notificación flotante con auto-desaparición."""
import customtkinter as ctk
from typing import Literal, Callable, Optional
from kool_tpv.config.notificaciones_config import load_notificaciones_config

ToastType = Literal['success', 'info', 'warning', 'error']


class ToastWidget:
    """Toast flotante no-modal. Uso: ToastWidget.show(parent, 'mensaje', tipo='success')"""

    _instancias: list = []

    def __init__(self, parent: ctk.CTk, mensaje: str, tipo: ToastType = 'info',
                 duracion_ms: Optional[int] = None, al_cerrar: Optional[Callable] = None):
        self.cfg = load_notificaciones_config()
        self.parent = parent
        self.tipo = tipo
        self.mensaje = mensaje
        self.duracion_ms = duracion_ms or self.cfg['toast_duracion_ms']
        self.al_cerrar = al_cerrar
        self._after_id = None
        self._frame = None

    @classmethod
    def show(cls, parent: ctk.CTk, mensaje: str, tipo: ToastType = 'info',
             duracion_ms: Optional[int] = None, al_cerrar: Optional[Callable] = None):
        toast = cls(parent, mensaje, tipo, duracion_ms, al_cerrar)
        toast._mostrar()
        return toast

    def cerrar(self):
        self._destruir()

    def _mostrar(self):
        if self._frame is not None:
            return
        self._frame = ctk.CTkToplevel(self.parent)
        self._frame.overrideredirect(True)
        self._frame.attributes('-topmost', True)
        self._frame.attributes('-alpha', 0.0)  # invisible hasta posicionar

        bg = self._color_bg()
        fg = self.cfg['toast_text_color']
        r = self.cfg['toast_corner_radius']
        w = self.cfg['toast_ancho']
        px = self.cfg['toast_padding_x']
        py = self.cfg['toast_padding_y']

        inner = ctk.CTkFrame(self._frame, fg_color=bg, corner_radius=r, width=w)
        inner.pack(fill='both', expand=True)
        inner.pack_propagate(False)

        icono = self._icono_para_tipo()
        header = ctk.CTkFrame(inner, fg_color='transparent', width=w)
        header.pack(fill='x', padx=px, pady=(py, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=icono, font=('Segoe UI Emoji', 16), text_color=fg).pack(side='left', padx=(0, 8))
        ctk.CTkLabel(header, text=self.tipo.upper(), font=('Helvetica', 10, 'bold'), text_color=fg).pack(side='left')

        ctk.CTkLabel(inner, text=self.mensaje, font=('Helvetica', 11), text_color=fg,
                     wraplength=w - 2 * px, justify='left').pack(
            fill='both', expand=True, padx=px, pady=(4, py))

        for wgt in inner.winfo_children():
            for child in self._all_children(wgt):
                child.bind('<Button-1>', lambda e: self._destruir())

        # Posicionar tras render para tener dimensiones reales
        self._frame.after(80, self._posicionar_y_mostrar)
        self._after_id = self._frame.after(self.duracion_ms + 80, self._destruir)
        ToastWidget._instancias.append(self)

    def _all_children(self, widget):
        yield widget
        for c in widget.winfo_children():
            yield from self._all_children(c)

    def _destruir(self):
        if self._frame is None:
            return
        if self._after_id:
            try:
                self._frame.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._frame.destroy()
        except Exception:
            pass
        self._frame = None
        if self in ToastWidget._instancias:
            ToastWidget._instancias.remove(self)
        if self.al_cerrar:
            try:
                self.al_cerrar()
            except Exception:
                pass

    def _posicionar_y_mostrar(self):
        if self._frame is None:
            return
        self._frame.update_idletasks()
        tw = self.cfg['toast_ancho']
        # Usar altura real si ya la tiene, sino altura fija de fallback
        th = self._frame.winfo_height()
        if th < 20:
            th = self.cfg.get('toast_alto', 80)
        try:
            root = self.parent.winfo_toplevel()
            rx = root.winfo_x()
            ry = root.winfo_y()
            rw = root.winfo_width()
            rh = root.winfo_height()
        except Exception:
            rx = ry = 0
            rw = self.parent.winfo_screenwidth()
            rh = self.parent.winfo_screenheight()
        pos = self.cfg['toast_posicion']
        ox = self.cfg['toast_offset_x']
        oy = self.cfg['toast_offset_y']
        if pos == 'bottom-right':
            x, y = rx + rw - tw - ox, ry + rh - th - oy
        elif pos == 'bottom-left':
            x, y = rx + ox, ry + rh - th - oy
        elif pos == 'top-right':
            x, y = rx + rw - tw - ox, ry + oy
        else:
            x, y = rx + ox, ry + oy
        self._frame.geometry(f"{tw}x{th}+{x}+{y}")
        self._frame.attributes('-alpha', self.cfg['toast_max_opacity'])

    def _color_bg(self):
        return {
            'success': self.cfg['toast_success_bg'],
            'info': self.cfg['toast_info_bg'],
            'warning': self.cfg['toast_warning_bg'],
            'error': self.cfg['toast_error_bg'],
        }.get(self.tipo, self.cfg['toast_info_bg'])

    def _icono_para_tipo(self):
        return {
            'success': '✅',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
        }.get(self.tipo, 'ℹ️')
