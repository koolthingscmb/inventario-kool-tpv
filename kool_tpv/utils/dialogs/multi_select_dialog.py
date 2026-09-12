import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Any, Optional
from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

class MultiSelectDialog(BaseDialog):
    """Diálogo genérico para selección múltiple de elementos."""
    
    def __init__(self, parent, items: List[Dict[str, Any]], selected_ids: List[int], titulo="Seleccionar"):
        self.items = items # [{ 'id': 1, 'nombre': 'Manga' }, ...]
        self.selected_ids = set(selected_ids)
        self.result = None
        self.checkboxes = {}
        
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido()
        self.geometry("500x600")
        self._center_window(parent, 500, 600)

    def _crear_contenido(self):
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        title_font = self._get_font('title')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            main_frame, text="VINCULAR TIPOS", 
            font=title_font, text_color=tipo_config.get('title_text', '#FFFFFF')
        ).pack(pady=(10, 5))

        scroll_frame = ctk.CTkScrollableFrame(
            main_frame, fg_color='transparent', height=400,
            scrollbar_button_color=tipo_config.get('primary', '#00A4DF')
        )
        scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        for item in self.items:
            i_id = item['id']
            i_name = item['nombre']
            
            var = tk.BooleanVar(value=i_id in self.selected_ids)
            cb = ctk.CTkCheckBox(
                scroll_frame, text=i_name.upper(), variable=var,
                font=message_font, fg_color=tipo_config.get('primary', '#00A4DF')
            )
            cb.pack(pady=5, anchor="w", padx=10)
            self.checkboxes[i_id] = var

        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(20, 0))
        
        ButtonFactory.create_button(
            parent=btn_frame, text='CANCELAR', command=self.destroy,
            style_key='dialog_cancel_btn', font=button_font
        ).pack(side='left', expand=True, padx=(0, 10))

        ButtonFactory.create_button(
            parent=btn_frame, text='GUARDAR', command=self._on_accept,
            style_key=self._get_button_style_key(), font=button_font
        ).pack(side='left', expand=True)

    def _on_accept(self):
        self.result = [i_id for i_id, var in self.checkboxes.items() if var.get()]
        self.destroy()

def show_multi_select_dialog(parent, items: List[Dict[str, Any]], selected_ids: List[int], titulo="Seleccionar") -> Optional[List[int]]:
    dialog = MultiSelectDialog(parent, items, selected_ids, titulo)
    parent.wait_window(dialog)
    return dialog.result
