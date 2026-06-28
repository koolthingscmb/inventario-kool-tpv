"""UI de Importar Albarán para Producción - Gestión de Bases Textiles."""
import logging
import json
import re
import unicodedata
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from decimal import Decimal
import customtkinter as ctk

from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.csv_import import CsvParser
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.modulos.almacen.albaran_repository import AlbaranRepository
from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)

class ProduccionImportarAlbaran:
    """UI para importar albaranes de bases textiles en el taller."""

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner
        
        self.selected_file_path = None
        self.parse_result = [] # Datos brutos del CSV
        self.lineas_procesadas = [] # Datos con color mapeado y validaciones
        self.mapeo_colores = {} # color_prov -> color_interno (nombre)
        self.mapeo_variantes = {} # "Tipo / Variante" -> [keywords]
        self.mapeo_tallas = {} # talla_kool -> [keywords]
        self.colores_internos = {} # nombre -> id
        self.tallas_internas = {} # nombre -> id
        self.variantes_disponibles = {} # id -> "Tipo / Variante"
        self.variantes_lookup = {} # "Tipo / Variante" -> (variante_id, tipo_id)
        
        try:
            self.colors = load_colors('produccion')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        self._cargar_mapeos()
        self._setup_ui()
        
        self._esc_handler = lambda e: self._on_volver_click()
        self._bind_esc_recursive(self.container)

    def _cargar_mapeos(self):
        """Cargar configuración de colores y variantes."""
        if not self.db: return
        
        prov_service = ProveedorService(self.db)
        # 1. Mapeos del proveedor
        if self.proveedor_id:
            # Colores
            mapeo_colores_json = prov_service.get_mapeo_colores(self.proveedor_id)
            if mapeo_colores_json:
                try:
                    self.mapeo_colores = json.loads(mapeo_colores_json)
                except Exception:
                    logger.error("Error parseando mapeo_colores JSON")
            
            # Variantes
            mapeo_variantes_json = prov_service.get_mapeo_variantes(self.proveedor_id)
            if mapeo_variantes_json:
                try:
                    self.mapeo_variantes = json.loads(mapeo_variantes_json)
                except Exception:
                    logger.error("Error parseando mapeo_variantes JSON")

            # Tallas
            mapeo_tallas_json = prov_service.get_mapeo_tallas(self.proveedor_id)
            if mapeo_tallas_json:
                try:
                    self.mapeo_tallas = json.loads(mapeo_tallas_json)
                except Exception:
                    logger.error("Error parseando mapeo_tallas JSON")

        
        # 2. Colores internos (Canonical)
        try:
            svc_colores = ProduccionColoresService(self.db)
            self.colores_internos = {c.nombre: c.id for c in svc_colores.obtener_activos()}
        except Exception:
            logger.exception("Error cargando colores internos")

        # 2b. Tallas internas (Canonical)
        try:
            from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
            svc_tallas = ProduccionTallasService(self.db)
            self.tallas_internas = {t.nombre: t.id for t in svc_tallas.obtener_todas()}
        except Exception:
            logger.exception("Error cargando tallas internas")
            
        # 3. Variantes disponibles
        try:
            svc_variantes = ProduccionTiposVariantesService(self.db)
            dict_variantes = svc_variantes.obtener_activos_como_dict()
            self.variantes_disponibles = dict_variantes  # {id: "Tipo / Variante"}
            # Construir lookup inverso: "Tipo / Variante" -> (variante_id, tipo_id)
            for vid, etiqueta in dict_variantes.items():
                variante = svc_variantes.obtener_por_id(vid)
                if variante:
                    self.variantes_lookup[etiqueta] = (vid, variante.tipo_id)
        except Exception:
            logger.exception("Error cargando variantes")


    def _setup_ui(self):
        font_config = load_font_config()
        title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})
        entry_font = font_config.get('entry', {'family': 'Courier New', 'size': 14})

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container, 
            text=f'IMPORTAR ALBARÁN DE BASES: {self.proveedor_nombre.upper()}',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(title_font['family'], title_font['size'], title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(15, 10))

        # TOP PANEL: Archivo y Cabecera
        top_panel = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        top_panel.pack(fill='x', padx=20, pady=5)

        # Fila 1: Selección de archivo
        file_row = ctk.CTkFrame(top_panel, fg_color='transparent')
        file_row.pack(fill='x', padx=10, pady=10)
        
        self.btn_seleccionar = ButtonFactory.create_button(
            file_row, 'SELECCIONAR CSV', self._on_seleccionar_click, style_key='action_confirm'
        )
        self.btn_seleccionar.pack(side='left', padx=(0, 10))
        
        self.lbl_archivo = ctk.CTkLabel(
            file_row, 
            text='Ningún archivo seleccionado', 
            text_color='#888888',
            font=(entry_font['family'], entry_font['size'])
        )
        self.lbl_archivo.pack(side='left')

        # Fila 2: Cabecera
        cab_row = ctk.CTkFrame(top_panel, fg_color='transparent')
        cab_row.pack(fill='x', padx=10, pady=(0, 10))
        
        ctk.CTkLabel(cab_row, text='Nº Albarán:', font=(label_font['family'], label_font['size'])).pack(side='left', padx=5)
        self.entry_num = ctk.CTkEntry(cab_row, width=120, font=(entry_font['family'], entry_font['size']))
        self.entry_num.pack(side='left', padx=5)
        
        # Pre-rellenar número
        try:
            albaran_service = AlbaranService(self.db)
            self.entry_num.insert(0, str(albaran_service.get_next_num_albaran()))
        except: pass

        # TABLA PREVIEW
        self.columns = [
            ('PRODUCTO CSV', 180), ('VARIANTE KOOL', 140),
            ('COLOR PROV', 110), ('COLOR KOOL', 100), 
            ('TALLA PROV', 80), ('TALLA KOOL', 80),
            ('UDS', 50), ('COSTE', 70), ('ESTADO', 120)
        ]
        self.nav_list = VirtualNavList(self.container, columns=self.columns, module_name='produccion')
        self.nav_list.pack(fill='both', expand=True, padx=20, pady=10)

        # RESUMEN PANEL
        self.resumen_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        self.resumen_frame.pack(fill='x', padx=20, pady=5)
        self.lbl_resumen = ctk.CTkLabel(self.resumen_frame, text='', font=(label_font['family'], label_font['size']))
        self.lbl_resumen.pack(pady=10)

        # BOTONES FOOTER
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(fill='x', padx=20, pady=15)
        
        self.btn_importar = ButtonFactory.create_button(
            footer, 'CONFIRMAR Y SUBIR STOCK', self._on_importar_click, style_key='action_success'
        )
        self.btn_importar.pack(side='right')
        self.btn_importar.configure(state='disabled')
        
        self.btn_volver = ButtonFactory.create_button(
            footer, 'VOLVER', self._on_volver_click, style_key='action_secondary'
        )
        self.btn_volver.pack(side='left')

    def _on_seleccionar_click(self):
        path = filedialog.askopenfilename(
            title='Seleccionar archivo CSV',
            filetypes=[('Archivos CSV', '*.csv'), ('Todos los archivos', '*.*')]
        )
        if path:
            self.selected_file_path = path
            self.lbl_archivo.configure(text=Path(path).name, text_color=COLOR_MATRIX)
            self._analizar_csv()

    def _analizar_csv(self):
        if not self.selected_file_path: return
        
        try:
            parser = CsvParser()
            prov_service = ProveedorService(self.db)
            mapeo_csv = prov_service.get_mapeo_csv(self.proveedor_id)
            if mapeo_csv:
                parser.set_provider_mapping(json.loads(mapeo_csv))
                
            datos, errores = parser.parse_file(self.selected_file_path)
            if errores and not datos:
                ToastWidget.show(self.container, f'ERROR PARSEANDO CSV: {errores[0]}', tipo='error')
                return
                
            self.parse_result = datos
            self._procesar_lineas()
            
        except Exception:
            logger.exception("Error analizando CSV")
            ToastWidget.show(self.container, 'NO SE PUDO ANALIZAR EL CSV', tipo='error')

    @staticmethod
    def _normalizar(texto: str) -> str:
        """Normalizar texto para matching robusto:
        - Lowercase
        - Quitar tildes/diacríticos
        - Quitar caracteres especiales (#, -, _, etc.)
        - Colapsar espacios múltiples
        """
        if not texto:
            return ""
        texto = texto.lower()
        texto = unicodedata.normalize('NFD', texto)
        texto = texto.encode('ascii', 'ignore').decode('ascii')
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def _procesar_lineas(self):
        """Aplicar mapeos y validaciones a los datos brutos."""
        self.lineas_procesadas = []
        
        logger.info(f"Procesando {len(self.parse_result)} líneas con mapeo_variantes: {self.mapeo_variantes}")
        logger.info(f"Mapeo colores: {self.mapeo_colores}")
        logger.info(f"Mapeo tallas: {self.mapeo_tallas}")
        
        for fila in self.parse_result:
            nombre_csv = fila.get('nombre', '').strip()
            col_prov = fila.get('color', '').strip()
            talla_prov = fila.get('talla', '').strip()
            uds = fila.get('cantidad', 0)
            coste = fila.get('coste', 0.0)
            
            # 1. Mapeo de VARIANTE (por palabras clave en nombre)
            variante_id = None
            tipo_id = None
            variante_label = '???'
            nombre_norm = self._normalizar(nombre_csv)
            
            # Recorrer el diccionario: "Tipo / Variante" -> [Lista de Keywords]
            if isinstance(self.mapeo_variantes, dict):
                for v_label, keywords in self.mapeo_variantes.items():
                    if isinstance(keywords, list):
                        for kw in keywords:
                            if self._normalizar(kw) in nombre_norm:
                                lookup = self.variantes_lookup.get(v_label)
                                if lookup:
                                    variante_id, tipo_id = lookup
                                    variante_label = v_label
                                break
                    if variante_id: break

            # 2. Mapeo de COLOR
            # Recorrer el diccionario: ColorInterno -> [Lista de Colores Proveedor]
            color_mapeado = None
            if isinstance(self.mapeo_colores, dict):
                col_prov_norm = self._normalizar(col_prov)
                for c_interno, c_prov_list in self.mapeo_colores.items():
                    if isinstance(c_prov_list, list):
                        if any(self._normalizar(str(cp)) in col_prov_norm for cp in c_prov_list):
                            color_mapeado = c_interno
                            break
                    elif self._normalizar(str(c_prov_list)) in col_prov_norm:
                        color_mapeado = c_interno
                        break
            
            color_id = self.colores_internos.get(color_mapeado) if color_mapeado else None

            # 3. Mapeo de TALLA
            talla_mapeada = None
            if isinstance(self.mapeo_tallas, dict):
                talla_prov_norm = self._normalizar(talla_prov)
                for t_interna, t_prov_list in self.mapeo_tallas.items():
                    if isinstance(t_prov_list, list):
                        if any(self._normalizar(str(tp)) == talla_prov_norm for tp in t_prov_list):
                            talla_mapeada = t_interna
                            break
                    elif self._normalizar(str(t_prov_list)) == talla_prov_norm:
                        talla_mapeada = t_interna
                        break
            
            # Si no hay mapeo explícito, probamos si coincide directamente con una interna
            if not talla_mapeada:
                t_prov_norm = self._normalizar(talla_prov)
                for t_interna in self.tallas_internas.keys():
                    if self._normalizar(t_interna) == t_prov_norm:
                        talla_mapeada = t_interna
                        break
            
            talla_id = self.tallas_internas.get(talla_mapeada) if talla_mapeada else None
            
            estado = '✓ OK'
            if not variante_id:
                estado = '⚠ Falta Variante'
            elif not color_id:
                estado = '⚠ Color desconocido'
            elif not talla_id:
                estado = '⚠ Talla desconocida'
            elif uds <= 0:
                estado = '⚠ Cantidad 0'
            
            self.lineas_procesadas.append({
                'nombre_csv': nombre_csv,
                'tipo_id': tipo_id,
                'variante_id': variante_id,
                'variante_nombre': variante_label,
                'color_id': color_id,
                'color_prov': col_prov,
                'color_interno': color_mapeado or '???',
                'talla_prov': talla_prov,
                'talla_kool': talla_mapeada or '???',
                'talla_id': talla_id,
                'uds': uds,
                'coste': coste,
                'total': uds * coste,
                'estado': estado,
                'valida': estado == '✓ OK'
            })
            
        self._mostrar_preview()

    def _mostrar_preview(self):
        rows = []
        tot_uds = 0
        tot_importe = 0.0
        todas_validas = True
        
        for p in self.lineas_procesadas:
            rows.append({
                'PRODUCTO CSV': p['nombre_csv'],
                'VARIANTE KOOL': p['variante_nombre'],
                'COLOR PROV': p['color_prov'],
                'COLOR KOOL': p['color_interno'],
                'TALLA PROV': p['talla_prov'],
                'TALLA KOOL': p['talla_kool'],
                'UDS': str(p['uds']),
                'COSTE': f"{p['coste']:.2f}€",
                'ESTADO': p['estado']
            })
            if p['valida']:
                tot_uds += p['uds']
                tot_importe += p['total']
            else:
                todas_validas = False
                
        self.nav_list.set_items(rows)
        self.lbl_resumen.configure(text=f"Total válido: {tot_uds} unidades | {tot_importe:.2f}€")
        
        if todas_validas and rows:
            self.btn_importar.configure(state='normal')
        else:
            self.btn_importar.configure(state='disabled')

    def _on_importar_click(self):
        """Guardar albarán y actualizar stock con coste medio."""
        if not self.lineas_procesadas: return
        
        num_albaran = self.entry_num.get().strip()
        if not num_albaran:
            ToastWidget.show(self.container, 'INTRODUCE UN NÚMERO DE ALBARÁN', tipo='error')
            return
            
        try:
            from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
            stock_service = ProduccionStockBaseService(self.db)
            repo_albaran = AlbaranRepository(self.db)
            
            # 1. Preparar líneas para AlbaranRepository (registro histórico)
            lineas_albaran = []
            for p in self.lineas_procesadas:
                lineas_albaran.append({
                    'producto_id': None, # No es un producto de la tabla 'productos'
                    'ean': '',
                    'nombre': f"{p['variante_nombre']} - {p['color_interno']} ({p['talla_kool']})",
                    'cantidad': p['uds'],
                    'coste': p['coste'],
                    'tipo_iva': 21,
                    'es_producto_nuevo': False
                })
            
            # 2. Guardar albarán
            totales = {
                'total_neto': sum(p['total'] for p in self.lineas_procesadas),
                'total_iva_4': 0, 'total_iva_10': 0, 'total_iva_21': 0,
                'total': sum(p['total'] for p in self.lineas_procesadas) * 1.21
            }
            # Simplificamos IVAs para este módulo
            totales['total_iva_21'] = totales['total_neto'] * 0.21
            
            from datetime import date
            repo_albaran.guardar_albaran_completo(
                num_albaran=num_albaran,
                proveedor_id=self.proveedor_id,
                fecha=date.today().strftime('%Y-%m-%d'),
                tipo='ENTRADA',
                lineas=lineas_albaran,
                totales=totales
            )
            
            # 3. Actualizar Stock y Coste Medio usando el servicio
            for p in self.lineas_procesadas:
                stock_service.importar_stock(
                    tipo_id=p['tipo_id'],
                    color_id=p['color_id'],
                    talla=p['talla_kool'],
                    cantidad_nueva=p['uds'],
                    coste_nuevo_eur=p['coste'],
                    variante_id=p.get('variante_id'),
                    talla_id=p.get('talla_id')
                )
                
            ToastWidget.show(self.container, "Albarán procesado y stock actualizado", tipo='success')
            self._on_volver_click()
            
        except Exception:
            logger.exception("Error procesando importación")
            ToastWidget.show(self.container, 'ERROR AL PROCESAR LA IMPORTACIÓN', tipo='error')

    def _on_volver_click(self):
        if self.owner and hasattr(self.owner, 'show_proveedores'):
            self.owner.show_proveedores(proveedor_id=self.proveedor_id)

    def _bind_esc_recursive(self, widget):
        widget.bind('<Escape>', self._esc_handler)
        for child in widget.winfo_children():
            self._bind_esc_recursive(child)

    def get_widget(self):
        return self.container
