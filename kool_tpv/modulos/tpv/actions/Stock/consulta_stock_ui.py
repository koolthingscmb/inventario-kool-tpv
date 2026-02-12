"""Lógica separada para el modo 'consulta' del overlay de stock.

Esta clase encapsula carga de ventas, renderizado de filas de venta,
gestión del `VisorNegro` y acciones relacionadas (mostrar/imprimir).
Se construye con una referencia al `StockUI` padre para reutilizar
su `tree`, `db`, `formatter` y `view` sin duplicar UI.
"""
import logging
import re

from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro


class ConsultaStockHandler:
    def __init__(self, parent):
        self.parent = parent  # StockUI instance
        # The handler can store transient state if needed

    def load_ventas(self, termino=''):
        """Cargar ventas del producto seleccionado en el parent."""
        try:
            producto = getattr(self.parent, 'producto_consulta', None)
            if not producto:
                return []
            producto_id = producto.get('id')
            ventas = []
            try:
                if getattr(self.parent, 'data_service', None):
                    ventas = self.parent.data_service.obtener_ventas_producto(producto_id)
                else:
                    ventas = []
            except Exception:
                logging.exception('Error obteniendo ventas desde data_service')
                ventas = []

            if termino:
                termino_lower = termino.lower()
                ventas = [v for v in ventas if termino_lower in (v.get('cliente_nombre') or '').lower()]

            # Diagnostic log: cuántas ventas se han obtenido y qué tickets contienen
            try:
                ticket_ids = [v.get('ticket_id') or v.get('id') for v in ventas]
                logging.info('ConsultaStockHandler.load_ventas producto_id=%s -> %d ventas, tickets=%s', producto_id, len(ventas), ticket_ids)
            except Exception:
                pass

            return ventas
        except Exception:
            logging.exception('Error en ConsultaStockHandler.load_ventas')
            return []

    def render_ventas(self, ventas):
        """Renderizar las ventas en el tree del parent."""
        try:
            tree = getattr(self.parent, 'tree', None)
            db = getattr(self.parent, 'db', None)
            formatter = getattr(self.parent, 'formatter', None)
            if tree is None:
                return

            for venta in ventas:
                try:
                    fecha_raw = venta.get('fecha', '')
                    fecha_formateada = ''
                    try:
                        if formatter:
                            fecha_formateada = formatter.format_fecha(fecha_raw)
                        else:
                            if fecha_raw and len(fecha_raw) >= 10:
                                partes = fecha_raw[:10].split('-')
                                if len(partes) == 3:
                                    fecha_formateada = f"{partes[2]}/{partes[1]}/{partes[0]}"
                                else:
                                    fecha_formateada = fecha_raw.split()[0]
                            else:
                                fecha_formateada = fecha_raw
                    except Exception:
                        fecha_formateada = fecha_raw.split()[0] if fecha_raw else ''

                    cantidad_raw = venta.get('cantidad', 0)
                    try:
                        cantidad_str = str(int(float(cantidad_raw)))
                    except Exception:
                        cantidad_str = str(cantidad_raw)

                    ticket_id_row = venta.get('ticket_id') or venta.get('id')
                    num_ticket_display = venta.get('num_ticket')
                    if not num_ticket_display and db is not None:
                        try:
                            row = db.fetch_one("SELECT num_ticket FROM tickets WHERE id = ?", (ticket_id_row,))
                            if row:
                                num_ticket_display = row[0]
                        except Exception:
                            pass

                    display_ticket = num_ticket_display or ticket_id_row

                    tree.insert('', 'end', iid=str(ticket_id_row), values=(display_ticket, fecha_formateada, cantidad_str, venta.get('cliente_nombre')))
                except Exception:
                    logging.exception('Error insertando venta en tree (ConsultaStockHandler)')
        except Exception:
            logging.exception('Error en ConsultaStockHandler.render_ventas')

    def configurar_modo_consulta(self):
        """Configurar elementos visuales y botones necesarios para modo consulta.

        Esta función manipula el `parent` (StockUI) widgets para mostrar
        el VisorNegro y los botones de imprimir/volver sin tocar el layout general.
        """
        try:
            parent = self.parent

            nombre_prod = parent.producto_consulta.get('nombre', 'Producto') if parent.producto_consulta else 'Producto'
            parent.title_text = f"CONSULTA: {nombre_prod}"
            try:
                if hasattr(parent, 'header_label'):
                    parent.header_label.configure(text=parent.title_text)
            except Exception:
                pass

            # Aplicar columnas de consulta desde parent
            try:
                parent._aplicar_config_columnas(parent.columns_config_consulta)
            except Exception:
                pass

            # Ocultar botones específicos de stock
            try:
                if hasattr(parent, 'modificar_btn'):
                    parent.modificar_btn.pack_forget()
            except Exception:
                pass

            try:
                if hasattr(parent, 'anadir_btn'):
                    parent.anadir_btn.pack_forget()
            except Exception:
                pass

            # Crear/mostrar botón IMPRIMIR (volver_btn)
            try:
                if not hasattr(parent, 'volver_btn'):
                    from customtkinter import CTkButton
                    parent.volver_btn = CTkButton(parent.header_actions_frame, text="IMPRIMIR", fg_color='#FFFFFF', text_color='#000000', hover_color="#3af9fc", command=parent._on_imprimir_ticket, width=140)
                try:
                    parent.volver_btn.pack(side="left", padx=5)
                except Exception:
                    pass
            except Exception:
                pass

            # Aceptar → Mostrar ticket
            try:
                if hasattr(parent, 'aceptar_btn'):
                    parent.aceptar_btn.configure(text="Mostrar Ticket", command=parent._on_mostrar_ticket)
            except Exception:
                pass

            # Mantener búsqueda habilitada
            try:
                if hasattr(parent, 'search_var'):
                    parent.search_var.set('')
                if hasattr(parent, 'search_entry'):
                    parent.search_entry.configure(state='normal')
                    parent.after(100, lambda: parent.search_entry.focus_set())
            except Exception:
                pass

            # Crear VisorNegro en view.cart_view si es posible
            try:
                view = getattr(parent, 'view', None)
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    if getattr(parent, '_visor_negro', None) is None:
                        parent._visor_negro = VisorNegro(view.cart_view)
                    try:
                        parent._visor_negro.set_text('')
                        parent._visor_negro.set_text_color('#00FF00')
                        parent._visor_negro.set_font_size(13)
                        parent._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error creando/mostrando VisorNegro (ConsultaStockHandler)')

        except Exception:
            logging.exception('Error en configurar_modo_consulta')

    def on_imprimir_ticket(self):
        """Imprimir el ticket actualmente mostrado en el VisorNegro o seleccionado."""
        try:
            parent = self.parent
            ticket_id = getattr(parent, '_last_shown_ticket_id', None)
            if ticket_id is None:
                sel = parent.tree.selection()
                if sel:
                    try:
                        ticket_id = int(sel[0])
                    except Exception:
                        ticket_id = None

            if ticket_id is None:
                logging.info('No hay ticket para imprimir')
                return

            from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
            impresora = ImpresoraService(parent.db)
            try:
                texto_imp = impresora.generar_ticket_desde_id(ticket_id)
                if texto_imp:
                    print("\n" + "="*50)
                    print(" IMPRIMIENDO TICKET ")
                    print("="*50 + "\n")
                    print(texto_imp)
                    print("\n" + "="*50 + "\n")
                    try:
                        impresora.logger.info("Ticket impreso (simulado) id=%s", ticket_id)
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error imprimiendo ticket (ConsultaStockHandler)')

        except Exception:
            logging.exception('Error en on_imprimir_ticket')

    def on_mostrar_ticket(self):
        """Mostrar ticket seleccionado/regenerado en VisorNegro."""
        try:
            parent = self.parent
            sel = parent.tree.selection()
            if not sel:
                logging.info('No hay ticket seleccionado')
                return
            try:
                ticket_id = int(sel[0])
            except Exception:
                logging.error('ID de ticket inválido')
                return

            ticket_text = None
            regenerated = False
            try:
                if getattr(parent, 'db', None) is not None:
                    try:
                        row = parent.db.fetch_one("SELECT ticket_text FROM tickets WHERE id = ?", (ticket_id,))
                        if row and row[0]:
                            ticket_text = row[0]
                    except Exception:
                        logging.exception('Error leyendo ticket_text desde BD')

                if not ticket_text:
                    from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                    try:
                        impresora = ImpresoraService(parent.db)
                        ticket_text = impresora.generar_ticket_desde_id(ticket_id)
                        regenerated = True
                    except Exception:
                        logging.exception('Error regenerando ticket desde impresora')

                if not ticket_text:
                    logging.warning(f'No se pudo obtener/crear ticket {ticket_id}')
                    return

                if regenerated:
                    try:
                        ticket_text = re.sub(r"--(?=\d)", "-", ticket_text)
                        ticket_text = ticket_text.replace('-0.00', '0.00')
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error recuperando o generando ticket')
                return

            try:
                parent._last_shown_ticket_id = ticket_id
            except Exception:
                parent._last_shown_ticket_id = None

            try:
                view = getattr(parent, 'view', None)
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    if parent._visor_negro is None:
                        parent._visor_negro = VisorNegro(view.cart_view)
                    try:
                        parent._visor_negro.set_text_color('#00FF00')
                    except Exception:
                        pass
                    try:
                        parent._visor_negro.set_text(ticket_text)
                    except Exception:
                        parent._visor_negro.set_text(str(ticket_text))
                    try:
                        parent._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error mostrando ticket en VisorNegro (ConsultaStockHandler)')

        except Exception:
            logging.exception('Error en on_mostrar_ticket')
