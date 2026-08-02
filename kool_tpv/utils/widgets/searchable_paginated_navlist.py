"""Searchable NavList widget con VirtualNavList.

Proporciona una entrada de búsqueda arriba y un VirtualNavList
debajo. La búsqueda se dispara al llamar a search() o set_search_text().
No dispara en tiempo real — evita queries continuas a la BD.
"""
from typing import List, Callable, Optional, Any
import logging
import tkinter as tk
import customtkinter as ctk

from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

logger = logging.getLogger(__name__)


class SearchablePaginatedNavList(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        columns,
        search_function: Callable[[str], List[Any]],
        map_function: Callable[[Any], dict],
        module_name: Optional[str] = None,
        page_limit: int = 50,
        on_double_click: Optional[Callable[[dict], None]] = None,
        keyboard_manager=None,
        layout_config: Optional[dict] = None,
        multi_select: bool = False,
        on_selection_change: Optional[Callable[[List[int]], None]] = None,
        **kwargs,
    ):
        self.layout_config = layout_config if isinstance(layout_config, dict) else None
        super().__init__(parent, **kwargs)

        self.search_function = search_function
        self.map_function = map_function
        self.module_name = module_name
        self.on_double_click = on_double_click
        self.keyboard_manager = keyboard_manager
        self.termino = ""

        self.nav_list = VirtualNavList(
            parent=self,
            columns=columns,
            on_double_click=self.on_double_click,
            module_name=self.module_name or '',
            keyboard_manager=self.keyboard_manager,
            layout_config=self.layout_config,
            multi_select=multi_select,
            on_selection_change=on_selection_change
        )
        self.nav_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Carga inicial: mostrar todos los registros
        try:
            self._on_search('')
        except Exception:
            logger.exception('Error en carga inicial SearchablePaginatedNavList')

    def _on_search(self, texto: str = '', grab_focus: bool = True):
        """Ejecutar búsqueda y cargar resultados en VirtualNavList."""
        try:
            self.termino = texto.strip()
            try:
                resultados = self.search_function(self.termino)
            except Exception:
                logger.exception('Error ejecutando search_function')
                resultados = []

            mapped = []
            for itm in (resultados or []):
                try:
                    mapped.append(self.map_function(itm))
                except Exception:
                    logger.exception('Error mapeando item')

            self.nav_list.set_items(mapped, grab_focus=grab_focus)

        except Exception:
            logger.exception('Error en _on_search')

    def search(self, texto: str = '', grab_focus: bool = True):
        """API pública: disparar búsqueda con el texto dado."""
        self._on_search(texto, grab_focus=grab_focus)

    def get_selected_item(self) -> Optional[dict]:
        """Obtener el item actualmente seleccionado en la lista."""
        if hasattr(self, 'nav_list'):
            return self.nav_list.get_selected_data()
        return None

    def get_selected_items(self) -> List[dict]:
        """Obtener todos los items seleccionados en modo multiselección."""
        if hasattr(self, 'nav_list'):
            return self.nav_list.get_selected_items()
        return []

    def destroy(self):
        """Limpiar referencias al destruir."""
        try:
            self.search_function = None
            self.map_function = None
            self.on_double_click = None
            if hasattr(self, 'nav_list'):
                self.nav_list.destroy()
        except: pass
        finally:
            super().destroy()
