"""Vista de selección de albaranes - Pantalla 2."""
import logging
from typing import Callable, List, Dict, Any, Optional

import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

logger = logging.getLogger(__name__)


class VistaSeleccion(ctk.CTkFrame, KeyboardNavigableMixin):
    """Pantalla 2: Lista de albaranes con selección múltiple y acciones."""

    def __init__(
        self,
        parent,
        albaranes: List[Dict[str, Any]],
        on_volver_callback: Callable[[], None],
        on_exportar_csv_callback: Callable[[List[int], bool], None],
        on_exportar_pdf_callback: Callable[[List[int], bool, bool], None],
        on_imprimir_callback: Callable[[List[int]], None],
        mostrar_tienda_default: bool = False,
        **kwargs
    ):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)

        self.albaranes = albaranes
        self.on_volver_callback = on_volver_callback
        self.on_exportar_csv_callback = on_exportar_csv_callback
        self.on_exportar_pdf_callback = on_exportar_pdf_callback
        self.on_imprimir_callback = on_imprimir_callback
        self.mostrar_tienda_default = mostrar_tienda_default

        # Config
        self.colors = load_colors('almacen')
        self.fonts = load_font_config()
        self.button_factory = ButtonFactory()

        self._setup_ui()
        self._cargar_albaranes()
        self._setup_keyboard_nav()

    def _setup_ui(self):
        """Construir interfaz de selección."""
        self.configure(fg_color=self.colors.get('background', '#2B2B2B'))

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título
        self.grid_rowconfigure(1, weight=0)  # Opciones
        self.grid_rowconfigure(2, weight=1)  # Lista
        self.grid_rowconfigure(3, weight=0)  # Botones selección
        self.grid_rowconfigure(4, weight=0)  # Botones acción

        # Título
        title_font = self.fonts.get('title', {})
        self.lbl_titulo = ctk.CTkLabel(
            self,
            text=f"SELECCIONAR ALBARANES ({len(self.albaranes)} encontrados)",
            font=(
                title_font.get('family', 'Arial'),
                title_font.get('size', 20),
                title_font.get('weight', 'bold')
            ),
            text_color=self.colors.get('primary', '#1F6AA5')
        )
        self.lbl_titulo.grid(row=0, column=0, pady=(15, 10), padx=20)

        # Frame opciones (checkboxes)
        self.frame_opciones = ctk.CTkFrame(
            self,
            fg_color=self.colors.get('surface', '#333333')
        )
        self.frame_opciones.grid(row=1, column=0, padx=20, pady=5, sticky='ew')

        _body = self.fonts.get('default', {})
        _body_font = ctk.CTkFont(family=_body.get('family', 'Arial'), size=_body.get('size', 13))

        # Checkbox "Incluir cabecera de tienda"
        self.var_cabecera = ctk.BooleanVar(value=self.mostrar_tienda_default)
        self.chk_cabecera = ctk.CTkCheckBox(
            self.frame_opciones,
            text="Incluir cabecera de tienda",
            variable=self.var_cabecera,
            font=_body_font,
            text_color=self.colors.get('text', '#FFFFFF'),
            fg_color=self.colors.get('primary', '#1F6AA5'),
            hover_color=self.colors.get('secondary', '#4A90A4')
        )
        self.chk_cabecera.pack(side='left', padx=15, pady=10)

        # Checkbox "Agrupar por proveedor"
        self.var_agrupar = ctk.BooleanVar(value=False)
        self.chk_agrupar = ctk.CTkCheckBox(
            self.frame_opciones,
            text="AGRUPAR ALBARANES",
            variable=self.var_agrupar,
            font=_body_font,
            text_color=self.colors.get('text', '#FFFFFF'),
            fg_color=self.colors.get('primary', '#1F6AA5'),
            hover_color=self.colors.get('secondary', '#4A90A4')
        )
        self.chk_agrupar.pack(side='left', padx=15, pady=10)

        # Lista de albaranes con VirtualNavList (Multi-select)
        self.columns_spec = [
            ('id', 50, 'ID'),
            ('num_albaran', 150, 'Nº Albarán'),
            ('fecha', 120, 'Fecha'),
            ('proveedor_nombre', 250, 'Proveedor'),
            ('total', 120, 'Total')
        ]
        
        self.lista_albaranes = VirtualNavList(
            self,
            columns=self.columns_spec,
            module_name=self.colors.get('module_name', 'almacen'),
            keyboard_manager=getattr(self.winfo_toplevel(), 'keyboard_manager', None),
            multi_select=True,
            on_selection_change=self._on_seleccion_cambio
        )
        self.lista_albaranes.grid(row=2, column=0, padx=20, pady=10, sticky='nsew')

        # Frame botones de selección
        self.frame_seleccion = ctk.CTkFrame(
            self,
            fg_color='transparent'
        )
        self.frame_seleccion.grid(row=3, column=0, pady=5)

        # Botón Seleccionar Todos
        self.btn_todos = self.button_factory.create_button(
            parent=self.frame_seleccion,
            style_key='action_secondary',
            text='SEL. TODOS',
            command=self._on_seleccionar_todos
        )
        self.btn_todos.pack(side='left', padx=5)

        # Botón Seleccionar Ninguno
        self.btn_ninguno = self.button_factory.create_button(
            parent=self.frame_seleccion,
            style_key='action_secondary',
            text='SEL. NINGUNO',
            command=self._on_seleccionar_ninguno
        )
        self.btn_ninguno.pack(side='left', padx=5)

        # Frame botones de acción
        self.frame_acciones = ctk.CTkFrame(
            self,
            fg_color='transparent'
        )
        self.frame_acciones.grid(row=4, column=0, pady=(10, 20))

        # Botón Volver
        self.btn_volver = self.button_factory.create_button(
            parent=self.frame_acciones,
            style_key='action_secondary',
            text='VOLVER',
            command=self._on_volver
        )
        self.btn_volver.pack(side='left', padx=5)

        # Botón Exportar CSV
        self.btn_csv = self.button_factory.create_button(
            parent=self.frame_acciones,
            style_key='action_primary',
            text='EXPORTAR CSV',
            command=self._on_exportar_csv
        )
        self.btn_csv.pack(side='left', padx=5)

        # Botón Exportar PDF
        self.btn_pdf = self.button_factory.create_button(
            parent=self.frame_acciones,
            style_key='action_primary',
            text='EXPORTAR PDF',
            command=self._on_exportar_pdf
        )
        self.btn_pdf.pack(side='left', padx=5)

        # Botón Imprimir
        self.btn_imprimir = self.button_factory.create_button(
            parent=self.frame_acciones,
            style_key='action_primary',
            text='IMPRIMIR',
            command=self._on_imprimir
        )
        self.btn_imprimir.pack(side='left', padx=5)

    def _cargar_albaranes(self):
        """Cargar albaranes en la lista."""
        try:
            filas = []
            for alb in self.albaranes:
                filas.append({
                    'id': alb.get('id'),
                    'num_albaran': str(alb.get('num_albaran', '')),
                    'fecha': alb.get('fecha', ''),
                    'proveedor_nombre': alb.get('proveedor_nombre', ''),
                    'num_lineas': str(alb.get('num_lineas', 0)),
                    'total': f"{alb.get('total', 0):.2f} €"
                })
            self.lista_albaranes.set_items(filas)
            logger.info(f"Cargados {len(filas)} albaranes en la lista virtual")
        except Exception:
            logger.exception("Error cargando albaranes en la lista virtual")

    def _on_seleccion_cambio(self, selected_ids):
        """Callback cuando cambia la selección."""
        logger.debug(f"Selección cambiada: {len(selected_ids)} albaranes")

    def _on_seleccionar_todos(self):
        """Seleccionar todos los albaranes."""
        self.lista_albaranes.select_all()
        logger.info("Seleccionados todos los albaranes")

    def _on_seleccionar_ninguno(self):
        """Deseleccionar todos los albaranes."""
        self.lista_albaranes.deselect_all()
        logger.info("Deseleccionados todos los albaranes")

    def _get_seleccionados(self) -> List[int]:
        """Obtener IDs de albaranes seleccionados."""
        items = self.lista_albaranes.get_selected_items()
        return [item['id'] for item in items if item.get('id')]

    def _on_volver(self):
        """Volver a la pantalla de filtros."""
        if self.on_volver_callback:
            self.on_volver_callback()

    def _on_exportar_csv(self):
        """Exportar seleccionados a CSV."""
        seleccionados = self._get_seleccionados()
        if not seleccionados:
            logger.warning("No hay albaranes seleccionados para CSV")
            return

        incluir_cabecera = self.var_cabecera.get()
        agrupar = self.var_agrupar.get()
        logger.info(f"Exportando {len(seleccionados)} albaranes a CSV (cabecera={incluir_cabecera}, agrupar={agrupar})")

        if self.on_exportar_csv_callback:
            self.on_exportar_csv_callback(seleccionados, incluir_cabecera, agrupar)

    def _on_exportar_pdf(self):
        """Exportar seleccionados a PDF."""
        seleccionados = self._get_seleccionados()
        if not seleccionados:
            logger.warning("No hay albaranes seleccionados para PDF")
            return

        incluir_cabecera = self.var_cabecera.get()
        agrupar = self.var_agrupar.get()
        logger.info(f"Exportando {len(seleccionados)} albaranes a PDF (cabecera={incluir_cabecera}, agrupar={agrupar})")

        if self.on_exportar_pdf_callback:
            self.on_exportar_pdf_callback(seleccionados, incluir_cabecera, agrupar)

    def _on_imprimir(self):
        """Imprimir albaranes seleccionados."""
        seleccionados = self._get_seleccionados()
        if not seleccionados:
            logger.warning("No hay albaranes seleccionados para imprimir")
            return

        logger.info(f"Imprimiendo {len(seleccionados)} albaranes")

        if self.on_imprimir_callback:
            self.on_imprimir_callback(seleccionados)

    def _setup_keyboard_nav(self):
        """Configurar navegación por teclado."""
        # Widgets navegables
        widgets = [
            self.chk_cabecera,
            self.chk_agrupar,
            self.btn_todos,
            self.btn_ninguno,
            self.btn_volver,
            self.btn_csv,
            self.btn_pdf,
            self.btn_imprimir
        ]

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
