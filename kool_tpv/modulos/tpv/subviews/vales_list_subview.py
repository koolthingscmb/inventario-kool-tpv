from customtkinter import CTkFrame
import logging
from decimal import Decimal
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.dialogs.input_dialog import InputDialog
from kool_tpv.base_datos.money_adapter import read_from_db, prepare_for_db

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
        
        self.btn_usar = ButtonFactory.create_button(
            parent=self.header_frame,
            text="USAR VALE",
            style_key="action_success",
            command=self._on_usar_vale
        )
        self.btn_usar.pack(side="right", padx=10)
        self.btn_usar.configure(state="disabled")

        self.btn_crear = ButtonFactory.create_button(
            parent=self.header_frame,
            text="+ CREAR VALE",
            style_key="action_primary",
            command=self._on_crear_vale
        )
        self.btn_crear.pack(side="right", padx=10)

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
            ("fecha", 90, "FECHA"),
            ("nombre_vale", 150, "NOMBRE"),
            ("cliente", 180, "CLIENTE", True), # Stretch
            ("importe", 90, "💰"),
            ("ticket_devolucion", 120, "DEVOLUCIÓN"),
            ("usado_check", 50, "📥"),
            ("saldo", 120, "SALDO"),
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

        # Setup Tab Navigation
        self._setup_tab_nav()

    def _setup_tab_nav(self):
        """Configurar la navegación por Tab."""
        try:
            root = self.winfo_toplevel()
            root.bind("<Tab>", self._on_tab_next)
            root.bind("<Shift-Tab>", self._on_tab_prev)

            self.bind("<Destroy>", self._on_view_destroy)
        except Exception:
            logging.exception("Error vinculando Tab en ValesListSubView")

    def _on_view_destroy(self, event):
        """Limpiar bindings globales al cerrar la vista."""
        if event.widget == self:
            try:
                root = self.winfo_toplevel()
                root.unbind("<Tab>")
                root.unbind("<Shift-Tab>")
            except Exception:
                pass

    def _get_navigable_widgets(self):
        """Obtiene la lista de widgets navegables en orden."""
        widgets = []
        def add_widget(w):
            if not w: return
            if hasattr(w, '_entry'): widgets.append(w._entry)
            elif hasattr(w, '_canvas'): widgets.append(w._canvas)
            else: widgets.append(w)

        add_widget(self.btn_select_all)
        add_widget(self.btn_crear)
        add_widget(self.btn_eliminar)
        add_widget(self.btn_usar)

        return [w for w in widgets if w.winfo_exists() and w.winfo_viewable()]

    def _on_tab_next(self, event):
        """Foco al siguiente widget."""
        widgets = self._get_navigable_widgets()
        if not widgets: return

        try:
            current = self.focus_get()
            if current in widgets:
                idx = widgets.index(current)
                next_idx = (idx + 1) % len(widgets)
                widgets[next_idx].focus_set()
            else:
                widgets[0].focus_set()
        except Exception:
            widgets[0].focus_set()

        return "break"

    def _on_tab_prev(self, event):
        """Foco al widget anterior."""
        widgets = self._get_navigable_widgets()
        if not widgets: return

        try:
            current = self.focus_get()
            if current in widgets:
                idx = widgets.index(current)
                prev_idx = (idx - 1) % len(widgets)
                widgets[prev_idx].focus_set()
            else:
                widgets[-1].focus_set()
        except Exception:
            widgets[-1].focus_set()

        return "break"

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
            
            # Cálculo de saldo disponible
            saldo_restante_cents = vale.get('importe_restante_cents', vale.get('importe_cents', 0))
            saldo_euros = read_from_db(saldo_restante_cents)
            
            # Formato fecha d-m-y
            raw_fecha = vale.get('fecha', '')
            if raw_fecha:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(raw_fecha)
                    fecha_str = dt.strftime('%d-%m-%y')
                except Exception:
                    fecha_str = raw_fecha[:10]
            else:
                fecha_str = '-'

            usado = vale.get('usado', False)
            usado_check = '✓' if usado else '✗'

            # Si el vale está usado, el saldo es 0
            if usado:
                saldo_restante_cents = 0
                saldo_euros = Decimal('0.00')
            
            # Obtener nombre del archivo sin extensión
            path_str = vale.get('path', '')
            nombre_vale = _Path(path_str).stem if path_str else '?'
            if nombre_vale.startswith('USADO_'):
                nombre_vale = nombre_vale[6:]
            
            return {
                'id': vale.get('id'),
                'path': path_str,
                'fecha': fecha_str,
                'nombre_vale': nombre_vale,
                'cliente': vale.get('cliente_nombre') or '-',
                'importe': f'{importe:.2f} €',
                'ticket_devolucion': vale.get('num_ticket_devolucion', '-'),
                'usado_check': usado_check,
                'usado': usado,
                'saldo_cents': saldo_restante_cents,
                'saldo_original_cents': vale.get('importe_original_cents', vale.get('importe_cents', 0)),
                'saldo': f'{saldo_euros:.2f} €',
            }
        except Exception:
            return {}

    def _on_selection_change(self, indices):
        """Habilitar/Deshabilitar botones según selección."""
        if indices:
            self.btn_eliminar.configure(state="normal")
            # Habilitar USAR VALE solo si hay 1 seleccionado y no está usado
            items = self.search_list.get_selected_items()
            if len(items) == 1 and not items[0].get('usado'):
                self.btn_usar.configure(state="normal")
            else:
                self.btn_usar.configure(state="disabled")
        else:
            self.btn_eliminar.configure(state="disabled")
            self.btn_usar.configure(state="disabled")

    def _on_crear_vale(self):
        """Abrir subvista de creación manual de vale."""
        try:
            from kool_tpv.modulos.tpv.subviews.vale_crear_ui import ValeCrearUI
            root = self.winfo_toplevel()
            db = getattr(root, 'db', None)
            
            subview = ValeCrearUI(
                parent=self.view.center_area,
                view=self.view,
                db=db,
                callback_success=lambda: self.search_list.search('')
            )
            self.view.push_subview(subview, "CREAR VALE MANUAL")
        except Exception:
            logger.exception('Error abriendo ValeCrearUI')

    def _on_usar_vale(self):
        """Aplicar el vale seleccionado al carrito del TPV."""
        items = self.search_list.get_selected_items()
        if not items or len(items) != 1:
            return

        vale_data = items[0]
        if vale_data.get('usado'):
            ToastWidget.show(self, "El vale ya ha sido usado", tipo='warning')
            return

        try:
            # 1. Cargar datos completos del vale desde el service (necesitamos importe_cents)
            full_vale = self.vale_service.obtener_por_id(vale_data['id'])
            if not full_vale:
                ToastWidget.show(self, "No se encontró el archivo del vale", tipo='error')
                return

            # 2. Determinar saldo disponible (nuevo o legacy)
            importe_total_cents = full_vale.get('importe_cents', 0)
            saldo_restante_cents = full_vale.get('importe_restante_cents', importe_total_cents)
            saldo_euros = read_from_db(saldo_restante_cents)

            # 3. Preguntar importe a aplicar
            def _on_importe_decidido(valor_str):
                if valor_str is None:
                    return  # Cancelado

                try:
                    valor_str = valor_str.strip().replace(',', '.')
                    if not valor_str:
                        ToastWidget.show(self, "Debes introducir un importe", tipo='warning')
                        return

                    importe_euros = Decimal(valor_str)
                    if importe_euros <= Decimal('0.00'):
                        ToastWidget.show(self, "El importe debe ser mayor que 0", tipo='warning')
                        return

                    importe_aplicar_cents = prepare_for_db(importe_euros)

                    if importe_aplicar_cents > saldo_restante_cents:
                        ToastWidget.show(
                            self,
                            f"El importe ({importe_euros:.2f} €) supera el saldo disponible",
                            tipo='warning'
                        )
                        return

                    # 4. Aplicar al carrito con el importe decidido
                    if hasattr(self.view, 'carrito_service'):
                        self.view.carrito_service.aplicar_vale({
                            'id': full_vale['id'],
                            'importe_cents': importe_aplicar_cents,
                            'importe_restante_cents': saldo_restante_cents,
                            'cliente_id': full_vale.get('cliente_id'),
                        })

                        # 5. Refrescar ticket
                        ticket = getattr(self.view, 'ticket_widget', None)
                        if ticket and hasattr(ticket, 'update_carrito'):
                            ticket.update_carrito()

                        # 6. Volver al TPV
                        if hasattr(self.view, 'pop_subview'):
                            self.view.pop_subview()
                            ToastWidget.show(self.view, f"Vale de {importe_euros:.2f} € aplicado", tipo='success')
                    else:
                        ToastWidget.show(self, "No se pudo acceder al carrito", tipo='error')
                except Exception:
                    logger.exception('Error aplicando vale')
                    ToastWidget.show(self, "Error al aplicar el vale", tipo='error')

            InputDialog(
                parent=self.winfo_toplevel(),
                titulo="IMPORTE A USAR",
                mensaje=f"Saldo disponible: {saldo_euros:.2f} €",
                valor_defecto=f"{saldo_euros:.2f}",
                callback=_on_importe_decidido,
            )
        except Exception:
            logger.exception('Error usando vale')
            ToastWidget.show(self, "Error al aplicar el vale", tipo='error')

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
