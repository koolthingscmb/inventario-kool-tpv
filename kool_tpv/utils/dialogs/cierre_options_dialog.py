import customtkinter as ctk
import logging

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

logger = logging.getLogger(__name__)

class CierreOptionsDialog(BaseDialog):
    """Diálogo para seleccionar opciones de impresión del cierre.
    
    Hereda de BaseDialog para mantener la consistencia visual del TPV.
    """
    def __init__(self, parent, titulo="Opciones de Cierre", callback=None):
        # Usamos tipo='info' para el estilo visual
        super().__init__(parent, tipo='info', titulo=titulo, callback=callback)
        
        self.result = None
        
        # Opciones disponibles (las obligatorias se mencionan pero no se eligen)
        self.options = {
            "6": {"text": "VENTAS POR CATEGORÍA", "var": ctk.BooleanVar(value=True)},
            "7": {"text": "DEVOLUCIONES POR CATEGORÍA", "var": ctk.BooleanVar(value=True)},
            "8": {"text": "VENTAS POR TIPO", "var": ctk.BooleanVar(value=True)},
            "9": {"text": "DEVOLUCIONES POR TIPO", "var": ctk.BooleanVar(value=True)},
            "11": {"text": "DETALLE DE PRODUCTOS", "var": ctk.BooleanVar(value=False)},
            "12": {"text": "PUNTOS DE TESORO", "var": ctk.BooleanVar(value=True)},
        }
        
        # Crear contenido específico
        self._crear_contenido()
        
        # Bindings de teclado
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_accept())
        
        # Ajustar tamaño final (sobrescribir el del BaseDialog que es muy pequeño)
        self._setup_geometry_custom(parent, 400, 600)

    def _setup_geometry_custom(self, parent, w, h):
        """Configuración de geometría personalizada para este diálogo."""
        self.geometry(f"{w}x{h}")
        self._center_window(parent, w, h)

    def _crear_contenido(self):
        """Construye la interfaz del diálogo siguiendo el estilo base."""
        from .content_container import create_dialog_content_container
        
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        title_font = self._get_font('title')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        # Frame principal con padding
        padding_x = int(self.geometry_cfg.get('padding_x', 20))
        padding_y = int(self.geometry_cfg.get('padding_y', 20))
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=padding_x, pady=padding_y)
        
        content_parent = create_dialog_content_container(main_frame, self.geometry_cfg)
        
        # Título
        title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
        titulo_label = ctk.CTkLabel(
            content_parent,
            text="IMPRESIÓN DE CIERRE",
            font=title_font,
            text_color=title_color
        )
        titulo_label.pack(pady=(10, 5))
        
        subtitulo_label = ctk.CTkLabel(
            content_parent,
            text="SELECCIONA BLOQUES OPCIONALES:",
            font=message_font,
            text_color=tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
        )
        subtitulo_label.pack(pady=(0, 15))

        # Contenedor de Checkboxes
        options_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        options_frame.pack(fill='x', padx=20, pady=10)
        
        for key, opt in self.options.items():
            cb = ctk.CTkCheckBox(
                options_frame,
                text=opt["text"],
                variable=opt["var"],
                font=message_font,
                checkbox_width=24,
                checkbox_height=24,
                border_width=2
            )
            cb.pack(pady=6, anchor="w")

        # Info de bloques obligatorios
        info_fijos = ctk.CTkLabel(
            content_parent,
            text="* Ventas, IVA, Finanzas y Cajeros se imprimirán siempre.",
            font=(message_font[0], message_font[1]-2, 'italic'),
            text_color="#888888"
        )
        info_fijos.pack(pady=(15, 20))

        # Botones (Cancelar / Confirmar)
        btn_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(10, 0))
        
        # Cancelar
        self.btn_cancel = ButtonFactory.create_button(
            parent=btn_frame,
            text='CANCELAR',
            command=self._on_cancel,
            style_key='dialog_cancel_btn',
            font=button_font
        )
        self.btn_cancel.pack(side='left', expand=True, padx=(0, 10))
        self._setup_button_focus(self.btn_cancel, is_accept=False)

        # Confirmar
        self.btn_accept = ButtonFactory.create_button(
            parent=btn_frame,
            text='GENERAR E IMPRIMIR',
            command=self._on_accept,
            style_key=self._get_button_style_key(),
            font=button_font
        )
        self.btn_accept.pack(side='left', expand=True)
        self._setup_button_focus(self.btn_accept, is_accept=True)
        
        # Foco inicial
        self.btn_accept.focus_set()

    def _on_accept(self):
        """Guardar selección y cerrar."""
        self.result = {k: v["var"].get() for k, v in self.options.items()}
        # Forzar Bloque 4 como True siempre (aunque ya se gestiona en el generador)
        self.result["4"] = True
        
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_cancel(self):
        """Cancelar operación."""
        self.result = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

def show_cierre_options_dialog(parent):
    """Función helper para mostrar el diálogo y retornar el resultado."""
    dialog = CierreOptionsDialog(parent)
    # Al heredar de BaseDialog, ya se centra y se hace modal
    parent.wait_window(dialog)
    return dialog.result
