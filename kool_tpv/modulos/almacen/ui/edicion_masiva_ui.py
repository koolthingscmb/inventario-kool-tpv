"""EdicionMasivaUI: Subvista de edición masiva de productos (nombres y PVP).

Modos de trabajo (selector superior):
- NOMBRES: unificación de nombres mediante plantillas ({num}, {sku}, {actual})
  con detección automática del número de tomo y padding opcional.
- PVP: cambio masivo de precio (fijo, +%, -%, +€, -€) con redondeos
  comerciales (.95, .99, euro entero — siempre hacia arriba).

Flujo común a ambos modos:
1. Buscar lotes por término, categoría y tipo.
2. Descartar productos de la lista (Ctrl/Cmd+clic, Shift, Supr) sin borrarlos de la BD.
3. Previsualizar los cambios en tabla virtualizada y editar filas con doble clic.
4. Guardar de forma atómica vía repositorio (histórico de precios + audit + pending_sync).
"""
import logging
import re
import tkinter as tk
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.modulos.almacen.services.edicion_masiva_service import EdicionMasivaService
from kool_tpv.utils.config_loader import load_colors, load_layout_config
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
from kool_tpv.utils.dialogs.helpers import show_warning, show_input_dialog
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX

logger = logging.getLogger(__name__)


class EdicionMasivaUI:
    """Subvista para la edición masiva de nombres y PVP de productos en Almacén."""

    # Columnas de la tabla según el modo activo
    COLUMNAS_NOMBRES = [
        ('id', 60, 'ID'),
        ('sku', 130, 'SKU'),
        ('nombre_actual', 320, 'NOMBRE ACTUAL'),
        ('nombre_propuesto', 420, 'NUEVO NOMBRE PROPUESTO (Doble clic para editar)', True),
        ('num_detectado', 80, 'TOMO'),
        ('estado_cambio', 110, 'ESTADO')
    ]

    COLUMNAS_PVP = [
        ('id', 60, 'ID'),
        ('sku', 130, 'SKU'),
        ('nombre_actual', 340, 'NOMBRE'),
        ('pvp_actual', 110, 'PVP ACTUAL'),
        ('pvp_propuesto', 180, 'NUEVO PVP (Doble clic para editar)', True),
        ('estado_cambio', 110, 'ESTADO')
    ]

    def __init__(self, parent, db: Database, owner=None, keyboard_manager=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.keyboard_mgr = keyboard_manager
        self.module_name = module_name

        # Servicios
        self.service = EdicionMasivaService(db)
        self.categoria_service = CategoriaService(db)
        self.tipo_service = TipoService(db)

        # Colores y fuentes
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {
                'background': COLOR_BG_TERMINAL,
                'text': COLOR_MATRIX,
                'border': COLOR_MATRIX,
                'primary': COLOR_MATRIX,
                'secondary': '#3498db',
                'accent': '#e67e22',
                'light': '#00AA00',
                'error': '#e74c3c'
            }

        self._bg = self.colors.get('background', COLOR_BG_TERMINAL)
        self._text = self.colors.get('text', COLOR_MATRIX)
        self._primary = self.colors.get('primary', COLOR_MATRIX)
        self._border = self.colors.get('border', self._primary)

        # Estado: 'nombres' o 'pvp'
        self._modo = 'nombres'
        self._productos_cargados: List[Dict[str, Any]] = []
        # Previews por modo: {pid: item}. Las ediciones manuales se conservan
        # al regenerar o al alternar entre modos (flag 'editado_manual').
        self._previews: Dict[str, Dict[Any, Dict[str, Any]]] = {'nombres': {}, 'pvp': {}}

        # Contenedor principal
        self.container = ctk.CTkFrame(self.parent, fg_color=self._bg)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Construcción de la UI
        self._crear_barra_busqueda()
        self._crear_barra_operacion()
        self._crear_tabla_previsualizacion()
        self._crear_footer()

    def get_widget(self):
        return self.container

    # --- 1. BARRA DE BÚSQUEDA Y FILTROS ---

    def _crear_barra_busqueda(self):
        """Crea la zona de búsqueda de productos a modificar."""
        search_frame = ctk.CTkFrame(self.container, fg_color="transparent", border_width=0)
        search_frame.pack(fill='x', padx=12, pady=(10, 6))

        # Fila superior de filtros
        top_filter = ctk.CTkFrame(search_frame, fg_color='transparent')
        top_filter.pack(fill='x', padx=10, pady=8)

        # Label buscador
        ctk.CTkLabel(
            top_filter,
            text="Busca productos:",
            text_color=self._text,
            font=get_font('label_bold', module=self.module_name)
        ).pack(side='left', padx=(0, 8))

        # Buscador por texto
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            top_filter,
            textvariable=self.search_var,
            placeholder_text="Nombre o SKU + ENTER...",
            height=36,
            fg_color=self.colors.get('bg_dark', '#000000'),
            text_color=self._text,
            border_color=self._primary,
            border_width=2,
            font=get_font('entry', module=self.module_name)
        )
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._on_buscar_lote())

        # Categorías
        categorias = [{'id': None, 'nombre': 'Todas'}] + (self.categoria_service.get_all() or [])
        ctk.CTkLabel(
            top_filter,
            text="Cat:",
            text_color=self._text,
            font=get_font('label_small', module=self.module_name)
        ).pack(side='left', padx=(0, 4))

        self.cat_combo = SearchableCombo(
            top_filter,
            options=[(c['id'], c['nombre']) for c in categorias],
            width=140
        )
        self.cat_combo.set('Todas')
        self.cat_combo.pack(side='left', padx=(0, 10))

        # Tipos
        tipos = [{'id': None, 'nombre': 'Todos'}] + (self.tipo_service.get_all_tipos() or [])
        ctk.CTkLabel(
            top_filter,
            text="Tipo:",
            text_color=self._text,
            font=get_font('label_small', module=self.module_name)
        ).pack(side='left', padx=(0, 4))

        self.tipo_combo = SearchableCombo(
            top_filter,
            options=[(t['id'], t['nombre']) for t in tipos],
            width=140
        )
        self.tipo_combo.set('Todos')
        self.tipo_combo.pack(side='left', padx=(0, 10))

        # Botón Cargar Lote
        self.btn_cargar = ButtonFactory.create_button(
            parent=top_filter,
            text='BUSCAR LOTES',
            command=self._on_buscar_lote,
            style_key='action_primary',
            module=self.module_name,
            palette_key='primary'
        )
        self.btn_cargar.pack(side='left')

    # --- 2. BARRA DE OPERACIÓN (SELECTOR DE MODO + CONTROLES POR MODO) ---

    def _crear_barra_operacion(self):
        """Crea el selector de modo y las barras de operación (plantilla / PVP)."""
        op_frame = ctk.CTkFrame(
            self.container,
            fg_color=self.colors.get('bg_medium', '#1A1A1A'),
            corner_radius=8,
            border_width=0
        )
        op_frame.pack(fill='x', padx=12, pady=(0, 6))

        # Fila 0: selector de modo (chips)
        row_modo = ctk.CTkFrame(op_frame, fg_color='transparent')
        row_modo.pack(fill='x', padx=12, pady=(8, 4))

        self.btn_modo_nombres = ButtonFactory.create_button(
            parent=row_modo,
            text='NOMBRES',
            command=lambda: self._on_cambiar_modo('nombres'),
            style_key='chip_selected',
            module=self.module_name,
            palette_key='primary',
            width=110,
            height=30,
            cursor='hand2'
        )
        self.btn_modo_nombres.pack(side='left', padx=(0, 8))

        self.btn_modo_pvp = ButtonFactory.create_button(
            parent=row_modo,
            text='PVP',
            command=lambda: self._on_cambiar_modo('pvp'),
            style_key='chip_default',
            module=self.module_name,
            palette_key='secondary',
            width=110,
            height=30,
            cursor='hand2'
        )
        self.btn_modo_pvp.pack(side='left')

        self.lbl_contador = ctk.CTkLabel(
            row_modo,
            text="0 productos cargados",
            font=get_font('label_small', module=self.module_name),
            text_color="#2ECC71"
        )
        self.lbl_contador.pack(side='right', padx=(10, 0))

        # Barras de operación por modo
        self._crear_barra_nombres(op_frame)
        self._crear_barra_pvp(op_frame)

        # Estado inicial: modo nombres
        self.frame_pvp.pack_forget()

    def _crear_barra_nombres(self, parent):
        """Barra de operación del modo NOMBRES: plantilla + padding."""
        self.frame_nombres = ctk.CTkFrame(parent, fg_color='transparent')
        self.frame_nombres.pack(fill='x')

        row1 = ctk.CTkFrame(self.frame_nombres, fg_color='transparent')
        row1.pack(fill='x', padx=12, pady=(4, 4))

        ctk.CTkLabel(
            row1,
            text="PLANTILLA DE NOMBRE:",
            font=get_font('label_bold', module=self.module_name),
            text_color=self._primary
        ).pack(side='left', padx=(0, 8))

        self.patron_var = tk.StringVar(value="")
        self.entry_patron = ctk.CTkEntry(
            row1,
            textvariable=self.patron_var,
            placeholder_text="Ej: One Piece 3en1 Tomo {num}  |  Variables: {num}, {sku}, {actual}",
            height=36,
            fg_color=self.colors.get('bg_dark', '#000000'),
            text_color=self._text,
            border_color=self._primary,
            border_width=2,
            font=get_font('entry', module=self.module_name)
        )
        self.entry_patron.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.entry_patron.bind('<Return>', lambda e: self._on_aplicar_operacion())

        # Checkbox para ceros a la izquierda (01, 02...)
        self.check_ceros_var = tk.BooleanVar(value=False)
        self.check_ceros = ctk.CTkCheckBox(
            row1,
            text="0 delante (01, 02...)",
            variable=self.check_ceros_var,
            font=get_font('label_small', module=self.module_name),
            text_color=self._text,
            fg_color=self.colors.get('secondary', '#C2FF35'),
            hover_color=self.colors.get('light', '#99FF52')
        )
        self.check_ceros.pack(side='left', padx=(0, 12))

        self.btn_prev_nombres = ButtonFactory.create_button(
            parent=row1,
            text='PREVISUALIZAR',
            command=self._on_aplicar_operacion,
            style_key='action_confirm',
            module=self.module_name,
            palette_key='secondary'
        )
        self.btn_prev_nombres.pack(side='left')

        # Fila 2: ayuda
        row2 = ctk.CTkFrame(self.frame_nombres, fg_color='transparent')
        row2.pack(fill='x', padx=12, pady=(0, 8))

        ctk.CTkLabel(
            row2,
            text="Variables disponibles: {num} (número de tomo detectado)  ·  {sku} (código SKU)  ·  {actual} (nombre original)",
            font=get_font('small', module=self.module_name),
            text_color="#95A5A6"
        ).pack(side='left')

    def _crear_barra_pvp(self, parent):
        """Barra de operación del modo PVP: operación + valor + redondeo."""
        self.frame_pvp = ctk.CTkFrame(parent, fg_color='transparent')
        # Se empaqueta/desempaqueta según el modo activo

        row1 = ctk.CTkFrame(self.frame_pvp, fg_color='transparent')
        row1.pack(fill='x', padx=12, pady=(4, 4))

        ctk.CTkLabel(
            row1,
            text="OPERACIÓN PVP:",
            font=get_font('label_bold', module=self.module_name),
            text_color=self._primary
        ).pack(side='left', padx=(0, 8))

        # Combo de operación
        self.op_pvp_combo = SearchableCombo(
            row1,
            options=[(k, v) for k, v in self.service.OPERACIONES_PVP.items()],
            width=170
        )
        self.op_pvp_combo.set(self.service.OPERACIONES_PVP['fijo'])
        self.op_pvp_combo.pack(side='left', padx=(0, 10))

        ctk.CTkLabel(
            row1,
            text="VALOR:",
            font=get_font('label_bold', module=self.module_name),
            text_color=self._primary
        ).pack(side='left', padx=(0, 8))

        self.valor_pvp_var = tk.StringVar(value="")
        self.entry_valor_pvp = ctk.CTkEntry(
            row1,
            textvariable=self.valor_pvp_var,
            placeholder_text="Ej: 9.95  ó  5",
            width=120,
            height=36,
            fg_color=self.colors.get('bg_dark', '#000000'),
            text_color=self._text,
            border_color=self._primary,
            border_width=2,
            font=get_font('entry', module=self.module_name)
        )
        self.entry_valor_pvp.pack(side='left', padx=(0, 10))
        self.entry_valor_pvp.bind('<Return>', lambda e: self._on_aplicar_operacion())

        ctk.CTkLabel(
            row1,
            text="REDONDEO:",
            font=get_font('label_bold', module=self.module_name),
            text_color=self._primary
        ).pack(side='left', padx=(0, 8))

        self.redondeo_combo = SearchableCombo(
            row1,
            options=[(k, v) for k, v in self.service.REDONDEO_OPCIONES.items()],
            width=160
        )
        self.redondeo_combo.set(self.service.REDONDEO_OPCIONES['ninguno'])
        self.redondeo_combo.pack(side='left', padx=(0, 12))

        self.btn_prev_pvp = ButtonFactory.create_button(
            parent=row1,
            text='PREVISUALIZAR',
            command=self._on_aplicar_operacion,
            style_key='action_confirm',
            module=self.module_name,
            palette_key='secondary'
        )
        self.btn_prev_pvp.pack(side='left')

        # Fila 2: ayuda
        row2 = ctk.CTkFrame(self.frame_pvp, fg_color='transparent')
        row2.pack(fill='x', padx=12, pady=(0, 8))

        ctk.CTkLabel(
            row2,
            text="VALOR según operación: euros para PRECIO FIJO / SUBIR € / BAJAR €  ·  porcentaje para SUBIR % / BAJAR %  ·  el redondeo siempre sube al siguiente",
            font=get_font('small', module=self.module_name),
            text_color="#95A5A6"
        ).pack(side='left')

    def _on_cambiar_modo(self, modo: str):
        """Alterna entre los modos NOMBRES y PVP conservando la lista de trabajo."""
        if modo == self._modo:
            return
        self._modo = modo

        # Restilado de chips: activo sólido (primary), inactivo outline (secondary)
        if modo == 'nombres':
            ButtonFactory.apply_style(
                self.btn_modo_nombres, 'chip_selected', module=self.module_name, palette_key='primary')
            ButtonFactory.apply_style(
                self.btn_modo_pvp, 'chip_default', module=self.module_name, palette_key='secondary')
            self.frame_pvp.pack_forget()
            self.frame_nombres.pack(fill='x')
        else:
            ButtonFactory.apply_style(
                self.btn_modo_pvp, 'chip_selected', module=self.module_name, palette_key='primary')
            ButtonFactory.apply_style(
                self.btn_modo_nombres, 'chip_default', module=self.module_name, palette_key='secondary')
            self.frame_nombres.pack_forget()
            self.frame_pvp.pack(fill='x')

        # Reconstruir tabla con las columnas del modo y regenerar preview
        self._rebuild_tabla()
        if self._productos_cargados:
            self._generar_preview_actual()
        self._actualizar_tabla()

    # --- 3. TABLA DE VISTA PREVIA (VIRTUALNAVLIST) ---

    def _crear_tabla_previsualizacion(self):
        """Crea el contenedor de la tabla comparativa."""
        self._table_container = ctk.CTkFrame(self.container, fg_color='transparent')
        self._table_container.pack(fill='both', expand=True, padx=12, pady=4)
        self.nav_list = None
        self._rebuild_tabla()

    def _rebuild_tabla(self):
        """(Re)crea la VirtualNavList con las columnas del modo activo."""
        if self.nav_list is not None:
            try:
                self.nav_list.destroy()
            except Exception:
                pass

        columns = self.COLUMNAS_NOMBRES if self._modo == 'nombres' else self.COLUMNAS_PVP

        self.nav_list = VirtualNavList(
            self._table_container,
            columns=columns,
            module_name=self.module_name,
            keyboard_manager=self.keyboard_mgr,
            on_double_click=self._on_editar_fila_individual,
            layout_config=load_layout_config(),
            row_color_callback=self._row_color_styler,
            multi_select=True,
            on_selection_change=self._on_selection_change
        )
        self.nav_list.pack(fill='both', expand=True)

        # Atajos de teclado para quitar seleccionados (Supr / Delete)
        try:
            if hasattr(self.nav_list, '_canvas'):
                self.nav_list._canvas.bind('<Delete>', lambda e: self._on_quitar_seleccionados())
                self.nav_list._canvas.bind('<BackSpace>', lambda e: self._on_quitar_seleccionados())
        except Exception:
            pass

    def _on_selection_change(self, indices: List[int]):
        """Actualiza el texto del botón de quitar según los elementos seleccionados."""
        total_sel = len(indices) if indices else 0
        if total_sel > 0:
            self.btn_quitar.configure(text=f"QUITAR ({total_sel}) DE LA LISTA")
        else:
            self.btn_quitar.configure(text="QUITAR DE LA LISTA")

    def _row_color_styler(self, item: dict, index: int) -> Optional[dict]:
        """Destaca en verde las filas que cambiarán en el modo activo."""
        if self._modo == 'nombres':
            cambia = bool(item.get('nombre_propuesto')) and item.get('nombre_propuesto') != item.get('nombre_actual')
        else:
            prop = item.get('_pvp_propuesto_dec')
            act = item.get('_pvp_actual_dec')
            cambia = prop is not None and prop != act

        if cambia:
            return {'bg': '#1b2a20', 'fg': '#2ECC71'}
        return None

    # --- 4. FOOTER DE ACCIONES ---

    def _crear_footer(self):
        """Crea la barra inferior con botones de volver, quitar, revertir y guardar."""
        footer = ctk.CTkFrame(self.container, fg_color=self._bg)
        footer.pack(fill='x', padx=12, pady=(6, 12))

        # Botón Volver
        self.btn_volver = ButtonFactory.create_button(
            parent=footer,
            text='VOLVER',
            command=self._on_volver,
            style_key='action_secondary',
            module=self.module_name,
            palette_key='secondary'
        )
        self.btn_volver.pack(side='left', padx=(0, 10))

        # Botón Quitar Seleccionados de la lista (Paleta Accent)
        self.btn_quitar = ButtonFactory.create_button(
            parent=footer,
            text='QUITAR DE LA LISTA',
            command=self._on_quitar_seleccionados,
            style_key='action_secondary',
            module=self.module_name,
            palette_key='accent'
        )
        self.btn_quitar.pack(side='left', padx=10)

        # Botón Revertir
        self.btn_revertir = ButtonFactory.create_button(
            parent=footer,
            text='REVERTIR PROPUESTAS',
            command=self._on_revertir,
            style_key='action_secondary',
            module=self.module_name,
            palette_key='secondary'
        )
        self.btn_revertir.pack(side='left', padx=10)

        # Botón Guardar Cambios (derecha)
        self.btn_guardar = ButtonFactory.create_button(
            parent=footer,
            text='GUARDAR CAMBIOS (0)',
            command=self._on_guardar_cambios,
            style_key='action_confirm',
            module=self.module_name,
            palette_key='primary'
        )
        self.btn_guardar.pack(side='right')

    # --- PREVIEW: GENERACIÓN Y RENDERIZADO ---

    def _parsear_valor_pvp(self) -> Optional[Decimal]:
        """Parsea el valor del modo PVP aceptando coma o punto decimal."""
        raw = self.valor_pvp_var.get().strip().replace(',', '.')
        if not raw:
            return None
        try:
            valor = Decimal(raw)
        except InvalidOperation:
            return None
        return valor if valor >= 0 else None

    def _generar_preview_actual(self):
        """Regenera el preview del modo activo preservando las ediciones manuales."""
        mapa = self._previews[self._modo]
        manuales = {pid: it for pid, it in mapa.items() if it.get('editado_manual')}
        mapa.clear()

        if self._modo == 'nombres':
            items = self.service.generar_previsualizacion(
                productos=self._productos_cargados,
                patron=self.patron_var.get().strip(),
                rellenar_ceros=self.check_ceros_var.get()
            )
        else:
            operacion = self.op_pvp_combo.get_id() or 'fijo'
            valor = self._parsear_valor_pvp()
            redondeo = self.redondeo_combo.get_id() or 'ninguno'
            if valor is None:
                # Sin valor válido: preview neutra (propuesto = actual) para
                # evitar proponer cambios peligrosos (p. ej. PVP a 0.00€).
                items = []
                for p in self._productos_cargados:
                    pvp = p.get('pvp')
                    if not isinstance(pvp, Decimal):
                        try:
                            pvp = Decimal(str(pvp or '0'))
                        except InvalidOperation:
                            pvp = Decimal('0.00')
                    items.append({
                        'id': p.get('id'),
                        'sku': p.get('sku') or '',
                        'nombre_actual': str(p.get('nombre') or '').strip(),
                        'pvp_actual': pvp,
                        'pvp_propuesto': pvp,
                        'seleccionado': True,
                        '_raw': p
                    })
            else:
                items = self.service.generar_previsualizacion_pvp(
                    productos=self._productos_cargados,
                    operacion=operacion,
                    valor=valor,
                    redondeo=redondeo
                )

        for it in items:
            pid = it.get('id')
            manual = manuales.get(pid)
            if manual:
                if self._modo == 'nombres':
                    it['nombre_propuesto'] = manual.get('nombre_propuesto', it['nombre_propuesto'])
                else:
                    it['pvp_propuesto'] = manual.get('pvp_propuesto', it['pvp_propuesto'])
                it['editado_manual'] = True
            mapa[pid] = it

    def _preview_list(self) -> List[Dict[str, Any]]:
        """Devuelve los items de preview del modo activo en el orden de la lista."""
        mapa = self._previews[self._modo]
        return [mapa[p['id']] for p in self._productos_cargados if p.get('id') in mapa]

    def _item_cambia(self, item: Dict[str, Any]) -> bool:
        """Determina si un item de preview cambiará según el modo activo."""
        if self._modo == 'nombres':
            prop = item.get('nombre_propuesto')
            return bool(prop) and prop != item.get('nombre_actual')
        prop = item.get('pvp_propuesto')
        return prop is not None and prop != item.get('pvp_actual')

    def _actualizar_tabla(self):
        """Actualiza las filas de la tabla y los contadores según el modo activo."""
        rows = []
        modificados = 0

        for item in self._preview_list():
            va_a_cambiar = self._item_cambia(item)
            if va_a_cambiar:
                modificados += 1
            estado_txt = "MODIFICAR" if va_a_cambiar else "SIN CAMBIOS"

            if self._modo == 'nombres':
                rows.append({
                    'id': str(item['id']),
                    'sku': item['sku'],
                    'nombre_actual': item['nombre_actual'],
                    'nombre_propuesto': item['nombre_propuesto'],
                    'num_detectado': str(item['num_detectado']) if item.get('num_detectado') is not None else "-",
                    'estado_cambio': estado_txt,
                    '_raw': item
                })
            else:
                pvp_act = item.get('pvp_actual', Decimal('0.00'))
                pvp_prop = item.get('pvp_propuesto')
                rows.append({
                    'id': str(item['id']),
                    'sku': item['sku'],
                    'nombre_actual': item['nombre_actual'],
                    'pvp_actual': f"{pvp_act:.2f} €",
                    'pvp_propuesto': f"{pvp_prop:.2f} €" if pvp_prop is not None else "-",
                    'estado_cambio': estado_txt,
                    '_pvp_actual_dec': pvp_act,
                    '_pvp_propuesto_dec': pvp_prop,
                    '_raw': item
                })

        self.nav_list.set_items(rows)
        total = len(rows)
        self.lbl_contador.configure(
            text=f"{total} productos cargados ({modificados} con cambios)"
        )
        self.btn_guardar.configure(text=f"GUARDAR CAMBIOS ({modificados})")

    # --- LÓGICA Y MANEJADORES ---

    def _on_buscar_lote(self):
        """Busca y carga los productos según los filtros de búsqueda."""
        termino = self.search_var.get().strip()
        cat_id = self.cat_combo.get_id()
        tipo_id = self.tipo_combo.get_id()

        self._productos_cargados = self.service.buscar_lote_productos(
            termino=termino,
            categoria_id=cat_id,
            tipo_id=tipo_id,
            limit=500
        )

        # Nueva búsqueda: las previews anteriores ya no aplican
        self._previews['nombres'].clear()
        self._previews['pvp'].clear()

        if not self._productos_cargados:
            ToastWidget.show(self.container, "No se encontraron productos con esos filtros", tipo="warning")
            self._actualizar_tabla()
            return

        if self._modo == 'nombres':
            # Sugerir un patrón inicial basado en el primer producto si está vacío
            patron = self.patron_var.get().strip()
            if not patron:
                primer_nombre = self._productos_cargados[0].get('nombre', '')
                num = self.service.extraer_numero(primer_nombre)
                if num is not None:
                    base = re.sub(
                        r'\b(?:tomo|volumen|vol|num|numero|n[ºo\.]|#)?\s*\d+\b',
                        '', primer_nombre, flags=re.IGNORECASE
                    ).strip()
                    self.patron_var.set(f"{base} Tomo {{num}}")

        self._generar_preview_actual()
        self._actualizar_tabla()
        ToastWidget.show(self.container, f"Cargados {len(self._productos_cargados)} productos", tipo="info")

    def _on_aplicar_operacion(self):
        """Genera la previsualización aplicando la operación del modo activo."""
        if not self._productos_cargados:
            ToastWidget.show(self.container, "Primero busca un lote de productos", tipo="warning")
            return

        if self._modo == 'pvp' and self._parsear_valor_pvp() is None:
            ToastWidget.show(self.container, "Introduce un valor numérico válido para la operación PVP", tipo="warning")
            return

        self._generar_preview_actual()
        self._actualizar_tabla()

    def _on_editar_fila_individual(self, row_data: dict):
        """Permite editar manualmente la propuesta de una fila (doble clic)."""
        item = row_data.get('_raw')
        if not item:
            return

        pid = item['id']

        if self._modo == 'nombres':
            nuevo_manual = show_input_dialog(
                self.container,
                titulo="EDITAR NOMBRE INDIVIDUAL",
                mensaje=f"Modificar propuesta para ID {pid} (Actual: {item['nombre_actual']}):",
                valor_defecto=item['nombre_propuesto']
            )
            if nuevo_manual is not None and nuevo_manual.strip():
                item['nombre_propuesto'] = nuevo_manual.strip()
                item['editado_manual'] = True
                self._actualizar_tabla()
        else:
            pvp_act = item.get('pvp_actual', Decimal('0.00'))
            nuevo_manual = show_input_dialog(
                self.container,
                titulo="EDITAR PVP INDIVIDUAL",
                mensaje=f"Nuevo PVP para ID {pid} (Actual: {pvp_act:.2f} €):",
                valor_defecto=str(item.get('pvp_propuesto') or pvp_act)
            )
            if nuevo_manual is not None and nuevo_manual.strip():
                try:
                    pvp_manual = Decimal(nuevo_manual.strip().replace(',', '.'))
                except InvalidOperation:
                    ToastWidget.show(self.container, "El PVP introducido no es válido", tipo="warning")
                    return
                if pvp_manual < 0:
                    ToastWidget.show(self.container, "El PVP no puede ser negativo", tipo="warning")
                    return
                item['pvp_propuesto'] = pvp_manual.quantize(Decimal('0.01'))
                item['editado_manual'] = True
                self._actualizar_tabla()

    def _on_quitar_seleccionados(self):
        """Quita los productos seleccionados de la lista de trabajo (no los borra de la BD)."""
        selected_items = self.nav_list.get_selected_items()
        if not selected_items:
            idx = getattr(self.nav_list, 'selected_index', -1)
            if 0 <= idx < len(self.nav_list._all_data):
                selected_items = [self.nav_list._all_data[idx]]

        if not selected_items:
            ToastWidget.show(self.container, "Selecciona los productos que deseas quitar de la lista", tipo="warning")
            return

        ids_a_quitar = set()
        for it in selected_items:
            raw = it.get('_raw', {})
            pid = raw.get('id') or it.get('id')
            if pid is not None:
                try:
                    ids_a_quitar.add(int(pid))
                except (ValueError, TypeError):
                    ids_a_quitar.add(pid)

        if not ids_a_quitar:
            return

        # Filtrar de la lista de trabajo y de las previews de ambos modos
        self._productos_cargados = [p for p in self._productos_cargados if p.get('id') not in ids_a_quitar]
        for pid in ids_a_quitar:
            self._previews['nombres'].pop(pid, None)
            self._previews['pvp'].pop(pid, None)

        # Limpiar selección y refrescar tabla
        if hasattr(self.nav_list, 'deselect_all'):
            self.nav_list.deselect_all()
        self._on_selection_change([])
        self._actualizar_tabla()
        ToastWidget.show(self.container, f"Se han quitado {len(ids_a_quitar)} productos de la lista", tipo="info")

    def _on_revertir(self):
        """Restaura las propuestas del modo activo a los valores originales."""
        mapa = self._previews[self._modo]
        for item in mapa.values():
            item['editado_manual'] = False
            if self._modo == 'nombres':
                item['nombre_propuesto'] = item['nombre_actual']
            else:
                item['pvp_propuesto'] = item.get('pvp_actual', Decimal('0.00'))
        self._actualizar_tabla()
        ToastWidget.show(self.container, "Propuestas restauradas a los valores originales", tipo="info")

    def _on_guardar_cambios(self):
        """Guarda los cambios del modo activo en la base de datos de forma atómica."""
        cambios_a_aplicar = [
            item for item in self._preview_list()
            if self._item_cambia(item)
        ]

        if not cambios_a_aplicar:
            ToastWidget.show(self.container, "No hay cambios pendientes de guardar", tipo="warning")
            return

        total = len(cambios_a_aplicar)
        modo_txt = "PVP" if self._modo == 'pvp' else "nombres"
        confirmado = show_warning(
            self.container,
            titulo="CONFIRMAR EDICIÓN MASIVA",
            mensaje=f"Se modificará el {modo_txt} de {total} productos.\n\n¿Deseas continuar?",
            confirm=True
        )

        if not confirmado:
            return

        usuario_id = None
        if self.owner and hasattr(self.owner, 'current_user') and self.owner.current_user:
            usuario_id = self.owner.current_user.get('id')

        try:
            if self._modo == 'nombres':
                actualizados = self.service.aplicar_cambios(cambios_a_aplicar, usuario_id=usuario_id)
            else:
                actualizados = self.service.aplicar_cambios_pvp(cambios_a_aplicar, usuario_id=usuario_id)

            ToastWidget.show(self.container, f"¡Éxito! Se han actualizado {actualizados} productos.", tipo="success")

            # Recargar SOLO los productos modificados desde la BD
            # (sin repetir la búsqueda original ni recuperar los descartados)
            ids_cambiados = [c.get('id') for c in cambios_a_aplicar if c.get('id') is not None]
            self._productos_cargados = self.service.get_productos_por_ids(ids_cambiados)

            # Limpiar preview del modo guardado y regenerar (quedará SIN CAMBIOS)
            self._previews[self._modo].clear()
            self._generar_preview_actual()
            self._actualizar_tabla()

        except Exception as e:
            logger.exception("Error guardando cambios masivos")
            ToastWidget.show(self.container, f"Error al guardar: {e}", tipo="error")

    def _on_volver(self):
        """Vuelve a la vista anterior (Búsqueda)."""
        if self.owner and hasattr(self.owner, 'show_busqueda'):
            self.owner.show_busqueda()

    def destroy(self):
        """Limpieza de la subvista."""
        try:
            self.container.destroy()
        except Exception:
            pass
