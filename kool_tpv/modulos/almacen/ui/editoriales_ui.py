"""UI de Editoriales y Fuentes — estética Matrix, misma estructura que TiposUI.

Una sola lista de fichas: cada chip es una EDITORIAL (el texto que puede
llevar el campo Editorial de un producto). Al pulsarla, el formulario se
rellena con los datos de SU fuente: plataforma (qué código la busca:
zonalibros/planeta/shopify), URL y zona de acceso.

Dos editoriales pueden compartir fuente (ivrea y panini -> SD): al guardar,
si ya existe una fuente con la misma plataforma+url+usuario se reutiliza;
si se cambia algo, se crea una fuente nueva para esa editorial y la otra
no se toca. Las fuentes sin editoriales se borran solas.

PROBAR: intenta entrar en la fuente asociada (solo lectura, en hilo).
"""
import logging
import threading

import customtkinter as ctk

from kool_tpv.modulos.almacen.services.fuentes_editorial_service import (
    FuentesEditorialService,
)
from kool_tpv.modulos.almacen.services.fuentes.registro import RegistroFuentes
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.dialogs.helpers import show_warning, show_error

logger = logging.getLogger(__name__)

# 'web' = sin fuente de búsqueda: solo sirve la web pública para el IR
PLATAFORMAS = ["zonalibros", "planeta", "shopify", "panini_web",
               "ivrea_web", "udl_web", "web"]


class EditorialesUI:
    def __init__(self, parent, db=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX,
                           'secondary': COLOR_MATRIX}
        self.service = FuentesEditorialService(db)
        self.registro = RegistroFuentes(self.service)
        self.container = ctk.CTkFrame(
            self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        self._entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'height': 32, 'border_width': 2,
        }
        self._lbl_font = get_font('label', module=self.module_name)

        self._seleccion = None     # id de la editorial cargada
        self._chip_sel = None

        # --- Título ---
        ctk.CTkLabel(
            self.container, text='EDITORIALES Y FUENTES',
            text_color=self.colors.get('primary', COLOR_MATRIX),
            font=get_font('title', module=self.module_name),
        ).pack(anchor='w', padx=12, pady=(10, 0))

        # --- Formulario ---
        self.form = ctk.CTkFrame(self.container, fg_color='transparent')
        self.form.pack(fill='x', padx=12, pady=6)
        for c in range(8):
            self.form.grid_columnconfigure(c, weight=1)

        self._label(self.form, 'ID:', 0, 0)
        self.e_id = self._entry(self.form, 'automático', 0, 1)
        self.e_id.configure(state='disabled',
                            text_color=self.colors.get('light', '#666666'))
        self._label(self.form, 'NOMBRE:', 0, 2)
        self.e_nombre = self._entry(
            self.form, 'lo que se escribe en Editorial: panini...', 0, 3)
        self._label(self.form, 'PLATAFORMA:', 0, 4)
        self.om_tipo = ctk.CTkOptionMenu(
            self.form, values=PLATAFORMAS,
            fg_color=self.colors.get('primary'),
            text_color='#000000',
            button_color=self.colors.get('secondary'),
            font=self._lbl_font)
        self.om_tipo.grid(row=0, column=5, sticky='ew', padx=6, pady=6)

        self._label(self.form, 'URL:', 1, 0)
        self.e_url = self._entry(
            self.form, 'web del portal donde se busca (ej. la de SD)', 1, 1,
            colspan=7)

        # --- Zona de acceso ---
        sep = ctk.CTkFrame(self.form, fg_color='transparent')
        sep.grid(row=2, column=0, columnspan=8, sticky='ew', pady=(10, 0))
        ctk.CTkLabel(
            sep, text='ZONA DE ACCESO  (solo si el portal pide usuario)',
            text_color=self.colors.get('secondary', COLOR_MATRIX),
            font=self._lbl_font).pack(anchor='w')

        self._label(self.form, 'NIF:', 3, 0)
        self.e_nif = self._entry(self.form, 'NIF fiscal', 3, 1)
        self._label(self.form, 'USUARIO:', 3, 2)
        self.e_usuario = self._entry(self.form, 'usuario', 3, 3)
        self._label(self.form, 'CONTRASEÑA:', 3, 4)
        self.e_password = self._entry(self.form, 'contraseña', 3, 5, colspan=3,
                                    show='*')

        # --- Chips (un chip = una editorial) ---
        self.chips_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.chips_frame.pack(fill='both', expand=True, padx=12, pady=6)

        # --- Footer ---
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)
        create_action_button(self.footer, 'anadir', self.clear,
                             module='almacen', palette_key='secondary').pack(
            side='left', padx=8)
        self.btn_guardar = create_action_button(
            self.footer, 'guardar', self.save, module='almacen',
            palette_key='primary')
        self.btn_guardar.pack(side='left', padx=8)
        create_action_button(self.footer, 'eliminar', self.delete,
                             module='almacen', palette_key='accent').pack(
            side='left', padx=8)
        self.btn_probar = create_action_button(
            self.footer, 'probar', self.probar, module='almacen',
            palette_key='secondary')
        self.btn_probar.pack(side='left', padx=8)

        self._load_chips()

    def get_widget(self):
        return self.container

    # ---------- helpers de formulario ----------

    def _label(self, parent, texto, row, col):
        ctk.CTkLabel(parent, text=texto, text_color=self.colors['text'],
                     font=self._lbl_font).grid(
            row=row, column=col, sticky='w', padx=6, pady=6)

    def _entry(self, parent, placeholder, row, col, colspan=1, show=None):
        kw = dict(self._entry_kw)
        if show:
            kw['show'] = show
        e = ctk.CTkEntry(parent, placeholder_text=placeholder, **kw)
        e.grid(row=row, column=col, columnspan=colspan, sticky='ew',
               padx=6, pady=6)
        return e

    # ---------- chips ----------

    def _select_chip(self, btn, ficha):
        if self._chip_sel is not None:
            try:
                if self._chip_sel.winfo_exists():
                    ButtonFactory.apply_style(self._chip_sel, "chip_default")
            except Exception:
                pass
        self._chip_sel = btn
        ButtonFactory.apply_style(btn, "chip_selected")
        self._load_ficha(ficha)

    def _load_chips(self):
        for w in list(self.chips_frame.winfo_children()):
            w.destroy()
        for c in range(8):
            self.chips_frame.grid_columnconfigure(c, weight=1)
        for i, ficha in enumerate(self.service.listar_fichas()):
            btn = ButtonFactory.create_button(
                parent=self.chips_frame,
                text=ficha.get('nombre') or str(ficha['id']), command=None,
                style_key="chip_default")
            btn.grid(row=i // 8, column=i % 8, padx=5, pady=5, sticky='nsew')
            btn.bind('<Button-1>',
                     lambda e, b=btn, f=ficha: self._select_chip(b, f))

    # ---------- carga / limpieza ----------

    def _load_ficha(self, ficha):
        """`ficha` = fila de editoriales + su fuente embebida."""
        fuente = ficha.get('fuente') or {}
        self._seleccion = ficha.get('id')
        self.e_id.configure(state='normal')
        self.e_id.delete(0, 'end')
        self.e_id.insert(0, str(ficha.get('id') or ''))
        self.e_id.configure(state='disabled')
        self.e_nombre.delete(0, 'end')
        self.e_nombre.insert(0, ficha.get('nombre') or '')
        self.om_tipo.set(fuente.get('plataforma') or 'web')
        self.e_url.delete(0, 'end')
        self.e_url.insert(0, fuente.get('url') or '')
        self.e_nif.delete(0, 'end')
        self.e_nif.insert(0, fuente.get('nif') or '')
        self.e_usuario.delete(0, 'end')
        self.e_usuario.insert(0, fuente.get('usuario') or '')
        self.e_password.delete(0, 'end')
        self.e_password.insert(0, fuente.get('password') or '')
        self.btn_guardar.configure(text='ACTUALIZAR')

    def clear(self):
        """AÑADIR: vacía el formulario; el id lo asigna la base de datos."""
        self._seleccion = None
        for e in (self.e_nombre, self.e_url,
                  self.e_nif, self.e_usuario, self.e_password):
            e.delete(0, 'end')
        self.e_id.configure(state='normal')
        self.e_id.delete(0, 'end')
        self.e_id.configure(state='disabled')
        self.om_tipo.set('zonalibros')
        self.btn_guardar.configure(text='GUARDAR')
        try:
            self.e_nombre.focus_set()
        except Exception:
            pass

    # ---------- acciones ----------

    def save(self):
        try:
            self._seleccion = self.service.guardar_ficha(
                {'nombre': self.e_nombre.get(),
                 'plataforma': self.om_tipo.get(),
                 'url': self.e_url.get(),
                 'nif': self.e_nif.get().strip(),
                 'usuario': self.e_usuario.get().strip(),
                 'password': self.e_password.get().strip()},
                editorial_id=self._seleccion)
            self.e_id.configure(state='normal')
            self.e_id.delete(0, 'end')
            self.e_id.insert(0, str(self._seleccion))
            self.e_id.configure(state='disabled')
            self._load_chips()
            self.btn_guardar.configure(text='ACTUALIZAR')
            ToastWidget.show(self.container, 'Editorial guardada',
                             tipo='success')
        except ValueError as e:
            show_error(self.container, 'Error', str(e))
        except Exception:
            logger.exception('Error guardando editorial')
            show_error(self.container, 'Error', 'No se pudo guardar')

    def delete(self):
        if not self._seleccion:
            return
        try:
            ok = show_warning(
                self.container, 'Eliminar editorial',
                f"¿Eliminar '{self.e_nombre.get() or self._seleccion}'?",
                confirm=True)
            if not ok:
                return
            self.service.borrar_editorial(self._seleccion)
            self._seleccion = None
            self._load_chips()
            self.clear()
        except Exception:
            logger.exception('Error eliminando editorial')
            show_error(self.container, 'Error', 'No se pudo eliminar')

    def probar(self):
        """Intenta entrar en la fuente de la editorial cargada (solo lectura,
        en hilo)."""
        nombre = (self.e_nombre.get() or "").strip()
        if not nombre:
            ToastWidget.show(self.container, 'Escribe el nombre primero',
                             tipo='warning')
            return
        self.btn_probar.configure(state='disabled', text='PROBANDO...')

        def _run():
            try:
                fuente = self.registro.fuente_para_editorial(nombre)
                resultado = fuente.probar() if fuente else (
                    False, 'Esta editorial no tiene fuente de búsqueda')
            except Exception as e:
                logger.exception('Error probando fuente')
                resultado = (False, str(e))
            self.container.after(0, lambda: self._probar_fin(nombre, resultado))

        threading.Thread(target=_run, daemon=True).start()

    def _probar_fin(self, nombre, resultado):
        self.btn_probar.configure(state='normal', text='PROBAR')
        ok, msg = resultado
        ToastWidget.show(self.container, f"'{nombre}': {msg}",
                         tipo='success' if ok else 'error')
