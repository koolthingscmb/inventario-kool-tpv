import customtkinter as ctk
import tkinter as tk
from tkinter import Toplevel, ttk, Button, Label, messagebox

from modulos.impresion.print_service import ImpresionService


class ConfiguracionImpresoraDialog:
    def __init__(self, master):
        self.master = master
        self.impresion_service = ImpresionService()

        # Crear la ventana de diálogo
        self.window = Toplevel(master)
        self.window.title("Configurar Impresora")
        try:
            self.window.geometry("420x260")
        except Exception:
            pass

        # Título
        Label(self.window, text="Configurar Impresora", font=("Arial", 14, "bold")).pack(pady=10)

        # Combobox para elegir impresora
        Label(self.window, text="Seleccione la impresora:").pack(pady=5)
        impresoras = self.impresion_service.listar_impresoras() or []
        self.combobox = ttk.Combobox(self.window, values=impresoras)
        self.combobox.pack(pady=5)
        try:
            # Preseleccionar si existe
            current = self.impresion_service.nombre_impresora or ''
            if current:
                try:
                    self.combobox.set(current)
                except Exception:
                    pass
        except Exception:
            pass

        # Botón de prueba de impresión
        btn_frame = ctk.CTkFrame(self.window)
        btn_frame.pack(fill='x', pady=12, padx=12)

        def probar_impresora():
            seleccionada = self.combobox.get().strip()
            if not seleccionada:
                messagebox.showerror('Impresora', 'Seleccione una impresora para probar.')
                return
            try:
                # Guardar temporalmente para que el backend use el nombre
                self.impresion_service.guardar_configuracion(nombre_impresora=seleccionada, ancho_ticket=self.impresion_service.ticket_width or '80mm')
                texto_prueba = "Kool Things - Prueba de impresión.\nTicket de prueba."
                ok = self.impresion_service.imprimir_ticket(texto_prueba)
                if ok:
                    messagebox.showinfo('Prueba', 'Impresión enviada (o simulada) correctamente.')
                else:
                    messagebox.showwarning('Prueba', 'El envío de impresión devolvió un estado no OK.')
            except Exception as e:
                messagebox.showerror('Prueba', f'Error prueba impresión: {e}')

        def guardar_configuracion():
            seleccionada = self.combobox.get().strip()
            if not seleccionada:
                messagebox.showerror('Guardar', 'Seleccione una impresora antes de guardar.')
                return
            try:
                self.impresion_service.guardar_configuracion(nombre_impresora=seleccionada, ancho_ticket=self.impresion_service.ticket_width or '80mm')
                messagebox.showinfo('Guardar', f'Impresora guardada: {seleccionada}')
                try:
                    self.window.destroy()
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror('Guardar', f'Error guardando configuración: {e}')

        ctk.CTkButton(btn_frame, text='Probar impresión', command=probar_impresora, fg_color='#3399FF').pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text='Guardar', command=guardar_configuracion, fg_color='#2E8B57').pack(side='right', padx=6)

        # Cancelar
        ctk.CTkButton(self.window, text='Cancelar', command=lambda: self.window.destroy(), fg_color='#777777').pack(side='bottom', pady=10)
