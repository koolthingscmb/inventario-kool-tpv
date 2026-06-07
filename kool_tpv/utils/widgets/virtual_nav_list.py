"""VirtualNavList - Lista navegable simple y fluida.

Diseño minimalista:
- Filas creadas UNA SOLA VEZ al llamar set_items()
- Sin hover, sin re-render continuo
- Solo repinta la fila seleccionada/deseleccionada al hacer clic
- Scroll fluido con tk.Canvas nativo

API pública compatible con NavList:
  - add_item(data) / clear_items() / set_items(items)
  - select_next() / select_previous() / get_selected_data()
  - selected_index, on_select_callback, on_double_click_callback
  - bind_return(callback)
"""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import List, Tuple, Callable, Optional, Any

from kool_tpv.utils.config_loader import load_colors, load_layout_config

logger = logging.getLogger(__name__)

_ROW_HEIGHT_DEFAULT = 36
_HEADER_HEIGHT = 40
_FONT_HEADER_DEFAULT = ('Courier New', 14, 'bold')
_FONT_ROW_DEFAULT = ('Courier New', 12)


class VirtualNavList(ctk.CTkFrame):
    """Lista navegable simple y fluida. Sin hover, sin re-render masivo."""

    def __init__(
        self,
        parent,
        columns: List[Tuple],
        on_select: Optional[Callable[[Any], None]] = None,
        on_double_click: Optional[Callable[[Any], None]] = None,
        module_name: str = 'clientes',
        keyboard_manager=None,
        layout_config: Optional[dict] = None,
        **kwargs
    ):
        self.colors = load_colors(module_name)
        self.module_name = module_name

        nav_cfg = self.colors.get('nav_list', {})
        self.row_normal_bg    = nav_cfg.get('row_normal_bg',    '#1a1a1a')
        self.row_normal_text  = nav_cfg.get('row_normal_text',  '#e0e0e0')
        self.row_selected_bg  = nav_cfg.get('row_selected_bg',  '#0d0d0d')
        self.row_selected_text= nav_cfg.get('row_selected_text','#ffffff')

        border_key = nav_cfg.get('row_selected_border', 'primary')
        self.row_selected_border = (
            self.colors.get('primary', '#FFD700') if border_key == 'primary' else border_key
        )

        layout_root = layout_config if isinstance(layout_config, dict) else (load_layout_config() or {})
        nav_layout = layout_root.get('components', {}).get('nav_list', {}) or {}
        self.row_height: int = int(nav_layout.get('row_height', nav_cfg.get('row_height', _ROW_HEIGHT_DEFAULT)))

        font_cfg = self.colors.get('fonts', {})
        self._font_header = tuple(font_cfg.get('header', list(_FONT_HEADER_DEFAULT)))
        self._font_row    = tuple(font_cfg.get('row',    list(_FONT_ROW_DEFAULT)))

        super().__init__(
            parent,
            fg_color=self.colors.get('background', '#000000'),
            **kwargs
        )

        self.columns = self._parse_columns(columns)
        self.on_select_callback = on_select
        self.on_double_click_callback = on_double_click
        self.keyboard_manager = keyboard_manager

        self._all_data: List[dict] = []
        self.selected_index: int = -1
        # _row_widgets: lista de (frame, labels[]) creados una sola vez
        self._row_widgets: List[tuple] = []
        self._on_return_callback = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Parseo de columnas
    # ------------------------------------------------------------------

    def _parse_columns(self, columns):
        result = []
        for col in columns:
            try:
                if len(col) == 3:
                    key, width, label = col
                elif len(col) == 2:
                    key, width = col
                    label = key
                else:
                    key = str(col); width = 100; label = key
            except Exception:
                key = str(col); width = 100; label = key
            result.append((key, int(width), str(label)))
        return result

    # ------------------------------------------------------------------
    # Construcción UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        bg      = self.colors.get('background', '#000000')
        bg_dark = self.colors.get('bg_dark', '#0d0d0d')
        secondary = self.colors.get('secondary', '#FFD700')

        # Header
        self._header = tk.Frame(self, bg=bg_dark, height=_HEADER_HEIGHT)
        self._header.pack(fill='x', padx=6, pady=(0, 2))
        self._header.pack_propagate(False)
        x = 8
        for key, width, label in self.columns:
            tk.Label(
                self._header, text=label, font=self._font_header,
                fg=secondary, bg=bg_dark, anchor='w'
            ).place(x=x, y=8, width=width, height=_HEADER_HEIGHT - 16)
            x += width + 8

        # Canvas + scrollbar
        container = tk.Frame(self, bg=bg)
        container.pack(fill='both', expand=True, padx=6, pady=(0, 6))

        self._scrollbar = tk.Scrollbar(container, orient='vertical')
        self._scrollbar.pack(side='right', fill='y')

        self._canvas = tk.Canvas(
            container, bg=bg, highlightthickness=0,
            yscrollcommand=self._scrollbar.set
        )
        self._canvas.pack(side='left', fill='both', expand=True)
        self._scrollbar.config(command=self._canvas.yview)

        self._row_frame = tk.Frame(self._canvas, bg=bg)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._row_frame, anchor='nw')

        self._row_frame.bind('<Configure>', lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfig(self._canvas_window, width=e.width))

        # Scroll con rueda — bindear en canvas y row_frame
        for widget in (self._canvas, self._row_frame):
            widget.bind('<MouseWheel>', self._on_mousewheel)
            widget.bind('<Button-4>',   self._on_mousewheel)
            widget.bind('<Button-5>',   self._on_mousewheel)

        # Enter sobre el canvas
        self._canvas.bind('<Return>',   lambda e: self._fire_return())
        self._canvas.bind('<KP_Enter>', lambda e: self._fire_return())
        self.bind('<FocusIn>', lambda e: self._canvas.focus_set())

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def bind_return(self, callback):
        self._on_return_callback = callback

    def _fire_return(self):
        if self._on_return_callback and self.selected_index >= 0:
            try:
                self._on_return_callback()
            except Exception:
                logger.exception('Error en return callback VirtualNavList')

    def set_items(self, items: List[dict]):
        """Reemplazar datos y reconstruir filas."""
        self._all_data = list(items)
        self.selected_index = -1
        self._rebuild_rows()

    def clear_items(self):
        self._all_data.clear()
        self.selected_index = -1
        self._rebuild_rows()

    def add_item(self, data: dict):
        """Añadir una fila al final."""
        self._all_data.append(data)
        self._append_row(len(self._all_data) - 1, data)
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def get_selected_data(self) -> Optional[dict]:
        if 0 <= self.selected_index < len(self._all_data):
            return self._all_data[self.selected_index]
        return None

    def select_next(self) -> bool:
        if not self._all_data:
            return False
        new_idx = 0 if self.selected_index < 0 else min(len(self._all_data) - 1, self.selected_index + 1)
        if new_idx != self.selected_index:
            self._select(new_idx, fire_callback=True)
            return True
        return False

    def select_previous(self) -> bool:
        if not self._all_data:
            return False
        new_idx = len(self._all_data) - 1 if self.selected_index < 0 else max(0, self.selected_index - 1)
        if new_idx != self.selected_index:
            self._select(new_idx, fire_callback=True)
            return True
        return False

    # ------------------------------------------------------------------
    # Construcción/actualización de filas (SIN re-render masivo)
    # ------------------------------------------------------------------

    def _rebuild_rows(self):
        """Destruir todas las filas y recrearlas. Solo al llamar set_items/clear_items."""
        for w in self._row_frame.winfo_children():
            w.destroy()
        self._row_widgets.clear()

        for i, data in enumerate(self._all_data):
            self._append_row(i, data)

        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def _append_row(self, i: int, data: dict):
        """Crear una fila nueva para el índice i."""
        rh = self.row_height
        bg_row = self.row_normal_bg
        fg_row = self.row_normal_text

        row = tk.Frame(self._row_frame, bg=bg_row, height=rh)
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)

        labels = []
        x = 8
        for key, width, _ in self.columns:
            val = str(data.get(key, ''))
            lbl = tk.Label(row, text=val, font=self._font_row, fg=fg_row, bg=bg_row, anchor='w')
            lbl.place(x=x, y=0, width=width, height=rh)
            labels.append(lbl)
            x += width + 8

        self._row_widgets.append((row, labels))

        # Eventos — bindear en frame y cada label
        for widget in [row] + labels:
            widget.bind('<Button-1>',        lambda e, idx=i: self._on_row_click(idx))
            widget.bind('<Double-Button-1>', lambda e, idx=i: self._on_row_double_click(idx))
            widget.bind('<MouseWheel>',      self._on_mousewheel)
            widget.bind('<Button-4>',        self._on_mousewheel)
            widget.bind('<Button-5>',        self._on_mousewheel)

    # ------------------------------------------------------------------
    # Selección — solo repinta 2 filas máximo
    # ------------------------------------------------------------------

    def _select(self, index: int, fire_callback: bool = False):
        """Seleccionar fila: deseleccionar anterior, colorear nueva."""
        prev = self.selected_index

        # Deseleccionar fila anterior
        if 0 <= prev < len(self._row_widgets) and prev != index:
            self._paint_row(prev, selected=False)

        self.selected_index = index

        # Seleccionar nueva fila
        if 0 <= index < len(self._row_widgets):
            self._paint_row(index, selected=True)
            self._scroll_to_selected()

        if self.keyboard_manager:
            try:
                self.keyboard_manager.set_active_list(self)
            except Exception:
                pass
        try:
            self._canvas.focus_set()
        except Exception:
            pass

        if fire_callback and self.on_select_callback and 0 <= index < len(self._all_data):
            try:
                self.on_select_callback(self._all_data[index])
            except Exception:
                pass

    def _paint_row(self, index: int, selected: bool):
        """Cambiar color de fondo y texto de una fila. Sin recrear nada."""
        if index < 0 or index >= len(self._row_widgets):
            return
        row, labels = self._row_widgets[index]
        bg = self.row_selected_bg  if selected else self.row_normal_bg
        fg = self.row_selected_text if selected else self.row_normal_text
        try:
            row.configure(bg=bg)
            for lbl in labels:
                lbl.configure(bg=bg, fg=fg)
        except Exception:
            pass

    def _scroll_to_selected(self):
        if self.selected_index < 0 or not self._row_widgets:
            return
        try:
            rh = self.row_height + 1
            total_h = len(self._row_widgets) * rh
            if total_h == 0:
                return
            canvas_h = self._canvas.winfo_height()
            row_top = self.selected_index * rh
            row_bot = row_top + rh
            yview = self._canvas.yview()
            vis_top = yview[0] * total_h
            vis_bot = yview[1] * total_h
            if row_top < vis_top:
                self._canvas.yview_moveto(row_top / total_h)
            elif row_bot > vis_bot:
                self._canvas.yview_moveto((row_bot - canvas_h) / total_h)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_row_click(self, idx: int):
        self._select(idx)
        if self.on_select_callback and 0 <= idx < len(self._all_data):
            try:
                self.on_select_callback(self._all_data[idx])
            except Exception:
                pass

    def _on_row_double_click(self, idx: int):
        self._select(idx)
        if self.on_double_click_callback and 0 <= idx < len(self._all_data):
            try:
                self.on_double_click_callback(self._all_data[idx])
            except Exception:
                pass

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, 'units')
        elif event.num == 5:
            self._canvas.yview_scroll(1, 'units')
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
