"""Widget Breadcrumb clickeable.

Muestra una ruta de navegación donde cada parte es un botón clickeable,
excepto la última (vista actual).
"""
import logging
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import get_font


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

    def __init__(self, parent, module_name=None, **kwargs):
        """Constructor.

        Args:
            parent: widget padre.
            module_name: nombre del módulo para cargar paleta (ej: 'clientes').
        """
        super().__init__(parent, fg_color=COLOR_BG_TERMINAL, **kwargs)
        self.parts = []
        # Cargar paleta de colores (fallback a COLOR_MATRIX si no existe)
        try:
            self.module_name = module_name
            self.colors = load_colors(module_name) if module_name else {}
        except Exception:
            logging.exception('Error cargando paleta de colores para ClickableBreadcrumb')
            self.colors = {}
        self.text_color = self.colors.get('text', COLOR_MATRIX)

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
                        text_color=self.text_color,
                        font=get_font('breadcrumb', module=self.module_name)
                    )
                    sep.pack(side='left', padx=4)

                # Última parte (no clickeable) o con callback
                is_last = (i == len(parts) - 1)

                if is_last or callback is None:
                    # Label normal (no clickeable)
                    label = ctk.CTkLabel(
                        self,
                        text=text,
                        text_color=self.text_color,
                        font=get_font('breadcrumb', module=self.module_name)
                    )
                    label.pack(side='left', padx=2)
                else:
                    # Botón clickeable
                    btn = ctk.CTkButton(
                        self,
                        text=text,
                        text_color=self.text_color,
                        fg_color='transparent',
                        hover_color='#333333',
                        font=get_font('breadcrumb', module=self.module_name),
                        command=callback,
                        width=len(text) * 12,  # Ancho aproximado según texto
                        height=28,
                        corner_radius=4,
                        cursor='hand2' # Cursor manita
                    )

                    # Subrayado en hover
                    def _on_enter(e, button=btn):
                        try:
                            f = get_font('breadcrumb', module=self.module_name)
                            try:
                                button.configure(font=(f[0], f[1], f[2], 'underline'))
                            except Exception:
                                button.configure(font=f)
                        except Exception:
                            pass

                    def _on_leave(e, button=btn):
                        try:
                            button.configure(font=get_font('breadcrumb', module=self.module_name))
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
