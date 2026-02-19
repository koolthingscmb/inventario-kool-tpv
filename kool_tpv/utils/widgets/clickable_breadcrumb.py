"""Widget Breadcrumb clickeable.

Muestra una ruta de navegación donde cada parte es un botón clickeable,
excepto la última (vista actual).
"""
import logging
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL


class ClickableBreadcrumb(ctk.CTkFrame):
    """Breadcrumb con partes clicables.

    Uso:
        breadcrumb = ClickableBreadcrumb(parent)
        breadcrumb.update_parts([
            ('ALMACÉN', callback_almacen),
            ('ALBARANES', callback_albaranes),
            ('DETALLE', None)  # última parte no clickeable
        ])
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLOR_BG_TERMINAL, **kwargs)
        self.parts = []

    def update_parts(self, parts: list):
        """Actualizar breadcrumb con nuevas partes.

        Args:
            parts: Lista de tuplas (texto, callback)
                   Última tupla debe tener callback=None
        """
        try:
            # Limpiar widgets anteriores
            for widget in self.winfo_children():
                widget.destroy()

            self.parts = parts

            # Crear widgets para cada parte
            for i, (text, callback) in enumerate(parts):
                # Separador "/"
                if i > 0:
                    sep = ctk.CTkLabel(
                        self,
                        text='/',
                        text_color=COLOR_MATRIX,
                        font=(FONT_TERMINAL[0], 20, 'bold')
                    )
                    sep.pack(side='left', padx=4)

                # Última parte (no clickeable) o con callback
                is_last = (i == len(parts) - 1)

                if is_last or callback is None:
                    # Label normal (no clickeable)
                    label = ctk.CTkLabel(
                        self,
                        text=text,
                        text_color=COLOR_MATRIX,
                        font=(FONT_TERMINAL[0], 20, 'bold')
                    )
                    label.pack(side='left', padx=2)
                else:
                    # Botón clickeable
                    btn = ctk.CTkButton(
                        self,
                        text=text,
                        text_color=COLOR_MATRIX,
                        fg_color='transparent',
                        hover_color='#333333',
                        font=(FONT_TERMINAL[0], 20, 'bold'),
                        command=callback,
                        width=len(text) * 12,  # Ancho aproximado según texto
                        height=28,
                        corner_radius=4,
                        cursor='hand2' # Cursor manita
                    )

                    # Subrayado en hover
                    def _on_enter(e, button=btn):
                        try:
                            button.configure(font=(FONT_TERMINAL[0], 20, 'bold', 'underline'))
                        except Exception:
                            pass

                    def _on_leave(e, button=btn):
                        try:
                            button.configure(font=(FONT_TERMINAL[0], 20, 'bold'))
                        except Exception:
                            pass

                    btn.bind('<Enter>', _on_enter)
                    btn.bind('<Leave>', _on_leave)

                    btn.pack(side='left', padx=2)

        except Exception:
            logging.exception('Error actualizando ClickableBreadcrumb')

    def get_text(self) -> str:
        """Obtener texto completo del breadcrumb.

        Returns:
            Texto como "ALMACÉN / ALBARANES / DETALLE"
        """
        try:
            return ' / '.join([text for text, _ in self.parts])
        except Exception:
            return ''
