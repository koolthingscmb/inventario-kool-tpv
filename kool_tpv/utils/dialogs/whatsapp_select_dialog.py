import customtkinter as ctk
import logging
import tkinter as tk
from typing import List, Dict, Optional

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

logger = logging.getLogger(__name__)

class WhatsappSelectDialog(BaseDialog):
    """Diálogo para seleccionar plantillas de WhatsApp.
    
    Usa checkboxes siguiendo el estilo del Cierre Z.
    """
    def __init__(self, parent, plantillas: List[Dict], cliente_data: Dict, titulo="Seleccionar Mensaje"):
        self.plantillas = plantillas
        self.cliente_data = cliente_data
        self.result = None
        
        # Guardar variables de cada checkbox
        self.options_vars = []
        for p in self.plantillas:
            self.options_vars.append({"nombre": p['nombre'], "texto": p['texto'], "var": tk.BooleanVar(value=False)})
            
        # Opción extra: mensaje en blanco
        self.blank_var = tk.BooleanVar(value=False)
        
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido()
        
        # Ajustar tamaño
        self.geometry("500x600")
        self._center_window(parent, 500, 600)

    def _crear_contenido(self):
        """Construye el contenido del diálogo con checkboxes."""
        from .content_container import create_dialog_content_container
        
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        title_font = self._get_font('title')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        content_parent = create_dialog_content_container(main_frame, self.geometry_cfg)
        
        # Título
        ctk.CTkLabel(
            content_parent,
            text="MENSAJE WHATSAPP",
            font=title_font,
            text_color=tipo_config.get('title_text', '#FFFFFF')
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            content_parent,
            text="SELECCIONA LAS PLANTILLAS A ENVIAR:",
            font=message_font,
            text_color=tipo_config.get('message_text', '#FFFFFF')
        ).pack(pady=(0, 15))

        # Contenedor scrollable para las opciones
        scroll_frame = ctk.CTkScrollableFrame(
            content_parent, 
            fg_color='transparent',
            height=300,
            scrollbar_button_color=tipo_config.get('primary', '#00FF00')
        )
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Opción: Mensaje en blanco (siempre primero)
        cb_blank = ctk.CTkCheckBox(
            scroll_frame,
            text="MENSAJE EN BLANCO (ESCRIBIR A MANO)",
            variable=self.blank_var,
            font=message_font,
            checkbox_width=24,
            checkbox_height=24,
            border_width=2,
            command=lambda: self._on_checkbox_changed(-1)
        )
        cb_blank.pack(pady=8, anchor="w", padx=10)

        # Separador visual
        ctk.CTkFrame(scroll_frame, height=2, fg_color="#333333").pack(fill='x', pady=10, padx=5)

        # Listado de plantillas
        for i, opt in enumerate(self.options_vars):
            cb = ctk.CTkCheckBox(
                scroll_frame,
                text=opt["nombre"].upper(),
                variable=opt["var"],
                font=message_font,
                checkbox_width=24,
                checkbox_height=24,
                border_width=2,
                command=lambda idx=i: self._on_checkbox_changed(idx)
            )
            cb.pack(pady=8, anchor="w", padx=10)

        # Botones
        btn_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(20, 0))
        
        # Cancelar
        self.btn_cancel = ButtonFactory.create_button(
            parent=btn_frame,
            text='CANCELAR',
            command=self._on_cancel,
            style_key='dialog_cancel_btn',
            font=button_font
        )
        self.btn_cancel.pack(side='left', expand=True, padx=(0, 10))

        # Aceptar
        self.btn_accept = ButtonFactory.create_button(
            parent=btn_frame,
            text='ABRIR WHATSAPP',
            command=self._on_accept,
            style_key=self._get_button_style_key(),
            font=button_font
        )
        self.btn_accept.pack(side='left', expand=True)
        self.btn_accept.focus_set()

    def _on_checkbox_changed(self, index):
        """Lógica opcional: si quieres que se comporte como radio button 
        pero con aspecto de checkbox, descomenta la lógica de desmarcar otros.
        Si prefieres permitir concatenar mensajes, déjalo vacío.
        
        De momento permitimos selección múltiple para concatenar, 
        que es más flexible si usan checkboxes.
        """
        pass

    def _on_accept(self):
        """Procesar selección y cerrar."""
        textos_finales = []
        
        # Si marcó "en blanco", ignoramos el resto y mandamos vacío
        if self.blank_var.get():
            self.result = ""
        else:
            # Concatenar todos los seleccionados
            for opt in self.options_vars:
                if opt["var"].get():
                    texto = opt["texto"]
                    # Reemplazar variables
                    texto = texto.replace('{nombre}', self.cliente_data.get('nombre', ''))\
                                 .replace('{telefono}', self.cliente_data.get('telefono', ''))\
                                 .replace('{email}', self.cliente_data.get('email', ''))
                    textos_finales.append(texto)
            
            if not textos_finales:
                # Si no seleccionó nada, asumimos en blanco
                self.result = ""
            else:
                # Unir con dos saltos de línea
                self.result = "\n\n".join(textos_finales)
        
        self.destroy()

    def _on_cancel(self):
        """Cancelar operación."""
        self.result = None
        self.destroy()

def show_whatsapp_select_dialog(parent, plantillas: List[Dict], cliente_data: Dict) -> Optional[str]:
    """Muestra el diálogo y retorna el mensaje formateado o None si cancela."""
    dialog = WhatsappSelectDialog(parent, plantillas, cliente_data)
    parent.wait_window(dialog)
    return dialog.result
