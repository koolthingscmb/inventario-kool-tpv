"""UI para configurar mapeo CSV de importación de albaranes (Producción)."""
import logging
import json
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.font_loader import get_font
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.custom_dialog import show_error
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)


class ProduccionProveedoresMapeoCsv:
    """Editor de configuración JSON para importación CSV por proveedor."""

    PLANTILLA_JSON = '''{
  "separador": ";",
  "encoding": "utf-8",
  "skip_rows": 0,
  "columna_nombre": "",
  "columna_cantidad": "",
  "columna_color": "",
  "columna_talla": "",
  "columna_precio_base": "",
  "columna_coste": "",
  "columna_descuento": "",
  "columna_iva": "",
  "columna_pvpr": "",
  "calcular_coste_desde_precio_dto": false,
  "calcular_pvpr_desde_precio_iva": false
}'''

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner
        self.proveedor_service = ProveedorService(db)
        self.mapeo_original = None
        self._undo_stack = []
        self._undo_index = -1
        self._undo_active = False

        try:
            self.colors = load_colors('produccion')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        tutorial_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a', corner_radius=8)
        tutorial_frame.pack(fill='x', padx=12, pady=(12, 6))

        ctk.CTkLabel(tutorial_frame, text='CONFIGURACIÓN MAPEO CSV',
                     font=('Courier New', 18, 'bold'), text_color='#9b59b6').pack(pady=(10, 8))

        texto = """COLUMNAS DEL CSV (pon el nombre exacto):
  columna_nombre / columna_cantidad
  columna_color / columna_talla  (obligatorias en producción)
  columna_precio_base / columna_coste / columna_descuento
  columna_iva / columna_pvpr

CÁLCULOS: calcular_coste_desde_precio_dto / calcular_pvpr_desde_precio_iva
TÉCNICA: separador ("," o ";"), skip_rows, encoding (utf-8 / latin-1)"""
        ctk.CTkLabel(tutorial_frame, text=texto, font=('Courier New', 15),
                     text_color='#CCCCCC', justify='left', anchor='nw').pack(fill='both', padx=20, pady=(0, 10))

        ctk.CTkLabel(self.container, text=f'PROVEEDOR: {self.proveedor_nombre}',
                     font=('Courier New', 14, 'bold'),
                     text_color=self.colors.get('text', COLOR_MATRIX)).pack(pady=(6, 6), padx=12, anchor='w')

        json_header = ctk.CTkFrame(self.container, fg_color='transparent')
        json_header.pack(fill='x', padx=12, pady=(0, 4))
        ctk.CTkLabel(json_header, text='CONFIGURACIÓN JSON:',
                     font=('Courier New', 13, 'bold'), text_color='#FFFFFF').pack(side='left')
        self.btn_plantilla = ctk.CTkButton(json_header, text='PLANTILLA', font=('Courier New', 11, 'bold'),
                                           fg_color='#9b59b6', hover_color='#8e44ad', width=90, height=26,
                                           command=self._insertar_plantilla)
        self.btn_plantilla.pack(side='right')

        self.textbox = ctk.CTkTextbox(self.container, font=('Courier New', 16), fg_color='#000000',
                                      text_color='#00FF00', border_color='#9b59b6', border_width=3, wrap='none')
        self.textbox.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        self._setup_undo()
        self._cargar_mapeo()

        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(side='bottom', fill='x', padx=12, pady=12)
        self.btn_cancelar = create_action_button(footer, 'cancelar', self._on_cancelar)
        self.btn_cancelar.pack(side='left', padx=8)
        self.btn_guardar = create_action_button(footer, 'guardar', self._on_guardar)
        self.btn_guardar.pack(side='left', padx=8)

        try:
            self.textbox.focus_set()
        except Exception:
            pass

    def get_widget(self):
        return self.container

    def has_unsaved_changes(self):
        try:
            contenido_actual = self.textbox.get('1.0', 'end-1c').strip()
            return contenido_actual != (self.mapeo_original or '').strip()
        except Exception:
            return False

    def _cargar_mapeo(self):
        try:
            mapeo = self.proveedor_service.get_mapeo_csv(self.proveedor_id)
            if not mapeo:
                mapeo = self.PLANTILLA_JSON
            try:
                parsed = json.loads(mapeo)
                mapeo = json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                pass
            self.mapeo_original = mapeo
            self.textbox.insert('1.0', mapeo)
        except Exception:
            logging.exception('Error cargando mapeo CSV')

    def _on_guardar(self):
        try:
            contenido = self.textbox.get('1.0', 'end-1c').strip()
            try:
                parsed = json.loads(contenido)
                campos_req = ['columna_nombre', 'columna_cantidad', 'columna_color', 'columna_talla']
                faltantes = [c for c in campos_req if c not in parsed]
                tiene_precio = any(k in parsed for k in ('columna_precio_base', 'columna_coste', 'columna_precio'))
                if not tiene_precio:
                    faltantes.append('columna_precio_base o columna_coste')
                if faltantes:
                    show_error(self.container, 'JSON incompleto', f'Faltan: {", ".join(faltantes)}')
                    return
            except json.JSONDecodeError as e:
                show_error(self.container, 'JSON inválido', f'Error línea {e.lineno}: {e.msg}')
                return
            if self.proveedor_service.save_mapeo_csv(self.proveedor_id, contenido):
                ToastWidget.show(self.container, 'Mapeo CSV guardado', tipo='success')
                self.mapeo_original = contenido
                try:
                    if getattr(self, 'owner', None) and hasattr(self.owner, 'show_proveedores'):
                        self.owner.show_proveedores(proveedor_id=self.proveedor_id)
                except Exception:
                    logging.exception('Error volviendo a proveedores')
            else:
                show_error(self.container, 'Error', 'No se pudo guardar')
        except Exception:
            logging.exception('Error guardando mapeo CSV')

    def _insertar_plantilla(self):
        try:
            self.textbox.delete('1.0', 'end')
            self.textbox.insert('1.0', self.PLANTILLA_JSON)
            self.textbox.focus_set()
            self._save_undo_state()
        except Exception:
            logging.exception('Error insertando plantilla')

    def _save_undo_state(self):
        if self._undo_active:
            return
        current = self.textbox.get('1.0', 'end-1c')
        if self._undo_index < 0 or self._undo_stack[self._undo_index] != current:
            self._undo_stack = self._undo_stack[:self._undo_index + 1]
            self._undo_stack.append(current)
            self._undo_index += 1

    def _setup_undo(self):
        try:
            self.textbox.bind('<KeyRelease>', lambda e: self._save_undo_state())
            def undo(event=None):
                if self._undo_index > 0:
                    self._undo_active = True
                    self._undo_index -= 1
                    self.textbox.delete('1.0', 'end')
                    self.textbox.insert('1.0', self._undo_stack[self._undo_index])
                    self._undo_active = False
                return 'break'
            def redo(event=None):
                if self._undo_index < len(self._undo_stack) - 1:
                    self._undo_active = True
                    self._undo_index += 1
                    self.textbox.delete('1.0', 'end')
                    self.textbox.insert('1.0', self._undo_stack[self._undo_index])
                    self._undo_active = False
                return 'break'
            self.textbox.bind('<Control-z>', undo)
            self.textbox.bind('<Control-Z>', undo)
            self.textbox.bind('<Control-y>', redo)
            self.textbox.bind('<Control-Y>', redo)
            self._save_undo_state()
        except Exception:
            logging.exception('Error configurando undo/redo')

    def _on_cancelar(self):
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_proveedores'):
                self.owner.show_proveedores(proveedor_id=self.proveedor_id)
        except Exception:
            logging.exception('Error en _on_cancelar')
