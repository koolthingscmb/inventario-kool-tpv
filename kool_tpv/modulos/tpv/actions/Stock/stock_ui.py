"""
UI overlay para consulta y gestión de stock de productos.

Hereda de SelectionOverlayTemplate y soporta 2 modos:

Modo 'stock': Lista de productos con stock
Modo 'consulta': Historial de ventas de un producto
"""
import logging
import re
from typing import Optional, Callable
import math
import customtkinter as ctk

from kool_tpv.utils.formatter_service import FormatterService

from .StockBase import StockBaseUI
from kool_tpv.base_datos.producto_service import ProductoService
from .consulta_stock_ui import ConsultaStockHandler
from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro


class StockUI(StockBaseUI):
    """Overlay para consulta de stock con modo dual (stock/consulta)."""

    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[Callable] = None):
        """
        Args:
            view_or_action_panel: TpvView o action_panel
            db: Database instance
            on_selection_callback: Callback al añadir producto al carrito
        """
        # Configuración UI
        ui_config = {
            'page_size': 15,
        }

        super().__init__(
            view_or_action_panel,
            db=db,
            on_selection_callback=on_selection_callback,
            ui_config=ui_config
        )

        # Instanciar ProductoService
        self.data_service = ProductoService(db)
        self.db = db

        # Instanciar FormatterService
        try:
            self.formatter = FormatterService()
        except Exception:
            logging.exception('Error instanciando FormatterService en StockUI')
            self.formatter = None

        # Modo del overlay: 'stock' o 'consulta'
        self.modo = 'stock'
        self.producto_consulta = None  # Guarda producto seleccionado para consulta
        self._visor_negro = None
        # Handler for consulta-related behaviour (keeps logic separate)
        try:
            self._consulta_handler = ConsultaStockHandler(self)
        except Exception:
            self._consulta_handler = None
        # Crear VisorNegro pero NO mostrarlo automáticamente
        try:
            view = getattr(self, 'view', None)
            parent_widget = None
            if view is not None and getattr(view, 'cart_view', None) is not None:
                parent_widget = view.cart_view
            else:
                parent_widget = getattr(self, 'overlay', None)
            if parent_widget is not None:
                self._visor_negro = VisorNegro(parent_widget)
                self._visor_negro.set_text('')
                try:
                    self._visor_negro.set_text_color('#00FF00')
                except Exception:
                    pass
                try:
                    self._visor_negro.set_font_size(13)
                except Exception:
                    pass
                # Do NOT show the VisorNegro here automatically
        except Exception:
            logging.exception('Error creando VisorNegro en StockUI')
        # Saved page size to restore after leaving consulta mode
        self._saved_page_size = None

        # Personalizar título inicial
        self.title_text = "STOCK"
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Configurar columnas para MODO STOCK
        self.columns_config_stock = [
            ("id", "ID", 60, "center"),
            ("nombre", "Nombre", 280, "w"),
            ("stock", "Stock", 80, "center"),
            ("categoria", "Categoría", 150, "w"),
            ("tipo", "Tipo", 150, "w"),
        ]

        # Configurar columnas para MODO CONSULTA
        self.columns_config_consulta = [
            ("ticket_id", "Ticket", 80, "center"),
            ("fecha", "Fecha", 150, "center"),
            ("cantidad", "Cant", 80, "center"),
            ("cliente", "Cliente", 250, "w"),
        ]

        # Aplicar configuración inicial (stock)
        self._aplicar_config_columnas(self.columns_config_stock)

        # Adaptar botones de la zona superior
        self._adaptar_botones()

    def _adaptar_botones(self):
        """Adaptar botones de top_buttons según especificación."""
        try:
            # Renombrar "Añadir" → "Consultar"
            if hasattr(self, 'anadir_btn') and self.anadir_btn is not None:
                try:
                    self.anadir_btn.configure(text="Consultar", command=self._on_consultar)
                except Exception:
                    # Some templates may expose different attributes
                    pass

            # Crear botón "Modificar" nuevo
            if hasattr(self, 'header_actions_frame'):
                try:
                    self.modificar_btn = ctk.CTkButton(
                        self.header_actions_frame,
                        text="Modificar",
                        fg_color=getattr(self, 'ADD_BTN_COLOR', '#2ecc71'),
                        command=self._on_modificar,
                        width=140,
                        state='disabled'  # Placeholder por ahora
                    )
                    # Insertar entre Aceptar y Consultar si existe
                    try:
                        self.modificar_btn.pack(side="left", padx=5, after=self.aceptar_btn)
                    except Exception:
                        # fallback: pack normally
                        self.modificar_btn.pack(side="left", padx=5)
                except Exception:
                    logging.exception('Error creando botón Modificar en StockUI')
        except Exception:
            logging.exception('Error adaptando botones en StockUI')

    def _aplicar_config_columnas(self, columns_config):
        """Aplicar configuración de columnas al treeview.

        Args:
            columns_config: Lista de tuplas (key, heading, width, anchor)
        """
        try:
            if not hasattr(self, 'tree') or self.tree is None:
                return

            # Guardar config actual
            self.columns_config = columns_config

            # Reconfigurar tree
            cols = [c[0] for c in columns_config]
            self.tree.configure(columns=cols)

            for key, heading, width, anchor in columns_config:
                try:
                    self.tree.heading(key, text=heading)
                    self.tree.column(key, width=width, anchor=anchor)
                except Exception:
                    logging.exception(f'Error configurando columna {key}')
        except Exception:
            logging.exception('Error aplicando config de columnas')

    def _load_and_render(self, termino: str) -> None:
        """Cargar datos según modo actual y renderizar.

        Args:
            termino: Término de búsqueda
        """
        try:
            if self.modo == 'stock':
                self._load_productos(termino)
            elif self.modo == 'consulta':
                if self._consulta_handler is not None:
                    self._items = self._consulta_handler.load_ventas(termino)
                else:
                    self._items = []

            self._current_page = 0
            self._render_clients_page()

        except Exception:
            logging.exception('Error en _load_and_render de StockUI')

    def _load_productos(self, termino: str):
        """Cargar productos usando ProductoService."""
        try:
            if self.data_service:
                self._items = self.data_service.listar_productos(termino)
            else:
                self._items = []
        except Exception:
            logging.exception('Error cargando productos')
            self._items = []

    def _load_ventas_producto(self, termino=''):
        """Deprecated: delegated to ConsultaStockHandler.load_ventas."""
        try:
            if self._consulta_handler is not None:
                self._items = self._consulta_handler.load_ventas(termino)
            else:
                self._items = []
        except Exception:
            logging.exception('Error delegado cargando ventas de producto')
            self._items = []

    def _render_clients_page(self):
        """Renderizar página según modo actual."""
        try:
            # Diagnostic: página y tamaño
            try:
                ps = getattr(self, '_page_size', 15)
                start = getattr(self, '_current_page', 0) * ps
                total = len(self._items or [])
                logging.info('StockUI._render_clients_page modo=%s page=%s page_size=%s total_items=%s start=%s', self.modo, getattr(self, '_current_page', 0), ps, total, start)
            except Exception:
                pass
            # Limpiar tree
            for child in list(self.tree.get_children()):
                try:
                    self.tree.delete(child)
                except Exception:
                    pass

            # Calcular rango de página
            start = getattr(self, '_current_page', 0) * getattr(self, '_page_size', 15)
            end = start + getattr(self, '_page_size', 15)
            page_items = (self._items or [])[start:end]

            # Renderizar según modo
            if self.modo == 'stock':
                self._render_productos(page_items)
            elif self.modo == 'consulta':
                self._render_ventas(page_items)

            # Actualizar paginación
            total_pages = max(1, math.ceil(len(self._items or []) / getattr(self, '_page_size', 15)))
            try:
                if hasattr(self, 'page_label'):
                    self.page_label.configure(text=f"Página {getattr(self, '_current_page', 0) + 1} / {total_pages}")
                if hasattr(self, 'prev_btn'):
                    self.prev_btn.configure(state=('normal' if getattr(self, '_current_page', 0) > 0 else 'disabled'))
                if hasattr(self, 'next_btn'):
                    self.next_btn.configure(state=('normal' if getattr(self, '_current_page', 0) < total_pages - 1 else 'disabled'))
            except Exception:
                pass

        except Exception:
            logging.exception('Error renderizando página en StockUI')

    def _render_productos(self, productos):
        """Renderizar lista de productos (modo stock)."""
        for prod in productos:
            try:
                self.tree.insert(
                    '',
                    'end',
                    iid=str(prod.get('id')),
                    values=(
                        prod.get('id'),
                        prod.get('nombre'),
                        prod.get('stock_actual'),
                        prod.get('categoria'),
                        prod.get('tipo')
                    )
                )
            except Exception:
                logging.exception('Error insertando producto en tree')

    def _render_ventas(self, ventas):
        """Deprecated: delegated to ConsultaStockHandler.render_ventas."""
        try:
            if self._consulta_handler is not None:
                self._consulta_handler.render_ventas(ventas)
        except Exception:
            logging.exception('Error delegando render_ventas')

    def _on_consultar(self):
        """Handler botón Consultar: cambiar a modo consulta."""
        try:
            # Obtener producto seleccionado
            sel = self.tree.selection()
            if not sel:
                return

            iid = sel[0]

            # Buscar producto en _items
            producto = None
            for p in (self._items or []):
                if str(p.get('id')) == str(iid):
                    producto = p
                    break

            if not producto:
                return

            # Guardar producto para consulta
            self.producto_consulta = producto

            # Cambiar a modo consulta
            self._cambiar_modo('consulta')
            logging.info(f'Consultando ventas para producto {producto.get("nombre")}')

        except Exception:
            logging.exception('Error en _on_consultar')

    def _on_modificar(self):
        """Handler botón Modificar (placeholder)."""
        logging.info('Modificar producto - placeholder (no implementado)')

    def _cambiar_modo(self, nuevo_modo: str):
        """Cambiar entre modo 'stock' y 'consulta'.

        Args:
            nuevo_modo: 'stock' o 'consulta'
        """
        try:
            self.modo = nuevo_modo

            if self.modo == 'stock':
                # Restaurar modo stock
                self._configurar_modo_stock()
            elif self.modo == 'consulta':
                # Activar modo consulta (delegar a handler)
                try:
                    if self._consulta_handler is not None:
                        self._consulta_handler.configurar_modo_consulta()
                    else:
                        self._configurar_modo_consulta()
                except Exception:
                    # fallback to internal method if exists
                    try:
                        self._configurar_modo_consulta()
                    except Exception:
                        pass

            # En modo consulta forzar un mínimo de filas visibles y guardar el valor previo
            try:
                if self.modo == 'consulta':
                    try:
                        # Do not force page_size here; keep template dynamic sizing
                        # previous behavior forced a minimum of 20 which could
                        # collapse pagination when many items exist. Preserve
                        # existing _page_size to allow proper pagination.
                        pass
                    except Exception:
                        pass
                else:
                    # Restaurar tamaño de página original si existe
                    try:
                        if getattr(self, '_saved_page_size', None) is not None:
                            self._page_size = self._saved_page_size
                            self._saved_page_size = None
                    except Exception:
                        pass
            except Exception:
                pass

            # Recargar datos
            self._load_and_render('')

        except Exception:
            logging.exception('Error cambiando modo en StockUI')

    def _configurar_modo_stock(self):
        """Configurar UI para modo stock."""
        try:
            # Cambiar título
            self.title_text = "STOCK"
            if hasattr(self, 'header_label'):
                try:
                    self.header_label.configure(text=self.title_text)
                except Exception:
                    pass

            # Aplicar columnas de stock
            self._aplicar_config_columnas(self.columns_config_stock)

            # Mostrar botones stock (Modificar, Consultar)
            if hasattr(self, 'modificar_btn'):
                try:
                    self.modificar_btn.pack(side="left", padx=5)
                except Exception:
                    pass

            if hasattr(self, 'anadir_btn'):
                try:
                    self.anadir_btn.configure(text="Consultar")
                    self.anadir_btn.pack(side="left", padx=5)
                except Exception:
                    pass

            # Ocultar botón Volver si existe
            if hasattr(self, 'volver_btn'):
                try:
                    self.volver_btn.pack_forget()
                except Exception:
                    pass

            # Botón Aceptar: añadir al carrito
            if hasattr(self, 'aceptar_btn'):
                try:
                    self.aceptar_btn.configure(text="Aceptar", command=self._on_accept)
                except Exception:
                    pass

            # Limpiar producto consulta
            self.producto_consulta = None

            # Limpiar búsqueda
            try:
                if hasattr(self, 'search_var'):
                    self.search_var.set('')
            except Exception:
                pass

            # Habilitar y dar focus a search_entry
            try:
                if hasattr(self, 'search_entry') and self.search_entry:
                    self.search_entry.configure(state='normal')
                    self.after(100, lambda: self.search_entry.focus_set())
            except Exception:
                pass

            # (visor de ticket eliminado en rollback) --- no-op
            # Si existe el VisorNegro (creado en modo consulta), destruirlo
            try:
                if getattr(self, '_visor_negro', None) is not None:
                    try:
                        self._visor_negro.destroy()
                    except Exception:
                        pass
                    self._visor_negro = None
            except Exception:
                pass

        except Exception:
            logging.exception('Error configurando modo stock')

    def _configurar_modo_consulta(self):
        """Delegar configuración de modo 'consulta' al handler especializado."""
        try:
            if getattr(self, '_consulta_handler', None) is not None:
                try:
                    self._consulta_handler.configurar_modo_consulta()
                    return
                except Exception:
                    logging.exception('Error en ConsultaStockHandler.configurar_modo_consulta')
        except Exception:
            logging.exception('Error delegando configurar_modo_consulta')

    def _on_ficha_cliente(self):
        """Handler botón Ficha Cliente (placeholder)."""
        logging.info('Ficha cliente - placeholder (no implementado)')

    def _on_imprimir_ticket(self):
        """Imprimir el ticket actualmente mostrado en el VisorNegro.

        Si no hay ticket mostrado, intenta tomar la selección actual.
        """
        try:
            if getattr(self, '_consulta_handler', None) is not None:
                try:
                    self._consulta_handler.on_imprimir_ticket()
                    return
                except Exception:
                    logging.exception('Error en ConsultaStockHandler.on_imprimir_ticket')
        except Exception:
            logging.exception('Error delegando _on_imprimir_ticket')

    def _on_mostrar_ticket(self):
        """Mostrar ticket del elemento seleccionado en modo consulta."""
        try:
            if getattr(self, '_consulta_handler', None) is not None:
                try:
                    self._consulta_handler.on_mostrar_ticket()
                    return
                except Exception:
                    logging.exception('Error en ConsultaStockHandler.on_mostrar_ticket')
        except Exception:
            logging.exception('Error delegando _on_mostrar_ticket')

    def _on_mi_tree_select(self, event=None):
        """Detectar selección en tree (no usado, binding desactivado)."""
        # Este método ya no se usa porque el binding fue eliminado
        return

    def hide(self):
        """Override hide() para detectar modo.

        Si está en consulta, vuelve a stock.
        Si está en stock, cierra overlay.
        """
        try:
            if getattr(self, 'modo', None) == 'consulta':
                # Volver a modo stock (no cerrar)
                self._cambiar_modo('stock')
            else:
                # Cerrar overlay
                try:
                    super().hide()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error en hide() de StockUI')
            # Fallback: cerrar siempre
            try:
                super().hide()
            except Exception:
                pass

    def _on_row_double_click(self, event=None):
        """Override: doble click en modo consulta muestra ticket.

        En modo stock: añade al carrito SIN cerrar overlay.
        En modo consulta: muestra ticket.
        """
        try:
            if self.modo == 'consulta':
                # Mostrar ticket (no confirmar selección ni añadir al carrito)
                try:
                    self._on_mostrar_ticket()
                except Exception:
                    logging.exception('Error mostrando ticket en doble click (StockUI)')
                return
            else:
                # Modo stock: añadir al carrito SIN cerrar
                sel = self.tree.selection()
                if sel and self.on_selection_callback:
                    iid = sel[0]
                    # Buscar producto en _items
                    for item in (self._items or []):
                        if str(item.get('id')) == str(iid):
                            try:
                                self.on_selection_callback(item)
                                logging.info(f'Producto añadido: {item.get("nombre")}')
                            except Exception:
                                logging.exception('Error en callback de selección')
                            break
        except Exception:
            logging.exception('Error en _on_row_double_click de StockUI')

    # _on_tree_select removed: using direct binding to _on_mi_tree_select instead
