import customtkinter as ctk
from typing import List, Optional, Callable
import logging
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.config_loader import load_colors


class TagSelector(ctk.CTkFrame):
    """Selector múltiple con búsqueda dinámica y visualización de tags.

    Uso:
        tag_selector = TagSelector(parent, module_name='informes')
        tag_selector.set_search_function(mi_funcion_busqueda)

        ids = tag_selector.get_selected_ids()
    """

    def __init__(
        self,
        master,
        module_name: Optional[str] = None,
        placeholder: str = 'Buscar...',
        on_change: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        # Cargar colores del módulo
        try:
            self.colors = load_colors(module_name) if module_name else {}
        except Exception:
            self.colors = {}

        # Estado interno: {id: nombre}
        self._selected_items = {}

        # Callback opcional llamado cuando cambia la selección
        self.on_change_callback = on_change

        # SearchableCombo para buscar
        self.search_combo = SearchableCombo(
            self,
            search_function=None,
            placeholder=placeholder,
            module_name=module_name,
            width=300,
            command=self._on_item_selected
        )
        self.search_combo.pack(fill='x', pady=(0, 8))

        # Frame para tags visuales (altura fija)
        self.tags_frame = ctk.CTkFrame(self, fg_color='transparent', height=50)
        self.tags_frame.pack(fill='x', expand=False)
        try:
            # Evitar que el frame cambie de tamaño según su contenido
            self.tags_frame.pack_propagate(False)
        except Exception:
            pass

    def set_search_function(self, search_function: Optional[Callable]):
        """Asignar función de búsqueda dinámica.

        La función debe devolver:
        [{"id": int, "nombre_display": str}, ...]
        """
        try:
            self.search_combo.search_function = search_function
        except Exception:
            logging.exception('Error asignando search_function en TagSelector')

    def get_selected_ids(self) -> List[int]:
        """Obtener IDs de elementos seleccionados."""
        try:
            return list(self._selected_items.keys())
        except Exception:
            return []

    def clear(self):
        """Limpiar todas las selecciones."""
        try:
            self._selected_items.clear()
            self._render_tags()
            self.search_combo.clear()
        except Exception:
            logging.exception('Error limpiando TagSelector')

    def add_tag(self, tag_id: int, tag_name: str):
        """Añadir tag manualmente."""
        try:
            if tag_id not in self._selected_items:
                self._selected_items[tag_id] = tag_name
                self._render_tags()
                # Notificar cambio
                if self.on_change_callback:
                    try:
                        self.on_change_callback()
                    except Exception:
                        logging.exception('Error ejecutando on_change callback')
        except Exception:
            logging.exception('Error añadiendo tag')

    def remove_tag(self, tag_id: int):
        """Eliminar tag."""
        try:
            if tag_id in self._selected_items:
                del self._selected_items[tag_id]
                self._render_tags()
                # Notificar cambio
                if self.on_change_callback:
                    try:
                        self.on_change_callback()
                    except Exception:
                        logging.exception('Error ejecutando on_change callback')
        except Exception:
            logging.exception('Error eliminando tag')

    def _on_item_selected(self, value: str):
        """Callback cuando se selecciona item del SearchableCombo."""
        try:
            # Debug logging removed to reduce log noise
            # Obtener datos completos del item
            item_data = self.search_combo.get_producto_data()

            if item_data:
                item_id = item_data.get('id')
                nombre = item_data.get('nombre_display')

                if item_id and nombre:
                    self.add_tag(item_id, nombre)
                    self.search_combo.clear()
                    # Restaurar foco al entry del SearchableCombo
                    try:
                        self.search_combo.entry.focus_set()
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error procesando selección en TagSelector')

    def _render_tags(self):
        """Renderizar tags visuales."""
        try:
            # Limpiar tags anteriores
            for widget in self.tags_frame.winfo_children():
                widget.destroy()

            # Crear tag por cada elemento seleccionado
            for tag_id, tag_name in self._selected_items.items():
                self._create_tag(tag_id, tag_name)
        except Exception:
            logging.exception('Error renderizando tags')

    def _create_tag(self, tag_id: int, tag_name: str):
        """Crear widget visual de tag."""
        try:
            tag_frame = ctk.CTkFrame(
                self.tags_frame,
                fg_color=self.colors.get('primary', '#00A4DF'),
                corner_radius=6
            )
            tag_frame.pack(side='left', padx=4, pady=2)

            # Label con nombre
            label = ctk.CTkLabel(
                tag_frame,
                text=tag_name,
                text_color='#000000',
                font=('Roboto', 12)
            )
            label.pack(side='left', padx=(8, 4), pady=4)

            # Botón X para eliminar
            btn_remove = ctk.CTkButton(
                tag_frame,
                text='×',
                width=20,
                height=20,
                fg_color='transparent',
                text_color='#000000',
                hover_color='#ff0000',
                font=('Roboto', 16, 'bold'),
                command=lambda: self.remove_tag(tag_id)
            )
            btn_remove.pack(side='left', padx=(0, 4), pady=4)
        except Exception:
            logging.exception('Error creando tag visual')
