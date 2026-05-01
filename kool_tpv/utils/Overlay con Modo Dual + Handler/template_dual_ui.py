"""UI con modo dual - PLANTILLA REUTILIZABLE

Copia este archivo y busca/reemplaza:

    MiUI → NombreDeTuUI
    MiHandler → NombreDeTuHandler
    modo1/modo2 → nombres descriptivos de tus modos
"""

import logging
from typing import Optional
import math
import customtkinter as ctk

from .mi_base_ui import MiBaseUI  # ← Cambiar por tu BaseUI
from .mi_handler import MiHandler  # ← Cambiar por tu Handler


class MiUI(MiBaseUI):
    """Overlay con modo dual (modo1/modo2)."""

    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        ui_cfg = {'page_size': 25}
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        self.db = db

        # SISTEMA DE MODOS
        self.modo = 'modo1'  # 'modo1' o 'modo2'
        self._saved_page_size = None

        # HANDLER para modo2
        try:
            self._mi_handler = MiHandler(self)
        except Exception:
            self._mi_handler = None
            logging.exception('Error instanciando MiHandler')

        # TÍTULO
        self.title_text = "MODO 1"
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # COLUMNAS MODO 1
        self.columns_config_modo1 = [
            ("col1", "Columna 1", 100, "center"),
            ("col2", "Columna 2", 180, "center"),
            ("col3", "Columna 3", 120, "e"),
        ]

        # COLUMNAS MODO 2
        self.columns_config_modo2 = [
            ("col_a", "Columna A", 100, "center"),
            ("col_b", "Columna B", 180, "center"),
            ("col_c", "Columna C", 120, "e"),
        ]

        # Aplicar config inicial
        self.columns_config = self.columns_config_modo1
        try:
            self._aplicar_config_columnas(self.columns_config)
        except Exception:
            logging.exception('Error aplicando columnas')

        # Ocultar búsqueda si no la necesitas
        try:
            if hasattr(self, 'search_entry'):
                self.search_entry.pack_forget()
            if hasattr(self, 'search_controls_frame'):
                self.search_controls_frame.pack_forget()
        except Exception:
            pass

        # Botones del header
        self._add_header_controls()

        # Cargar datos iniciales
        self._items = []
        self._load_and_render('')

    def _add_header_controls(self):
        """Crear botones específicos de cada modo."""
        try:
            container = getattr(self, 'top_buttons', None) or getattr(self, 'overlay', None)
            self._header_buttons_row = ctk.CTkFrame(container, fg_color='transparent')
            self._header_buttons_row.pack(side='top', fill='x', pady=(6, 4))

            # BOTONES MODO 1
            self.btn_accion1 = ctk.CTkButton(
                self._header_buttons_row,
                text="Acción 1",
                width=140,
                command=self._on_accion1
            )
            self.btn_cambiar_modo2 = ctk.CTkButton(
                self._header_buttons_row,
                text="Ver Modo 2",
                width=140,
                command=self._on_cambiar_modo2
            )

            # BOTÓN MODO 2 (inicialmente oculto)
            self.btn_imprimir = ctk.CTkButton(
                self._header_buttons_row,
                text="IMPRIMIR",
                width=140,
                fg_color='#FFFFFF',
                text_color='#000000',
                command=self._on_imprimir
            )

            # Pack solo los de modo1
            self.btn_accion1.pack(side="left", padx=5)
            self.btn_cambiar_modo2.pack(side="left", padx=5)
            # btn_imprimir NO se hace pack aquí

        except Exception:
            logging.exception('Error añadiendo header controls')

    def _load_and_render(self, termino: str = ''):
        """Cargar datos según modo actual."""
        try:
            if self.modo == 'modo1':
                # TODO: Cargar datos modo1
                self._items = []  # ← Reemplazar con tu lógica
            elif self.modo == 'modo2':
                if self._mi_handler is not None:
                    self._items = self._mi_handler.load_modo2(termino)
                else:
                    self._items = []

            self._current_page = 0
            self._render_clients_page()

        except Exception:
            logging.exception('Error en _load_and_render')

    def _render_clients_page(self):
        """Renderizar página según modo."""
        try:
            # Limpiar tree
            for child in list(self.tree.get_children()):
                try:
                    self.tree.delete(child)
                except Exception:
                    pass

            # Paginación
            start = getattr(self, '_current_page', 0) * getattr(self, '_page_size', 25)
            end = start + getattr(self, '_page_size', 25)
            page_items = (self._items or [])[start:end]

            # Renderizar según modo
            if self.modo == 'modo1':
                self._render_modo1(page_items)
            elif self.modo == 'modo2':
                if self._mi_handler:
                    self._mi_handler.render_modo2(page_items)

            # Actualizar controles paginación
            total_pages = max(1, math.ceil(len(self._items or []) / getattr(self, '_page_size', 25)))
            if hasattr(self, 'page_label'):
                self.page_label.configure(text=f"Página {getattr(self, '_current_page', 0) + 1} / {total_pages}")

        except Exception:
            logging.exception('Error renderizando página')

    def _render_modo1(self, items):
        """Renderizar items del modo1."""
        for item in items:
            try:
                self.tree.insert(
                    '',
                    'end',
                    iid=str(item.get('id')),
                    values=(
                        item.get('col1'),
                        item.get('col2'),
                        item.get('col3')
                    )
                )
            except Exception:
                logging.exception('Error insertando item')

    def _cambiar_modo(self, nuevo_modo: str):
        """CLAVE: Cambiar entre modos."""
        try:
            self.modo = nuevo_modo

            if self.modo == 'modo1':
                self._configurar_modo1()
            elif self.modo == 'modo2':
                if self._mi_handler is not None:
                    self._mi_handler.configurar_modo2()

            # Recargar datos
            self._load_and_render('')

        except Exception:
            logging.exception('Error cambiando modo')

    def _configurar_modo1(self):
        """Configurar UI para modo1."""
        try:
            # Título
            self.title_text = "MODO 1"
            if hasattr(self, 'header_label'):
                self.header_label.configure(text=self.title_text)

            # Columnas
            self._aplicar_config_columnas(self.columns_config_modo1)

            # Mostrar botones modo1
            if hasattr(self, 'btn_accion1'):
                self.btn_accion1.pack(side="left", padx=5)
            if hasattr(self, 'btn_cambiar_modo2'):
                self.btn_cambiar_modo2.pack(side="left", padx=5)

            # Ocultar botones modo2
            if hasattr(self, 'btn_imprimir'):
                self.btn_imprimir.pack_forget()

            # Destruir VisorNegro
            if getattr(self, '_visor_negro', None):
                try:
                    self._visor_negro.destroy()
                except Exception:
                    pass
                self._visor_negro = None

        except Exception:
            logging.exception('Error configurando modo1')

    def _aplicar_config_columnas(self, columns_config):
        """Aplicar configuración de columnas."""
        try:
            if not hasattr(self, 'tree') or self.tree is None:
                return

            self.columns_config = columns_config
            cols = [c[0] for c in columns_config]
            self.tree.configure(columns=cols)

            for key, heading, width, anchor in columns_config:
                self.tree.heading(key, text=heading)
                self.tree.column(key, width=width, anchor=anchor)
        except Exception:
            logging.exception('Error aplicando columnas')

    def _on_accion1(self):
        """Acción del modo1."""
        logging.info('Acción 1 ejecutada')

    def _on_cambiar_modo2(self):
        """Cambiar a modo2."""
        self._cambiar_modo('modo2')

    def _on_imprimir(self):
        """Delegar a handler."""
        if self._mi_handler:
            self._mi_handler.on_imprimir()

    def hide(self):
        """CLAVE: Override hide para detectar modo."""
        try:
            if getattr(self, 'modo', None) == 'modo2':
                # Volver a modo1 (NO cerrar)
                self._cambiar_modo('modo1')
            else:
                # Limpiar y cerrar
                if getattr(self, '_visor_negro', None):
                    try:
                        self._visor_negro.hide()
                    except Exception:
                        pass
                    try:
                        self._visor_negro.destroy()
                    except Exception:
                        pass
                    self._visor_negro = None

                super().hide()
        except Exception:
            logging.exception('Error en hide()')
            super().hide()
