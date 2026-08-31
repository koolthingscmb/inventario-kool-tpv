import customtkinter as ctk
import logging
import tkinter as tk
from typing import List, Dict, Optional

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

logger = logging.getLogger(__name__)

class ReposicionSelectDialog(BaseDialog):
    """Diálogo para seleccionar una línea de reposición entre varias opciones."""
    
    def __init__(self, parent, potenciales: List[Dict], titulo="Seleccionar Reposición"):
        self.potenciales = potenciales
        self.result = None
        self.selected_var = tk.StringVar(value="") # Guardará el ID de la línea seleccionada
        
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido()
        
        # Ajustar tamaño
        self.geometry("600x500")
        self._center_window(parent, 600, 500)

    def _crear_contenido(self):
        """Construye el contenido del diálogo con radio buttons."""
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
            text="VINCULAR REPOSICIÓN",
            font=title_font,
            text_color=tipo_config.get('title_text', '#FFFFFF')
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            content_parent,
            text="SELECCIONA LA LÍNEA QUE CORRESPONDE:",
            font=message_font,
            text_color=tipo_config.get('message_text', '#FFFFFF')
        ).pack(pady=(0, 15))

        # Contenedor scrollable para las opciones
        scroll_frame = ctk.CTkScrollableFrame(
            content_parent, 
            fg_color='transparent',
            height=250,
            scrollbar_button_color=tipo_config.get('primary', '#00FF00')
        )
        scroll_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Listado de reposiciones
        for p in self.potenciales:
            repo_id = p.get('id')
            # Intentar usar el nombre enriquecido que pasamos desde el resumen
            diseno = p.get('_diseno_nombre_db') or p.get('diseno_codigo') or "SIN DISEÑO"
            comentarios = p.get('comentarios') or "(Sin comentarios)"
            fecha = p.get('fecha', '')[:10]
            cantidad = p.get('cantidad', 0)
            
            # Texto descriptivo
            label_text = f"{diseno} - Cant: {cantidad} - {fecha}\n   {comentarios}"
            
            rb = ctk.CTkRadioButton(
                scroll_frame,
                text=label_text,
                variable=self.selected_var,
                value=repo_id,
                font=message_font,
                radiobutton_width=24,
                radiobutton_height=24,
                border_width_unchecked=2,
                border_width_checked=6
            )
            rb.pack(pady=8, anchor="w", padx=10)

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
            text='VINCULAR',
            command=self._on_accept,
            style_key=self._get_button_style_key(),
            font=button_font
        )
        self.btn_accept.pack(side='left', expand=True)
        self.btn_accept.focus_set()

    def _on_accept(self):
        """Procesar selección y cerrar."""
        val = self.selected_var.get()
        if not val:
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self, "Selecciona una opción o cancela", tipo='warning')
            return
            
        self.result = val
        self.destroy()

    def _on_cancel(self):
        """Cancelar operación."""
        self.result = None
        self.destroy()

def show_reposicion_select_dialog(parent, potenciales: List[Dict]) -> Optional[str]:
    """Muestra el diálogo y retorna el ID de la reposición seleccionada o None."""
    dialog = ReposicionSelectDialog(parent, potenciales)
    parent.wait_window(dialog)
    return dialog.result
