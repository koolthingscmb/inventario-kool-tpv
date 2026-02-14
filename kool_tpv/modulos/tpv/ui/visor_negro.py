"""VisorNegro: simple caja negra reutilizable para visualizar tickets/informes.

Se coloca dentro del mismo contenedor que `CarritoUI` para garantizar
dimensiones/posición idénticas (usa place(relwidth=1, relheight=1)).
"""
from typing import Optional
import logging
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk


class VisorNegro:
    """Componente mínimo: caja negra con un Text blanco dentro.

    API:
    - set_text(text)
    - show()
    - hide()
    - destroy()
    """

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self._frame: Optional[ctk.CTkFrame] = None
        self._text_widget: Optional[tk.Text] = None
        self._visible = False
        # default fractional size when showing the visor
        # Historically this overlay occupied the full cart area; restore
        # full coverage by default to avoid layout regressions.
        self._default_relwidth = 1.0
        self._default_relheight = 1.0
        try:
            # Use CTkFrame to match styling; use true black background
            # NOTE: do NOT place the frame full-screen here. We only create
            # the frame and its internal widgets. The actual placement is
            # performed by `show()` so callers can control size/position and
            # avoid blocking other UI areas.
            self._frame = ctk.CTkFrame(self.parent, fg_color="#000000")

            # Use a standard Tk Text inside to allow monospaced content and easy copy
            self._text_widget = tk.Text(self._frame, bg="#000000", fg="#FFFFFF", insertbackground="#FFFFFF")
            try:
                self._text_widget.pack(fill='both', expand=True, padx=6, pady=6)
            except Exception:
                pass

            # keep hidden until explicitly shown
            self._visible = False
        except Exception:
            logging.exception('Error creando VisorNegro')

    def set_text(self, text: str):
        try:
            if not self._text_widget:
                return
            self._text_widget.configure(state='normal')
            self._text_widget.delete('1.0', tk.END)
            if text:
                try:
                    self._text_widget.insert('1.0', text)
                except Exception:
                    self._text_widget.insert('1.0', str(text))
            self._text_widget.configure(state='disabled')
        except Exception:
            logging.exception('Error seteando texto en VisorNegro')

    def set_text_color(self, color: str):
        """Set the foreground color used to render text in the viewer."""
        try:
            if not self._text_widget:
                return
            # Tk Text doesn't support a single fg for entire widget via configure
            # set default tag for all text
            try:
                self._text_widget.tag_configure('all', foreground=color)
                # apply tag to all existing content
                self._text_widget.tag_add('all', '1.0', 'end')
            except Exception:
                # fallback: configure widget fg where supported
                try:
                    self._text_widget.configure(fg=color)
                except Exception:
                    pass
        except Exception:
            logging.exception('Error seteando color en VisorNegro')

    def set_font_size(self, size: int, family: str = 'Courier'):
        """Set the font size used by the text widget for visual display only.

        This does not affect the ticket text content used for printing.
        """
        try:
            if not self._text_widget:
                return
            try:
                f = tkfont.Font(family=family, size=int(size))
                self._text_widget.configure(font=f)
            except Exception:
                try:
                    # fallback: set a tuple
                    self._text_widget.configure(font=(family, int(size)))
                except Exception:
                    pass
        except Exception:
            logging.exception('Error seteando tamaño de fuente en VisorNegro')

    def show(self):
        try:
            if not self._frame:
                return
            # Place the frame centered within its parent using default
            # fractional dimensions unless caller places it differently
            try:
                relw = float(getattr(self, '_default_relwidth', 0.6))
                relh = float(getattr(self, '_default_relheight', 0.6))
                relx = max(0.0, (1.0 - relw) / 2.0)
                rely = max(0.0, (1.0 - relh) / 2.0)
                try:
                    self._frame.place(relx=relx, rely=rely, relwidth=relw, relheight=relh)
                except Exception:
                    # fallback to pack if place unsupported
                    try:
                        self._frame.pack(fill='both', expand=True)
                    except Exception:
                        pass
                try:
                    self._frame.lift()
                except Exception:
                    pass
            except Exception:
                try:
                    self._frame.lift()
                except Exception:
                    pass
            self._visible = True
        except Exception:
            logging.exception('Error mostrando VisorNegro')

    def hide(self):
        try:
            if not self._frame:
                return
            try:
                # reverse the placement so it no longer captures events
                try:
                    self._frame.place_forget()
                except Exception:
                    try:
                        self._frame.lower()
                    except Exception:
                        pass
            except Exception:
                pass
            self._visible = False
        except Exception:
            logging.exception('Error ocultando VisorNegro')

    def destroy(self):
        try:
            if self._frame:
                try:
                    self._frame.destroy()
                except Exception:
                    pass
            self._frame = None
            self._text_widget = None
            self._visible = False
        except Exception:
            logging.exception('Error destruyendo VisorNegro')
