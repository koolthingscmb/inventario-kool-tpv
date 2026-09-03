"""Vista de filtros para exportación - Pantalla 1."""
import logging
from datetime import datetime, timedelta
from typing import Callable, List, Dict, Any, Optional

import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin
from kool_tpv.base_datos.proveedor_service import ProveedorService

logger = logging.getLogger(__name__)


class VistaFiltros(ctk.CTkFrame, KeyboardNavigableMixin):
    """Pantalla 1: Filtros de búsqueda (proveedor + fechas + botón BUSCAR)."""

    def __init__(
        self,
        parent,
        db,
        on_buscar_callback: Callable[[Optional[int], str, str], None],
        on_cancelar_callback: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)

        self.db = db
        self.on_buscar_callback = on_buscar_callback
        self.on_cancelar_callback = on_cancelar_callback

        # Services
        self.proveedor_service = ProveedorService(db) if db else None

        # Config
        self.colors = load_colors('almacen')
        self.fonts = load_font_config()
        self.button_factory = ButtonFactory()

        # Datos
        self.proveedores_list: List[Dict[str, Any]] = []
        self.selected_chip = None

        self._setup_ui()
        self._cargar_proveedores()
        self._setup_keyboard_nav()

    def _setup_ui(self):
        """Construir interfaz de filtros."""
        self.configure(fg_color=self.colors.get('background', '#2B2B2B'))

        # Layout vertical: título, fechas, proveedor label, chips, botones
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Título
        self.grid_rowconfigure(1, weight=0)  # Fechas
        self.grid_rowconfigure(2, weight=0)  # Label proveedor
        self.grid_rowconfigure(3, weight=0)  # Chips proveedores
        self.grid_rowconfigure(4, weight=0)  # Botones
        self.grid_rowconfigure(5, weight=1)  # Espacio

        # Título
        title_font = self.fonts.get('title', {})
        self.lbl_titulo = ctk.CTkLabel(
            self,
            text="EXPORTAR ALBARANES",
            font=(
                title_font.get('family', 'Arial'),
                title_font.get('size', 24),
                title_font.get('weight', 'bold')
            ),
            text_color=self.colors.get('primary', '#1F6AA5')
        )
        self.lbl_titulo.grid(row=0, column=0, pady=(20, 30), padx=20)

        # Label font
        label_font = self.fonts.get('body', {})
        label_font_tuple = (
            label_font.get('family', 'Arial'),
            label_font.get('size', 14),
            label_font.get('weight', 'normal')
        )

        # --- Fila de fechas: Desde y Hasta en la misma fila ---
        self.frame_fechas = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_fechas.grid(row=1, column=0, padx=40, pady=(10, 5), sticky='ew')

        self.lbl_desde = ctk.CTkLabel(
            self.frame_fechas,
            text="Desde:",
            font=label_font_tuple,
            text_color=self.colors.get('text', '#FFFFFF')
        )
        self.lbl_desde.pack(side='left', padx=(0, 5))

        self.entry_desde = DatePickerEntry(
            self.frame_fechas,
            width=150,
            height=35
        )
        self.entry_desde.pack(side='left', padx=(0, 30))
        fecha_desde_default = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.entry_desde.set(fecha_desde_default)

        self.lbl_hasta = ctk.CTkLabel(
            self.frame_fechas,
            text="Hasta:",
            font=label_font_tuple,
            text_color=self.colors.get('text', '#FFFFFF')
        )
        self.lbl_hasta.pack(side='left', padx=(0, 5))

        self.entry_hasta = DatePickerEntry(
            self.frame_fechas,
            width=150,
            height=35
        )
        self.entry_hasta.pack(side='left')
        fecha_hasta_default = datetime.now().strftime('%Y-%m-%d')
        self.entry_hasta.set(fecha_hasta_default)

        # --- Chips de proveedor a todo el ancho ---
        self.lbl_proveedor = ctk.CTkLabel(
            self,
            text="Proveedor:",
            font=label_font_tuple,
            text_color=self.colors.get('text', '#FFFFFF')
        )
        self.lbl_proveedor.grid(row=2, column=0, padx=40, pady=(10, 5), sticky='w')

        self.chips_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=self.colors.get('surface', '#333333'),
            height=100
        )
        self.chips_frame.grid(row=3, column=0, padx=40, pady=(0, 15), sticky='ew')

        # Frame botones
        self.frame_botones = ctk.CTkFrame(
            self,
            fg_color='transparent'
        )
        self.frame_botones.grid(row=4, column=0, pady=30)

        # Botón BUSCAR - usando ButtonFactory
        self.btn_buscar = self.button_factory.create_button(
            parent=self.frame_botones,
            style_key='action_primary',
            text='BUSCAR',
            command=self._on_buscar,
            module='almacen',
            palette_key='primary'
        )
        self.btn_buscar.pack(side='left', padx=10)

        # Botón CANCELAR - usando ButtonFactory
        if self.on_cancelar_callback:
            self.btn_cancelar = self.button_factory.create_button(
                parent=self.frame_botones,
                style_key='action_secondary',
                text='CANCELAR',
                command=self._on_cancelar,
                module='almacen',
                palette_key='accent'
            )
            self.btn_cancelar.pack(side='left', padx=10)

    def _cargar_proveedores(self):
        """Cargar chips de proveedores."""
        if not self.proveedor_service:
            logger.warning("No hay proveedor_service")
            return

        try:
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            proveedores = self.proveedor_service.get_all_proveedores() or []

            # Chip "Todos"
            btn_todos = ButtonFactory.create_button(
                parent=self.chips_frame,
                text='-- Todos --',
                command=None,
                style_key='chip_selected'
            )
            btn_todos.grid(row=0, column=0, padx=4, pady=4, sticky='w')
            btn_todos.bind('<Button-1>', lambda e, b=btn_todos: self._select_chip(b))
            setattr(btn_todos, '_prov_data', {'id': None, 'nombre': '-- Todos --'})
            self.selected_chip = btn_todos

            for i, p in enumerate(proveedores):
                col = (i + 1) % 4
                row = (i + 1) // 4
                btn = ButtonFactory.create_button(
                    parent=self.chips_frame,
                    text=p.get('nombre', ''),
                    command=None,
                    style_key='chip_default'
                )
                btn.grid(row=row, column=col, padx=4, pady=4, sticky='w')
                btn.bind('<Button-1>', lambda e, b=btn: self._select_chip(b))
                setattr(btn, '_prov_data', p)

            logger.info(f"Cargados {len(proveedores)} proveedores")

        except Exception:
            logger.exception("Error cargando proveedores")

    def _select_chip(self, btn):
        """Seleccionar chip de proveedor."""
        try:
            if self.selected_chip is not None:
                ButtonFactory.apply_style(self.selected_chip, 'chip_default')
            self.selected_chip = btn
            ButtonFactory.apply_style(btn, 'chip_selected')
        except Exception:
            logger.exception('Error seleccionando chip de proveedor')

    def _get_proveedor_seleccionado(self) -> Optional[int]:
        """Obtener ID del proveedor seleccionado."""
        try:
            if self.selected_chip is not None:
                return self.selected_chip._prov_data.get('id')
        except Exception:
            pass
        return None

    def _parse_fecha(self, fecha_str: str) -> str:
        """Convertir fecha de DD/MM/YYYY a YYYY-MM-DD."""
        try:
            return datetime.strptime(fecha_str, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            return fecha_str

    def _on_buscar(self):
        """Callback al pulsar BUSCAR."""
        proveedor_id = self._get_proveedor_seleccionado()
        fecha_desde = self._parse_fecha(self.entry_desde.get())
        fecha_hasta = self._parse_fecha(self.entry_hasta.get())

        logger.info(f"Buscando: proveedor={proveedor_id}, desde={fecha_desde}, hasta={fecha_hasta}")

        if self.on_buscar_callback:
            self.on_buscar_callback(proveedor_id, fecha_desde, fecha_hasta)

    def _on_cancelar(self):
        """Callback al pulsar CANCELAR."""
        if self.on_cancelar_callback:
            self.on_cancelar_callback()

    def _setup_keyboard_nav(self):
        """Configurar navegación por teclado via KeyboardNavigableMixin."""
        self._navigable_buttons = [
            (self.entry_desde, self.entry_desde._open_calendar),
            (self.entry_hasta, self.entry_hasta._open_calendar),
            (self.btn_buscar, self._on_buscar),
        ]
        if hasattr(self, 'btn_cancelar'):
            self._navigable_buttons.append((self.btn_cancelar, self._on_cancelar))

        self._setup_keyboard_navigation()
