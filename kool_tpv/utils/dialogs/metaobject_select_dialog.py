import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional
from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

class MetaobjectSelectDialog(BaseDialog):
    """Diálogo para selección múltiple de metaobjetos de Shopify."""
    
    def __init__(self, parent, tipo_meta: str, opciones: List[Dict[str, Any]], seleccionados_actuales: List[str]):
        self.tipo_meta = tipo_meta
        self.opciones = opciones
        self.seleccionados_actuales = set(seleccionados_actuales)
        self.checkboxes = {}
        
        titulo = f"SELECCIONAR {tipo_meta.upper()}"
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido_especifico()
        # Ajustar geometría si es necesario (BaseDialog ya hace un setup inicial)
        self.geometry("500x650")
        self._center_window(parent, 500, 650)

    def _crear_contenido_especifico(self):
        # 1. Crear barra de título (Kool Style)
        # Nota: BaseDialog._crear_barra_titulo devuelve el content_frame
        content_frame = self._crear_barra_titulo(self, self.title())
        
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        primary_color = tipo_config.get('primary', '#00A4DF')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        main_container = ctk.CTkFrame(content_frame, fg_color='transparent')
        main_container.pack(fill='both', expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            main_container, text=f"SELECCIONA {self.tipo_meta.upper()}:", 
            font=self._get_font('title'), text_color=primary_color
        ).pack(pady=(5, 10))

        # 2. Área de scroll con checkboxes
        scroll_frame = ctk.CTkScrollableFrame(
            main_container, fg_color='transparent',
            scrollbar_button_color=primary_color
        )
        scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        for op in self.opciones:
            i_id = op['id']
            i_name = op['displayName']
            
            var = tk.BooleanVar(value=i_id in self.seleccionados_actuales)
            cb = ctk.CTkCheckBox(
                scroll_frame, text=i_name.upper(), variable=var,
                font=message_font, fg_color=primary_color
            )
            cb.pack(pady=5, anchor="w", padx=10)
            self.checkboxes[i_id] = var

        # 3. Botones (Kool Style)
        # self._crear_botones devuelve el botón de aceptar si confirm=True
        self._crear_botones(content_frame, btn_text='CONFIRMAR SELECCIÓN', confirm=True)

    def _on_accept(self):
        """Al pulsar confirmar, guardamos resultado y cerramos."""
        self.result = [gid for gid, var in self.checkboxes.items() if var.get()]
        try:
            self.grab_release()
        except: pass
        self.destroy()

    def _on_cancel(self):
        """Al cancelar, devolvemos None."""
        self.result = None
        try:
            self.grab_release()
        except: pass
        self.destroy()

def show_metaobject_select_dialog(parent, tipo_meta: str, opciones: List[Dict[str, Any]], seleccionados_actuales: List[str]) -> Optional[List[str]]:
    """Función helper para mostrar el diálogo y esperar resultado."""
    dialog = MetaobjectSelectDialog(parent, tipo_meta, opciones, seleccionados_actuales)
    parent.wait_window(dialog)
    return dialog.result
