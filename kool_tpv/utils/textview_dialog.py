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


from .dialogs.base_dialog import BaseDialog


class TextViewDialog(BaseDialog):
    """Diálogo modal para visualizar texto largo con scroll."""

    def __init__(self, parent, titulo='', texto='', width=None, height=None, callback=None, print_callback=None):
        """
        Args:
            parent: Ventana padre
            titulo: Título del diálogo
            texto: Texto completo a mostrar
            width: Ancho de la ventana (opcional)
            height: Alto de la ventana (opcional)
            callback: Función a ejecutar al cerrar (opcional)
        """
        self.texto_inicial = texto
        self.print_callback = print_callback
        
        # Si no se pasan dimensiones, se usarán las de la config (tipo info por defecto)
        super().__init__(parent, tipo='info', titulo=titulo, callback=callback)
        
        if width and height:
            self.geometry(f"{width}x{height}")

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

    def _crear_contenido(self, titulo, mensaje):
        """Crear widgets del visor de texto dentro de la estructura de BaseDialog."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        
        # Frame principal sin padding (la barra va full-width)
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True)

        # Barra de título con icono
        content_frame = self._crear_barra_titulo(main_frame, titulo)

        # Frame para texto con scroll
        padding_x = int(self.current_geom.get('padding_x', 20))
        padding_y = int(self.current_geom.get('padding_y', 20))
        
        text_container = ctk.CTkFrame(content_frame, fg_color='transparent')
        text_container.pack(fill='both', expand=True, padx=padding_x, pady=(padding_y, 0))

        # Frame interno para tk.Text
        text_frame = tk.Frame(text_container, bg='#2b2b2b')
        text_frame.pack(fill='both', expand=True)

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
            # Limpiar etiquetas de impresión para visualización
            clean_text = (self.texto_inicial or '').replace('{{BOLD_ON}}', '').replace('{{BOLD_OFF}}', '').replace('{{BADGE}}', '')
            self.text_widget.insert('1.0', clean_text)
            self.text_widget.configure(state='disabled')
        except Exception:
            logging.exception('Error insertando texto en TextViewDialog')

        # Botones unificados (Cerrar y opcional Imprimir)
        self.btn = self._crear_botones_visor(content_frame)

    def _crear_botones_visor(self, parent):
        """Crear botones específicos para el visor (Cerrar / Imprimir)."""
        btn_frame = ctk.CTkFrame(parent, fg_color='transparent')
        pady_top = self.current_spacing.get('message_bottom', 10)
        btn_frame.pack(pady=(pady_top, 10))

        # Botón Imprimir (si se provee callback)
        if self.print_callback is not None:
            try:
                self.print_btn = ctk.CTkButton(
                    btn_frame,
                    text='IMPRIMIR',
                    command=self._on_print,
                    fg_color='#2ecc71',
                    hover_color='#27ae60',
                    font=self._get_font('button'),
                    width=160,
                    height=44,
                    corner_radius=8
                )
                self.print_btn.pack(side='left', padx=(0, 12))
                self._setup_button_focus(self.print_btn, is_accept=True)
            except Exception:
                logging.exception('Error creando botón IMPRIMIR en TextViewDialog')

        # Botón Cerrar (usa estilo de aceptar de info)
        style_key = self._get_button_style_key()
        self.btn = ctk.CTkButton(
            btn_frame,
            text='CERRAR',
            command=self._on_close,
            fg_color=self.dialogs_colors.get('info', {}).get('button_bg', '#3498db'),
            hover_color=self.dialogs_colors.get('info', {}).get('button_hover', '#2980b9'),
            font=self._get_font('button'),
            width=200,
            height=50,
            corner_radius=10
        )
        self.btn.pack(side='left')
        self._setup_button_focus(self.btn, is_accept=True)
        return self.btn

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


def show_text_viewer(parent, titulo, texto, width=None, height=None, callback=None, print_callback=None):
    """Mostrar diálogo de visualización de texto largo.

    Args:
        parent: Ventana padre
        titulo: Título del diálogo
        texto: Texto completo a mostrar (monoespaciado)
        width: Ancho de la ventana (opcional)
        height: Alto de la ventana (opcional)
        callback: Función a ejecutar al cerrar (opcional)
    """
    try:
        TextViewDialog(parent, titulo=titulo, texto=texto, width=width, height=height, callback=callback, print_callback=print_callback)
    except Exception:
        logging.exception('Error mostrando TextViewDialog')
