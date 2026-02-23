"""NavList - Widget lista navegable con teclado (flechas Up/Down).

Características:

    Filas genéricas con columnas configurables
    Hover elegante
    Selección con borde del módulo (usa primary)
    Auto-registro con KeyboardManager
    Scroll automático
    Colores desde colors_config
"""
import logging
from typing import List, Tuple, Callable, Optional, Any
import customtkinter as ctk
import tkinter as tk

from kool_tpv.utils.config_loader import load_colors

logger = logging.getLogger(__name__)


class NavList(ctk.CTkScrollableFrame):
    """Lista navegable con flechas - implementa protocolo Navigable."""

    def __init__(
        self,
        parent,
        columns: List[Tuple[str, int]],  # [(header, width), ...]
        on_select: Optional[Callable[[Any], None]] = None,
        on_double_click: Optional[Callable[[Any], None]] = None,
        module_name: str = 'clientes',
        keyboard_manager=None,
        **kwargs
    ):
        # Cargar colores del módulo
        self.colors = load_colors(module_name)
        self.module_name = module_name

        # Configuración nav_list desde colors_config (con fallbacks)
        nav_cfg = self.colors.get('nav_list', {})
        self.row_normal_bg = nav_cfg.get('row_normal_bg', '#1a1a1a')
        self.row_normal_text = nav_cfg.get('row_normal_text', '#e0e0e0')
        self.row_hover_bg = nav_cfg.get('row_hover_bg', '#2a2a2a')
        self.row_hover_text = nav_cfg.get('row_hover_text', '#ffffff')
        self.row_selected_bg = nav_cfg.get('row_selected_bg', '#0d0d0d')
        self.row_selected_text = nav_cfg.get('row_selected_text', '#ffffff')

        # Borde selección: usar 'primary' si dice "primary"
        border_key = nav_cfg.get('row_selected_border', 'primary')
        if border_key == 'primary':
            self.row_selected_border = self.colors.get('primary', '#FFD700')
        else:
            self.row_selected_border = border_key

        self.row_height = nav_cfg.get('row_height', 35)

        # Frame scroll
        super().__init__(
            parent,
            fg_color=self.colors.get('background', '#000000'),
            **kwargs
        )

        self.columns = columns
        self.on_select_callback = on_select
        # Callback para doble-click (p. ej. abrir ficha)
        self.on_double_click_callback = on_double_click
        self.keyboard_manager = keyboard_manager

        # Estado interno
        self.rows_data: List[tuple] = []  # [(data_dict, frame_widget), ...]
        self.selected_index = -1

        # Crear header
        self._create_header()

        logger.debug(f'NavList creado con {len(columns)} columnas, module={module_name}')

    def _create_header(self):
        """Crear fila de headers."""
        header_frame = ctk.CTkFrame(
            self,
            fg_color=self.colors.get('bg_dark', '#0d0d0d'),
            height=40
        )
        header_frame.pack(fill='x', padx=6, pady=(0, 6))

        for col in self.columns:
            # columns entries can be (key, width) or (key, width, display_text)
            try:
                if len(col) == 2:
                    header_text, width = col
                else:
                    header_text, width, display_text = col
                    header_text = display_text
            except Exception:
                # Fallback: try unpacking directly
                try:
                    header_text, width = col
                except Exception:
                    header_text = str(col)
                    width = 100

            ctk.CTkLabel(
                header_frame,
                text=header_text,
                font=('Courier New', 14, 'bold'),
                text_color=self.colors.get('secondary', '#FFD700'),
                width=width,
                anchor='w'
            ).pack(side='left', padx=8, pady=8)

    def add_item(self, data: dict):
        """Añadir una fila a la lista.

        Args:
            data: Dict que debe contener keys según columnas + cualquier dato extra
        """
        # Crear frame de fila
        row_frame = ctk.CTkFrame(
            self,
            fg_color=self.row_normal_bg,
            corner_radius=6,
            height=self.row_height,
            border_width=0
        )
        row_frame.pack(fill='x', padx=6, pady=3)

        # Guardar referencia
        index = len(self.rows_data)
        self.rows_data.append((data, row_frame))

        # Crear labels por columna
        for col in self.columns:
            try:
                if len(col) == 2:
                    col_key, width = col
                else:
                    col_key, width, _ = col
            except Exception:
                try:
                    col_key, width = col
                except Exception:
                    # Fallback: treat entire spec as key
                    col_key = str(col)
                    width = 100

            # col_key puede ser header o key; usar raw key si existe
            value = data.get(col_key, '')

            lbl = ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=('Courier New', 12),
                text_color=self.row_normal_text,
                width=width,
                anchor='w'
            )
            lbl.pack(side='left', padx=8, pady=8)

            # Bind clicks
            try:
                lbl.bind('<Button-1>', lambda e, idx=index: self._on_row_click(idx))
                # doble-click separado (selección y acción distinta)
                lbl.bind('<Double-Button-1>', lambda e, idx=index: self._on_row_double_click(idx))
            except Exception:
                pass

        # Bind hover
        try:
            row_frame.bind('<Enter>', lambda e, f=row_frame: self._on_row_enter(f))
            row_frame.bind('<Leave>', lambda e, f=row_frame: self._on_row_leave(f))
            row_frame.bind('<Button-1>', lambda e, idx=index: self._on_row_click(idx))
            row_frame.bind('<Double-Button-1>', lambda e, idx=index: self._on_row_double_click(idx))
        except Exception:
            pass

    def _on_row_double_click(self, index: int):
        """Doble click en fila - ejecutar acción independiente de la selección."""
        try:
            # Asegurarnos de que la fila está seleccionada primero
            self._select_row(index)

            # Registrar como lista activa en KeyboardManager
            if self.keyboard_manager:
                try:
                    self.keyboard_manager.set_active_list(self)
                except Exception:
                    pass

            # Mover foco al NavList para que KeyboardManager no ignore teclas
            try:
                try:
                    self.focus_set()
                except Exception:
                    try:
                        self.winfo_toplevel().focus_set()
                    except Exception:
                        pass
            except Exception:
                pass

            # Callback de doble-click (acción diferenciada)
            if self.on_double_click_callback:
                try:
                    data, _ = self.rows_data[index]
                    self.on_double_click_callback(data)
                except Exception:
                    logger.exception('Error ejecutando on_double_click callback')

        except Exception:
            logger.exception('Error manejando doble-click en fila')

    def clear_items(self):
        """Limpiar todas las filas (mantiene header)."""
        try:
            # Destruir todos menos el header (primero)
            children = self.winfo_children()
            for widget in children[1:]:
                try:
                    widget.destroy()
                except Exception:
                    pass

            self.rows_data = []
            self.selected_index = -1

        except Exception:
            logger.exception('Error limpiando NavList')

    def set_items(self, items: List[dict]):
        """Reemplazar todas las filas con nueva lista.

        Args:
            items: Lista de dicts con datos para cada fila
        """
        self.clear_items()
        for item in items:
            self.add_item(item)

    def _on_row_enter(self, frame):
        """Hover sobre fila - solo si no está seleccionada."""
        try:
            # No aplicar hover si es la fila seleccionada
            if self.selected_index >= 0:
                _, selected_frame = self.rows_data[self.selected_index]
                if frame == selected_frame:
                    return

            frame.configure(fg_color=self.row_hover_bg)

            # Cambiar color texto de labels
            for child in frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        child.configure(text_color=self.row_hover_text)
                    except Exception:
                        pass

        except Exception:
            pass

    def _on_row_leave(self, frame):
        """Salir de hover - restaurar color normal."""
        try:
            # No restaurar si es la fila seleccionada
            if self.selected_index >= 0:
                _, selected_frame = self.rows_data[self.selected_index]
                if frame == selected_frame:
                    return

            frame.configure(fg_color=self.row_normal_bg)

            # Restaurar texto
            for child in frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        child.configure(text_color=self.row_normal_text)
                    except Exception:
                        pass

        except Exception:
            pass

    def _on_row_click(self, index: int):
        """Click en fila - seleccionar y notificar."""
        try:
            self._select_row(index)

            # Registrar como lista activa en KeyboardManager
            if self.keyboard_manager:
                try:
                    self.keyboard_manager.set_active_list(self)
                except Exception:
                    pass

            # Mover foco al NavList para que KeyboardManager no ignore teclas
            try:
                # Intentar dar foco al widget scrollable
                try:
                    self.focus_set()
                except Exception:
                    try:
                        self.winfo_toplevel().focus_set()
                    except Exception:
                        pass
            except Exception:
                pass

            # Callback
            if self.on_select_callback:
                try:
                    data, _ = self.rows_data[index]
                    self.on_select_callback(data)
                except Exception:
                    logger.exception('Error ejecutando on_select callback')

        except Exception:
            logger.exception('Error manejando click en fila')

    def _select_row(self, index: int):
        """Seleccionar fila visualmente."""
        try:
            if index < 0 or index >= len(self.rows_data):
                return

            # Restaurar fila anterior
            if self.selected_index >= 0 and self.selected_index < len(self.rows_data):
                _, prev_frame = self.rows_data[self.selected_index]
                prev_frame.configure(
                    fg_color=self.row_normal_bg,
                    border_width=0
                )
                for child in prev_frame.winfo_children():
                    if isinstance(child, ctk.CTkLabel):
                        try:
                            child.configure(text_color=self.row_normal_text)
                        except Exception:
                            pass

            # Highlight nueva fila
            data, new_frame = self.rows_data[index]
            try:
                new_frame.configure(
                    fg_color=self.row_selected_bg,
                    border_color=self.row_selected_border,
                    border_width=3
                )
            except Exception:
                try:
                    new_frame.configure(fg_color=self.row_selected_bg)
                except Exception:
                    pass

            for child in new_frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    try:
                        child.configure(text_color=self.row_selected_text)
                    except Exception:
                        pass

            self.selected_index = index

            # Auto-scroll para hacer visible
            self._scroll_to_index(index)

        except Exception:
            logger.exception('Error seleccionando fila')

    def _scroll_to_index(self, index: int):
        """Hacer scroll para que fila sea visible."""
        try:
            if not self.rows_data:
                return

            total = len(self.rows_data)
            ratio = index / max(total - 1, 1)

            # Intentar localizar canvas interno
            canvas = None
            if hasattr(self, '_parent_canvas'):
                canvas = getattr(self, '_parent_canvas')
            elif hasattr(self, '_canvas'):
                canvas = getattr(self, '_canvas')

            if canvas is not None:
                try:
                    canvas.yview_moveto(ratio)
                except Exception:
                    pass

        except Exception:
            logger.exception('Error haciendo scroll a índice')

    # === Implementación protocolo Navigable ===

    def select_next(self) -> bool:
        """Seleccionar siguiente fila (flecha abajo)."""
        try:
            if not self.rows_data:
                return False

            # Si no hay selección, empezar por primera
            if self.selected_index < 0:
                nuevo_indice = 0
            else:
                nuevo_indice = min(len(self.rows_data) - 1, self.selected_index + 1)

            if nuevo_indice != self.selected_index:
                self._select_row(nuevo_indice)

                # Callback
                if self.on_select_callback:
                    try:
                        data, _ = self.rows_data[nuevo_indice]
                        self.on_select_callback(data)
                    except Exception:
                        logger.exception('Error en callback select_next')

                return True

            return False

        except Exception:
            logger.exception('Error en select_next')
            return False

    def select_previous(self) -> bool:
        """Seleccionar fila anterior (flecha arriba)."""
        try:
            if not self.rows_data:
                return False

            # Si no hay selección, empezar por última
            if self.selected_index < 0:
                nuevo_indice = len(self.rows_data) - 1
            else:
                nuevo_indice = max(0, self.selected_index - 1)

            if nuevo_indice != self.selected_index:
                self._select_row(nuevo_indice)

                # Callback
                if self.on_select_callback:
                    try:
                        data, _ = self.rows_data[nuevo_indice]
                        self.on_select_callback(data)
                    except Exception:
                        logger.exception('Error en callback select_previous')

                return True

            return False

        except Exception:
            logger.exception('Error en select_previous')
            return False

    def get_selected_data(self) -> Optional[dict]:
        """Obtener datos de la fila seleccionada."""
        try:
            if self.selected_index >= 0 and self.selected_index < len(self.rows_data):
                data, _ = self.rows_data[self.selected_index]
                return data
            return None
        except Exception:
            logger.exception('Error obteniendo datos seleccionados')
            return None
