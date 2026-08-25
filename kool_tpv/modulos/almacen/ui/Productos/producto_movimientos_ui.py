import logging
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from kool_tpv.modulos.almacen.services.stock_movement_service import StockMovementService
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX

logger = logging.getLogger(__name__)

class ProductoMovimientosUI:
    def __init__(self, parent, db, producto_id: int, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.producto_id = producto_id
        self.module_name = module_name
        
        self.service = StockMovementService(db)
        
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        # Frame principal
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        # Título / Info superior
        self.header_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.header_frame.pack(fill='x', padx=12, pady=10)
        
        # Intentar obtener nombre del producto para el título
        nombre_prod = "Producto"
        try:
            res = self.db.fetch_one("SELECT nombre FROM productos WHERE id = ?", (producto_id,))
            if res:
                nombre_prod = res[0]
        except: pass
        
        ctk.CTkLabel(
            self.header_frame, 
            text=f"HISTORIAL DE MOVIMIENTOS: {nombre_prod.upper()}", 
            font=get_font('header', module='almacen'),
            text_color=self.colors.get('text', COLOR_MATRIX)
        ).pack(side='left')

        # Lista Virtualizada
        self._setup_list()
        
        # Cargar datos
        self.cargar_datos()

    def _setup_list(self):
        """Configura la VirtualNavList para mostrar los movimientos."""
        columns = [
            ('FECHA', 180),
            ('CANTIDAD', 100),
            ('MOTIVO', 400, True), # Expandible
            ('USUARIO', 150)
        ]
        
        self.nav_list = VirtualNavList(
            self.container,
            columns=columns,
            module_name=self.module_name
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=(0, 12))

    def cargar_datos(self):
        """Carga los movimientos del producto en la lista."""
        movements = self.service.obtener_historial_producto(self.producto_id)
        
        items = []
        for m in movements:
            cantidad = m['cantidad']
            # Color según si suma o resta
            row_fg = "#2ECC71" if cantidad > 0 else "#E74C3C" if cantidad < 0 else self.colors.get('text', COLOR_MATRIX)
            
            items.append({
                'FECHA': m['created_at'],
                'CANTIDAD': f"{'+' if cantidad > 0 else ''}{cantidad}",
                'MOTIVO': m['motivo'] or '-',
                'USUARIO': m['usuario_nombre'],
                '_row_fg': row_fg # Aplicar color a la fila
            })
            
        self.nav_list.set_items(items)

    def get_widget(self):
        return self.container
