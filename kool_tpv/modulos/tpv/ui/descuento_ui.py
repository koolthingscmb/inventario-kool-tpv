"""UI overlay para aplicar descuentos.

Hereda de SelectionOverlayTemplate y la adapta para descuentos.
"""
import logging
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.utils.custom_dialog import show_warning
from kool_tpv.utils.formatter_service import FormatterService


class UIDescuento(SelectionOverlayTemplate):
    """Overlay para aplicar descuentos usando plantilla base."""

    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[Callable] = None):
        """
        Args:
            view_or_action_panel: TpvView o action_panel
            db: Database instance
            on_selection_callback: Función a ejecutar al aplicar descuento
        """
        # Configurar UI personalizada
        ui_config = {
            'page_size': 12,
            # Ensure same sizing as clientes overlay
            'reserved_right': 420,
            'min_overlay_w': 360,
            'top_left': 280,
        }

        super().__init__(
            view_or_action_panel,
            db=db,
            on_selection_callback=on_selection_callback,
            ui_config=ui_config
        )

        # Personalizar título
        self.title_text = "APLICAR DESCUENTO"
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Configurar columnas para historial
        self.columns_config = [
            ("ticket", "N° Ticket", 100, "center"),
            ("fecha", "Fecha", 120, "center"),
            ("articulos", "N° Artículos", 120, "center"),
            ("total", "Total Venta", 120, "e"),
            ("descuento", "Descuento", 160, "e"),
        ]

        # Reconfigurar treeview
        try:
            if hasattr(self, 'tree') and self.tree is not None:
                self.tree.configure(columns=[c[0] for c in self.columns_config])
                for key, heading, width, anchor in self.columns_config:
                    try:
                        self.tree.heading(key, text=heading)
                        self.tree.column(key, width=width, anchor=anchor)
                    except Exception:
                        logging.exception(f'Error configurando columna {key}')
                # Configurar tag rojo
                self.tree.tag_configure('descuento_row', foreground='#ff3333')
        except Exception:
            logging.exception('Error reconfigurando tree')

        self.db = db

        # REEMPLAZAR search_entry por formulario de descuento
        try:
            # Ocultar search_entry original
            if hasattr(self, 'search_entry'):
                try:
                    self.search_entry.pack_forget()
                except Exception:
                    pass

            # Crear controles de descuento
            import tkinter as tk
            from tkinter import ttk
            import customtkinter as ctk

            # Label Importe
            lbl_importe = ctk.CTkLabel(self.search_controls_frame, text="Importe:", font=("Roboto", 16))
            lbl_importe.pack(side="left", padx=(0, 8))

            # Entry para valor
            self.valor_var = tk.StringVar(value="")
            self.entry_valor = ctk.CTkEntry(self.search_controls_frame, textvariable=self.valor_var, width=120, font=("Roboto", 16))
            self.entry_valor.pack(side="left", padx=(0, 12))

            # Combobox para tipo
            self.tipo_var = tk.StringVar(value="Directo €")
            self.combo_tipo = ttk.Combobox(self.search_controls_frame, values=["Directo €", "Porcentaje %"], state="readonly", width=18, textvariable=self.tipo_var)
            self.combo_tipo.set("Directo €")
            self.combo_tipo.pack(side="left", padx=(0, 12))

            # Bind Enter
            self.entry_valor.bind("<Return>", lambda e: self._aplicar_descuento())

            # Cambiar texto botón Aceptar → Aplicar
            if hasattr(self, 'aceptar_btn'):
                try:
                    self.aceptar_btn.configure(text="Aplicar", fg_color="#28a745", hover_color="#218838", command=self._aplicar_descuento)
                except Exception:
                    pass

            # Ocultar botón Añadir
            if hasattr(self, 'anadir_btn'):
                try:
                    self.anadir_btn.pack_forget()
                except Exception:
                    pass

        except Exception:
            logging.exception('Error creando formulario de descuento')

    def _load_and_render(self, termino: str) -> None:
        """Cargar historial de descuentos desde BD."""
        try:
            self._items = self._cargar_historial_bd()
            self._current_page = 0
            self._render_clients_page()
        except Exception:
            logging.exception('Error cargando historial')
            self._items = []
            self._render_clients_page()

    def _cargar_historial_bd(self):
        """Cargar historial desde tabla tickets."""
        query = """
            SELECT t.num_ticket, t.created_at, COUNT(tl.id) as num_articulos, 
                   t.total, t.descuento_euros, t.descuento_tipo, t.descuento_valor
            FROM tickets t
            LEFT JOIN ticket_lines tl ON t.id = tl.ticket_id
            WHERE t.descuento_euros IS NOT NULL AND t.descuento_euros > 0
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT 50
        """

        try:
            from datetime import datetime

            rows = self.db.fetch_all(query) if hasattr(self.db, 'fetch_all') else []
            items = []

            for r in rows:
                if isinstance(r, dict):
                    num_ticket = r.get('num_ticket')
                    created_at = r.get('created_at')
                    num_articulos = r.get('num_articulos')
                    total = r.get('total')
                    descuento_euros = r.get('descuento_euros')
                    descuento_tipo = r.get('descuento_tipo')
                    descuento_valor = r.get('descuento_valor')
                else:
                    num_ticket, created_at, num_articulos, total, descuento_euros, descuento_tipo, descuento_valor = r

                # Formatear fecha
                try:
                    if isinstance(created_at, str):
                        dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = created_at
                    fecha_str = dt.strftime('%d/%m/%Y')
                except:
                    fecha_str = str(created_at)

                # Formatear descuento usando instancia
                fmt = FormatterService()
                total_str = fmt.format_precio(total)
                if descuento_tipo == 'porcentaje':
                    descuento_str = f"-{descuento_valor}% ({fmt.format_precio(descuento_euros)})"
                else:
                    descuento_str = f"-{fmt.format_precio(descuento_euros)}"

                items.append({
                    'id': num_ticket,
                    'ticket': num_ticket,
                    'fecha': fecha_str,
                    'articulos': num_articulos,
                    'total': total_str,
                    'descuento': descuento_str
                })

            return items
        except Exception:
            logging.exception('Error cargando historial descuentos')
            return []

    def _render_clients_page(self):
        """Renderizar página de historial."""
        try:
            import math

            for child in list(self.tree.get_children()):
                self.tree.delete(child)

            start = self._current_page * self._page_size
            end = start + self._page_size
            page_items = (self._items or [])[start:end]

            for item in page_items:
                self.tree.insert(
                    '', 'end',
                    iid=str(item.get('id')),
                    values=(
                        item.get('ticket'),
                        item.get('fecha'),
                        item.get('articulos'),
                        item.get('total'),
                        item.get('descuento')
                    ),
                    tags=('descuento_row',)
                )

            total_pages = max(1, math.ceil(len(self._items or []) / self._page_size))
            self.page_label.configure(text=f"Página {self._current_page+1} / {total_pages}")
            self.prev_btn.configure(state=('normal' if self._current_page>0 else 'disabled'))
            self.next_btn.configure(state=('normal' if self._current_page < total_pages-1 else 'disabled'))
        except Exception:
            logging.exception('Error renderizando página')

    def _aplicar_descuento(self):
        """Validar y aplicar descuento."""
        try:
            valor_str = (self.valor_var.get() or '').strip()
            if not valor_str:
                show_warning(self.overlay, 'CAMPO VACÍO', 'Introduzca un importe')
                return

            valor_str_norm = valor_str.replace(',', '.')
            try:
                valor = Decimal(valor_str_norm)
            except (InvalidOperation, ValueError):
                show_warning(self.overlay, 'VALOR INVÁLIDO', 'Introduzca un número válido')
                return

            if valor <= 0:
                show_warning(self.overlay, 'VALOR INVÁLIDO', 'El descuento debe ser mayor que 0')
                return

            tipo_texto = self.tipo_var.get()
            if tipo_texto == 'Directo €':
                tipo = 'directo'
                euros = valor
            else:
                tipo = 'porcentaje'
                if valor > Decimal('100'):
                    show_warning(self.overlay, 'VALOR INVÁLIDO', 'El porcentaje no puede ser mayor que 100')
                    return
                euros = Decimal('0')

            # Enviar Decimals para mantener precisión en la capa de servicio
            descuento_data = {
                'tipo': tipo,
                'valor': valor,  # Decimal
                'euros': euros if tipo == 'directo' else Decimal('0.00'),
            }

            if callable(self.on_selection_callback):
                self.on_selection_callback(descuento_data)

            self.hide()

        except Exception:
            logging.exception('Error aplicando descuento')

    def show(self):
        """Override show() para dar focus al entry de valor."""
        super().show()
        try:
            self.entry_valor.focus_set()
        except Exception:
            pass


__all__ = ['UIDescuento']
