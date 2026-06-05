"""Vista de previsualización antes de exportar - Pantalla 3 (opcional)."""
import logging
from typing import Callable, List, Dict, Any, Optional

import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

logger = logging.getLogger(__name__)


class VistaPreview(ctk.CTkFrame, KeyboardNavigableMixin):
    """Pantalla 3: Preview de la exportación antes de confirmar."""

    def __init__(
        self,
        parent,
        albaranes: List[Dict[str, Any]],
        tipo_exportacion: str,  # 'csv', 'pdf_individual', 'pdf_agrupado', 'imprimir'
        opciones: Dict[str, Any],
        on_exportar_callback: Callable[[], None],
        on_volver_callback: Callable[[], None],
        on_cancelar_callback: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)

        self.albaranes = albaranes
        self.tipo_exportacion = tipo_exportacion
        self.opciones = opciones
        self.on_exportar_callback = on_exportar_callback
        self.on_volver_callback = on_volver_callback
        self.on_cancelar_callback = on_cancelar_callback

        # Config
        self.colors = load_colors('almacen')
        self.fonts = load_font_config()
        self.button_factory = ButtonFactory()

        self._setup_ui()
        self._setup_keyboard_nav()

    def _setup_ui(self):
        """Construir interfaz de preview."""
        self.configure(fg_color=self.colors.get('background', '#2B2B2B'))

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título
        self.grid_rowconfigure(1, weight=0)  # Info tipo exportación
        self.grid_rowconfigure(2, weight=0)  # Opciones
        self.grid_rowconfigure(3, weight=1)  # Lista scrollable
        self.grid_rowconfigure(4, weight=0)  # Totales
        self.grid_rowconfigure(5, weight=0)  # Botones

        # Título
        title_font = self.fonts.get('title', {})
        self.lbl_titulo = ctk.CTkLabel(
            self,
            text="VISTA PREVIA DE EXPORTACIÓN",
            font=(
                title_font.get('family', 'Arial'),
                title_font.get('size', 22),
                title_font.get('weight', 'bold')
            ),
            text_color=self.colors.get('primary', '#1F6AA5')
        )
        self.lbl_titulo.grid(row=0, column=0, pady=(20, 10), padx=20)

        # Tipo de exportación
        tipo_texto = self._get_tipo_exportacion_texto()
        self.lbl_tipo = ctk.CTkLabel(
            self,
            text=f"Tipo: {tipo_texto}",
            font=self.fonts.get('subtitle', {}),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        self.lbl_tipo.grid(row=1, column=0, pady=5, padx=20)

        # Frame opciones seleccionadas
        self.frame_opciones = ctk.CTkFrame(
            self,
            fg_color=self.colors.get('surface', '#333333')
        )
        self.frame_opciones.grid(row=2, column=0, padx=40, pady=10, sticky='ew')

        opciones_texto = self._format_opciones()
        self.lbl_opciones = ctk.CTkLabel(
            self.frame_opciones,
            text=opciones_texto,
            font=self.fonts.get('body', {}),
            text_color=self.colors.get('text_secondary', '#AAAAAA'),
            justify='left'
        )
        self.lbl_opciones.pack(padx=15, pady=10, anchor='w')

        # Lista de albaranes (scrollable)
        self.frame_lista = ctk.CTkScrollableFrame(
            self,
            fg_color=self.colors.get('surface', '#333333'),
            height=200
        )
        self.frame_lista.grid(row=3, column=0, padx=40, pady=10, sticky='nsew')

        self._cargar_lista_albaranes()

        # Frame totales
        self.frame_totales = ctk.CTkFrame(
            self,
            fg_color=self.colors.get('surface', '#333333')
        )
        self.frame_totales.grid(row=4, column=0, padx=40, pady=10, sticky='ew')

        total_albaranes = len(self.albaranes)
        total_euros = sum(a.get('total', 0) for a in self.albaranes)

        self.lbl_totales = ctk.CTkLabel(
            self.frame_totales,
            text=f"Total albaranes: {total_albaranes}  |  Importe total: {total_euros:.2f} €",
            font=(
                self.fonts.get('body', {}).get('family', 'Arial'),
                14,
                'bold'
            ),
            text_color=self.colors.get('primary', '#1F6AA5')
        )
        self.lbl_totales.pack(padx=15, pady=10)

        # Frame botones
        self.frame_botones = ctk.CTkFrame(
            self,
            fg_color='transparent'
        )
        self.frame_botones.grid(row=5, column=0, pady=(10, 20))

        # Botón Volver
        self.btn_volver = self.button_factory.create_button(
            parent=self.frame_botones,
            style_key='secondary',
            text='VOLVER',
            command=self._on_volver
        )
        self.btn_volver.pack(side='left', padx=5)

        # Botón Cancelar
        if self.on_cancelar_callback:
            self.btn_cancelar = self.button_factory.create_button(
                parent=self.frame_botones,
                style_key='secondary',
                text='CANCELAR',
                command=self._on_cancelar
            )
            self.btn_cancelar.pack(side='left', padx=5)

        # Botón Exportar
        texto_exportar = self._get_texto_boton_exportar()
        self.btn_exportar = self.button_factory.create_button(
            parent=self.frame_botones,
            style_key='action',
            text=texto_exportar,
            command=self._on_exportar
        )
        self.btn_exportar.pack(side='left', padx=5)

    def _get_tipo_exportacion_texto(self) -> str:
        """Obtener texto descriptivo del tipo de exportación."""
        tipos = {
            'csv': 'Archivo CSV',
            'pdf_individual': 'PDFs Individuales',
            'pdf_agrupado': 'PDF Agrupado',
            'imprimir': 'Impresión'
        }
        return tipos.get(self.tipo_exportacion, 'Desconocido')

    def _format_opciones(self) -> str:
        """Formatear opciones seleccionadas como texto."""
        partes = []

        if self.opciones.get('incluir_cabecera'):
            partes.append("✓ Incluir cabecera de tienda")
        else:
            partes.append("✗ Sin cabecera de tienda")

        if self.tipo_exportacion == 'pdf_agrupado':
            if self.opciones.get('agrupar_por_proveedor'):
                partes.append("✓ Agrupado por proveedor")
            else:
                partes.append("✗ Sin agrupar")

        return "  |  ".join(partes) if partes else "Sin opciones adicionales"

    def _get_texto_boton_exportar(self) -> str:
        """Obtener texto del botón según tipo de exportación."""
        textos = {
            'csv': 'EXPORTAR CSV',
            'pdf_individual': 'EXPORTAR PDFs',
            'pdf_agrupado': 'EXPORTAR PDF',
            'imprimir': 'IMPRIMIR'
        }
        return textos.get(self.tipo_exportacion, 'EXPORTAR')

    def _cargar_lista_albaranes(self):
        """Cargar lista de albaranes en el frame scrollable."""
        # Headers
        headers = ['Nº Albarán', 'Fecha', 'Proveedor', 'Líneas', 'Total']
        for col, header in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.frame_lista,
                text=header,
                font=(
                    self.fonts.get('body', {}).get('family', 'Arial'),
                    12,
                    'bold'
                ),
                text_color=self.colors.get('primary', '#1F6AA5'),
                width=100
            )
            lbl.grid(row=0, column=col, padx=5, pady=5, sticky='w')

        # Datos
        for row, alb in enumerate(self.albaranes, start=1):
            datos = [
                alb.get('num_albaran', ''),
                alb.get('fecha', ''),
                alb.get('proveedor_nombre', '')[:20],
                str(alb.get('num_lineas', 0)),
                f"{alb.get('total', 0):.2f} €"
            ]

            for col, valor in enumerate(datos):
                lbl = ctk.CTkLabel(
                    self.frame_lista,
                    text=valor,
                    font=self.fonts.get('body', {}),
                    text_color=self.colors.get('text', '#FFFFFF'),
                    width=100
                )
                lbl.grid(row=row, column=col, padx=5, pady=2, sticky='w')

    def _on_volver(self):
        """Volver a la pantalla de selección."""
        if self.on_volver_callback:
            self.on_volver_callback()

    def _on_cancelar(self):
        """Cancelar y cerrar."""
        if self.on_cancelar_callback:
            self.on_cancelar_callback()

    def _on_exportar(self):
        """Confirmar exportación."""
        if self.on_exportar_callback:
            self.on_exportar_callback()

    def _setup_keyboard_nav(self):
        """Configurar navegación por teclado."""
        widgets = [
            self.btn_volver
        ]

        if hasattr(self, 'btn_cancelar'):
            widgets.append(self.btn_cancelar)

        widgets.append(self.btn_exportar)

        for i, widget in enumerate(widgets):
            widget.bind('<Tab>', lambda e, idx=i: self._focus_next(e, widgets, idx))
            widget.bind('<Shift-Tab>', lambda e, idx=i: self._focus_prev(e, widgets, idx))

    def _focus_next(self, event, widgets, current_idx):
        """Mover foco al siguiente widget."""
        next_idx = (current_idx + 1) % len(widgets)
        widgets[next_idx].focus_set()
        return 'break'

    def _focus_prev(self, event, widgets, current_idx):
        """Mover foco al widget anterior."""
        prev_idx = (current_idx - 1) % len(widgets)
        widgets[prev_idx].focus_set()
        return 'break'
