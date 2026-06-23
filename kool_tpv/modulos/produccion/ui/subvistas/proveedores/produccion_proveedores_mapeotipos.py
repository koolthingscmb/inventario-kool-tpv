"""Editor JSON para el mapeo de palabras clave a tipos de producto (Producción)."""
import logging
import json
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.base_datos.proveedor_service import ProveedorService

logger = logging.getLogger(__name__)

class ProduccionProveedoresMapeoTipos:
    """Editor de mapeo de tipos con diseño de dos columnas."""

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner
        self.proveedor_service = ProveedorService(db)
        
        self.undo_stack = []
        self.redo_stack = []
        
        try:
            self.colors = load_colors('produccion')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        font_config = load_font_config()
        title_font = font_config.get('title', {'family': 'Courier New', 'size': 20, 'weight': 'bold'})
        label_font = font_config.get('label', {'family': 'Courier New', 'size': 14})
        code_font = {'family': 'Consolas', 'size': 14}

        # --- HEADER (Simple) ---
        header = ctk.CTkFrame(self.container, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(10, 0))
        
        lbl_titulo = ctk.CTkLabel(
            header, 
            text=f"MAPEO DE TIPOS: {self.proveedor_nombre.upper()}",
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(title_font['family'], title_font['size'], title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(side='left')

        # --- MAIN AREA (2 COLUMNS) ---
        main_area = ctk.CTkFrame(self.container, fg_color='transparent')
        main_area.pack(fill='both', expand=True, padx=20, pady=10)

        # 1. LEFT COLUMN (REFERENCE)
        left_col = ctk.CTkFrame(main_area, width=300, fg_color='#1a1a1a')
        left_col.pack(side='left', fill='y', padx=(0, 10))
        left_col.pack_propagate(False)

        # Instrucciones breves
        ctk.CTkLabel(left_col, text="REFERENCIA INTERNA", text_color="#888888", 
                     font=(label_font['family'], 12, 'bold')).pack(pady=(10, 5))
        
        instrucciones = (
            "Asocia palabras clave del\n"
            "proveedor a tus tipos.\n\n"
            "Formato:\n"
            ' "Tipo": ["palabra", ...]\n\n'
            "Ejemplo:\n"
            ' "Camiseta": ["shirt", "tee"]'
        )
        ctk.CTkLabel(left_col, text=instrucciones, text_color="#aaaaaa", justify='left',
                     font=(label_font['family'], 11)).pack(padx=10, pady=5)

        # Lista de tipos internos
        ctk.CTkLabel(left_col, text="TUS TIPOS (ACTIVOS):", text_color=COLOR_MATRIX, 
                     font=(label_font['family'], 12, 'bold')).pack(pady=(15, 5))
        
        self.types_list = ctk.CTkTextbox(left_col, fg_color='#121212', text_color="#88ff88", 
                                        font=('Consolas', 11), border_width=0)
        self.types_list.pack(fill='both', expand=True, padx=10, pady=5)
        self.types_list.configure(state='disabled')

        # 2. RIGHT COLUMN (EDITOR)
        right_col = ctk.CTkFrame(main_area, fg_color='transparent')
        right_col.pack(side='left', fill='both', expand=True)

        # Botón Plantilla arriba a la derecha del editor
        btn_plantilla = ButtonFactory.create_button(
            right_col, 'PLANTILLA', self._insert_template, style_key='action_warning'
        )
        btn_plantilla.pack(anchor='ne', pady=(0, 5))

        self.txt_json = ctk.CTkTextbox(
            right_col, 
            fg_color='#0a0a0a', 
            text_color='#00ff00', 
            font=(code_font['family'], code_font['size']),
            undo=True,
            border_width=1,
            border_color='#333333'
        )
        self.txt_json.pack(fill='both', expand=True)

        # --- FOOTER ---
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(fill='x', padx=20, pady=15)

        btn_cancelar = ButtonFactory.create_button(
            footer, 'CANCELAR', self._on_cancelar, style_key='action_danger'
        )
        btn_cancelar.pack(side='left')

        btn_guardar = ButtonFactory.create_button(
            footer, 'GUARDAR', self._on_guardar, style_key='action_success'
        )
        btn_guardar.pack(side='right')

    def _load_data(self):
        """Cargar datos de la BD (tipos internos y mapeo guardado)."""
        if not self.db: return

        # 1. Cargar tipos internos para la columna de referencia
        try:
            rows = self.db.fetch_all("SELECT nombre FROM tipos WHERE activo = 1 ORDER BY nombre")
            types_text = "\n".join([f"• {r[0]}" for r in rows])
            self.types_list.configure(state='normal')
            self.types_list.delete("1.0", "end")
            self.types_list.insert("1.0", types_text)
            self.types_list.configure(state='disabled')
        except Exception:
            logger.exception("Error cargando tipos para referencia")

        # 2. Cargar mapeo JSON guardado
        mapeo = self.proveedor_service.get_mapeo_tipos(self.proveedor_id)
        if mapeo:
            try:
                # Formatear JSON para que sea legible
                parsed = json.loads(mapeo)
                pretty = json.dumps(parsed, indent=4, ensure_ascii=False)
                self.txt_json.insert("1.0", pretty)
            except Exception:
                self.txt_json.insert("1.0", mapeo)
        else:
            self._insert_template()

    def _insert_template(self):
        template = {
            "Camiseta": ["t-shirt", "shirt", "tee"],
            "Sudadera": ["hood", "sweat", "pullover"],
            "Tote": ["bag", "tote"]
        }
        self.txt_json.delete("1.0", "end")
        self.txt_json.insert("1.0", json.dumps(template, indent=4, ensure_ascii=False))

    def _on_guardar(self):
        contenido = self.txt_json.get("1.0", "end-1c").strip()
        
        # Validar JSON
        try:
            if contenido:
                json.loads(contenido)
        except json.JSONDecodeError as e:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, "Error de Formato", f"El JSON no es válido:\n{str(e)}")
            return

        if self.proveedor_service.save_mapeo_tipos(self.proveedor_id, contenido):
            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            ToastWidget.show(self.container, "Mapeo de tipos guardado correctamente", tipo='success')
            self._on_cancelar()

    def _on_cancelar(self):
        if self.owner and hasattr(self.owner, 'show_proveedores'):
            self.owner.show_proveedores(proveedor_id=self.proveedor_id)

    def get_widget(self):
        return self.container
