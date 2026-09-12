import customtkinter as ctk
import logging
import tkinter as tk
from typing import List, Dict, Optional, Any

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget

logger = logging.getLogger(__name__)

class SourceSearchDialog(BaseDialog):
    """
    Diálogo genérico para seleccionar un resultado de búsqueda entre varias fuentes externas.
    Agnóstico al tipo de producto (Manga, Libros, Juegos, etc.)
    """
    
    def __init__(self, parent, results: List[Dict[str, Any]], titulo="Resultados de Búsqueda"):
        self.results = results
        self.result = None
        # Almacenará un diccionario con {'id': ..., 'source_id': ...}
        self.selected_index = tk.IntVar(value=-1) 
        
        super().__init__(parent, tipo='info', titulo=titulo)
        
        self._crear_contenido()
        
        # Geometría ampliada para mejor lectura
        self.geometry("900x700")
        self._center_window(parent, 900, 700)

    def _crear_contenido(self):
        """Construye la interfaz de selección de resultados."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        title_font = self._get_font('title')
        message_font = self._get_font('message')
        button_font = self._get_font('button')
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Título y subtítulo
        ctk.CTkLabel(
            main_frame,
            text="RESULTADOS ENCONTRADOS",
            font=title_font,
            text_color=tipo_config.get('title_text', '#FFFFFF')
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            main_frame,
            text=f"Se han encontrado {len(self.results)} coincidencias en las fuentes activas:",
            font=message_font,
            text_color=tipo_config.get('message_text', '#AAAAAA')
        ).pack(pady=(0, 15))

        # Contenedor scrollable ampliado
        scroll_frame = ctk.CTkScrollableFrame(
            main_frame, 
            fg_color='transparent',
            height=450,
            scrollbar_button_color=tipo_config.get('primary', '#00A4DF')
        )
        scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)

        if not self.results:
            ctk.CTkLabel(
                scroll_frame,
                text="No se encontraron resultados.",
                font=message_font,
                text_color="#FF5555"
            ).pack(pady=20)
        else:
            for i, res in enumerate(self.results):
                self._render_result_item(scroll_frame, i, res, message_font)

        # Botones de acción
        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(20, 0))
        
        self.btn_cancel = ButtonFactory.create_button(
            parent=btn_frame,
            text='CANCELAR',
            command=self._on_cancel,
            style_key='dialog_cancel_btn',
            font=button_font
        )
        self.btn_cancel.pack(side='left', expand=True, padx=(0, 10))

        self.btn_accept = ButtonFactory.create_button(
            parent=btn_frame,
            text='SELECCIONAR',
            command=self._on_accept,
            style_key=self._get_button_style_key(),
            font=button_font
        )
        self.btn_accept.pack(side='left', expand=True)
        self.btn_accept.focus_set()

    def _render_result_item(self, parent, index, data, font):
        """Renderiza una fila de resultado con RadioButton."""
        item_frame = ctk.CTkFrame(parent, fg_color='transparent')
        item_frame.pack(fill='x', pady=5, padx=5)
        
        # Extraer el título de forma segura (puede ser string o dict)
        title_raw = data.get('title') or data.get('name') or "Sin título"
        if isinstance(title_raw, dict):
            title = title_raw.get('romaji') or title_raw.get('english') or list(title_raw.values())[0]
        else:
            title = title_raw

        subtitle = data.get('subtitle') or data.get('description_short') or ""
        source_name = data.get('_source_name', 'Fuente externa')
        
        # Texto formateado limpio y aprovechando el ancho
        display_text = f"[{source_name.upper()}] {title}"
        if subtitle:
            # Limpiar HTML si lo hubiera en el subtítulo
            import re
            clean_subtitle = re.sub('<[^<]+?>', '', str(subtitle))
            display_text += f"\n   {clean_subtitle}" # Quitamos el límite de [:100]

        rb = ctk.CTkRadioButton(
            item_frame,
            text=display_text,
            variable=self.selected_index,
            value=index,
            font=font,
            radiobutton_width=20,
            radiobutton_height=20,
            border_width_unchecked=2,
            border_width_checked=5,
            hover_color=self.dialogs_colors.get('info', {}).get('primary', '#00A4DF')
        )
        rb.pack(side='left', fill='x', expand=True, anchor="w")

    def _on_accept(self):
        idx = self.selected_index.get()
        if idx == -1:
            ToastWidget.show(self, "Por favor, selecciona un resultado", tipo='warning')
            return
            
        selected_data = self.results[idx]
        # Devolvemos el diccionario con la info mínima necesaria para el orquestador
        self.result = {
            'id': selected_data.get('id'),
            'source_id': selected_data.get('_source_id'),
            'title': selected_data.get('title') or selected_data.get('name')
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

def show_source_search_dialog(parent, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Muestra el diálogo de búsqueda y retorna el resultado seleccionado o None."""
    dialog = SourceSearchDialog(parent, results)
    parent.wait_window(dialog)
    return dialog.result
