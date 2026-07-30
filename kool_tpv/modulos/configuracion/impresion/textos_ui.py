"""
TextosPlantillaUI: edición de headers/footers con visor, basada en PaginaConVisor.

Estructura: izquierda (selector + header/footer + botones) + derecha (visor)
"""
import logging
import re
import customtkinter as ctk
from typing import List

from kool_tpv.utils.templates.pagina_con_visor import PaginaConVisor
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.font_loader import get_font

from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator
from kool_tpv.modulos.impresion.cierre_ticket_generator import CierreTicketGenerator
from kool_tpv.modulos.impresion.nivel_ticket_generator import NivelTicketGenerator
from kool_tpv.utils.widgets.notificaciones import ToastWidget


class TextosPlantillaUI(PaginaConVisor):
    ALLOWED_PLACEHOLDERS = {
        "fecha",
        "hora",
        "cliente",
        "num_ticket",
        "total",
        "forma_pago",
        "nivel_anterior",
        "nivel_nuevo",
        "total_acumulado",
    }

    def __init__(self, parent, db, module_name: str = 'config'):
        # Preparar datos antes del constructor base
        self.tipos_ticket = ['venta', 'devolucion', 'cierre', 'nivel']
        self.venta_gen = VentaTicketGenerator()
        self.cierre_gen = CierreTicketGenerator()
        self.nivel_gen = NivelTicketGenerator()

        # Inicializar plantilla (esto llamará a _build_header/_build_grid/_build_footer)
        super().__init__(parent, db=db, module_name='config')

        # Breadcrumb personalizado
        try:
            self.breadcrumb_text = "CONFIG > IMPRESIÓN > TEXTOS"
        except Exception:
            pass

    def _build_header(self):
        """Minimal header: only the tipo combobox (no nav list)."""
        try:
            # Clear any existing widgets in header
            try:
                for c in list(self.header.winfo_children()):
                    try:
                        c.destroy()
                    except Exception:
                        pass
            except Exception:
                pass

            header_content = ctk.CTkFrame(self.header, fg_color='transparent')
            header_content.pack(fill='x', padx=12, pady=(6, 6))

            ctk.CTkLabel(
                header_content,
                text='TIPO DE TICKET:',
                font=get_font('label', module='config'),
                text_color=self.colors.get('text')
            ).pack(side='left', padx=(0, 12))

            self.combo_tipo = ctk.CTkComboBox(
                header_content,
                values=self.tipos_ticket,
                width=200,
                fg_color=self.colors.get('background'),
                text_color=self.colors.get('text'),
                border_color=self.colors.get('primary'),
                button_color=self.colors.get('primary'),
                button_hover_color=self.colors.get('secondary'),
                dropdown_fg_color=self.colors.get('background'),
                dropdown_text_color=self.colors.get('text'),
                font=get_font('entry', module='config'),
                command=self._on_tipo_change
            )
            try:
                self.combo_tipo.set(self.tipos_ticket[0])
            except Exception:
                pass
            self.combo_tipo.pack(side='left')
            self.label_seleccionado = ctk.CTkLabel(
                header_content,
                text='Seleccionado ticket de VENTA',
                font=get_font('label', module='config'),
                text_color=self.colors.get('accent')
            )
            self.label_seleccionado.pack(side='left', padx=(20, 0))
        except Exception:
            logging.exception('Error building minimal header in TextosPlantillaUI')

    def _build_grid(self):
        """Grid izquierdo: Entry header + Entry footer."""
        # Remove any existing grid/scrollable nav content created by base
        try:
            if hasattr(self, 'grid_scroll') and self.grid_scroll is not None:
                try:
                    self.grid_scroll.pack_forget()
                except Exception:
                    pass
                try:
                    self.grid_scroll.destroy()
                except Exception:
                    pass
        except Exception:
            pass

        # Frame contenedor dentro de left_container
        grid_content = ctk.CTkFrame(self.left_container, fg_color='transparent')
        grid_content.pack(fill='both', expand=True, padx=12, pady=(6, 6))

        # Label + Entry Header
        ctk.CTkLabel(
            grid_content,
            text='HEADER:',
            font=get_font('label', module='config'),
            text_color=self.colors.get('text')
        ).pack(anchor='w', pady=(0, 6))

        self.entry_header = ctk.CTkTextbox(
            grid_content,
            width=400,
            height=120,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2,
            font=get_font('entry', module='config')
        )
        self.entry_header.pack(fill='both', expand=True, pady=(0, 20))

        # Label + Entry Footer
        ctk.CTkLabel(
            grid_content,
            text='FOOTER:',
            font=get_font('label', module='config'),
            text_color=self.colors.get('text')
        ).pack(anchor='w', pady=(0, 6))

        self.entry_footer = ctk.CTkTextbox(
            grid_content,
            width=400,
            height=120,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2,
            font=get_font('entry', module='config')
        )
        self.entry_footer.pack(fill='both', expand=True)

        # Label + Entry Cuidado Camisetas (solo para venta)
        self.label_camisetas = ctk.CTkLabel(
            grid_content,
            text='CUIDADO CAMISETAS (aparece solo si hay camisetas):',
            font=get_font('label', module='config'),
            text_color=self.colors.get('text')
        )
        self.entry_camisetas = ctk.CTkTextbox(
            grid_content,
            width=400,
            height=100,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2,
            font=get_font('entry', module='config')
        )
        # No empaquetar aún, se muestra/oculta según el tipo

        # Label + Entry Sin Recompensa (solo para nivel)
        self.label_sin_recompensa = ctk.CTkLabel(
            grid_content,
            text='SIN RECOMPENSA (aparece cuando no hay recompensa):',
            font=get_font('label', module='config'),
            text_color=self.colors.get('text')
        )
        self.entry_sin_recompensa = ctk.CTkTextbox(
            grid_content,
            width=400,
            height=100,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('primary'),
            border_width=2,
            font=get_font('entry', module='config')
        )
        # No empaquetar aún, se muestra/oculta según el tipo

        # Cargar valores iniciales
        try:
            self._cargar_valores()
        except Exception:
            logging.exception('Error cargando valores iniciales en TextosPlantillaUI')

    def _build_footer(self):
        """Footer: botones Guardar y Mostrar."""
        self.btn_guardar = create_action_button(
            self.footer,
            'guardar',
            self._on_guardar
        )
        self.btn_guardar.pack(side='left', padx=8)

        self.btn_mostrar = create_action_button(
            self.footer,
            'mostrar',
            self._on_mostrar
        )
        self.btn_mostrar.pack(side='left', padx=8)

    # --- Auxiliares funcionales solicitados ---
    def _on_tipo_change(self, event=None):
        """Al cambiar tipo, recargar header/footer desde BD."""
        self._cargar_valores()
        try:
            tipo_texto = self.combo_tipo.get().upper()
            try:
                self.label_seleccionado.configure(
                    text=f'Seleccionado ticket de {tipo_texto}'
                )
            except Exception:
                pass
        except Exception:
            logging.exception('Error actualizando label_seleccionado en _on_tipo_change')

    def _cargar_valores(self):
        """Cargar header, footer y cuidado camisetas desde BD según tipo seleccionado."""
        tipo = self.combo_tipo.get()
        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"

        header_val = ""
        footer_val = ""
        camisetas_val = ""
        sin_recompensa_val = ""

        if self.db:
            try:
                row = self.db.fetch_one(
                    "SELECT valor FROM configuracion WHERE clave = ?",
                    (header_key,)
                )
                if row and row[0]:
                    header_val = str(row[0])
            except Exception:
                pass

            try:
                row = self.db.fetch_one(
                    "SELECT valor FROM configuracion WHERE clave = ?",
                    (footer_key,)
                )
                if row and row[0]:
                    footer_val = str(row[0])
            except Exception:
                pass

            try:
                row = self.db.fetch_one(
                    "SELECT valor FROM configuracion WHERE clave = ?",
                    ('ticket_cuidado_camisetas',)
                )
                if row and row[0]:
                    camisetas_val = str(row[0])
            except Exception:
                pass

            try:
                row = self.db.fetch_one(
                    "SELECT valor FROM configuracion WHERE clave = ?",
                    ('ticket_nivel_sin_recompensa',)
                )
                if row and row[0]:
                    sin_recompensa_val = str(row[0])
            except Exception:
                pass

        try:
            self.entry_header.delete('1.0', 'end')
            self.entry_header.insert('1.0', header_val)

            self.entry_footer.delete('1.0', 'end')
            self.entry_footer.insert('1.0', footer_val)

            self.entry_camisetas.delete('1.0', 'end')
            self.entry_camisetas.insert('1.0', camisetas_val)

            self.entry_sin_recompensa.delete('1.0', 'end')
            self.entry_sin_recompensa.insert('1.0', sin_recompensa_val)
        except Exception:
            logging.exception('Error actualizando widgets en _cargar_valores')

        # Mostrar/ocultar campo camisetas según tipo
        try:
            if tipo == 'venta':
                self.label_camisetas.pack(anchor='w', pady=(20, 6))
                self.entry_camisetas.pack(fill='both', expand=True, pady=(0, 0))
            else:
                self.label_camisetas.pack_forget()
                self.entry_camisetas.pack_forget()
        except Exception:
            pass

        # Mostrar/ocultar campo sin_recompensa según tipo
        try:
            if tipo == 'nivel':
                self.label_sin_recompensa.pack(anchor='w', pady=(20, 6))
                self.entry_sin_recompensa.pack(fill='both', expand=True, pady=(0, 0))
            else:
                self.label_sin_recompensa.pack_forget()
                self.entry_sin_recompensa.pack_forget()
        except Exception:
            pass

    def _on_guardar(self):
        """Guardar header, footer, cuidado camisetas y sin_recompensa en BD."""
        header_text = self.entry_header.get('1.0', 'end').rstrip('\n')
        footer_text = self.entry_footer.get('1.0', 'end').rstrip('\n')
        camisetas_text = self.entry_camisetas.get('1.0', 'end').rstrip('\n')
        sin_recompensa_text = self.entry_sin_recompensa.get('1.0', 'end').rstrip('\n')

        if not header_text and not footer_text and not camisetas_text and not sin_recompensa_text:
            from kool_tpv.utils.widgets.notificaciones import show_warning
            show_warning(self.container, 'No hay información para guardar')
            return

        tipo = self.combo_tipo.get()
        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"

        try:
            if header_text:
                self.db.execute_query(
                    "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                    (header_key, header_text)
                )

            if footer_text:
                self.db.execute_query(
                    "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                    (footer_key, footer_text)
                )

            # Guardar cuidado camisetas (clave global, no por tipo)
            self.db.execute_query(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                ('ticket_cuidado_camisetas', camisetas_text)
            )

            # Guardar sin_recompensa (clave global, no por tipo)
            self.db.execute_query(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                ('ticket_nivel_sin_recompensa', sin_recompensa_text)
            )

            ToastWidget.show(self.parent, 'Textos guardados', tipo='success')
        except Exception:
            logging.exception('Error guardando textos')
            from kool_tpv.utils.dialogs import show_error
            show_error(self.container, 'Error', 'No se pudo guardar')

    def _on_mostrar(self):
        """Generar preview y mostrar en visor."""
        tipo = self.combo_tipo.get()
        header_text = self.entry_header.get('1.0', 'end').rstrip('\n')
        footer_text = self.entry_footer.get('1.0', 'end').rstrip('\n')
        camisetas_text = self.entry_camisetas.get('1.0', 'end').rstrip('\n')
        sin_recompensa_text = self.entry_sin_recompensa.get('1.0', 'end').rstrip('\n')

        header_key = f"ticket_header_{tipo}"
        footer_key = f"ticket_footer_{tipo}"

        config_preview = {
            header_key: header_text,
            footer_key: footer_text
        }

        # Incluir texto de camisetas en el preview de venta
        if tipo == 'venta' and camisetas_text:
            config_preview['ticket_cuidado_camisetas'] = camisetas_text

        # Incluir texto sin_recompensa en el preview de nivel
        if tipo == 'nivel' and sin_recompensa_text:
            config_preview['ticket_nivel_sin_recompensa'] = sin_recompensa_text

        # Contexto mock
        mock = {
            'fecha': '2026-01-01',
            'hora': '12:00',
            'cliente': 'CLIENTE DEMO',
            'num_ticket': '1234',
            'total': '99.99',
            'forma_pago': 'Efectivo',
            'nivel_anterior': 'Recluta',
            'nivel_nuevo': 'Mercenario',
            'total_acumulado': '150.00'
        }

        texto = ''
        try:
            if tipo == 'venta' or tipo == 'devolucion':
                ticket_data = {
                    'fecha': mock['fecha'],
                    'hora': mock['hora'],
                    'cajero': 'DEMO',
                    'num_ticket': mock['num_ticket'],
                    'subtotal': mock['total'],
                    'iva_desglose': {},
                    'total': mock['total'],
                    'forma_pago': mock['forma_pago'],
                    'entregado': mock['total'],
                    'cambio': '0.00'
                }
                if tipo == 'devolucion':
                    ticket_data['tipo'] = 'devolucion'
                texto = self.venta_gen.generate(config_preview, ticket_data, [], {'nombre': mock['cliente']})
            elif tipo == 'cierre':
                cierre_data = {
                    'fecha': mock['fecha'],
                    'hora': mock['hora'],
                    'usuario': 'DEMO',
                    'cierre_id': 'C-001'
                }
                texto = self.cierre_gen.generate(config_preview, cierre_data, [], totals={})
            elif tipo == 'nivel':
                nivel_data = {
                    'fecha': mock['fecha'],
                    'hora': mock['hora'],
                    'cliente': mock['cliente'],
                    'nivel_anterior': mock['nivel_anterior'],
                    'nivel_nuevo': mock['nivel_nuevo'],
                    'grafismo': '',
                    'total_acumulado': mock['total_acumulado']
                }
                texto = self.nivel_gen.generate(config_preview, nivel_data)

            self.update_visor(texto or 'Sin contenido')
        except Exception:
            logging.exception('Error generando preview')
            self.update_visor('Error generando preview')

    # --- Mantener validación de placeholders/sintaxis ---
    def _validate_placeholders(self, text: str) -> List[str]:
        if not text:
            return []
        found = re.findall(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", text)
        invalid = set()
        for name in found:
            if name not in self.ALLOWED_PLACEHOLDERS:
                invalid.add(name)
        return list(invalid)

    def _validate_syntax(self, text: str) -> bool:
        if not text:
            return True

        open_count = text.count("{{")
        close_count = text.count("}}")
        if open_count != close_count:
            return False

        balance = 0
        i = 0
        while i < len(text):
            if text[i:i+2] == "{{":
                balance += 1
                i += 2
                continue
            elif text[i:i+2] == "}}":
                balance -= 1
                if balance < 0:
                    return False
                i += 2
                continue
            i += 1

        return balance == 0
