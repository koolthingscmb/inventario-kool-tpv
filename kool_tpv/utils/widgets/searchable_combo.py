"""SearchableCombo PROFESIONAL - Versión unificada con búsqueda dinámica integrada.

Soporta 3 modos:

values: Lista simple de strings
options: Lista de tuplas [(id, nombre), …]
search_function: Función de búsqueda dinámica que devuelve [{id, nombre_display, …}, …]
Funciona IGUAL en Windows, Mac y Linux.
"""
from typing import List, Optional, Tuple, Callable
import logging
import tkinter as tk
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL


class SearchableCombo(ctk.CTkFrame):
    """Entry + dropdown con filtrado local o búsqueda dinámica.

    Modos de uso:
    - Simple: SearchableCombo(parent, values=['A', 'B', 'C'])
    - Con IDs: SearchableCombo(parent, options=[(1, 'A'), (2, 'B')])
    - Dinámico: SearchableCombo(parent, search_function=mi_funcion_busqueda)
    """

    def __init__(
        self,
        master,
        values: Optional[List[str]] = None,
        options: Optional[List[Tuple[int, str]]] = None,
        search_function: Optional[Callable[[str], List[dict]]] = None,
        command: Optional[Callable] = None,
        placeholder: str = '',
        width: int = 240,
        **kwargs
    ):
        """Constructor unificado SearchableCombo.

        Args:
            master: Widget padre
            values: Lista strings (modo simple)
            options: Lista tuplas [(id, nombre), ...] (modo con IDs)
            search_function: Función(texto) -> [{id, nombre_display, ...}] (modo dinámico)
            command: Callback al seleccionar (recibe string seleccionado)
            placeholder: Texto placeholder del entry
            width: Ancho del entry
        """
        super().__init__(master, **kwargs)

        # Modo de operación
        self.search_function = search_function
        self._command = command
        self._last_results = []  # Cache para resultados dinámicos

        # Inicializar valores según modo
        if search_function:
            # Modo dinámico: sin valores iniciales
            self._values = []
            self._opts = None
            self._names = []
            self._mapping = {}
        elif options is not None:
            # Modo tuplas con IDs
            self._opts = list(options)
            self._names = [n for (_id, n) in self._opts]
            self._mapping = {n: _id for (_id, n) in self._opts}
            self._values = self._names
        else:
            # Modo simple strings
            self._values = list(values or [])
            self._opts = None
            self._names = self._values
            self._mapping = {}

        self._var = tk.StringVar()

        # Entry
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            width=width,
            fg_color=COLOR_BG_TERMINAL,
            text_color=COLOR_MATRIX,
            border_color=COLOR_MATRIX,
            font=FONT_TERMINAL
        )
        self.entry.pack(fill='x', expand=True)

        # Placeholder
        if placeholder:
            try:
                self.entry.configure(placeholder_text=placeholder)
            except Exception:
                pass

        self._dropdown = None

        # Event bindings CROSS-PLATFORM (Windows + Mac + Linux)
        self.entry.bind('<KeyRelease>', self._on_key)
        self.entry.bind('<Down>', self._on_down)
        self.entry.bind('<Up>', self._on_up)
        self.entry.bind('<Return>', self._on_return_key)
        self.entry.bind('<FocusOut>', self._on_focus_out)

    # --- Properties ---
    @property
    def values(self) -> List[str]:
        return self._values

    @values.setter
    def values(self, v: List[str]):
        self._values = list(v or [])
        self._names = self._values

    # --- API Pública ---
    def set(self, value: str):
        try:
            self._var.set('' if value is None else str(value))
        except Exception:
            logging.exception('Error in SearchableCombo.set')

    def get(self) -> str:
        try:
            return self._var.get()
        except Exception:
            return ''

    def clear(self):
        try:
            self._var.set('')
        except Exception:
            pass

    def get_id(self) -> Optional[int]:
        """Obtener ID del elemento seleccionado.

        Funciona en modo options y search_function.
        Returns None en modo values simple o si no hay match.
        """
        try:
            name = self.get().strip()

            # Modo search_function: buscar en _last_results
            if self.search_function and self._last_results:
                for r in self._last_results:
                    if r.get('nombre_display') == name:
                        return r.get('id')
                return None

            # Modo options: usar mapping
            if self._mapping:
                return self._mapping.get(name)

            return None
        except Exception:
            logging.exception('Error en SearchableCombo.get_id')
            return None

    def set_options(self, options: List[Tuple[int, str]]):
        """Actualizar opciones (modo tuplas con IDs)."""
        try:
            self._opts = list(options or [])
            self._names = [n for (_id, n) in self._opts]
            self._mapping = {n: _id for (_id, n) in self._opts}
            self._values = self._names
        except Exception:
            logging.exception('Error en SearchableCombo.set_options')

    def get_producto_data(self) -> Optional[dict]:
        """Obtener datos completos del producto seleccionado.

        Solo funciona en modo search_function.
        Returns el dict completo del resultado seleccionado o None.
        """
        try:
            if not self.search_function or not self._last_results:
                return None

            name = self.get().strip()
            for r in self._last_results:
                if r.get('nombre_display') == name:
                    return r
            return None
        except Exception:
            logging.exception('Error en get_producto_data')
            return None

    # --- Event Handlers ---
    def _on_key(self, event=None):
        """Manejar teclas: filtrado local o búsqueda dinámica."""
        try:
            # IGNORAR teclas de navegación
            if event is not None:
                keysym = getattr(event, 'keysym', '').lower()
                if keysym in ('up', 'down', 'return', 'escape', 'tab', 'left', 'right'):
                    return

            txt = self.get().strip()

            # MODO SEARCH_FUNCTION: búsqueda dinámica
            if self.search_function:
                if len(txt) < 2:
                    self._hide_dropdown()
                    return

                try:
                    resultados = self.search_function(txt)
                except Exception:
                    logging.exception('Error ejecutando search_function')
                    resultados = []

                self._last_results = resultados or []
                matches = [r.get('nombre_display') for r in self._last_results if r.get('nombre_display')]

                if matches:
                    self._show_dropdown(matches)
                else:
                    self._hide_dropdown()
                return

            # MODO LOCAL: filtrado en memoria
            try:
                matches = [v for v in self._values if txt.lower() in v.lower()]
            except Exception:
                matches = list(self._values)

            if matches:
                self._show_dropdown(matches)
            else:
                self._hide_dropdown()

        except Exception:
            logging.exception('Error en _on_key')

    def _on_down(self, event=None):
        """Flecha abajo: abre dropdown o navega."""
        try:
            txt = self.get().strip()

            # Si dropdown no visible, abrirlo
            if not (self._dropdown and getattr(self._dropdown, 'winfo_exists', lambda: False)()):
                # Determinar qué mostrar
                if self.search_function:
                    # Modo dinámico: si no hay resultados, no abrir
                    if not self._last_results:
                        return 'break'
                    matches = [r.get('nombre_display') for r in self._last_results if r.get('nombre_display')]
                else:
                    # Modo local: filtrar o mostrar todo
                    if txt == '':
                        matches = list(self._values)
                    else:
                        matches = [v for v in self._values if txt.lower() in v.lower()]

                if not matches:
                    return 'break'

                self._show_dropdown(matches)
                lb = self._dropdown.listbox
                idx = 0
                lb.selection_clear(0, 'end')
                lb.selection_set(idx)
                lb.activate(idx)
                lb.see(idx)
                try:
                    self._var.set(lb.get(idx))
                except Exception:
                    pass
                return 'break'

            # Dropdown visible: navegar hacia abajo
            lb = self._dropdown.listbox
            size = lb.size()
            if size == 0:
                return 'break'

            sel = lb.curselection()
            idx = 0 if not sel else min(size - 1, sel[0] + 1)

            lb.selection_clear(0, 'end')
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
            try:
                self._var.set(lb.get(idx))
            except Exception:
                pass

            return 'break'
        except Exception:
            logging.exception('Error handling Down key')
            return 'break'

    def _on_up(self, event=None):
        """Flecha arriba: abre dropdown o navega."""
        try:
            txt = self.get().strip()

            # Si dropdown no visible, abrirlo
            if not (self._dropdown and getattr(self._dropdown, 'winfo_exists', lambda: False)()):
                # Determinar qué mostrar
                if self.search_function:
                    if not self._last_results:
                        return 'break'
                    matches = [r.get('nombre_display') for r in self._last_results if r.get('nombre_display')]
                else:
                    if txt == '':
                        matches = list(self._values)
                    else:
                        matches = [v for v in self._values if txt.lower() in v.lower()]

                if not matches:
                    return 'break'

                self._show_dropdown(matches)
                lb = self._dropdown.listbox
                idx = max(0, lb.size() - 1)
                lb.selection_clear(0, 'end')
                lb.selection_set(idx)
                lb.activate(idx)
                lb.see(idx)
                try:
                    self._var.set(lb.get(idx))
                except Exception:
                    pass
                return 'break'

            # Dropdown visible: navegar hacia arriba
            lb = self._dropdown.listbox
            size = lb.size()
            if size == 0:
                return 'break'

            sel = lb.curselection()
            idx = size - 1 if not sel else max(0, sel[0] - 1)

            lb.selection_clear(0, 'end')
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
            try:
                self._var.set(lb.get(idx))
            except Exception:
                pass

            return 'break'
        except Exception:
            logging.exception('Error handling Up key')
            return 'break'

    def _on_return_key(self, event=None):
        """Enter: confirmar selección."""
        try:
            if self._dropdown and getattr(self._dropdown, 'winfo_exists', lambda: False)():
                lb = self._dropdown.listbox
                sel = lb.curselection()
                if sel:
                    value = lb.get(sel[0])
                    self.set(value)
                    self._hide_dropdown()

                    # Disparar eventos
                    try:
                        self.entry.event_generate('<<SearchableComboSelected>>')
                    except Exception:
                        pass

                    if callable(self._command):
                        try:
                            self._command(value)
                        except Exception:
                            logging.exception('Error ejecutando command')

                    try:
                        self.entry.focus_set()
                    except Exception:
                        pass
                    return 'break'
        except Exception:
            logging.exception('Error handling Return key')
            return 'break'

    def _on_focus_out(self, event=None):
        try:
            self.after(120, self._delay_hide_if_focus_outside)
        except Exception:
            pass

    def _delay_hide_if_focus_outside(self):
        try:
            cur = None
            try:
                top = self.winfo_toplevel()
                cur = top.focus_get()
            except Exception:
                cur = None

            if self._dropdown and getattr(self._dropdown, 'winfo_exists', lambda: False)():
                try:
                    lb = self._dropdown.listbox
                    if cur is lb or (hasattr(cur, 'master') and getattr(cur, 'master', None) is lb):
                        return
                except Exception:
                    pass
            self._hide_dropdown()
        except Exception:
            pass

    def _show_dropdown(self, items: List[str]):
        try:
            if self._dropdown is None or not self._dropdown.winfo_exists():
                self._dropdown = tk.Toplevel(self)
                self._dropdown.wm_overrideredirect(True)
                self._dropdown.attributes('-topmost', True)
                self._dropdown.configure(bg=COLOR_BG_TERMINAL)

                lb = tk.Listbox(
                    self._dropdown,
                    activestyle='dotbox',
                    bg=COLOR_BG_TERMINAL,
                    fg=COLOR_MATRIX,
                    selectbackground='#03519F',
                    selectforeground='white',
                    highlightthickness=0,
                    bd=0
                )
                lb.pack(side='left', fill='both', expand=True)
                lb.bind('<<ListboxSelect>>', self._on_select)
                lb.bind('<Return>', self._on_select)
                lb.bind('<Double-Button-1>', self._on_select)
                self._dropdown.listbox = lb

            lb = self._dropdown.listbox
            lb.delete(0, 'end')
            for it in items:
                lb.insert('end', it)

            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            w = self.entry.winfo_width()
            self._dropdown.geometry(f"{w}x150+{x}+{y}")
            self._dropdown.deiconify()
        except Exception:
            logging.exception('Error mostrando dropdown')

    def _hide_dropdown(self):
        try:
            if self._dropdown and self._dropdown.winfo_exists():
                self._dropdown.withdraw()
        except Exception:
            pass

    def _on_select(self, event=None):
        """Selección desde listbox (click o Enter)."""
        try:
            if not (self._dropdown and getattr(self._dropdown, 'winfo_exists', lambda: False)()):
                return 'break'

            lb = self._dropdown.listbox
            sel = lb.curselection()
            if not sel:
                return 'break'

            value = lb.get(sel[0])
            self.set(value)
            self._hide_dropdown()

            try:
                self.entry.focus_set()
            except Exception:
                pass

            if callable(self._command):
                try:
                    self._command(value)
                except Exception:
                    logging.exception('Error ejecutando command')

            try:
                self.entry.event_generate('<<SearchableComboSelected>>')
            except Exception:
                pass

            return 'break'
        except Exception:
            logging.exception('Error en selección')
