"""Plantilla reutilizable para overlays de selección (proveedores, promociones, etc.).

Esta plantilla provee una interfaz visual y la lógica básica de paginación
y selección; debe clonarse y adaptarse para cada entidad concreta.

Variables a modificar al clonar:
- `self.title_text`: texto del encabezado del panel.
- `self.columns_config`: lista de columnas para el `Treeview`.
- Instanciar `self.data_service` en el constructor (marcado con placeholder).

Regla: No añadir lógica de acceso a bases de datos aquí; la plantilla solo
expone puntos de integración para que el módulo concreto llene `self._items`
usando su propio servicio.
"""
from __future__ import annotations
from typing import Optional, Callable, List, Dict, Any
import logging
import math

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from datetime import datetime, timedelta

# [INSTANCIAR AQUÍ EL SERVICIO CORRESPONDIENTE]
# from mi_modulo.mi_servicio import MiServicio


class SelectionOverlayTemplate:
    """Plantilla de overlay que reproduce el posicionamiento y comportamiento
    del panel original (close button, posicionamiento, pagination), pero sin
    acoplarla a la entidad 'cliente'.

    Args:
        view_or_action_panel: TpvView o action_panel.
        db: objeto de base de datos o contexto (opcional) — instanciar servicio en el lugar indicado.
        on_item_selected: callback opcional que recibirá el diccionario del elemento seleccionado.
    """

    def __init__(self, view_or_action_panel: object, db: object = None, on_selection_callback: Optional[Callable[[Dict[str, Any]], None]] = None, ui_config: Optional[dict] = None):
        self._visible = False

        # Título personalizable del panel (respetar valor proporcionado por subclases)
        if not hasattr(self, 'title_text') or not getattr(self, 'title_text'):
            self.title_text = "TITULO PANEL"

        # UI configurable defaults
        cfg = {
            'top_height': 130,
            'top_left': 280,
            'reserved_right': 420,
            'min_overlay_w': 360,
            'categories_height': None,
            'articles_height': None,
            'btn_width': 180,
            'category_btn_height': 48,
            'article_btn_height': 56,
            'btn_font': ("Roboto", 18, "bold"),
            'page_size': 12,
            'min_page_size': 25,
            'default_filter_days': 30,
            'pagination_height': 48,
        }
        if isinstance(ui_config, dict):
            cfg.update(ui_config)

        # Standardized colors and fonts (single place to change)
        self.BG_COLOR = "#393E46"
        self.PANEL_BG = "#333333"
        self.LIST_BG = "#FFFFFF"
        self.ACCEPT_BTN_COLOR = "#00A4DF"
        self.ADD_BTN_COLOR = "#555555"
        self.HEADER_FONT_SIZE = 34
        self.HEADER_FONT_WEIGHT = "bold"
        # choose font family: prefer Roboto, fallback to Arial
        try:
            available = list(tkfont.families())
            self.FONT_FAMILY = "Roboto" if "Roboto" in available else ("Segoe UI" if "Segoe UI" in available else "Arial")
        except Exception:
            self.FONT_FAMILY = "Arial"

        # Example columns configuration (key, heading, width, anchor)
        # Customize this list in the instance to match the entity being selected.
        # Ejemplo comentado:
        # self.columns_config = [
        #     ("id", "ID", 60, "center"),
        #     ("name", "Nombre", 300, "w"),
        #     ("phone", "Teléfono", 140, "center"),
        # ]
        self.columns_config = [
            ("id", "ID", 60, "center"),
            ("name", "Nombre", 300, "w"),
        ]

        # expose as attributes
        self.top_height = int(cfg['top_height'])
        self.top_left = int(cfg['top_left'])
        self.reserved_right = int(cfg['reserved_right'])
        self.min_overlay_w = int(cfg['min_overlay_w'])
        self.categories_height = cfg['categories_height']
        self.articles_height = cfg['articles_height']
        self.btn_width = int(cfg['btn_width'])
        self.category_btn_height = int(cfg['category_btn_height'])
        self.article_btn_height = int(cfg['article_btn_height'])
        self.btn_font = tuple(cfg['btn_font'])
        self._page_size = int(cfg['page_size'])
        # Minimum page size to avoid very small pages on some resolutions
        self._min_page_size = int(cfg.get('min_page_size', 25))
        # Default quick date filter (days)
        self._filter_days = int(cfg.get('default_filter_days', 30))
        self._filter_from = None
        self._filter_to = None
        self.pagination_height = int(cfg['pagination_height'])

        # Detect whether we received the view or the panel
        if hasattr(view_or_action_panel, "action_panel"):
            self.view = view_or_action_panel
            self.action_panel = getattr(self.view, "action_panel", None)
        else:
            self.view = None
            self.action_panel = view_or_action_panel

        # Determine root
        try:
            if self.action_panel is not None:
                self.root = self.action_panel.winfo_toplevel()
            elif self.view is not None and getattr(self.view, "parent", None) is not None:
                self.root = self.view.parent.winfo_toplevel()
            else:
                self.root = None
        except Exception:
            self.root = None

        # Placeholder for the concrete service instance
        # [INSTANCIAR AQUÍ EL SERVICIO CORRESPONDIENTE]
        # Example: self.data_service = MiServicio(db)
        self.data_service = None

        # Create overlay on the root (or action_panel if root missing)
        parent_for_overlay = self.root if self.root is not None else self.action_panel
        try:
            self.overlay = ctk.CTkFrame(parent_for_overlay, fg_color="#393E46")

            # create global close button (same import pattern as BuscarArticuloPanel)
            from kool_tpv.utils.global_buttons import create_global_close_button

            self.close_btn = create_global_close_button(self.overlay, command=self.hide)
            # Registrar el handler de este overlay en el root (si la app expone la API)
            try:
                app_root = self.root
                if app_root is not None and hasattr(app_root, 'register_power_handler'):
                    try:
                        app_root.register_power_handler(self.hide, owner=self)
                        logging.info('SelectionOverlayTemplate: power handler registrado en root')
                        # Configurar el botón para delegar siempre al dispatcher central
                        try:
                            if hasattr(app_root, '_dispatch_power') and self.close_btn is not None:
                                self.close_btn.configure(command=app_root._dispatch_power)
                        except Exception:
                            pass
                    except Exception:
                        logging.exception('SelectionOverlayTemplate: error registrando power handler en root')
            except Exception:
                logging.exception('SelectionOverlayTemplate: error comprobando registro power handler')
            # Desregistrar handler al destruir el overlay
            try:
                def _on_destroy(event=None):
                    try:
                        app = self.root
                        if app is not None and hasattr(app, 'unregister_power_handler'):
                            try:
                                app.unregister_power_handler(owner=self)
                                logging.info('SelectionOverlayTemplate: power handler desregistrado en destroy')
                            except Exception:
                                logging.exception('SelectionOverlayTemplate: error desregistrando power handler')
                    except Exception:
                        pass

                try:
                    if getattr(self, 'overlay', None) is not None:
                        self.overlay.bind('<Destroy>', _on_destroy)
                except Exception:
                    pass
            except Exception:
                logging.exception('SelectionOverlayTemplate: error vinculando Destroy para desregistro')
        except Exception:
            logging.exception("Error inicializando SelectionOverlayTemplate overlay")

        # selection callback (rename to a generic name)
        self.on_selection_callback: Optional[Callable[[Dict[str, Any]], None]] = on_selection_callback

        # Build UI: top (title + search), central (treeview), bottom (pagination + buttons)
        try:
            # TOP BUTTONS area replaced by label + entry
            self.top_buttons = ctk.CTkFrame(self.overlay, fg_color="transparent", height=self.top_height)
            self.top_buttons.pack(side="top", fill="x", pady=(8, 0), padx=(self.top_left, 12))
            self.top_buttons.pack_propagate(False)

            # Header: large title and horizontal control row (search + accept + add)
            header_font = ("Roboto", 34, "bold")
            self.header_label = ctk.CTkLabel(self.top_buttons, text=self.title_text, font=header_font)
            self.header_label.pack(side="top", anchor="w", padx=(0, 12), pady=(6, 0))

            # Search controls: entry and action buttons aligned in a single row
            self.search_var = tk.StringVar()
            self.search_controls_frame = ctk.CTkFrame(self.top_buttons, fg_color="transparent")
            # place under the header label, aligned to the left to match title padding
            self.search_controls_frame.pack(side="top", anchor="w", pady=(8, 0))

            self.search_entry = ctk.CTkEntry(self.search_controls_frame, textvariable=self.search_var, width=400)
            self.search_entry.pack(side="left", padx=(0, 10))
            self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_change(e))

            # Header actions container (allows adding more buttons easily)
            self.header_actions_frame = ctk.CTkFrame(self.search_controls_frame, fg_color="transparent")
            self.header_actions_frame.pack(side="left")

            # Action buttons placed immediately to the right of the search entry
            self.aceptar_btn = ctk.CTkButton(self.header_actions_frame, text="Aceptar", fg_color=self.ACCEPT_BTN_COLOR, command=self._on_accept, width=140)
            self.anadir_btn = ctk.CTkButton(self.header_actions_frame, text="Añadir", fg_color=self.ADD_BTN_COLOR, command=self._on_add, width=140)
            self.aceptar_btn.pack(side="left", padx=5)
            self.anadir_btn.pack(side="left", padx=5)

            # ARTICLES area -> items tree
            self.articles_container = ctk.CTkFrame(self.overlay, fg_color="#333333")
            if self.articles_height is not None:
                try:
                    h2 = int(self.articles_height)
                    self.articles_container.pack(side="bottom", fill="x", expand=False, padx=12, pady=(0, 12))
                    self.articles_container.configure(height=h2)
                    self.articles_container.pack_propagate(False)
                except Exception:
                    self.articles_container.pack(side="bottom", fill="both", expand=True, padx=12, pady=(0, 12))
            else:
                self.articles_container.pack(side="bottom", fill="both", expand=True, padx=12, pady=(0, 12))

            # place treeview for items inside articles_container
            self.articles_grid = ctk.CTkFrame(self.articles_container, fg_color="transparent")
            self.articles_grid.pack(side="top", fill="both", expand=True)

            # footer frame (flexible container for pagination and other controls)
            self.footer_frame = ctk.CTkFrame(self.articles_container, height=self.pagination_height, fg_color="transparent")
            self.footer_frame.pack(side="bottom", fill="x", padx=12, pady=(6, 6))
            self.prev_btn = ctk.CTkButton(self.footer_frame, text="Anterior", command=self.prev_page, width=100)
            self.next_btn = ctk.CTkButton(self.footer_frame, text="Siguiente", command=self.next_page, width=100)
            self.page_label = ctk.CTkLabel(self.footer_frame, text="", width=120)
            self.prev_btn.pack(side="left", padx=6, pady=6)
            self.page_label.pack(side="left", padx=6)
            self.next_btn.pack(side="left", padx=6, pady=6)

            # Quick date filters (placed at right side of footer)
            try:
                self.filters_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
                self.filters_frame.pack(side="right")
                # Quick filter buttons: 7 / 30 / 90 days
                self.filter_7_btn = ctk.CTkButton(self.filters_frame, text="7d", width=48, command=lambda: self._set_quick_filter(7))
                self.filter_30_btn = ctk.CTkButton(self.filters_frame, text="30d", width=48, command=lambda: self._set_quick_filter(30))
                self.filter_90_btn = ctk.CTkButton(self.filters_frame, text="90d", width=48, command=lambda: self._set_quick_filter(90))
                self.filter_label = ctk.CTkLabel(self.filters_frame, text=f"Últimos {self._filter_days} días")
                self.filter_7_btn.pack(side="left", padx=4)
                self.filter_30_btn.pack(side="left", padx=4)
                self.filter_90_btn.pack(side="left", padx=4)
                self.filter_label.pack(side="left", padx=(8, 0))
                # date range entries for template (display in DD/MM/YY)
                try:
                    self.from_var = tk.StringVar(value="")
                    self.to_var = tk.StringVar(value="")
                    self.from_entry = ctk.CTkEntry(self.filters_frame, textvariable=self.from_var, width=110)
                    self.to_entry = ctk.CTkEntry(self.filters_frame, textvariable=self.to_var, width=110)
                    self.apply_date_btn = ctk.CTkButton(self.filters_frame, text="Aplicar", width=80, command=self._apply_date_filter)
                    # pack to the right of filter_label
                    self.from_entry.pack(side="left", padx=4)
                    self.to_entry.pack(side="left", padx=4)
                    self.apply_date_btn.pack(side="left", padx=6)
                except Exception:
                    pass
            except Exception:
                pass

            # internal state
            self._active_view = None
            self._items: List[Dict[str, Any]] = []
            self._current_page = 0
            self._page_size = int(cfg['page_size'])

            # build treeview
            tree_container = tk.Frame(self.articles_grid)
            tree_container.pack(fill="both", expand=True, padx=12, pady=8)
            # Build treeview based on self.columns_config for modularity
            cols = [c[0] for c in self.columns_config]
            self.tree = ttk.Treeview(tree_container, columns=cols, show="headings")
            for key, heading, width, anchor in self.columns_config:
                try:
                    self.tree.heading(key, text=heading)
                    self.tree.column(key, width=width, anchor=anchor)
                except Exception:
                    # skip misconfigured columns defensively
                    logging.exception('Error configurando columna de Treeview: %s', key)

            vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
            hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            self.tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            tree_container.grid_rowconfigure(0, weight=1)
            tree_container.grid_columnconfigure(0, weight=1)

            # bindings
            self.tree.bind("<Double-1>", lambda e: self._on_row_double_click(e))
            self.tree.bind("<Return>", lambda e: self._on_accept(e))
            self.tree.bind("<KP_Enter>", lambda e: self._on_accept(e))
            self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_tree_select(e))

            # overlay resize binding
            try:
                self.overlay.bind('<Configure>', lambda e: self._on_overlay_configure(e))
            except Exception:
                pass
            
            # Helper to apply column configuration from concrete implementations
            def _aplicar_config_columnas_impl(columns_config):
                try:
                    if not hasattr(self, 'tree') or self.tree is None:
                        return
                    # Guarda config actual
                    self.columns_config = columns_config

                    cols = [c[0] for c in columns_config]
                    try:
                        self.tree.configure(columns=cols)
                    except Exception:
                        pass

                    for key, heading, width, anchor in columns_config:
                        try:
                            self.tree.heading(key, text=heading)
                            self.tree.column(key, width=width, anchor=anchor)
                        except Exception:
                            logging.exception('Error configurando columna %s en SelectionOverlayTemplate', key)
                except Exception:
                    logging.exception('Error aplicando config de columnas en SelectionOverlayTemplate')

            # expose as method on the instance for backward compatibility
            try:
                setattr(self, '_aplicar_config_columnas', _aplicar_config_columnas_impl)
            except Exception:
                pass
        except Exception:
            logging.exception('Error creando SelectionOverlayTemplate interna')

    def show(self) -> None:
        """Mostrar overlay. Copia comportamiento de posicionamiento del overlay original."""
        try:
            self._visible = True
            try:
                if self.root is None:
                    self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                else:
                    try:
                        self.root.update_idletasks()
                    except Exception:
                        pass

                    right_container = None
                    try:
                        if getattr(self, 'view', None) is not None:
                            right_container = getattr(self.view, 'right_container', None)
                    except Exception:
                        right_container = None
                    if right_container is None:
                        right_container = getattr(self.root, 'right_container', None)

                    try:
                        if right_container is not None:
                            rc_w = max(0, right_container.winfo_width())
                            root_w = max(1, self.root.winfo_width())
                            RESERVED = getattr(self, 'reserved_right', 420)
                            MIN_OVERLAY_W = getattr(self, 'min_overlay_w', 360)
                            overlay_w = max(MIN_OVERLAY_W, root_w - RESERVED)
                            if overlay_w <= 0 or overlay_w >= root_w:
                                left_fraction = max(0.2, (root_w - rc_w) / root_w)
                                self.overlay.place(x=0, y=0, relwidth=left_fraction, relheight=1)
                            else:
                                try:
                                    self.overlay.place(x=0, y=0, width=overlay_w, relheight=1)
                                except Exception:
                                    left_fraction = max(0.2, (root_w - rc_w) / root_w)
                                    self.overlay.place(x=0, y=0, relwidth=left_fraction, relheight=1)
                        else:
                            self.overlay.place(x=0, y=0, relwidth=0.7, relheight=1)
                    except Exception:
                        try:
                            self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
                        except Exception:
                            pass
            except Exception:
                logging.exception("Error colocando overlay SelectionOverlayTemplate")
            self.overlay.lift()
            # Ensure global floating power stays on top
            try:
                app = getattr(self, 'root', None)
                if app is not None and hasattr(app, 'power_floating'):
                    try:
                        app.power_floating.lift()
                    except Exception:
                        pass
            except Exception:
                pass
            # Ensure layout metrics are computed now that the overlay is visible
            try:
                self._on_overlay_configure()
            except Exception:
                logging.exception('Error configurando overlay tras lift in SelectionOverlayTemplate')
            # Load initial data and render the first page
            try:
                # [IMPLEMENTAR AQUI: llamar al servicio para cargar datos iniciales]
                self._load_and_render("")
            except Exception:
                logging.exception('Error cargando iniciales en SelectionOverlayTemplate')

            # Position close button mirroring BuscarArticuloPanel logic
            try:
                if getattr(self, 'close_btn', None) is not None:
                    app_root = self.root
                    nav = getattr(app_root, 'nav_frame', None)
                    try:
                        if app_root is not None:
                            app_root.update_idletasks()
                    except Exception:
                        pass
                    try:
                        self.overlay.update_idletasks()
                    except Exception:
                        pass

                    if nav is not None:
                        ov_x = self.overlay.winfo_rootx()
                        ov_y = self.overlay.winfo_rooty()
                        try:
                            pb = getattr(app_root, 'power_button', None)
                            if pb is not None:
                                pb_rootx = pb.winfo_rootx()
                                pb_rooty = pb.winfo_rooty()
                                rel_x = pb_rootx - ov_x
                                rel_y = pb_rooty - ov_y
                            else:
                                nav_x = nav.winfo_rootx()
                                nav_y = nav.winfo_rooty()
                                rel_x = 12 + (nav_x - ov_x)
                                rel_y = 12 + (nav_y - ov_y)
                        except Exception:
                            nav_x = nav.winfo_rootx()
                            nav_y = nav.winfo_rooty()
                            rel_x = 12 + (nav_x - ov_x)
                            rel_y = 12 + (nav_y - ov_y)
                        try:
                            self.close_btn.place(x=rel_x, y=rel_y)
                            self.close_btn.lift()
                        except Exception:
                            try:
                                self.close_btn.place(x=12, y=12)
                            except Exception:
                                pass
                    else:
                        try:
                            self.close_btn.place(x=12, y=12)
                        except Exception:
                            pass
                    # Ensure the handler remains registered while overlay is visible
                    try:
                        app_root = self.root
                        if app_root is not None and hasattr(app_root, 'register_power_handler'):
                            try:
                                app_root.register_power_handler(self.hide, owner=self)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            # focus search entry
            try:
                self.search_entry.focus_set()
            except Exception:
                pass

            logging.info("SelectionOverlayTemplate: mostrado (overlay parent=%s, visible=%s)", getattr(self.overlay, 'master', None), self._visible)
        except Exception:
            logging.exception("Error mostrando SelectionOverlayTemplate")

    def hide(self) -> None:
        try:
            self.overlay.place_forget()
            self._visible = False
        except Exception:
            logging.exception("Error ocultando SelectionOverlayTemplate")

        if callable(self.on_selection_callback):
            # no-op here; external caller may use on_close
            pass

    # --- pagination and rendering helpers ---
    def _compute_columns(self) -> int:
        try:
            frame = getattr(self, 'articles_grid', None)
            w = max(200, frame.winfo_width() if frame is not None else 400)
            bw = getattr(self, 'btn_width', 180)
            padding = 12
            cols = max(1, w // (bw + padding))
            return cols
        except Exception:
            return 3

    def _render_clients_page(self):
        try:
            # clear tree
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
                    # For a generic template, avoid calling any entity-specific service.
                    # Use item fields directly (customize in concrete implementation).
                    self.tree.insert('', 'end', iid=str(item.get('id')), values=(item.get('id'), item.get('nombre') if isinstance(item, dict) else str(item), item.get('telefono') if isinstance(item, dict) else ''))
                except Exception:
                    pass
            total_pages = max(1, math.ceil(len(self._items or []) / self._page_size))
            try:
                self.page_label.configure(text=f"Página {self._current_page+1} / {total_pages}")
                self.prev_btn.configure(state=('normal' if self._current_page>0 else 'disabled'))
                self.next_btn.configure(state=('normal' if self._current_page < total_pages-1 else 'disabled'))
            except Exception:
                pass
        except Exception:
            logging.exception('Error renderizando página en SelectionOverlayTemplate')

    def prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_clients_page()

    def next_page(self):
        total_pages = max(1, math.ceil(len(self._items or []) / self._page_size))
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self._render_clients_page()

    def _on_overlay_configure(self, event=None):
        try:
            # adjust page_size based on container size
            try:
                approx_btn_w = max(1, getattr(self, 'btn_width', 180))
                cols = max(1, max(1, self.articles_grid.winfo_width()) // (approx_btn_w + 12))
                h = max(200, self.articles_grid.winfo_height())
                btn_h = getattr(self, 'article_btn_height', 56)
                vpadding = 12
                # compute dynamic page size but enforce a sensible minimum
                rows = max(1, h // (btn_h + vpadding))
                self._page_size = max(1, cols * rows)
                try:
                    self._page_size = max(self._page_size, int(getattr(self, '_min_page_size', 25)))
                except Exception:
                    pass
            except Exception:
                pass
            if self._items:
                self._render_clients_page()
        except Exception:
            pass

    # --- search / selection logic ---
    def _on_search_change(self, event: Optional[tk.Event] = None) -> None:
        try:
            if getattr(self, '_search_after_id', None):
                try:
                    self.overlay.after_cancel(self._search_after_id)
                except Exception:
                    pass
            self._search_after_id = self.overlay.after(250, lambda: self._load_and_render(self.search_var.get()))
        except Exception:
            logging.exception('Error en on_search_change SelectionOverlayTemplate')

    def _load_and_render(self, termino: str) -> None:
        try:
            # Concrete implementations should call their own service here and
            # populate `self._clients_items` (or override this method).
            # Ejemplo:
            # if self.data_service is not None:
            #     self._items = self.data_service.search(termino)
            # else:
            self._items = []
            self._current_page = 0
            self._render_clients_page()
        except Exception:
            logging.exception('Error cargando datos en SelectionOverlayTemplate')

    def _set_quick_filter(self, days: int) -> None:
        try:
            self._filter_days = int(days)
            now = datetime.now()
            self._filter_to = now
            self._filter_from = now - timedelta(days=self._filter_days)
            try:
                if hasattr(self, 'filter_label') and self.filter_label is not None:
                    self.filter_label.configure(text=f"Últimos {self._filter_days} días")
                # update entries display in DD/MM/YY if present
                try:
                    if getattr(self, 'from_var', None) is not None:
                        self.from_var.set(self._filter_from.strftime('%d/%m/%y'))
                    if getattr(self, 'to_var', None) is not None:
                        self.to_var.set(self._filter_to.strftime('%d/%m/%y'))
                except Exception:
                    pass
            except Exception:
                pass
            # reload data using current search term
            try:
                self._current_page = 0
                self._load_and_render(self.search_var.get())
            except Exception:
                pass
        except Exception:
            logging.exception('Error aplicando filtro rápido')

    def _apply_date_filter(self) -> None:
        try:
            ftext = (getattr(self, 'from_var', tk.StringVar(value='')) or '').strip()
            ttext = (getattr(self, 'to_var', tk.StringVar(value='')) or '').strip()
            f_from = None
            f_to = None
            # try parsing DD/MM/YY then YYYY-MM-DD then ISO
            def _parse(s: str):
                if not s:
                    return None
                s1 = s.split('.')[0]
                for fmt in ('%d/%m/%y', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(s1, fmt)
                    except Exception:
                        continue
                try:
                    return datetime.fromisoformat(s1)
                except Exception:
                    return None

            try:
                f_from = _parse(ftext)
                f_to = _parse(ttext)
            except Exception:
                f_from = None
                f_to = None

            self._filter_from = f_from
            self._filter_to = f_to
            # reload
            try:
                self._current_page = 0
                self._load_and_render(self.search_var.get())
            except Exception:
                pass
        except Exception:
            logging.exception('Error aplicando filtro de fecha en template')

    def _on_row_double_click(self, event: Optional[tk.Event] = None) -> None:
        try:
            self._confirm_selection()
        except Exception:
            logging.exception('Error en doble click SelectionOverlayTemplate')

    def _on_tree_select(self, event: Optional[tk.Event] = None) -> None:
        try:
            sel = self.tree.selection()
            if sel:
                try:
                    self._current_selection = int(sel[0])
                except Exception:
                    self._current_selection = None
            else:
                self._current_selection = None
        except Exception:
            logging.exception('Error seleccionando fila en SelectionOverlayTemplate')

    def _on_accept(self, event: Optional[tk.Event] = None) -> None:
        try:
            self._confirm_selection()
        except Exception:
            logging.exception('Error on accept SelectionOverlayTemplate')

    def _confirm_selection(self) -> None:
        try:
            sel = self.tree.selection()
            if not sel:
                return
            iid = sel[0]
            vals = self.tree.item(iid, 'values')
            item = {
                'id': int(vals[0]) if vals and vals[0] else None,
                'nombre': vals[1] if vals and len(vals) > 1 else '',
            }
            # try enrich from internal cache
            try:
                for c in (self._items or []):
                    if str(c.get('id')) == str(iid):
                        item.update(c)
                        break
            except Exception:
                pass

            if callable(self.on_selection_callback):
                try:
                    self.on_selection_callback(item)
                except Exception:
                    logging.exception('Error llamando callback on_selection_callback')
            # hide overlay
            try:
                self.hide()
            except Exception:
                pass
        except Exception:
            logging.exception('Error confirmando selección SelectionOverlayTemplate')

    def _on_add(self) -> None:
        try:
            self.search_entry.focus_set()
        except Exception:
            logging.exception('Error placeholder add SelectionOverlayTemplate')
