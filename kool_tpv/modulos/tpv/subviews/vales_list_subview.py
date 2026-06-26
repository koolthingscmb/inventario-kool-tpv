from customtkinter import CTkFrame
import logging
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)


class ValesListSubView(CTkFrame):

    def __init__(self, parent, view=None, module_name='tpv'):
        super().__init__(parent)

        self.view = view
        self.module_name = module_name

        from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
        self.vale_service = ValeDevolucionService()

        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_eliminar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="ELIMINAR",
            style_key="mini_outline_clientes",
            command=self._on_eliminar_seleccionado
        )
        self.btn_eliminar.pack(side="right", padx=10)

        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        columns = [
            ("fecha", 160, "Fecha"),
            ("importe", 100, "Importe"),
            ("estado", 100, "Estado"),
            ("ticket_devolucion", 140, "Ticket Devolución"),
            ("ticket_venta", 140, "Usado en Ticket"),
        ]

        from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
        from kool_tpv.utils.config_loader import load_layout_config

        root = self.winfo_toplevel()
        from kool_tpv.utils.keyboard_manager import KeyboardManager
        _km = getattr(root, 'keyboard_manager', None)

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_vales,
            map_function=self._map_vale,
            module_name=self.module_name,
            page_limit=50,
            on_double_click=self._on_double_click,
            keyboard_manager=_km,
            layout_config=load_layout_config(),
        )
        self.search_list.pack(fill="both", expand=True)

        nav = getattr(self.search_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_key'):
            try:
                nav.bind_key('<Delete>', lambda e: self._on_eliminar_seleccionado())
            except Exception:
                pass

    def _buscar_vales(self, texto):
        try:
            vales = self.vale_service.listar_todos()
            vales.sort(key=lambda v: v.get('fecha', ''), reverse=True)
            if texto:
                t = texto.lower()
                vales = [
                    v for v in vales
                    if t in v.get('num_ticket_devolucion', '').lower()
                    or t in v.get('num_ticket_venta_uso', '').lower()
                    or t in v.get('fecha', '').lower()
                ]
            return vales
        except Exception:
            logger.exception('Error listando vales')
            return []

    def _map_vale(self, vale):
        try:
            from kool_tpv.base_datos.money_adapter import read_from_db
            importe = read_from_db(vale.get('importe_cents', 0))
            fecha = vale.get('fecha', '')[:16].replace('T', ' ')
            usado = vale.get('usado', False)
            estado = 'USADO' if usado else 'PENDIENTE'
            ticket_venta = vale.get('num_ticket_venta_uso') or '-'
            return {
                'id': vale.get('id'),
                'path': vale.get('path', ''),
                'fecha': fecha,
                'importe': f'{importe:.2f} €',
                'estado': estado,
                'ticket_devolucion': vale.get('num_ticket_devolucion', '-'),
                'ticket_venta': ticket_venta,
                'usado': usado,
            }
        except Exception:
            return {}

    def _on_double_click(self, data):
        self._confirmar_eliminar(data)

    def _on_eliminar_seleccionado(self):
        nav = getattr(self.search_list, 'nav_list', None)
        if nav:
            data = nav.get_selected_data()
            if data:
                self._confirmar_eliminar(data)

    def _confirmar_eliminar(self, data):
        if not data:
            return
        usado = data.get('usado', False)
        path = data.get('path', '')
        vale_id = data.get('id', '')

        def _ejecutar():
            ok = self.vale_service.eliminar_por_path(path) if path else self.vale_service.eliminar(vale_id)
            if ok:
                ToastWidget.show(self, 'Vale eliminado', tipo='success')
                self.search_list.search('')
            else:
                ToastWidget.show(self, 'NO SE PUDO ELIMINAR EL VALE', tipo='error')

        _ejecutar()

    def destroy(self):
        super().destroy()
