import logging
import customtkinter as ctk
from typing import Optional, Dict, Any

from kool_tpv.base_datos.audit_repository import AuditRepository
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.utils import COLOR_BG_TERMINAL

logger = logging.getLogger(__name__)

class AuditLogsUI:
    def __init__(self, parent, db, module_name: str = 'config', keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.keyboard_manager = keyboard_manager
        
        self.repository = AuditRepository(db)
        
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': '#FFFFFF', 'background': COLOR_BG_TERMINAL}

        # Frame principal
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        # Barra de filtros
        self.filter_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.filter_frame.pack(fill='x', padx=12, pady=10)
        
        self._setup_filters()
        
        # Lista Virtualizada
        self._setup_list()
        
        # Cargar datos iniciales
        self.ejecutar_busqueda()

    def _setup_filters(self):
        """Configura la barra superior de filtros."""
        # Columna de Entidad
        entidades = ["TODAS"] + self.repository.obtener_entidades()
        ctk.CTkLabel(self.filter_frame, text="ENTIDAD:", font=get_font('label', module='config'), text_color="#FFFFFF").pack(side='left', padx=(0, 5))
        self.cb_entidad = ctk.CTkComboBox(self.filter_frame, values=entidades, width=140, font=get_font('entry', module='config'))
        self.cb_entidad.set("TODAS")
        self.cb_entidad.pack(side='left', padx=(0, 15))

        # Columna de Acción
        acciones = ["TODAS"] + self.repository.obtener_acciones()
        ctk.CTkLabel(self.filter_frame, text="ACCIÓN:", font=get_font('label', module='config'), text_color="#FFFFFF").pack(side='left', padx=(0, 5))
        self.cb_accion = ctk.CTkComboBox(self.filter_frame, values=acciones, width=140, font=get_font('entry', module='config'))
        self.cb_accion.set("TODAS")
        self.cb_accion.pack(side='left', padx=(0, 15))

        # Fecha Inicio
        ctk.CTkLabel(self.filter_frame, text="DESDE:", font=get_font('label', module='config'), text_color="#FFFFFF").pack(side='left', padx=(0, 5))
        self.dp_inicio = DatePickerEntry(
            self.filter_frame, 
            module_name=self.module_name, 
            width=120,
            default_mode='first_day_of_month'
        )
        self.dp_inicio.pack(side='left', padx=(0, 15))

        # Fecha Fin
        ctk.CTkLabel(self.filter_frame, text="HASTA:", font=get_font('label', module='config'), text_color="#FFFFFF").pack(side='left', padx=(0, 5))
        self.dp_fin = DatePickerEntry(
            self.filter_frame, 
            module_name=self.module_name, 
            width=120,
            default_mode='today'
        )
        self.dp_fin.pack(side='left', padx=(0, 15))

        # Botón Buscar
        self.btn_buscar = ButtonFactory.create_button(
            self.filter_frame,
            text="BUSCAR",
            command=self.ejecutar_busqueda,
            module="config",
            palette_key="primary",
            style_key="action_success",
            width=100
        )
        self.btn_buscar.pack(side='left', padx=10)

        # Botón Limpiar
        self.btn_limpiar = ButtonFactory.create_button(
            self.filter_frame,
            text="LIMPIAR",
            command=self.limpiar_filtros,
            module="config",
            palette_key="secondary",
            style_key="action_success",
            width=100
        )
        self.btn_limpiar.pack(side='left')

    def _setup_list(self):
        """Configura la VirtualNavList para mostrar los logs."""
        columns = [
            ('FECHA', 180),
            ('ENTIDAD', 120),
            ('ID', 60),
            ('ACCIÓN', 180),
            ('USUARIO', 120),
            ('DETALLES (PREVIO/NUEVO)', 400, True) # Expandible
        ]
        
        self.nav_list = VirtualNavList(
            self.container,
            columns=columns,
            module_name=self.module_name,
            keyboard_manager=self.keyboard_manager,
            on_double_click=self._on_log_double_click
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=(0, 12))

    def ejecutar_busqueda(self):
        """Recopila filtros y actualiza la lista."""
        filters = {}
        
        entidad = self.cb_entidad.get()
        if entidad != "TODAS":
            filters['entidad'] = entidad
            
        accion = self.cb_accion.get()
        if accion != "TODAS":
            filters['accion'] = accion
            
        f_inicio = self.dp_inicio.get()
        if f_inicio:
            filters['fecha_inicio'] = f_inicio
            
        f_fin = self.dp_fin.get()
        if f_fin:
            filters['fecha_fin'] = f_fin
            
        logs = self.repository.fetch_logs(filters)
        
        items = []
        for l in logs:
            # Combinar datos previos y nuevos para la columna de detalles
            detalles = ""
            if l['datos_previos']:
                detalles += f"PREVIO: {l['datos_previos']} "
            if l['datos_nuevos']:
                detalles += f"NUEVO: {l['datos_nuevos']}"
            
            items.append({
                'FECHA': l['created_at'],
                'ENTIDAD': l['entidad'],
                'ID': str(l['entidad_id'] or ''),
                'ACCIÓN': l['accion'],
                'USUARIO': l['usuario_nombre'],
                'DETALLES (PREVIO/NUEVO)': detalles.strip(),
                '_raw': l # Guardar objeto completo para el doble clic
            })
            
        self.nav_list.set_items(items)

    def limpiar_filtros(self):
        """Resetea los filtros y recarga."""
        import datetime
        today = datetime.date.today()
        first_day = today.replace(day=1)
        
        self.cb_entidad.set("TODAS")
        self.cb_accion.set("TODAS")
        self.dp_inicio.set(first_day.isoformat())
        self.dp_fin.set(today.isoformat())
        self.ejecutar_busqueda()

    def _on_log_double_click(self, item):
        """Muestra detalles completos del log en un diálogo (opcional por ahora)."""
        # Por ahora solo logueamos, podríamos abrir un popup con el JSON formateado
        logger.info(f"Log seleccionado: {item.get('FECHA')} - {item.get('ACCIÓN')}")

    def get_widget(self):
        return self.container
