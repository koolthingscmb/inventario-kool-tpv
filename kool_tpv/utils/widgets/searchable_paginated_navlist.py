"""Searchable + Paginated NavList widget.

Proporciona una entrada de búsqueda arriba y un `NavList` paginado
debajo. No toca servicios ni NavList internamente; espera una
`search_function(texto) -> List[Any]` y un `map_function(item) -> dict`
compatible con `NavList`.
"""
from typing import List, Callable, Optional, Any
import logging
import tkinter as tk
import customtkinter as ctk

from kool_tpv.utils.widgets.nav_list import NavList

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
        **kwargs,
    ):
        # Preserve provided layout_config before any widget initialization
        self.layout_config = layout_config if isinstance(layout_config, dict) else None

        super().__init__(parent, **kwargs)

        self.search_function = search_function
        self.map_function = map_function
        self.module_name = module_name
        self.page_limit = int(page_limit or 50)
        self.on_double_click = on_double_click
        self.keyboard_manager = keyboard_manager

        # State
        self._all_items: List[Any] = []
        self._visible_offset = 0
        self.loading = False
        self.termino = ""

        # Search state (StringVar kept as attribute; Entry creation moved to parent views)
        self._search_var = tk.StringVar()

        # NavList (pass layout_config so NavList can read wraplength before adding rows)
        self.nav_list = NavList(
            parent=self,
            columns=columns,
            on_double_click=self.on_double_click,
            module_name=self.module_name or '',
            keyboard_manager=self.keyboard_manager,
            layout_config=self.layout_config,
        )
        self.nav_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Canvas reference used for scroll detection (evaluated in periodic check)
        # Initialize to the NavList internal canvas if available, otherwise
        # use a safe dummy object with a winfo_exists method to avoid
        # AttributeError during early CustomTkinter drawing.
        try:
            potential = getattr(self.nav_list, '_parent_canvas', None) or getattr(self.nav_list, '_canvas', None)
            if potential is not None:
                self._canvas = potential
            else:
                class _DummyCanvas:
                    def winfo_exists(self):
                        return False

                self._canvas = _DummyCanvas()
        except Exception:
            class _DummyCanvas:
                def winfo_exists(self):
                    return False

            self._canvas = _DummyCanvas()

        # Start periodic check for scroll-bottom
        try:
            self.after(200, self._periodic_check)
        except Exception:
            pass

        # Carga inicial automática
        try:
            self._on_search()
        except Exception:
            pass

    def _on_search(self):
        try:
            texto = (self._search_var.get() or '').strip()
            self.termino = texto

            # Obtener lista completa del servicio de búsqueda
            try:
                resultados = self.search_function(texto)
            except Exception:
                logger.exception('Error ejecutando search_function')
                resultados = []

            self._all_items = resultados or []
            self._visible_offset = 0

            # Limpiar NavList y cargar la primera página
            try:
                self.nav_list.clear_items()
            except Exception:
                pass

            self._load_next_page()

        except Exception:
            logger.exception('Error en _on_search')

    def _load_next_page(self):
        if self.loading:
            return
        # Si no hay items cargados, nada que hacer
        if not self._all_items:
            return

        self.loading = True
        try:
            start = int(self._visible_offset or 0)
            end = min(start + self.page_limit, len(self._all_items))

            for itm in self._all_items[start:end]:
                try:
                    mapped = self.map_function(itm)
                    # Añadir al NavList
                    self.nav_list.add_item(mapped)
                except Exception:
                    logger.exception('Error mapeando o añadiendo item a NavList')

            self._visible_offset = end

        except Exception:
            logger.exception('Error en _load_next_page')
        finally:
            self.loading = False

    def _periodic_check(self):
        try:
            # Resolver canvas interno (compatibilidad con NavList internals)
            if not getattr(self, '_canvas', None):
                self._canvas = getattr(self.nav_list, '_parent_canvas', None) or getattr(self.nav_list, '_canvas', None)

            canvas = self._canvas
            if canvas is not None:
                try:
                    yview = canvas.yview()
                    if isinstance(yview, (list, tuple)) and len(yview) == 2 and yview[1] >= 0.995:
                        self._load_next_page()
                except Exception:
                    pass
        except Exception:
            logger.exception('Error en _periodic_check')
        finally:
            try:
                self.after(200, self._periodic_check)
            except Exception:
                pass

    def set_search_text(self, texto):
        try:
            self._search_var.set(texto)
            self._on_search()
        except Exception:
            pass
