import logging
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from kool_tpv.base_datos.stock_movement_service import StockMovementService
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.dialogs import show_error
from kool_tpv.utils.templates.pagina_con_visor import PaginaConVisor
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService

logger = logging.getLogger(__name__)

class ProductoMovimientosUI(PaginaConVisor):
    def __init__(self, parent, db, producto_id: int, module_name: str = 'almacen', owner=None, keyboard_manager=None):
        self.producto_id = producto_id
        self.owner = owner
        self.keyboard_manager = keyboard_manager
        self.service = StockMovementService(db)
        
        # Heredar de plantilla (esto llama a _build_header, _build_grid y _build_footer)
        super().__init__(parent, db=db, module_name=module_name)
        
        # Cargar datos iniciales
        self.cargar_datos()

    def _build_header(self):
        """Implementar cabecera con el título del producto."""
        # Intentar obtener nombre del producto
        nombre_prod = "Producto"
        try:
            res = self.db.fetch_one("SELECT nombre FROM productos WHERE id = ?", (self.producto_id,))
            if res:
                nombre_prod = res[0]
        except: pass
        
        ctk.CTkLabel(
            self.header, 
            text=f"HISTORIAL DE MOVIMIENTOS: {nombre_prod.upper()}", 
            font=get_font('header', module='almacen'),
            text_color=self.colors.get('text', COLOR_MATRIX)
        ).pack(side='left', padx=12, pady=10)

        # Resumen de Stock a la derecha
        self.summary_frame = ctk.CTkFrame(self.header, fg_color='transparent')
        self.summary_frame.pack(side='right', padx=20, pady=10)

        self.lbl_entradas = ctk.CTkLabel(self.summary_frame, text="Entradas: +0", text_color="#2ECC71", font=get_font('small_bold', module='almacen'))
        self.lbl_entradas.pack(side='left', padx=10)

        self.lbl_salidas = ctk.CTkLabel(self.summary_frame, text="Salidas: -0", text_color="#E74C3C", font=get_font('small_bold', module='almacen'))
        self.lbl_salidas.pack(side='left', padx=10)

        self.lbl_stock = ctk.CTkLabel(self.summary_frame, text="Stock: 0", text_color=self.colors.get('accent', COLOR_MATRIX), font=get_font('label_bold', module='almacen'))
        self.lbl_stock.pack(side='left', padx=10)

    def _build_grid(self):
        """Implementar la lista de movimientos en el panel izquierdo."""
        columns = [
            ('FECHA', 180),
            ('CANTIDAD', 100),
            ('MOTIVO', 400, True), # Expandible
            ('USUARIO', 150)
        ]
        
        self.nav_list = VirtualNavList(
            self.grid_scroll,
            columns=columns,
            module_name=self.module_name,
            on_select=self._on_row_select,
            keyboard_manager=self.keyboard_manager
        )
        self.nav_list.pack(fill='both', expand=True, padx=2, pady=2)

    def _build_footer(self):
        """Implementar botones de acción en el footer."""
        # Botón VER ALBARÁN
        self.btn_albaran = ButtonFactory.create_button(
            parent=self.footer,
            text='VER ALBARÁN',
            command=self._on_ver_albaran,
            style_key='action_primary',
            module='almacen',
            palette_key='secondary'
        )
        self.btn_albaran.pack(side='left', padx=6)
        self.btn_albaran.configure(state='disabled')

    def _on_row_select(self, data: dict):
        """Habilita/deshabilita botones y actualiza el visor lateral."""
        try:
            raw = data.get('_raw', {})
            ticket_line_id = raw.get('ticket_line_id')
            motivo = str(raw.get('motivo') or '').lower()
            
            # 1. Habilitar/Deshabilitar botones
            if ticket_line_id:
                # 2. Actualizar visor automáticamente si es un ticket
                self._mostrar_ticket_en_visor(ticket_line_id)
            else:
                self.clear_visor()
                
            if 'albaran:' in motivo:
                self.btn_albaran.configure(state='normal')
            else:
                self.btn_albaran.configure(state='disabled')
                
        except Exception:
            logger.exception("Error en selección de fila de movimientos")

    def _mostrar_ticket_en_visor(self, ticket_line_id: int):
        """Recupera el ticket completo usando ImpresoraService y lo muestra en el visor derecho."""
        try:
            # 1. Primero necesitamos el ticket_id real desde la línea
            res = self.db.fetch_one("SELECT ticket_id FROM ticket_lines WHERE id = ?", (ticket_line_id,))
            if not res:
                self.update_visor("--- LÍNEA DE TICKET NO ENCONTRADA ---")
                return
            
            ticket_id = res[0]
            
            # 2. Usar ImpresoraService para reconstruir el ticket tal cual se imprimiría
            imp = ImpresoraService(db=self.db)
            content = imp.generar_ticket_desde_id(ticket_id)
            
            if content:
                self.update_visor(content)
            else:
                self.update_visor(f"--- ERROR AL GENERAR TICKET #{ticket_id} ---")
                
        except Exception:
            logger.exception("Error actualizando visor de ticket")
            self.update_visor("--- ERROR CRÍTICO AL CARGAR TICKET ---")

    def _on_ver_albaran(self):
        """Busca el albarán asociado y abre su detalle (Navegación)."""
        try:
            sel = self.nav_list.get_selected_data()
            if not sel: return
            
            raw = sel.get('_raw', {})
            motivo = str(raw.get('motivo') or '').lower()
            
            if 'albaran:' not in motivo: return
            num_albaran = motivo.split('albaran:')[1].strip()
            
            res = self.db.fetch_one("SELECT id FROM albaranes WHERE num_albaran = ?", (num_albaran,))
            if not res:
                show_error(self.container, "ERROR", f"No se encontró el albarán {num_albaran}")
                return
            
            albaran_id = res[0]
            
            if self.owner and hasattr(self.owner, 'show_entrada_manual'):
                cb_volver = lambda: self.owner.show_movimientos_producto(self.producto_id)
                self.owner.show_entrada_manual(albaran_id=albaran_id, back_callback=cb_volver)
        except Exception:
            logger.exception("Error al mostrar albarán")

    def cargar_datos(self):
        """Carga los movimientos del producto en la lista y actualiza el resumen del header."""
        movements = self.service.obtener_historial_producto(self.producto_id)
        
        items = []
        total_entradas = 0
        total_salidas = 0
        
        for m in movements:
            cantidad = m['cantidad']
            if cantidad > 0:
                total_entradas += cantidad
            elif cantidad < 0:
                total_salidas += abs(cantidad)

            row_fg = "#2ECC71" if cantidad > 0 else "#E74C3C" if cantidad < 0 else self.colors.get('text', COLOR_MATRIX)
            
            items.append({
                'FECHA': m['created_at'],
                'CANTIDAD': f"{'+' if cantidad > 0 else ''}{cantidad}",
                'MOTIVO': m['motivo'] or '-',
                'USUARIO': m['usuario_nombre'],
                '_row_fg': row_fg,
                '_raw': m 
            })
            
        self.nav_list.set_items(items)

        # Actualizar labels de la cabecera
        self.lbl_entradas.configure(text=f"Entradas: +{total_entradas}")
        self.lbl_salidas.configure(text=f"Salidas: -{total_salidas}")
        
        # Obtener stock actual real de la ficha
        try:
            row_stock = self.db.fetch_one("SELECT stock_actual FROM productos WHERE id = ?", (self.producto_id,))
            stock_actual = row_stock[0] if row_stock else 0
            self.lbl_stock.configure(text=f"Stock: {stock_actual}")
        except Exception:
            logger.exception("Error recuperando stock actual para el resumen")
