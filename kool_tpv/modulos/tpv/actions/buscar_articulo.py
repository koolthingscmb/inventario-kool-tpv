"""Panel overlay para 'Buscar Artículo'.

El overlay cubre la zona izquierda de la aplicación: la barra de
navegación (power/print) y el `action_panel` del TPV. Para ello el
overlay se crea como hijo de la ventana raíz y su ancho se ajusta
dynamicamente para dejar libre el panel derecho (carrito).
"""
from __future__ import annotations
from typing import Optional, Union
import logging
import os
import math

import customtkinter as ctk
try:
    from PIL import Image
except Exception:
    Image = None

# Services DB
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService


class BuscarArticuloPanel:
    """Overlay que cubre la parte izquierda de la UI y muestra un botón "volver".

    El constructor acepta ya sea la `view` completa (TpvView) o el
    `action_panel`. Cuando se recibe la `view`, el overlay calcula su
    ancho como `root.width - right_container.width` y se posiciona en x=0.
    """

    def __init__(self, view_or_action_panel: Union[object, ctk.CTkFrame], on_close: Optional[callable] = None, ui_config: Optional[dict] = None):
        self.on_close = on_close
        self._visible = False

        # UI configurable defaults (puedes pasar `ui_config` para sobrescribir)
        cfg = {
            'top_height': 130,
            'top_left': 280,
            'reserved_right': 420,
            'min_overlay_w': 360,
            'categories_height': None,  # si None => expand=True (proporcional)
            'articles_height': None,    # si None => expand=True (proporcional)
            'btn_width': 180,
            'category_btn_height': 48,
            'article_btn_height': 56,
            'btn_font': ("Roboto", 18, "bold"),
            'page_size': 12,
            'pagination_height': 48,
        }
        if isinstance(ui_config, dict):
            cfg.update(ui_config)

        # expose as attributes para permitir modificaciones desde fuera
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

        # Detectar si nos pasaron la vista completa o sólo el action_panel
        if hasattr(view_or_action_panel, "action_panel"):
            self.view = view_or_action_panel
            self.action_panel = getattr(self.view, "action_panel", None)
        else:
            self.view = None
            self.action_panel = view_or_action_panel

        # Determinar ventana raíz donde colocar el overlay
        try:
            if self.action_panel is not None:
                self.root = self.action_panel.winfo_toplevel()
            elif self.view is not None and getattr(self.view, "parent", None) is not None:
                self.root = self.view.parent.winfo_toplevel()
            else:
                self.root = None
        except Exception:
            self.root = None

        # Inicializar services
        try:
            db = getattr(self.root, 'db', None)
            if db:
                self.producto_service = ProductoService(db)
                self.categoria_service = CategoriaService(db)
                self.tipo_service = TipoService(db)
            else:
                self.producto_service = None
                self.categoria_service = None 
                self.tipo_service = None
        except Exception:
            self.producto_service = None
            self.categoria_service = None
            self.tipo_service = None

        # Crear overlay en la raíz (si no hay raíz, usar action_panel)
        parent_for_overlay = self.root if self.root is not None else self.action_panel
        try:
            self.overlay = ctk.CTkFrame(parent_for_overlay, fg_color="#393E46")

            # Importar función global
            from kool_tpv.utils.global_buttons import create_global_close_button

            # Crear botón con función global (no colocarlo aquí)
            self.close_btn = create_global_close_button(self.overlay, command=self.hide)

            # No bind necesario: el botón se colocará en posición fija
        except Exception:
            logging.exception("Error inicializando BuscarArticuloPanel")

        # callback when an article is selected (external code may set this)
        self.on_article_selected = None

        # Área de controles: botones Categorías / Tipos y contenedor de resultados
        try:
            # ZONA SUPERIOR - Botones principales (altura fija)
            # ZONA SUPERIOR - Botones principales (altura fija, editable)
            self.top_buttons = ctk.CTkFrame(self.overlay, fg_color="transparent", height=self.top_height)
            self.top_buttons.pack(side="top", fill="x", pady=(8, 0), padx=(self.top_left, 12))
            self.top_buttons.pack_propagate(False)

            btn_font = ("Roboto", 30, "bold")
            # Sin expand para mantener altura fija y comportamiento conforme al diseño
            self.cat_btn = ctk.CTkButton(self.top_buttons,
                text="CATEGORÍAS",
                fg_color="#555555",
                hover_color="#00A4DF",
                command=self.show_categorias,
                font=btn_font,
                width=250,      # <-- ancho del botón superior (px)
                height=150       # <-- alto del botón superior (px)
            )
            self.tipos_btn = ctk.CTkButton(self.top_buttons,
                text="TIPOS",
                fg_color="#555555",
                hover_color="#00A4DF",
                command=self.show_tipos,
                font=btn_font,
                width=250,      # <-- ancho del botón superior (px)
                height=150       # <-- alto del botón superior (px)
            )
            self.cat_btn.pack(side="left", padx=(0, 6))
            self.tipos_btn.pack(side="left", padx=(6, 0))

            # ZONA CENTRAL - Categorías/Tipos (con scroll)
            # ZONA CENTRAL - Categorías/Tipos (con scroll). Si se especifica `categories_height`
            # se aplicará como altura fija y expand=False para que puedas controlar manualmente.
            self.categories_container = ctk.CTkFrame(self.overlay, fg_color="#444444")
            if self.categories_height is not None:
                try:
                    h = int(self.categories_height)
                    self.categories_container.pack(side="top", fill="x", expand=False, padx=12, pady=8)
                    self.categories_container.configure(height=h)
                    self.categories_container.pack_propagate(False)
                except Exception:
                    self.categories_container.pack(side="top", fill="both", expand=True, padx=12, pady=8)
            else:
                self.categories_container.pack(side="top", fill="both", expand=True, padx=12, pady=8)
            # Scrollable frame para la lista de categorías/tipos
            try:
                self.categories_scroll = ctk.CTkScrollableFrame(self.categories_container, fg_color="transparent")
                self.categories_scroll.pack(fill="both", expand=True)
            except Exception:
                # si CTkScrollableFrame no está disponible, usar frame simple
                self.categories_scroll = ctk.CTkFrame(self.categories_container, fg_color="transparent")
                self.categories_scroll.pack(fill="both", expand=True)
            self.categories_grid = ctk.CTkFrame(self.categories_scroll, fg_color="transparent")
            self.categories_grid.pack(fill="both", expand=True)

            # ZONA INFERIOR - Artículos (con paginación)
            # ZONA INFERIOR - Artículos (con paginación). Si se especifica `articles_height`
            # se aplicará como altura fija y expand=False.
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
            self.articles_grid = ctk.CTkFrame(self.articles_container, fg_color="transparent")
            self.articles_grid.pack(side="top", fill="both", expand=True)

            # Footer con paginación para artículos
            self.pagination_frame = ctk.CTkFrame(self.articles_container, height=48, fg_color="transparent")
            self.pagination_frame.pack(side="bottom", fill="x")
            self.prev_btn = ctk.CTkButton(self.pagination_frame, text="Anterior", command=self.prev_page, width=100)
            self.next_btn = ctk.CTkButton(self.pagination_frame, text="Siguiente", command=self.next_page, width=100)
            self.page_label = ctk.CTkLabel(self.pagination_frame, text="", width=120)
            self.prev_btn.pack(side="left", padx=6, pady=6)
            self.page_label.pack(side="left", padx=6)
            self.next_btn.pack(side="left", padx=6, pady=6)

            # State for grid/pagination
            self._active_view = None  # 'categorias' or 'tipos' (central)
            self._categories_items = []
            self._articles_items = []
            self._current_page = 0  # for articles
            self._page_size = 12

            # Selection tracking (store selected names)
            self._selected_category = None
            self._selected_tipo = None

            # Responsive: recalcular columnas al cambiar tamaño
            try:
                self.overlay.bind('<Configure>', lambda e: self._on_overlay_configure(e))
            except Exception:
                pass
        except Exception:
            logging.exception('Error creando UI interna BuscarArticuloPanel')

    # _reposition removed: use fixed placement for `close_btn` (place(x=12, y=12) in __init__)

    def show(self) -> None:
        try:
            # marcar visible antes de posicionar para que _reposition actúe
            self._visible = True
            # colocar el overlay para hacerlo visible (ocupando la zona del padre)
            try:
                if self.root is None:
                    # no hay root accesible: ocupar todo el padre
                    self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                else:
                    # Intentar reservar el ancho del `right_container` (visor/carrito)
                    try:
                        # Asegurar geometría establecida
                        self.root.update_idletasks()
                    except Exception:
                        pass

                    # Buscar contenedor derecho en la vista o en la raíz
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
                            # Reservar exactamente `self.reserved_right` px para el carrito (visor)
                            RESERVED = getattr(self, 'reserved_right', 380)
                            MIN_OVERLAY_W = getattr(self, 'min_overlay_w', 360)
                            overlay_w = max(MIN_OVERLAY_W, root_w - RESERVED)
                            # proteger contra tamaños inválidos
                            if overlay_w <= 0 or overlay_w >= root_w:
                                # fallback a fracción si algo raro sucede
                                left_fraction = max(0.2, (root_w - rc_w) / root_w)
                                self.overlay.place(x=0, y=0, relwidth=left_fraction, relheight=1)
                            else:
                                # colocar overlay en la parte izquierda con ancho fijo en píxeles
                                try:
                                    self.overlay.place(x=0, y=0, width=overlay_w, relheight=1)
                                except Exception:
                                    # si place con width falla, caer a relwidth
                                    left_fraction = max(0.2, (root_w - rc_w) / root_w)
                                    self.overlay.place(x=0, y=0, relwidth=left_fraction, relheight=1)
                        else:
                            # sin contenedor derecho conocido, reservar 70% como fallback
                            self.overlay.place(x=0, y=0, relwidth=0.7, relheight=1)
                    except Exception:
                        # último recurso: ocupar todo
                        try:
                            self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
                        except Exception:
                            pass
            except Exception:
                logging.exception("Error colocando overlay BuscarArticuloPanel")
            self.overlay.lift()
            # Colocar el botón una vez el overlay está visible y su geometría es estable
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
                        # Preferir coordenadas exactas del `power_button` si existe
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
            logging.info("BuscarArticuloPanel: mostrado (overlay parent=%s, visible=%s)", getattr(self.overlay, 'master', None), self._visible)
        except Exception:
            logging.exception("Error mostrando BuscarArticuloPanel")

    # Data loading helpers
    def _load_tipos_from_db(self):
        if self.tipo_service:
            return self.tipo_service.get_tipos_con_productos()
        return []

    def _load_articles_from_db(self, category_or_type, filter_type='category'):
        if not self.producto_service:
            return []
        
        if filter_type == 'category':
            return self.producto_service.get_productos_by_categoria(category_or_type)
        else:  # filter_type == 'tipo'
            return self.producto_service.get_productos_by_tipo(category_or_type)

    def _load_categorias_from_db(self):
        if self.categoria_service:
            return self.categoria_service.get_categorias_con_productos()
        return []

    # Grid / pagination helpers
    def _compute_columns(self):
        try:
            # Prefer a frame to compute columns for; default to categories_grid
            frame = getattr(self, 'grid_frame', None)
            if getattr(self, 'articles_grid', None) is not None:
                frame = self.articles_grid
            w = max(200, frame.winfo_width() if frame is not None else 400)
            # desired button width
            bw = 180
            padding = 12
            cols = max(1, w // (bw + padding))
            return cols
        except Exception:
            return 3

    def _render_page(self):
        # Backwards-compatible alias: rendering moved to _render_articles_page
        self._render_articles_page()

    def _render_categories(self):
        # clear categories grid
        for child in list(self.categories_grid.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        try:
            w = max(200, self.categories_grid.winfo_width())
            bw = getattr(self, 'btn_width', 180)
            padding = 12
            cols = max(1, w // (bw + padding))
        except Exception:
            cols = 3

        items = self._categories_items or []
        btn_font = getattr(self, 'btn_font', ("Roboto", 14, "bold"))
        r = 0
        c = 0
        for idx, item in enumerate(items):
            # visual selected state: if this item is selected, use selected colors
            is_selected = (self._active_view == 'categorias' and item == self._selected_category) or (self._active_view == 'tipos' and item == self._selected_tipo)
            fg = "#00A4DF" if is_selected else "#A5B1C4"
            tcolor = "white" if is_selected else "black"
            btn = ctk.CTkButton(self.categories_grid,
                text=str(item).upper(),
                fg_color=fg,
                hover_color="#00A4DF",
                text_color=tcolor,
                font=btn_font,
                height=getattr(self, 'category_btn_height', 48)
            )
            # connect to load articles depending on active view and set selection
            if self._active_view == 'categorias':
                btn.configure(command=(lambda name=item: (self._on_category_click(name), self.show_articles_by_category(name))))
            else:
                btn.configure(command=(lambda name=item: (self._on_tipo_click(name), self.show_articles_by_tipo(name))))
            btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            c += 1
            if c >= cols:
                c = 0
                r += 1

        for i in range(cols):
            try:
                self.categories_grid.grid_columnconfigure(i, weight=1)
            except Exception:
                pass

    def _render_articles_page(self):
        # clear articles grid
        for child in list(self.articles_grid.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        # (temporary debug removed)

        try:
            w = max(200, self.articles_grid.winfo_width())
            bw = getattr(self, 'btn_width', 180)
            padding = 12
            cols = max(1, w // (bw + padding))
        except Exception:
            cols = 3

        start = self._current_page * self._page_size
        end = start + self._page_size
        page_items = (self._articles_items or [])[start:end]

        btn_font = getattr(self, 'btn_font', ("Roboto", 14, "bold"))
        r = 0
        c = 0
        for idx, item in enumerate(page_items):
            # article buttons should display lowercase
            btn_text = (item.get('nombre') if isinstance(item, dict) and 'nombre' in item else str(item)).lower()
            btn = ctk.CTkButton(self.articles_grid, text=btn_text, fg_color="#444444", hover_color="#00A4DF", text_color="white", font=btn_font, height=getattr(self, 'article_btn_height', 56))
            # attach click handler to add item to carrito via callback (with debug prints)
            try:
                btn.configure(command=(lambda _item=item: self._on_article_click(_item)))
            except Exception:
                pass
            btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            c += 1
            if c >= cols:
                c = 0
                r += 1

        for i in range(cols):
            try:
                self.articles_grid.grid_columnconfigure(i, weight=1)
            except Exception:
                pass

        total_pages = max(1, math.ceil(len(self._articles_items or []) / self._page_size))
        try:
            self.page_label.configure(text=f"Página {self._current_page+1} / {total_pages}")
            self.prev_btn.configure(state=('normal' if self._current_page>0 else 'disabled'))
            self.next_btn.configure(state=('normal' if self._current_page < total_pages-1 else 'disabled'))
        except Exception:
            pass

    def _on_overlay_configure(self, event=None):
        # recompute page size based on available height and columns
        try:
            # Re-render categories and articles when overlay resizes
            try:
                self._render_categories()
            except Exception:
                pass

            # Recompute articles page size based on articles_grid
            try:
                # Use configured widths/heights to compute page size
                approx_btn_w = max(1, getattr(self, 'btn_width', 180))
                cols = max(1, max(1, self.articles_grid.winfo_width()) // (approx_btn_w + 12))
                h = max(200, self.articles_grid.winfo_height())
                btn_h = getattr(self, 'article_btn_height', 56)
                vpadding = 12
                rows = max(1, h // (btn_h + vpadding))
                self._page_size = max(1, cols * rows)
            except Exception:
                pass

            # re-render articles page if there's an active articles list
            if self._articles_items:
                self._render_articles_page()
            # also re-render categories to reflect potential selection style
            if self._categories_items:
                try:
                    self._render_categories()
                except Exception:
                    pass
        except Exception:
            pass

    def show_tipos(self):
        try:
            self._categories_items = self._load_tipos_from_db()
            self._active_view = 'tipos'
            # clear articles
            self._articles_items = []
            self._current_page = 0
            # mark top button selection
            try:
                self.cat_btn.configure(fg_color="#555555", text_color="black")
                self.tipos_btn.configure(fg_color="#00A4DF", text_color="white")
            except Exception:
                pass
            self._render_categories()
        except Exception:
            logging.exception('Error mostrando tipos')

    def show_categorias(self):
        try:
            self._categories_items = self._load_categorias_from_db()
            self._active_view = 'categorias'
            # clear articles
            self._articles_items = []
            self._current_page = 0
            # mark top button selection
            try:
                self.tipos_btn.configure(fg_color="#555555", text_color="black")
                self.cat_btn.configure(fg_color="#00A4DF", text_color="white")
            except Exception:
                pass
            self._render_categories()
        except Exception:
            logging.exception('Error mostrando categorias')

    def show_articles_by_category(self, categoria: str):
        try:
            # mark selected category
            try:
                self._selected_category = categoria
            except Exception:
                self._selected_category = None
            self._articles_items = self._load_articles_from_db(categoria, filter_type='category')
            self._current_page = 0
            self._render_articles_page()
        except Exception:
            logging.exception('Error mostrando artículos por categoría')

    def show_articles_by_tipo(self, tipo: str):
        try:
            # mark selected tipo
            try:
                self._selected_tipo = tipo
            except Exception:
                self._selected_tipo = None
            self._articles_items = self._load_articles_from_db(tipo, filter_type='tipo')
            self._current_page = 0
            self._render_articles_page()
        except Exception:
            logging.exception('Error mostrando artículos por tipo')

    def _on_article_click(self, item):
        """Callback interno al pulsar un artículo en la lista.

        Llama a `self.on_article_selected(item)` si está definido.
        """
        try:
            if callable(getattr(self, 'on_article_selected', None)):
                try:
                    self.on_article_selected(item)
                except Exception:
                    logging.exception('Error en on_article_selected callback')
        except Exception:
            logging.exception('Error handling article click')

    def prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_articles_page()

    def next_page(self):
        total_pages = max(1, math.ceil(len(self._articles_items or []) / self._page_size))
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self._render_articles_page()

    def hide(self) -> None:
        try:
            self.overlay.place_forget()
            self._visible = False
        except Exception:
            logging.exception("Error ocultando BuscarArticuloPanel")

        if callable(self.on_close):
            try:
                self.on_close()
            except Exception:
                logging.exception("Error on_close BuscarArticuloPanel")
        logging.info("BuscarArticuloPanel: ocultado")

    # Selection helpers
    def _on_category_click(self, name: str):
        try:
            self._selected_category = name
        except Exception:
            self._selected_category = None

    def _on_tipo_click(self, name: str):
        try:
            self._selected_tipo = name
        except Exception:
            self._selected_tipo = None

    def set_ui_config(self, **kwargs):
        """Actualizar configuraciones UI en tiempo de ejecución.

        Parámetros admitidos: top_height, top_left, reserved_right, min_overlay_w,
        categories_height, articles_height, btn_width, category_btn_height,
        article_btn_height, btn_font, page_size, pagination_height
        """
        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

            # aplicar cambios visibles inmediatamente
            try:
                if getattr(self, 'top_buttons', None) is not None:
                    self.top_buttons.configure(height=self.top_height)
                    self.top_buttons.pack_configure(padx=(self.top_left, 12))
            except Exception:
                pass

            try:
                # categories container
                if getattr(self, 'categories_container', None) is not None:
                    if self.categories_height is not None:
                        self.categories_container.configure(height=int(self.categories_height))
                        self.categories_container.pack_configure(fill='x', expand=False)
                    else:
                        self.categories_container.pack_configure(fill='both', expand=True)
            except Exception:
                pass

            try:
                if getattr(self, 'articles_container', None) is not None:
                    if self.articles_height is not None:
                        self.articles_container.configure(height=int(self.articles_height))
                        self.articles_container.pack_configure(fill='x', expand=False)
                    else:
                        self.articles_container.pack_configure(fill='both', expand=True)
            except Exception:
                pass

            # Re-render to apply new button sizes
            try:
                self._render_categories()
            except Exception:
                pass
            try:
                self._render_articles_page()
            except Exception:
                pass
        except Exception:
            logging.exception('Error aplicando set_ui_config')
