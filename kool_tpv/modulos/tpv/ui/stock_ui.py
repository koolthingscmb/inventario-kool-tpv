"""
UI overlay para consulta y gestión de stock de productos.

Hereda de SelectionOverlayTemplate y soporta 2 modos:

Modo 'stock': Lista de productos con stock
Modo 'consulta': Historial de ventas de un producto
"""
import logging
from typing import Optional, Callable
import math
import customtkinter as ctk

from kool_tpv.utils.formatter_service import FormatterService

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.base_datos.producto_service import ProductoService


class StockUI(SelectionOverlayTemplate):
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
                self._load_ventas_producto(termino)

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
        """Cargar ventas con filtro opcional por nombre de cliente."""
        try:
            if not self.producto_consulta:
                self._items = []
                return

            producto_id = self.producto_consulta.get('id')
            if self.data_service:
                ventas = self.data_service.obtener_ventas_producto(producto_id)

                # Filtrar por nombre de cliente si hay término de búsqueda
                if termino:
                    termino_lower = termino.lower()
                    self._items = [
                        v for v in ventas
                        if termino_lower in (v.get('cliente_nombre') or '').lower()
                    ]
                else:
                    self._items = ventas
            else:
                self._items = []
        except Exception:
            logging.exception('Error cargando ventas de producto')
            self._items = []

    def _render_clients_page(self):
        """Renderizar página según modo actual."""
        try:
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
        """Renderizar lista de ventas (modo consulta)."""
        for venta in ventas:
            try:
                # Formatear fecha a formato español (DD/MM/YYYY)
                fecha_raw = venta.get('fecha', '')
                fecha_formateada = ''
                try:
                    if self.formatter:
                        fecha_formateada = self.formatter.format_fecha(fecha_raw)
                    else:
                        # Fallback manual: 2026-02-08 → 08/02/2026
                        if fecha_raw and len(fecha_raw) >= 10:
                            partes = fecha_raw[:10].split('-')
                            if len(partes) == 3:
                                fecha_formateada = f"{partes[2]}/{partes[1]}/{partes[0]}"
                            else:
                                fecha_formateada = fecha_raw.split()[0]
                        else:
                            fecha_formateada = fecha_raw
                except Exception:
                    fecha_formateada = fecha_raw.split()[0] if fecha_raw else ''

                # Formatear cantidad como entero
                cantidad_raw = venta.get('cantidad', 0)
                try:
                    cantidad_str = str(int(float(cantidad_raw)))
                except Exception:
                    cantidad_str = str(cantidad_raw)

                try:
                    ticket_id_row = venta.get('ticket_id') or venta.get('id')
                    # Preferir num_ticket si viene; si no, leer desde la tabla tickets
                    num_ticket_display = venta.get('num_ticket')
                    if not num_ticket_display:
                        try:
                            row = self.db.fetch_one("SELECT num_ticket FROM tickets WHERE id = ?", (ticket_id_row,))
                            if row:
                                num_ticket_display = row[0]
                        except Exception:
                            pass

                    display_ticket = num_ticket_display or ticket_id_row

                    self.tree.insert(
                        '',
                        'end',
                        iid=str(ticket_id_row),  # usar id DB como iid
                        values=(
                            display_ticket,
                            fecha_formateada,
                            cantidad_str,
                            venta.get('cliente_nombre')
                        )
                    )
                except Exception:
                    logging.exception('Error insertando venta en tree')
            except Exception:
                logging.exception('Error insertando venta en tree')

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
                # Activar modo consulta
                self._configurar_modo_consulta()

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

        except Exception:
            logging.exception('Error configurando modo stock')

    def _configurar_modo_consulta(self):
        """Configurar UI para modo consulta."""
        try:
            # Cambiar título con nombre del producto
            nombre_prod = self.producto_consulta.get('nombre', 'Producto') if self.producto_consulta else 'Producto'
            self.title_text = f"CONSULTA: {nombre_prod}"
            if hasattr(self, 'header_label'):
                try:
                    self.header_label.configure(text=self.title_text)
                except Exception:
                    pass

            # Aplicar columnas de consulta
            self._aplicar_config_columnas(self.columns_config_consulta)

            # Ocultar botones de stock
            if hasattr(self, 'modificar_btn'):
                try:
                    self.modificar_btn.pack_forget()
                except Exception:
                    pass

            if hasattr(self, 'anadir_btn'):
                try:
                    self.anadir_btn.pack_forget()
                except Exception:
                    pass

            # Crear/mostrar botón Volver
            if not hasattr(self, 'volver_btn'):
                try:
                    self.volver_btn = ctk.CTkButton(
                        self.header_actions_frame,
                        text="Volver",
                        fg_color='#7f8c8d',
                        hover_color='#95a5a6',
                        command=lambda: self._cambiar_modo('stock'),
                        width=140
                    )
                except Exception:
                    self.volver_btn = None

            try:
                if self.volver_btn is not None:
                    self.volver_btn.pack(side="left", padx=5)
            except Exception:
                pass

            # Botón Aceptar → Mostrar Ticket
            if hasattr(self, 'aceptar_btn'):
                try:
                    self.aceptar_btn.configure(text="Mostrar Ticket", command=self._on_mostrar_ticket)
                except Exception:
                    pass

            # Limpiar búsqueda pero MANTENER habilitada para filtrar clientes
            try:
                if hasattr(self, 'search_var'):
                    self.search_var.set('')
                if hasattr(self, 'search_entry'):
                    self.search_entry.configure(state='normal')
                    self.after(100, lambda: self.search_entry.focus_set())
            except Exception:
                pass

        except Exception:
            logging.exception('Error configurando modo consulta')

    def _on_ficha_cliente(self):
        """Handler botón Ficha Cliente (placeholder)."""
        logging.info('Ficha cliente - placeholder (no implementado)')

    def _on_mostrar_ticket(self):
        """Mostrar ticket del elemento seleccionado en modo consulta."""
        try:
            sel = self.tree.selection()
            if not sel:
                logging.info('No hay ticket seleccionado')
                return

            try:
                ticket_id = int(sel[0])
            except Exception:
                logging.error('ID de ticket inválido')
                return

            # Generar ticket
            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
            from kool_tpv.utils.textview_dialog import show_text_viewer

            impresora = ImpresoraService(self.db)
            ticket_text = impresora.generar_ticket_desde_id(ticket_id)

            if not ticket_text:
                logging.warning(f'No se pudo generar ticket {ticket_id}')
                return

            # Parent correcto
            try:
                parent = self.view.parent.winfo_toplevel()
            except Exception:
                parent = self.view.parent

            # Obtener num_ticket para título
            num_ticket = None
            try:
                num_row = self.db.fetch_one(
                    "SELECT num_ticket FROM tickets WHERE id = ?",
                    (ticket_id,)
                )
                if num_row:
                    num_ticket = num_row[0]
            except Exception:
                logging.exception('Error obteniendo num_ticket')

            # Mostrar dialog
            titulo = f"TICKET #{num_ticket}" if num_ticket else f"TICKET #{ticket_id}"

            # Definir callback de impresión que reutiliza ImpresoraService
            def _print_ticket():
                try:
                    texto_imp = impresora.generar_ticket_desde_id(ticket_id)
                    if texto_imp:
                        print("\n" + "="*50)
                        print(" SIMULACIÓN IMPRESIÓN TICKET ")
                        print("="*50 + "\n")
                        print(texto_imp)
                        print("\n" + "="*50 + "\n")
                        try:
                            impresora.logger.info("Ticket impreso (simulado) num_ticket=%s", num_ticket or ticket_id)
                        except Exception:
                            pass
                except Exception:
                    logging.exception('Error imprimiendo ticket desde dialog')

            show_text_viewer(parent, titulo, ticket_text, print_callback=_print_ticket)

        except Exception:
            logging.exception('Error mostrando ticket desde botón')

    def _on_mi_tree_select(self, event=None):
        """Detectar selección en tree (no usado, binding desactivado)."""
        # Este método ya no se usa porque el binding fue eliminado
        pass

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
                # Mostrar ticket
                self._on_mostrar_ticket()
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
