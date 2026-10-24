import logging
import threading

import customtkinter as ctk

from kool_tpv.modulos.almacen.services.fuentes_editorial_service import FuentesEditorialService
from kool_tpv.modulos.almacen.services.fuentes.registro import RegistroFuentes
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import create_action_button, load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.dialogs.helpers import show_warning, show_error

logger = logging.getLogger(__name__)


class EditorialesUI:
    def __init__(self, parent, db=None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.colors = load_colors(module_name)
        self.service = FuentesEditorialService(db)
        self.registro = RegistroFuentes(self.service)
        self._seleccion = None
        self._fuente_id = None
        self._editoriales = {}
        self._fuentes = {}
        self._chips_editoriales = {}
        self._chips_fuentes = {}
        self._lbl_font = get_font('label', module=module_name)
        self._entry_kw = {
            'fg_color': self.colors.get('background', COLOR_BG_TERMINAL),
            'text_color': self.colors.get('text', COLOR_MATRIX),
            'border_color': self.colors.get('border', COLOR_MATRIX),
            'height': 32, 'border_width': 2,
        }
        self.container = ctk.CTkFrame(parent, fg_color=self.colors.get('background'))
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure((0, 1), weight=1, uniform='mitades')
        self.zona_editoriales = self._zona('EDITORIALES', 0)
        self.zona_fuentes = self._zona('FUENTES', 1)
        self.form = self._formulario(self.zona_editoriales)
        self.e_id = self._campo(self.form, 'ID:', 0, 0)
        self.e_nombre = self._campo(self.form, 'NOMBRE:', 0, 2)
        self.e_url = self._campo(self.form, 'WEB:', 0, 4)
        self.e_id.configure(state='disabled')
        self._label(self.form, 'FUENTE:', 1, 0)
        self.cb_fuente = SearchableCombo(
            self.form, options=[], module_name=module_name,
            command=lambda _: self._cambiar_principal())
        self.cb_fuente.grid(row=1, column=1, columnspan=2, sticky='ew', padx=6, pady=4)
        self._label(self.form, 'FUENTE DE RESERVA:', 1, 3)
        self.cb_reserva = SearchableCombo(self.form, options=[], module_name=module_name)
        self.cb_reserva.grid(row=1, column=4, columnspan=2, sticky='ew', padx=6, pady=4)
        self.chips_frame = self._chips(self.zona_editoriales)
        self.footer = self._pie(self.zona_editoriales)
        self._boton(self.footer, 'anadir', self.clear, 'NUEVA EDITORIAL')
        self.btn_guardar = self._boton(self.footer, 'guardar', self.save, 'GUARDAR EDITORIAL')
        self._boton(self.footer, 'eliminar', self.delete, 'ELIMINAR EDITORIAL')

        self.form_fuente = self._formulario(self.zona_fuentes)
        self.f_id = self._campo(self.form_fuente, 'ID:', 0, 0)
        self.f_nombre = self._campo(self.form_fuente, 'NOMBRE:', 0, 2)
        self.f_id.configure(state='disabled')
        self._label(self.form_fuente, 'PLATAFORMA:', 0, 4)
        self.om_tipo = SearchableCombo(
            self.form_fuente, values=self.service.listar_plataformas(), module_name=module_name)
        self.om_tipo.grid(row=0, column=5, sticky='ew', padx=6, pady=4)
        self.f_url = self._campo(self.form_fuente, 'URL:', 1, 0, colspan=5)
        self._label(self.form_fuente, 'ZONA DE ACCESO (SOLO SI EL PORTAL PIDE USUARIO)', 2, 0, colspan=6)
        self.e_nif = self._campo(self.form_fuente, 'NIF:', 3, 0)
        self.e_usuario = self._campo(self.form_fuente, 'USUARIO:', 3, 2)
        self.e_password = self._campo(self.form_fuente, 'CONTRASEÑA:', 3, 4, show='*')
        self.chips_fuentes = self._chips(self.zona_fuentes)
        pie = self._pie(self.zona_fuentes)
        self._boton(pie, 'anadir', self._nueva_fuente, 'NUEVA FUENTE')
        self.btn_guardar_fuente = self._boton(pie, 'guardar', self._guardar_fuente, 'GUARDAR FUENTE')
        self._boton(pie, 'eliminar', self._borrar_fuente, 'ELIMINAR FUENTE')
        self.btn_probar = self._boton(pie, 'probar', self.probar, 'PROBAR FUENTE')
        self._load_chips()
        self.clear()

    def get_widget(self):
        return self.container

    def _zona(self, titulo, fila):
        zona = ctk.CTkFrame(self.container, fg_color='transparent')
        zona.grid(row=fila, column=0, sticky='nsew', padx=12, pady=6)
        zona.grid_columnconfigure(0, weight=1)
        zona.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(zona, text=titulo, font=get_font('title', module=self.module_name),
                     text_color=self.colors.get('primary')).grid(row=0, column=0, sticky='w')
        return zona

    def _formulario(self, zona):
        form = ctk.CTkFrame(zona, fg_color='transparent')
        form.grid(row=1, column=0, sticky='ew')
        for col in (1, 3, 5):
            form.grid_columnconfigure(col, weight=1)
        return form

    def _label(self, parent, texto, row, col, colspan=1):
        ctk.CTkLabel(parent, text=texto, text_color=self.colors.get('text', COLOR_MATRIX),
                     font=self._lbl_font).grid(
            row=row, column=col, columnspan=colspan, sticky='w', padx=6, pady=4)

    def _campo(self, parent, texto, row, col, colspan=1, show=None):
        self._label(parent, texto, row, col)
        kw = dict(self._entry_kw)
        if show:
            kw['show'] = show
        entry = ctk.CTkEntry(parent, **kw)
        entry.grid(row=row, column=col + 1, columnspan=colspan, sticky='ew', padx=6, pady=4)
        return entry

    def _chips(self, zona):
        frame = ctk.CTkScrollableFrame(zona, height=45, fg_color='transparent')
        frame.grid(row=2, column=0, sticky='nsew', pady=4)
        for col in range(6):
            frame.grid_columnconfigure(col, weight=1)
        return frame

    def _pie(self, zona):
        pie = ctk.CTkFrame(zona, fg_color='transparent')
        pie.grid(row=3, column=0, sticky='ew', pady=4)
        return pie

    def _boton(self, parent, accion, command, texto):
        boton = create_action_button(parent, accion, command, module='almacen', palette_key='primary')
        boton.configure(text=texto)
        boton.pack(side='left', padx=6)
        return boton

    @staticmethod
    def _poner(entry, valor, bloqueado=False):
        if bloqueado:
            entry.configure(state='normal')
        entry.delete(0, 'end')
        entry.insert(0, str(valor or ''))
        if bloqueado:
            entry.configure(state='disabled')

    def _load_chips(self):
        self._editoriales = {e['id']: e for e in self.service.listar_fichas()}
        self._fuentes = {f['id']: f for f in self.service.listar_fuentes()}
        opciones = [(None, 'ninguna')] + self.service.opciones_fuentes()
        ids = (self.cb_fuente.get_id(), self.cb_reserva.get_id())
        self.cb_fuente.set_options(opciones)
        self.cb_reserva.set_options(opciones)
        for combo, fid in zip((self.cb_fuente, self.cb_reserva), ids):
            self._poner_combo(combo, fid)
        for frame, datos, destino, callback in (
                (self.chips_frame, self._editoriales, self._chips_editoriales, self._seleccionar_editorial),
                (self.chips_fuentes, self._fuentes, self._chips_fuentes, self._seleccionar_fuente)):
            for widget in frame.winfo_children():
                widget.destroy()
            destino.clear()
            for i, dato in enumerate(datos.values()):
                fid = dato['id']
                texto = dato['nombre'] if frame is self.chips_frame else f"{dato['nombre']} · ID {fid}"
                boton = ButtonFactory.create_button(
                    parent=frame, text=texto, command=lambda n=fid, cb=callback: cb(n),
                    style_key='chip_default')
                boton.grid(row=i // 6, column=i % 6, sticky='ew', padx=4, pady=4)
                destino[fid] = boton
        self._marcar_chips()

    def _marcar_chips(self):
        for botones, elegido in ((self._chips_editoriales, self._seleccion),
                                  (self._chips_fuentes, self._fuente_id)):
            for fid, boton in botones.items():
                ButtonFactory.apply_style(boton, 'chip_selected' if fid == elegido else 'chip_default')

    def _poner_combo(self, combo, fid):
        fuente = self._fuentes.get(fid)
        combo.set(f"{fuente['nombre']} · ID {fid}" if fuente else 'ninguna')

    def _seleccionar_editorial(self, editorial_id):
        ficha = self._editoriales[editorial_id]
        self._seleccion = editorial_id
        self._poner(self.e_id, editorial_id, True)
        self._poner(self.e_nombre, ficha['nombre'])
        self._poner(self.e_url, ficha.get('web_buscar'))
        self._poner_combo(self.cb_fuente, ficha.get('fuente_id'))
        self._poner_combo(self.cb_reserva, ficha.get('fuente_reserva_id'))
        self._cargar_fuente(ficha.get('fuente_id'))

    def _seleccionar_fuente(self, fuente_id):
        self.clear()
        self._cargar_fuente(fuente_id)

    def _cambiar_principal(self):
        self._cargar_fuente(self.cb_fuente.get_id())

    def _cargar_fuente(self, fuente_id):
        fuente = self._fuentes.get(fuente_id) or {}
        self._fuente_id = fuente.get('id')
        for entry, clave in ((self.f_id, 'id'), (self.f_nombre, 'nombre'),
                            (self.f_url, 'url'), (self.e_nif, 'nif'),
                            (self.e_usuario, 'usuario'), (self.e_password, 'password')):
            self._poner(entry, fuente.get(clave), entry is self.f_id)
        self.om_tipo.set(fuente.get('plataforma') or '')
        self._marcar_chips()

    def clear(self):
        self._seleccion = None
        self._poner(self.e_id, '', True)
        self._poner(self.e_nombre, '')
        self._poner(self.e_url, '')
        self.cb_fuente.set('ninguna')
        self.cb_reserva.set('ninguna')
        self._cargar_fuente(None)

    def _nueva_fuente(self):
        self.clear()
        self.f_nombre.focus_set()

    def _id_combo(self, combo):
        if combo.get().strip() in ('', 'ninguna'):
            return None
        fid = combo.get_id()
        if fid is None:
            raise ValueError('Selecciona una fuente de la lista o ninguna')
        return fid

    def save(self):
        try:
            eid = self.service.guardar_asignacion({
                'nombre': self.e_nombre.get(), 'web_buscar': self.e_url.get(),
                'fuente_id': self._id_combo(self.cb_fuente),
                'fuente_reserva_id': self._id_combo(self.cb_reserva)}, self._seleccion)
            self._load_chips()
            self._seleccionar_editorial(eid)
            ToastWidget.show(self.container, 'Editorial guardada', tipo='success')
        except ValueError as e:
            show_error(self.container, 'EDITORIAL', str(e))
        except Exception:
            logger.exception('Error guardando editorial')
            show_error(self.container, 'EDITORIAL', 'No se pudo guardar')

    def delete(self):
        if not self._seleccion:
            return
        if not show_warning(self.container, 'ELIMINAR EDITORIAL',
                            f"¿Eliminar '{self._editoriales[self._seleccion]['nombre']}'?\n"
                            'Sus fuentes se conservarán.', confirm=True):
            return
        try:
            self.service.borrar_editorial(self._seleccion)
            self.clear()
            self._load_chips()
        except Exception:
            logger.exception('Error eliminando editorial')
            show_error(self.container, 'EDITORIAL', 'No se pudo eliminar')

    def _guardar_fuente(self):
        try:
            datos = {'nombre': self.f_nombre.get(), 'url': self.f_url.get(),
                     'plataforma': self.om_tipo.get(), 'nif': self.e_nif.get(),
                     'usuario': self.e_usuario.get(), 'password': self.e_password.get()}
            if self._fuente_id:
                usos = self.service.usos_de_fuente(self._fuente_id)
                if usos and not show_warning(
                        self.container, 'EDITAR FUENTE COMPARTIDA',
                        'Estos cambios afectarán a: ' + ', '.join(u['nombre'] for u in usos)
                        + '\n¿Guardar los cambios de la fuente?', confirm=True):
                    return
            fid = self.service.guardar_fuente(datos, self._fuente_id)
            self._load_chips()
            self._cargar_fuente(fid)
            ToastWidget.show(self.container, 'Fuente guardada', tipo='success')
        except ValueError as e:
            show_error(self.container, 'FUENTE', str(e))
        except Exception:
            logger.exception('Error guardando fuente')
            show_error(self.container, 'FUENTE', 'No se pudo guardar')

    def _borrar_fuente(self):
        if not self._fuente_id:
            return
        usos = self.service.usos_de_fuente(self._fuente_id)
        if usos:
            show_error(self.container, 'FUENTE EN USO',
                       'Reasigna primero estas editoriales: ' + ', '.join(u['nombre'] for u in usos))
            return
        if not show_warning(self.container, 'ELIMINAR FUENTE',
                            f"¿Eliminar '{self._fuentes[self._fuente_id]['nombre']}'?", confirm=True):
            return
        try:
            self.service.borrar_fuente(self._fuente_id)
            self.clear()
            self._load_chips()
        except ValueError as e:
            show_error(self.container, 'FUENTE', str(e))
        except Exception:
            logger.exception('Error eliminando fuente')
            show_error(self.container, 'FUENTE', 'No se pudo eliminar')

    def probar(self):
        fid = self._fuente_id
        if not fid:
            ToastWidget.show(self.container, 'Guarda o selecciona una fuente primero', tipo='warning')
            return
        self.btn_probar.configure(state='disabled', text='PROBANDO...')

        def work():
            try:
                fuente = self.registro.fuente_para_portal(fid)
                resultado = fuente.probar() if fuente else (False, 'Plataforma no disponible')
            except Exception:
                logger.exception('Error probando fuente')
                resultado = (False, 'No se pudo probar la fuente; revisa el registro')
            self.container.after(0, lambda: self._probar_fin(resultado))

        threading.Thread(target=work, daemon=True).start()

    def _probar_fin(self, resultado):
        self.btn_probar.configure(state='normal', text='PROBAR FUENTE')
        ok, mensaje = resultado
        ToastWidget.show(self.container, mensaje, tipo='success' if ok else 'error')
