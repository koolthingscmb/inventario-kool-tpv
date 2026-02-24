"""Plantilla reutilizable para overlays que muestran/visuan registros (visor).

Esta clase es una versión genérica de la lógica contenida originalmente en
`consulta_stock_ui.py`. Está pensada para ser importada y usada por distintos
overlays; los nombres concretos (producto/venta/ticket/impresora) se han
generalizado a `item`/`record`/`print_service`/`visor` para facilitar su
reutilización. Cuando se integre en un overlay concreto, basta con adaptar
los nombres de los callbacks/atributos del `parent` (o extender esta clase).

Comportamiento principal:
- `load_items(item_id, termino='')` intenta cargar registros usando varios
  puntos de extensión del `parent` (función `data_loader`, `data_service`,
  o método específico si existen).
- `render_items(items)` inserta filas en el `tree` del `parent`.
- `configure_vis_mode()` prepara la UI para el modo visor (botón imprimir,
  cambiar texto de aceptar, crear `VisorNegro`).
- `on_print_item()` y `on_show_item()` ofrecen hooks genéricos para imprimir o
  mostrar el registro; intentan usar `parent.print_callback` o
  `parent.print_service` si existen, y caen a un intento seguro con la BD.
"""
import logging
import re

from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro


class SelectionOverlayVisor:
    def __init__(self, parent):
        self.parent = parent

    def load_items(self, item_id=None, termino=''):
        """Cargar registros relacionados con `item_id`.

        Busca de forma flexible en el `parent` los puntos de carga disponibles:
        - `parent.data_loader(item_id)` si existe y es callable
        - `parent.data_service.obtener_ventas_producto(item_id)` (compatibilidad)
        - `parent.load_items_for_parent(item_id)` si existe
        Devuelve una lista de dicts (puede ser vacía).
        """
        parent = self.parent
        try:
            if item_id is None:
                # intentar obtener un item seleccionado del parent con nombres
                item = getattr(parent, 'item_for_consulta', None) or getattr(parent, 'selected_item', None)
                if item:
                    item_id = item.get('id')

            items = []
            try:
                loader = getattr(parent, 'data_loader', None)
                if callable(loader):
                    items = loader(item_id)
                elif getattr(parent, 'data_service', None):
                    svc = parent.data_service
                    # compat: servicio concreto usado en repo original
                    if hasattr(svc, 'obtener_ventas_producto'):
                        items = svc.obtener_ventas_producto(item_id)
                    elif hasattr(svc, 'obtener_items'):
                        items = svc.obtener_items(item_id)
                    else:
                        items = []
                elif hasattr(parent, 'load_items_for_parent'):
                    items = parent.load_items_for_parent(item_id)
                else:
                    items = []
            except Exception:
                logging.exception('Error en loader de SelectionOverlayVisor')
                items = []

            # filtro por termino si se proporcionó
            if termino:
                termino_lower = termino.lower()
                items = [it for it in items if termino_lower in (it.get('cliente_nombre') or it.get('name') or '').lower()]

            try:
                ids = [it.get('ticket_id') or it.get('id') for it in items]
                logging.info('SelectionOverlayVisor.load_items id=%s -> %d items, ids=%s', item_id, len(items), ids)
            except Exception:
                pass

            return items
        except Exception:
            logging.exception('Error en SelectionOverlayVisor.load_items')
            return []

    def render_items(self, items):
        """Renderizar lista de items en el tree del parent.

        Se asume que cada item tiene campos como `fecha`, `cantidad`,
        `cliente_nombre` y `ticket_id`/`id`. El formato de fecha se delega en
        `parent.formatter` si existe.
        """
        try:
            tree = getattr(self.parent, 'tree', None)
            db = getattr(self.parent, 'db', None)
            formatter = getattr(self.parent, 'formatter', None)
            if tree is None:
                return

            # preservar selección actual antes de re-renderizar
            try:
                current_selection = list(tree.selection() or [])
            except Exception:
                current_selection = []

            # limpiar tree antes de insertar si el parent no lo hace
            try:
                for iid in tree.get_children():
                    tree.delete(iid)
            except Exception:
                pass

            # Render according to parent's columns_config when available
            cols = []
            try:
                cols = getattr(self.parent, 'columns_config', [])
            except Exception:
                cols = []

            for it in items:
                try:
                    record_id = it.get('ticket_id') or it.get('id')

                    values = []
                    for col in cols:
                        key = col[0]
                        val = None
                        try:
                            if key in ('id', 'ticket_id'):
                                val = record_id
                            elif key in ('created_at', 'fecha'):
                                raw = it.get('created_at') or it.get('fecha') or ''
                                if formatter:
                                    try:
                                        val = formatter.format_fecha(raw)
                                    except Exception:
                                        val = raw
                                else:
                                    if raw and len(raw) >= 10:
                                        partes = raw[:10].split('-')
                                        if len(partes) == 3:
                                            val = f"{partes[2]}/{partes[1]}/{partes[0]}"
                                        else:
                                            val = raw.split()[0]
                                    else:
                                        val = raw
                            else:
                                # generic: try direct key, then num_ticket, then cliente_nombre
                                val = it.get(key)
                                if val is None and key == 'num_ticket':
                                    val = it.get('num_ticket') or it.get('num') or it.get('numero')
                                if val is None and key == 'total':
                                    v = it.get('total')
                                    try:
                                        if formatter and v is not None:
                                            val = formatter.format_currency(v)
                                        else:
                                            val = v
                                    except Exception:
                                        val = v
                                if val is None:
                                    # fallback to common fields
                                    val = it.get('cliente_nombre') or it.get('name') or it.get('cliente')

                        except Exception:
                            val = ''
                        values.append(val)

                    # Ensure we have an iid
                    iid = str(record_id) if record_id is not None else None
                    tree.insert('', 'end', iid=iid, values=tuple(values))
                except Exception:
                    logging.exception('Error insertando item en tree (SelectionOverlayVisor)')
            # restaurar selección previa cuando sea posible
            try:
                for iid in current_selection:
                    # only re-add selection if item still exists
                    if iid and iid in tree.get_children():
                        try:
                            tree.selection_add(iid)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error en SelectionOverlayVisor.render_items')

    def configure_vis_mode(self):
        """Configurar la UI del parent para el modo visor (mostrar/imprimir).

        Cambia cabecera, botones y crea un `VisorNegro` en `parent.view.cart_view`
        si está disponible.
        """
        try:
            parent = self.parent

            nombre = ''
            item = getattr(parent, 'item_for_consulta', None) or getattr(parent, 'selected_item', None)
            if item:
                nombre = item.get('nombre') or item.get('name') or ''

            parent.title_text = f"VISOR: {nombre}" if nombre else "VISOR"
            try:
                if hasattr(parent, 'header_label'):
                    parent.header_label.configure(text=parent.title_text)
            except Exception:
                pass

            # aplicar columnas de consulta si el parent expone la configuración
            try:
                if hasattr(parent, '_aplicar_config_columnas') and getattr(parent, 'columns_config_consulta', None):
                    parent._aplicar_config_columnas(parent.columns_config_consulta)
            except Exception:
                pass

            # ocultar botones no necesarios (si existen)
            try:
                if hasattr(parent, 'modificar_btn'):
                    parent.modificar_btn.pack_forget()
                if hasattr(parent, 'anadir_btn'):
                    parent.anadir_btn.pack_forget()
            except Exception:
                pass

            # Botón imprimir (intentar crear si no existe)
            try:
                if not hasattr(parent, 'imprimir_btn'):
                    from customtkinter import CTkButton
                    parent.imprimir_btn = CTkButton(parent.header_actions_frame, text="IMPRIMIR", fg_color='#FFFFFF', text_color='#000000', hover_color="#3af9fc", command=self.on_print_item, width=140)
                try:
                    parent.imprimir_btn.pack(side="left", padx=5)
                except Exception:
                    pass
            except Exception:
                pass

            # Aceptar → Mostrar registro
            try:
                if hasattr(parent, 'aceptar_btn'):
                    parent.aceptar_btn.configure(text="Mostrar", command=self.on_show_item)
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

            # Crear/mostrar VisorNegro si la vista lo provee
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
                logging.exception('Error creando/mostrando VisorNegro (SelectionOverlayVisor)')

        except Exception:
            logging.exception('Error en SelectionOverlayVisor.configure_vis_mode')

    def on_print_item(self):
        """Imprimir el registro seleccionado o mostrado.

        Intenta usar varios puntos de extensión del `parent`: `print_callback`,
        `print_service`, o por último intenta usar `kool_tpv.modulos.impresion.impresora_service`
        como compatibilidad.
        """
        try:
            parent = self.parent
            record_id = getattr(parent, '_last_shown_record_id', None)
            if record_id is None:
                sel = parent.tree.selection()
                if sel:
                    try:
                        record_id = int(sel[0])
                    except Exception:
                        record_id = None

            if record_id is None:
                logging.info('No hay registro para imprimir')
                return

            # preferir callback del parent si existe
            try:
                if hasattr(parent, 'print_callback') and callable(parent.print_callback):
                    parent.print_callback(record_id)
                    return
            except Exception:
                logging.exception('Error en parent.print_callback')

            # intentar servicio de impresión expuesto por el parent
            try:
                svc = getattr(parent, 'print_service', None)
                if svc and hasattr(svc, 'generar_ticket_desde_id'):
                    texto = svc.generar_ticket_desde_id(record_id)
                    if texto:
                        print(texto)
                        return
            except Exception:
                logging.exception('Error en parent.print_service')

            # compat: intentar módulo impresora del proyecto
            try:
                from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                impresora = ImpresoraService(getattr(parent, 'db', None))
                texto_imp = impresora.generar_ticket_desde_id(record_id)
                if texto_imp:
                    print(texto_imp)
            except Exception:
                logging.exception('Error imprimiendo registro (SelectionOverlayVisor)')

        except Exception:
            logging.exception('Error en SelectionOverlayVisor.on_print_item')

    def on_show_item(self):
        """Mostrar el registro seleccionado/regenerado en el visor.

        Genera/lee el texto del registro con las mismas opciones flexibles que
        en `on_print_item`, luego lo vuelca al `VisorNegro` asociado al parent.
        """
        try:
            parent = self.parent
            sel = parent.tree.selection()
            if not sel:
                logging.info('No hay registro seleccionado')
                return
            try:
                record_id = int(sel[0])
            except Exception:
                logging.error('ID de registro inválido')
                return

            record_text = None
            regenerated = False
            try:
                # intentar leer texto guardado en BD
                if getattr(parent, 'db', None) is not None:
                    try:
                        row = parent.db.fetch_one("SELECT ticket_text FROM tickets WHERE id = ?", (record_id,))
                        if row and row[0]:
                            record_text = row[0]
                    except Exception:
                        logging.exception('Error leyendo ticket_text desde BD (SelectionOverlayVisor)')

                # intentar servicio de impresión/regen
                if not record_text:
                    try:
                        svc = getattr(parent, 'print_service', None)
                        if svc and hasattr(svc, 'generar_ticket_desde_id'):
                            record_text = svc.generar_ticket_desde_id(record_id)
                            regenerated = True
                    except Exception:
                        logging.exception('Error en parent.print_service al regenerar')

                if not record_text:
                    try:
                        from kool_tpv.modulos.impresion.impresora_service import ImpresoraService
                        impresora = ImpresoraService(getattr(parent, 'db', None))
                        record_text = impresora.generar_ticket_desde_id(record_id)
                        regenerated = True
                    except Exception:
                        logging.exception('Error regenerando ticket (SelectionOverlayVisor)')

                if not record_text:
                    logging.warning('No se pudo obtener/crear texto para registro %s', record_id)
                    return

                if regenerated:
                    try:
                        record_text = re.sub(r"--(?=\d)", "-", record_text)
                        record_text = record_text.replace('-0.00', '0.00')
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error recuperando o generando registro (SelectionOverlayVisor)')
                return

            try:
                parent._last_shown_record_id = record_id
            except Exception:
                parent._last_shown_record_id = None

            try:
                view = getattr(parent, 'view', None)
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    if getattr(parent, '_visor_negro', None) is None:
                        parent._visor_negro = VisorNegro(view.cart_view)
                    try:
                        parent._visor_negro.set_text_color('#00FF00')
                    except Exception:
                        pass
                    try:
                        parent._visor_negro.set_text(record_text)
                    except Exception:
                        parent._visor_negro.set_text(str(record_text))
                    try:
                        parent._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error mostrando registro en VisorNegro (SelectionOverlayVisor)')

        except Exception:
            logging.exception('Error en SelectionOverlayVisor.on_show_item')
