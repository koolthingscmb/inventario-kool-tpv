"""Informes module main view.

Minimal scaffold for the Informes module. Shows a centered placeholder
label in the central area provided by BaseModuleView.
"""
from typing import Optional
import customtkinter as ctk
import logging

from kool_tpv.utils.config_loader import load_colors, create_action_button, load_layout_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.templates.base_module_view import BaseModuleView
from kool_tpv.utils.utils import FONT_TERMINAL
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.date_picker_entry import DatePickerEntry
from kool_tpv.modulos.informes.informes_service import InformesService
from kool_tpv.utils.formatter_service import FormatterService
from kool_tpv.utils.widgets.tag_selector import TagSelector


class InformesView(BaseModuleView):
    """Main view for the Informes module (placeholder).

    This class is intentionally minimal: it provides the UI shell and a
    centered message indicating the module is under construction. No
    business logic or database queries are performed here.
    """

    def __init__(self, parent, db, keyboard_manager: Optional[object] = None):
        # Initialize BaseModuleView using module key 'informes' so the
        # sidebar palette and menu are loaded according to config.
        super().__init__(parent, config_section='informes')

        # Store commonly used references
        try:
            self.db = db
            self.keyboard_manager = keyboard_manager
        except Exception:
            self.db = db
            self.keyboard_manager = None

        # Desactivar captura global de teclado en este módulo
        if self.keyboard_manager:
            try:
                self.keyboard_manager.pause()
            except AttributeError:
                try:
                    self.keyboard_manager.disable()
                except Exception:
                    pass
            except Exception:
                pass

        # Load colors for the module (used by future UIs)
        try:
            self.colors = load_colors('informes') or {}
        except Exception:
            logging.exception('Error loading colors for informes')
            self.colors = {}

        # Estado del informe actual generado
        self.current_report_data = None

        # Update breadcrumb to module root (display only)
        try:
            self.actualizar_ruta('INFORMES')
        except Exception:
            logging.exception('Error updating breadcrumb in InformesView')

        # Show generator immediately when entering the module
        try:
            self.show_generar()
        except Exception:
            logging.exception('Error auto-opening generador en InformesView')

        # Forzar foco absoluto al módulo poco después de inicializar
        try:
            self.after(100, lambda: self._force_initial_focus())
        except Exception:
            pass

    def destroy(self):
        # Reactivar KeyboardManager antes de destruir
        if hasattr(self, 'keyboard_manager') and self.keyboard_manager:
            try:
                self.keyboard_manager.resume()
            except AttributeError:
                try:
                    self.keyboard_manager.enable()
                except Exception:
                    pass
            except Exception:
                pass

        try:
            # Destruir Toplevels pendientes del calendario
            if hasattr(self, 'entry_fecha_inicio'):
                try:
                    self.entry_fecha_inicio.destroy()
                except Exception:
                    pass

            if hasattr(self, 'entry_fecha_fin'):
                try:
                    self.entry_fecha_fin.destroy()
                except Exception:
                    pass

            # Limpiar estado
            try:
                self.current_report_data = None
            except Exception:
                pass
        except Exception:
            import logging
            logging.exception('Error en cleanup de InformesView')

        super().destroy()

    def get_widget(self):
        return self

    def _force_initial_focus(self):
        try:
            self.focus_set()
            if hasattr(self, 'cb_tipo_informe'):
                try:
                    self.cb_tipo_informe.focus_set()
                except Exception:
                    pass
        except Exception:
            pass

    def show_generar(self):
        """Mostrar el generador de informes (placeholder).

        Crea un frame simple con un label centrado y actualiza la ruta.
        """
        try:
            colors = self.colors or {}
            primary_btn = (colors.get('buttons') or {}).get('primary', {})
            btn_bg = primary_btn.get('bg', colors.get('primary', '#00A4DF'))
            btn_hover = primary_btn.get('hover', primary_btn.get('bg', '#6FCFF5'))
            btn_text = primary_btn.get('text', colors.get('text', '#FFFFFF'))

            # Main content frame
            content_frame = ctk.CTkFrame(self.central_area, fg_color=colors.get('background', 'transparent'))

            # HEADER
            header_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            header_frame.pack(fill='x', padx=12, pady=(12, 8))

            title_lbl = ctk.CTkLabel(header_frame, text='GENERADOR DE INFORMES', font=get_font('title', module='informes'), text_color=colors.get('text'))
            title_lbl.pack(anchor='w', padx=6, pady=(0, 6))

            # Filters row
            filters_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
            filters_frame.pack(fill='x', padx=6, pady=(4, 6))

            lbl_tipo = ctk.CTkLabel(filters_frame, text='Tipo:', font=get_font('label', module='informes'), text_color=colors.get('text'))
            lbl_tipo.pack(side='left', padx=(0, 6))
            self.cb_tipo_informe = ctk.CTkComboBox(
                filters_frame,
                values=[
                    "Resumen de ventas",
                    "Ventas diarias",
                    "Ventas por cajero",
                    "Ventas por categoría",
                    "Ventas por tipo",
                    "Ventas por producto",
                    "Stock por categoría",
                    "Stock por tipo"
                ],
                state='readonly',
                width=220,
                font=get_font('entry', module='informes')
            )
            self.cb_tipo_informe.pack(side='left', padx=(0, 12))

            # Invalidar informe si cambian los filtros
            try:
                # DatePickerEntry expone el widget interno `entry`
                self.entry_fecha_inicio.entry.bind('<KeyRelease>', self._on_filter_change)
            except Exception:
                pass

            lbl_desde = ctk.CTkLabel(filters_frame, text='Desde:', font=get_font('label', module='informes'), text_color=colors.get('text'))
            lbl_desde.pack(side='left', padx=(0, 6))
            # Guardar referencia para mostrar/ocultar dinámicamente
            self.lbl_desde = lbl_desde
            self.entry_fecha_inicio = DatePickerEntry(filters_frame, module_name='informes', width=140, allow_future=False)
            self.entry_fecha_inicio.pack(side='left', padx=(0, 12))

            lbl_hasta = ctk.CTkLabel(filters_frame, text='Hasta:', font=get_font('label', module='informes'), text_color=colors.get('text'))
            lbl_hasta.pack(side='left', padx=(0, 6))
            # Guardar referencia para mostrar/ocultar dinámicamente
            self.lbl_hasta = lbl_hasta
            self.entry_fecha_fin = DatePickerEntry(filters_frame, module_name='informes', width=140, allow_future=False)
            self.entry_fecha_fin.pack(side='left', padx=(0, 12))

            # Fechas por defecto: primer día del mes actual → hoy
            from datetime import date
            today = date.today()
            first_day = today.replace(day=1)
            self.entry_fecha_inicio.set(first_day.isoformat())
            self.entry_fecha_fin.set(today.isoformat())

            # Extra filters: tag selector (starts disabled)
            try:
                extra_filters_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
                extra_filters_frame.pack(fill='x', padx=6, pady=(0, 8))

                # Label hint dinámico (CTkEntry no refresca placeholder_text dinámicamente)
                self.lbl_tag_hint = ctk.CTkLabel(
                    extra_filters_frame,
                    text="Selecciona un tipo de informe compatible...",
                    font=get_font('label', module='informes'),
                    text_color=colors.get('text_secondary', '#888888')
                )
                self.lbl_tag_hint.pack(anchor='w', padx=12, pady=(0, 2))

                self.tag_selector = TagSelector(extra_filters_frame, module_name='informes')
                self.tag_selector.pack(fill='x', padx=12, pady=(0, 8))
                try:
                    # Altura fija para la zona de tags
                    self.tag_selector.configure(height=80)
                except Exception:
                    pass
                try:
                    # Desactivar inicialmente la caja de búsqueda interna
                    self.tag_selector.search_combo.configure(state='disabled')
                except Exception:
                    pass
            except Exception:
                logging.exception('Error creando TagSelector en InformesView')

            self.btn_generar = ButtonFactory.create_button(
                parent=filters_frame,
                text='ACEPTAR',
                command=self._on_generar_click,
                style_key='action_confirm'
            )
            self.btn_generar.pack(side='left', padx=(6, 0))

            try:
                # Ensure ComboBox notifies when selection changes
                self.cb_tipo_informe.configure(command=self._on_tipo_informe_changed)
            except Exception:
                pass

            # BODY
            result_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            result_frame.pack(fill='both', expand=True, padx=12, pady=(6, 12))

            # Leer configuración de layout para el viewer
            layout_cfg = load_layout_config()
            informes_cfg = layout_cfg.get('informes', {})
            viewer_cfg = informes_cfg.get('viewer', {})
            viewer_width = viewer_cfg.get('width', 800)
            viewer_height = viewer_cfg.get('height', 600)

            self.result_textbox = ctk.CTkTextbox(result_frame, width=viewer_width, height=viewer_height)
            self.result_textbox.pack(fill='both', expand=True)
            # Configurar como solo lectura pero copiable
            try:
                # Permitir selección y copia, bloquear edición
                def block_edit(event):
                    # Permitir Ctrl+C/A (Windows/Linux) y Command+C/A (Mac)
                    if event.state & 0x4 or event.state & 0x8:  # Ctrl o Command
                        if event.keysym in ('c', 'a', 'C', 'A'):
                            return
                    # Bloquear solo teclas que modifican contenido
                    if event.keysym in ('BackSpace', 'Delete'):
                        return "break"
                    # Permitir navegación (flechas, home, end, etc)
                    if len(event.keysym) > 1:
                        return
                    # Bloquear inserción de caracteres
                    return "break"

                self.result_textbox.bind("<Key>", block_edit)
            except Exception:
                pass

            # FOOTER (placeholder)
            footer_frame = ctk.CTkFrame(content_frame, fg_color='transparent')
            footer_frame.pack(fill='x', padx=12, pady=(0, 12))

            # Botones de exportación CSV y PDF
            try:
                self.btn_export_csv = ButtonFactory.create_button(
                    footer_frame,
                    text='Exportar CSV',
                    command=self._on_exportar_csv_click,
                    style_key='action_secondary'
                )
                self.btn_export_csv.pack(side='left', padx=8)
                self.btn_export_pdf = ButtonFactory.create_button(
                    footer_frame,
                    text='Exportar PDF',
                    command=self._on_exportar_pdf_click,
                    style_key='action_secondary'
                )
                self.btn_export_pdf.pack(side='left', padx=8)
                try:
                    self._update_export_button_state()
                except Exception:
                    pass
            except Exception:
                logging.exception('Error creando botones Exportar en InformesView')

            navigated = False
            try:
                navigated = self.set_central_content(content_frame)
            except Exception:
                logging.exception('Error pasando content_frame a set_central_content en show_generar')

            if navigated:
                try:
                    self.actualizar_ruta('INFORMES / GENERAR')
                except Exception:
                    pass

        except Exception:
            logging.exception('Error en show_generar de InformesView')

    def _on_generar_click(self):
        try:
            fecha_inicio = self.entry_fecha_inicio.get()
            fecha_fin = self.entry_fecha_fin.get()

            # Detectar tipo pronto para condicionar validaciones
            try:
                tipo_informe = self.cb_tipo_informe.get()
            except Exception:
                tipo_informe = ''

            # Validaciones: solo para informes que NO son de Stock
            try:
                if 'stock' not in (tipo_informe or '').lower():
                    if not fecha_inicio or not fecha_fin:
                        from kool_tpv.utils.custom_dialog import show_warning
                        show_warning(self.central_area, 'Fechas requeridas',
                                     'Debes seleccionar ambas fechas')
                        return

                    if fecha_inicio > fecha_fin:
                        from kool_tpv.utils.custom_dialog import show_warning
                        show_warning(self.central_area, 'Rango inválido',
                                     'La fecha inicio no puede ser mayor que la fecha fin')
                        return
            except Exception:
                pass

            service = InformesService(self.db)

            # Generar informe según tipo
            if tipo_informe == "Resumen de ventas":
                report_data = service.get_informe_resumen_ventas(fecha_inicio, fecha_fin)
            elif tipo_informe == "Ventas diarias":
                report_data = service.get_informe_ventas_diarias(fecha_inicio, fecha_fin)
            elif tipo_informe == "Ventas por cajero":
                report_data = service.get_informe_ventas_por_cajero(fecha_inicio, fecha_fin)
            elif tipo_informe == "Ventas por categoría":
                categorias = None
                try:
                    categorias = self.tag_selector.get_selected_ids()
                except Exception:
                    categorias = None
                report_data = service.get_informe_ventas_por_categoria(fecha_inicio, fecha_fin, categorias=categorias)
            elif tipo_informe == "Ventas por tipo":
                tipos = None
                try:
                    tipos = self.tag_selector.get_selected_ids()
                except Exception:
                    tipos = None
                report_data = service.get_informe_ventas_por_tipo(fecha_inicio, fecha_fin, tipos=tipos)
            elif tipo_informe == "Ventas por producto":
                report_data = service.get_informe_ventas_por_producto(fecha_inicio, fecha_fin)
            elif tipo_informe == "Stock por categoría":
                try:
                    categoria_ids = self.tag_selector.get_selected_ids()
                except Exception:
                    categoria_ids = None
                report_data = service.get_informe_stock_por_categoria(categoria_ids if categoria_ids else None)
            elif tipo_informe == "Stock por tipo":
                try:
                    tipo_ids = self.tag_selector.get_selected_ids()
                except Exception:
                    tipo_ids = None
                report_data = service.get_informe_stock_por_tipo(tipo_ids if tipo_ids else None)
            else:
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(self.central_area, 'Tipo no soportado',
                             f'El tipo de informe "{tipo_informe}" no está implementado.')
                return

            # GUARDAR ESTADO
            self.current_report_data = report_data

            try:
                self._update_export_button_state()
            except Exception:
                pass

            # Renderizar
            self._render_report(report_data)

            # Restaurar foco al área de informes
            try:
                self.cb_tipo_informe.focus_set()
            except Exception:
                try:
                    self.focus_set()
                except Exception:
                    pass

        except Exception:
            import logging
            logging.exception('Error generando informe')

    def _render_report(self, report_data: dict):
        try:
            formatter = FormatterService()

            try:
                self.result_textbox.delete('1.0', 'end')
            except Exception:
                pass

            # Check for special display formats
            display_format = report_data.get('display_format')
            if display_format == 'justified_list':
                self._render_justified_list(report_data)
                return

            # Title
            self.result_textbox.insert('end', f"{report_data.get('title', '')}\n")

            # Metadata: generated_at and range
            generated_at = report_data.get('generated_at')
            if generated_at:
                try:
                    self.result_textbox.insert('end', f"Generado: {formatter.format_fecha(generated_at)}\n")
                except Exception:
                    try:
                        self.result_textbox.insert('end', f"Generado: {generated_at}\n")
                    except Exception:
                        pass

            rng = report_data.get('range', {})
            if rng:
                start = rng.get('start', '')
                end = rng.get('end', '')
                self.result_textbox.insert('end', f"Rango: {start} → {end}\n\n")

            # Iterate sections
            for section in report_data.get('sections', []) or []:
                sec_type = section.get('type')

                # Summary section
                if sec_type == 'summary':
                    headers = section.get('headers', [])
                    rows = section.get('rows', [])
                    money_columns = section.get('money_columns', []) or []

                    self.result_textbox.insert('end', '-' * 40 + "\n")
                    if headers and rows:
                        vals = rows[0]
                        for col_index, header in enumerate(headers):
                            try:
                                value = vals[col_index]
                                if col_index in money_columns and isinstance(value, (int, float)):
                                    value_fmt = formatter.format_precio(value)
                                else:
                                    value_fmt = str(value)
                            except Exception:
                                value_fmt = ''
                            self.result_textbox.insert('end', f"{header:<20} : {value_fmt}\n")
                    self.result_textbox.insert('end', "\n")

                # Table section
                elif sec_type == 'table':
                    headers = section.get('headers', [])
                    rows = section.get('rows', [])
                    money_columns = section.get('money_columns', []) or []

                    self.result_textbox.insert('end', '-' * 40 + "\n")
                    if section.get('title'):
                        self.result_textbox.insert('end', f"{section.get('title')}\n")
                    if headers:
                        self.result_textbox.insert('end', " | ".join(headers) + "\n")
                    for row in rows:
                        formatted_row = []
                        for col_index, value in enumerate(row):
                            try:
                                if col_index in money_columns and isinstance(value, (int, float)):
                                    formatted_row.append(formatter.format_precio(value))
                                else:
                                    formatted_row.append(str(value))
                            except Exception:
                                formatted_row.append(str(value))
                        self.result_textbox.insert('end', " | ".join(formatted_row) + "\n")
                    self.result_textbox.insert('end', "\n")

                # Blocks section (vertical)
                elif sec_type == 'blocks':
                    self.result_textbox.insert('end', '-' * 40 + "\n")
                    if section.get('title'):
                        self.result_textbox.insert('end', f"{section.get('title')}\n")

                    blocks = section.get('blocks', [])
                    for block in blocks:
                        block_title = block.get('title', '')
                        self.result_textbox.insert('end', f"\n{block_title}\n")
                        self.result_textbox.insert('end', '-' * 40 + "\n")

                        fields = block.get('fields', [])
                        for field in fields:
                            label = field.get('label', '')
                            value = field.get('value')
                            is_money = field.get('is_money', False)

                            if is_money and isinstance(value, (int, float)):
                                try:
                                    value_fmt = formatter.format_precio(value)
                                except Exception:
                                    value_fmt = str(value)
                            else:
                                value_fmt = str(value)

                            self.result_textbox.insert('end', f"{label:<25} : {value_fmt:>15}\n")

                        self.result_textbox.insert('end', "\n")

            # leave textbox interactive (key-filtered) so selection/copying works

        except Exception:
            logging.exception('Error renderizando informe')

    def _render_justified_list(self, report_data: dict):
        """Renderizar informe con formato de lista justificada.

        Formato:
        - Tipo (X Tickets):
        X uds ----------------------------- XX.XX€
        """
        try:
            formatter = FormatterService()

            # Leer configuración de layout
            layout_cfg = load_layout_config()
            formats_cfg = layout_cfg.get('informes', {}).get('formats', {}).get('justified_list', {})
            left_width = formats_cfg.get('left_width', 10)
            right_width = formats_cfg.get('right_width', 12)
            sep_char = formats_cfg.get('separator_char', '-')
            sep_padding = formats_cfg.get('separator_padding', 2)

            # Limpiar textbox
            try:
                self.result_textbox.delete('1.0', 'end')
            except Exception:
                pass

            # Title
            title = report_data.get('title', '')
            self.result_textbox.insert('end', f"{title}\n")
            self.result_textbox.insert('end', '=' * len(title) + "\n")

            # Metadata: fecha y hora
            generated_at = report_data.get('generated_at')
            if generated_at:
                try:
                    self.result_textbox.insert('end', f"Generado: {formatter.format_fecha(generated_at)}\n")
                except Exception:
                    self.result_textbox.insert('end', f"Generado: {generated_at}\n")

            # Rango
            rng = report_data.get('range', {})
            if rng:
                start = rng.get('start', '')
                end = rng.get('end', '')
                self.result_textbox.insert('end', f"Rango: {start} → {end}\n")

            self.result_textbox.insert('end', "\n")

            # Calcular ancho del separador basado en viewer width
            viewer_cfg = layout_cfg.get('informes', {}).get('viewer', {})
            viewer_width = viewer_cfg.get('width', 800)
            # Asumimos 8px por caracter aproximadamente
            total_chars = viewer_width // 8
            sep_width = total_chars - left_width - right_width - (sep_padding * 2) - 10  # 10 para "uds" y espacios
            sep_width = max(sep_width, 10)  # Mínimo 10 guiones

            # Renderizar items
            total_tickets = 0
            total_uds = 0
            total_euros = 0.0
            has_tickets_items = False

            display_subformat = report_data.get('display_subformat', '')
            items = report_data.get('items', [])
            item_count = len(items)
            for idx, item in enumerate(items):
                tipo_nombre = item.get('nombre', 'Sin nombre')
                tickets = item.get('tickets', 0)
                uds = item.get('uds', 0)
                euros = item.get('euros', 0.0)

                total_tickets += tickets
                total_uds += uds
                total_euros += euros
                if tickets and tickets > 0:
                    has_tickets_items = True

                # Detectar marcador de separador especial
                if tipo_nombre == '---SEPARADOR---':
                    self.result_textbox.insert('end', "\n\n")  # Doble salto antes de Ticket Medio
                    continue

                if display_subformat == 'daily':
                    # Formato compacto para Ventas Diarias: una sola línea por día
                    right_text = formatter.format_precio(euros)
                    line = f"- {tipo_nombre} ({tickets} Tickets - {uds} Uds): {right_text}\n\n"
                    self.result_textbox.insert('end', line)
                elif display_subformat == 'cajero':
                    item_tipo = item.get('tipo', '')
                    right_text = formatter.format_precio(euros)
                    if item_tipo == 'linea_cajero':
                        fecha_raw = item.get('fecha', '')
                        try:
                            from datetime import datetime as _dt
                            fecha_fmt = _dt.strptime(fecha_raw, '%Y-%m-%d').strftime('%d-%m-%Y')
                        except Exception:
                            fecha_fmt = fecha_raw
                        prev_item = items[idx - 1] if idx > 0 else None
                        if prev_item is None or prev_item.get('nombre') != tipo_nombre or prev_item.get('tipo') == 'subtotal_cajero':
                            self.result_textbox.insert('end', f"{tipo_nombre}:\n")
                        line = f"  {fecha_fmt} - {tickets} Tickets - {uds} Uds: {right_text}\n"
                        self.result_textbox.insert('end', line)
                    elif item_tipo == 'subtotal_cajero':
                        line = f"  TOTAL {tickets} Tickets - {uds} Uds: {right_text}\n\n"
                        self.result_textbox.insert('end', line)
                elif display_subformat in ('categoria', 'tipo', 'producto'):
                    item_tipo = item.get('tipo', '')
                    right_text = formatter.format_precio(euros)
                    if item_tipo == 'linea_grupo':
                        fecha_raw = item.get('fecha', '')
                        try:
                            from datetime import datetime as _dt
                            fecha_fmt = _dt.strptime(fecha_raw, '%Y-%m-%d').strftime('%d-%m-%Y')
                        except Exception:
                            fecha_fmt = fecha_raw
                        prev_item = items[idx - 1] if idx > 0 else None
                        if prev_item is None or prev_item.get('nombre') != tipo_nombre or prev_item.get('tipo') == 'subtotal_grupo':
                            self.result_textbox.insert('end', f"{tipo_nombre}:\n")
                        line = f"  {fecha_fmt} - {tickets} Tickets - {uds} Uds: {right_text}\n"
                        self.result_textbox.insert('end', line)
                    elif item_tipo == 'subtotal_grupo':
                        line = f"  TOTAL {tickets} Tickets - {uds} Uds: {right_text}\n\n"
                        self.result_textbox.insert('end', line)
                    elif item_tipo == 'total_global':
                        self.result_textbox.insert('end', f"{tipo_nombre}:\n")
                        line = f"  {tickets} Tickets - {uds} Uds: {right_text}\n"
                        self.result_textbox.insert('end', line)
                elif tickets and tickets > 0:
                    # Formato con tickets (para informes por tipo/categoría)
                    self.result_textbox.insert('end', f"- {tipo_nombre} ({tickets} Tickets):\n")
                    left_text = f"{uds} uds"
                    right_text = formatter.format_precio(euros)
                    separator = sep_char * sep_width
                    line = f"  {left_text:<{left_width}} {separator:^{sep_width}} {right_text:>{right_width}}\n"
                    self.result_textbox.insert('end', line)
                else:
                    # Formato simple sin tickets (para resumen de ventas)
                    right_text = formatter.format_precio(euros)

                    # Detectar si es Resumen de Ventas (items sin tickets)
                    is_resumen_ventas = not has_tickets_items

                    if is_resumen_ventas:
                        # Formato especial para Resumen de Ventas
                        # Doble salto antes de TOTAL y Ticket Medio
                        if tipo_nombre == 'TOTAL' or tipo_nombre == 'Ticket Medio':
                            self.result_textbox.insert('end', "\n")

                        if tipo_nombre == 'Total Tickets':
                            # Mostrar tickets sin €
                            line = f"{tipo_nombre}: {uds}\n"
                        elif tipo_nombre == 'Ticket Medio':
                            # Emoji para Ticket Medio
                            line = f"📊 {tipo_nombre}: {right_text}\n"
                        else:
                            line = f"{tipo_nombre}: {right_text}\n"
                        self.result_textbox.insert('end', line)

                        # Salto simple entre items (excepto después de doble salto)
                        if tipo_nombre not in ('TOTAL', 'Ticket Medio') and idx < item_count - 1:
                            self.result_textbox.insert('end', "\n")
                    else:
                        # Formato estándar para otros informes
                        # Línea de separador antes de TOTAL
                        if tipo_nombre == 'TOTAL':
                            self.result_textbox.insert('end', "-" * 40 + "\n")

                        if tipo_nombre == 'Total Tickets':
                            # Mostrar tickets en lugar de euros
                            line = f"{tipo_nombre:<{total_chars - right_width - 2}} {uds:>{right_width}}\n"
                        elif tipo_nombre == 'TOTAL':
                            # TOTAL con símbolo €
                            line = f"{tipo_nombre:<{total_chars - right_width - 2}} {right_text:>{right_width}}\n"
                        else:
                            line = f"{tipo_nombre:<{total_chars - right_width - 2}} {right_text:>{right_width}}\n"
                        self.result_textbox.insert('end', line)

                        # Línea separadora después (excepto antes del separador especial o último)
                        is_next_separator = (idx + 1 < item_count and items[idx + 1].get('nombre') == '---SEPARADOR---')
                        if idx < item_count - 1 and not is_next_separator:
                            self.result_textbox.insert('end', "-" * 40 + "\n")

            # Total (solo para informes con items que tienen tickets, excepto los que tienen sus propios subtotales)
            if items and has_tickets_items and display_subformat not in ('cajero', 'categoria', 'tipo', 'producto'):
                right_text = formatter.format_precio(total_euros)
                if display_subformat == 'daily':
                    self.result_textbox.insert('end', "\n")
                    self.result_textbox.insert('end', f"TOTAL ({total_tickets} Tickets - {total_uds} Uds): {right_text}\n")
                else:
                    self.result_textbox.insert('end', "\n")
                    self.result_textbox.insert('end', "-" * 50 + "\n")
                    self.result_textbox.insert('end', f"TOTAL ({total_tickets} Tickets):\n")

                    left_text = f"{total_uds} uds"
                    separator = sep_char * sep_width
                    line = f"  {left_text:<{left_width}} {separator:^{sep_width}} {right_text:>{right_width}}\n"
                    self.result_textbox.insert('end', line)

        except Exception:
            logging.exception('Error renderizando justified_list')

    def _on_filter_change(self, event=None):
        try:
            self.current_report_data = None
            self._update_export_button_state()
        except Exception:
            pass

    def _on_tipo_informe_changed(self, value=None):
        try:
            tipo = value if value is not None else None
            try:
                if not tipo:
                    tipo = self.cb_tipo_informe.get()
            except Exception:
                tipo = tipo

            tipo_lower = tipo.lower() if tipo else ""
            service = InformesService(self.db)

            # Limpiar selecciones previas
            try:
                self.tag_selector.clear()
            except Exception:
                pass

            # Si es informe de Stock: ocultar DatePickers
            try:
                if 'stock' in tipo_lower:
                    try:
                        self.lbl_desde.pack_forget()
                        self.entry_fecha_inicio.pack_forget()
                        self.lbl_hasta.pack_forget()
                        self.entry_fecha_fin.pack_forget()
                    except Exception:
                        pass
                else:
                    # Mostrar DatePickers en orden si no están visibles
                    try:
                        self.lbl_desde.pack(side='left', padx=(0, 6), after=self.cb_tipo_informe)
                        self.entry_fecha_inicio.pack(side='left', padx=(0, 12), after=self.lbl_desde)
                        self.lbl_hasta.pack(side='left', padx=(0, 6), after=self.entry_fecha_inicio)
                        self.entry_fecha_fin.pack(side='left', padx=(0, 12), after=self.lbl_hasta)
                    except Exception:
                        pass
            except Exception:
                pass

            # Configurar TagSelector según tipo
            try:
                if 'categoría' in tipo_lower or 'categoria' in tipo_lower:
                    self.tag_selector.set_search_function(lambda txt: service.buscar_categorias_dinamico(txt))
                    try:
                        self.tag_selector.search_combo.entry.configure(state='normal')
                        self.lbl_tag_hint.configure(text="Escribe para buscar categorías...")
                    except Exception:
                        pass
                elif 'tipo' in tipo_lower:
                    self.tag_selector.set_search_function(lambda txt: service.buscar_tipos_dinamico(txt))
                    try:
                        self.tag_selector.search_combo.entry.configure(state='normal')
                        self.lbl_tag_hint.configure(text="Escribe para buscar tipos...")
                    except Exception:
                        pass
                else:
                    self.tag_selector.set_search_function(None)
                    try:
                        self.tag_selector.search_combo.entry.configure(state='disabled')
                        self.lbl_tag_hint.configure(text="Selecciona un tipo de informe compatible...")
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error configurando TagSelector según tipo seleccionado')

            # Invalidar informe
            try:
                self.current_report_data = None
                self._update_export_button_state()
            except Exception:
                pass

        except Exception:
            import logging
            logging.exception('Error en _on_tipo_informe_changed')

    def _update_export_button_state(self):
        try:
            state = 'normal' if self.current_report_data else 'disabled'
            if hasattr(self, 'btn_export_csv'):
                try:
                    self.btn_export_csv.configure(state=state)
                except Exception:
                    pass
            if hasattr(self, 'btn_export_pdf'):
                try:
                    self.btn_export_pdf.configure(state=state)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_exportar_csv_click(self):
        self._exportar_informe('csv')

    def _on_exportar_pdf_click(self):
        self._exportar_informe('pdf')

    def _exportar_informe(self, formato: str):
        try:
            # Verificar que hay informe generado
            if not self.current_report_data:
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(self.central_area, 'No hay informe',
                             'Genera un informe antes de exportar.')
                return

            if formato == 'csv':
                from kool_tpv.modulos.informes.exportadores.exportador_csv_informes import ExportadorCSVInformes
                exportador = ExportadorCSVInformes()
                resultado = exportador.exportar(self.current_report_data, self.parent.winfo_toplevel())
            else:
                from kool_tpv.modulos.informes.exportadores.exportador_pdf_informes import ExportadorPDFInformes
                exportador = ExportadorPDFInformes(self.db)
                resultado = exportador.exportar(self.current_report_data, self.parent.winfo_toplevel())

        except PermissionError:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(
                self.central_area,
                "No se pudo guardar el archivo",
                "El archivo está abierto o no tienes permisos.\n"
                "Ciérralo e inténtalo de nuevo."
            )
        except Exception:
            import logging
            logging.exception('Error durante exportación del informe')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(
                self.central_area,
                "Error al exportar",
                "Ocurrió un error inesperado al generar el archivo."
            )
