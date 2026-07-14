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
        self._editing_index = None # Índice de la línea en edición
        
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
        self._setup_tab_navigation()
        
        # Handler para ESC
        self._esc_handler = lambda e: self._on_volver_click()
        self._bind_esc_recursive(self.container)
        
        # Foco inicial en Tipo
        self.container.after(100, lambda: self.combo_tipo.entry.focus_set())

    def _setup_ui(self):
        font_config = load_font_config()
        self.title_font = font_config.get('title', {'family': 'Courier New', 'size': 22, 'weight': 'bold'})
        self.label_font = font_config.get('label', {'family': 'Courier New', 'size': 16})
        self.entry_font = font_config.get('entry', {'family': 'Courier New', 'size': 14})

        # Título
        lbl_titulo = ctk.CTkLabel(
            self.container, 
            text=f"CREANDO ALBARÁN PARA EL PROVEEDOR: {self.proveedor_nombre.upper()}",
            text_color=self.colors.get('primary', COLOR_MATRIX),
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
        root = self.container.winfo_toplevel()
        km = getattr(root, 'keyboard_manager', None)
        self.nav_list = VirtualNavList(
            self.container, 
            columns=self.columns, 
            module_name='produccion',
            keyboard_manager=km,
            on_double_click=self._on_linea_double_click
        )
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
        """Carga la lista de tipos, colores y todas las tallas del sistema."""
        self._tipos_data = {t.id: t for t in self.tipos_service.obtener_activos()}
        self.tipo_map = {t.nombre: t.id for t in self._tipos_data.values()}
        self.combo_tipo.set_options([(t.id, t.nombre) for t in self._tipos_data.values()])
        
        colores = self.colores_service.obtener_activos()
        self.color_map = {c.nombre: c.id for c in colores}
        self.combo_color.set_options([(c.id, c.nombre) for c in colores])

        tallas = self.tallas_service.obtener_todas()
        self.combo_talla.set_options([(t.id, t.nombre) for t in tallas])

    def _on_tipo_change(self, nombre_tipo):
        """Al cambiar el tipo, cargar variantes asociadas y configurar requisitos."""
        self.combo_variante.clear()
        
        tipo_id = self.tipo_map.get(nombre_tipo)
        if not tipo_id: return
        
        tipo = self._tipos_data.get(tipo_id)
        
        # 1. Configurar requisitos visuales y de validación
        req_talla = getattr(tipo, 'requiere_talla', 0) == 1
        req_color = getattr(tipo, 'requiere_color', 0) == 1
        
        if not req_color:
            self.combo_color.set('')
            
        if not req_talla:
            self.combo_talla.set('')

        # 2. Sugerir coste base
        coste_base = getattr(tipo, 'coste_base', 0.0)
        self.entry_coste.delete(0, 'end')
        self.entry_coste.insert(0, f"{coste_base:.2f}")

        # 3. Cargar variantes
        variantes = self.variantes_service.obtener_por_tipo(tipo_id, solo_activos=True)
        self.variante_map = {v.nombre: v.id for v in variantes}
        self.combo_variante.set_options([(v.id, v.nombre) for v in variantes])

    def _on_variante_change(self, nombre_var):
        """Al cambiar la variante, podríamos filtrar tallas o colores si fuera necesario."""
        pass

    def _on_color_change(self, nombre_color):
        """Al cambiar el color, no solemos filtrar nada en entrada manual."""
        pass

    # --- ACCIONES ---

    def _on_anadir_click(self):
        """Añade la selección actual a la lista de líneas."""
        tipo_nom = self.combo_tipo.get()
        var_nom = self.combo_variante.get()
        col_nom = self.combo_color.get()
        talla_nom = self.combo_talla.get()
        
        if not tipo_nom:
            ToastWidget.show(self.container, 'SELECCIONA UN TIPO', tipo='error')
            return

        tipo_id = self.tipo_map.get(tipo_nom)
        tipo = self._tipos_data.get(tipo_id)
        
        # Validar requisitos según tipo
        req_color = getattr(tipo, 'requiere_color', 0) == 1
        req_talla = getattr(tipo, 'requiere_talla', 0) == 1
        
        if req_color and not col_nom:
            ToastWidget.show(self.container, f'EL TIPO {tipo_nom} REQUIERE COLOR', tipo='error')
            return
            
        if req_talla and not talla_nom:
            ToastWidget.show(self.container, f'EL TIPO {tipo_nom} REQUIERE TALLA', tipo='error')
            return

        try:
            cant = int(self.entry_cant.get())
            coste = Decimal(self.entry_coste.get().replace(',', '.'))
        except:
            ToastWidget.show(self.container, 'CANTIDAD O COSTE INVÁLIDOS', tipo='error')
            return

        var_id = self.variante_map.get(var_nom) if var_nom else None
        col_id = self.color_map.get(col_nom) if col_nom else None
        
        # Crear descripción para la línea (solo lo seleccionado)
        desc = f"{tipo_nom}"
        if var_nom: desc += f" / {var_nom}"
        if col_nom: desc += f" - {col_nom}"
        if talla_nom: desc += f" ({talla_nom})"

        nueva_linea = {
            'tipo_id': tipo_id,
            'variante_id': var_id,
            'color_id': col_id,
            'talla': talla_nom if talla_nom else "",
            'nombre': desc,
            'cantidad': cant,
            'coste': coste,
            'total': cant * coste
        }
        
        if self._editing_index is not None:
            self.lineas[self._editing_index] = nueva_linea
            self._editing_index = None
            self.btn_anadir.configure(text='AÑADIR LÍNEA')
        else:
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
        """Limpia todos los campos y resetea el estado de edición."""
        self.combo_tipo.set('')
        self.combo_variante.clear()
        self.combo_talla.clear()
        self.combo_color.set('')
        self.entry_cant.delete(0, 'end')
        self.entry_cant.insert(0, '1')
        self.entry_coste.delete(0, 'end')
        self.entry_coste.insert(0, '0.00')
        self._editing_index = None
        self.btn_anadir.configure(text='AÑADIR LÍNEA')
        self.combo_tipo.entry.focus_set()

    def _on_linea_double_click(self, item_data):
        """Al hacer doble clic en una línea, cargarla para editar."""
        idx = self.nav_list.selected_index
        if idx is not None and 0 <= idx < len(self.lineas):
            linea = self.lineas[idx]
            self._editing_index = idx
            
            # 1. Cargar Tipo y disparar su lógica (variantes, requisitos, coste base)
            tipo_id = linea['tipo_id']
            tipo = self._tipos_data.get(tipo_id)
            if tipo:
                self.combo_tipo.set(tipo.nombre)
                self._on_tipo_change(tipo.nombre)
            
            # 2. Cargar Variante
            if linea['variante_id']:
                # Buscar nombre por ID en el mapa recién cargado por _on_tipo_change
                for name, vid in self.variante_map.items():
                    if vid == linea['variante_id']:
                        self.combo_variante.set(name)
                        break
            
            # 3. Cargar Color
            if linea['color_id']:
                for name, cid in self.color_map.items():
                    if cid == linea['color_id']:
                        self.combo_color.set(name)
                        break
            
            # 4. Cargar Talla y otros campos
            self.combo_talla.set(linea['talla'])
            self.entry_cant.delete(0, 'end')
            self.entry_cant.insert(0, str(linea['cantidad']))
            self.entry_coste.delete(0, 'end')
            self.entry_coste.insert(0, f"{linea['coste']:.2f}")
            
            # 5. Cambiar modo visual y dar foco
            self.btn_anadir.configure(text='ACTUALIZAR LÍNEA')
            self.combo_tipo.entry.focus_set()
            try: self.combo_tipo.entry._entry.selection_range(0, 'end')
            except: pass

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

        if not self.proveedor_id:
            ToastWidget.show(self.container, 'ERROR: NO SE HA DETECTADO EL PROVEEDOR', tipo='error')
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
                # Verificar que el proveedor existe o al menos registrar el ID que llega
                logger.info(f"Guardando albarán manual {num_albaran} para proveedor_id={self.proveedor_id}")
                
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
            
            ToastWidget.show(
                self.container, 
                f"ALBARÁN '{num_albaran}' GUARDADO Y STOCK ACTUALIZADO", 
                tipo='success'
            )
            self._on_volver_click()

        except Exception:
            logger.exception("Error guardando albarán manual")
            ToastWidget.show(self.container, "ERROR AL GUARDAR EL ALBARÁN", tipo='error')

    def _setup_tab_navigation(self):
        """Configura navegación manual con Tab/Shift+Tab entre los campos en orden lógico."""
        self._tab_order = [
            self.entry_num,
            self.entry_fecha,
            self.combo_tipo,
            self.combo_variante,
            self.combo_color,
            self.combo_talla,
            self.entry_cant,
            self.entry_coste,
            self.btn_anadir,
            self.btn_guardar,
            self.btn_eliminar,
            self.btn_volver,
        ]
        
        # Mapear los widgets reales de tkinter a sus objetos CTK o envoltorios
        # CTkButton tiene _canvas y _text_label internos que reciben los eventos
        self._widget_map = {}
        for w in self._tab_order:
            if hasattr(w, 'entry') and hasattr(w.entry, '_entry'): # SearchableCombo
                self._widget_map[str(w.entry._entry)] = w
            elif hasattr(w, '_entry'): # CTKEntry
                self._widget_map[str(w._entry)] = w
            elif hasattr(w, '_canvas'): # CTkButton
                self._widget_map[str(w._canvas)] = w
                if hasattr(w, '_text_label'):
                    self._widget_map[str(w._text_label)] = w
            else: # Fallback
                self._widget_map[str(w)] = w

        def on_tab(event):
            current_tk = str(event.widget)
            current_obj = self._widget_map.get(current_tk)
            
            if current_obj in self._tab_order:
                idx = self._tab_order.index(current_obj)
                
                # Si es un combo y hay algo escrito, intentar validar antes de saltar
                if hasattr(current_obj, '_on_focus_out'):
                    current_obj._on_focus_out(event)

                if event.state & 0x1:  # Shift presionado
                    next_idx = (idx - 1) % len(self._tab_order)
                else:
                    next_idx = (idx + 1) % len(self._tab_order)
                
                next_obj = self._tab_order[next_idx]
                
                # Dar foco al widget real (o su entry si es combo)
                if hasattr(next_obj, 'entry'):
                    next_obj.entry.focus_set()
                    try: next_obj.entry._entry.selection_range(0, 'end')
                    except: pass
                elif hasattr(next_obj, '_entry'):
                    next_obj.focus_set()
                    try: next_obj._entry.selection_range(0, 'end')
                    except: pass
                else:
                    next_obj.focus_set()
                
                return 'break'
            return None
        
        # Vincular a todos los widgets internos para capturar el Tab
        for w in self._tab_order:
            if hasattr(w, 'entry'): # SearchableCombo → bind su entry interno
                w.entry._entry.bind('<Tab>', on_tab)
                w.entry._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_entry'): # CTKEntry → bind su entry interno
                w._entry.bind('<Tab>', on_tab)
                w._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_canvas'): # CTkButton → bind canvas + text_label
                w._canvas.bind('<Tab>', on_tab)
                w._canvas.bind('<Shift-Tab>', on_tab)
                if hasattr(w, '_text_label'):
                    w._text_label.bind('<Tab>', on_tab)
                    w._text_label.bind('<Shift-Tab>', on_tab)
            else:
                w.bind('<Tab>', on_tab)
                w.bind('<Shift-Tab>', on_tab)

        # Desactivar takefocus en todos los frames para que Tab no se pierda en ellos
        def disable_frame_focus(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkFrame, tk.Frame)):
                    try: child.configure(takefocus=0)
                    except: pass
                    disable_frame_focus(child)
        disable_frame_focus(self.container)

    def _on_volver_click(self):
        if self.owner and hasattr(self.owner, 'show_proveedores'):
            self.owner.show_proveedores(proveedor_id=self.proveedor_id)

    def _bind_esc_recursive(self, widget):
        widget.bind('<Escape>', self._esc_handler)
        for child in widget.winfo_children():
            self._bind_esc_recursive(child)

    def get_widget(self):
        return self.container
