"""VirtualNavList - Lista navegable con VIRTUALIZACIÓN REAL.

Diseño de alto rendimiento:
- Solo se crean los widgets necesarios para llenar la pantalla (celdas reciclables).
- El scroll no mueve miles de widgets, solo actualiza el texto de los existentes.
- Memoria constante e independiente del número de registros (10 o 100.000).
- Compatible con la API original de NavList.
"""
import logging
import re
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
        
        # Estado de ordenación
        self._sort_column = None  # Key de la columna ordenada
        self._sort_direction = 'asc'  # 'asc' o 'desc'
        self._header_labels = []  # Referencias a los labels del header para actualizar indicadores
        
        # Virtualización
        self._visible_rows: List[dict] = [] # Referencias a los widgets de fila creados
        self._top_index = 0  # Índice del primer dato visible
        self._row_widgets_count = 0 # Cuántas filas físicas hemos creado
        
        # Sistema de columnas responsivas
        self._col_positions = [] # [(x, width), ...] calculado dinámicamente
        
        self._build_ui()

    def _parse_columns(self, columns):
        result = []
        for col in columns:
            try:
                stretch = False
                if len(col) == 4:
                    key, width, label, stretch = col
                elif len(col) == 3:
                    # Detectar si el tercer elemento es el label o el stretch
                    if isinstance(col[2], bool):
                        key, width, stretch = col
                        label = key
                    else:
                        key, width, label = col
                elif len(col) == 2:
                    key, width = col
                    label = key
                else:
                    key = str(col); width = 100; label = key
            except Exception:
                key = str(col); width = 100; label = key
            
            result.append({
                'key': key,
                'width': int(width),
                'label': str(label),
                'stretch': stretch
            })
        return result

    def _build_ui(self):
        bg      = self.colors.get('background', '#000000')
        bg_dark = self.colors.get('bg_dark', '#0d0d0d')
        secondary = self.colors.get('secondary', '#FFD700')

        # 1. Header Canvas (Paso 1: Cabecera desplazable)
        self._header_canvas = tk.Canvas(self, bg=bg_dark, height=_HEADER_HEIGHT, highlightthickness=0)
        self._header_canvas.pack(fill='x', padx=6, pady=(0, 2))
        
        self._header_container = tk.Frame(self._header_canvas, bg=bg_dark, height=_HEADER_HEIGHT)
        self._header_window = self._header_canvas.create_window((0, 0), window=self._header_container, anchor='nw')
        
        x = 10 # Margen inicial
        self._header_labels = []
        for i, col in enumerate(self.columns):
            width = col['width']
            label = col['label']
            header_label = tk.Label(
                self._header_container, text=label, font=self._font_header,
                fg=secondary, bg=bg_dark, anchor='w', cursor='hand2'
            )
            header_label.place(x=x, y=8, width=width, height=_HEADER_HEIGHT - 16)
            header_label.bind('<Button-1>', lambda e, col_idx=i: self._on_header_click(col_idx))
            self._header_labels.append(header_label)
            x += width + 12 # Espaciado

        # 2. Contenedor de lista
        container = tk.Frame(self, bg=bg)
        container.pack(fill='both', expand=True, padx=6, pady=(0, 6))

        # Scrollbar Horizontal (Paso 2: Barra de scroll física en la parte inferior)
        self._scrollbar_x = tk.Scrollbar(container, orient='horizontal', command=self._on_hscroll)
        self._scrollbar_x.pack(side='bottom', fill='x')

        # Scrollbar Vertical
        self._scrollbar = tk.Scrollbar(container, orient='vertical', command=self._on_vscroll)
        self._scrollbar.pack(side='right', fill='y')

        # Canvas (El corazón de la virtualización)
        self._canvas = tk.Canvas(
            container, bg=bg, highlightthickness=0,
            yscrollcommand=self._scrollbar.set,
            xscrollcommand=self._on_canvas_xscroll
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
            # NO bindeamos Return/Enter aquí para no interferir con el BarcodeService o el CarritoNavList

        # Atajos de teclado para multi-select
        self._canvas.bind('<Control-a>', lambda e: self.select_all())
        self._canvas.bind('<Control-A>', lambda e: self.select_all())
        # En Mac suele ser Command-A, pero tkinter suele mapear Control a Command en muchos casos o necesita binding extra
        self._canvas.bind('<Command-a>', lambda e: self.select_all())
        self._canvas.bind('<Command-A>', lambda e: self.select_all())

        # Atajo para Enter
        self._canvas.bind('<Return>', self._handle_return_key)
        self._canvas.bind('<KP_Enter>', self._handle_return_key)
        self._canvas.bind('<space>', self._on_space_key)

        # Atajos para scroll horizontal con teclado (Paso 5)
        self._canvas.bind('<Left>', self._on_key_left)
        self._canvas.bind('<Right>', self._on_key_right)

        self.bind('<FocusIn>', lambda e: self._canvas.focus_set())

    # ------------------------------------------------------------------
    # Lógica de Virtualización
    # ------------------------------------------------------------------

    @property
    def data(self) -> List[dict]:
        """Propiedad de compatibilidad con NavList antigua."""
        return self._all_data

    def select_index(self, index: int, fire_callback: bool = True):
        """Método de compatibilidad con NavList antigua."""
        self._select(index, fire_callback=fire_callback)

    def _on_canvas_configure(self, event):
        """Al cambiar el tamaño del canvas, recalculamos anchos de columna y ajustamos widgets."""
        canvas_w = event.width
        canvas_h = event.height
        
        # 1. INTELIGENCIA DE LÍMITES (Paso 4: Responsividad + Scroll Horizontal)
        # Calculamos el espacio mínimo que necesitan las columnas sumando sus anchos originales
        total_orig_w = sum(col['width'] for col in self.columns)
        fixed_margins = 10 + (12 * (len(self.columns) - 1)) + 25
        min_required_width = total_orig_w + fixed_margins
        
        if canvas_w < min_required_width:
            # Pantalla pequeña: se activa la barra de scroll y las columnas mantienen su tamaño mínimo legible
            table_width = min_required_width
            self._scrollbar_x.pack(side='bottom', fill='x')
        else:
            # Pantalla grande: se oculta la barra de scroll y las columnas se estiran proporcionalmente
            table_width = canvas_w
            self._scrollbar_x.pack_forget()
            
        self._table_width = table_width
        
        # Configurar anchos de los frames internos al tamaño final calculado
        self._canvas.itemconfig(self._canvas_window, width=table_width)
        self._header_canvas.itemconfig(self._header_window, width=table_width)
        self._header_canvas.configure(scrollregion=(0, 0, table_width, _HEADER_HEIGHT))
        
        # 2. RECALCULAR ANCHOS RESPONSIVOS / PROPORCIONALES
        if total_orig_w > 0:
            available_w = max(100, table_width - fixed_margins)
            
            # Identificar columnas que se estiran (stretch=True)
            stretch_cols = [c for c in self.columns if c.get('stretch', False)]
            
            new_positions = []
            current_x = 10
            
            if stretch_cols:
                # MODO PRO: Columnas fijas + una o varias elásticas
                # Calculamos cuánto espacio ocupan las fijas
                fixed_w_sum = sum(c['width'] for c in self.columns if not c.get('stretch', False))
                remaining_w = max(0, available_w - fixed_w_sum)
                
                # Repartimos el sobrante entre las elásticas (normalmente solo habrá una)
                stretch_share = remaining_w // len(stretch_cols)
                
                for i, col in enumerate(self.columns):
                    if col.get('stretch', False):
                        col_w = stretch_share
                    else:
                        col_w = col['width']
                    
                    new_positions.append((current_x, col_w))
                    if i < len(self._header_labels):
                        self._header_labels[i].place(x=current_x, width=col_w)
                    current_x += col_w + 12
            else:
                # MODO COMPATIBILIDAD: Reparto proporcional clásico (todas se estiran según su peso)
                for i, col in enumerate(self.columns):
                    orig_w = col['width']
                    col_w = int((orig_w / total_orig_w) * available_w)
                    new_positions.append((current_x, col_w))
                    
                    if i < len(self._header_labels):
                        self._header_labels[i].place(x=current_x, width=col_w)
                    
                    current_x += col_w + 12
            
            self._col_positions = new_positions

        # 3. ACTUALIZAR FILAS YA CREADAS (Pivote de place)
        if self._col_positions:
            for row in self._visible_rows:
                for i, lbl in enumerate(row['labels']):
                    if i < len(self._col_positions):
                        x, w = self._col_positions[i]
                        lbl.place(x=x, width=w)

        # 4. CALCULAR NECESIDAD DE MÁS FILAS
        needed = (canvas_h // self.row_height) + 2
        if needed > self._row_widgets_count:
            for i in range(self._row_widgets_count, needed):
                self._create_row_widget()
            self._row_widgets_count = needed
            
        self._refresh_ui()

    def _create_row_widget(self):
        """Crea un widget de fila vacío y lo añade al pool usando anchos responsivos."""
        rh = self.row_height
        bg = self.row_normal_bg
        fg = self.row_normal_text
        
        row_frame = tk.Frame(
            self._row_container, 
            bg=bg, 
            height=rh,
            highlightthickness=0,
            bd=0
        )
        row_frame.pack(fill='x', side='top')
        row_frame.pack_propagate(False)
        
        labels = []
        # Si ya tenemos posiciones calculadas, las usamos; si no, fallback a estático
        if self._col_positions:
            for i in range(len(self.columns)):
                x, width = self._col_positions[i]
                lbl = tk.Label(row_frame, text="", font=self._font_row, fg=fg, bg=bg, anchor='w')
                lbl.place(x=x, y=0, width=width, height=rh)
                labels.append(lbl)
        else:
            # Fallback estático (solo primera creación antes de primer Configure)
            x = 10
            for col in self.columns:
                width = col['width']
                lbl = tk.Label(row_frame, text="", font=self._font_row, fg=fg, bg=bg, anchor='w')
                lbl.place(x=x, y=0, width=width, height=rh)
                labels.append(lbl)
                x += width + 12
            
        idx_in_pool = len(self._visible_rows)
        row_data = {
            'frame': row_frame,
            'labels': labels,
            'data_index': -1
        }
        
        # Bindings (clic, doble clic, scroll)
        for w in [row_frame] + labels:
            w.bind('<Button-1>', lambda e, i=idx_in_pool: self._on_row_click(i, e))
            w.bind('<Double-Button-1>', lambda e, i=idx_in_pool: self._on_row_double_click(i))
            w.bind('<MouseWheel>', self._on_mousewheel)
            w.bind('<Button-4>',   self._on_mousewheel)
            w.bind('<Button-5>',   self._on_mousewheel)
            
        self._visible_rows.append(row_data)

    def _refresh_ui(self):
        """Actualiza el contenido de los widgets visibles según el scroll."""
        table_width = getattr(self, '_table_width', 0)
        if not self._all_data:
            # Ocultar todos los widgets si no hay datos
            for row in self._visible_rows:
                row['frame'].pack_forget()
                row['data_index'] = -1
            self._canvas.configure(scrollregion=(0, 0, table_width, 0))
            return

        total_items = len(self._all_data)
        total_height = total_items * self.row_height
        self._canvas.configure(scrollregion=(0, 0, table_width, total_height))
        
        # Obtener posición actual del scroll (0.0 a 1.0)
        try:
            scroll_pos = self._canvas.yview()[0]
        except Exception:
            scroll_pos = 0.0
            
        # Calcular qué índice de datos debe ir arriba
        self._top_index = int(scroll_pos * total_items)
        # Asegurar que no nos pasamos del final
        max_top = max(0, total_items - len(self._visible_rows))
        self._top_index = min(self._top_index, max_top)
        
        # Posicionar el row_container en el scroll exacto para que parezca continuo
        y_offset = self._top_index * self.row_height
        self._canvas.coords(self._canvas_window, 0, y_offset)
        
        # Actualizar cada widget de fila con los datos correspondientes
        for i, row in enumerate(self._visible_rows):
            data_idx = self._top_index + i
            
            if data_idx < total_items:
                row['frame'].pack(fill='x')
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

                # Sobrescribir si hay colores en el data o callback
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
                row['frame'].configure(bg=bg, highlightthickness=0)
                
                # Actualizar Labels
                for j, lbl in enumerate(row['labels']):
                    col = self.columns[j]
                    key = col['key']
                    # Usar ancho actual calculado en lugar del original de self.columns
                    current_w = self._col_positions[j][1] if j < len(self._col_positions) else col['width']
                    
                    val = str(data.get(key, ''))
                    
                    # Soporte para estilos específicos por celda (Pro)
                    cell_bg = data.get(f"_cell_bg_{key}", bg)
                    cell_fg = data.get(f"_cell_fg_{key}", fg)
                    
                    lbl.configure(text=self._truncate(val, current_w), bg=cell_bg, fg=cell_fg)
            else:
                # Ocultar widget si no hay más datos para él
                row['frame'].pack_forget()
                row['data_index'] = -1

    def _on_vscroll(self, *args):
        """Manejador de scroll manual."""
        self._canvas.yview(*args)
        self._refresh_ui()

    def _on_hscroll(self, *args):
        """Paso 3: Sincroniza el desplazamiento horizontal desde la barra de scroll a ambos canvas."""
        self._canvas.xview(*args)
        self._header_canvas.xview(*args)

    def _on_canvas_xscroll(self, *args):
        """Paso 3: Sincroniza el desplazamiento horizontal desde el canvas principal a la barra de scroll y cabecera."""
        self._scrollbar_x.set(*args)
        self._header_canvas.xview_moveto(args[0])

    def _on_key_left(self, event):
        """Paso 5: Mover scroll horizontal a la izquierda con el teclado."""
        self._canvas.xview_scroll(-2, 'units')
        return 'break'

    def _on_key_right(self, event):
        """Paso 5: Mover scroll horizontal a la derecha con el teclado."""
        self._canvas.xview_scroll(2, 'units')
        return 'break'

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

    def set_items(self, items: List[dict], grab_focus: bool = True):
        self._all_data = list(items)
        self.selected_index = -1
        self.selected_indices.clear()

        # Reaplicar ordenación si existe una columna activa
        if self._sort_column:
            self._sort_data()

        # Asegurar refresco visual
        self.update_idletasks()
        self._refresh_ui()

        if self.keyboard_manager:
            try: 
                self.keyboard_manager.set_active_list(self)
                # Solo dar foco si se solicita explícitamente y hay items
                if grab_focus and items:
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

    def _handle_return_key(self, event=None):
        """Manejar pulsación de tecla Enter/Return."""
        if self.multi_select and self.selected_index >= 0:
            # En multi-select, Enter selecciona/deselecciona la fila enfocada
            self.toggle_selection(self.selected_index)
            return "break"

        if self._on_return_callback:
            try:
                self._on_return_callback()
            except Exception:
                logger.exception("Error ejecutando on_return_callback en VirtualNavList")

    def _on_space_key(self, event=None):
        """Alternar selección con la barra espaciadora en modo multi-select."""
        if self.multi_select and self.selected_index >= 0:
            self.toggle_selection(self.selected_index)
            return "break"

    # ------------------------------------------------------------------
    # Manejo de Eventos de Fila
    # ------------------------------------------------------------------

    def _on_row_click(self, pool_idx: int, event: Optional[tk.Event] = None):
        data_idx = self._visible_rows[pool_idx]['data_index']
        if data_idx >= 0:
            if self.multi_select:
                # Soporte para Shift y Control/Command (Estándar OS)
                is_shift = event and (event.state & 0x0001)  # Shift
                is_ctrl = event and (event.state & 0x0004 or event.state & 0x0008)  # Control o Command(Mac)
                
                if is_shift and self.selected_index >= 0:
                    # Rango entre foco actual y el clic
                    start = min(self.selected_index, data_idx)
                    end = max(self.selected_index, data_idx)
                    # En Shift-click estándar solemos limpiar y seleccionar el rango
                    # o extender si ya había selección. Para simplificar y robustez:
                    # Limpiamos y seleccionamos el rango nuevo.
                    self.selected_indices.clear()
                    for i in range(start, end + 1):
                        self.selected_indices.add(i)
                elif is_ctrl:
                    # Toggle individual (Sin limpiar el resto)
                    self.toggle_selection(data_idx)
                else:
                    # Clic normal: Limpiar selección y seleccionar solo este
                    self.selected_indices.clear()
                    self.selected_indices.add(data_idx)
                
                # El foco visual (cursor) siempre sigue al último clic
                self.selected_index = data_idx
                self._refresh_ui()
                self._fire_selection_change()
                self._canvas.focus_set()
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
        
        if self.multi_select:
            # En modo multi-select, si seleccionamos vía teclado/API, 
            # solemos querer que esta sea la única seleccionada a menos que usemos Ctrl/Shift
            self.selected_indices.clear()
            if 0 <= index < len(self._all_data):
                self.selected_indices.add(index)
            self._fire_selection_change()

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

    def destroy(self):
        """Limpieza profunda para evitar fugas de memoria."""
        try:
            # 1. Desvincular del gestor de teclado
            if self.keyboard_manager:
                try:
                    if getattr(self.keyboard_manager, 'active_list', None) == self:
                        self.keyboard_manager.clear_active_list()
                except: pass
            
            # 2. Liberar datos pesados
            self._all_data = []
            self._visible_rows = []
            
            # 3. Limpiar callbacks para romper posibles ciclos
            self.on_select_callback = None
            self.on_double_click_callback = None
            self.row_color_callback = None
            self.on_selection_change_callback = None
            self._on_return_callback = None
            
        except Exception:
            logger.exception("Error en destroy de VirtualNavList")
        finally:
            super().destroy()

    # ------------------------------------------------------------------
    # Ordenación por Cabecera
    # ------------------------------------------------------------------

    def _on_header_click(self, col_index):
        """Maneja el clic en la cabecera para ordenar."""
        col = self.columns[col_index]
        key = col['key']
        label_text = col['label']  # El texto visible en la cabecera (ej: 'ARTÍCULO', 'PVP')
        
        # Toggle dirección si clic en la misma columna
        if self._sort_column == key:
            self._sort_direction = 'desc' if self._sort_direction == 'asc' else 'asc'
        else:
            self._sort_column = key
            self._sort_direction = 'asc'
        
        # Ordenar los datos
        self._sort_data()
        
        # Actualizar indicadores visuales en cabeceras
        self._update_header_indicators()
        
        # Refrescar UI
        self._refresh_ui()

    def _sort_data(self):
        """Ordena _all_data según la columna y dirección actuales usando natural sort."""
        if not self._sort_column:
            return
        
        reverse = (self._sort_direction == 'desc')
        
        def natural_key(text):
            """Convierte texto en lista para ordenación natural (ej: 'OP 10' -> ['OP ', 10])."""
            if not isinstance(text, str):
                # Si no es string, intentar convertir a número directamente
                try:
                    return [float(text)]
                except (ValueError, TypeError):
                    return [str(text)]
            
            # Separar texto y números usando regex
            # Ejemplo: "OP 10" -> ['OP ', 10]
            # Ejemplo: "Producto 2 A" -> ['Producto ', 2, ' A']
            return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', text)]
        
        def sort_key(item):
            # 1. Criterio Principal
            sort_key_name = f"_sort_{self._sort_column}"
            primary_val = None
            if sort_key_name in item:
                val = item[sort_key_name]
                primary_val = [float(val)] if isinstance(val, (int, float, Decimal)) else natural_key(str(val))
            else:
                value = item.get(self._sort_column, '')
                if isinstance(value, (int, float, Decimal)):
                    primary_val = [float(value)]
                elif isinstance(value, str):
                    try:
                        primary_val = [float(value)]
                    except ValueError:
                        primary_val = natural_key(value)
                else:
                    primary_val = natural_key(str(value))

            # 2. Criterio Secundario (Agrupar por el primer campo, normalmente ARTÍCULO/NOMBRE)
            # Esto evita que registros con el mismo valor principal (ej: misma talla) salgan desordenados entre sí.
            secondary_column = self.columns[0]['key'] # La primera columna definida
            if secondary_column == self._sort_column and len(self.columns) > 1:
                secondary_column = self.columns[1]['key'] # Si ya estamos en la primera, usamos la segunda
            
            secondary_value = item.get(secondary_column, '')
            secondary_key = natural_key(str(secondary_value))

            return (primary_val, secondary_key)
        
        self._all_data.sort(key=sort_key, reverse=reverse)

    def _update_header_indicators(self):
        """Actualiza las flechas de ordenación en las cabeceras."""
        for i, col in enumerate(self.columns):
            key = col['key']
            label = col['label']
            if key == self._sort_column:
                arrow = ' ▲' if self._sort_direction == 'asc' else ' ▼'
                self._header_labels[i].configure(text=label + arrow)
            else:
                self._header_labels[i].configure(text=label)

    def _truncate(self, text: str, width_px: int) -> str:
        try:
            char_w = max(1, int(self._font_row[1] * 0.7)) # Estimación
            max_chars = max(1, (width_px - 10) // char_w)
            if len(text) > max_chars:
                return text[:max(1, max_chars - 1)] + '…'
        except: pass
        return text
