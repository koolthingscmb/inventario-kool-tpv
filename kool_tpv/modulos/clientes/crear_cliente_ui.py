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
from kool_tpv.modulos.clientes.clientes_tickets import ClientesTicketsUI

logger = logging.getLogger(__name__)


class CrearClienteUI:
    """Ficha completa de cliente con tesoro y niveles (sección datos básicos)."""

    def __init__(self, parent, db: Optional[Database] = None, cliente_id: Optional[int] = None, module_name: str = 'clientes'):
        self.parent = parent
        self.db = db
        self.cliente_id = cliente_id
        self.module_name = module_name
        # try to load module color palette; fall back to COLOR_MATRIX if loader fails
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {
                'text': COLOR_MATRIX,
                'primary': COLOR_MATRIX,
            }

        self.cliente_service = ClienteService(db) if db else None

        self.container = ctk.CTkFrame(parent, fg_color=COLOR_BG_TERMINAL)

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
        self.main_scroll = ctk.CTkScrollableFrame(self.container, fg_color=COLOR_BG_TERMINAL)
        self.main_scroll.pack(fill='both', expand=True, padx=12, pady=8)

        # Grid 8 columnas
        for c in range(8):
            self.main_scroll.grid_columnconfigure(c, weight=1, uniform='col')

        lbl_font = get_font('label', module=self.module_name)
        entry_kw = {
            "fg_color": COLOR_BG_TERMINAL,
            "text_color": self.colors.get('text', COLOR_MATRIX),
            "border_width": 2,
            "border_color": self.colors.get('primary', COLOR_MATRIX),
            "corner_radius": 4
        }

        # === FILA 0: ID | NOMBRE | TESORO ACTIVADO ===
        ctk.CTkLabel(self.main_scroll, text="ID:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=0, sticky='w', padx=6, pady=6
        )
        self.e_id = ctk.CTkEntry(
            self.main_scroll,
            placeholder_text="ID (auto)",
            state='disabled',
            fg_color=COLOR_BG_TERMINAL,
            text_color=self.colors.get('text', "#666666"),
            border_color=self.colors.get('primary', COLOR_MATRIX)
        )
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="NOMBRE:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=2, sticky='w', padx=6, pady=6
        )
        self.e_nombre = ctk.CTkEntry(self.main_scroll, placeholder_text="Nombre completo", **entry_kw)
        self.e_nombre.grid(row=0, column=3, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="TESORO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=0, column=6, sticky='w', padx=6, pady=6
        )
        self.chk_tesoro = ctk.CTkCheckBox(
            self.main_scroll,
            text='Activado',
            fg_color=self.colors.get('primary', COLOR_MATRIX),
            text_color=self.colors.get('text', COLOR_MATRIX)
        )
        self.chk_tesoro.grid(row=0, column=7, sticky='w', padx=6, pady=6)
        try:
            self.chk_tesoro.select()  # Por defecto ON
        except Exception:
            pass

        # === FILA 1: DNI | FECHA NACIMIENTO ===
        ctk.CTkLabel(self.main_scroll, text="DNI:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=1, column=0, sticky='w', padx=6, pady=6
        )
        self.e_dni = ctk.CTkEntry(self.main_scroll, placeholder_text="DNI/NIE", **entry_kw)
        self.e_dni.grid(row=1, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="F. NACIMIENTO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=1, column=4, sticky='w', padx=6, pady=6
        )
        self.e_fecha_nac = ctk.CTkEntry(self.main_scroll, placeholder_text="YYYY-MM-DD", **entry_kw)
        self.e_fecha_nac.grid(row=1, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # === FILA 2: DIRECCIÓN | PAÍS ===
        ctk.CTkLabel(self.main_scroll, text="DIRECCIÓN:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=2, column=0, sticky='w', padx=6, pady=6
        )
        self.e_direccion = ctk.CTkEntry(self.main_scroll, placeholder_text="Calle, número...", **entry_kw)
        self.e_direccion.grid(row=2, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="PAÍS:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=2, column=4, sticky='w', padx=6, pady=6
        )
        self.e_pais = ctk.CTkEntry(self.main_scroll, placeholder_text="España", **entry_kw)
        self.e_pais.grid(row=2, column=5, columnspan=3, sticky='ew', padx=6, pady=6)
        try:
            self.e_pais.insert(0, 'España')  # Default
        except Exception:
            pass

        # === FILA 3: CIUDAD | CÓDIGO POSTAL ===
        ctk.CTkLabel(self.main_scroll, text="CIUDAD:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=3, column=0, sticky='w', padx=6, pady=6
        )
        self.e_ciudad = ctk.CTkEntry(self.main_scroll, placeholder_text="Ciudad", **entry_kw)
        self.e_ciudad.grid(row=3, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="C.P.:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=3, column=4, sticky='w', padx=6, pady=6
        )
        self.e_cp = ctk.CTkEntry(self.main_scroll, placeholder_text="Código Postal", **entry_kw)
        self.e_cp.grid(row=3, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # === FILA 4: TELÉFONO | EMAIL | TAGS ===
        ctk.CTkLabel(self.main_scroll, text="TELÉFONO:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=0, sticky='w', padx=6, pady=6
        )
        self.e_telefono = ctk.CTkEntry(self.main_scroll, placeholder_text="Teléfono", **entry_kw)
        self.e_telefono.grid(row=4, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="EMAIL:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=3, sticky='w', padx=6, pady=6
        )
        self.e_email = ctk.CTkEntry(self.main_scroll, placeholder_text="email@ejemplo.com", **entry_kw)
        self.e_email.grid(row=4, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.main_scroll, text="TAGS:", text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(
            row=4, column=6, sticky='w', padx=6, pady=6
        )
        self.e_tags = ctk.CTkEntry(self.main_scroll, placeholder_text="tag1, tag2", **entry_kw)
        self.e_tags.grid(row=4, column=7, sticky='ew', padx=6, pady=6)

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

        self.btn_comunicacion = create_action_button(self.footer, 'comunicacion', self._on_comunicacion)
        self.btn_comunicacion.pack(side='left', padx=8)

        # Cargar datos si es edición
        if self.cliente_id:
            self._cargar_cliente()

        logger.info('CrearClienteUI inicializado completamente')

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
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Cliente no encontrado en BD')
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

            # Fecha nacimiento
            try:
                self.e_fecha_nac.delete(0, 'end')
                if cliente.get('fecha_nacimiento'):
                    self.e_fecha_nac.insert(0, cliente['fecha_nacimiento'])
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
                self.lbl_grafismo.configure(text=cliente.get('nivel_grafismo', '~'))
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
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Servicio de clientes no disponible')
                return

            # Validar nombre obligatorio
            nombre = (self.e_nombre.get() or '').strip()
            if not nombre:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Validación', 'El nombre es obligatorio')
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
            # Auto-corregir formato de fecha: aceptar tanto YYYY/MM/DD como YYYY-MM-DD
            if fecha_nac and '/' in fecha_nac:
                fecha_nac = fecha_nac.replace('/', '-')
            tags = (self.e_tags.get() or '').strip()
            fidelidad_activa = 1 if getattr(self.chk_tesoro, 'get', lambda: 1)() else 0

            # Guardar o actualizar
            ok = False
            if self.cliente_id:
                # Actualizar cliente existente
                ok = self.cliente_service.update_cliente(
                    self.cliente_id, nombre, telefono, email, dni, direccion,
                    ciudad, cp, pais, fecha_nac, tags, fidelidad_activa
                )
                if ok:
                    from kool_tpv.utils.custom_dialog import show_success
                    show_success(self.container, 'Actualizado', 
                               f'Cliente {nombre} actualizado correctamente')
                    # Recargar datos para actualizar tesoro/nivel
                    try:
                        self._cargar_cliente()
                    except Exception:
                        logger.exception('Error recargando cliente tras update')
            else:
                # Crear nuevo cliente
                ok = self.cliente_service.save_cliente(
                    nombre, telefono, email, dni, direccion, ciudad, cp, pais,
                    fecha_nac, tags, fidelidad_activa
                )
                if ok:
                    from kool_tpv.utils.custom_dialog import show_success
                    show_success(self.container, 'Guardado', 
                               f'Cliente {nombre} creado correctamente')
                    # Limpiar formulario para siguiente alta
                    try:
                        self._limpiar_formulario()
                    except Exception:
                        logger.exception('Error limpiando formulario tras save')

            if not ok:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se pudo guardar el cliente')

        except Exception:
            logger.exception('Error guardando cliente')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'Error inesperado al guardar')

    def _on_sumar_puntos(self):
        """Sumar puntos tesoro (requiere password admin)."""
        try:
            # TODO: Validar password admin + diálogo sumar puntos
            logger.info('TODO: Implementar sumar puntos con pw admin')
            from kool_tpv.utils.custom_dialog import show_info
            show_info(self.container, 'En desarrollo', 'Función SUMAR PUNTOS próximamente')
        except Exception:
            logger.exception('Error en sumar puntos')

    def _on_tickets(self):
        """Abrir vista de tickets del cliente actual."""
        try:
            # Validar que hay cliente cargado
            if not self.cliente_id:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Tickets', 'Debes guardar el cliente primero')
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
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se pudo abrir vista de tickets')
            except Exception:
                pass

    def _on_comunicacion(self):
        """Abrir comunicación con cliente."""
        try:
            # TODO: Abrir UI de comunicación
            logger.info('TODO: Implementar comunicación cliente')
            from kool_tpv.utils.custom_dialog import show_info
            show_info(self.container, 'En desarrollo', 'Función COMUNICACIÓN próximamente')
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
                self.lbl_grafismo.configure(text='~')
            except Exception:
                pass

            logger.info('Formulario cliente limpiado')

        except Exception:
            logger.exception('Error limpiando formulario cliente')
