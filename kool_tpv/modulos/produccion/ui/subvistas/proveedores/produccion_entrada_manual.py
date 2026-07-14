"""UI para la entrada manual de albaranes de producción (materias primas)."""
import logging
import tkinter as tk
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import load_font_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.modulos.almacen.albaran_repository import AlbaranRepository
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService

logger = logging.getLogger(__name__)

class ProduccionEntradaManualUI:
    """UI para introducir manualmente albaranes de materias primas."""

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner

        self.lineas = [] # List[Dict] con las líneas del albarán
        
        # Servicios
        self.albaran_service = AlbaranService(db)
        self.albaran_repo = AlbaranRepository(db)
        self.stock_service = ProduccionStockBaseService(db)
        self.tipos_service = ProduccionTiposService(db)
        self.variantes_service = ProduccionTiposVariantesService(db)
        self.colores_service = ProduccionColoresService(db)
        self.tallas_service = ProduccionTallasService(db)

        try:
            self.colors = load_colors('produccion')
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        self._setup_ui()
        self._cargar_combos_iniciales()
        
        # Handler para ESC
        self._esc_handler = lambda e: self._on_volver_click()
        self._bind_esc_recursive(self.container)

    def _setup_ui(self):
        font_config = load_font_config()
        self.title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        self.label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})
        self.entry_font = font_config.get('entry', {'family': 'Courier New', 'size': 14})

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container, 
            text=f'ENTRADA MANUAL DE MATERIAS PRIMAS: {self.proveedor_nombre.upper()}',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=(self.title_font['family'], self.title_font['size'], self.title_font.get('weight', 'normal'))
        )
        lbl_titulo.pack(pady=(15, 10))

        # PANEL SUPERIOR: Cabecera Albarán
        top_panel = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        top_panel.pack(fill='x', padx=20, pady=5)
        
        cab_row = ctk.CTkFrame(top_panel, fg_color='transparent')
        cab_row.pack(fill='x', padx=10, pady=10)
        
        ctk.CTkLabel(cab_row, text='Nº Albarán:', font=(self.label_font['family'], self.label_font['size'])).pack(side='left', padx=5)
        self.entry_num = ctk.CTkEntry(cab_row, width=120, font=(self.entry_font['family'], self.entry_font['size']))
        self.entry_num.pack(side='left', padx=5)
        self.entry_num.insert(0, str(self.albaran_service.get_next_num_albaran()))

        ctk.CTkLabel(cab_row, text='Fecha:', font=(self.label_font['family'], self.label_font['size'])).pack(side='left', padx=(20, 5))
        self.entry_fecha = ctk.CTkEntry(cab_row, width=120, font=(self.entry_font['family'], self.entry_font['size']))
        self.entry_fecha.pack(side='left', padx=5)
        self.entry_fecha.insert(0, date.today().strftime('%Y-%m-%d'))

        # PANEL SELECCIÓN: Buscador de Material
        search_panel = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        search_panel.pack(fill='x', padx=20, pady=5)
        
        # Fila 1: Tipo y Variante
        row1 = ctk.CTkFrame(search_panel, fg_color='transparent')
        row1.pack(fill='x', padx=10, pady=(10, 5))
        
        ctk.CTkLabel(row1, text='Tipo:', width=60, anchor='w').pack(side='left', padx=5)
        self.combo_tipo = SearchableCombo(row1, width=250, placeholder='Selecciona tipo...', command=self._on_tipo_change)
        self.combo_tipo.pack(side='left', padx=5)
        
        ctk.CTkLabel(row1, text='Variante:', width=80, anchor='w').pack(side='left', padx=(20, 5))
        self.combo_variante = SearchableCombo(row1, width=250, placeholder='(Opcional)', command=self._on_variante_change)
        self.combo_variante.pack(side='left', padx=5)

        # Fila 2: Color y Talla
        row2 = ctk.CTkFrame(search_panel, fg_color='transparent')
        row2.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkLabel(row2, text='Color:', width=60, anchor='w').pack(side='left', padx=5)
        self.combo_color = SearchableCombo(row2, width=250, placeholder='Selecciona color...', command=self._on_color_change)
        self.combo_color.pack(side='left', padx=5)
        
        ctk.CTkLabel(row2, text='Talla:', width=80, anchor='w').pack(side='left', padx=(20, 5))
        self.combo_talla = SearchableCombo(row2, width=250, placeholder='Selecciona talla...')
        self.combo_talla.pack(side='left', padx=5)

        # Fila 3: Cantidad y Coste
        row3 = ctk.CTkFrame(search_panel, fg_color='transparent')
        row3.pack(fill='x', padx=10, pady=(5, 10))
        
        ctk.CTkLabel(row3, text='Cantidad:', width=80, anchor='w').pack(side='left', padx=5)
        self.entry_cant = ctk.CTkEntry(row3, width=80, font=(self.entry_font['family'], self.entry_font['size']))
        self.entry_cant.pack(side='left', padx=5)
        self.entry_cant.insert(0, '1')

        ctk.CTkLabel(row3, text='Coste Un.:', width=80, anchor='w').pack(side='left', padx=(20, 5))
        self.entry_coste = ctk.CTkEntry(row3, width=100, font=(self.entry_font['family'], self.entry_font['size']))
        self.entry_coste.pack(side='left', padx=5)
        self.entry_coste.insert(0, '0.00')
        ctk.CTkLabel(row3, text='€').pack(side='left')

        self.btn_anadir = ButtonFactory.create_button(
            row3, 'AÑADIR LÍNEA', self._on_anadir_click, style_key='action_confirm'
        )
        self.btn_anadir.pack(side='right', padx=10)

        # TABLA DE LÍNEAS
        self.columns = [
            ('MATERIA PRIMA', 450), ('CANT', 80), ('COSTE UN.', 100), ('TOTAL', 120)
        ]
        self.nav_list = VirtualNavList(self.container, columns=self.columns, module_name='produccion')
        self.nav_list.pack(fill='both', expand=True, padx=20, pady=10)

        # RESUMEN PANEL
        self.resumen_frame = ctk.CTkFrame(self.container, fg_color='#1a1a1a')
        self.resumen_frame.pack(fill='x', padx=20, pady=5)
        self.lbl_resumen = ctk.CTkLabel(self.resumen_frame, text='Total: 0.00€', font=(self.label_font['family'], self.label_font['size'], 'bold'))
        self.lbl_resumen.pack(pady=10, side='right', padx=20)

        # BOTONES FOOTER
        footer = ctk.CTkFrame(self.container, fg_color='transparent')
        footer.pack(fill='x', padx=20, pady=15)
        
        self.btn_guardar = ButtonFactory.create_button(
            footer, 'GUARDAR ALBARÁN', self._on_guardar_click, style_key='action_success'
        )
        self.btn_guardar.pack(side='right')
        self.btn_guardar.configure(state='disabled')
        
        self.btn_eliminar = ButtonFactory.create_button(
            footer, 'ELIMINAR LÍNEA', self._on_eliminar_linea_click, style_key='action_danger'
        )
        self.btn_eliminar.pack(side='right', padx=20)
        
        self.btn_volver = ButtonFactory.create_button(
            footer, 'VOLVER', self._on_volver_click, style_key='action_secondary'
        )
        self.btn_volver.pack(side='left')

    # --- LÓGICA DE DATOS Y COMBOS ---

    def _cargar_combos_iniciales(self):
        """Carga la lista de tipos y colores."""
        tipos = self.tipos_service.obtener_activos()
        self.tipo_map = {t.nombre: t.id for t in tipos}
        self.combo_tipo.set_options(list(self.tipo_map.keys()))
        
        colores = self.colores_service.obtener_activos()
        self.color_map = {c.nombre: c.id for c in colores}
        self.combo_color.set_options(list(self.color_map.keys()))

    def _on_tipo_change(self, nombre_tipo):
        """Al cambiar el tipo, cargar variantes asociadas."""
        self.combo_variante.clear()
        self.combo_talla.clear()
        
        tipo_id = self.tipo_map.get(nombre_tipo)
        if not tipo_id: return
        
        variantes = self.variantes_service.obtener_por_tipo(tipo_id, solo_activos=True)
        self.variante_map = {v.nombre: v.id for v in variantes}
        self.combo_variante.set_options(list(self.variante_map.keys()))
        
        # También cargar tallas si el tipo requiere talla y no hay variantes todavía
        # (algunos tipos podrían no tener variantes pero sí tallas)
        self._cargar_tallas_disponibles(tipo_id)

    def _on_variante_change(self, nombre_var):
        """Al cambiar la variante, podríamos filtrar tallas o colores si fuera necesario."""
        pass

    def _on_color_change(self, nombre_color):
        """Al cambiar el color, no solemos filtrar nada en entrada manual (queremos poder añadir cualquier talla)."""
        pass

    def _cargar_tallas_disponibles(self, tipo_id: int):
        """Cargar todas las tallas del sistema como opciones."""
        tallas = self.tallas_service.obtener_todas()
        self.talla_options = [t.nombre for t in tallas]
        self.combo_talla.set_options(self.talla_options)

    # --- ACCIONES ---

    def _on_anadir_click(self):
        """Añade la selección actual a la lista de líneas."""
        tipo_nom = self.combo_tipo.get()
        var_nom = self.combo_variante.get()
        col_nom = self.combo_color.get()
        talla_nom = self.combo_talla.get()
        
        try:
            cant = int(self.entry_cant.get())
            coste = Decimal(self.entry_coste.get().replace(',', '.'))
        except:
            ToastWidget.show(self.container, 'CANTIDAD O COSTE INVÁLIDOS', tipo='error')
            return

        if not tipo_nom or not col_nom:
            ToastWidget.show(self.container, 'SELECCIONA AL MENOS TIPO Y COLOR', tipo='error')
            return

        tipo_id = self.tipo_map.get(tipo_nom)
        var_id = self.variante_map.get(var_nom) if var_nom else None
        col_id = self.color_map.get(col_nom)
        
        # Crear descripción para la línea
        desc = f"{tipo_nom}"
        if var_nom: desc += f" / {var_nom}"
        desc += f" - {col_nom}"
        if talla_nom: desc += f" ({talla_nom})"

        nueva_linea = {
            'tipo_id': tipo_id,
            'variante_id': var_id,
            'color_id': col_id,
            'talla': talla_nom,
            'nombre': desc,
            'cantidad': cant,
            'coste': coste,
            'total': cant * coste
        }
        
        self.lineas.append(nueva_linea)
        self._actualizar_tabla()
        self._limpiar_campos_entrada()

    def has_unsaved_changes(self) -> bool:
        """Verificar si hay líneas sin guardar para mostrar el warning al salir."""
        return len(self.lineas) > 0

    def _actualizar_tabla(self):
        rows = []
        total_acum = Decimal('0.00')
        for l in self.lineas:
            rows.append({
                'MATERIA PRIMA': l['nombre'],
                'CANT': str(l['cantidad']),
                'COSTE UN.': f"{l['coste']:.2f}€",
                'TOTAL': f"{l['total']:.2f}€"
            })
            total_acum += l['total']
        
        self.nav_list.set_items(rows)
        self.lbl_resumen.configure(text=f"Total: {total_acum:.2f}€")
        
        if self.lineas:
            self.btn_guardar.configure(state='normal')
        else:
            self.btn_guardar.configure(state='disabled')

    def _limpiar_campos_entrada(self):
        # Mantenemos tipo/variante/color para facilitar entrada múltiple
        self.entry_cant.delete(0, 'end')
        self.entry_cant.insert(0, '1')

    def _on_eliminar_linea_click(self):
        idx = self.nav_list.get_selected_index()
        if idx is not None and 0 <= idx < len(self.lineas):
            self.lineas.pop(idx)
            self._actualizar_tabla()

    def _on_guardar_click(self):
        """Guarda el albarán completo y actualiza stock."""
        if not self.lineas: return
        
        num_albaran = self.entry_num.get().strip()
        fecha = self.entry_fecha.get().strip()
        
        if not num_albaran:
            ToastWidget.show(self.container, 'Nº ALBARÁN OBLIGATORIO', tipo='error')
            return

        try:
            # 1. Preparar líneas para AlbaranRepository
            lineas_albaran = []
            for l in self.lineas:
                lineas_albaran.append({
                    'producto_id': None,
                    'ean': '',
                    'nombre': l['nombre'],
                    'cantidad': l['cantidad'],
                    'coste': l['coste'],
                    'tipo_iva': 21,
                    'es_producto_nuevo': False
                })
            
            # 2. Calcular totales (neto + 21% IVA)
            total_neto = sum(l['total'] for l in self.lineas)
            total_iva = total_neto * Decimal('0.21')
            totales = {
                'total_neto': total_neto,
                'total_iva_4': 0, 'total_iva_10': 0, 'total_iva_21': total_iva,
                'total': total_neto + total_iva
            }
            
            # 3. Transacción atómica
            with self.db.transaction() as cur:
                self.albaran_repo.guardar_albaran_completo(
                    num_albaran=num_albaran,
                    proveedor_id=self.proveedor_id,
                    fecha=fecha,
                    tipo='ENTRADA_PROD',
                    lineas=lineas_albaran,
                    totales=totales,
                    cur=cur
                )
                
                for l in self.lineas:
                    self.stock_service.importar_stock(
                        tipo_id=l['tipo_id'],
                        color_id=l['color_id'],
                        talla=l['talla'],
                        cantidad_nueva=l['cantidad'],
                        coste_nuevo_eur=float(l['coste']),
                        variante_id=l['variante_id'],
                        cur=cur
                    )
            
            ToastWidget.show(self.container, "ALBARÁN GUARDADO Y STOCK ACTUALIZADO", tipo='success')
            self._on_volver_click()

        except Exception:
            logger.exception("Error guardando albarán manual")
            ToastWidget.show(self.container, "ERROR AL GUARDAR EL ALBARÁN", tipo='error')

    def _on_volver_click(self):
        if self.owner and hasattr(self.owner, 'show_proveedores'):
            self.owner.show_proveedores(proveedor_id=self.proveedor_id)

    def _bind_esc_recursive(self, widget):
        widget.bind('<Escape>', self._esc_handler)
        for child in widget.winfo_children():
            self._bind_esc_recursive(child)

    def get_widget(self):
        return self.container
