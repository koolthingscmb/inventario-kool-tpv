from customtkinter import CTkFrame
import logging
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)


class ValesListSubView(CTkFrame):

    def __init__(self, parent, view=None, module_name='tpv', on_select=None):
        super().__init__(parent)

        self.view = view
        self.module_name = module_name
        self.on_select_callback = on_select

        from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
        self.vale_service = ValeDevolucionService()

        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        from kool_tpv.utils.factories.button_factory import ButtonFactory
        self.btn_eliminar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="ELIMINAR",
            style_key="action_danger",
            command=self._on_eliminar_seleccionados
        )
        self.btn_eliminar.pack(side="right", padx=10)
        self.btn_eliminar.configure(state="disabled")

        self.btn_select_all = ButtonFactory.create_button(
            parent=self.header_frame,
            text="TODO",
            style_key="action_primary",
            command=lambda: self.search_list.nav_list.select_all() if hasattr(self.search_list, 'nav_list') else None,
            width=80
        )
        self.btn_select_all.pack(side="right", padx=5)

        self.list_frame = CTkFrame(self)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        columns = [
            ("fecha", 160, "Fecha"),
            ("nombre_vale", 200, "Nombre Vale"),
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
            multi_select=True,
            on_selection_change=self._on_selection_change
        )
        self.search_list.pack(fill="both", expand=True)

        nav = getattr(self.search_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_key'):
            try:
                nav.bind_key('<Delete>', lambda e: self._on_eliminar_seleccionados())
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
            from pathlib import Path as _Path
            importe = read_from_db(vale.get('importe_cents', 0))
            fecha = vale.get('fecha', '')[:16].replace('T', ' ')
            usado = vale.get('usado', False)
            estado = 'USADO' if usado else 'PENDIENTE'
            ticket_venta = vale.get('num_ticket_venta_uso') or '-'
            
            # Obtener nombre del archivo sin extensión
            path_str = vale.get('path', '')
            nombre_vale = _Path(path_str).stem if path_str else '?'
            if nombre_vale.startswith('USADO_'):
                nombre_vale = nombre_vale[6:]
            
            return {
                'id': vale.get('id'),
                'path': path_str,
                'fecha': fecha,
                'nombre_vale': nombre_vale,
                'importe': f'{importe:.2f} €',
                'estado': estado,
                'ticket_devolucion': vale.get('num_ticket_devolucion', '-'),
                'ticket_venta': ticket_venta,
                'usado': usado,
            }
        except Exception:
            return {}

    def _on_selection_change(self, indices):
        """Habilitar/Deshabilitar botón eliminar según selección."""
        if indices:
            self.btn_eliminar.configure(state="normal")
        else:
            self.btn_eliminar.configure(state="disabled")

    def _on_double_click(self, data):
        if self.on_select_callback:
            self.on_select_callback(data)
        else:
            self._confirmar_eliminar([data])

    def _on_eliminar_seleccionados(self):
        items = self.search_list.get_selected_items()
        if items:
            self._confirmar_eliminar(items)

    def _confirmar_eliminar(self, items):
        if not items:
            return
            
        count = len(items)
        if count == 1:
            mensaje = f"¿Estás seguro de que deseas eliminar el vale '{items[0].get('nombre_vale')}'?"
        else:
            mensaje = f"¿Estás seguro de que deseas eliminar {count} vales?"

        from kool_tpv.utils.dialogs import MessageDialog
        
        def _ejecutar(confirm):
            if confirm:
                success_count = 0
                for data in items:
                    path = data.get('path', '')
                    vale_id = data.get('id', '')
                    ok = self.vale_service.eliminar_por_path(path) if path else self.vale_service.eliminar(vale_id)
                    if ok:
                        success_count += 1
                
                if success_count > 0:
                    ToastWidget.show(self, f'{success_count} vales eliminados', tipo='success')
                    self.search_list.search('')
                else:
                    ToastWidget.show(self, 'NO SE PUDO ELIMINAR NINGÚN VALE', tipo='error')

        MessageDialog(
            self.winfo_toplevel(),
            titulo="ELIMINAR VALES",
            mensaje=mensaje,
            tipo="warning",
            confirm=True,
            callback=_ejecutar
        )

    def destroy(self):
        super().destroy()
