"""Diálogo modal para validar la clave maestra de configuración.

Clase: DialogoPassConfig(ctk.CTkToplevel)

Uso: crear la instancia pasando el `parent` (root o ventana padre), luego
`parent.wait_window(dialog)` para bloquear hasta que se cierre. Revisar
`dialog.resultado` para saber si la validación fue exitosa.
"""
from typing import Optional
import tkinter as tk
import customtkinter as ctk
import tkinter.font as tkfont

from modulos.configuracion.config_service import ConfigService


class DialogoPassConfig(ctk.CTkToplevel):
    def __init__(self, parent: Optional[tk.Widget] = None):
        super().__init__(parent)

        self.parent = parent
        self.title('ACCESO RESTRINGIDO')
        self.geometry('350x220')
        self.resizable(False, False)

        # Modal
        if parent:
            try:
                self.transient(parent)
            except Exception:
                pass
        try:
            self.grab_set()
        except Exception:
            pass

        # Resultado público que la pantalla llamante comprobará
        self.resultado = False

        # Estilo y fuentes
        heading_font = ('Arial', 14, 'bold')
        label_font = ('Arial', 11)
        entry_font = ('Arial', 16)

        # Contenedor
        pad = 12
        self.grid_columnconfigure(0, weight=1)

        # Título / encabezado
        lbl_head = ctk.CTkLabel(self, text='ACCESO RESTRINGIDO', font=heading_font)
        lbl_head.grid(row=0, column=0, padx=pad, pady=(16, 8), sticky='n')

        # Instrucción
        lbl_instr = ctk.CTkLabel(self, text='Introduzca la clave maestra:', font=label_font)
        lbl_instr.grid(row=1, column=0, padx=pad, pady=(4, 8), sticky='w')

        # Entry para contraseña
        self.entry_var = tk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, show='*', font=entry_font, justify='center')
        self.entry.grid(row=2, column=0, padx=pad, pady=(0, 8), sticky='ew')

        # Etiqueta de error (vacía inicialmente)
        self.lbl_error = ctk.CTkLabel(self, text='', text_color='red', font=label_font)
        self.lbl_error.grid(row=3, column=0, padx=pad, pady=(4, 8), sticky='w')

        # Botones
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=4, column=0, padx=pad, pady=(8, 12), sticky='e')
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_cancel = ctk.CTkButton(btn_frame, text='CANCELAR', width=100, command=self.on_cancel)
        self.btn_cancel.grid(row=0, column=0, padx=(0, 8))
        self.btn_ok = ctk.CTkButton(btn_frame, text='ACEPTAR', width=100, command=self.on_accept)
        self.btn_ok.grid(row=0, column=1)

        # Bindings
        self.entry.bind('<Return>', self.on_accept)
        self.entry.bind('<KP_Enter>', self.on_accept)

        # Focus
        try:
            self.entry.focus_set()
        except Exception:
            pass

        # Centrar respecto al padre o pantalla
        self.update_idletasks()
        self._center()

    def _center(self):
        w = 350
        h = 220
        try:
            if self.parent:
                px = self.parent.winfo_rootx()
                py = self.parent.winfo_rooty()
                pw = self.parent.winfo_width()
                ph = self.parent.winfo_height()
                x = px + max(0, (pw - w) // 2)
                y = py + max(0, (ph - h) // 2)
            else:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = (sw - w) // 2
                y = (sh - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            try:
                self.geometry(f"{w}x{h}")
            except Exception:
                pass

    def on_accept(self, event=None):
        intento = (self.entry_var.get() or '').strip()
        try:
            ok = ConfigService.validar_pass_config(intento)
        except Exception:
            ok = False

        if ok:
            self.resultado = True
            try:
                self.grab_release()
            except Exception:
                pass
            try:
                self.destroy()
            except Exception:
                pass
        else:
            self.lbl_error.configure(text='Clave incorrecta')
            try:
                self.entry_var.set('')
                self.entry.focus_set()
            except Exception:
                pass

    def on_cancel(self, event=None):
        self.resultado = False
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
