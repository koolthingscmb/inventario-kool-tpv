import customtkinter as ctk
import tkinter.messagebox as messagebox
import tkinter as tk
from modulos.configuracion.reiniciar.reset_service import ResetService


class UIMantenimiento(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.service = ResetService()

        # Layout 20% / 80%
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=20)
        self.grid_columnconfigure(1, weight=80)

        # Left menu
        self.menu_panel = ctk.CTkFrame(self, fg_color="#2c3e50")
        self.menu_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        ctk.CTkButton(self.menu_panel, text="← Volver", fg_color="#e74c3c", command=self._on_volver).pack(fill="x", padx=15, pady=20)
        ctk.CTkLabel(self.menu_panel, text="MANTENIMIENTO", font=("Arial", 16, "bold"), text_color="white").pack(pady=(10,20))

        opts = {"anchor": "w", "height": 45, "font": ("Arial", 13)}
        # Buttons for maintenance actions
        ctk.CTkButton(self.menu_panel, text='Vaciar Ventas', fg_color='#e74c3c', command=self._vaciar_ventas, **opts).pack(fill='x', padx=10, pady=6)
        ctk.CTkButton(self.menu_panel, text='Vaciar Inventario', fg_color='#e67e22', command=self._vaciar_inventario, **opts).pack(fill='x', padx=10, pady=6)
        ctk.CTkButton(self.menu_panel, text='Vaciar Clientes', fg_color='#f39c12', command=self._vaciar_clientes, **opts).pack(fill='x', padx=10, pady=6)
        ctk.CTkButton(self.menu_panel, text='Vaciar Todo', fg_color='#9b59b6', command=self._vaciar_todo, **opts).pack(fill='x', padx=10, pady=12)

        # Main panel
        self.main_panel = ctk.CTkFrame(self, fg_color="#f2f2f2")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.main_panel, fg_color="white", height=70, corner_radius=0)
        header.grid(row=0, column=0, sticky='ew')
        ctk.CTkLabel(header, text='HERRAMIENTAS DE MANTENIMIENTO', font=("Arial", 20, "bold"), text_color='black').pack(side='left', padx=20, pady=14)

        self.content = ctk.CTkFrame(self.main_panel, fg_color='transparent')
        self.content.grid(row=1, column=0, sticky='nsew', padx=20, pady=20)

        info = ctk.CTkLabel(self.content, text='Acciones de limpieza (solo en entorno de desarrollo).', text_color='black')
        info.pack(pady=8)

    def _on_volver(self):
        try:
            if self.controller:
                self.controller.volver_a_configuracion()
        except Exception:
            pass

    def _confirm(self, mensaje: str) -> bool:
        try:
            return messagebox.askyesno('Confirmar', mensaje)
        except Exception:
            return True

    def _vaciar_ventas(self):
        if not self._confirm('¿Estás seguro? Esta acción borrará todos los tickets, cierres y secuencia y no se puede deshacer.'):
            return
        ok = self.service.borrar_ventas()
        if ok:
            messagebox.showinfo('Éxito', 'Ventas vaciadas correctamente')
        else:
            messagebox.showerror('Error', 'Error al vaciar ventas')

    def _vaciar_inventario(self):
        if not self._confirm('¿Estás seguro? Esta acción borrará todos los productos, precios y códigos de barras y no se puede deshacer.'):
            return
        ok = self.service.borrar_inventario()
        if ok:
            messagebox.showinfo('Éxito', 'Inventario vaciado correctamente')
        else:
            messagebox.showerror('Error', 'Error al vaciar inventario')

    def _vaciar_clientes(self):
        if not self._confirm('¿Estás seguro? Esta acción borrará todos los clientes y no se puede deshacer.'):
            return
        ok = self.service.borrar_clientes()
        if ok:
            messagebox.showinfo('Éxito', 'Clientes vaciados correctamente')
        else:
            messagebox.showerror('Error', 'Error al vaciar clientes')

    def _vaciar_todo(self):
        if not self._confirm('¿Estás seguro? Esta acción borrará VENTAS, INVENTARIO y CLIENTES. Es irreversible.'):
            return
        ok = self.service.borrar_todo()
        if ok:
            messagebox.showinfo('Éxito', 'Datos vaciados correctamente')
        else:
            messagebox.showerror('Error', 'Error al vaciar datos')
