"""UI para configurar mapeo CSV de importación de albaranes."""
import logging
import json
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.custom_dialog import show_error, show_success

logger = logging.getLogger(__name__)


class MapeoCsvUI:
    """Editor de configuración JSON para importación CSV por proveedor."""

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre=''):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.proveedor_service = ProveedorService(db)
        self.mapeo_original = None

        self.container = ctk.CTkFrame(parent, fg_color=COLOR_BG_TERMINAL)

        # Header: Tutorial
        tutorial_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a', corner_radius=8)
        tutorial_frame.pack(fill='x', padx=12, pady=(12, 6))

        titulo_tutorial = ctk.CTkLabel(
            tutorial_frame,
            text='📋 GUÍA DE CONFIGURACIÓN',
            font=('Courier New', 16, 'bold'),
            text_color='#9b59b6'
        )
        titulo_tutorial.pack(pady=(10, 5))

        tutorial_text = """
    • columna_ean: Nombre de la columna con el código EAN/código de barras
    • columna_cantidad: Nombre de la columna con las unidades compradas
    • columna_precio: Nombre de la columna con el precio/coste unitario

    • separador:
    "," → CSV americano (Google Sheets, Excel inglés)
    ";" → CSV europeo (Excel español)

    • skip_rows:
    0 → Lee desde línea 1 (cabecera incluida)
    1 → Salta primera fila (si tiene título extra antes de cabecera)

    • encoding: Codificación del archivo ("utf-8" o "latin-1")

    NOTA: Con el EAN se obtiene automáticamente el nombre, IVA y otros datos desde la BD.
    Si el precio difiere del registrado, se actualizará y se avisará.
    """

        tutorial_label = ctk.CTkLabel(
            tutorial_frame,
            text=tutorial_text.strip(),
            font=('Courier New', 12),
            text_color='#CCCCCC',
            justify='left',
            anchor='w'
        )
        tutorial_label.pack(fill='x', padx=20, pady=(0, 10))

        # Label proveedor
        prov_label = ctk.CTkLabel(
            self.container,
            text=f'PROVEEDOR: {self.proveedor_nombre}',
            font=('Courier New', 14, 'bold'),
            text_color=COLOR_MATRIX
        )
        prov_label.pack(pady=(6, 6), padx=12, anchor='w')

        # TextArea para JSON
        json_label = ctk.CTkLabel(
            self.container,
            text='CONFIGURACIÓN JSON:',
            font=('Courier New', 13, 'bold'),
            text_color='#FFFFFF'
        )
        json_label.pack(pady=(0, 4), padx=12, anchor='w')

        self.textbox = ctk.CTkTextbox(
            self.container,
            font=('Courier New', 14),
            fg_color='#000000',
            text_color='#00FF00',
            border_color='#9b59b6',
            border_width=3,
            wrap='none'
        )
        self.textbox.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        # Cargar mapeo actual
        self._cargar_mapeo()

        # Footer con botones
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=12, pady=12)

        btn_cancelar = ctk.CTkButton(
            footer,
            text='CANCELAR',
            fg_color='#7f8c8d',
            hover_color='#95a5a6',
            text_color='#000000',
            font=('Courier New', 18, 'bold'),
            width=140,
            height=50,
            corner_radius=0,
            command=self._on_cancelar
        )
        btn_cancelar.pack(side='left', padx=8)

        btn_guardar = ctk.CTkButton(
            footer,
            text='GUARDAR',
            fg_color='#2ecc71',
            hover_color='#27ae60',
            text_color='#000000',
            font=('Courier New', 18, 'bold'),
            width=140,
            height=50,
            corner_radius=0,
            command=self._on_guardar
        )
        btn_guardar.pack(side='left', padx=8)

        # Foco en textbox
        try:
            self.textbox.focus_set()
        except Exception:
            pass

    def get_widget(self):
        return self.container

    def has_unsaved_changes(self):
        """Verificar si el JSON fue modificado."""
        try:
            contenido_actual = self.textbox.get('1.0', 'end-1c').strip()
            return contenido_actual != (self.mapeo_original or '').strip()
        except Exception:
            return False

    def _cargar_mapeo(self):
        """Cargar mapeo desde BD y mostrarlo en el editor."""
        try:
            mapeo = self.proveedor_service.get_mapeo_csv(self.proveedor_id)

            # Plantilla por defecto si no existe
            if not mapeo:
                mapeo = '''{
"columna_ean": "EAN",
"columna_cantidad": "Cantidad",
"columna_precio": "Precio",
"separador": ",",
"skip_rows": 0,
"encoding": "utf-8"
}'''

            # Formatear bonito
            try:
                parsed = json.loads(mapeo)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                mapeo = formatted
            except Exception:
                pass

            self.mapeo_original = mapeo
            self.textbox.insert('1.0', mapeo)

        except Exception:
            logging.exception('Error cargando mapeo CSV')

    def _on_guardar(self):
        """Validar JSON y guardar en BD."""
        try:
            contenido = self.textbox.get('1.0', 'end-1c').strip()

            # Validar que es JSON válido
            try:
                parsed = json.loads(contenido)

                # Validar campos obligatorios (solo EAN, Cantidad, Precio)
                campos_req = ['columna_ean', 'columna_cantidad', 'columna_precio']
                faltantes = [c for c in campos_req if c not in parsed]

                if faltantes:
                    show_error(
                        self.container,
                        'JSON incompleto',
                        f'Faltan campos obligatorios: {", ".join(faltantes)}'
                    )
                    return

            except json.JSONDecodeError as e:
                show_error(
                    self.container,
                    'JSON inválido',
                    f'Error de sintaxis en línea {e.lineno}: {e.msg}'
                )
                return

            # Guardar en BD
            if self.proveedor_service.save_mapeo_csv(self.proveedor_id, contenido):
                show_success(self.container, 'Guardado', 'Mapeo CSV guardado correctamente')
                self.mapeo_original = contenido  # Actualizar para has_unsaved_changes
                logging.info(f'Mapeo CSV guardado para proveedor {self.proveedor_id}')
            else:
                show_error(self.container, 'Error', 'No se pudo guardar el mapeo CSV')

        except Exception:
            logging.exception('Error guardando mapeo CSV')

    def _on_cancelar(self):
        """Cancelar edición (verificado por warnings automáticos)."""
        logging.info('Cancelando edición mapeo CSV')
