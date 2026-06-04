"""NavListMultiSelect - Lista con selección múltiple via checkboxes."""

import logging
from typing import List, Optional, Callable, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.font_loader import load_font_config

logger = logging.getLogger(__name__)


class NavListMultiSelect(ctk.CTkScrollableFrame):
    """Lista navegable con checkboxes para selección múltiple."""

    def __init__(
        self,
        parent,
        columns: List[str],
        column_widths: List[int],
        header_texts: List[str],
        on_selection_change: Optional[Callable[[List[int]], None]] = None,
        row_height: int = 30,
        **kwargs
    ):
        """Inicializar lista multi-select.

        Args:
            parent: Widget padre
            columns: Nombres de columnas (keys del diccionario de datos)
            column_widths: Anchos de columnas en pixels
            header_texts: Textos de cabecera
            on_selection_change: Callback cuando cambia selección (recibe lista de índices)
            row_height: Altura de filas
        """
        super().__init__(parent, **kwargs)

        # Configuración
        self.columns = columns
        self.column_widths = column_widths
        self.header_texts = header_texts
        self.on_selection_change = on_selection_change
        self.row_height = row_height

        # Estado
        self.rows_data: List[Dict[str, Any]] = []
        self.row_widgets: List[ctk.CTkFrame] = []
        self.checkboxes: List[ctk.CTkCheckBox] = []
        self.selected_indices: set = set()
        self.master_checkbox: Optional[ctk.CTkCheckBox] = None

        # Fuentes desde config
        self.font_config = load_font_config()
        self.header_font = ctk.CTkFont(
            family=self.font_config.get('list_header', {}).get('family', 'Inter'),
            size=self.font_config.get('list_header', {}).get('size', 12),
            weight=self.font_config.get('list_header', {}).get('weight', 'bold')
        )
        self.cell_font = ctk.CTkFont(
            family=self.font_config.get('list_cell', {}).get('family', 'Inter'),
            size=self.font_config.get('list_cell', {}).get('size', 12),
            weight=self.font_config.get('list_cell', {}).get('weight', 'normal')
        )
        self.checkbox_font = ctk.CTkFont(
            family=self.font_config.get('default', {}).get('family', 'Inter'),
            size=self.font_config.get('default', {}).get('size', 11)
        )

        # Setup UI
        self._setup_header()
        self._setup_content_frame()

    def _setup_header(self):
        """Crear cabecera con checkbox maestro."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=self.row_height)
        self.header_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.header_frame.pack_propagate(False)

        # Checkbox maestro (primera columna)
        checkbox_width = 30
        self.master_checkbox = ctk.CTkCheckBox(
            self.header_frame,
            text="",
            width=checkbox_width,
            height=20,
            checkbox_width=18,
            checkbox_height=18,
            command=self._on_master_checkbox_toggle
        )
        self.master_checkbox.pack(side="left", padx=(5, 2))

        # Cabeceras de columnas
        for i, (text, width) in enumerate(zip(self.header_texts, self.column_widths)):
            # Ajustar primera columna por el checkbox
            actual_width = width - checkbox_width if i == 0 else width

            lbl = ctk.CTkLabel(
                self.header_frame,
                text=text,
                font=self.header_font,
                width=actual_width,
                anchor="w"
            )
            lbl.pack(side="left", padx=(2, 5))

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="gray50").pack(fill="x", padx=5, pady=2)

    def _setup_content_frame(self):
        """Crear contenedor para filas."""
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _on_master_checkbox_toggle(self):
        """Manejar toggle del checkbox maestro."""
        if self.master_checkbox.get():
            self.select_all()
        else:
            self.deselect_all()

    def _on_row_checkbox_toggle(self, index: int):
        """Manejar toggle de checkbox de fila."""
        checkbox = self.checkboxes[index]
        if checkbox.get():
            self.selected_indices.add(index)
            self._highlight_row(index, True)
        else:
            self.selected_indices.discard(index)
            self._highlight_row(index, False)

        # Actualizar master checkbox
        self._update_master_checkbox()

        # Notificar cambio
        if self.on_selection_change:
            try:
                self.on_selection_change(self.get_selected_indices())
            except Exception:
                logger.exception("Error en callback on_selection_change")

    def _highlight_row(self, index: int, selected: bool):
        """Resaltar/desresaltar fila."""
        if 0 <= index < len(self.row_widgets):
            row_frame = self.row_widgets[index]
            if selected:
                row_frame.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                row_frame.configure(fg_color="transparent")

    def _update_master_checkbox(self):
        """Actualizar estado del checkbox maestro."""
        if not self.master_checkbox:
            return

        if len(self.selected_indices) == 0:
            self.master_checkbox.deselect()
        elif len(self.selected_indices) == len(self.rows_data):
            self.master_checkbox.select()
        else:
            # Estado intermedio - deseleccionar visualmente
            self.master_checkbox.deselect()

    def clear(self):
        """Limpiar todas las filas."""
        for widget in self.row_widgets:
            widget.destroy()

        self.rows_data = []
        self.row_widgets = []
        self.checkboxes = []
        self.selected_indices = set()

        if self.master_checkbox:
            self.master_checkbox.deselect()

    def add_row(self, data: Dict[str, Any]) -> int:
        """Añadir fila a la lista.

        Args:
            data: Diccionario con datos (keys deben coincidir con columns)

        Returns:
            Índice de la fila añadida
        """
        index = len(self.rows_data)

        # Crear frame de fila
        row_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color="transparent",
            height=self.row_height
        )
        row_frame.pack(fill="x", pady=1)
        row_frame.pack_propagate(False)

        # Checkbox
        checkbox = ctk.CTkCheckBox(
            row_frame,
            text="",
            width=30,
            height=20,
            checkbox_width=18,
            checkbox_height=18,
            font=self.checkbox_font,
            command=lambda idx=index: self._on_row_checkbox_toggle(idx)
        )
        checkbox.pack(side="left", padx=(5, 2))
        self.checkboxes.append(checkbox)

        # Celdas de datos
        for col_name, width in zip(self.columns, self.column_widths):
            # Ajustar primera columna por checkbox
            actual_width = width - 30 if col_name == self.columns[0] else width

            value = data.get(col_name, "")
            cell = ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=self.cell_font,
                width=actual_width,
                anchor="w"
            )
            cell.pack(side="left", padx=(2, 5))

        # Guardar datos
        self.rows_data.append(data)
        self.row_widgets.append(row_frame)

        return index

    def set_data(self, data_list: List[Dict[str, Any]]):
        """Cargar lista completa de datos.

        Args:
            data_list: Lista de diccionarios con datos
        """
        self.clear()
        for data in data_list:
            self.add_row(data)

    def get_selected_indices(self) -> List[int]:
        """Obtener índices de filas seleccionadas."""
        return sorted(list(self.selected_indices))

    def get_selected_items(self) -> List[Dict[str, Any]]:
        """Obtener datos de filas seleccionadas."""
        return [self.rows_data[i] for i in self.get_selected_indices()]

    def select_all(self):
        """Seleccionar todas las filas."""
        for i, checkbox in enumerate(self.checkboxes):
            checkbox.select()
            self.selected_indices.add(i)
            self._highlight_row(i, True)

        if self.master_checkbox:
            self.master_checkbox.select()

        if self.on_selection_change:
            try:
                self.on_selection_change(self.get_selected_indices())
            except Exception:
                logger.exception("Error en callback on_selection_change")

    def deselect_all(self):
        """Deseleccionar todas las filas."""
        for i, checkbox in enumerate(self.checkboxes):
            checkbox.deselect()
            self.selected_indices.discard(i)
            self._highlight_row(i, False)

        if self.master_checkbox:
            self.master_checkbox.deselect()

        if self.on_selection_change:
            try:
                self.on_selection_change([])
            except Exception:
                logger.exception("Error en callback on_selection_change")

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Obtener todos los datos."""
        return self.rows_data.copy()

    def get_item_at(self, index: int) -> Optional[Dict[str, Any]]:
        """Obtener datos de fila específica."""
        if 0 <= index < len(self.rows_data):
            return self.rows_data[index]
        return None

    def is_selected(self, index: int) -> bool:
        """Verificar si fila está seleccionada."""
        return index in self.selected_indices

    def select_item(self, index: int):
        """Seleccionar fila específica."""
        if 0 <= index < len(self.checkboxes):
            self.checkboxes[index].select()
            self.selected_indices.add(index)
            self._highlight_row(index, True)
            self._update_master_checkbox()

    def deselect_item(self, index: int):
        """Deseleccionar fila específica."""
        if 0 <= index < len(self.checkboxes):
            self.checkboxes[index].deselect()
            self.selected_indices.discard(index)
            self._highlight_row(index, False)
            self._update_master_checkbox()
