import customtkinter as ctk
import tkinter as tk
from typing import Optional, List, Dict

from modulos.configuracion.usuario_service import UsuarioService


class LoginCajero(ctk.CTkToplevel):
    def __init__(self, parent, title: str = 'Login Cajero'):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry('450x400')
        try:
            self.transient(parent)
        except Exception:
            pass
        self.resizable(False, False)
        self.result: Optional[Dict] = None

        self.service = UsuarioService()
        self._users = self.service.listar_usuarios() or []
        self._buttons = {}
        self._selected_name: Optional[str] = None

        # Center window over parent
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = 500
            h = 450
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        # Main frame
        self.frame = ctk.CTkFrame(self, fg_color='transparent')
        self.frame.pack(fill='both', expand=True, padx=16, pady=16)

        # Title
        self.lbl_title = ctk.CTkLabel(self.frame, text='IDENTIFICACIÓN DE CAJERO', font=('Arial', 16, 'bold'), text_color='white')
        self.lbl_title.pack(pady=(0, 12))

        # Users buttons area (simple frame that adapts to content)
        self.users_frame = ctk.CTkFrame(self.frame, fg_color='transparent')
        self.users_frame.pack(fill='x', pady=(0, 12))
        self._render_user_buttons()

        # Password label
        self.lbl_pwd_title = ctk.CTkLabel(self.frame, text='INTRODUZCA SU CLAVE', font=('Arial', 16, 'bold'), text_color='white')
        self.lbl_pwd_title.pack(pady=(8, 6))

        # Password entry large
        self.entry_password = ctk.CTkEntry(self.frame, show='*', font=('Arial', 24), fg_color='white', text_color='black')
        self.entry_password.pack(fill='x', pady=(0, 8))
        self.entry_password.bind('<Return>', lambda e: self._on_login())
        self.entry_password.bind('<KP_Enter>', lambda e: self._on_login())

        # feedback label (inline)
        self.lbl_error = ctk.CTkLabel(self.frame, text='', text_color='red', font=('Arial', 12))
        self.lbl_error.pack(pady=(4, 8))

        # Buttons (placed at bottom, centered)
        btn_frame = ctk.CTkFrame(self.frame, fg_color='transparent')
        btn_frame.pack(side='bottom', pady=(12, 16))
        self.btn_cancel = ctk.CTkButton(btn_frame, text='CANCELAR', width=140, fg_color='#95a5a6', command=self._on_cancel)
        self.btn_cancel.grid(row=0, column=0, padx=8, pady=8)
        self.btn_enter = ctk.CTkButton(btn_frame, text='ENTRAR', width=140, fg_color='#2ecc71', command=self._on_login)
        self.btn_enter.grid(row=0, column=1, padx=8, pady=8)

        # Select first user by default (if any)
        if self._users:
            try:
                first = self._users[0].get('nombre')
                if first:
                    self._select_user(first)
            except Exception:
                pass

        # focus password by default
        try:
            self.entry_password.focus_set()
        except Exception:
            pass

        # adjust window size to content
        try:
            self.update_idletasks()
            req_w = self.winfo_reqwidth()
            req_h = self.winfo_reqheight()
            w = min(450, max(300, req_w + 32))
            h = min(400, max(250, req_h + 32))
            try:
                pw = self.parent.winfo_width()
                ph = self.parent.winfo_height()
                px = self.parent.winfo_rootx()
                py = self.parent.winfo_rooty()
                x = px + max(0, (pw - w) // 2)
                y = py + max(0, (ph - h) // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")
            except Exception:
                self.geometry(f"{w}x{h}")
        except Exception:
            pass

        # keys: Enter handled by entry, but ensure top-level also responds to KP_Enter
        try:
            self.bind('<KP_Enter>', lambda e: self._on_login())
            self.bind('<Return>', lambda e: self._on_login())
        except Exception:
            pass

        # modal
        try:
            self.grab_set()
        except Exception:
            pass

    def _render_user_buttons(self):
        # clear
        try:
            for w in self.users_frame.winfo_children():
                w.destroy()
        except Exception:
            pass

        # create a button per user in a grid (max 3 columns)
        col = 0
        row = 0
        for u in self._users:
            nombre = u.get('nombre') or ''
            btn = ctk.CTkButton(self.users_frame, text=nombre, width=140, height=50, fg_color='#777777', corner_radius=10,
                                font=('Arial', 14, 'bold'), command=lambda n=nombre: self._on_user_click(n))
            btn.grid(row=row, column=col, padx=8, pady=8)
            self._buttons[nombre] = btn
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _on_user_click(self, nombre: str):
        # mark selection visually and focus password
        self._select_user(nombre)
        try:
            self.entry_password.focus_set()
        except Exception:
            pass

    def _select_user(self, nombre: str):
        # deselect previous
        try:
            for n, b in self._buttons.items():
                try:
                    b.configure(fg_color='#777777')
                except Exception:
                    pass
        except Exception:
            pass
        # select current
        try:
            btn = self._buttons.get(nombre)
            if btn:
                btn.configure(fg_color='#2ecc71')
        except Exception:
            pass
        self._selected_name = nombre

    def _on_cancel(self):
        self.result = None
        try:
            self.destroy()
        except Exception:
            pass

    def _on_login(self):
        nombre = self._selected_name or ''
        pwd = ''
        try:
            pwd = self.entry_password.get() or ''
        except Exception:
            pwd = ''

        if not nombre:
            self.lbl_error.configure(text='Selecciona un cajero')
            return

        try:
            user = self.service.verificar_credenciales(nombre, pwd)
        except Exception:
            user = None

        if user:
            # fast flow: close immediately with result
            self.result = user
            try:
                self.destroy()
            except Exception:
                pass
        else:
            # show inline error and clear password
            try:
                self.lbl_error.configure(text='Contraseña incorrecta')
            except Exception:
                pass
            try:
                self.entry_password.delete(0, tk.END)
            except Exception:
                pass

