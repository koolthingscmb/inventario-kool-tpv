"""
TextViewDialog - Template para visualizar texto largo con scroll.

Similar a CustomDialog pero especializado en mostrar textos extensos
(tickets, informes, cierres de caja) con fuente monoespaciada.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import logging
import tkinter as tk


class TextViewDialog(ctk.CTkToplevel):
    """Diálogo modal para visualizar texto largo con scroll."""

    def __init__(self, parent, titulo='', texto='', width=600, height=800, callback=None, print_callback=None):
        """
        Args:
            parent: Ventana padre
            titulo: Título del diálogo
            texto: Texto completo a mostrar
            width: Ancho de la ventana (default 600)
            height: Alto de la ventana (default 800)
            callback: Función a ejecutar al cerrar (opcional)
        """
        super().__init__(parent)

        self.callback = callback
        self.print_callback = print_callback

        # Configurar ventana
        self.title(titulo or 'Visualización')
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)

        try:
            self.configure(fg_color='#2b2b2b')
        except Exception:
            pass

        # Prepare hidden window, set transient and compute geometry before mapping
        try:
            self.withdraw()
        except Exception:
            pass
        try:
            self.transient(parent)
        except Exception:
            pass

        try:
            self.update_idletasks()
            w, h = width, height
            if parent is not None and getattr(parent, 'winfo_ismapped', None) and parent.winfo_ismapped():
                try:
                    parent.update_idletasks()
                    px = parent.winfo_rootx()
                    py = parent.winfo_rooty()
                    pw = parent.winfo_width() or parent.winfo_reqwidth()
                    ph = parent.winfo_height() or parent.winfo_reqheight()
                    x = px + max(0, (pw - w) // 2)
                    y = py + max(0, (ph - h) // 2)
                except Exception:
                    x = (self.winfo_screenwidth() // 2) - (w // 2)
                    y = (self.winfo_screenheight() // 2) - (h // 2)
            else:
                x = (self.winfo_screenwidth() // 2) - (w // 2)
                y = (self.winfo_screenheight() // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        self._crear_contenido(titulo, texto)

        # Show immediately (no animation) and grab
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

        # Bind Escape para cerrar
        try:
            self.bind('<Escape>', lambda e: self._on_close())
        except Exception:
            pass

        # Foco en el botón (sin delay)
        try:
            self.btn.focus_set()
        except Exception:
            pass

    def _cargar_icono(self):
        """Cargar icono dialog_info.png (libro mágico azul)."""
        try:
            base = Path(__file__).resolve().parents[1]  # kool_tpv/
            icon_path = base / "assets" / "dialogs" / "dialog_info.png"

            if icon_path.exists():
                img = Image.open(icon_path)
                img = img.resize((96, 96), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(96, 96))
        except Exception:
            logging.exception('Error cargando icono dialog_info.png en TextViewDialog')

        return None

    def _crear_contenido(self, titulo, texto):
        """Crear widgets del diálogo."""
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(0, 10))

        # Título
        if titulo:
            titulo_label = ctk.CTkLabel(
                main_frame,
                text=titulo,
                font=('Roboto-Bold', 24),
                text_color='#FFFFFF'
            )
            titulo_label.pack(pady=(0, 10))

        # Frame para texto con scroll
        text_frame = tk.Frame(main_frame, bg='#2b2b2b')
        text_frame.pack(fill='both', expand=True, pady=(0, 15))

        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')

        # Text widget con fuente monoespaciada
        self.text_widget = tk.Text(
            text_frame,
            font=('Courier New', 10),
            bg='#FFFFFF',
            fg='#000000',
            wrap='none',
            padx=15,
            pady=15,
            relief='flat',
            yscrollcommand=scrollbar.set
        )
        self.text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.text_widget.yview)

        # Insertar texto
        try:
            self.text_widget.insert('1.0', texto or '')
            self.text_widget.configure(state='disabled')
        except Exception:
            logging.exception('Error insertando texto en TextViewDialog')

        # Botones: Cerrar (por defecto focus) y opcional Imprimir
        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(pady=(10, 0))

        # Botón Imprimir (si se provee callback)
        if self.print_callback is not None:
            try:
                self.print_btn = ctk.CTkButton(
                    btn_frame,
                    text='IMPRIMIR',
                    command=self._on_print,
                    fg_color='#2ecc71',
                    hover_color='#27ae60',
                    font=('Roboto-SemiBold', 18),
                    width=160,
                    height=44,
                    corner_radius=8
                )
                self.print_btn.pack(side='left', padx=(0, 12))
            except Exception:
                logging.exception('Error creando botón IMPRIMIR en TextViewDialog')

        # Botón Cerrar (color info azul)
        self.btn = ctk.CTkButton(
            btn_frame,
            text='CERRAR',
            command=self._on_close,
            fg_color='#3498db',
            hover_color='#2980b9',
            font=('Roboto-SemiBold', 20),
            width=200,
            height=50,
            corner_radius=10
        )
        self.btn.pack(side='left')

    def _on_close(self):
        """Cerrar diálogo y ejecutar callback si existe."""
        try:
            if self.callback and callable(self.callback):
                self.callback()
        except Exception:
            logging.exception('Error ejecutando callback de TextViewDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_print(self):
        """Ejecutar la callback de impresión si existe."""
        try:
            if self.print_callback and callable(self.print_callback):
                try:
                    self.print_callback()
                except Exception:
                    logging.exception('Error ejecutando print_callback en TextViewDialog')
        except Exception:
            logging.exception('Error en _on_print de TextViewDialog')


def show_text_viewer(parent, titulo, texto, width=600, height=800, callback=None, print_callback=None):
    """Mostrar diálogo de visualización de texto largo.

    Args:
        parent: Ventana padre
        titulo: Título del diálogo
        texto: Texto completo a mostrar (monoespaciado)
        width: Ancho de la ventana (default 600)
        height: Alto de la ventana (default 800)
        callback: Función a ejecutar al cerrar (opcional)
    """
    try:
        TextViewDialog(parent, titulo=titulo, texto=texto, width=width, height=height, callback=callback, print_callback=print_callback)
    except Exception:
        logging.exception('Error mostrando TextViewDialog')
