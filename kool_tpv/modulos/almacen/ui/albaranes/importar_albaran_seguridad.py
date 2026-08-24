"""
Subvista de búsqueda rápida para vincular productos del albarán con el stock existente.
Se integra como un frame dentro del flujo de importación, no como ventana flotante.
"""
import logging
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

logger = logging.getLogger(__name__)

class AlbaranBusquedaSeguridadView(ctk.CTkFrame):
    """
    Vista que permite buscar un producto en la base de datos para vincularlo
    a una línea del albarán que ha sido detectada como 'NUEVA'.
    """

    def __init__(self, parent, db, query_inicial='', on_vincular=None, on_cancelar=None):
        super().__init__(parent, fg_color=COLOR_BG_TERMINAL)
        self.db = db
        self.query_inicial = query_inicial
        self.on_vincular = on_vincular
        self.on_cancelar = on_cancelar
        self.result = None

        # Configuración de fuentes
        font_config = load_font_config()
        label_cfg = font_config.get('label', {'family': 'Courier New', 'size': 16})
        entry_cfg = font_config.get('entry', {'family': 'Courier New', 'size': 14})
        title_cfg = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        
        self.label_font = (label_cfg['family'], label_cfg['size'], label_cfg.get('weight', 'normal'))
        self.entry_font = (entry_cfg['family'], entry_cfg['size'], entry_cfg.get('weight', 'normal'))
        self.title_font = (title_cfg['family'], title_cfg['size'], title_cfg.get('weight', 'normal'))

        self._crear_ui()
        
        # Cargar búsqueda inicial
        if self.query_inicial:
            self.entry_busqueda.insert(0, self.query_inicial)
            self._ejecutar_busqueda()

    def _crear_ui(self):
        """Crear los widgets de la vista."""
        # Título de la subvista
        lbl_titulo = ctk.CTkLabel(
            self,
            text='SEGURIDAD: VINCULAR A PRODUCTO EXISTENTE',
            text_color=COLOR_MATRIX,
            font=self.title_font
        )
        lbl_titulo.pack(pady=(20, 10))

        # Frame de búsqueda
        search_frame = ctk.CTkFrame(self, fg_color='transparent')
        search_frame.pack(fill='x', padx=40, pady=10)

        ctk.CTkLabel(search_frame, text="BUSCAR:", font=self.label_font).pack(side='left', padx=(0, 10))
        
        self.entry_busqueda = ctk.CTkEntry(
            search_frame, 
            font=self.entry_font,
            placeholder_text="Nombre del producto...",
            width=500
        )
        self.entry_busqueda.pack(side='left', fill='x', expand=True)
        self.entry_busqueda.bind('<Return>', lambda e: self._ejecutar_busqueda())

        btn_buscar = ButtonFactory.create_button(
            parent=search_frame,
            text='BUSCAR',
            command=self._ejecutar_busqueda,
            style_key='action_primary'
        )
        btn_buscar.pack(side='left', padx=10)

        # Tabla de resultados
        self.nav_list = VirtualNavList(
            self,
            columns=[
                ('ID', 60), ('NOMBRE', 450, True), ('SKU', 150), ('STOCK', 80), ('PVP', 80)
            ],
            module_name='almacen',
            on_double_click=self._on_aceptar
        )
        self.nav_list.pack(fill='both', expand=True, padx=40, pady=10)

        # Botones de pie
        footer_frame = ctk.CTkFrame(self, fg_color='transparent')
        footer_frame.pack(fill='x', padx=40, pady=20)

        btn_cancelar = ButtonFactory.create_button(
            parent=footer_frame,
            text='VOLVER ATRÁS',
            command=self.on_cancelar,
            style_key='action_secondary'
        )
        btn_cancelar.pack(side='left', padx=5)

        self.btn_aceptar = ButtonFactory.create_button(
            parent=footer_frame,
            text='VINCULAR SELECCIONADO',
            command=self._on_aceptar,
            style_key='action_success'
        )
        self.btn_aceptar.pack(side='right', padx=5)

    def _ejecutar_busqueda(self):
        """Ejecutar la búsqueda en la base de datos."""
        query_text = self.entry_busqueda.get().strip()
        if not query_text:
            return

        try:
            # Dividir la búsqueda en palabras para búsqueda flexible
            # Ej: "Buenas Noches Punpun 03" -> ["Buenas", "Noches", "Punpun", "03"]
            words = query_text.split()
            
            # Construir SQL dinámico para que contenga todas las palabras
            where_clauses = []
            params = []
            
            for word in words:
                where_clauses.append("(p.nombre LIKE ? OR p.sku LIKE ?)")
                params.extend([f"%{word}%", f"%{word}%"])
            
            sql = f"""
                SELECT p.id, p.nombre, p.sku, p.stock_actual, pr.pvp
                FROM productos p
                LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
                WHERE {" AND ".join(where_clauses)}
                ORDER BY p.nombre ASC
                LIMIT 100
            """
            
            rows = self.db.fetch_all(sql, tuple(params))

            # Si no hay resultados con todas las palabras, intentar una búsqueda más laxa (alguna palabra)
            if not rows and len(words) > 1:
                where_clauses_or = []
                params_or = []
                for word in words:
                    if len(word) > 2: # Solo palabras significativas
                        where_clauses_or.append("(p.nombre LIKE ? OR p.sku LIKE ?)")
                        params_or.extend([f"%{word}%", f"%{word}%"])
                
                if where_clauses_or:
                    sql = f"""
                        SELECT p.id, p.nombre, p.sku, p.stock_actual, pr.pvp
                        FROM productos p
                        LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
                        WHERE {" OR ".join(where_clauses_or)}
                        ORDER BY p.nombre ASC
                        LIMIT 100
                    """
                    rows = self.db.fetch_all(sql, tuple(params_or))

            items = []
            for r in rows:
                pvp_val = r[4] / 100 if r[4] else 0
                items.append({
                    'ID': str(r[0]),
                    'NOMBRE': r[1],
                    'SKU': r[2] or '',
                    'STOCK': str(r[3]),
                    'PVP': f"{pvp_val:.2f}€"
                })
            
            self.nav_list.set_items(items)
            
            if not items:
                logger.info(f"No se encontraron resultados para: {query_text}")
        except Exception as e:
            logger.exception("Error en búsqueda de seguridad")

    def _on_aceptar(self, item_data=None):
        """Confirmar la vinculación del producto seleccionado."""
        selected = item_data or self.nav_list.get_selected_data()
        if not selected:
            return

        self.result = {
            'producto_id': int(selected['ID']),
            'nombre': selected['NOMBRE'],
            'sku': selected['SKU'],
            'pvp': float(selected['PVP'].replace('€', '').replace(',', '.').strip())
        }
        
        if self.on_vincular:
            self.on_vincular(self.result)
