"""UI para mostrar Top General de Clientes.

Estructura mínima: header (label), NavList con resultados y footer con botones.
"""
from typing import Optional
import logging
import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.custom_dialog import show_warning
from kool_tpv.modulos.clientes.services.clientes_tops_service import ClientesTopsService
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService

logger = logging.getLogger(__name__)


class ClientesTopsUI(ctk.CTkFrame):
    """UI básica para mostrar TOP CLIENTES (Top General).

    No contiene filtros por ahora; carga automáticamente el Top General.
    """

    def __init__(self, parent, db, owner: Optional[object] = None, keyboard_manager: Optional[object] = None):
        super().__init__(parent)
        self.db = db
        self.owner = owner
        self.keyboard_manager = keyboard_manager
        self.module_name = 'clientes'
        self.service = ClientesTopsService(db)

        # Colores por módulo
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {}

        # Header
        try:
            self.header_frame = ctk.CTkFrame(self, fg_color=self.colors.get('background', '#000000'))
            self.header_frame.pack(fill='x', padx=12, pady=(12, 6))

            self.title_label = ctk.CTkLabel(
                self.header_frame,
                text='TOP CLIENTES',
                font=get_font('title', module=self.module_name),
                text_color=self.colors.get('text', '#FFFFFF')
            )
            self.title_label.pack(anchor='w', padx=6, pady=6)
            # Estado de filtros
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            self.modo_tesoro = False
            # Filters sub-frame: botones de filtro (visual only por ahora)
            try:
                self.filters_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
                self.filters_frame.pack(fill='x', padx=6, pady=(4, 6))

                try:
                    btn_general = ButtonFactory.create_button(
                        self.filters_frame,
                        'GENERAL',
                        command=self._on_general,
                        style_key='mini_outline_clientes'
                    )
                    btn_general.pack(side='left', padx=4)

                    btn_tesoro_actual = ButtonFactory.create_button(
                        self.filters_frame,
                        'TESORO ACTUAL',
                        command=self._on_tesoro_actual,
                        style_key='mini_outline_clientes'
                    )
                    btn_tesoro_actual.pack(side='left', padx=4)

                    btn_tesoro_gastado = ButtonFactory.create_button(
                        self.filters_frame,
                        'TESORO GASTADO',
                        command=self._on_tesoro_gastado,
                        style_key='mini_outline_clientes'
                    )
                    btn_tesoro_gastado.pack(side='left', padx=4)

                    btn_tesoro_total = ButtonFactory.create_button(
                        self.filters_frame,
                        'TESORO TOTAL GANADO',
                        command=self._on_tesoro_total,
                        style_key='mini_outline_clientes'
                    )
                    btn_tesoro_total.pack(side='left', padx=4)
                except Exception:
                    logger.exception('Error creando botones de filtro en ClientesTopsUI')
            except Exception:
                logger.exception('Error creando filters_frame en ClientesTopsUI')

            # Search frame debajo de filtros (contiene combos para categoria, tipo y producto)
            try:
                self.search_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
                self.search_frame.pack(fill='x', padx=6, pady=(4, 6))
                try:
                    # Categoria
                    lbl_cat = ctk.CTkLabel(self.search_frame, text='Categoría:', font=get_font('label', module=self.module_name), text_color=self.colors.get('text', '#FFFFFF'))
                    lbl_cat.pack(side='left', padx=(0, 6))
                    self.cb_categoria = SearchableCombo(
                        self.search_frame,
                        placeholder='Buscar categoría...',
                        module_name=self.module_name,
                        width=220,
                        command=lambda value: self._on_categoria_selected()
                    )
                    self.cb_categoria.pack(side='left', padx=(0, 8))

                    # Tipo
                    lbl_tipo = ctk.CTkLabel(self.search_frame, text='Tipo:', font=get_font('label', module=self.module_name), text_color=self.colors.get('text', '#FFFFFF'))
                    lbl_tipo.pack(side='left', padx=(0, 6))
                    self.cb_tipo = SearchableCombo(
                        self.search_frame,
                        placeholder='Buscar tipo...',
                        module_name=self.module_name,
                        width=220,
                        command=lambda value: self._on_tipo_selected()
                    )
                    self.cb_tipo.pack(side='left', padx=(0, 8))

                    # Producto (principal)
                    lbl_prod = ctk.CTkLabel(self.search_frame, text='Producto:', font=get_font('label', module=self.module_name), text_color=self.colors.get('text', '#FFFFFF'))
                    lbl_prod.pack(side='left', padx=(0, 6))
                    self.search_combo = SearchableCombo(
                        self.search_frame,
                        placeholder='Buscar producto...',
                        module_name=self.module_name,
                        width=420,
                        command=lambda value: self._on_producto_selected()
                    )
                    self.search_combo.pack(side='left', fill='x', expand=True)
                    

                    # Cargar opciones reales en los combos
                    try:
                        self._load_filter_options()
                    except Exception:
                        logger.exception('Error llamando a _load_filter_options')

                except Exception:
                    logger.exception('Error creando SearchableCombo en ClientesTopsUI')
            except Exception:
                logger.exception('Error creando search_frame en ClientesTopsUI')
        except Exception:
            logger.exception('Error creando header en ClientesTopsUI')

        # NavList (data area)
        try:
            columns = [
                ("posicion", 60),
                ("nombre", 200),
                ("total_tickets", 120),
                ("total_unidades", 120),
                ("total_euros", 120),
                # Campos de tesoro (clave, ancho, texto a mostrar en header)
                ("tesoro_total", 120, 'TESORO ACTUAL'),
                ("tesoro_gastado_total", 140, 'TESORO GASTADO'),
                ("tesoro_historico", 160, 'TESORO TOTAL GANADO'),
            ]

            # on_double_click: abrir ficha de cliente en el owner si existe
            def _on_double_click(data):
                if self.owner:
                    try:
                        self.owner.show_editar_cliente(data.get("cliente_id"))
                    except Exception:
                        raise

            self.nav_list = VirtualNavList(self, columns=columns, module_name=self.module_name, keyboard_manager=self.keyboard_manager, on_double_click=_on_double_click)
            self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)

            # Cargar datos
            try:
                items = self.service.get_top_clientes_general()
                # Asegurar formato de total_euros (mostrar 2 decimales)
                for it in items:
                    try:
                        te = it.get('total_euros', 0.0)
                        it['total_euros'] = f"{float(te):.2f}"
                    except Exception:
                        pass
                self.nav_list.set_items(items)
            except Exception:
                logger.exception('Error cargando top clientes en ClientesTopsUI')
        except Exception:
            logger.exception('Error creando NavList en ClientesTopsUI')

        # Footer con botones (imprimir / exportar)
        try:
            self.footer_frame = ctk.CTkFrame(self, fg_color='transparent')
            self.footer_frame.pack(side='bottom', fill='x', padx=12, pady=12)

            def _on_imprimir():
                # placeholder
                return

            def _on_exportar():
                # placeholder
                return

            btn_print = create_action_button(self.footer_frame, 'imprimir', _on_imprimir)
            btn_print.pack(side='left', padx=8)

            btn_export = create_action_button(self.footer_frame, 'exportar', _on_exportar)
            btn_export.pack(side='left', padx=8)
        except Exception:
            logger.exception('Error creando footer en ClientesTopsUI')

        # Breadcrumb name para BaseModuleView auto-update
        try:
            self.breadcrumb_name = 'CLIENTES / TOPS'
        except Exception:
            pass

    def get_widget(self):
        return self

    # --- Filtrado dinámico ---
    def _refrescar_top(self):
        try:
            if self.modo_tesoro:
                items = self.service.get_top_por_tesoro()
            elif any((self.filtro_categoria_id is not None, self.filtro_tipo_id is not None, self.filtro_producto_id is not None)):
                items = self.service.get_top_filtrado(
                    categoria_id=self.filtro_categoria_id,
                    tipo_id=self.filtro_tipo_id,
                    producto_id=self.filtro_producto_id,
                )
            else:
                items = self.service.get_top_clientes_general()

            # Formatear total_euros
            for it in items:
                try:
                    te = it.get('total_euros', 0.0)
                    it['total_euros'] = f"{float(te):.2f}"
                except Exception:
                    pass

            # Si no hay resultados, mostrar advertencia y NO limpiar la lista previa
            if not items:
                try:
                    # Mostrar diálogo modal de advertencia
                    try:
                        show_warning(self, 'Sin resultados', 'No hay ventas para esos filtros')
                    except Exception:
                        pass

                    # Si ya había elementos en la lista, mantenerlos y salir
                except Exception:
                    logger.exception('Error manejando caso sin resultados en _refrescar_top')

            try:
                self.nav_list.set_items(items)
            except Exception:
                logger.exception('Error seteando items en NavList desde _refrescar_top')
        except Exception:
            logger.exception('Error en _refrescar_top')

    def _on_categoria_selected(self):
        try:
            print("CATEGORIA SELECTED:", self.cb_categoria.get_id())
            print("TIPO SELECTED:", getattr(self, 'cb_tipo', None) and self.cb_tipo.get_id())
            print("PRODUCTO SELECTED:", getattr(self, 'search_combo', None) and self.search_combo.get_id())
            cid = self.cb_categoria.get_id()
            self.filtro_categoria_id = cid if cid is not None else None
            # reset tesoro mode when applying filters
            self.modo_tesoro = False
            self._refrescar_top()
        except Exception:
            logger.exception('Error manejando seleccion categoria')

    def _on_tipo_selected(self):
        try:
            print("CATEGORIA SELECTED:", getattr(self, 'cb_categoria', None) and self.cb_categoria.get_id())
            print("TIPO SELECTED:", self.cb_tipo.get_id())
            print("PRODUCTO SELECTED:", getattr(self, 'search_combo', None) and self.search_combo.get_id())
            tid = self.cb_tipo.get_id()
            self.filtro_tipo_id = tid if tid is not None else None
            self.modo_tesoro = False
            self._refrescar_top()
        except Exception:
            logger.exception('Error manejando seleccion tipo')

    def _on_producto_selected(self):
        try:
            print("CATEGORIA SELECTED:", getattr(self, 'cb_categoria', None) and self.cb_categoria.get_id())
            print("TIPO SELECTED:", getattr(self, 'cb_tipo', None) and self.cb_tipo.get_id())
            print("PRODUCTO SELECTED:", self.search_combo.get_id())
            pid = self.search_combo.get_id()
            self.filtro_producto_id = pid if pid is not None else None
            self.modo_tesoro = False
            self._refrescar_top()
        except Exception:
            logger.exception('Error manejando seleccion producto')

    def _on_general(self):
        try:
            # limpiar filtros
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            try:
                self.cb_categoria.clear()
            except Exception:
                pass
            try:
                self.cb_tipo.clear()
            except Exception:
                pass
            try:
                self.search_combo.clear()
            except Exception:
                pass
            self.modo_tesoro = False
            self._refrescar_top()
        except Exception:
            logger.exception('Error ejecutando _on_general')

    def _on_tesoro(self):
        try:
            # limpiar filtros
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            try:
                self.cb_categoria.clear()
            except Exception:
                pass
            try:
                self.cb_tipo.clear()
            except Exception:
                pass
            try:
                self.search_combo.clear()
            except Exception:
                pass
            self.modo_tesoro = True
            self._refrescar_top()
        except Exception:
            logger.exception('Error ejecutando _on_tesoro')

    # --- Tesoro ordering helpers ---
    def _refresh_ordered_by_tesoro(self, field: str):
        try:
            items = self.service.get_top_ordenado_por_tesoro(field)

            # Formatear valores numéricos
            for it in items:
                try:
                    te = it.get('total_euros', 0.0)
                    it['total_euros'] = f"{float(te):.2f}"
                except Exception:
                    pass
                for k in ('tesoro_total', 'tesoro_gastado_total', 'tesoro_historico'):
                    try:
                        v = it.get(k, 0.0)
                        it[k] = f"{float(v):.2f}"
                    except Exception:
                        pass

            if not items:
                try:
                    show_warning(self, 'Sin resultados', 'No hay datos de tesoro para ese criterio')
                except Exception:
                    pass
            try:
                self.nav_list.set_items(items)
            except Exception:
                logger.exception('Error seteando items en NavList desde _refresh_ordered_by_tesoro')
        except Exception:
            logger.exception('Error en _refresh_ordered_by_tesoro')

    def _on_tesoro_actual(self):
        try:
            # limpiar filtros
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            try:
                self.cb_categoria.clear()
            except Exception:
                pass
            try:
                self.cb_tipo.clear()
            except Exception:
                pass
            try:
                self.search_combo.clear()
            except Exception:
                pass
            # fetch ordered by cliente.tesoro_total
            self._refresh_ordered_by_tesoro('tesoro_total')
        except Exception:
            logger.exception('Error ejecutando _on_tesoro_actual')

    def _on_tesoro_gastado(self):
        try:
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            try:
                self.cb_categoria.clear()
            except Exception:
                pass
            try:
                self.cb_tipo.clear()
            except Exception:
                pass
            try:
                self.search_combo.clear()
            except Exception:
                pass
            self._refresh_ordered_by_tesoro('tesoro_gastado_total')
        except Exception:
            logger.exception('Error ejecutando _on_tesoro_gastado')

    def _on_tesoro_total(self):
        try:
            self.filtro_categoria_id = None
            self.filtro_tipo_id = None
            self.filtro_producto_id = None
            try:
                self.cb_categoria.clear()
            except Exception:
                pass
            try:
                self.cb_tipo.clear()
            except Exception:
                pass
            try:
                self.search_combo.clear()
            except Exception:
                pass
            self._refresh_ordered_by_tesoro('tesoro_historico')
        except Exception:
            logger.exception('Error ejecutando _on_tesoro_total')

    def _load_filter_options(self):
        try:
            # Categorías
            try:
                categoria_service = CategoriaService(self.db)
                categorias = categoria_service.get_all()
                cat_options = [(c.get('id'), c.get('nombre')) for c in (categorias or [])]
                try:
                    self.cb_categoria.set_options(cat_options)
                except Exception:
                    pass
            except Exception:
                logger.exception('Error cargando categorias en _load_filter_options')

            # Tipos
            try:
                tipo_service = TipoService(self.db)
                tipos = tipo_service.get_all_tipos()
                tipo_options = [(t.get('id'), t.get('nombre')) for t in (tipos or [])]
                try:
                    self.cb_tipo.set_options(tipo_options)
                except Exception:
                    pass
            except Exception:
                logger.exception('Error cargando tipos en _load_filter_options')

            # Productos
            try:
                producto_service = ProductoService(self.db)
                productos = producto_service.listar_productos()
                prod_options = [(p.get('id'), p.get('nombre')) for p in (productos or [])]
                try:
                    self.search_combo.set_options(prod_options)
                except Exception:
                    pass
            except Exception:
                logger.exception('Error cargando productos en _load_filter_options')

        except Exception:
            logger.exception('Error cargando opciones de filtros en ClientesTopsUI')
