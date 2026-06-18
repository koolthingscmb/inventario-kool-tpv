"""
ColorPickerDialog - Selector de colores "Kool".
Ofrece una paleta de colores predefinidos y la opción de elegir uno personalizado.
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser
import logging

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory

logger = logging.getLogger(__name__)

# Paleta de colores "Pro" para TPV (colores vivos pero elegantes sobre fondo oscuro)
PRESET_COLORS = [
    "#FF5252", "#FF4081", "#E040FB", "#7C4DFF", 
    "#536DFE", "#448AFF", "#40C4FF", "#18FFFF",
    "#64FFDA", "#69F0AE", "#B2FF59", "#EEFF41",
    "#FFFF00", "#FFD740", "#FFAB40", "#FF6E40",
    "#FFFFFF", "#BDBDBD", "#757575", "#424242"
]

class ColorPickerDialog(BaseDialog):
    def __init__(self, parent, callback=None, initial_color="#333333"):
        super().__init__(parent, titulo="SELECCIONAR COLOR", callback=callback)
        self.result = initial_color
        self._crear_contenido()

    def _crear_contenido(self):
        from .content_container import create_dialog_content_container
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        content_parent = create_dialog_content_container(main_frame, self.geometry_cfg)

        # 1. Grid de colores predefinidos
        grid_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        grid_frame.pack(pady=10)

        cols = 5
        for i, color in enumerate(PRESET_COLORS):
            r = i // cols
            c = i % cols
            btn = ctk.CTkButton(
                grid_frame,
                text="",
                width=40,
                height=40,
                fg_color=color,
                hover_color=color, # Sin hover para que no cambie el color al pasar por encima
                corner_radius=4,
                border_width=2,
                border_color="#000000",
                command=lambda x=color: self._select_preset(x)
            )
            btn.grid(row=r, column=c, padx=5, pady=5)

        # 2. Botón Personalizado
        custom_btn = ButtonFactory.create_button(
            parent=content_parent,
            text="COLOR PERSONALIZADO",
            command=self._open_system_picker,
            style_key="action_secondary"
        )
        custom_btn.pack(pady=20, fill='x', padx=20)

        # 3. Footer (Botón Cerrar)
        footer = ctk.CTkFrame(content_parent, fg_color='transparent')
        footer.pack(side='bottom', pady=10)
        
        ButtonFactory.create_button(
            parent=footer,
            text="CANCELAR",
            command=self.destroy,
            style_key="dialog_cancel_btn"
        ).pack()

    def _select_preset(self, color):
        self.result = color
        if self.callback:
            self.callback(color)
        self.destroy()

    def _open_system_picker(self):
        try:
            # Ocultar temporalmente el grab para que el selector de sistema funcione
            self.grab_release()
            color = colorchooser.askcolor(initialcolor=self.result, title="Elige un color")[1]
            if color:
                self.result = color
                if self.callback:
                    self.callback(color)
                self.destroy()
            else:
                # Si cancela el picker de sistema, re-activar grab
                self.grab_set()
        except Exception:
            logger.exception("Error abriendo selector de color de sistema")
