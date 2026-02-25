"""
Interfaz para edición de plantillas de impresión (headers/footers) con preview.

Proporciona:
- Selector de tipo de ticket (venta, devolucion, cierre, nivel)
- Áreas de texto para Header y Footer (CTkTextbox)
- Botones Guardar / Restaurar / Preview

La persistencia se realiza en la tabla `configuracion` usando
`INSERT OR REPLACE INTO configuracion (clave, valor)`.

El preview reutiliza los generadores reales para mantener coherencia.
"""
import logging
import re
import customtkinter as ctk
import tkinter as tk
from typing import Optional

from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator
from kool_tpv.modulos.impresion.cierre_ticket_generator import CierreTicketGenerator
from kool_tpv.modulos.impresion.nivel_ticket_generator import NivelTicketGenerator
from kool_tpv.utils.textview_dialog import show_text_viewer


class TextosPlantillaUI:
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
        self.parent = parent
        self.db = db
        self.container = ctk.CTkFrame(self.parent)

        # Generadores reales (usados para preview)
        self.venta_gen = VentaTicketGenerator()
        self.cierre_gen = CierreTicketGenerator()
        self.nivel_gen = NivelTicketGenerator()

        # Tipos soportados
        self.types = ['venta', 'devolucion', 'cierre', 'nivel']

        self._build_ui()

    def get_widget(self):
        return self.container

    def _build_ui(self):
        # Row 0: selector tipo
        lbl = ctk.CTkLabel(self.container, text='Tipo de ticket:')
        lbl.grid(row=0, column=0, sticky='w', padx=8, pady=6)

        self.var_tipo = tk.StringVar(value=self.types[0])
        self.cb_tipo = ctk.CTkComboBox(self.container, values=self.types, variable=self.var_tipo)
        self.cb_tipo.grid(row=0, column=1, columnspan=3, sticky='we', padx=8, pady=6)
        self.cb_tipo.configure(command=self._on_tipo_change)

        # Row 1: Header label + textbox
        lbl_h = ctk.CTkLabel(self.container, text='Header:')
        lbl_h.grid(row=1, column=0, sticky='nw', padx=8, pady=6)
        self.txt_header = ctk.CTkTextbox(self.container, width=800, height=120)
        self.txt_header.grid(row=1, column=1, columnspan=3, sticky='we', padx=8, pady=6)

        # Row 2: Footer label + textbox
        lbl_f = ctk.CTkLabel(self.container, text='Footer:')
        lbl_f.grid(row=2, column=0, sticky='nw', padx=8, pady=6)
        self.txt_footer = ctk.CTkTextbox(self.container, width=800, height=120)
        self.txt_footer.grid(row=2, column=1, columnspan=3, sticky='we', padx=8, pady=6)

        # Row 3: botones
        btn_save = ctk.CTkButton(self.container, text='Guardar', command=self._on_save)
        btn_save.grid(row=3, column=1, sticky='we', padx=8, pady=12)

        btn_restore = ctk.CTkButton(self.container, text='Restaurar', command=self._on_restore)
        btn_restore.grid(row=3, column=2, sticky='we', padx=8, pady=12)

        btn_preview = ctk.CTkButton(self.container, text='Preview', command=self._on_preview)
        btn_preview.grid(row=3, column=3, sticky='we', padx=8, pady=12)

        # inicializar valores
        try:
            self._load_current()
        except Exception:
            logging.exception('Error cargando plantillas iniciales en TextosPlantillaUI')

    def _on_tipo_change(self, event=None):
        # Cuando cambia el selector, recargar header/footer desde BD
        self._load_current()

    def _make_keys(self):
        t = (self.var_tipo.get() or '').strip()
        return f"ticket_header_{t}", f"ticket_footer_{t}"

    def _load_current(self):
        header_key, footer_key = self._make_keys()
        header_val = ''
        footer_val = ''
        if not self.db:
            # limpiar widgets
            try:
                self.txt_header.delete('0.0', 'end')
                self.txt_footer.delete('0.0', 'end')
            except Exception:
                pass
            return

        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (header_key,))
            if row and row[0] is not None:
                header_val = str(row[0])
        except Exception:
            logging.exception('Error leyendo header desde BD')

        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (footer_key,))
            if row and row[0] is not None:
                footer_val = str(row[0])
        except Exception:
            logging.exception('Error leyendo footer desde BD')

        try:
            self.txt_header.delete('0.0', 'end')
            self.txt_header.insert('1.0', header_val)
            self.txt_footer.delete('0.0', 'end')
            self.txt_footer.insert('1.0', footer_val)
        except Exception:
            logging.exception('Error actualizando widgets de header/footer')

    def _on_restore(self):
        # Restaurar contenido desde la BD (descartar cambios no guardados)
        self._load_current()

    def _validate_placeholders(self, text: str) -> list[str]:
        """Detecta placeholders del tipo {{name}} y devuelve los nombres
        que NO están en ALLOWED_PLACEHOLDERS. Resultado sin duplicados.
        """
        if not text:
            return []
        found = re.findall(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", text)
        invalid = set()
        for name in found:
            if name not in self.ALLOWED_PLACEHOLDERS:
                invalid.add(name)
        return list(invalid)

    def _validate_syntax(self, text: str) -> bool:
        """Validación básica de sintaxis de placeholders.

        - Cuenta '{{' vs '}}' deben coincidir.
        - Si hay '{{' pero no coinciden con el patrón {{name}} válido => False.
        """
        if not text:
            return True
        open_cnt = text.count("{{")
        close_cnt = text.count("}}")
        if open_cnt != close_cnt:
            return False
        # Contar ocurrencias válidas del patrón {{name}}
        valid_pairs = re.findall(r"\{\{\s*[A-Za-z0-9_]+\s*\}\}", text)
        if len(valid_pairs) != open_cnt:
            return False
        return True

    def _on_save(self):
        if not self.db:
            return
        header_key, footer_key = self._make_keys()
        try:
            header_text = self.txt_header.get('1.0', 'end').rstrip('\n')
            footer_text = self.txt_footer.get('1.0', 'end').rstrip('\n')

            # Validación estricta de sintaxis: llaves balanceadas y patrones válidos
            if not self._validate_syntax(header_text) or not self._validate_syntax(footer_text):
                from kool_tpv.utils.custom_dialog import show_error
                show_error(
                    self.container,
                    'Error de sintaxis',
                    'La sintaxis de placeholders es inválida.\nRevise que todas las llaves {{ }} estén correctamente cerradas.'
                )
                return

            # Validar placeholders y avisar si hay desconocidos (no bloquea)
            invalid = set()
            invalid.update(self._validate_placeholders(header_text))
            invalid.update(self._validate_placeholders(footer_text))
            if invalid:
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(
                    self.container,
                    'Placeholders desconocidos',
                    'Los siguientes placeholders no son válidos:\n' + ', '.join(sorted(invalid))
                )

            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (header_key, header_text))
            cur.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (footer_key, footer_text))
            conn.commit()

            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Guardado', 'Plantillas guardadas')
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.exception('Error guardando plantillas en BD')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar plantillas')

    def _on_preview(self):
        # Construir contexto mock
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

        t = (self.var_tipo.get() or '').strip()
        texto = ''
        try:
            # Construir configuración temporal a partir de los textbox (preview en vivo)
            header_key, footer_key = self._make_keys()
            header_text = self.txt_header.get('1.0', 'end').rstrip('\n')
            footer_text = self.txt_footer.get('1.0', 'end').rstrip('\n')
            config_preview = {header_key: header_text, footer_key: footer_text}

            # Validar placeholders y avisar si hay desconocidos (no bloquea)
            invalid = set()
            invalid.update(self._validate_placeholders(header_text))
            invalid.update(self._validate_placeholders(footer_text))
            if invalid:
                from kool_tpv.utils.custom_dialog import show_warning
                show_warning(
                    self.container,
                    'Placeholders desconocidos',
                    'Los siguientes placeholders no son válidos:\n' + ', '.join(sorted(invalid))
                )

            if t == 'venta' or t == 'devolucion':
                # Construir datos mínimos para VentaTicketGenerator
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
                if t == 'devolucion':
                    ticket_data['tipo'] = 'devolucion'
                texto = self.venta_gen.generate(config_preview, ticket_data, [], {'nombre': mock['cliente']})
            elif t == 'cierre':
                cierre_data = {'fecha': mock['fecha'], 'hora': mock['hora'], 'usuario': 'DEMO', 'cierre_id': 'C-001'}
                tickets = []
                texto = self.cierre_gen.generate(config_preview, cierre_data, tickets, totals={})
            elif t == 'nivel':
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

            # Mostrar preview en diálogo monoespaciado
            show_text_viewer(self.parent, 'Preview plantilla', texto or '')
        except Exception:
            logging.exception('Error generando preview de plantilla')
"""
Placeholder for Textos UI (TEXTOS TICKETS configuration).
Currently a stub — to be implemented later.
"""

# Minimal placeholder file — real UI will be implemented later.
