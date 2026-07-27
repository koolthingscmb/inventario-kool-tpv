"""CrearClienteUI: Interfaz para alta/edición de clientes (datos básicos)."""
from typing import Optional
import logging
import customtkinter as ctk
from pathlib import Path
try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency for image assets
    Image = None

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.utils.widgets.notificaciones import ToastWidget
try:
    from kool_tpv.modulos.clientes.cliente_service import ClienteService
except Exception:  # pragma: no cover - optional dependency during early UI dev
    ClienteService = None
from kool_tpv.utils.utils import (
    COLOR_BG_TERMINAL,
    COLOR_MATRIX,
)
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.dialogs import show_input_dialog, show_password_dialog
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.modulos.clientes.clientes_tickets import ClientesTicketsUI
from kool_tpv.utils.badge_loader import load_badge_image

logger = logging.getLogger(__name__)


class CrearClienteUI:
    """Ficha completa de cliente con tesoro y niveles (sección datos básicos)."""

    def __init__(self, parent, db: Optional[Database] = None, cliente_id: Optional[int] = None, module_name: str = 'clientes', on_save_callback: Optional[callable] = None):
        self.parent = parent
        self.db = db
        self.cliente_id = cliente_id
        self.module_name = module_name
        self.on_save_callback = on_save_callback
        # try to load module color palette; fall back to COLOR_MATRIX if loader fails
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {
                'text': COLOR_MATRIX,
                'primary': COLOR_MATRIX,
            }

        self.cliente_service = ClienteService(db) if db else None
        self.auth_service = AuthService(db) if db else None

        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # Header
        titulo_text = "> EDITAR_CLIENTE" if cliente_id else "> NUEVO_CLIENTE_SISTEMA"
        self.lbl_titulo = ctk.CTkLabel(
            self.container,
            text=titulo_text,
            font=get_font('title', module=self.module_name),
            text_color=self.colors.get('text', COLOR_MATRIX)
        )
        self.lbl_titulo.pack(anchor="w", padx=12, pady=(12, 8))

        # Main area con scroll
        self.main_scroll = ctk.CTkScrollableFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.main_scroll.pack(fill='both', expand=True, padx=12, pady=8)

        # Grid 8 columnas
        for c in [0, 2, 4, 6]:
            self.main_scroll.grid_columnconfigure(c, weight=0)
        for c in [1, 3, 5, 7]:
            self.main_scroll.grid_columnconfigure(c, weight=1)

        lbl_font = get_font('label', module=self.module_name)
        entry_kw = {
            "fg_color": self.colors.get('background', COLOR_BG_TERMINAL),
            "text_color": self.colors.get('text', COLOR_MATRIX),
            "border_width": 2,
            "border_color": self.colors.get('primary', COLOR_MATRIX),
            "corner_radius": 4
        }

        # === FILA 0: ID | NOMBRE | TESORO ACTIVADO ===
        ctk.CTkLabel(self.main_scroll, text="ID:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=0, sticky='w', padx=(12, 2), pady=4
        )
        self.e_id = ctk.CTkEntry(
            self.main_scroll,
            placeholder_text="ID (auto)",
            state='disabled',
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('text', "#666666"),
            border_color=self.colors.get('primary', COLOR_MATRIX)
        )
        self.e_id.grid(row=0, column=1, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="NOMBRE:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=2, sticky='w', padx=(12, 2), pady=4
        )
        self.e_nombre = ctk.CTkEntry(self.main_scroll, placeholder_text="Nombre completo", **entry_kw)
        self.e_nombre.grid(row=0, column=3, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="TESORO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=6, sticky='w', padx=(12, 2), pady=4
        )
        self.chk_tesoro = ctk.CTkCheckBox(
            self.main_scroll,
            text='Activado',
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            text_color=self.colors.get('text', COLOR_MATRIX)
        )
        self.chk_tesoro.grid(row=0, column=7, sticky='w', padx=(2, 12), pady=4)
        try:
            self.chk_tesoro.select()  # Por defecto ON
        except Exception:
            pass

        # === FILA 1: DNI | FECHA NACIMIENTO ===
        ctk.CTkLabel(self.main_scroll, text="DNI:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=1, column=0, sticky='w', padx=(12, 2), pady=4
        )
        self.e_dni = ctk.CTkEntry(self.main_scroll, placeholder_text="DNI/NIE", **entry_kw)
        self.e_dni.grid(row=1, column=1, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="F. NACIMIENTO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=1, column=4, sticky='w', padx=(12, 2), pady=4
        )
        self.e_fecha_nac = ctk.CTkEntry(self.main_scroll, placeholder_text="DD-MM-YYYY", **entry_kw)
        self.e_fecha_nac.grid(row=1, column=5, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        # === FILA 2: DIRECCIÓN | PAÍS ===
        ctk.CTkLabel(self.main_scroll, text="DIRECCIÓN:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=2, column=0, sticky='w', padx=(12, 2), pady=4
        )
        self.e_direccion = ctk.CTkEntry(self.main_scroll, placeholder_text="Calle, número...", **entry_kw)
        self.e_direccion.grid(row=2, column=1, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="PAÍS:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=2, column=4, sticky='w', padx=(12, 2), pady=4
        )
        self.e_pais = ctk.CTkEntry(self.main_scroll, placeholder_text="España", **entry_kw)
        self.e_pais.grid(row=2, column=5, columnspan=3, sticky='ew', padx=(2, 12), pady=4)
        try:
            self.e_pais.insert(0, 'España')  # Default
        except Exception:
            pass

        # === FILA 3: CIUDAD | CÓDIGO POSTAL ===
        ctk.CTkLabel(self.main_scroll, text="CIUDAD:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=3, column=0, sticky='w', padx=(12, 2), pady=4
        )
        self.e_ciudad = ctk.CTkEntry(self.main_scroll, placeholder_text="Ciudad", **entry_kw)
        self.e_ciudad.grid(row=3, column=1, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="C.P.:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=3, column=4, sticky='w', padx=(12, 2), pady=4
        )
        self.e_cp = ctk.CTkEntry(self.main_scroll, placeholder_text="Código Postal", **entry_kw)
        self.e_cp.grid(row=3, column=5, columnspan=3, sticky='ew', padx=(2, 12), pady=4)

        # === FILA 4: TELÉFONO | EMAIL | TAGS ===
        ctk.CTkLabel(self.main_scroll, text="TELÉFONO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=0, sticky='w', padx=(12, 2), pady=4
        )
        self.e_telefono = ctk.CTkEntry(self.main_scroll, placeholder_text="Teléfono", **entry_kw)
        self.e_telefono.grid(row=4, column=1, columnspan=2, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="EMAIL:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=3, sticky='w', padx=(12, 2), pady=4
        )
        self.e_email = ctk.CTkEntry(self.main_scroll, placeholder_text="email@ejemplo.com", **entry_kw)
        self.e_email.grid(row=4, column=4, columnspan=2, sticky='ew', padx=(2, 12), pady=4)

        ctk.CTkLabel(self.main_scroll, text="TAGS:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=6, sticky='w', padx=(12, 2), pady=4
        )
        self.e_tags = ctk.CTkEntry(self.main_scroll, placeholder_text="tag1, tag2", **entry_kw)
        self.e_tags.grid(row=4, column=7, sticky='ew', padx=(2, 12), pady=4)

        # === FILA 5: SEPARADOR VISUAL ===
        separador = ctk.CTkFrame(self.main_scroll, height=3, fg_color=self.colors.get('primary', COLOR_MATRIX))
        separador.grid(row=5, column=0, columnspan=8, sticky='ew', padx=6, pady=16)

        # === FILA 6: CONTENEDOR TESORO COMPLETO ===
        tesoro_container = ctk.CTkFrame(
            self.main_scroll,
            fg_color='#0d0d0d',
            corner_radius=12,
            border_width=3,
            border_color=self.colors.get('secondary', '#FFD700')
        )
        tesoro_container.grid(row=6, column=0, columnspan=8, sticky='ew', padx=6, pady=6)

        # === HEADER INLINE: ICONO + TESORO + LEVEL + NOMBRE + GRAFISMO ===
        header_frame = ctk.CTkFrame(tesoro_container, fg_color='transparent')
        header_frame.pack(fill='x', padx=20, pady=(20, 16))

        # Center content inside header_frame
        content_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
        content_frame.pack(anchor='center')

        # Icono dialog_tesoro.png (80x80)
        try:
            from pathlib import Path
            from PIL import Image

            # Buscar la carpeta root del paquete `kool_tpv` para localizar `assets` de forma robusta
            assets_base = None
            this_path = Path(__file__).resolve()
            for p in this_path.parents:
                if (p / '__init__.py').exists() and p.name == 'kool_tpv':
                    assets_base = p / 'assets'
                    break
            if assets_base is None:
                # Fallback al comportamiento anterior
                assets_base = this_path.parents[4] / 'assets'

            assets_dialogs = assets_base / 'dialogs'
            img_tesoro_path = assets_dialogs / 'dialog_tesoro.png'

            if img_tesoro_path.exists():
                img_tesoro = Image.open(img_tesoro_path).convert('RGBA')
                ctk_img_tesoro = ctk.CTkImage(img_tesoro, size=(80, 80))
                lbl_icon = ctk.CTkLabel(content_frame, image=ctk_img_tesoro, text='')
                lbl_icon.pack(side='left', padx=(0, 12))
                lbl_icon._img_ref = ctk_img_tesoro
            else:
                logger.error(f'dialog_tesoro.png NO encontrado: {img_tesoro_path}')
        except Exception:
            logger.exception('Error cargando dialog_tesoro.png')

        # Texto dinámico TESORO DE [nombre]
        self.lbl_titulo_tesoro = ctk.CTkLabel(
            content_frame,
            text='TESORO DE', # Se actualiza con nombre al cargar cliente
            font=('Courier New', 22, 'bold'),
            text_color=self.colors.get('accent', '#FFD700')
        )
        self.lbl_titulo_tesoro.pack(side='left', padx=(0, 30))

        # Level más grande
        ctk.CTkLabel(
            content_frame,
            text='Level:',
            font=('Courier New', 16, 'bold'),
            text_color=self.colors.get('light', '#9b59b6')
        ).pack(side='left', padx=(0, 6))

        self.lbl_level = ctk.CTkLabel(
            content_frame,
            text='1',
            font=('Courier New', 20, 'bold'),
            text_color=self.colors.get('light', '#9b59b6'),
            width=50
        )
        self.lbl_level.pack(side='left', padx=(0, 16))

        # Nombre nivel más grande
        self.lbl_nombre_nivel = ctk.CTkLabel(
            content_frame,
            text='Forastero',
            font=('Courier New', 20, 'bold'),
            text_color=self.colors.get('light', '#9b59b6')
        )
        self.lbl_nombre_nivel.pack(side='left', padx=(0, 16))

        # Grafismo más grande
        self.lbl_grafismo = ctk.CTkLabel(
            content_frame,
            text='~',
            font=('Courier New', 28, 'bold'),
            text_color=self.colors.get('light', '#00FFFF'),
            width=100
        )
        self.lbl_grafismo.pack(side='left')

        # === GRID 2x2: VALORES TESORO ===
        valores_frame = ctk.CTkFrame(tesoro_container, fg_color='transparent')
        valores_frame.pack(fill='x', padx=20, pady=(0, 20))

        valores_frame.grid_columnconfigure(0, weight=1)
        valores_frame.grid_columnconfigure(1, weight=1)

        # Localizar carpeta de iconos dentro de `kool_tpv/assets/iconos` de forma robusta
        from pathlib import Path
        this_path = Path(__file__).resolve()
        iconos_path = None
        for p in this_path.parents:
            if (p / '__init__.py').exists() and p.name == 'kool_tpv':
                iconos_path = p / 'assets' / 'iconos'
                break
        if iconos_path is None:
            iconos_path = this_path.parents[4] / 'assets' / 'iconos'

        # === FILA 0, COLUMNA 0: TESORO ACTUAL ===
        fila0_col0 = ctk.CTkFrame(valores_frame, fg_color='transparent')
        fila0_col0.grid(row=0, column=0, sticky='nsew', padx=(0, 20), pady=8)

        # group frame to center contents horizontally
        fila0_col0_group = ctk.CTkFrame(fila0_col0, fg_color='transparent')
        fila0_col0_group.pack(anchor='center')

        try:
            img_total_path = iconos_path / 'icono_tesoro_total.png'
            if img_total_path.exists():
                img_total = Image.open(img_total_path).convert('RGBA')
                ctk_img_total = ctk.CTkImage(img_total, size=(54, 54))
                icon_total = ctk.CTkLabel(fila0_col0_group, image=ctk_img_total, text='')
                icon_total.pack(side='left', padx=(0, 12))
                icon_total._img_ref = ctk_img_total
            else:
                logger.error(f'icono_tesoro_total.png NO encontrado: {img_total_path}')
        except Exception:
            logger.exception('Error cargando icono_tesoro_total.png')

        ctk.CTkLabel(
            fila0_col0_group,
            text='TESORO ACTUAL',
            font=('Courier New', 16, 'bold'),
            text_color=self.colors.get('primary', '#FFD700')
        ).pack(side='left', padx=(0, 12))

        self.e_tesoro_total = ctk.CTkEntry(
            fila0_col0_group,
            width=200,
            height=44,
            state='readonly',
            fg_color='#000000',
            text_color=self.colors.get('primary', '#FFD700'),
            border_color=self.colors.get('primary', '#FFD700'),
            border_width=3,
            font=('Courier New', 30, 'bold'),
            justify='center'
        )
        self.e_tesoro_total.pack(side='left')

        # === FILA 0, COLUMNA 1: TOTAL GANADO ===
        fila0_col1 = ctk.CTkFrame(valores_frame, fg_color='transparent')
        fila0_col1.grid(row=0, column=1, sticky='nsew', padx=(20, 0), pady=8)

        fila0_col1_group = ctk.CTkFrame(fila0_col1, fg_color='transparent')
        fila0_col1_group.pack(anchor='center')

        try:
            img_ganado_path = iconos_path / 'icono_tesoro_ganado_total.png'
            if img_ganado_path.exists():
                img_ganado = Image.open(img_ganado_path).convert('RGBA')
                ctk_img_ganado = ctk.CTkImage(img_ganado, size=(54, 54))
                icon_ganado = ctk.CTkLabel(fila0_col1_group, image=ctk_img_ganado, text='')
                icon_ganado.pack(side='left', padx=(0, 12))
                icon_ganado._img_ref = ctk_img_ganado
            else:
                logger.error(f'icono_tesoro_ganado_total.png NO encontrado: {img_ganado_path}')
        except Exception:
            logger.exception('Error cargando icono_tesoro_ganado_total.png')

        ctk.CTkLabel(
            fila0_col1_group,
            text='TOTAL GANADO',
            font=('Courier New', 16, 'bold'),
            text_color=self.colors.get('secondary', '#00FF00')
        ).pack(side='left', padx=(0, 12))

        self.e_tesoro_ganado = ctk.CTkEntry(
            fila0_col1_group,
            width=200,
            height=44,
            state='readonly',
            fg_color='#000000',
            text_color=self.colors.get('secondary', '#00FF00'),
            border_color=self.colors.get('secondary', '#00FF00'),
            border_width=3,
            font=('Courier New', 30, 'bold'),
            justify='center'
        )
        self.e_tesoro_ganado.pack(side='left')

        # === FILA 1, COLUMNA 0: TOTAL GASTADO ===
        fila1_col0 = ctk.CTkFrame(valores_frame, fg_color='transparent')
        fila1_col0.grid(row=1, column=0, sticky='nsew', padx=(0, 20), pady=8)

        fila1_col0_group = ctk.CTkFrame(fila1_col0, fg_color='transparent')
        fila1_col0_group.pack(anchor='center')

        try:
            img_gastado_path = iconos_path / 'icono_tesoro_gastado_total.png'
            if img_gastado_path.exists():
                img_gastado = Image.open(img_gastado_path).convert('RGBA')
                ctk_img_gastado = ctk.CTkImage(img_gastado, size=(54, 54))
                icon_gastado = ctk.CTkLabel(fila1_col0_group, image=ctk_img_gastado, text='')
                icon_gastado.pack(side='left', padx=(0, 12))
                icon_gastado._img_ref = ctk_img_gastado
            else:
                logger.error(f'icono_tesoro_gastado_total.png NO encontrado: {img_gastado_path}')
        except Exception:
            logger.exception('Error cargando icono_tesoro_gastado_total.png')

        ctk.CTkLabel(
            fila1_col0_group,
            text='TOTAL GASTADO',
            font=('Courier New', 16, 'bold'),
            text_color=self.colors.get('light', '#FF4444')
        ).pack(side='left', padx=(0, 12))

        self.e_tesoro_gastado = ctk.CTkEntry(
            fila1_col0_group,
            width=200,
            height=44,
            state='readonly',
            fg_color='#000000',
            text_color=self.colors.get('light', '#FF4444'),
            border_color=self.colors.get('light', '#FF4444'),
            border_width=3,
            font=('Courier New', 30, 'bold'),
            justify='center'
        )
        self.e_tesoro_gastado.pack(side='left')

        # === FILA 1, COLUMNA 1: VENCIMIENTO (SIN ICONO) ===
        fila1_col1 = ctk.CTkFrame(valores_frame, fg_color='transparent')
        fila1_col1.grid(row=1, column=1, sticky='nsew', padx=(20, 0), pady=8)

        fila1_col1_group = ctk.CTkFrame(fila1_col1, fg_color='transparent')
        fila1_col1_group.pack(anchor='center')

        ctk.CTkLabel(
            fila1_col1_group,
            text='VENCIMIENTO TESORO',
            font=('Courier New', 16, 'bold'),
            text_color=self.colors.get('accent', '#FFA500')
        ).pack(side='left', padx=(0, 12))

        self.e_fecha_venc = ctk.CTkEntry(
            fila1_col1_group,
            width=200,
            height=44,
            state='readonly',
            fg_color='#000000',
            text_color=self.colors.get('accent', '#FFA500'),
            border_color=self.colors.get('accent', '#FFA500'),
            border_width=3,
            font=('Courier New', 30, 'bold'),
            justify='center'
        )
        self.e_fecha_venc.pack(side='left')

        # (Fila 8 eliminado - nivel mostrado ahora en el header)

        # === FOOTER CON 4 BOTONES (DESDE CONFIG) ===
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)

        # Botones creados automáticamente desde buttons_actions_config.json
        self.btn_guardar = create_action_button(self.footer, 'guardar', self._on_guardar)
        self.btn_guardar.pack(side='left', padx=8)

        self.btn_sumar_puntos = create_action_button(self.footer, 'sumar_puntos', self._on_sumar_puntos)
        self.btn_sumar_puntos.pack(side='left', padx=8)

        self.btn_tickets = create_action_button(self.footer, 'tickets', self._on_tickets)
        self.btn_tickets.pack(side='left', padx=8)

        self.btn_pedido = create_action_button(self.footer, 'pedido', self._on_pedido)
        self.btn_pedido.pack(side='left', padx=8)

        self.btn_comunicacion = create_action_button(self.footer, 'comunicacion', self._on_comunicacion)
        self.btn_comunicacion.pack(side='left', padx=8)

        # Cargar datos si es edición
        if self.cliente_id:
            self._cargar_cliente()

        self._setup_tab_navigation()

        logger.info('CrearClienteUI inicializado completamente')
        
        # Dar foco al nombre automáticamente
        self.e_nombre.after(200, lambda: self.e_nombre.focus_set())

    def _setup_tab_navigation(self):
        """Configura navegación Tab/Shift+Tab entre los campos editables."""
        self._tab_order = [
            self.e_nombre,
            self.e_dni,
            self.e_fecha_nac,
            self.e_direccion,
            self.e_pais,
            self.e_ciudad,
            self.e_cp,
            self.e_telefono,
            self.e_email,
            self.e_tags,
            self.chk_tesoro,
            self.btn_guardar,
        ]

        self._widget_map = {}
        for w in self._tab_order:
            if hasattr(w, '_entry'):
                self._widget_map[str(w._entry)] = w
            elif hasattr(w, '_canvas'):
                self._widget_map[str(w._canvas)] = w
                if hasattr(w, '_text_label'):
                    self._widget_map[str(w._text_label)] = w
            else:
                self._widget_map[str(w)] = w

        def on_tab(event):
            current_tk = str(event.widget)
            current_obj = self._widget_map.get(current_tk)
            if current_obj not in self._tab_order:
                return None
            idx = self._tab_order.index(current_obj)
            if event.state & 0x1:
                next_idx = (idx - 1) % len(self._tab_order)
            else:
                next_idx = (idx + 1) % len(self._tab_order)
            next_obj = self._tab_order[next_idx]
            if hasattr(next_obj, '_entry'):
                next_obj.focus_set()
                try: next_obj._entry.selection_range(0, 'end')
                except: pass
            else:
                next_obj.focus_set()
            return 'break'

        for w in self._tab_order:
            if hasattr(w, '_entry'):
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

        import tkinter as _tk
        def disable_frame_focus(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkFrame, _tk.Frame)):
                    try: child.configure(takefocus=0)
                    except: pass
                    disable_frame_focus(child)
        disable_frame_focus(self.container)

    def get_widget(self):
        return self.container

    def _cargar_cliente(self):
        """Cargar datos del cliente desde BD y rellenar formulario completo."""
        try:
            if not self.cliente_service or not self.cliente_id:
                return

            # Obtener cliente completo con datos de nivel
            cliente = self.cliente_service.get_cliente(self.cliente_id)

            if not cliente:
                logger.error(f'Cliente {self.cliente_id} no encontrado')
                ToastWidget.show(self.container, 'CLIENTE NO ENCONTRADO EN BD', tipo='error')
                return

            # === RELLENAR DATOS BÁSICOS ===

            # ID (readonly)
            try:
                self.e_id.configure(state='normal')
                self.e_id.delete(0, 'end')
                self.e_id.insert(0, str(cliente['id']))
                self.e_id.configure(state='disabled')
            except Exception:
                pass

            # Nombre
            try:
                self.e_nombre.delete(0, 'end')
                self.e_nombre.insert(0, cliente.get('nombre', ''))
            except Exception:
                pass

            # DNI
            try:
                self.e_dni.delete(0, 'end')
                self.e_dni.insert(0, cliente.get('dni', ''))
            except Exception:
                pass

            # Fecha nacimiento (Convertir YYYY-MM-DD -> DD-MM-YYYY para visualización)
            try:
                self.e_fecha_nac.delete(0, 'end')
                fecha_db = cliente.get('fecha_nacimiento')
                if fecha_db and '-' in fecha_db:
                    partes = fecha_db.split('-')
                    if len(partes) == 3 and len(partes[0]) == 4: # Formato ISO
                        fecha_es = f"{partes[2]}-{partes[1]}-{partes[0]}"
                        self.e_fecha_nac.insert(0, fecha_es)
                    else:
                        self.e_fecha_nac.insert(0, fecha_db)
                elif fecha_db:
                    self.e_fecha_nac.insert(0, fecha_db)
            except Exception:
                pass

            # Dirección
            try:
                self.e_direccion.delete(0, 'end')
                self.e_direccion.insert(0, cliente.get('direccion', ''))
            except Exception:
                pass

            # País
            try:
                self.e_pais.delete(0, 'end')
                self.e_pais.insert(0, cliente.get('pais', ''))
            except Exception:
                pass

            # Ciudad
            try:
                self.e_ciudad.delete(0, 'end')
                self.e_ciudad.insert(0, cliente.get('ciudad', ''))
            except Exception:
                pass

            # CP
            try:
                self.e_cp.delete(0, 'end')
                self.e_cp.insert(0, cliente.get('cp', ''))
            except Exception:
                pass

            # Teléfono
            try:
                self.e_telefono.delete(0, 'end')
                self.e_telefono.insert(0, cliente.get('telefono', ''))
            except Exception:
                pass

            # Email
            try:
                self.e_email.delete(0, 'end')
                self.e_email.insert(0, cliente.get('email', ''))
            except Exception:
                pass

            # Tags
            try:
                self.e_tags.delete(0, 'end')
                self.e_tags.insert(0, cliente.get('tags', ''))
            except Exception:
                pass

            # Checkbox tesoro
            try:
                if cliente.get('fidelidad_activa'):
                    self.chk_tesoro.select()
                else:
                    try:
                        self.chk_tesoro.deselect()
                    except Exception:
                        pass
            except Exception:
                pass

            # === RELLENAR SECCIÓN TESORO ===

            # Header: "TESORO DE [nombre]"
            try:
                self.lbl_titulo_tesoro.configure(text=f"TESORO DE {cliente.get('nombre','')}")
            except Exception:
                pass

            # Tesoro actual
            try:
                self.e_tesoro_total.configure(state='normal')
                self.e_tesoro_total.delete(0, 'end')
                self.e_tesoro_total.insert(0, f"{cliente.get('tesoro_total',0.0):.2f}€")
                self.e_tesoro_total.configure(state='readonly')
            except Exception:
                pass

            # Tesoro ganado (histórico)
            try:
                self.e_tesoro_ganado.configure(state='normal')
                self.e_tesoro_ganado.delete(0, 'end')
                self.e_tesoro_ganado.insert(0, f"{cliente.get('tesoro_historico',0.0):.2f}€")
                self.e_tesoro_ganado.configure(state='readonly')
            except Exception:
                pass

            # Tesoro gastado
            try:
                self.e_tesoro_gastado.configure(state='normal')
                self.e_tesoro_gastado.delete(0, 'end')
                self.e_tesoro_gastado.insert(0, f"{cliente.get('tesoro_gastado_total',0.0):.2f}€")
                self.e_tesoro_gastado.configure(state='readonly')
            except Exception:
                pass

            # Fecha vencimiento
            try:
                self.e_fecha_venc.configure(state='normal')
                self.e_fecha_venc.delete(0, 'end')
                fecha_venc = cliente.get('fecha_vencimiento_tesoro') or 'Sin vencimiento'
                self.e_fecha_venc.insert(0, str(fecha_venc))
                self.e_fecha_venc.configure(state='readonly')
            except Exception:
                pass

            # === RELLENAR NIVEL ===
            try:
                self.lbl_level.configure(text=str(cliente.get('nivel_level', 1)))
            except Exception:
                pass

            try:
                self.lbl_nombre_nivel.configure(text=cliente.get('nivel_nombre', 'Forastero'))
            except Exception:
                pass

            try:
                # self.lbl_grafismo.configure(text=cliente.get('nivel_grafismo', '~'))
                # Reemplazar texto por imagen usando badge_loader
                badge_file = cliente.get('nivel_grafismo')
                badge_img = load_badge_image(badge_file, size=(120, 19))
                if badge_img:
                    self.lbl_grafismo.configure(image=badge_img, text="")
                    self.lbl_grafismo._img_ref = badge_img # Mantener referencia
                else:
                    self.lbl_grafismo.configure(image=None, text=cliente.get('nivel_grafismo', '~'))
            except Exception:
                pass

            # Activar botón SUMAR PUNTOS
            try:
                self.btn_sumar_puntos.configure(state='normal')
            except Exception:
                pass

            logger.info(f'Cliente {self.cliente_id} cargado: {cliente.get("nombre","")}')

        except Exception:
            logger.exception(f'Error cargando cliente {self.cliente_id}')

    def _on_guardar(self):
        """Guardar/actualizar cliente."""
        try:
            if not self.cliente_service:
                ToastWidget.show(self.container, 'SERVICIO DE CLIENTES NO DISPONIBLE', tipo='error')
                return

            # Validar nombre obligatorio
            nombre = (self.e_nombre.get() or '').strip()
            if not nombre:
                ToastWidget.show(self.container, 'EL NOMBRE ES OBLIGATORIO', tipo='error')
                return

            # Recopilar datos del formulario
            telefono = (self.e_telefono.get() or '').strip()
            email = (self.e_email.get() or '').strip()
            dni = (self.e_dni.get() or '').strip()
            direccion = (self.e_direccion.get() or '').strip()
            ciudad = (self.e_ciudad.get() or '').strip()
            cp = (self.e_cp.get() or '').strip()
            pais = (self.e_pais.get() or '').strip()
            fecha_nac = (self.e_fecha_nac.get() or '').strip() or None
            
            # Normalizar fecha: DD-MM-YYYY o DD/MM/YYYY -> YYYY-MM-DD
            if fecha_nac:
                fecha_nac = fecha_nac.replace('/', '-')
                partes = fecha_nac.split('-')
                # Si viene en formato español (DD-MM-YYYY), la volteamos para la BD
                if len(partes) == 3 and len(partes[0]) <= 2:
                    fecha_nac = f"{partes[2]}-{partes[1]}-{partes[0]}"
            tags = (self.e_tags.get() or '').strip()
            fidelidad_activa = 1 if getattr(self.chk_tesoro, 'get', lambda: 1)() else 0

            # Guardar o actualizar
            if self.cliente_id:
                # Actualizar cliente existente
                ok = self.cliente_service.update_cliente(
                    self.cliente_id, nombre, telefono, email, dni, direccion,
                    ciudad, cp, pais, fecha_nac, tags, fidelidad_activa
                )
                if ok:
                    ToastWidget.show(self.container, f'Cliente {nombre} actualizado', tipo='success')
                    # Recargar datos para actualizar tesoro/nivel
                    try:
                        self._cargar_cliente()
                    except Exception:
                        logger.exception('Error recargando cliente tras update')
                else:
                    ToastWidget.show(self.container, 'NO SE PUDO ACTUALIZAR EL CLIENTE', tipo='error')
            else:
                # Crear nuevo cliente
                cliente_id = self.cliente_service.save_cliente(
                    nombre, telefono, email, dni, direccion, ciudad, cp, pais,
                    fecha_nac, tags, fidelidad_activa
                )
                if cliente_id:
                    ToastWidget.show(self.container, f'Cliente {nombre} creado', tipo='success')
                    # Si hay callback, llamarlo con el ID del cliente nuevo
                    if self.on_save_callback:
                        try:
                            self.on_save_callback(cliente_id)
                        except Exception:
                            logger.exception('Error ejecutando on_save_callback')
                    else:
                        # Limpiar formulario para siguiente alta (comportamiento original)
                        try:
                            self._limpiar_formulario()
                        except Exception:
                            logger.exception('Error limpiando formulario tras save')
                else:
                    ToastWidget.show(self.container, 'NO SE PUDO GUARDAR EL CLIENTE', tipo='error')

        except Exception:
            logger.exception('Error guardando cliente')
            ToastWidget.show(self.container, 'ERROR INESPERADO AL GUARDAR', tipo='error')

    def _on_sumar_puntos(self):
        """Sumar puntos tesoro (requiere password admin y diálogo de entrada)."""
        try:
            if not self.cliente_id:
                ToastWidget.show(self.container, 'DEBES GUARDAR EL CLIENTE PRIMERO', tipo='error')
                return

            if not self.cliente_service or not self.auth_service:
                ToastWidget.show(self.container, 'SERVICIOS NO DISPONIBLES', tipo='error')
                return

            # Obtener ventana padre para los diálogos
            try:
                parent_window = self.container.winfo_toplevel()
            except Exception:
                parent_window = self.container

            # 1. PEDIR PASSWORD ADMIN
            pwd = show_password_dialog(parent_window, "Seguridad", "Introduzca contraseña de Administrador:")
            if not pwd:
                return # Cancelado
            
            is_valid, _ = self.auth_service.validate_admin_password(pwd)
            if not is_valid:
                ToastWidget.show(parent_window, 'CONTRASEÑA DE ADMINISTRADOR INCORRECTA', tipo='error')
                return

            # 2. MOSTRAR DIÁLOGO DE ENTRADA PARA LA CANTIDAD
            nombre_cliente = (self.e_nombre.get() or '').strip()
            prompt = f"Cliente: {nombre_cliente}\n¿Cuánto Tesoro deseas sumar o restar?\n(Usa - para restar, ej: -5.00)"
            
            valor_str = show_input_dialog(parent_window, "ACTUALIZAR TESORO", prompt, tipo='info')

            # Si se canceló o no se introdujo nada, salir
            if valor_str is None or str(valor_str).strip() == "":
                return

            # Normalizar separador decimal y validar como Decimal
            from decimal import Decimal, InvalidOperation
            valor_normalizado = str(valor_str).strip().replace(',', '.')
            try:
                valor_decimal = Decimal(valor_normalizado)
            except (InvalidOperation, ValueError):
                ToastWidget.show(parent_window, 'INTRODUZCA UN NÚMERO VÁLIDO', tipo='error')
                return

            # No permitir cero (no tiene sentido)
            if valor_decimal == Decimal('0'):
                return

            # Ejecutar persistencia en BD
            ok = self.cliente_service.sumar_tesoro(self.cliente_id, valor_decimal)

            if ok:
                msg = f'Tesoro actualizado: {valor_decimal:+.2f}€'
                ToastWidget.show(self.container, msg, tipo='success')
                # Recargar ficha para ver nuevos valores
                self._cargar_cliente()
            else:
                ToastWidget.show(parent_window, 'NO SE PUDO ACTUALIZAR EL TESORO EN LA BASE DE DATOS', tipo='error')

        except Exception:
            logger.exception('Error en _on_sumar_puntos')
            ToastWidget.show(self.container, 'ERROR INESPERADO AL SUMAR TESORO', tipo='error')

    def _on_tickets(self):
        """Abrir vista de tickets del cliente actual."""
        try:
            # Validar que hay cliente cargado
            if not self.cliente_id:
                ToastWidget.show(self.container, 'DEBES GUARDAR EL CLIENTE PRIMERO', tipo='error')
                return

            # Obtener nombre del cliente
            cliente_nombre = (self.e_nombre.get() or '').strip() or f'Cliente {self.cliente_id}'

            # Limpiar área central del padre (si procede)
            if hasattr(self, 'parent') and hasattr(self.parent, 'winfo_children'):
                try:
                    for widget in list(self.parent.winfo_children()):
                        widget.destroy()
                except Exception:
                    pass

            # Crear y mostrar ClientesTicketsUI
            tickets_ui = ClientesTicketsUI(
                parent=self.parent,
                db=self.db,
                cliente_id=self.cliente_id,
                cliente_nombre=cliente_nombre
            )
            try:
                tickets_ui.get_widget().pack(fill='both', expand=True)
            except Exception:
                # Fallback: if template returns container via get_widget
                try:
                    self.parent.update()
                except Exception:
                    pass

            logger.info(f'ClientesTicketsUI abierto para cliente_id={self.cliente_id}')

        except Exception:
            logger.exception('Error en _on_tickets')
            try:
                ToastWidget.show(self.container, 'NO SE PUDO ABRIR VISTA DE TICKETS', tipo='error')
            except Exception:
                pass

    def _on_pedido(self):
        """Navegar a la subvista de creación de pedido para este cliente."""
        try:
            if not self.cliente_id:
                ToastWidget.show(self.container, 'DEBES GUARDAR EL CLIENTE PRIMERO', tipo='error')
                return

            # Obtener ClientesView (owner del owner en esta estructura)
            # CrearClienteUI -> central_area -> ClientesView
            # Buscamos el objeto que tenga show_crear_pedido
            
            view = None
            # En la arquitectura de este proyecto, self.parent suele ser central_area
            # y BaseModuleView tiene la referencia al owner (ClientesView)
            
            # Buscamos el owner que sea ClientesView
            from kool_tpv.modulos.clientes.clientes_view import ClientesView
            
            # Si el parent tiene un atributo 'owner' que es ClientesView
            if hasattr(self.parent, 'owner') and isinstance(self.parent.owner, ClientesView):
                view = self.parent.owner
            elif hasattr(self, 'owner') and isinstance(self.owner, ClientesView):
                view = self.owner

            if view:
                view.show_crear_pedido(cliente_id=self.cliente_id)
            else:
                # Fallback: intentar abrir diálogo si no hay navegación (no debería pasar)
                from kool_tpv.modulos.clientes.pedido_dialog import PedidoDialog
                dialog = PedidoDialog(
                    self.container.winfo_toplevel(), 
                    self.db, 
                    cliente_id=self.cliente_id, 
                    keyboard_manager=getattr(self, 'keyboard_mgr', None)
                )
                if dialog.show():
                    ToastWidget.show(self.container, "PEDIDO REGISTRADO CORRECTAMENTE", tipo='success')
        except Exception:
            logger.exception('Error navegando a crear pedido desde ficha cliente')
            ToastWidget.show(self.container, 'NO SE PUDO ABRIR CREAR PEDIDO', tipo='error')

    def _on_comunicacion(self):
        """Abrir comunicación con cliente."""
        try:
            # TODO: Abrir UI de comunicación
            logger.info('TODO: Implementar comunicación cliente')
            ToastWidget.show(self.container, 'FUNCIÓN COMUNICACIÓN PRÓXIMAMENTE', tipo='info')
        except Exception:
            logger.exception('Error en comunicación')

    def _limpiar_formulario(self):
        """Limpiar todos los campos del formulario."""
        try:
            # Limpiar campos editables
            self.e_nombre.delete(0, 'end')
            self.e_telefono.delete(0, 'end')
            self.e_email.delete(0, 'end')
            self.e_dni.delete(0, 'end')
            self.e_direccion.delete(0, 'end')
            self.e_ciudad.delete(0, 'end')
            self.e_cp.delete(0, 'end')
            self.e_pais.delete(0, 'end')
            try:
                self.e_pais.insert(0, 'España')
            except Exception:
                pass
            self.e_fecha_nac.delete(0, 'end')
            self.e_tags.delete(0, 'end')

            # Checkbox tesoro activado por defecto
            try:
                self.chk_tesoro.select()
            except Exception:
                pass

            # Limpiar valores tesoro (readonly)
            for campo in ['e_tesoro_total', 'e_tesoro_ganado', 'e_tesoro_gastado', 'e_fecha_venc']:
                try:
                    w = getattr(self, campo, None)
                    if w:
                        w.configure(state='normal')
                        w.delete(0, 'end')
                        w.insert(0, '0.00' if 'fecha' not in campo else '')
                        w.configure(state='readonly')
                except Exception:
                    pass

            # Actualizar header tesoro
            try:
                self.lbl_titulo_tesoro.configure(text='TESORO DE')
                self.lbl_level.configure(text='1')
                self.lbl_nombre_nivel.configure(text='Forastero')
                self.lbl_grafismo.configure(image=None, text='~')
            except Exception:
                pass

            logger.info('Formulario cliente limpiado')

        except Exception:
            logger.exception('Error limpiando formulario cliente')
