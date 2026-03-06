"""
UI overlay para selección de cajero.

Hereda de SelectionOverlayTemplate y la adapta para cajeros.
"""
import logging
from typing import Optional, Callable, List, Dict

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate


class UICajero(SelectionOverlayTemplate):
    """Overlay para selección de cajero usando plantilla base."""

    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[Callable] = None):
        """
        Args:
            view_or_action_panel: TpvView o action_panel
            db: Database instance
            on_selection_callback: Función a ejecutar al seleccionar (recibe dict cajero)
        """
        # Configurar UI personalizada para cajeros
        ui_config = {
            'page_size': 10,  # Menos cajeros que productos
        }

        super().__init__(
            view_or_action_panel,
            db=db,
            on_selection_callback=on_selection_callback,
            ui_config=ui_config
        )

        # Personalizar título
        self.title_text = "SELECCIONAR CAJERO"
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Configurar columnas: ID, Nombre, Rol
        self.columns_config = [
            ("id", "ID", 60, "center"),
            ("nombre", "Nombre", 250, "w"),
            ("rol", "Rol", 120, "center"),
        ]

        # Reconfigurar treeview con las columnas de cajeros
        try:
            if hasattr(self, 'tree') and self.tree is not None:
                # Reconfigurar columnas
                self.tree.configure(columns=[c[0] for c in self.columns_config])
                for key, heading, width, anchor in self.columns_config:
                    try:
                        self.tree.heading(key, text=heading)
                        self.tree.column(key, width=width, anchor=anchor)
                    except Exception:
                        logging.exception(f'Error configurando columna {key}')
        except Exception:
            logging.exception('Error reconfigurando tree para cajeros')

        # Referencia a DB
        self.db = db

        # Ocultar botón "Añadir" (no aplica para cajeros)
        try:
            if hasattr(self, 'anadir_btn') and self.anadir_btn is not None:
                self.anadir_btn.pack_forget()
        except Exception:
            pass

    def _load_and_render(self, termino: str) -> None:
        """Cargar cajeros desde BD y renderizar en treeview.

        Args:
            termino: Término de búsqueda (filtra por nombre)
        """
        try:
            # Obtener todos los cajeros
            rows = self.db.fetch_all(
                "SELECT id, nombre, rol FROM usuarios ORDER BY nombre"
            )

            # Filtrar por término si existe
            cajeros = []
            for row in rows:
                nombre = row[1] or ''
                if termino.strip() == '' or termino.lower() in nombre.lower():
                    cajeros.append({
                        'id': row[0],
                        'nombre': nombre,
                        'rol': row[2] or ''
                    })

            # Guardar en _items para paginación
            self._items = cajeros
            self._current_page = 0

            # Renderizar
            self._render_clients_page()

        except Exception:
            logging.exception('Error cargando cajeros en UICajero')
            self._items = []
            self._render_clients_page()

    def _render_clients_page(self) -> None:
        """Renderizar página actual de cajeros en treeview.

        Override del método de la plantilla para usar columnas específicas de cajeros.
        """
        try:
            import math

            # Limpiar tree
            for child in list(self.tree.get_children()):
                try:
                    self.tree.delete(child)
                except Exception:
                    pass

            # Calcular rango de página
            start = self._current_page * self._page_size
            end = start + self._page_size
            page_items = (self._items or [])[start:end]

            # Insertar cajeros con columnas (id, nombre, rol)
            for cajero in page_items:
                try:
                    self.tree.insert(
                        '',
                        'end',
                        iid=str(cajero.get('id')),
                        values=(
                            cajero.get('id'),
                            cajero.get('nombre'),
                            cajero.get('rol')
                        )
                    )
                except Exception:
                    logging.exception('Error insertando cajero en tree')

            # Actualizar paginación
            total_pages = max(1, math.ceil(len(self._items or []) / self._page_size))
            try:
                self.page_label.configure(text=f"Página {self._current_page + 1} / {total_pages}")
                self.prev_btn.configure(state=('normal' if self._current_page > 0 else 'disabled'))
                self.next_btn.configure(state=('normal' if self._current_page < total_pages - 1 else 'disabled'))
            except Exception:
                pass

        except Exception:
            logging.exception('Error renderizando página de cajeros')

    def _confirm_selection(self) -> None:
        """Override: confirmar selección de cajero y ejecutar callback."""
        try:
            sel = self.tree.selection()
            if not sel:
                return

            iid = sel[0]

            # Buscar cajero completo en _items
            cajero_data = None
            for c in (self._items or []):
                if str(c.get('id')) == str(iid):
                    cajero_data = c
                    break

            if not cajero_data:
                logging.warning(f'Cajero {iid} no encontrado en _items')
                return

            # Ejecutar callback (CajeroAction._on_cajero_selected)
            if callable(self.on_selection_callback):
                try:
                    self.on_selection_callback(cajero_data)
                except Exception:
                    logging.exception('Error ejecutando callback de selección de cajero')

            # Ocultar overlay
            self.hide()

        except Exception:
            logging.exception('Error confirmando selección de cajero')
