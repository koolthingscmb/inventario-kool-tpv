"""VirtualNavList - Lista navegable con VIRTUALIZACIÓN REAL.

Diseño de alto rendimiento:
- Solo se crean los widgets necesarios para llenar la pantalla (celdas reciclables).
- El scroll no mueve miles de widgets, solo actualiza el texto de los existentes.
- Memoria constante e independiente del número de registros (10 o 100.000).
- Compatible con la API original de NavList.
"""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import List, Tuple, Callable, Optional, Any
from decimal import Decimal

from kool_tpv.utils.config_loader import load_colors, load_layout_config, load_font_config

logger = logging.getLogger(__name__)

_ROW_HEIGHT_DEFAULT = 38
_HEADER_HEIGHT = 42
_FONT_HEADER_DEFAULT = ('Courier New', 14, 'bold')
_FONT_ROW_DEFAULT = ('Courier New', 12)


class VirtualNavList(ctk.CTkFrame):
    """Lista navegable con reciclaje de celdas para alto rendimiento."""

    def __init__(
        self,
        parent,
        columns: List[Tuple],
        on_select: Optional[Callable[[Any], None]] = None,
        on_double_click: Optional[Callable[[Any], None]] = None,
        module_name: str = 'clientes',
        keyboard_manager=None,
        layout_config: Optional[dict] = None,
        row_color_callback: Optional[Callable[[dict, int], dict]] = None,
        multi_select: bool = False,
        on_selection_change: Optional[Callable[[List[int]], None]] = None,
        **kwargs
    ):
        self.colors = load_colors(module_name)
        self.module_name = module_name
        self.row_color_callback = row_color_callback
        self.multi_select = multi_select
        self.on_selection_change_callback = on_selection_change

        nav_cfg = self.colors.get('nav_list', {})
        self.row_normal_bg    = nav_cfg.get('row_normal_bg',    '#1a1a1a')
        self.row_normal_text  = nav_cfg.get('row_normal_text',  '#e0e0e0')
        self.row_zebra_bg     = nav_cfg.get('row_zebra_bg',     '#222222') # Fallback cebra
        self.row_selected_bg  = nav_cfg.get('row_selected_bg',  '#0d0d0d')
        self.row_selected_text= nav_cfg.get('row_selected_text','#ffffff')

        # Activar zebra si está en config o por defecto (opcional)
        self.use_zebra = nav_cfg.get('use_zebra', True)

        border_key = nav_cfg.get('row_selected_border', 'primary')
        self.row_selected_border = (
            self.colors.get('primary', '#FFD700') if border_key == 'primary' else border_key
        )

        layout_root = layout_config if isinstance(layout_config, dict) else (load_layout_config() or {})
        nav_layout = layout_root.get('components', {}).get('nav_list', {}) or {}
        
        # Buscar override específico en el módulo (paridad con NavList antigua)
        module_cfg = layout_root.get('modules', {}).get(module_name, {})
        if isinstance(module_cfg, dict):
            if 'nav_list' in module_cfg:
                nav_layout = {**nav_layout, **module_cfg.get('nav_list', {})}
            elif 'virtual_nav_list' in module_cfg:
                nav_layout = {**nav_layout, **module_cfg.get('virtual_nav_list', {})}

        # Configuración de borde (Paridad con NavList)
        self.row_height: int = int(nav_layout.get('row_height', nav_cfg.get('row_height', _ROW_HEIGHT_DEFAULT)))
        self.row_selected_border_width = nav_layout.get('selected_border_width', 3)
        self.row_corner_radius = nav_layout.get('corner_radius', 4)

        _fc = load_font_config()
        _nav_fonts = _fc.get('components', {}).get('nav_list', {})
        _hdr = _nav_fonts.get('header', {})
        _row = _nav_fonts.get('row', {})
        self._font_header = (
            _hdr.get('family', _FONT_HEADER_DEFAULT[0]),
            _hdr.get('size',   _FONT_HEADER_DEFAULT[1]),
            _hdr.get('weight', _FONT_HEADER_DEFAULT[2]),
        )
        self._font_row = (
            _row.get('family', _FONT_ROW_DEFAULT[0]),
            _row.get('size',   _FONT_ROW_DEFAULT[1]),
            _row.get('weight', 'normal'),
        )

        super().__init__(
            parent,
            fg_color=self.colors.get('background', '#000000'),
            **kwargs
        )

        self.columns = self._parse_columns(columns)
        self.on_select_callback = on_select
        self.on_double_click_callback = on_double_click
        self.keyboard_manager = keyboard_manager

        # Datos y Estado
        self._all_data: List[dict] = []
        self.selected_index: int = -1
        self.selected_indices: set = set() # Para multi-select
        self._on_return_callback = None
        
        # Virtualización
        self._visible_rows: List[dict] = [] # Referencias a los widgets de fila creados
        self._top_index = 0  # Índice del primer dato visible
        self._row_widgets_count = 0 # Cuántas filas físicas hemos creado
        
        self._build_ui()

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

    def _build_ui(self):
        bg      = self.colors.get('background', '#000000')
        bg_dark = self.colors.get('bg_dark', '#0d0d0d')
        secondary = self.colors.get('secondary', '#FFD700')

        # 1. Header Fijo
        self._header = tk.Frame(self, bg=bg_dark, height=_HEADER_HEIGHT)
        self._header.pack(fill='x', padx=6, pady=(0, 2))
        self._header.pack_propagate(False)
        x = 10 # Margen inicial
        for key, width, label in self.columns:
            tk.Label(
                self._header, text=label, font=self._font_header,
                fg=secondary, bg=bg_dark, anchor='w'
            ).place(x=x, y=8, width=width, height=_HEADER_HEIGHT - 16)
            x += width + 12 # Espaciado

        # 2. Contenedor de lista
        container = tk.Frame(self, bg=bg)
        container.pack(fill='both', expand=True, padx=6, pady=(0, 6))

        # Scrollbar
        self._scrollbar = tk.Scrollbar(container, orient='vertical', command=self._on_vscroll)
        self._scrollbar.pack(side='right', fill='y')

        # Canvas (El corazón de la virtualización)
        self._canvas = tk.Canvas(
            container, bg=bg, highlightthickness=0,
            yscrollcommand=self._scrollbar.set
        )
        self._canvas.pack(side='left', fill='both', expand=True)
        
        # Frame interno que contendrá SOLO las filas visibles
        self._row_container = tk.Frame(self._canvas, bg=bg)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._row_container, anchor='nw')

        # Eventos de redimensión para recalcular cuántas filas caben
        self._canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Eventos de ratón
        for w in (self._canvas, self._row_container):
            w.bind('<MouseWheel>', self._on_mousewheel)
            w.bind('<Button-4>',   self._on_mousewheel)
            w.bind('<Button-5>',   self._on_mousewheel)
            w.bind('<Return>',     lambda e: self._fire_return())
            w.bind('<KP_Enter>',   lambda e: self._fire_return())

        self.bind('<FocusIn>', lambda e: self._canvas.focus_set())

    # ------------------------------------------------------------------
    # Lógica de Virtualización
    # ------------------------------------------------------------------

    def _on_canvas_configure(self, event):
        """Al cambiar el tamaño del canvas, creamos/ajustamos los widgets de fila."""
        canvas_w = event.width
        canvas_h = event.height
        self._canvas.itemconfig(self._canvas_window, width=canvas_w)
        
        # Calcular cuántas filas caben en pantalla + un pequeño buffer
        needed = (canvas_h // self.row_height) + 2
        
        if needed > self._row_widgets_count:
            # Crear más widgets de fila si faltan
            for i in range(self._row_widgets_count, needed):
                self._create_row_widget()
            self._row_widgets_count = needed
            
        self._refresh_ui()

    def _create_row_widget(self):
        """Crea un widget de fila vacío y lo añade al pool."""
        rh = self.row_height
        bg = self.row_normal_bg
        fg = self.row_normal_text
        
        # Volvemos a tk.Frame para evitar cualquier artefacto o borde fantasma de CTk
        row_frame = tk.Frame(
            self._row_container, 
            bg=bg, 
            height=rh,
            highlightthickness=0,
            bd=0
        )
        # pack sin padx ni pady para que las filas sean bloques continuos
        row_frame.pack(fill='x', side='top')
        row_frame.pack_propagate(False)
        
        labels = []
        x = 10 # Margen inicial
        for i, (key, width, _) in enumerate(self.columns):
            # Si es la última columna, le damos un margen extra para que no la tape el scroll
            actual_width = width
            if i == len(self.columns) - 1:
                actual_width = width + 20 # Espacio extra para el scroll
            
            lbl = tk.Label(row_frame, text="", font=self._font_row, fg=fg, bg=bg, anchor='w')
            lbl.place(x=x, y=0, width=actual_width, height=rh)
            labels.append(lbl)
            x += width + 12 # Espaciado
            
        idx_in_pool = len(self._visible_rows)
        row_data = {
            'frame': row_frame,
            'labels': labels,
            'data_index': -1 # A qué índice de datos representa actualmente
        }
        
        # Bindings (clic, doble clic, scroll)
        for w in [row_frame] + labels:
            w.bind('<Button-1>', lambda e, i=idx_in_pool: self._on_row_click(i))
            w.bind('<Double-Button-1>', lambda e, i=idx_in_pool: self._on_row_double_click(i))
            w.bind('<MouseWheel>', self._on_mousewheel)
            w.bind('<Button-4>',   self._on_mousewheel)
            w.bind('<Button-5>',   self._on_mousewheel)
            
        self._visible_rows.append(row_data)

    def _refresh_ui(self):
        """Actualiza el contenido de los widgets visibles según el scroll."""
        if not self._all_data:
            # Ocultar todos los widgets si no hay datos
            for row in self._visible_rows:
                row['frame'].pack_forget()
                row['data_index'] = -1
            self._canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        total_items = len(self._all_data)
        total_height = total_items * (self.row_height + 1)
        self._canvas.configure(scrollregion=(0, 0, 0, total_height))
        
        # Obtener posición actual del scroll (0.0 a 1.0)
        try:
            scroll_pos = self._canvas.yview()[0]
        except Exception:
            scroll_pos = 0.0
            
        # Calcular qué índice de datos debe ir arriba
        self._top_index = int(scroll_pos * total_items)
        # Asegurar que no nos pasamos del final
        max_top = max(0, total_items - (len(self._visible_rows) - 1))
        self._top_index = min(self._top_index, max_top)
        
        # Posicionar el row_container en el scroll exacto para que parezca continuo
        y_offset = self._top_index * (self.row_height + 1)
        self._canvas.coords(self._canvas_window, 0, y_offset)
        
        # Actualizar cada widget de fila con los datos correspondientes
        for i, row in enumerate(self._visible_rows):
            data_idx = self._top_index + i
            
            if data_idx < total_items:
                row['frame'].pack(fill='x', pady=1)
                row['data_index'] = data_idx
                data = self._all_data[data_idx]
                
                # 1. Determinar colores base (Zebra / Normal)
                is_sel = (data_idx == self.selected_index)
                if self.multi_select:
                    is_sel = (data_idx in self.selected_indices)
                
                if is_sel:
                    bg = self.row_selected_bg
                    fg = self.row_selected_text
                else:
                    # Lógica de color normal / cebra / personalizada
                    bg = self.row_normal_bg
                    if self.use_zebra and (data_idx % 2 != 0):
                        bg = self.row_zebra_bg
                    fg = self.row_normal_text

                # Sobrescribir si hay colores en el data o callback (Incluso si está seleccionada si el callback lo decide)
                custom_colors = None
                if self.row_color_callback:
                    try:
                        custom_colors = self.row_color_callback(data, data_idx)
                    except: pass
                
                if not custom_colors:
                    # Fallback a claves especiales en data
                    if '_row_bg' in data or '_row_fg' in data:
                        custom_colors = {
                            'bg': data.get('_row_bg'),
                            'fg': data.get('_row_fg')
                        }
                
                if custom_colors:
                    # Si la fila tiene color personalizado, MANDAR sobre el resto (seleccion, cebra, etc)
                    if custom_colors.get('bg'): bg = custom_colors['bg']
                    if custom_colors.get('fg'): fg = custom_colors['fg']
                
                # Actualizar Frame (Bloque sólido, sin bordes)
                row['frame'].configure(bg=bg)
                
                # Actualizar Labels
                for j, lbl in enumerate(row['labels']):
                    key = self.columns[j][0]
                    width = self.columns[j][1]
                    val = str(data.get(key, ''))
                    lbl.configure(text=self._truncate(val, width), bg=bg, fg=fg)
            else:
                # Ocultar widget si no hay más datos para él
                row['frame'].pack_forget()
                row['data_index'] = -1

    def _on_vscroll(self, *args):
        """Manejador de scroll manual."""
        self._canvas.yview(*args)
        self._refresh_ui()

    def _on_mousewheel(self, event):
        """Manejador de rueda de ratón."""
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self._canvas.yview_scroll(-3, 'units')
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self._canvas.yview_scroll(3, 'units')
        self._refresh_ui()

    # ------------------------------------------------------------------
    # API Pública (Compatible con NavList)
    # ------------------------------------------------------------------

    def set_items(self, items: List[dict]):
        self._all_data = list(items)
        self.selected_index = -1
        self.selected_indices.clear()
        # Asegurar que el canvas tenga sus dimensiones reales antes de refrescar
        self.update_idletasks()
        canvas_h = self._canvas.winfo_height()
        if canvas_h <= 1:
            # El canvas aún no ha sido configurado (tab oculto, etc.)
            # Crear filas con un fallback de altura y refrescar
            fallback_h = 400
            needed = (fallback_h // self.row_height) + 2
            if needed > self._row_widgets_count:
                for i in range(self._row_widgets_count, needed):
                    self._create_row_widget()
                self._row_widgets_count = needed
        # Volver al inicio del scroll
        self._canvas.yview_moveto(0)
        self._refresh_ui()

        if self.keyboard_manager:
            try: 
                self.keyboard_manager.set_active_list(self)
                # Si hay items, dar foco al canvas para capturar teclas
                if items:
                    self._canvas.focus_set()
            except: pass

    def clear_items(self):
        self._all_data = []
        self.selected_index = -1
        self.selected_indices.clear()
        self._refresh_ui()

    def get_selected_data(self) -> Optional[dict]:
        if 0 <= self.selected_index < len(self._all_data):
            return self._all_data[self.selected_index]
        return None

    def get_selected_items(self) -> List[dict]:
        """Obtener lista de todos los items seleccionados (multi-select)."""
        if self.multi_select:
            return [self._all_data[i] for i in sorted(list(self.selected_indices)) if 0 <= i < len(self._all_data)]
        else:
            sel = self.get_selected_data()
            return [sel] if sel else []

    def select_all(self):
        """Seleccionar todos los items (solo multi-select)."""
        if not self.multi_select: return
        self.selected_indices = set(range(len(self._all_data)))
        self._refresh_ui()
        self._fire_selection_change()

    def deselect_all(self):
        """Deseleccionar todos los items."""
        self.selected_indices.clear()
        self.selected_index = -1
        self._refresh_ui()
        self._fire_selection_change()

    def toggle_selection(self, index: int):
        """Alternar selección de un item (solo multi-select)."""
        if not self.multi_select: return
        if 0 <= index < len(self._all_data):
            if index in self.selected_indices:
                self.selected_indices.discard(index)
            else:
                self.selected_indices.add(index)
            self._refresh_ui()
            self._fire_selection_change()

    def _fire_selection_change(self):
        if self.on_selection_change_callback:
            try:
                self.on_selection_change_callback(list(self.selected_indices))
            except: pass

    def select_next(self) -> bool:
        if not self._all_data: return False
        new_idx = 0 if self.selected_index < 0 else min(len(self._all_data) - 1, self.selected_index + 1)
        if new_idx != self.selected_index:
            self._select(new_idx, fire_callback=True)
            return True
        return False

    def select_previous(self) -> bool:
        if not self._all_data: return False
        new_idx = len(self._all_data) - 1 if self.selected_index < 0 else max(0, self.selected_index - 1)
        if new_idx != self.selected_index:
            self._select(new_idx, fire_callback=True)
            return True
        return False

    def bind_return(self, callback):
        self._on_return_callback = callback

    # ------------------------------------------------------------------
    # Manejo de Eventos de Fila
    # ------------------------------------------------------------------

    def _on_row_click(self, pool_idx: int):
        data_idx = self._visible_rows[pool_idx]['data_index']
        if data_idx >= 0:
            if self.multi_select:
                self.toggle_selection(data_idx)
            else:
                self._select(data_idx, fire_callback=True)

    def _on_row_double_click(self, pool_idx: int):
        data_idx = self._visible_rows[pool_idx]['data_index']
        if data_idx >= 0:
            self._select(data_idx)
            if self.on_double_click_callback:
                self.on_double_click_callback(self._all_data[data_idx])

    def _select(self, index: int, fire_callback: bool = False):
        self.selected_index = index
        
        # Asegurar que el elemento seleccionado sea visible en el scroll
        self._ensure_visible(index)
        self._refresh_ui()
        
        if fire_callback and self.on_select_callback and 0 <= index < len(self._all_data):
            self.on_select_callback(self._all_data[index])
            
        if self.keyboard_manager:
            try: self.keyboard_manager.set_active_list(self)
            except: pass
        self._canvas.focus_set()

    def _ensure_visible(self, index: int):
        """Ajusta el scroll si el índice seleccionado está fuera de vista."""
        total = len(self._all_data)
        if total == 0: return
        
        # Obtener área visible actual
        top_v, bot_v = self._canvas.yview()
        item_pos_top = index / total
        item_pos_bot = (index + 1) / total
        
        if item_pos_top < top_v:
            self._canvas.yview_moveto(item_pos_top)
        elif item_pos_bot > bot_v:
            # Cuántos items caben en el canvas
            canvas_h = self._canvas.winfo_height()
            if canvas_h <= 1: canvas_h = 400 # Fallback
            items_per_page = canvas_h // self.row_height
            move_to = max(0, (index - items_per_page + 1) / total)
            self._canvas.yview_moveto(move_to)

    def _fire_return(self):
        if self._on_return_callback and self.selected_index >= 0:
            self._on_return_callback()

    def _truncate(self, text: str, width_px: int) -> str:
        try:
            char_w = max(1, int(self._font_row[1] * 0.7)) # Estimación
            max_chars = max(1, (width_px - 10) // char_w)
            if len(text) > max_chars:
                return text[:max(1, max_chars - 1)] + '…'
        except: pass
        return text
