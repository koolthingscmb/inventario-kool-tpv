"""Panel overlay para Devoluciones — clon de SelectionOverlayTemplate adaptado.

Este módulo define `DevolucionesPanel` (interfaz) y `DevolucionAction`
que se usa desde `TpvView` para abrir el overlay.

Reglas específicas:
- Título: "DEVOLUCIONES" y subtítulo "Introduce EAN o nombre del artículo".
- Columnas: id, nombre, categoría, tipo, stock.
- Al mostrar, carga todos los productos ordenados por id usando ProductoService.
"""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import logging

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService


class DevolucionesPanel(SelectionOverlayTemplate):
    """Overlay específico para devoluciones.

    Nota: acceso restringido a admin/permiso (pendiente de implementación).
    """

    def __init__(self, view_or_action_panel: Any, db: Database, on_selection_callback: Optional[callable] = None, ui_config: Optional[dict] = None):
        # set title and columns before calling super so the base constructor
        # builds the header and treeview with the right config
        self.title_text = "DEVOLUCIONES"
        # columns: id, nombre, categoría, tipo, stock
        self.columns_config = [
            ("id", "ID", 80, "center"),
            ("nombre", "Nombre", 300, "w"),
            ("categoria", "Categoría", 160, "w"),
            ("tipo", "Tipo", 120, "center"),
            ("stock", "Stock", 100, "e"),
        ]

        super().__init__(view_or_action_panel, db, on_selection_callback=on_selection_callback, ui_config=ui_config)

        # instantiate producto service
        try:
            # Prefer passed db directly as it is more reliable than root attribute
            self.producto_service = ProductoService(db)
        except Exception:
            logging.exception('Error instanciando ProductoService en DevolucionesPanel')
            self.producto_service = None

        # Ajustar etiquetas y estilo de los botones del header según petición
        try:
            # El botón `aceptar_btn` debe mostrar "Añadir"
            if hasattr(self, 'aceptar_btn') and self.aceptar_btn is not None:
                try:
                    self.aceptar_btn.configure(text="Añadir")
                except Exception:
                    try:
                        self.aceptar_btn['text'] = "Añadir"
                    except Exception:
                        pass

            # El botón `anadir_btn` debe mostrar "Cliente" y ser amarillo con texto negro
            if hasattr(self, 'anadir_btn') and self.anadir_btn is not None:
                try:
                    # Prefer configure; algunos entornos aceptan 'text_color'
                    self.anadir_btn.configure(text="Cliente", fg_color="#FFD400", text_color="#000000")
                except Exception:
                    try:
                        self.anadir_btn.configure(text="Cliente", fg_color="#FFD400")
                        self.anadir_btn['fg_color'] = "#FFD400"
                        # intentar setear color de texto vía opción directa si existe
                        try:
                            self.anadir_btn['text_color'] = "#000000"
                        except Exception:
                            pass
                    except Exception:
                        try:
                            self.anadir_btn['text'] = "Cliente"
                        except Exception:
                            pass
                # Wire the Cliente button to open the CLIENTES overlay
                try:
                    def _open_clientes():
                        try:
                            # Prefer existing ClienteAction on the view
                            if getattr(self, 'view', None) is not None and getattr(self.view, '_cliente_action', None) is not None:
                                try:
                                    self.view._cliente_action.ejecutar()
                                    return
                                except Exception:
                                    pass

                            # Fallback: construct a ClienteAction with available references
                            from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
                            carrito = None
                            # try devoluciones_service -> carrito_service
                            if getattr(self, 'devoluciones_service', None) is not None and getattr(self.devoluciones_service, 'carrito_service', None) is not None:
                                carrito = self.devoluciones_service.carrito_service
                            # try view attribute
                            if carrito is None and getattr(self, 'view', None) is not None and getattr(self.view, 'carrito_service', None) is not None:
                                carrito = self.view.carrito_service
                            db_ref = None
                            try:
                                db_ref = getattr(self.root, 'db', None) if getattr(self, 'root', None) is not None else None
                                if db_ref is None:
                                    db_ref = getattr(self, 'db', None)
                            except Exception:
                                db_ref = None
                            try:
                                action = ClienteAction(getattr(self, 'view', None) or self, db_ref, carrito)
                                action.ejecutar()
                            except Exception:
                                logging.exception('Error abriendo panel CLIENTES desde DevolucionesPanel')
                        except Exception:
                            logging.exception('Error en _open_clientes fallback')

                    try:
                        self.anadir_btn.configure(command=_open_clientes)
                    except Exception:
                        try:
                            self.anadir_btn['command'] = _open_clientes
                        except Exception:
                            pass
                except Exception:
                    logging.exception('Error vinculando boton Cliente en DevolucionesPanel')
        except Exception:
            logging.exception('Error ajustando botones header en DevolucionesPanel')

        # Insert subtitle between header and search controls: re-pack to ensure order
        try:
            # remove search_controls_frame, add subtitle, then repack search_controls_frame
            try:
                self.search_controls_frame.pack_forget()
            except Exception:
                pass
            subtitle_font = (getattr(self, 'FONT_FAMILY', 'Arial'), int(getattr(self, 'HEADER_FONT_SIZE', 16) // 1.7))
            self.subtitle_label = ctk.CTkLabel(self.top_buttons, text="Introduce EAN o nombre del artículo", font=subtitle_font)
            self.subtitle_label.pack(side="top", anchor="w", padx=(0, 12), pady=(2, 0))
            try:
                self.search_controls_frame.pack(side="top", anchor="w", pady=(8, 0))
            except Exception:
                pass
        except Exception:
            logging.exception('Error insertando subtítulo en DevolucionesPanel')

        # ensure Add and Accept behaviors: keep overlay open after adding
        try:
            # override methods from template by assigning bound methods
            self._on_add = self._on_add_override
            self._on_row_double_click = self._on_row_double_click_override
            self._on_accept = self._on_accept_override
            
            # Disable real-time search and use Enter instead
            if hasattr(self, 'search_entry'):
                try:
                    # Template binds KeyRelease in __init__
                    self.search_entry.unbind("<KeyRelease>")
                except Exception:
                    pass
                # Bind Enter key to search
                self.search_entry.bind("<Return>", lambda e: self._do_manual_search())
        except Exception:
            pass

    def _do_manual_search(self):
        """Ejecuta la búsqueda manualmente al pulsar Enter."""
        try:
            termino = self.search_var.get()
            logging.info(f"DevolucionesPanel: buscando '{termino}'")
            self._load_and_render(termino)
        except Exception:
            logging.exception("Error en búsqueda manual de DevolucionesPanel")

    def show(self) -> None:
        """Override show para asegurar el focus en el buscador."""
        super().show()
        try:
            # Forzar focus en el entry después de un pequeño delay
            self.after(200, lambda: self.search_entry.focus_set())
        except Exception:
            pass

    def _load_and_render(self, termino: str) -> None:
        """Cargar productos desde ProductoService y renderizar la página.

        Si `termino` está vacío, carga todos los productos ordenados por id.
        """
        try:
            if self.producto_service is None:
                self._items = []
            else:
                try:
                    self._items = self.producto_service.listar_productos(termino or '')
                except Exception:
                    logging.exception('Error listando productos en DevolucionesPanel')
                    self._items = []
            self._current_page = 0
            self._render_clients_page()
        except Exception:
            logging.exception('Error cargando datos en DevolucionesPanel')

    def _render_clients_page(self):
        """Renderizar los productos en el treeview con las columnas definidas."""
        try:
            for child in list(self.tree.get_children()):
                try:
                    self.tree.delete(child)
                except Exception:
                    pass

            start = self._current_page * self._page_size
            end = start + self._page_size
            page_items = (self._items or [])[start:end]
            for item in page_items:
                try:
                    pid = item.get('id')
                    nombre = item.get('nombre') or ''
                    categoria = item.get('categoria') or item.get('categoria_nombre') or ''
                    tipo = item.get('tipo') or item.get('tipo_nombre') or ''
                    stock = item.get('stock_actual') if item.get('stock_actual') is not None else item.get('stock', '')
                    values = (pid, nombre, categoria, tipo, stock)
                    self.tree.insert('', 'end', iid=str(pid), values=values)
                except Exception:
                    logging.exception('Error insertando producto en pagina DevolucionesPanel')

            total_pages = max(1, (len(self._items or []) + self._page_size - 1) // self._page_size)
            try:
                self.page_label.configure(text=f"Página {self._current_page+1} / {total_pages}")
                self.prev_btn.configure(state=('normal' if self._current_page>0 else 'disabled'))
                self.next_btn.configure(state=('normal' if self._current_page < total_pages-1 else 'disabled'))
            except Exception:
                pass
        except Exception:
            logging.exception('Error renderizando página en DevolucionesPanel')

    # --- Overrides for selection/add behavior: do not hide on accept, add negative lines ---
    def _get_selected_product(self):
        try:
            sel = self.tree.selection()
            if not sel:
                return None
            iid = sel[0]
            # try to find in current items cache
            for it in (self._items or []):
                try:
                    if str(it.get('id')) == str(iid):
                        return it
                except Exception:
                    continue
            # fallback: try to load from DB using producto id
            try:
                pid = int(iid)
                if getattr(self, 'producto_service', None) is not None and getattr(self.producto_service, 'db', None) is not None:
                    q = """
                    SELECT p.id, p.nombre, p.stock_actual, c.nombre AS categoria_nombre, t.nombre AS tipo_nombre, COALESCE(pr.pvp,0.0) AS pvp, COALESCE(p.tipo_iva,21) AS tipo_iva
                    FROM productos p
                    LEFT JOIN categorias c ON p.categoria = c.id
                    LEFT JOIN tipos t ON p.tipo = t.id
                    LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
                    WHERE p.id = ?
                    """
                    row = self.producto_service.db.fetch_one(q, (pid,))
                    if row:
                        return {
                            'id': row[0],
                            'nombre': row[1],
                            'stock_actual': row[2],
                            'categoria': row[3],
                            'tipo': row[4],
                            'pvp': str(row[5]) if row[5] is not None else '0.00',
                            'tipo_iva': int(row[6] or 21)
                        }
            except Exception:
                pass
            return None
        except Exception:
            return None

    def _add_selected_to_devolucion(self):
        try:
            prod = self._get_selected_product()
            if not prod:
                return False
            # ensure devoluciones_service is available
            if not hasattr(self, 'devoluciones_service') or self.devoluciones_service is None:
                logging.error('No hay DevolucionesService asociado al panel')
                return False
            added = self.devoluciones_service.add_devolucion_item(prod, cantidad=1)
            # refresh UI lists and carrito display
            try:
                self._load_and_render(self.search_var.get() if hasattr(self, 'search_var') else '')
            except Exception:
                pass
            try:
                top = self.overlay.winfo_toplevel()
                if getattr(top, 'carrito_ui', None) is not None:
                    top.carrito_ui.update_display()
                elif getattr(self, 'view', None) is not None and getattr(self.view, 'carrito_ui', None) is not None:
                    self.view.carrito_ui.update_display()
            except Exception:
                pass
            return bool(added)
        except Exception:
            logging.exception('Error añadiendo producto como devolución')
            return False

    def _on_row_double_click_override(self, event=None):
        try:
            self._add_selected_to_devolucion()
        except Exception:
            logging.exception('Error en double click DevolucionesPanel')

    def _on_add_override(self):
        try:
            self.search_entry.focus_set()
        except Exception:
            pass

    def _on_accept_override(self, event=None):
        try:
            # Add selected product but DO NOT hide the overlay
            self._add_selected_to_devolucion()
        except Exception:
            logging.exception('Error en aceptar DevolucionesPanel')


class DevolucionAction:
    """Acción que abre el panel de devoluciones."""

    def __init__(self, view: Any, db: Database, carrito_service: Any):
        self.view = view
        self.db = db
        self.carrito_service = carrito_service
        self._panel: Optional[DevolucionesPanel] = None

    def ejecutar(self) -> None:
        try:
            # Comprobar permiso del cajero logueado
            from kool_tpv.modulos.tpv.actions.permisos import check_permiso
            parent = None
            try:
                parent = self.view.winfo_toplevel()
            except Exception:
                parent = self.view
            if not check_permiso(self.carrito_service, 'permiso_devolucion', parent):
                return

            if self._panel is None:
                self._panel = DevolucionesPanel(self.view, self.db, on_selection_callback=self._on_producto_selected)
                # attach devoluciones service to panel and start devolucion mode
                try:
                    self._panel.devoluciones_service = DevolucionesService(self.db, self.carrito_service)
                    # start when opening
                    self._panel.devoluciones_service.start_devolucion()
                    # override hide to ensure end_devolucion is called when panel closed
                    try:
                        original_hide = self._panel.hide
                        def _hide_and_end():
                            try:
                                self._panel.devoluciones_service.end_devolucion()
                            except Exception:
                                logging.exception('Error finalizando devolucion al cerrar panel')
                            try:
                                original_hide()
                            except Exception:
                                logging.exception('Error ocultando panel tras end_devolucion')
                        self._panel.hide = _hide_and_end
                    except Exception:
                        pass
                except Exception:
                    logging.exception('Error inicializando DevolucionesService para panel')
            else:
                self._panel.on_selection_callback = self._on_producto_selected

            try:
                self._panel.show()
            except Exception:
                logging.exception('DevolucionAction: fallo mostrando panel de devoluciones')
        except Exception:
            logging.exception('DevolucionAction: error al ejecutar acción')

    def _on_producto_selected(self, producto: Dict[str, Any]) -> None:
        # Callback when a product is chosen from the overlay. For devoluciones
        # typically we would add a negative quantity line to the carrito.
        try:
            try:
                # Ensure carrito_service supports add_item-like API
                # Prefer using devoluciones_service so stock and movimientos se registren
                try:
                    if hasattr(self, '_panel') and getattr(self._panel, 'devoluciones_service', None) is not None:
                        self._panel.devoluciones_service.add_devolucion_item(producto, cantidad=1)
                    elif self.carrito_service is not None and hasattr(self.carrito_service, 'add_item'):
                        prod = producto.copy()
                        prod['cantidad'] = 1
                        prod['line_tipo'] = 'devolucion'
                        try:
                            self.carrito_service.add_item(prod)
                        except Exception:
                            logging.exception('DevolucionAction: error añadiendo producto al carrito')
                except Exception:
                    logging.exception('DevolucionAction: error procesando devolucion via service')
                else:
                    logging.debug('DevolucionAction: carrito_service no disponible o no soporta add_item')
            except Exception:
                logging.exception('DevolucionAction: error procesando producto seleccionado')
        except Exception:
            logging.exception('DevolucionAction: fallo en callback on_producto_selected')
