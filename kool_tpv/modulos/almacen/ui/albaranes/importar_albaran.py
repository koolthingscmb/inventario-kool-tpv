"""UI de Importar Albarán - Paso 4: Preview de CSV con tabla y botón continuar."""
import logging
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
from kool_tpv.utils.dialogs import show_success, show_error, show_info
from kool_tpv.modulos.almacen.ui.albaranes.albaran_borrador import AlbaranBorradorService

logger = logging.getLogger(__name__)


class ImportarAlbaranUI:
    """
    UI para importar albaranes desde CSV.

    Flujo:
        1. Seleccionar archivo CSV
        2. Analizar y mostrar preview con tabla
        3. Crear productos nuevos si aplica
        4. Configurar cabecera y guardar
    """

    def __init__(self, parent, db=None, owner=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = module_name
        self.selected_file_path = None
        self.parse_result = None
        self._borrador_service = AlbaranBorradorService()
        self._borrador_path = None

        try:
            self.colors = load_colors('almacen')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self._setup_ui()

    def _setup_ui(self):
        """Configurar la UI completa con preview."""
        # Cargar configuración de fuentes
        font_config = load_font_config()
        title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})
        entry_font = font_config.get('entry', {'family': 'Courier New', 'size': 14})
        small_font = font_config.get('default', {'family': 'Courier New', 'size': 12})

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container,
            text='IMPORTAR ALBARÁN DESDE CSV',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(title_font['family'], title_font['size'], title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(10, 5))

        # Frame de selección de proveedor
        prov_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        prov_frame.pack(fill='x', padx=20, pady=5)

        ctk.CTkLabel(prov_frame, text='Proveedor:', font=(label_font['family'], label_font['size']), width=100, anchor='e').pack(side='left')
        self.combo_proveedor_import = SearchableCombo(
            prov_frame,
            options=[],
            placeholder='Selecciona proveedor',
            width=250,
            command=self._on_proveedor_seleccionado
        )
        self.combo_proveedor_import.pack(side='left', padx=5)

        # Cargar proveedores
        self._cargar_proveedores_import()

        # Frame de datos de cabecera (Nº Albarán y Fecha)
        cabecera_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        cabecera_frame.pack(fill='x', padx=20, pady=5)

        # Nº Albarán + botón SIGUIENTE
        ctk.CTkLabel(cabecera_frame, text='Nº Albarán:', font=(label_font['family'], label_font['size']), width=100, anchor='e').pack(side='left')
        self.entry_num_albaran = ctk.CTkEntry(cabecera_frame, font=(entry_font['family'], entry_font['size']), width=120)
        self.entry_num_albaran.pack(side='left', padx=5)

        btn_siguiente = ButtonFactory.create_button(
            parent=cabecera_frame,
            text='SIGUIENTE',
            command=self._set_next_num,
            style_key='mini_action'
        )
        btn_siguiente.pack(side='left', padx=(5, 20))

        # Fecha (read-only)
        ctk.CTkLabel(cabecera_frame, text='Fecha:', font=(label_font['family'], label_font['size']), width=60, anchor='e').pack(side='left')
        from datetime import date
        self.entry_fecha_albaran = ctk.CTkEntry(cabecera_frame, font=(entry_font['family'], entry_font['size']), width=100, state='readonly')
        self.entry_fecha_albaran.pack(side='left', padx=5)
        self.entry_fecha_albaran.configure(state='normal')
        self.entry_fecha_albaran.insert(0, date.today().strftime('%Y-%m-%d'))
        self.entry_fecha_albaran.configure(state='readonly')

        # Frame de selección de archivo
        file_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        file_frame.pack(fill='x', padx=20, pady=10)

        # Botón seleccionar archivo
        self.btn_seleccionar = ButtonFactory.create_button(
            parent=file_frame,
            text='SELECCIONAR CSV',
            command=self._on_seleccionar_click,
            style_key='action_confirm'
        )
        self.btn_seleccionar.pack(side='left', padx=(0, 10))
        self.btn_seleccionar.configure(state='disabled')  # Deshabilitado hasta seleccionar proveedor

        # Label con ruta del archivo seleccionado
        self.lbl_archivo = ctk.CTkLabel(
            file_frame,
            text='Ningún archivo seleccionado',
            text_color=self.colors.get('text_secondary', '#888888'),
            font=(small_font['family'], small_font['size'])
        )
        self.lbl_archivo.pack(side='left', fill='x', expand=True)

        # Frame de resumen (inicialmente oculto)
        self.resumen_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        self.resumen_frame.pack(fill='x', padx=20, pady=5)
        self.resumen_frame.pack_forget()  # Oculto hasta analizar

        # Usar fuente del font_config (subtitle para destacar)
        font_config = load_font_config()
        resumen_font = font_config.get('subtitle', {'family': 'Courier New', 'size': 14})
        self.lbl_resumen = ctk.CTkLabel(
            self.resumen_frame,
            text='',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(resumen_font['family'], resumen_font['size'], resumen_font.get('weight', 'normal'))
        )
        self.lbl_resumen.pack(pady=10)

        # Tabla NavList para preview de líneas (todas las columnas de BD)
        self.columns = [
            ('EAN', 120), ('NOMBRE', 200), ('UDS', 50),
            ('COSTE', 70), ('DTO', 50), ('IVA', 40),
            ('IMPORTE', 70), ('EDITORIAL', 100), ('FABRICANTE', 100),
            ('PVPR', 60), ('ESTADO', 80)
        ]

        self.nav_list = VirtualNavList(
            self.container,
            columns=self.columns,
            module_name=self.module_name,
            keyboard_manager=None,
            on_double_click=None,
        )
        self.nav_list.pack(fill='both', expand=True, padx=20, pady=5)

        # Frame de botones de acción
        action_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        action_frame.pack(fill='x', padx=20, pady=10)

        # Botón continuar (deshabilitado hasta análisis)
        self.btn_continuar = ButtonFactory.create_button(
            parent=action_frame,
            text='CONTINUAR',
            command=self._on_continuar_click,
            style_key='action_success'
        )
        self.btn_continuar.pack(side='right', padx=(10, 0))
        self.btn_continuar.configure(state='disabled')

        # Botón volver
        self.btn_volver = ButtonFactory.create_button(
            parent=action_frame,
            text='VOLVER',
            command=self._on_volver_click,
            style_key='action_secondary'
        )
        self.btn_volver.pack(side='right')

        # Pre-rellenar número de albarán
        self._set_next_num()

    def _on_seleccionar_click(self):
        """Abrir file dialog para seleccionar CSV y analizar automáticamente."""
        try:
            file_path = filedialog.askopenfilename(
                parent=self.container,
                title='Seleccionar archivo CSV',
                filetypes=[
                    ('Archivos CSV', '*.csv'),
                    ('Todos los archivos', '*.*')
                ],
                defaultextension='.csv'
            )

            if file_path:
                self.selected_file_path = file_path
                nombre_archivo = Path(file_path).name
                self.lbl_archivo.configure(
                    text=nombre_archivo,
                    text_color=self.colors.get('text', COLOR_MATRIX)
                )
                self._reset_preview()
                logger.info(f'Archivo CSV seleccionado: {file_path}')
                # Analizar automáticamente al seleccionar
                self._on_analizar_click()

        except Exception as e:
            logger.exception('Error seleccionando archivo')
            self._mostrar_error(f'Error al seleccionar: {e}')

    def _reset_preview(self):
        """Limpiar el preview actual."""
        self.parse_result = None
        self.resumen_frame.pack_forget()
        self.nav_list.clear_items()
        self.btn_continuar.configure(state='disabled')

    def _on_analizar_click(self):
        """Analizar el archivo CSV y mostrar preview."""
        if not self.selected_file_path:
            self._mostrar_error('Primero seleccione un archivo CSV')
            return

        try:
            from kool_tpv.utils.csv_import import CsvParser, AlbaranCsvValidator

            # Parsear CSV
            parser = CsvParser()

            # Usar mapeo del proveedor si existe
            if hasattr(self, '_mapeo_proveedor') and self._mapeo_proveedor:
                import json
                try:
                    # El mapeo viene como string JSON, convertir a dict
                    if isinstance(self._mapeo_proveedor, str):
                        mapeo_dict = json.loads(self._mapeo_proveedor)
                    else:
                        mapeo_dict = self._mapeo_proveedor
                    parser.set_provider_mapping(mapeo_dict)
                    logger.info(f'Usando mapeo CSV del proveedor: {mapeo_dict}')
                except json.JSONDecodeError as e:
                    logger.error(f'Error parseando mapeo JSON: {e}')

            datos, errores_parseo = parser.parse_file(self.selected_file_path)

            if errores_parseo and not datos:
                errores_text = '\n'.join(errores_parseo[:5])
                self._mostrar_error(f'Error al analizar CSV:\n{errores_text}')
                return

            # Validar contra BD
            validator = AlbaranCsvValidator(self.db)
            self.parse_result = validator.validar_datos(datos)

            # Mostrar resumen
            self._mostrar_resumen()

            # Cargar datos en tabla
            self._cargar_preview_tabla()

            # Habilitar continuar si hay líneas válidas
            if self.parse_result.lineas:
                self.btn_continuar.configure(state='normal')

            logger.info(
                f'CSV analizado: {len(self.parse_result.lineas)} líneas, '
                f'{len(self.parse_result.productos_existentes)} existentes, '
                f'{len(self.parse_result.productos_nuevos)} nuevos'
            )

        except Exception as e:
            logger.exception('Error analizando CSV')
            self._mostrar_error(f'Error al analizar: {e}')

    def _mostrar_resumen(self):
        """Mostrar resumen del análisis."""
        existentes = len(self.parse_result.productos_existentes)
        nuevos = len(self.parse_result.productos_nuevos)
        total = len(self.parse_result.lineas)

        # Calcular totales
        totales = self.parse_result.totales
        total_str = f'{totales.get("total", Decimal("0")):.2f} €'

        resumen_text = (
            f'Total: {total} líneas | '
            f'Existentes: {existentes} | '
            f'Nuevos: {nuevos} | '
            f'Total albarán: {total_str}'
        )

        # Verificar que los widgets existen antes de usarlos
        if hasattr(self, 'lbl_resumen') and hasattr(self.lbl_resumen, 'winfo_exists'):
            try:
                if self.lbl_resumen.winfo_exists():
                    self.lbl_resumen.configure(text=resumen_text)
            except Exception:
                pass

        if hasattr(self, 'resumen_frame') and hasattr(self.resumen_frame, 'winfo_exists'):
            try:
                if self.resumen_frame.winfo_exists():
                    self.resumen_frame.pack(fill='x', padx=20, pady=5)
            except Exception:
                pass

    def _cargar_preview_tabla(self):
        """Cargar las líneas del CSV en la tabla NavList."""
        self.nav_list.clear_items()

        for linea in self.parse_result.lineas:
            # Estado con color visual
            if linea.existe_en_bd:
                estado = '✓ OK'
            else:
                estado = '✗ NUEVO'

            # Formatear valores (usar propiedades que devuelven Decimal)
            coste_str = f'{linea.coste_cents / 100:.2f}'
            dto_str = f'{linea.descuento_cents / 100:.2f}' if linea.descuento_cents else '-'
            importe_str = f'{linea.importe_cents / 100:.2f}' if linea.importe_cents else '-'
            pvpr_str = f'{linea.pvpr_cents / 100:.2f}' if hasattr(linea, 'pvpr_cents') and linea.pvpr_cents else '-'
            editorial = getattr(linea, 'editorial', '') or '-'
            fabricante = getattr(linea, 'fabricante', '') or '-'

            # NavList espera un diccionario con keys que coincidan con columnas
            row_data = {
                'EAN': linea.ean,
                'NOMBRE': linea.nombre[:40],  # Limitar longitud
                'UDS': str(linea.cantidad),
                'COSTE': coste_str,
                'DTO': dto_str,
                'IVA': f'{linea.tipo_iva}%',
                'IMPORTE': importe_str,
                'EDITORIAL': editorial[:30],
                'FABRICANTE': fabricante[:30],
                'PVPR': pvpr_str,
                'ESTADO': estado
            }

            self.nav_list.add_item(row_data)

    def _on_continuar_click(self):
        """Continuar a crear productos o guardar directamente (cabecera ya está en la primera vista)."""
        if not self.parse_result:
            return

        # Validar que tenemos proveedor y número de albarán
        proveedor_id = self.combo_proveedor_import.get_id()
        if not proveedor_id:
            self._mostrar_error('Selecciona un proveedor')
            return

        num_albaran = self.entry_num_albaran.get().strip()
        if not num_albaran:
            self._mostrar_error('Introduce un número de albarán')
            return

        # Guardar datos de cabecera
        prov_nombre = self.combo_proveedor_import._var.get().strip()
        self._cabecera_data = {
            'num_albaran': num_albaran,
            'fecha': self.entry_fecha_albaran.get().strip(),
            'proveedor_id': proveedor_id,
            'proveedor_nombre': prov_nombre
        }

        logger.info(f'Cabecera configurada: {self._cabecera_data}')

        # Ahora ir a crear productos nuevos si los hay
        nuevos = len(self.parse_result.productos_nuevos)
        if nuevos > 0:
            self._iniciar_creacion_productos()
        else:
            # Si no hay productos nuevos, ir directamente a la vista de guardar
            self._mostrar_ui_guardar_albaran()

    def _set_next_num(self):
        """Obtener el siguiente número de albarán disponible."""
        try:
            from kool_tpv.base_datos.albaran_service import AlbaranService
            albaran_service = AlbaranService(self.db)
            next_num = albaran_service.get_next_num_albaran()
            self.entry_num_albaran.delete(0, 'end')
            self.entry_num_albaran.insert(0, str(next_num))
        except Exception:
            logger.exception('Error obteniendo siguiente num_albaran')

    def _cargar_proveedores_import(self):
        """Cargar proveedores para el selector de importación."""
        try:
            if self.db:
                from kool_tpv.base_datos.proveedor_service import ProveedorService
                prov_service = ProveedorService(self.db)
                proveedores = prov_service.get_all_proveedores()
                opts = [(p['id'], p['nombre']) for p in proveedores]
                self.combo_proveedor_import.set_options(opts)
        except Exception:
            logger.exception('Error cargando proveedores para importación')

    def _on_proveedor_seleccionado(self, proveedor_nombre):
        """Callback cuando se selecciona un proveedor."""
        # Obtener ID del proveedor seleccionado
        proveedor_id = self.combo_proveedor_import.get_id()
        self._proveedor_seleccionado_id = proveedor_id
        self._proveedor_seleccionado_nombre = proveedor_nombre

        # Cargar mapeo CSV del proveedor
        if proveedor_id and self.db:
            try:
                from kool_tpv.base_datos.proveedor_service import ProveedorService
                prov_service = ProveedorService(self.db)
                mapeo = prov_service.get_mapeo_csv(proveedor_id)
                self._mapeo_proveedor = mapeo
                logger.info(f'Mapeo CSV cargado para proveedor {proveedor_id}: {mapeo}')
            except Exception:
                logger.exception(f'Error cargando mapeo CSV para proveedor {proveedor_id}')
                self._mapeo_proveedor = None

        # Habilitar botón de seleccionar CSV
        if proveedor_id:
            self.btn_seleccionar.configure(state='normal')
        else:
            self.btn_seleccionar.configure(state='disabled')

    def _iniciar_creacion_productos(self):
        """Mostrar UI de creación de productos."""
        logger.info(f'Iniciando creación de {len(self.parse_result.productos_nuevos)} productos')

        # Inicializar datos de productos en memoria
        self._productos_data = {}
        for linea in self.parse_result.productos_nuevos:
            self._productos_data[linea.ean] = {
                'ean': linea.ean,
                'nombre': linea.nombre,
                'coste': linea.coste_cents / 100,  # Convertir a euros para UI
                'tipo_iva': linea.tipo_iva,
                'cantidad': getattr(linea, 'cantidad', 1),
                'categoria': None,
                'tipo': None,
                'pvp': None,
                'sku': '',
                'completado': False
            }

        self._current_producto_idx = 0
        self._cargar_categorias_tipos()
        self._mostrar_ui_creacion_productos()

    def _cargar_categorias_tipos(self):
        """Cargar categorías y tipos desde la base de datos usando repositories."""
        self._categorias = []
        self._tipos = []

        try:
            if self.db:
                # Usar repositories
                from kool_tpv.modulos.almacen.categoria_repository import CategoriaRepository
                from kool_tpv.modulos.almacen.tipo_repository import TipoRepository

                cat_repo = CategoriaRepository(self.db)
                tipo_repo = TipoRepository(self.db)

                # Cargar categorías
                cats = cat_repo.get_all()
                self._categorias = [(c['id'], c['nombre']) for c in cats]

                # Cargar tipos
                tipos = tipo_repo.get_all()
                self._tipos = [(t['id'], t['nombre']) for t in tipos]

            logger.info(f'Cargadas {len(self._categorias)} categorías y {len(self._tipos)} tipos')
        except Exception:
            logger.exception('Error cargando categorías/tipos')
            self._categorias = []
            self._tipos = []

    def _mostrar_ui_creacion_productos(self):
        """Mostrar UI para completar datos de productos nuevos."""
        # Cargar configuración de fuentes
        font_config = load_font_config()
        title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})
        entry_font = font_config.get('entry', {'family': 'Courier New', 'size': 14})
        small_font = font_config.get('default', {'family': 'Courier New', 'size': 12})

        # Limpiar container y reconstruir UI
        for widget in self.container.winfo_children():
            widget.destroy()

        total = len(self._productos_data)

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container,
            text=f'COMPLETAR {total} PRODUCTOS NUEVOS',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(title_font['family'], title_font['size'], title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(10, 5))

        # Label de progreso
        self.lbl_progreso = ctk.CTkLabel(
            self.container,
            text=f'Completados: 0/{total}',
            text_color=self.colors.get('text_secondary', '#888888'),
            font=(small_font['family'], small_font['size'])
        )
        self.lbl_progreso.pack(pady=5)

        # Tabla de productos
        self.nav_list_crear = VirtualNavList(
            self.container,
            columns=[('EAN', 120), ('NOMBRE', 300), ('ESTADO', 100)],
            module_name=self.module_name,
            keyboard_manager=None,
            on_select=self._on_seleccionar_producto,
        )
        self.nav_list_crear.pack(fill='both', expand=True, padx=20, pady=5)

        # Cargar productos en tabla
        self._cargar_tabla_productos_nuevos()

        # Panel de edición
        panel_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        panel_frame.pack(fill='x', padx=20, pady=10)

        # EAN (solo lectura)
        row1 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row1.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row1, text='EAN:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.entry_ean = ctk.CTkEntry(row1, font=(entry_font['family'], entry_font['size']), state='readonly', width=200)
        self.entry_ean.pack(side='left', padx=5)

        # Nombre (editable)
        row2 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row2.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row2, text='Nombre:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.entry_nombre = ctk.CTkEntry(row2, font=(entry_font['family'], entry_font['size']), width=400)
        self.entry_nombre.pack(side='left', padx=5, fill='x', expand=True)

        # SKU
        row_sku = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row_sku.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row_sku, text='SKU:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.entry_sku = ctk.CTkEntry(row_sku, font=(entry_font['family'], entry_font['size']), width=150, placeholder_text='Opcional')
        self.entry_sku.pack(side='left', padx=5)

        # Categoría
        row3 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row3.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row3, text='Categoría:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.combo_categoria = SearchableCombo(
            row3,
            options=self._categorias,
            placeholder='Buscar categoría...',
            width=250,
            module_name=self.module_name
        )
        self.combo_categoria.pack(side='left', padx=5)

        # Tipo
        row4 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row4.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row4, text='Tipo:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.combo_tipo = SearchableCombo(
            row4,
            options=self._tipos,
            placeholder='Buscar tipo...',
            width=250,
            module_name=self.module_name
        )
        self.combo_tipo.pack(side='left', padx=5)

        # PVP
        row5 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row5.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row5, text='PVP:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')
        self.entry_pvp = ctk.CTkEntry(row5, font=(entry_font['family'], entry_font['size']), width=100, placeholder_text='0.00')
        self.entry_pvp.pack(side='left', padx=5)
        ctk.CTkLabel(row5, text='€', font=(label_font['family'], label_font['size'])).pack(side='left')

        # Conversión de unidades (para casos como Magic: 1 caja = 36 sobres)
        row_conv = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row_conv.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(row_conv, text='CONV:', font=(label_font['family'], label_font['size']), width=80, anchor='e').pack(side='left')

        self.chk_convertir = ctk.CTkCheckBox(
            row_conv,
            text='Convertir unidades',
            font=(small_font['family'], small_font['size']),
            checkbox_width=18,
            checkbox_height=18,
            command=self._on_cambio_conversion
        )
        self.chk_convertir.pack(side='left', padx=5)

        self.entry_factor = ctk.CTkEntry(row_conv, font=(entry_font['family'], entry_font['size']), width=60, placeholder_text='1')
        self.entry_factor.pack(side='left', padx=5)
        self.entry_factor.configure(state='disabled')
        self.entry_factor.bind('<KeyRelease>', self._on_calcular_stock)

        ctk.CTkLabel(row_conv, text='uds/caja → Stock:', font=(small_font['family'], small_font['size'])).pack(side='left')
        self.lbl_stock_calc = ctk.CTkLabel(row_conv, text='0', font=(entry_font['family'], entry_font['size'], 'bold'), text_color='#00aa00')
        self.lbl_stock_calc.pack(side='left', padx=5)

        # Info del CSV
        row6 = ctk.CTkFrame(panel_frame, fg_color='transparent')
        row6.pack(fill='x', padx=10, pady=5)
        self.lbl_info_csv = ctk.CTkLabel(row6, text='', font=(small_font['family'], small_font['size']), text_color='#888888')
        self.lbl_info_csv.pack(side='left', padx=85)

        # Botones de acción
        btn_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        btn_frame.pack(fill='x', padx=20, pady=10)

        self.btn_guardar = ButtonFactory.create_button(
            parent=btn_frame,
            text='GUARDAR Y SIGUIENTE',
            command=self._on_guardar_producto,
            style_key='action_confirm'
        )
        self.btn_guardar.pack(side='left', padx=5)

        self.btn_crear_todos = ButtonFactory.create_button(
            parent=btn_frame,
            text=f'CREAR {total} PRODUCTOS',
            command=self._on_crear_todos_productos,
            style_key='action_success'
        )
        self.btn_crear_todos.pack(side='right', padx=5)
        self.btn_crear_todos.configure(state='disabled')

        btn_borrador = ButtonFactory.create_button(
            parent=btn_frame,
            text='GUARDAR BORRADOR',
            command=self._on_guardar_borrador_click,
            style_key='action_secondary'
        )
        btn_borrador.pack(side='left', padx=5)

        btn_volver = ButtonFactory.create_button(
            parent=btn_frame,
            text='VOLVER',
            command=self._on_volver_desde_creacion,
            style_key='action_secondary'
        )
        btn_volver.pack(side='right', padx=5)

        # Seleccionar primer producto
        self._seleccionar_producto_por_idx(0)

    def _cargar_tabla_productos_nuevos(self):
        """Cargar productos nuevos en la tabla de creación."""
        self.nav_list_crear.clear_items()

        for ean, data in self._productos_data.items():
            if data['completado']:
                estado = '✓ OK'
            else:
                estado = 'PENDIENTE'

            row = {
                'EAN': ean,
                'NOMBRE': data['nombre'][:40],
                'ESTADO': estado
            }
            self.nav_list_crear.add_item(row)

    def _on_seleccionar_producto(self, row_data):
        """Seleccionar producto de la tabla para editar.

        Args:
            row_data: Dict con los datos de la fila seleccionada (EAN, NOMBRE, ESTADO)
        """
        ean = row_data.get('EAN')
        if not ean:
            return

        # Encontrar índice del producto
        items = list(self._productos_data.items())
        for idx, (key, data) in enumerate(items):
            if key == ean:
                self._seleccionar_producto_por_idx(idx)
                return

    def _seleccionar_producto_por_idx(self, index):
        """Seleccionar producto por índice y cargar en panel."""
        items = list(self._productos_data.items())
        if index < 0 or index >= len(items):
            return

        self._current_producto_idx = index
        ean, data = items[index]

        # Cargar datos en panel
        self.entry_ean.configure(state='normal')
        self.entry_ean.delete(0, 'end')
        self.entry_ean.insert(0, ean)
        self.entry_ean.configure(state='readonly')

        self.entry_nombre.delete(0, 'end')
        self.entry_nombre.insert(0, data['nombre'])

        # SKU
        self.entry_sku.delete(0, 'end')
        if data.get('sku'):
            self.entry_sku.insert(0, data['sku'])

        # Categoría - SearchableCombo usa entry con texto
        if data['categoria']:
            cat_nombre = next((c[1] for c in self._categorias if c[0] == data['categoria']), '')
            self.combo_categoria._var.set(cat_nombre)
        else:
            self.combo_categoria._var.set('')

        # Tipo
        if data['tipo']:
            tipo_nombre = next((t[1] for t in self._tipos if t[0] == data['tipo']), '')
            self.combo_tipo._var.set(tipo_nombre)
        else:
            self.combo_tipo._var.set('')

        # PVP
        self.entry_pvp.delete(0, 'end')
        if data['pvp']:
            self.entry_pvp.insert(0, f"{data['pvp']:.2f}")

        # Info CSV
        cantidad_original = data.get('cantidad', 1)
        coste_display = data.get('coste', 0)
        if isinstance(coste_display, int):
            coste_display = coste_display / 100  # Convertir céntimos a euros
        info = f"Cantidad albarán: {cantidad_original} | Coste: {coste_display:.2f}€ | IVA: {data['tipo_iva']}%"
        self.lbl_info_csv.configure(text=info)

        # Conversión de unidades - cargar valores guardados o default
        if data.get('completado') and data.get('convertir'):
            # Producto ya completado con conversión
            self.chk_convertir.select()
            self.entry_factor.configure(state='normal')
            factor = data.get('factor_conversion', 1)
            self.entry_factor.delete(0, 'end')
            self.entry_factor.insert(0, str(factor))
            cantidad_final = data.get('cantidad_final', cantidad_original)
            self.lbl_stock_calc.configure(text=str(cantidad_final))
        else:
            # Default: sin conversión (factor 0 para productos nuevos)
            self.chk_convertir.deselect()
            self.entry_factor.delete(0, 'end')
            self.entry_factor.insert(0, '0')
            self.entry_factor.configure(state='disabled')
            self.lbl_stock_calc.configure(text=str(cantidad_original))

        # Seleccionar en tabla visualmente
        self.nav_list_crear._select(index)

    def _on_guardar_producto(self):
        """Guardar datos del producto actual y pasar al siguiente."""
        items = list(self._productos_data.items())
        if self._current_producto_idx >= len(items):
            return

        ean, data = items[self._current_producto_idx]

        # Validar datos
        nombre = self.entry_nombre.get().strip()
        sku = self.entry_sku.get().strip()
        categoria_nombre = self.combo_categoria._var.get().strip()
        tipo_nombre = self.combo_tipo._var.get().strip()
        pvp_str = self.entry_pvp.get().strip()

        if not nombre:
            self._mostrar_error('El nombre es obligatorio')
            return
        if not categoria_nombre:
            self._mostrar_error('Selecciona una categoría')
            return
        if not tipo_nombre:
            self._mostrar_error('Selecciona un tipo')
            return
        if not pvp_str:
            self._mostrar_error('El PVP es obligatorio')
            return

        try:
            pvp = Decimal(pvp_str.replace(',', '.'))
        except Exception:
            self._mostrar_error('PVP inválido')
            return

        # Buscar IDs por nombre
        categoria_id = next((c[0] for c in self._categorias if c[1] == categoria_nombre), None)
        tipo_id = next((t[0] for t in self._tipos if t[1] == tipo_nombre), None)

        if categoria_id is None:
            self._mostrar_error(f'Categoría "{categoria_nombre}" no válida')
            return
        if tipo_id is None:
            self._mostrar_error(f'Tipo "{tipo_nombre}" no válido')
            return

        # Calcular conversión de unidades
        cantidad_original = data.get('cantidad', 1)
        convertir = self.chk_convertir.get()
        factor = self._get_factor_conversion() if convertir else 1
        cantidad_final = cantidad_original * factor

        # Guardar en memoria
        self._productos_data[ean] = {
            'ean': ean,
            'nombre': nombre,
            'sku': sku,
            'coste': data['coste'] / 100 if isinstance(data['coste'], int) else data['coste'],  # Convertir si es céntimos
            'tipo_iva': data['tipo_iva'],
            'categoria': categoria_id,
            'tipo': tipo_id,
            'pvp': pvp,
            'completado': True,
            # Conversión de unidades
            'cantidad_original': cantidad_original,
            'convertir': convertir,
            'factor_conversion': factor,
            'cantidad_final': cantidad_final
        }

        # Actualizar tabla
        self._cargar_tabla_productos_nuevos()

        # Actualizar progreso
        completados = sum(1 for d in self._productos_data.values() if d['completado'])
        total = len(self._productos_data)
        self.lbl_progreso.configure(text=f'Completados: {completados}/{total}')

        # Habilitar botón crear todos si todos completados
        if completados == total:
            self.btn_crear_todos.configure(state='normal')
            show_success(self.container, 'Completado', '¡Todos los productos completados! Puedes crearlos ahora.')

        # Pasar al siguiente
        siguiente = self._current_producto_idx + 1
        if siguiente < total:
            self._seleccionar_producto_por_idx(siguiente)
        else:
            # Volver al primero pendiente si hay
            for i, (e, d) in enumerate(items):
                if not d['completado']:
                    self._seleccionar_producto_por_idx(i)
                    break

        logger.info(f'Producto {ean} guardado en memoria')

    def _on_crear_todos_productos(self):
        """Crear todos los productos en la base de datos usando el repository."""
        try:
            from kool_tpv.modulos.almacen.producto_repository import ProductoRepository

            completados = [d for d in self._productos_data.values() if d['completado']]
            if not completados:
                self._mostrar_error('No hay productos completados para crear')
                return

            logger.info(f'Creando {len(completados)} productos en la BD via repository...')

            repo = ProductoRepository(self.db)
            creados = 0

            for data in completados:
                try:
                    # Usar cantidad_final (con conversión aplicada) como stock
                    stock_producto = data.get('cantidad_final', 1)

                    # Obtener proveedor_id de la cabecera
                    proveedor_id = getattr(self, '_cabecera_data', {}).get('proveedor_id')

                    # Usar guardar_producto_completo del repository
                    producto_id = repo.guardar_producto_completo(
                        nombre=data['nombre'],
                        nombre_boton=data['nombre'][:20],  # Nombre corto para botón
                        sku=data.get('sku', ''),  # SKU introducido por usuario
                        categoria_id=data['categoria'],
                        tipo_id=data['tipo'],
                        proveedor_id=proveedor_id,  # Proveedor de la cabecera
                        iva=data['tipo_iva'],
                        stock_actual=stock_producto,  # Stock ya convertido
                        stock_min=0,
                        activo=1,
                        pvp=data.get('pvp', 0),
                        coste=data['coste'] / 100 if isinstance(data['coste'], int) else data['coste'],
                        codigos_barras=[data['ean']],  # EAN como código de barras
                    )
                    # Guardar el ID del producto creado para las líneas del albarán
                    data['producto_id'] = producto_id
                    creados += 1
                    logger.info(f'Producto creado: {data["ean"]} -> ID {producto_id}')
                except Exception as e:
                    logger.error(f'Error creando producto {data["ean"]}: {e}')

            if creados == len(completados):
                show_success(self.container, 'Éxito', f'✓ {creados} productos creados correctamente')
                # Ir a vista previa del albarán para guardarlo
                self._mostrar_ui_vista_previa_albaran()
            else:
                show_error(self.container, 'Error', f'Creados {creados} de {len(completados)} productos')

        except Exception:
            logger.exception('Error creando productos')
            show_error(self.container, 'Error', 'Error al crear productos en la base de datos')

    def _mostrar_ui_vista_previa_albaran(self):
        """Mostrar vista previa del albarán con cabecera y líneas antes de guardar."""
        # Cargar configuración de fuentes
        font_config = load_font_config()
        title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        subtitle_font = font_config.get('subtitle', {'family': 'Courier New', 'size': 20, 'weight': 'bold'})

        # Limpiar container
        for widget in self.container.winfo_children():
            widget.destroy()

        cabecera = getattr(self, '_cabecera_data', {})
        totales = self.parse_result.totales

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container,
            text='VISTA PREVIA DEL ALBARÁN',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(title_font['family'], title_font['size'], title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(20, 10))

        # Frame de cabecera
        header_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        header_frame.pack(fill='x', padx=20, pady=5)

        header_text = (
            f"Proveedor: {cabecera.get('proveedor_nombre', 'N/A')}  |  "
            f"Nº Albarán: {cabecera.get('num_albaran', 'N/A')}  |  "
            f"Fecha: {cabecera.get('fecha', 'N/A')}\n"
            f"Total: {totales.get('total', Decimal('0')):.2f} €  |  "
            f"Líneas: {len(self.parse_result.lineas)}"
        )
        # Usar fuente del font_config para el resumen
        ctk.CTkLabel(
            header_frame,
            text=header_text,
            font=(subtitle_font['family'], subtitle_font['size'], subtitle_font.get('weight', 'normal')),
            justify='left'
        ).pack(pady=10, padx=15)

        # Tabla de líneas con NavList (todas las columnas de BD)
        self.nav_list_albaran = VirtualNavList(
            self.container,
            columns=[
                ('EAN', 120), ('NOMBRE', 200), ('UDS', 50),
                ('COSTE', 70), ('DTO', 50), ('IVA', 40),
                ('IMPORTE', 70), ('EDITORIAL', 100), ('FABRICANTE', 100),
                ('PVPR', 60), ('ESTADO', 80)
            ],
            module_name=self.module_name,
            keyboard_manager=None
        )
        self.nav_list_albaran.pack(fill='both', expand=True, padx=20, pady=10)

        # Cargar líneas en la tabla
        self._cargar_lineas_albaran_preview()

        # Botones
        btn_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        btn_frame.pack(pady=15)

        btn_guardar = ButtonFactory.create_button(
            parent=btn_frame,
            text='GUARDAR ALBARÁN',
            command=self._on_guardar_albaran_final,
            style_key='action_success'
        )
        btn_guardar.pack(side='left', padx=10)

        btn_cancelar = ButtonFactory.create_button(
            parent=btn_frame,
            text='CANCELAR',
            command=self._on_volver_desde_creacion,
            style_key='action_secondary'
        )
        btn_cancelar.pack(side='left', padx=10)

    def _cargar_lineas_albaran_preview(self):
        """Cargar las líneas del CSV en la tabla de vista previa."""
        self.nav_list_albaran.clear_items()

        for linea in self.parse_result.lineas:
            coste_str = f'{linea.coste_cents / 100:.2f}' if linea.coste_cents else '0.00'
            dto_str = f'{linea.descuento_cents / 100:.2f}' if linea.descuento_cents else '0.00'
            importe_str = f'{linea.importe_cents / 100:.2f}' if linea.importe_cents else '0.00'
            pvpr_str = f'{linea.pvpr_cents / 100:.2f}' if hasattr(linea, 'pvpr_cents') and linea.pvpr_cents else '-'
            editorial = getattr(linea, 'editorial', '') or '-'
            fabricante = getattr(linea, 'fabricante', '') or '-'

            # Estado
            if linea.existe_en_bd:
                estado = '✓ OK'
            else:
                estado = '✗ NUEVO'

            row_data = {
                'EAN': linea.ean,
                'NOMBRE': linea.nombre[:35],
                'UDS': str(linea.cantidad),
                'COSTE': coste_str,
                'DTO': dto_str,
                'IVA': f'{linea.tipo_iva}%',
                'IMPORTE': importe_str,
                'EDITORIAL': editorial[:30],
                'FABRICANTE': fabricante[:30],
                'PVPR': pvpr_str,
                'ESTADO': estado
            }
            self.nav_list_albaran.add_item(row_data)

    def _mostrar_ui_guardar_albaran(self):
        """Mostrar UI final cuando no hay productos nuevos (todos existen)."""
        # Es el mismo flujo: mostrar vista previa
        self._mostrar_ui_vista_previa_albaran()

    def _on_guardar_albaran_final(self):
        """Guardar el albarán completo en la base de datos usando AlbaranRepository."""
        try:
            from kool_tpv.modulos.almacen.albaran_repository import AlbaranRepository

            cabecera = getattr(self, '_cabecera_data', {})
            if not cabecera:
                self._mostrar_error('No hay datos de cabecera')
                return

            # Preparar líneas para el repository
            lineas_repo = []
            for linea in self.parse_result.lineas:
                # Buscar producto_id (productos nuevos ya tienen ID, existentes hay que buscar)
                producto_id = None
                es_producto_nuevo = False
                if hasattr(self, '_productos_data') and linea.ean in self._productos_data:
                    producto_id = self._productos_data[linea.ean].get('producto_id')
                    es_producto_nuevo = True  # Viene de productos_data = producto nuevo
                # Si no está en productos nuevos, buscar en productos_existentes
                if not producto_id:
                    for prod in self.parse_result.productos_existentes:
                        if prod.ean == linea.ean:
                            producto_id = prod.producto_id
                            break

                lineas_repo.append({
                    'producto_id': producto_id,
                    'ean': linea.ean,
                    'nombre': linea.nombre,
                    'cantidad': linea.cantidad,
                    'coste': linea.coste_cents,
                    'descuento': linea.descuento_cents,
                    'importe': linea.importe_cents,
                    'tipo_iva': linea.tipo_iva,
                    'editorial': getattr(linea, 'editorial', ''),
                    'fabricante': getattr(linea, 'fabricante', ''),
                    'pvpr_cents': getattr(linea, 'pvpr_cents', 0),
                    'es_producto_nuevo': es_producto_nuevo
                })

            # Preparar totales (convertir de euros a céntimos)
            from kool_tpv.base_datos.money_adapter import prepare_for_db
            totales = self.parse_result.totales
            totales_repo = {
                'total_neto': prepare_for_db(totales.get('total_neto', Decimal('0'))),
                'total_iva_4': prepare_for_db(totales.get('total_iva_4', Decimal('0'))),
                'total_iva_10': prepare_for_db(totales.get('total_iva_10', Decimal('0'))),
                'total_iva_21': prepare_for_db(totales.get('total_iva_21', Decimal('0'))),
                'total': prepare_for_db(totales.get('total', Decimal('0')))
            }

            # Usar repository para guardar
            repo = AlbaranRepository(self.db)
            albaran_id = repo.guardar_albaran_completo(
                num_albaran=cabecera.get('num_albaran'),
                proveedor_id=cabecera.get('proveedor_id'),
                fecha=cabecera.get('fecha'),
                tipo='ENTRADA',
                lineas=lineas_repo,
                totales=totales_repo
            )

            # Eliminar borrador si existe
            if getattr(self, '_borrador_path', None):
                self._borrador_service.eliminar(self._borrador_path)
                self._borrador_path = None
            show_success(self.container, 'Éxito', f'Albarán guardado correctamente (ID: {albaran_id})')
            self._on_volver_desde_creacion()

        except Exception as e:
            logger.exception('Error guardando albarán')
            show_error(self.container, 'Error', f'Error al guardar albarán: {e}')

    def _on_volver_desde_creacion(self):
        """Volver desde la pantalla de creación a la de preview."""
        # Limpiar y recargar la UI original
        for widget in self.container.winfo_children():
            widget.destroy()
        self._setup_ui()
        # Recargar datos si hay
        if self.selected_file_path and self.parse_result:
            self._mostrar_resumen()
            self._cargar_preview_tabla()
            self.btn_continuar.configure(state='normal')

    def _on_guardar_borrador_click(self):
        """Guardar estado actual como borrador JSON."""
        try:
            cabecera = getattr(self, '_cabecera_data', {})
            if not cabecera:
                proveedor_id = self.combo_proveedor_import.get_id()
                prov_nombre = self.combo_proveedor_import._var.get().strip()
                num_albaran = self.entry_num_albaran.get().strip()
                fecha = self.entry_fecha_albaran.get().strip()
                cabecera = {
                    'num_albaran': num_albaran,
                    'fecha': fecha,
                    'proveedor_id': proveedor_id,
                    'proveedor_nombre': prov_nombre
                }
            paso = 'completar_productos' if getattr(self, '_productos_data', {}) else 'preview'
            path = self._borrador_service.guardar(
                cabecera=cabecera,
                productos_data=getattr(self, '_productos_data', {}),
                csv_path=self.selected_file_path,
                paso=paso
            )
            self._borrador_path = path
            show_success(self.container, 'Borrador guardado', f'Albarán {cabecera.get("num_albaran", "")} guardado como borrador.')
        except Exception:
            logger.exception('Error guardando borrador')
            show_error(self.container, 'Error', 'No se pudo guardar el borrador.')

    def cargar_borrador(self, borrador_info: dict):
        """Carga un borrador y restaura el estado de la UI.

        Args:
            borrador_info: dict devuelto por AlbaranBorradorService.listar()
        """
        try:
            data = self._borrador_service.cargar(borrador_info['path'])
            self._borrador_path = borrador_info['path']

            # Restaurar archivo CSV
            csv_path = data.get('csv_path', '')
            if csv_path:
                self.selected_file_path = csv_path
                from pathlib import Path as _Path
                self.lbl_archivo.configure(
                    text=_Path(csv_path).name,
                    text_color=self.colors.get('text', '#00FF00')
                )

            # Restaurar cabecera
            cabecera = data.get('cabecera', {})
            self._cabecera_data = cabecera

            # Restaurar proveedor en combo y cargar su mapeo CSV
            prov_id = cabecera.get('proveedor_id')
            prov_nombre = cabecera.get('proveedor_nombre', '')
            if prov_nombre:
                self.combo_proveedor_import._var.set(prov_nombre)
            if prov_id:
                self._proveedor_seleccionado_id = prov_id
                self.btn_seleccionar.configure(state='normal')
                # Cargar mapeo del proveedor explícitamente
                if self.db:
                    try:
                        from kool_tpv.base_datos.proveedor_service import ProveedorService
                        prov_service = ProveedorService(self.db)
                        mapeo = prov_service.get_mapeo_csv(prov_id)
                        self._mapeo_proveedor = mapeo
                    except Exception:
                        logger.warning('No se pudo cargar mapeo del proveedor al restaurar borrador')

            # Restaurar num_albaran y fecha
            self.entry_num_albaran.delete(0, 'end')
            self.entry_num_albaran.insert(0, cabecera.get('num_albaran', ''))
            self.entry_fecha_albaran.configure(state='normal')
            self.entry_fecha_albaran.delete(0, 'end')
            self.entry_fecha_albaran.insert(0, cabecera.get('fecha', ''))
            self.entry_fecha_albaran.configure(state='readonly')

            # Restaurar productos_data si los hay
            productos_data = data.get('productos_data', {})
            if productos_data:
                self._productos_data = productos_data

            # Re-analizar el CSV para recuperar parse_result
            if self.selected_file_path:
                self._on_analizar_click()

            # Si había productos pendientes, ir a ese paso
            paso = data.get('paso', 'preview')
            if paso == 'completar_productos' and productos_data:
                self._cargar_categorias_tipos()
                self._mostrar_ui_creacion_productos()

            logger.info(f'Borrador cargado: albarán {cabecera.get("num_albaran")}')
        except Exception:
            logger.exception('Error cargando borrador')
            show_error(self.container, 'Error', 'No se pudo cargar el borrador.')

    def _on_volver_click(self):
        """Volver a la vista anterior."""
        try:
            if self.owner and hasattr(self.owner, 'show_albaranes'):
                self.owner.show_albaranes()
            else:
                self._reset_preview()
                self.selected_file_path = None
                self.lbl_archivo.configure(
                    text='Ningún archivo seleccionado',
                    text_color=self.colors.get('text_secondary', '#888888')
                )
                self.btn_analizar.configure(state='disabled')
        except Exception:
            logger.exception('Error en volver')

    # ── MÉTODOS DE CONVERSIÓN DE UNIDADES ──────────────────────────────────

    def _on_cambio_conversion(self):
        """Callback cuando se marca/desmarca 'Convertir unidades'."""
        if self.chk_convertir.get():
            self.entry_factor.configure(state='normal')
            self._on_calcular_stock(None)
        else:
            self.entry_factor.configure(state='disabled')
            # Resetear a cantidad original
            items = list(self._productos_data.items())
            if self._current_producto_idx < len(items):
                ean, data = items[self._current_producto_idx]
                cantidad = data.get('cantidad', 1)
                self.lbl_stock_calc.configure(text=str(cantidad))

    def _on_calcular_stock(self, event):
        """Calcular y mostrar stock final al cambiar el factor."""
        try:
            items = list(self._productos_data.items())
            if self._current_producto_idx >= len(items):
                return

            ean, data = items[self._current_producto_idx]
            cantidad_original = data.get('cantidad', 1)

            if self.chk_convertir.get():
                factor = self._get_factor_conversion()
                stock_final = cantidad_original * factor
                self.lbl_stock_calc.configure(text=str(stock_final))
            else:
                self.lbl_stock_calc.configure(text=str(cantidad_original))
        except Exception:
            pass

    def _get_factor_conversion(self) -> int:
        """Leer factor de conversión del entry (default: 1)."""
        try:
            factor_str = self.entry_factor.get().strip()
            if not factor_str:
                return 1
            factor = int(factor_str)
            return max(1, factor)  # Mínimo 1
        except ValueError:
            return 1

    def _calcular_stock_final(self) -> int:
        """Calcular stock final según conversión."""
        items = list(self._productos_data.items())
        if self._current_producto_idx >= len(items):
            return 1

        ean, data = items[self._current_producto_idx]
        cantidad_original = data.get('cantidad', 1)

        if self.chk_convertir.get():
            return cantidad_original * self._get_factor_conversion()
        return cantidad_original

    def _mostrar_error(self, mensaje):
        """Mostrar mensaje de error usando diálogo del proyecto."""
        try:
            show_error(self.container, 'Error', mensaje)
        except Exception:
            logger.error(mensaje)

    def _mostrar_info(self, mensaje):
        """Mostrar mensaje informativo usando diálogo del proyecto."""
        try:
            show_info(self.container, 'Información', mensaje)
        except Exception:
            logger.info(mensaje)

    def get_widget(self):
        return self.container
