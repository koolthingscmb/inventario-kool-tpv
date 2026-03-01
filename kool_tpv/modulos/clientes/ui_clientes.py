"""Overlay UI para gestión de clientes.

Esta implementación sigue la arquitectura y el comportamiento del
`BuscarArticuloPanel` (posicionamiento, close button y lógica de overlay),
pero reemplaza los controles anteriores por un buscador y
un `Treeview` de clientes.
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

from kool_tpv.modulos.clientes.cliente_service import ClienteService


class UIClientes:
    """Overlay que reproduce el comportamiento de `BuscarArticuloPanel`.

    Args:
        view_or_action_panel: TpvView o action_panel.
        db: instancia de base de datos (se pasa a ClienteService).
        on_cliente_selected: callback opcional que recibirá el diccionario del cliente.
    """

    def __init__(self, view_or_action_panel: object, db: object, on_cliente_selected: Optional[Callable[[Dict[str, Any]], None]] = None, ui_config: Optional[dict] = None):
        self.on_cliente_selected = on_cliente_selected
        self._visible = False

        # module name for colors/fonts
        self.module_name = 'clientes'
        try:
            from kool_tpv.utils.config_loader import load_colors
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {}

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

        # Columns configuration: (key, heading, width, anchor)
        self.columns_config = [
            ("id", "ID", 60, "center"),
            ("nombre", "Nombre", 300, "w"),
            ("fecha_alta", "Fecha Alta", 120, "center"),
            ("telefono", "Teléfono", 140, "center"),
            ("nivel", "Nivel", 100, "center"),
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

        # Cliente service
        try:
            self.cliente_service = ClienteService(db)
        except Exception:
            self.cliente_service = None

        # Create overlay on the root (or action_panel if root missing)
        parent_for_overlay = self.root if self.root is not None else self.action_panel
        try:
            self.overlay = ctk.CTkFrame(parent_for_overlay, fg_color=self.colors.get('background', "#393E46"))

            # create global close button (same import pattern as BuscarArticuloPanel)
            from kool_tpv.utils.global_buttons import create_global_close_button

            self.close_btn = create_global_close_button(self.overlay, command=self.hide)
        except Exception:
            logging.exception("Error inicializando UIClientes overlay")

        # selection callback
        self.on_cliente_selected_internal: Optional[Callable[[Dict[str, Any]], None]] = on_cliente_selected

        # Build UI: top (title + search), central (treeview), bottom (pagination + buttons)
        try:
            # TOP BUTTONS area replaced by label + entry
            self.top_buttons = ctk.CTkFrame(self.overlay, fg_color="transparent", height=self.top_height)
            self.top_buttons.pack(side="top", fill="x", pady=(8, 0), padx=(self.top_left, 12))
            self.top_buttons.pack_propagate(False)

            # Header: large title and horizontal control row (search + accept + add)
            from kool_tpv.utils.font_loader import get_font
            self.header_label = ctk.CTkLabel(self.top_buttons, text="CLIENTE", font=get_font('title', module=self.module_name))
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

            # ARTICLES area -> clients tree
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

            # place treeview for clients inside articles_container
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

            # Date range filter controls in footer (quick buttons + desde / hasta)
            try:
                self.date_filters_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
                self.date_filters_frame.pack(side="right")

                # Quick filter buttons: 7 / 30 / 90 days
                try:
                    self.quick_7_btn = ctk.CTkButton(self.date_filters_frame, text="7d", width=48, command=lambda: self._set_quick_date(7))
                    self.quick_30_btn = ctk.CTkButton(self.date_filters_frame, text="30d", width=48, command=lambda: self._set_quick_date(30))
                    self.quick_90_btn = ctk.CTkButton(self.date_filters_frame, text="90d", width=48, command=lambda: self._set_quick_date(90))
                    self.quick_7_btn.pack(side="left", padx=4)
                    self.quick_30_btn.pack(side="left", padx=4)
                    self.quick_90_btn.pack(side="left", padx=4)
                except Exception:
                    pass

                # Label + Entries for date range (YYYY-MM-DD)
                try:
                    lbl_from = ctk.CTkLabel(self.date_filters_frame, text="Desde:")
                    lbl_to = ctk.CTkLabel(self.date_filters_frame, text="Hasta:")
                    lbl_from.pack(side="left", padx=(8, 2))
                except Exception:
                    lbl_from = None
                    lbl_to = None

                self.from_var = tk.StringVar(value="")
                self.to_var = tk.StringVar(value="")
                self.from_entry = ctk.CTkEntry(self.date_filters_frame, textvariable=self.from_var, width=110)
                if lbl_to:
                    try:
                        lbl_to.pack(side="left", padx=(8, 2))
                    except Exception:
                        pass
                self.to_entry = ctk.CTkEntry(self.date_filters_frame, textvariable=self.to_var, width=110)
                self.apply_date_btn = ctk.CTkButton(self.date_filters_frame, text="Aplicar", width=80, command=self._apply_date_filter)

                self.from_entry.pack(side="left", padx=4)
                self.to_entry.pack(side="left", padx=4)
                self.apply_date_btn.pack(side="left", padx=6)
            except Exception:
                pass

            # internal state
            self._active_view = None
            self._clients_items: List[Dict[str, Any]] = []
            self._current_page = 0
            # force default page size to 25 for clients overlay
            self._page_size = 25
            # date filter range values (None == no filter)
            self._filter_from = None
            self._filter_to = None

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

            # Note: action buttons were moved to the header for faster workflow.

            # overlay resize binding
            try:
                self.overlay.bind('<Configure>', lambda e: self._on_overlay_configure(e))
            except Exception:
                pass
        except Exception:
            logging.exception('Error creando UIClientes interna')

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
                logging.exception("Error colocando overlay UIClientes")
            self.overlay.lift()
            # Ensure layout metrics are computed now that the overlay is visible
            try:
                self._on_overlay_configure()
            except Exception:
                logging.exception('Error configurando overlay tras lift in UIClientes')
            # Initialize default date filter (últimos 30 días) and load initial data
            try:
                now = datetime.now()
                default_days = 30
                f_from = (now - timedelta(days=default_days)).strftime('%d/%m/%y')
                f_to = now.strftime('%d/%m/%y')
                try:
                    # populate UI entries if present
                    if getattr(self, 'from_var', None) is not None:
                        self.from_var.set(f_from)
                    if getattr(self, 'to_var', None) is not None:
                        self.to_var.set(f_to)
                except Exception:
                    pass
                # set internal filter values (store as datetimes)
                try:
                    self._filter_from = datetime.strptime(f_from, '%d/%m/%y')
                    self._filter_to = datetime.strptime(f_to, '%d/%m/%y')
                except Exception:
                    try:
                        self._filter_from = datetime.strptime(f_from, '%Y-%m-%d')
                        self._filter_to = datetime.strptime(f_to, '%Y-%m-%d')
                    except Exception:
                        self._filter_from = None
                        self._filter_to = None

                # Load initial page using current search term
                self._load_and_render("")
            except Exception:
                logging.exception('Error cargando clientes iniciales en UIClientes')

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
            except Exception:
                pass

            # focus search entry
            try:
                self.search_entry.focus_set()
            except Exception:
                pass

            logging.info("UIClientes: mostrado (overlay parent=%s, visible=%s)", getattr(self.overlay, 'master', None), self._visible)
        except Exception:
            logging.exception("Error mostrando UIClientes")

    def hide(self) -> None:
        try:
            self.overlay.place_forget()
            self._visible = False
        except Exception:
            logging.exception("Error ocultando UIClientes")

        if callable(self.on_cliente_selected_internal):
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
            page_items = (self._clients_items or [])[start:end]
            for item in page_items:
                try:
                    nivel = item.get('id_nivel')
                    nivel_label = self.cliente_service.formatear_nivel(nivel) if self.cliente_service else ''
                    # format fecha_alta if present
                    fecha_val = ''
                    try:
                        fa = item.get('fecha_alta') if isinstance(item, dict) else None
                        if fa:
                                if isinstance(fa, str):
                                    try:
                                        from datetime import datetime as _dt
                                        # try common formats
                                        try:
                                            fecha_val = _dt.strptime(fa.split('.')[0], '%d/%m/%y').strftime('%d/%m/%y')
                                        except Exception:
                                            try:
                                                fecha_val = _dt.strptime(fa.split('.')[0], '%Y-%m-%d').strftime('%d/%m/%y')
                                            except Exception:
                                                try:
                                                    fecha_val = _dt.fromisoformat(fa).strftime('%d/%m/%y')
                                                except Exception:
                                                    fecha_val = str(fa)
                                    except Exception:
                                        fecha_val = str(fa)
                                elif hasattr(fa, 'strftime'):
                                    try:
                                        fecha_val = fa.strftime('%d/%m/%y')
                                    except Exception:
                                        fecha_val = str(fa)
                                else:
                                    fecha_val = str(fa)
                    except Exception:
                        fecha_val = ''

                    self.tree.insert('', 'end', iid=str(item.get('id')), values=(item.get('id'), item.get('nombre'), fecha_val, item.get('telefono'), nivel_label))
                except Exception:
                    pass
            total_pages = max(1, math.ceil(len(self._clients_items or []) / self._page_size))
            try:
                self.page_label.configure(text=f"Página {self._current_page+1} / {total_pages}")
                self.prev_btn.configure(state=('normal' if self._current_page>0 else 'disabled'))
                self.next_btn.configure(state=('normal' if self._current_page < total_pages-1 else 'disabled'))
            except Exception:
                pass
        except Exception:
            logging.exception('Error renderizando página de clientes')

    def prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_clients_page()

    def next_page(self):
        total_pages = max(1, math.ceil(len(self._clients_items or []) / self._page_size))
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
                rows = max(1, h // (btn_h + vpadding))
                self._page_size = max(1, cols * rows)
            except Exception:
                pass
            if self._clients_items:
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
            logging.exception('Error en on_search_change UIClientes')

    def _load_and_render(self, termino: str) -> None:
        try:
            if self.cliente_service is None:
                self._clients_items = []
            else:
                # retrieve clients from service
                items = self.cliente_service.buscar_clientes(termino)

                # if a date filter range is set, try to filter locally by common date fields
                if getattr(self, '_filter_from', None) or getattr(self, '_filter_to', None):
                    f_from = getattr(self, '_filter_from', None)
                    f_to = getattr(self, '_filter_to', None)

                    def parse_date(v):
                        if v is None:
                            return None
                        if isinstance(v, datetime):
                            return v
                        s = str(v).split('.')[0]
                        # Try common display formats: DD/MM/YY, YYYY-MM-DD, ISO
                        for fmt in ('%d/%m/%y', '%Y-%m-%d'):
                            try:
                                return datetime.strptime(s, fmt)
                            except Exception:
                                continue
                        try:
                            return datetime.fromisoformat(s)
                        except Exception:
                            return None

                    filtered = []
                    for it in items:
                        # try common date keys
                        date_val = None
                        for k in ('fidelizado_at', 'created_at', 'fecha_alta', 'fecha'):
                            if isinstance(it, dict) and k in it and it.get(k):
                                date_val = parse_date(it.get(k))
                                break
                        if date_val is None:
                            # keep item if we cannot determine date
                            filtered.append(it)
                            continue
                        ok = True
                        if f_from and date_val < f_from:
                            ok = False
                        if f_to and date_val > f_to:
                            ok = False
                        if ok:
                            filtered.append(it)
                    self._clients_items = filtered
                else:
                    # no date filter: present clients as returned
                    self._clients_items = items
            self._current_page = 0
            self._render_clients_page()
        except Exception:
            logging.exception('Error cargando clientes en UIClientes')

    def _on_row_double_click(self, event: Optional[tk.Event] = None) -> None:
        try:
            self._confirm_selection()
        except Exception:
            logging.exception('Error en doble click UIClientes')

    def _apply_date_filter(self) -> None:
        """Apply date range from footer entries and reload the list."""
        try:
            ftext = (self.from_var.get() or '').strip()
            ttext = (self.to_var.get() or '').strip()
            f_from = None
            f_to = None
            try:
                if ftext:
                    f_from = datetime.strptime(ftext.split('.')[0], '%Y-%m-%d')
                if ttext:
                    f_to = datetime.strptime(ttext.split('.')[0], '%Y-%m-%d')
            except Exception:
                # ignore parse errors
                f_from = None
                f_to = None
            self._filter_from = f_from
            self._filter_to = f_to
            # reload with current search term
            self._current_page = 0
            self._load_and_render(self.search_var.get())
        except Exception:
            logging.exception('Error aplicando filtro de fecha UIClientes')

    def _set_quick_date(self, days: int) -> None:
        try:
            now = datetime.now()
            f_from = (now - timedelta(days=int(days))).strftime('%Y-%m-%d')
            f_to = now.strftime('%Y-%m-%d')
            if getattr(self, 'from_var', None) is not None:
                try:
                    self.from_var.set(f_from)
                except Exception:
                    pass
            if getattr(self, 'to_var', None) is not None:
                try:
                    self.to_var.set(f_to)
                except Exception:
                    pass
            try:
                self._filter_from = datetime.strptime(f_from, '%Y-%m-%d')
                self._filter_to = datetime.strptime(f_to, '%Y-%m-%d')
            except Exception:
                self._filter_from = None
                self._filter_to = None
            # reload
            self._current_page = 0
            self._load_and_render(self.search_var.get())
        except Exception:
            logging.exception('Error aplicando quick date filter')

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
            logging.exception('Error seleccionando fila en UIClientes')

    def _on_accept(self, event: Optional[tk.Event] = None) -> None:
        try:
            self._confirm_selection()
        except Exception:
            logging.exception('Error on accept UIClientes')

    def _confirm_selection(self) -> None:
        try:
            sel = self.tree.selection()
            if not sel:
                return
            iid = sel[0]
            vals = self.tree.item(iid, 'values')
            cliente = {
                'id': int(vals[0]) if vals and vals[0] else None,
                'nombre': vals[1] if vals and len(vals) > 1 else '',
                'telefono': vals[2] if vals and len(vals) > 2 else '',
                'id_nivel': None,
                'tesoro_total': None,
            }
            # try enrich id_nivel from internal cache
            try:
                for c in (self._clients_items or []):
                    if str(c.get('id')) == str(iid):
                        cliente['id_nivel'] = c.get('id_nivel')
                        # Ensure tesoro_total travels to the cart even if not shown in the Treeview
                        cliente['tesoro_total'] = c.get('tesoro_total')
                        break
            except Exception:
                pass

            if callable(self.on_cliente_selected_internal):
                try:
                    self.on_cliente_selected_internal(cliente)
                except Exception:
                    logging.exception('Error llamando callback on_cliente_selected')
            # hide overlay
            try:
                self.hide()
            except Exception:
                pass
        except Exception:
            logging.exception('Error confirmando selección UIClientes')

    def _on_add(self) -> None:
        try:
            self.search_entry.focus_set()
        except Exception:
            logging.exception('Error placeholder add cliente UI')
