"""UI para consultar albaranes de un proveedor en el módulo de Producción."""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import Optional

from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.base_datos.albaran_service import AlbaranService

logger = logging.getLogger(__name__)

class ProduccionConsultarAlbaranesUI:
    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner
        self.albaran_service = AlbaranService(db)

        try:
            self.colors = load_colors('produccion')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL, 'primary': COLOR_MATRIX}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        self._setup_ui()
        self._cargar_albaranes()

    def _setup_ui(self):
        font_config = load_font_config()
        self.title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        self.label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container, 
            text=f"ALBARANES DEL PROVEEDOR: {self.proveedor_nombre.upper()}",
            text_color=self.colors.get('primary', COLOR_MATRIX),
            font=(self.title_font['family'], self.title_font['size'], self.title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(20, 10))

        # Tabla de Albaranes
        self.columns = [
            ('ID', 80), 
            ('FECHA', 120), 
            ('NÚMERO', 150), 
            ('TIPO', 150), 
            ('UDS', 100), 
            ('TOTAL', 150)
        ]
        
        root = self.container.winfo_toplevel()
        km = getattr(root, 'keyboard_manager', None)
        
        self.nav_list = VirtualNavList(
            self.container, 
            columns=self.columns, 
            module_name='produccion',
            keyboard_manager=km,
            on_double_click=self._on_albaran_double_click
        )
        self.nav_list.pack(fill='both', expand=True, padx=40, pady=20)

        # Footer
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(fill='x', side='bottom', padx=40, pady=20)

        self.btn_volver = ButtonFactory.create_button(
            parent=footer,
            text='VOLVER',
            command=self._on_volver_click,
            module='produccion',
            palette_key='primary',
            style_key='action_secondary'
        )
        self.btn_volver.pack(side='left')

        self.btn_editar = ButtonFactory.create_button(
            parent=footer,
            text='EDITAR / VER DETALLE',
            command=self._on_editar_click,
            module='produccion',
            palette_key='secondary',
            style_key='action_secondary'
        )
        self.btn_editar.pack(side='right')

    def _cargar_albaranes(self):
        """Cargar albaranes del proveedor usando el service."""
        try:
            albaranes = self.albaran_service.filtrar_albaranes(
                proveedor_id=self.proveedor_id,
                limit=100
            )
            
            rows = []
            for alb in albaranes:
                rows.append({
                    'ID': str(alb.get('id', '')),
                    'FECHA': alb.get('fecha', ''),
                    'NÚMERO': str(alb.get('num_albaran', '')),
                    'TIPO': alb.get('tipo', ''),
                    'UDS': str(alb.get('cant_productos', 0)),
                    'TOTAL': f"{alb.get('total', 0.0):.2f}€",
                    '_id': alb.get('id')
                })
            
            self.nav_list.set_items(rows)
            
        except Exception:
            logger.exception("Error cargando albaranes de producción")

    def _on_albaran_double_click(self, data):
        self._editar_albaran(data.get('_id'))

    def _on_editar_click(self):
        idx = self.nav_list.get_selected_index()
        if idx is not None:
            data = self.nav_list._all_data[idx]
            self._editar_albaran(data.get('_id'))

    def _editar_albaran(self, albaran_id):
        if not albaran_id: return
        if self.owner and hasattr(self.owner, 'show_entrada_manual_produccion'):
            self.owner.show_entrada_manual_produccion(
                proveedor_id=self.proveedor_id,
                proveedor_nombre=self.proveedor_nombre,
                albaran_id=albaran_id
            )

    def _on_volver_click(self):
        if self.owner and hasattr(self.owner, 'show_proveedores'):
            self.owner.show_proveedores()

    def get_widget(self):
        return self.container
