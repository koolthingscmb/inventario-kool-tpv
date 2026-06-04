"""UI de Exportar Albarán - PASO 3: Conectado con servicios.

Funcional:
- Cargar proveedores desde ProveedorService
- Buscar albaranes filtrados desde AlbaranService
- Selección múltiple con NavListMultiSelect

Pendiente: Exportación e impresión (PASOS 5-8)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.nav_list_multi_select import NavListMultiSelect
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.base_datos.albaran_service import AlbaranService

logger = logging.getLogger(__name__)


class ExportarAlbaranUI:
    """UI para exportar albaranes con filtros y selección múltiple."""

    def __init__(self, parent, db=None, on_close_callback=None):
        """Inicializar UI de exportación.

        Args:
            parent: Widget padre
            db: Conexión a base de datos
            on_close_callback: Función a llamar al cerrar
        """
        self.parent = parent
        self.db = db
        self.on_close_callback = on_close_callback

        # Colores
        try:
            self.colors = load_colors('almacen')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        # Fuentes
        self.font_config = load_font_config()
        self.title_font = ctk.CTkFont(
            family=self.font_config.get('title', {}).get('family', 'Inter'),
            size=self.font_config.get('title', {}).get('size', 18),
            weight=self.font_config.get('title', {}).get('weight', 'bold')
        )
        self.subtitle_font = ctk.CTkFont(
            family=self.font_config.get('subtitle', {}).get('family', 'Inter'),
            size=self.font_config.get('subtitle', {}).get('size', 14),
            weight=self.font_config.get('subtitle', {}).get('weight', 'bold')
        )
        self.label_font = ctk.CTkFont(
            family=self.font_config.get('default', {}).get('family', 'Inter'),
            size=self.font_config.get('default', {}).get('size', 12)
        )
        self.button_factory = ButtonFactory()

        # State
        self.proveedores_list: List[Dict[str, Any]] = []
        self.albaranes_data: List[Dict[str, Any]] = []
        self.proveedor_map: Dict[str, int] = {}  # nombre -> id

        # Servicios
        self.proveedor_service = ProveedorService(self.db) if self.db else None
        self.albaran_service = AlbaranService(self.db) if self.db else None

        # Crear ventana modal
        self._create_window()

        # Cargar datos iniciales
        self._load_proveedores()

    def _create_window(self):
        """Crear ventana modal."""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Exportar Albaranes")
        self.window.geometry("900x700")
        self.window.resizable(True, True)

        # Centrar ventana
        self.window.update_idletasks()
        width = 900
        height = 700
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.window, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._setup_ui()

        # Hacer modal
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _setup_ui(self):
        """Configurar UI completa."""
        # ===== TITULO =====
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="EXPORTAR ALBARANES",
            font=self.title_font,
            text_color=self.colors.get('text', COLOR_MATRIX)
        )
        title_label.pack(pady=(0, 10))

        # ===== SECCIÓN FILTROS =====
        filters_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        filters_frame.pack(fill="x", pady=5)

        # Fila 1: Proveedor y Fechas
        row1 = ctk.CTkFrame(filters_frame, fg_color="transparent")
        row1.pack(fill="x", pady=3)

        # Proveedor
        ctk.CTkLabel(
            row1,
            text="Proveedor:",
            font=self.label_font
        ).pack(side="left", padx=(0, 5))

        self.combo_proveedor = SearchableCombo(
            row1,
            width=250,
            height=30
        )
        self.combo_proveedor.pack(side="left", padx=5)

        # Fecha Desde
        ctk.CTkLabel(
            row1,
            text="Desde:",
            font=self.label_font
        ).pack(side="left", padx=(20, 5))

        self.date_desde = DatePickerEntry(row1, width=120)
        self.date_desde.pack(side="left", padx=5)
        # Default: hace 30 días
        fecha_inicio = datetime.now() - timedelta(days=30)
        self.date_desde.set_date(fecha_inicio.strftime("%d/%m/%Y"))

        # Fecha Hasta
        ctk.CTkLabel(
            row1,
            text="Hasta:",
            font=self.label_font
        ).pack(side="left", padx=(20, 5))

        self.date_hasta = DatePickerEntry(row1, width=120)
        self.date_hasta.pack(side="left", padx=5)
        # Default: hoy
        self.date_hasta.set_date(datetime.now().strftime("%d/%m/%Y"))

        # Fila 2: Botón Buscar
        row2 = ctk.CTkFrame(filters_frame, fg_color="transparent")
        row2.pack(fill="x", pady=10)

        self.btn_buscar = self.button_factory.create_button(
            row2,
            "buscar",
            command=self._on_buscar,
            width=120,
            height=32
        )
        self.btn_buscar.pack(side="left", padx=5)

        # ===== SECCIÓN RESULTADOS =====
        results_label = ctk.CTkLabel(
            self.main_frame,
            text="Albaranes encontrados:",
            font=self.subtitle_font,
            text_color=self.colors.get('text', COLOR_MATRIX)
        )
        results_label.pack(anchor="w", pady=(10, 5))

        # NavListMultiSelect
        list_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, pady=5)

        self.nav_list = NavListMultiSelect(
            list_frame,
            columns=["id", "num_albaran", "fecha", "proveedor_nombre", "total"],
            column_widths=[50, 100, 100, 250, 100],
            header_texts=["ID", "Nº Albarán", "Fecha", "Proveedor", "Total"],
            on_selection_change=self._on_selection_change,
            row_height=30
        )
        self.nav_list.pack(fill="both", expand=True)

        # ===== SECCIÓN BOTONES SELECCIÓN =====
        selection_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        selection_frame.pack(fill="x", pady=5)

        self.btn_sel_todos = self.button_factory.create_button(
            selection_frame,
            "seleccionar_todos",
            command=self._on_sel_todos,
            width=140,
            height=28
        )
        self.btn_sel_todos.pack(side="left", padx=5)

        self.btn_sel_ninguno = self.button_factory.create_button(
            selection_frame,
            "seleccionar_ninguno",
            command=self._on_sel_ninguno,
            width=140,
            height=28
        )
        self.btn_sel_ninguno.pack(side="left", padx=5)

        # Label de contador
        self.lbl_contador = ctk.CTkLabel(
            selection_frame,
            text="0 seleccionados",
            font=self.label_font
        )
        self.lbl_contador.pack(side="right", padx=10)

        # ===== SECCIÓN OPCIONES =====
        options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=10)

        # Checkbox Cabecera tienda
        self.chk_cabecera_tienda = ctk.CTkCheckBox(
            options_frame,
            text="Incluir cabecera de tienda",
            font=self.label_font
        )
        self.chk_cabecera_tienda.pack(side="left", padx=5)
        self.chk_cabecera_tienda.select()

        # Checkbox Agrupar por proveedor
        self.chk_agrupar_proveedor = ctk.CTkCheckBox(
            options_frame,
            text="Agrupar por proveedor (1 PDF)",
            font=self.label_font
        )
        self.chk_agrupar_proveedor.pack(side="left", padx=(30, 5))

        # ===== SECCIÓN BOTONES ACCIÓN =====
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.pack(fill="x", pady=(10, 0))

        self.btn_export_csv = self.button_factory.create_button(
            action_frame,
            "exportar_csv",
            command=self._on_export_csv,
            width=140,
            height=35
        )
        self.btn_export_csv.pack(side="left", padx=5)

        self.btn_export_pdf = self.button_factory.create_button(
            action_frame,
            "exportar_pdf",
            command=self._on_export_pdf,
            width=140,
            height=35
        )
        self.btn_export_pdf.pack(side="left", padx=5)

        self.btn_imprimir = self.button_factory.create_button(
            action_frame,
            "imprimir",
            command=self._on_imprimir,
            width=120,
            height=35
        )
        self.btn_imprimir.pack(side="left", padx=5)

        self.btn_cancelar = self.button_factory.create_button(
            action_frame,
            "cancelar",
            command=self._on_cancel,
            width=120,
            height=35
        )
        self.btn_cancelar.pack(side="right", padx=5)

    def _load_proveedores(self):
        """Cargar proveedores en el combo."""
        try:
            if not self.proveedor_service:
                logger.warning("No hay conexión a BD para cargar proveedores")
                return

            self.proveedores_list = self.proveedor_service.get_all_proveedores()

            # Crear lista de opciones (nombre, id) y mapeo inverso
            opciones = []
            self.proveedor_map = {}

            for prov in self.proveedores_list:
                nombre = prov.get('nombre', '')
                prov_id = prov.get('id')
                if nombre and prov_id:
                    opciones.append(nombre)
                    self.proveedor_map[nombre] = prov_id

            # Añadir opción "Todos" al inicio
            opciones.insert(0, "-- Todos --")
            self.proveedor_map["-- Todos --"] = None

            # Configurar combo en modo options
            self.combo_proveedor.set_values(opciones)
            self.combo_proveedor.set("-- Todos --")

            logger.info(f"Cargados {len(self.proveedores_list)} proveedores")

        except Exception as e:
            logger.exception(f"Error cargando proveedores: {e}")

    def _on_buscar(self):
        """Buscar albaranes con filtros."""
        try:
            if not self.albaran_service:
                self._show_error("No hay conexión a base de datos")
                return

            # Obtener proveedor seleccionado
            proveedor_nombre = self.combo_proveedor.get()
            proveedor_id = self.proveedor_map.get(proveedor_nombre)

            # Obtener fechas
            fecha_desde_str = self.date_desde.get_date()
            fecha_hasta_str = self.date_hasta.get_date()

            # Convertir fechas para filtro (formato DD/MM/YYYY -> YYYY-MM-DD)
            fecha_desde = self._parse_fecha(fecha_desde_str) if fecha_desde_str else None
            fecha_hasta = self._parse_fecha(fecha_hasta_str) if fecha_hasta_str else None

            logger.info(f"Buscando albaranes: prov={proveedor_id}, desde={fecha_desde}, hasta={fecha_hasta}")

            # Llamar al servicio con filtros
            albaranes = self.albaran_service.filtrar_albaranes(
                proveedor_id=proveedor_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )

            # Transformar datos para NavListMultiSelect
            self.albaranes_data = []
            for alb in albaranes:
                self.albaranes_data.append({
                    'id': alb.get('id', ''),
                    'num_albaran': alb.get('num_albaran', ''),
                    'fecha': alb.get('fecha', ''),
                    'proveedor_nombre': alb.get('proveedor_nombre', ''),
                    'total': f"{alb.get('total', 0):.2f}"
                })

            # Cargar en la lista
            self.nav_list.set_data(self.albaranes_data)

            logger.info(f"Encontrados {len(self.albaranes_data)} albaranes")

        except Exception as e:
            logger.exception(f"Error buscando albaranes: {e}")
            self._show_error(f"Error al buscar albaranes: {e}")

    def _parse_fecha(self, fecha_str: str) -> Optional[str]:
        """Convertir fecha de DD/MM/YYYY a YYYY-MM-DD para la BD.

        Args:
            fecha_str: Fecha en formato DD/MM/YYYY

        Returns:
            Fecha en formato YYYY-MM-DD o None si es inválida
        """
        try:
            if not fecha_str:
                return None
            dt = datetime.strptime(fecha_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Formato de fecha inválido: {fecha_str}")
            return None

    def _on_selection_change(self, selected_indices: List[int]):
        """Actualizar contador cuando cambia selección."""
        count = len(selected_indices)
        self.lbl_contador.configure(text=f"{count} seleccionados")

    def _on_sel_todos(self):
        """Seleccionar todos los albaranes."""
        self.nav_list.select_all()

    def _on_sel_ninguno(self):
        """Deseleccionar todos los albaranes."""
        self.nav_list.deselect_all()

    def _on_export_csv(self):
        """Exportar a CSV (placeholder - implementar en PASO 5)."""
        seleccionados = self.nav_list.get_selected_items()
        if not seleccionados:
            self._show_error("Selecciona al menos un albarán")
            return
        logger.info(f"Exportar {len(seleccionados)} albaranes a CSV - pendiente PASO 5")

    def _on_export_pdf(self):
        """Exportar a PDF (placeholder - implementar en PASO 6/7)."""
        seleccionados = self.nav_list.get_selected_items()
        if not seleccionados:
            self._show_error("Selecciona al menos un albarán")
            return
        agrupar = self.chk_agrupar_proveedor.get()
        logger.info(f"Exportar {len(seleccionados)} albaranes a PDF (agrupar={agrupar}) - pendiente PASO 6/7")

    def _on_imprimir(self):
        """Imprimir (placeholder - implementar en PASO 8)."""
        seleccionados = self.nav_list.get_selected_items()
        if not seleccionados:
            self._show_error("Selecciona al menos un albarán")
            return
        logger.info(f"Imprimir {len(seleccionados)} albaranes - pendiente PASO 8")

    def _on_cancel(self):
        """Cerrar ventana."""
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()

    def _show_error(self, message: str):
        """Mostrar mensaje de error."""
        # TODO: Usar messagebox o dialogo personalizado
        logger.error(message)

    def show(self):
        """Mostrar ventana modal."""
        self.window.wait_window()
