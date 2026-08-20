"""UI unificada para configuración de mapeos de proveedor (CSV, Variantes, Colores, Tallas)."""
import logging
import json
import tkinter as tk
import customtkinter as ctk
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import get_font
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService

logger = logging.getLogger(__name__)

class ProduccionProveedoresConfigurador:
    """Configurador unificado con sistema de pestañas para mapeos."""

    def __init__(self, parent, db=None, proveedor_id=None, proveedor_nombre='', owner=None, tab_inicial='CSV', module_name='produccion'):
        self.parent = parent
        self.db = db
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.owner = owner
        self.module_name = module_name
        self.proveedor_service = ProveedorService(db)
        
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        # GRID LAYOUT PRINCIPAL
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(2, weight=1)

        self._setup_header()
        self._setup_menu()
        
        # Área de contenido
        self.content_area = ctk.CTkFrame(self.container, fg_color='transparent')
        self.content_area.grid(row=2, column=0, sticky='nsew', padx=20, pady=(0, 20))
        
        self._esc_handler = lambda e=None: self._on_volver()
        self._bind_esc_recursive(self.container)
        
        self.current_tab = None
        self.current_widget = None
        
        # ESTADO DE LA SESIÓN
        self.tipos_seleccionados = None 
        self.temp_mapeo_datos = {} # Memoria temporal para no perder lo escrito al cambiar pestañas
        self._cache_tipos_sistema = None
        self._cache_tipos_producto = None

        # Selección actual de los combos Tipo/Variante (se mantiene entre refrescos de la pestaña)
        self._map_tipo_sel = ''
        self._map_variante_sel = ''
        self.combo_map_tipo = None
        self.combo_map_variante = None

        self.show_tab(tab_inicial)

    def _get_variantes_sistema(self):
        if self._cache_tipos_sistema is None:
            svc = ProduccionTiposVariantesService(self.db)
            self._cache_tipos_sistema = svc.obtener_activos_como_dict()
        return self._cache_tipos_sistema

    def _get_tipos_producto(self):
        """Obtener tipos de producto activos del sistema (para el combo Tipo)."""
        if self._cache_tipos_producto is None:
            svc = ProduccionTiposService(self.db)
            self._cache_tipos_producto = svc.obtener_activos()
        return self._cache_tipos_producto

    def _setup_header(self):
        header = ctk.CTkFrame(self.container, fg_color='#1a1a1a', height=50)
        header.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text=f"MAPEOS PROVEEDOR: {self.proveedor_nombre.upper()}",
                     font=('Courier New', 18, 'bold'), 
                     text_color=self.colors.get('text', COLOR_MATRIX)).pack(pady=8)

    def _setup_menu(self):
        menu_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        menu_frame.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 10))
        
        if self.module_name == 'almacen':
            self.tabs = ['CSV']
        else:
            self.tabs = ['CSV', 'VARIANTES', 'COLORES', 'TALLAS']
        self.tab_buttons = {}
        for tab in self.tabs:
            btn = ctk.CTkButton(menu_frame, text=tab, width=100, height=32,
                                font=('Courier New', 13, 'bold'), fg_color='#333333', text_color='black',
                                command=lambda t=tab: self.show_tab(t))
            btn.pack(side='left', padx=4)
            self.tab_buttons[tab] = btn

        ctk.CTkButton(menu_frame, text="VOLVER", width=80, height=32,
                      font=('Courier New', 11, 'bold'), fg_color='#555555',
                      command=self._on_volver).pack(side='right', padx=4)

    def show_tab(self, tab_name):
        if self.current_tab == tab_name and self.current_widget: return
            
        # Guardar lo escrito en la pestaña actual antes de salir
        if self.current_tab in ['VARIANTES', 'COLORES', 'TALLAS'] and hasattr(self, 'mapping_entries'):
            self._update_temp_data()

        # Actualizar botones
        for name, btn in self.tab_buttons.items():
            btn.configure(fg_color=self.colors.get('primary', '#9b59b6') if name == tab_name else '#333333')
        
        for child in self.content_area.winfo_children(): child.destroy()
        self.current_tab = tab_name
        
        if tab_name == 'CSV': self.current_widget = self._build_csv_tab()
        elif tab_name == 'VARIANTES': self.current_widget = self._build_mapping_tab('variantes')
        elif tab_name == 'COLORES': self.current_widget = self._build_mapping_tab('colores')
        elif tab_name == 'TALLAS': self.current_widget = self._build_mapping_tab('tallas')
            
        if self.current_widget:
            self.current_widget.pack(fill='both', expand=True)
            self._bind_esc_recursive(self.current_widget)

    def _update_temp_data(self):
        if not hasattr(self, 'mapping_entries') or not self.current_tab:
            return
        # Normalizar clave (quitar tildes para la lógica interna)
        key = self.current_tab.upper().replace('É', 'E').replace('Ó', 'O')
        data = {}
        for item_nom, entry in self.mapping_entries.items():
            if isinstance(entry, dict) and 'incluye' in entry and 'excluye' in entry:
                # Variantes: formato dual horizontal
                inc_val = entry['incluye'].get().strip() if hasattr(entry['incluye'], 'get') else ""
                exc_val = entry['excluye'].get().strip() if hasattr(entry['excluye'], 'get') else ""
                inc_list = [k.strip() for k in inc_val.split(",") if k.strip()]
                exc_list = [k.strip() for k in exc_val.split(",") if k.strip()]
                data[item_nom] = {"incluye": inc_list, "excluye": exc_list}
            else:
                # Colores / Tallas (formato lista simple)
                val = entry.get().strip() if hasattr(entry, 'get') else str(entry)
                data[item_nom] = [k.strip() for k in val.split(",") if k.strip()]
        self.temp_mapeo_datos[key] = data

    def _build_csv_tab(self):
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color='#111111')
        try:
            mapeo_json = self.proveedor_service.get_mapeo_csv(self.proveedor_id)
            mapeo = json.loads(mapeo_json) if mapeo_json else {}
        except: mapeo = {}
            
        self._add_section_header(scroll, "CONFIGURACIÓN TÉCNICA")
        self.csv_entries = {}
        self._add_form_row(scroll, "Separador:", "separador", mapeo.get('separador', ';'), self.csv_entries)
        self._add_form_row(scroll, "Encoding:", "encoding", mapeo.get('encoding', 'utf-8'), self.csv_entries)
        self._add_form_row(scroll, "Saltar Filas:", "skip_rows", str(mapeo.get('skip_rows', 0)), self.csv_entries)
        
        self._add_section_header(scroll, "COLUMNAS DEL CSV")
        columnas = [("EAN:", "columna_ean"), ("Nombre:", "columna_nombre"), ("Cantidad:", "columna_cantidad")]
        if self.module_name != 'almacen':
            columnas += [("Color:", "columna_color"), ("Talla:", "columna_talla")]
        columnas += [("Precio Base:", "columna_precio_base"), ("Coste:", "columna_coste"),
                     ("Dto:", "columna_descuento"), ("IVA:", "columna_iva"), ("PVPR:", "columna_pvpr")]
        for label, key in columnas:
            self._add_form_row(scroll, label, key, mapeo.get(key, ''), self.csv_entries)
            
        self._add_section_header(scroll, "CÁLCULOS")
        self.csv_checks = {}
        self._add_check_row(scroll, "Calcular Coste desde Precio + Dto", "calcular_coste_desde_precio_dto", mapeo.get('calcular_coste_desde_precio_dto', False), self.csv_checks)
        self._add_check_row(scroll, "Calcular PVPR desde Precio + IVA", "calcular_pvpr_desde_precio_iva", mapeo.get('calcular_pvpr_desde_precio_iva', False), self.csv_checks)
        
        ButtonFactory.create_button(scroll, 'GUARDAR CONFIG CSV', self._save_csv, style_key='action_success').pack(pady=20)
        return scroll

    def _build_mapping_tab(self, mapping_type):
        container = ctk.CTkFrame(self.content_area, fg_color='transparent')
        tab_key = mapping_type.upper()
        
        # Cargar datos (Memoria > BD)
        if tab_key not in self.temp_mapeo_datos:
            mapeo_json = None
            if mapping_type == 'variantes':
                mapeo_json = self.proveedor_service.get_mapeo_variantes(self.proveedor_id)
            elif mapping_type == 'colores':
                mapeo_json = self.proveedor_service.get_mapeo_colores(self.proveedor_id)
            elif mapping_type == 'tallas':
                mapeo_json = self.proveedor_service.get_mapeo_tallas(self.proveedor_id)
            try:
                self.temp_mapeo_datos[tab_key] = json.loads(mapeo_json) if mapeo_json else {}
            except:
                self.temp_mapeo_datos[tab_key] = {}

        mapeo_actual = self.temp_mapeo_datos[tab_key]

        if mapping_type == 'variantes':
            # Obtener variantes reales del sistema
            variantes_sistema = self._get_variantes_sistema()
            nombres_sistema = set(variantes_sistema.values())

            # Cargar selección inicial solo con variantes que EXISTAN en el sistema
            if self.tipos_seleccionados is None:
                self.tipos_seleccionados = [nom for nom in mapeo_actual.keys() if nom in nombres_sistema]
            
            sel_frame = ctk.CTkFrame(container, fg_color='#1a1a1a')
            sel_frame.pack(fill='x', pady=(0, 5))
            ctk.CTkLabel(sel_frame, text="AÑADIR VARIANTE AL MAPEO:", font=('Courier New', 11, 'bold'), text_color=self.colors.get('primary', '#9b59b6')).pack(pady=5)

            pick_f = ctk.CTkFrame(sel_frame, fg_color='transparent')
            pick_f.pack(fill='x', padx=10, pady=(0, 10))

            tipos_producto = self._get_tipos_producto()
            opciones_tipo = [(t.id, t.nombre) for t in tipos_producto]

            self.combo_map_tipo = SearchableCombo(
                pick_f, options=opciones_tipo, placeholder='Tipo...',
                width=220, module_name=self.module_name,
                command=self._on_map_tipo_seleccionado
            )
            self.combo_map_tipo.pack(side='left', padx=(0, 8))

            self.combo_map_variante = SearchableCombo(
                pick_f, options=[], placeholder='Variante...',
                width=220, module_name=self.module_name
            )
            self.combo_map_variante.pack(side='left', padx=(0, 8))

            btn_anadir_variante = ButtonFactory.create_button(pick_f, 'AÑADIR', self._on_add_variante_mapeo, style_key='action_success')
            btn_anadir_variante.pack(side='left')

            # Restaurar selección previa (tipo -> repobla combo variante -> variante)
            if self._map_tipo_sel:
                self.combo_map_tipo.set(self._map_tipo_sel)
                self._on_map_tipo_seleccionado(self._map_tipo_sel)
                if self._map_variante_sel:
                    self.combo_map_variante.set(self._map_variante_sel)

            self._setup_tab_navigation_variantes(pick_f, btn_anadir_variante)

            # Foco inicial en Tipo para poder escribir directo al entrar en la pestaña
            self.combo_map_tipo.after(100, lambda: self.combo_map_tipo.entry.focus_set())

        scroll = ctk.CTkScrollableFrame(container, fg_color='#111111')
        scroll.pack(fill='both', expand=True)
        self._add_section_header(scroll, f"PALABRAS CLAVE: {tab_key}")

        if mapping_type == 'variantes':
            note = ctk.CTkLabel(scroll, text="Incluye: palabras que identifican la variante. Excluye: palabras que la descartan (prioridad). Separa por coma.",
                                font=('Courier New', 9), text_color='#888888')
            note.pack(anchor='w', padx=10, pady=(0, 4))

        self.mapping_entries = {}
        items = []
        if mapping_type == 'variantes':
            items = sorted(self.tipos_seleccionados)
        elif mapping_type == 'tallas':
            svc_tallas = ProduccionTallasService(self.db)
            items = [t.nombre for t in svc_tallas.obtener_todas()]
        else:
            svc_colores = ProduccionColoresService(self.db)
            items = [c.nombre for c in svc_colores.obtener_activos()]

        for item in items:
            val = mapeo_actual.get(item, [])
            if mapping_type == 'variantes':
                if isinstance(val, dict):
                    inc = ", ".join(str(x) for x in val.get('incluye', []))
                    exc = ", ".join(str(x) for x in val.get('excluye', []))
                else:
                    inc = ", ".join(str(x) for x in val) if isinstance(val, list) else str(val or "")
                    exc = ""
                self._add_variant_mapping_row(scroll, item, item, inc, exc, self.mapping_entries, on_remove=self._on_remove_variante_mapeo)
            else:
                self._add_form_row(scroll, item, item, ", ".join(val) if isinstance(val, list) else str(val), self.mapping_entries)

        ButtonFactory.create_button(scroll, f'GUARDAR MAPEO {tab_key}', lambda: self._save_mapping(mapping_type), style_key='action_success').pack(pady=20)
        return container

    def _on_map_tipo_seleccionado(self, tipo_nombre):
        """Al elegir un Tipo, repoblar el combo de Variante con las variantes de ese tipo."""
        try:
            tipos_producto = self._get_tipos_producto()
            tipo = next((t for t in tipos_producto if t.nombre == tipo_nombre), None)
            if not tipo or not self.combo_map_variante:
                return
            svc_variantes = ProduccionTiposVariantesService(self.db)
            variantes = svc_variantes.obtener_por_tipo(tipo.id)
            self.combo_map_variante.set_options([(v.id, v.nombre) for v in variantes])
        except Exception:
            logger.exception('Error filtrando variantes por tipo')

    def _setup_tab_navigation_variantes(self, pick_f, btn_anadir):
        """Configura navegación manual con Tab/Shift+Tab entre Tipo, Variante y AÑADIR.

        Replica el patrón usado en produccion_entrada_manual.py para que Tab
        recorra los widgets reales (entry interno de los combos / canvas del botón).
        """
        tab_order = [self.combo_map_tipo, self.combo_map_variante, btn_anadir]

        widget_map = {}
        for w in tab_order:
            if hasattr(w, 'entry') and hasattr(w.entry, '_entry'):
                widget_map[str(w.entry._entry)] = w
            elif hasattr(w, '_entry'):
                widget_map[str(w._entry)] = w
            elif hasattr(w, '_canvas'):
                widget_map[str(w._canvas)] = w
                if hasattr(w, '_text_label'):
                    widget_map[str(w._text_label)] = w
            else:
                widget_map[str(w)] = w

        def on_tab(event):
            current_obj = widget_map.get(str(event.widget))
            if current_obj in tab_order:
                idx = tab_order.index(current_obj)
                next_idx = (idx - 1) % len(tab_order) if (event.state & 0x1) else (idx + 1) % len(tab_order)
                next_obj = tab_order[next_idx]

                if hasattr(next_obj, 'entry'):
                    next_obj.entry.focus_set()
                    try: next_obj.entry._entry.selection_range(0, 'end')
                    except Exception: pass
                elif hasattr(next_obj, '_entry'):
                    next_obj.focus_set()
                    try: next_obj._entry.selection_range(0, 'end')
                    except Exception: pass
                else:
                    next_obj.focus_set()
                return 'break'
            return None

        for w in tab_order:
            if hasattr(w, 'entry'):
                w.entry._entry.bind('<Tab>', on_tab)
                w.entry._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_entry'):
                w._entry.bind('<Tab>', on_tab)
                w._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_canvas'):
                w._canvas.bind('<Tab>', on_tab)
                w._canvas.bind('<Shift-Tab>', on_tab)
                if hasattr(w, '_text_label'):
                    w._text_label.bind('<Tab>', on_tab)
                    w._text_label.bind('<Shift-Tab>', on_tab)
            else:
                w.bind('<Tab>', on_tab)
                w.bind('<Shift-Tab>', on_tab)

        # Desactivar takefocus en los frames intermedios para que Tab no se pierda en ellos
        def disable_frame_focus(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkFrame, tk.Frame)):
                    try: child.configure(takefocus=0)
                    except Exception: pass
                    disable_frame_focus(child)
        disable_frame_focus(pick_f)

    def _on_add_variante_mapeo(self):
        """Añadir la combinación Tipo/Variante seleccionada a la lista de mapeo."""
        try:
            tipo_nombre = self.combo_map_tipo.get().strip() if self.combo_map_tipo else ''
            variante_nombre = self.combo_map_variante.get().strip() if self.combo_map_variante else ''
            if not tipo_nombre or not variante_nombre:
                ToastWidget.show(self.container, 'Selecciona Tipo y Variante', tipo='error')
                return
            if self.combo_map_variante.get_id() is None:
                ToastWidget.show(self.container, 'Variante no válida para ese Tipo', tipo='error')
                return

            self._update_temp_data()
            etiqueta = f"{tipo_nombre} / {variante_nombre}"
            if etiqueta not in self.tipos_seleccionados:
                self.tipos_seleccionados.append(etiqueta)

            self._map_tipo_sel = tipo_nombre
            self._map_variante_sel = variante_nombre
            self.current_widget = None
            self.show_tab('VARIANTES')
        except Exception:
            logger.exception('Error añadiendo variante al mapeo')

    def _on_remove_variante_mapeo(self, etiqueta):
        """Quitar una variante ya añadida al mapeo."""
        try:
            self._update_temp_data()
            if etiqueta in self.tipos_seleccionados:
                self.tipos_seleccionados.remove(etiqueta)
            if 'VARIANTES' in self.temp_mapeo_datos:
                self.temp_mapeo_datos['VARIANTES'].pop(etiqueta, None)
            self.current_widget = None
            self.show_tab('VARIANTES')
        except Exception:
            logger.exception('Error quitando variante del mapeo')

    def _add_section_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=('Courier New', 14, 'bold'), text_color=self.colors.get('primary', '#9b59b6')).pack(anchor='w', padx=10, pady=(10, 2))
        ctk.CTkFrame(parent, height=2, fg_color='#333333').pack(fill='x', padx=10, pady=(0, 10))

    def _add_form_row(self, parent, label, key, value, storage):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=10, pady=2)
        ctk.CTkLabel(row, text=label, width=150, anchor='w', font=('Courier New', 12)).pack(side='left')
        entry = ctk.CTkEntry(row, font=('Courier New', 13), height=28)
        entry.pack(side='left', fill='x', expand=True, padx=5)
        entry.insert(0, str(value))
        storage[key] = entry

    def _add_variant_mapping_row(self, parent, label, key, incluye_val, excluye_val, storage, on_remove=None):
        """Horizontal layout for variants: label | Incluye entry | Excluye entry (same row, uses horizontal space)."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=10, pady=3)

        if on_remove:
            ctk.CTkButton(row, text='✕', width=26, height=26, fg_color='#7a1f1f', hover_color='#a52a2a',
                          font=('Courier New', 11, 'bold'),
                          command=lambda k=key: on_remove(k)).pack(side='left', padx=(0, 6))

        # Variant label (left)
        ctk.CTkLabel(row, text=label, width=200, anchor='w', font=('Courier New', 11)).pack(side='left')

        # Incluye (left side of the pair)
        ctk.CTkLabel(row, text="Incluye:", width=55, anchor='w', font=('Courier New', 10)).pack(side='left', padx=(4, 0))
        inc_entry = ctk.CTkEntry(row, font=('Courier New', 12), height=26)
        inc_entry.pack(side='left', fill='x', expand=True, padx=4)
        inc_entry.insert(0, str(incluye_val))

        # Excluye (right side of the pair)
        ctk.CTkLabel(row, text="Excluye:", width=55, anchor='w', font=('Courier New', 10)).pack(side='left', padx=(8, 0))
        exc_entry = ctk.CTkEntry(row, font=('Courier New', 12), height=26)
        exc_entry.pack(side='left', fill='x', expand=True, padx=4)
        exc_entry.insert(0, str(excluye_val))

        storage[key] = {"incluye": inc_entry, "excluye": exc_entry}

    def _add_check_row(self, parent, label, key, value, storage):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=10, pady=2)
        check = ctk.CTkCheckBox(row, text=label, font=('Courier New', 12), fg_color='#9b59b6')
        check.pack(side='left', padx=5)
        if value: check.select()
        storage[key] = check

    def _save_csv(self):
        try:
            data = {k: (int(e.get()) if k=='skip_rows' else e.get()) for k, e in self.csv_entries.items()}
            for k, c in self.csv_checks.items(): data[k] = bool(c.get())
            if self.proveedor_service.save_mapeo_csv(self.proveedor_id, json.dumps(data, indent=2)):
                ToastWidget.show(self.container, "CSV Guardado", tipo='success')
        except: logger.exception("Error CSV"); ToastWidget.show(self.container, 'ERROR AL GUARDAR CSV', tipo='error')

    def _save_mapping(self, m_type):
        try:
            self._update_temp_data()
            key = m_type.upper()
            if key not in self.temp_mapeo_datos:
                return

            json_str = json.dumps(self.temp_mapeo_datos[key], indent=2, ensure_ascii=False)
            success = False
            if m_type == 'variantes': success = self.proveedor_service.save_mapeo_variantes(self.proveedor_id, json_str)
            elif m_type == 'tallas': success = self.proveedor_service.save_mapeo_tallas(self.proveedor_id, json_str)
            else: success = self.proveedor_service.save_mapeo_colores(self.proveedor_id, json_str)
            
            if success: ToastWidget.show(self.container, f"Mapeo {m_type} guardado", tipo='success')
            else: ToastWidget.show(self.container, 'ERROR AL GUARDAR EN BD', tipo='error')
        except: logger.exception("Error Mapeo"); ToastWidget.show(self.container, 'ERROR AL GUARDAR', tipo='error')

    def _on_volver(self):
        if self.owner and hasattr(self.owner, 'show_proveedores_with_id'): self.owner.show_proveedores_with_id(self.proveedor_id)
        elif self.owner and hasattr(self.owner, 'show_proveedores'): self.owner.show_proveedores(self.proveedor_id)

    def _bind_esc_recursive(self, widget):
        widget.bind('<Escape>', self._esc_handler)
        for child in widget.winfo_children():
            self._bind_esc_recursive(child)

    def get_widget(self): return self.container
