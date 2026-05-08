from __future__ import annotations

from kool_tpv.modulos.impresion.venta_ticket_generator import VentaTicketGenerator
from kool_tpv.modulos.impresion.devolucion_ticket_generator import DevolucionTicketGenerator
from kool_tpv.modulos.impresion.venta_fidelizacion_ticket_generator import VentaFidelizacionTicketGenerator
from kool_tpv.modulos.impresion.descuento_ticket_generator import DescuentoTicketGenerator
from kool_tpv.modulos.impresion.nivel_ticket_generator import NivelTicketGenerator
from kool_tpv.modulos.impresion.cierre_ticket_generator import CierreTicketGenerator
from kool_tpv.modulos.impresion.ticket_type import TicketType
import logging
from typing import Optional
from pathlib import Path

# Optional ESC/POS support (import at runtime)
try:
    from kool_tpv.modulos.impresion.escpos.escpos_renderer import EscPosRenderer
    from kool_tpv.modulos.impresion.escpos.printer_adapter_windows import WindowsPrinterAdapter
except Exception:
    EscPosRenderer = None  # type: ignore
    WindowsPrinterAdapter = None  # type: ignore


class ImpresoraService:
    def __init__(self, db=None, imprimir_en_consola=True, verbose=False, modo_impresion: str = "texto", debug_dump: bool = False, dump_directory: Optional[Path] = None):
        self.db = db
        self.imprimir_en_consola = imprimir_en_consola
        self.verbose = verbose
        self.ticket_generator = VentaTicketGenerator()
        self.devolucion_ticket_generator = DevolucionTicketGenerator()
        self.venta_fidelizacion_ticket_generator = VentaFidelizacionTicketGenerator()
        self.descuento_ticket_generator = DescuentoTicketGenerator()
        self.nivel_ticket_generator = NivelTicketGenerator()
        self.cierre_ticket_generator = CierreTicketGenerator()
        self.logger = logging.getLogger(__name__)
        # modo_impresion: 'texto' (simulación/actual) o 'escpos' (envío ESC/POS)
        if modo_impresion not in ("texto", "escpos"):
            raise ValueError("modo_impresion must be 'texto' or 'escpos'")
        self.modo_impresion = modo_impresion

        # Inicializar componentes ESC/POS si están disponibles y si se pide modo escpos
        # No anotar con tipos que podrían no existir en tiempo de ejecución
        self.esc_renderer = None
        self.printer_adapter = None
        if modo_impresion == "escpos":
            if EscPosRenderer is not None:
                try:
                    # Pasar opciones de debug al renderer si se solicitan
                    self.esc_renderer = EscPosRenderer(debug_dump=bool(debug_dump), dump_directory=dump_directory)
                except Exception:
                    self.logger.exception("No se pudo instanciar EscPosRenderer")
            else:
                self.logger.warning("EscPosRenderer no disponible en este entorno")

            if WindowsPrinterAdapter is not None:
                try:
                    self.printer_adapter = WindowsPrinterAdapter()
                except Exception:
                    self.logger.exception("No se pudo instanciar WindowsPrinterAdapter")
            else:
                self.logger.warning("WindowsPrinterAdapter no disponible en este entorno")
        # Cargar configuración de ticket desde BD
        self.config = self._load_config_from_db()
        # Inicializar atributos de logo a partir de config
        try:
            self.logo_enabled = True if str(self.config.get('logo_enabled', '0')) == '1' else False
        except Exception:
            self.logo_enabled = False
        try:
            self.logo_filename = str(self.config.get('logo_filename', '') or '')
        except Exception:
            self.logo_filename = ''

    def _load_config_from_db(self):
        """Cargar configuración del ticket desde tabla configuracion.

        Claves esperadas:
        - ticket_nombre_negocio
        - ticket_direccion
        - ticket_nif
        - ticket_pie_texto

        Returns:
            dict con configuración (usa fallback si no existe en BD)
        """
        # Valores por defecto (fallback)
        config = {
            'nombre_negocio': 'KOOL DREAMS',
            'direccion': 'C/ Ejemplo 123, Ciudad',
            'nif': 'NIF: 00000000A',
            'pie_texto': 'Gracias por su compra'
        }

        # Valores adicionales por defecto para logo
        config.setdefault('logo_enabled', '0')
        config.setdefault('logo_filename', '')

        if self.db is None:
            # establecer atributos internos para logo
            self.logo_enabled = False
            self.logo_filename = ''
            return config

        # Leer de BD
        try:
            claves = ['ticket_nombre_negocio', 'ticket_direccion', 'ticket_nif', 'ticket_pie_texto']
            mapeo = {
                'ticket_nombre_negocio': 'nombre_negocio',
                'ticket_direccion': 'direccion',
                'ticket_nif': 'nif',
                'ticket_pie_texto': 'pie_texto'
            }

            # Añadir claves para logo
            claves = claves + ['logo_enabled', 'logo_filename']
            mapeo.update({'logo_enabled': 'logo_enabled', 'logo_filename': 'logo_filename'})

            for clave_bd in claves:
                try:
                    row = self.db.fetch_one(
                        "SELECT valor FROM configuracion WHERE clave = ?",
                        (clave_bd,)
                    )
                    if row and row[0]:
                        clave_config = mapeo[clave_bd]
                        config[clave_config] = row[0]
                except Exception:
                    pass  # Usar fallback para esta clave
        except Exception:
            logging.exception('Error cargando configuración de ticket desde BD')

        # Cargar qr_enabled
        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", ('qr_enabled',))
            if row and row[0]:
                config['qr_enabled'] = (row[0] == '1')
            else:
                config['qr_enabled'] = False
        except Exception:
            config['qr_enabled'] = False

        # Cargar qr_url
        try:
            row = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", ('qr_url',))
            if row and row[0]:
                config['qr_url'] = row[0]
            else:
                config['qr_url'] = ''
        except Exception:
            config['qr_url'] = ''

        # Cargar headers y footers dinámicos
        try:
            rows = self.db.fetch_all(
                "SELECT clave, valor FROM configuracion WHERE clave LIKE 'ticket_header_%' OR clave LIKE 'ticket_footer_%'"
            )
            if rows:
                for row in rows:
                    clave = row[0]
                    valor = row[1]
                    if clave and valor:
                        config[clave] = valor
        except Exception:
            logging.exception('Error cargando headers/footers dinámicos')

        return config

    def imprimir_ticket(self, ticket_data, items, cliente_data=None, printer_name: Optional[str] = None):
        """Imprime un ticket en el modo configurado.

        - En `texto` se mantiene la conducta actual (simulación por consola).
        - En `escpos` se renderiza a ESC/POS y se intenta enviar a la impresora
          mediante el adapter Windows (si está disponible).
        """
        texto = self.ticket_generator.generate(self.config, ticket_data, items, cliente_data)

        # Reutilizar la lógica común de impresión (texto/escpos/simulación)
        return self._imprimir_texto_generico(texto, {'num_ticket': ticket_data.get('num_ticket')}, printer_name)
# Servicio para gestión de la impresora y envío de trabajos de impresión
# Placeholder para integración con impresoras térmicas u otros dispositivos.

    def generar_ticket_desde_id(self, ticket_id: int) -> str:
        """Generar ticket completo desde ID (reconstruir desde BD).

        Args:
            ticket_id: ID del ticket

        Returns:
            Texto del ticket formateado, o None si no existe
        """
        # Debug: mostrar estado de la configuración en memoria antes de generar
        try:
            logging.info(f"DEBUG CONFIG KEYS: {list(self.config.keys())}")
            logging.info(f"DEBUG ticket_header_venta: {self.config.get('ticket_header_venta')}")
            logging.info(f"DEBUG ticket_footer_venta: {self.config.get('ticket_footer_venta')}")
        except Exception:
            pass

        try:
            from decimal import Decimal

            # Prefer the DB adapter for interpreting DB values. Treat
            # integral numerics (int, float.is_integer(), Decimal integral,
            # or digit-only strings) as céntimos and convert them to euros
            # using `read_from_db`. For non-integral values parse as euros.
            from kool_tpv.base_datos.money_adapter import read_from_db

            def _parse_money_db(v):
                try:
                    # None -> zero
                    if v is None:
                        return Decimal('0')

                    # ints -> céntimos
                    if isinstance(v, int):
                        return read_from_db(v)

                    # strings: digit-only -> céntimos, else parse as Decimal euros
                    if isinstance(v, str):
                        if v.isdigit():
                            return read_from_db(int(v))
                        try:
                            return Decimal(v)
                        except Exception:
                            return Decimal(str(v))

                    # floats: if integral treat as céntimos, else parse as euros
                    if isinstance(v, float):
                        if float(v).is_integer():
                            return read_from_db(int(v))
                        return Decimal(str(v))

                    # Decimal: if it has no fractional part, treat as céntimos
                    if isinstance(v, Decimal):
                        if v == v.to_integral_value():
                            return read_from_db(int(v))
                        return v

                    # Fallback: attempt Decimal conversion
                    return Decimal(v)
                except Exception:
                    try:
                        return Decimal(str(v))
                    except Exception:
                        return Decimal('0')

            # Obtener ticket
            ticket_row = self.db.fetch_one(
                """SELECT id, num_ticket, created_at, cajero, cliente, cliente_id,
                          total, forma_pago, importe_efectivo, importe_tarjeta,
                          tesoro_ganado, tesoro_gastado
                   FROM tickets WHERE id = ?""",
                (ticket_id,)
            )

            if not ticket_row:
                return None

            # if row_text and row_text[0]:
            #     return row_text[0]

            # Obtener líneas (incluimos line_tipo para detectar devoluciones)
            lines = self.db.fetch_all(
                "SELECT sku, nombre, cantidad, precio, iva, line_tipo FROM ticket_lines WHERE ticket_id = ?",
                (ticket_id,)
            )

            # Construir items
            items = []
            subtotal_calc = Decimal('0')
            iva_desglose = {}

            # Acumular por tipo y respetar devoluciones (signo negativo)
            base_by_type = {}
            gross_by_type = {}
            for line in lines:
                cantidad = int(float(line[2])) if line[2] else 0
                # Forzar conversión determinista: tratar el valor en BD siempre
                # como céntimos y convertir a euros aquí. Esto evita ambigüedad
                # y asegura la ruta de impresión muestra euros.
                try:
                    from kool_tpv.base_datos.money_adapter import read_from_db
                    if line[3] is None:
                        precio = Decimal('0')
                    else:
                        # Asegurar int (si viene como str/numeric), usar int()
                        precio_cents = int(line[3])
                        precio = read_from_db(precio_cents)
                except Exception:
                    # Fallback robusto: intentar parsear y convertir
                    try:
                        precio_cents = int(line[3])
                        from kool_tpv.base_datos.money_adapter import read_from_db as _r
                        precio = _r(precio_cents)
                    except Exception:
                        precio = _parse_money_db(line[3]) if line[3] is not None else Decimal('0')
                tipo_iva = int(float(line[4])) if line[4] else 21
                line_tipo = str(line[5]) if len(line) > 5 and line[5] is not None else 'venta'

                sign = Decimal('-1') if line_tipo == 'devolucion' else Decimal('1')

                # Calcular total de la línea (con signo) y base imponible
                total_linea = (precio * cantidad) * sign
                divisor = (Decimal('1') + (Decimal(tipo_iva) / Decimal('100')))
                try:
                    base = (total_linea / divisor)
                except Exception:
                    base = Decimal('0')
                cuota_iva = total_linea - base

                subtotal_calc += base

                # Acumular por tipo
                base_by_type[tipo_iva] = base_by_type.get(tipo_iva, Decimal('0')) + base
                gross_by_type[tipo_iva] = gross_by_type.get(tipo_iva, Decimal('0')) + total_linea

                # Acumular IVA por tipo (cuota_iva puede ser negativo for devoluciones)
                if tipo_iva not in iva_desglose:
                    iva_desglose[tipo_iva] = Decimal('0')
                iva_desglose[tipo_iva] += cuota_iva

                try:
                    logging.info("TRACE_DB_LINE sku=%s raw_precio=%r parsed_precio=%r total_linea=%r cantidad=%s", line[0], line[3], precio, total_linea, cantidad)
                except Exception:
                    logging.info("TRACE_DB_LINE could not log line details")


                items.append({
                    'sku': line[0],
                    'nombre': line[1],
                    'cantidad': cantidad,
                    # Keep Decimal values to preserve precision and avoid
                    # accidental interpretation as euros when floats are used.
                    'pvp': precio,
                    'tipo_iva': tipo_iva,
                    'line_tipo': line_tipo,
                    'total': total_linea,
                })

            # Separar fecha y hora
            fecha_completa = ticket_row[2] or ''
            if ' ' in fecha_completa:
                fecha, hora = fecha_completa.split(' ', 1)
            else:
                fecha = fecha_completa
                hora = ''

            # Si hay tesoro gastado, prorratearlo entre tipos de IVA y ajustar bases/IVA
            try:
                tesoro_gastado = _parse_money_db(ticket_row[11]) if ticket_row[11] is not None else Decimal('0')
            except Exception:
                tesoro_gastado = Decimal('0')

            # Calcular entregado y cambio
            total = _parse_money_db(ticket_row[6])
            forma_pago = ticket_row[7]
            importe_efectivo = _parse_money_db(ticket_row[8]) if ticket_row[8] is not None else Decimal('0')
            importe_tarjeta = _parse_money_db(ticket_row[9]) if ticket_row[9] is not None else Decimal('0')
            if tesoro_gastado and tesoro_gastado != 0 and sum(gross_by_type.values()) != 0:
                total_gross = sum(gross_by_type.values())
                try:
                    factor_pago = (total_gross - tesoro_gastado) / total_gross
                except Exception:
                    factor_pago = Decimal('1')
                # Recalcular bases e IVA por tipo
                # Detectar si el ticket es una devolución "pura" (solo importes negativos).
                is_pure_devolucion = False
                try:
                    vals = list(gross_by_type.values())
                    # Considerar "pura" si hay al menos un negativo y no hay positivos
                    is_pure_devolucion = any(v < 0 for v in vals) and not any(v > 0 for v in vals)
                except Exception:
                    is_pure_devolucion = False

                iva_desglose_new = {}
                subtotal_new = Decimal('0')
                for tipo, gross_orig in gross_by_type.items():
                    tipo_pct = Decimal(tipo)
                    proporcion = (gross_orig / total_gross) if total_gross != 0 else Decimal('0')
                    descuento_para_tipo = tesoro_gastado * proporcion
                    nueva_gross = gross_orig - descuento_para_tipo
                    # Si el ticket ES una devolución pura, conservar el signo (permitir negativa).
                    # En tickets normales, seguir forzando a 0 para evitar bases negativas.
                    if (not is_pure_devolucion) and nueva_gross < Decimal('0'):
                        nueva_gross = Decimal('0')
                    nueva_base = nueva_gross / (Decimal('1') + (tipo_pct / Decimal('100')))
                    nueva_cuota = nueva_gross - nueva_base
                    iva_desglose_new[int(tipo)] = nueva_cuota
                    subtotal_new += nueva_base
                iva_desglose = iva_desglose_new
                subtotal_calc = subtotal_new

            if forma_pago and forma_pago.lower() == 'mixto':
                entregado = importe_efectivo + importe_tarjeta
                cambio = Decimal('0')
            elif forma_pago and forma_pago.lower() == 'tarjeta':
                entregado = total
                cambio = Decimal('0')
            else:  # Efectivo
                entregado = importe_efectivo if importe_efectivo > 0 else total
                cambio = entregado - total if entregado > total else Decimal('0')

            # Construir ticket_data (usar Decimal para todos los importes)
            ticket_data = {
                'num_ticket': ticket_row[1],
                'fecha': fecha,
                'hora': hora,
                'cajero': ticket_row[3],
                'subtotal': subtotal_calc,
                'iva_desglose': iva_desglose,
                'total': total,
                'forma_pago': forma_pago,
                'entregado': entregado,
                'cambio': cambio,
                'importe_efectivo': importe_efectivo,
                'importe_tarjeta': importe_tarjeta,
            }

            # Cliente si existe
            cliente_data = None
            if ticket_row[5]:  # cliente_id
                cliente_row = self.db.fetch_one(
                    """SELECT c.id, c.nombre, c.tesoro_total, c.id_nivel,
                              n.nombre_nivel, n.grafismo_nivel, n.level
                       FROM clientes c
                       LEFT JOIN niveles_fidelidad n ON c.id_nivel = n.id
                       WHERE c.id = ?""",
                    (ticket_row[5],)
                )

                if cliente_row:
                    # Reconstruir tesoro_data (usar los parseos ya definidos)
                    tesoro_gastado = _parse_money_db(ticket_row[11]) if ticket_row[11] is not None else Decimal('0')
                    tesoro_ganado = _parse_money_db(ticket_row[10]) if ticket_row[10] is not None else Decimal('0')
                    tesoro_total_actual = _parse_money_db(cliente_row[2]) if cliente_row[2] is not None else Decimal('0')
                    tesoro_antes = tesoro_total_actual - tesoro_ganado + tesoro_gastado
                    tesoro_acumulado = tesoro_antes - tesoro_gastado

                    cliente_data = {
                        'id': cliente_row[0],
                        'nombre': cliente_row[1],
                        'nivel': cliente_row[4],  # ✅ key correcta
                        'grafismo': cliente_row[5],  # ✅ key correcta
                        'level_num': cliente_row[6]  # ✅ key correcta
                    }

                    # Leer motivo desde points_movements (si existe) para distinguir
                    # 'gasto' (canje) vs 'devolucion' (anulación de puntos)
                    motivo_val = None
                    try:
                        row_m = self.db.fetch_one(
                            "SELECT motivo FROM points_movements WHERE ticket_id = ? ORDER BY id DESC LIMIT 1",
                            (ticket_id,)
                        )
                        if row_m and row_m[0]:
                            motivo_val = str(row_m[0])
                    except Exception:
                        motivo_val = None

                    ticket_data['tesoro_data'] = {
                        'gastado': tesoro_gastado,  # ✅ key correcta
                        'antes': tesoro_antes,
                        'acumulado': tesoro_acumulado,  # ✅ key correcta
                        'ganado': tesoro_ganado,  # ✅ key correcta
                        'total': tesoro_total_actual,  # ✅ key correcta
                        'motivo': motivo_val,
                    }

            # No prints here: generador recibe `items` con `Decimal` en pvp/total

            # Generar ticket
            ticket_text = self.ticket_generator.generate(self.config, ticket_data, items, cliente_data)

            # IMPRIME EN CONSOLA si está configurado
            if self.imprimir_en_consola and ticket_text:
                print("\n" + "="*50)
                print(ticket_text)
                print("="*50 + "\n")

            return ticket_text

        except Exception:
            logging.exception(f'Error generando ticket desde ID {ticket_id}')
            return None

    def _imprimir_texto_generico(self, texto: str, meta: dict, printer_name: Optional[str] = None):
        """Lógica común para imprimir un texto ya generado.

        - Maneja la simulación (logger)
        - Soporta `modo_impresion` == 'texto' o 'escpos'
        - Valida `printer_name` consultando la BD como fallback
        - Prepara `logo_path` igual que en el comportamiento anterior
        - Renderiza con `EscPosRenderer` y envía con `WindowsPrinterAdapter`

        Args:
            texto: contenido del ticket ya formateado
            meta: diccionario con metadatos (ej. {'num_ticket': ...}) usado solo para logs
            printer_name: nombre de impresora opcional
        """
        # Simulación mediante logging
        if self.imprimir_en_consola:
            sep = "=" * 50
            self.logger.info("%s", sep)
            self.logger.info(" SIMULACIÓN IMPRESIÓN TICKET ")
            self.logger.info("%s", sep)
            self.logger.info("\n%s", texto)
            self.logger.info("%s", sep)

        # Comportamiento según modo
        if self.modo_impresion == "texto":
            self.logger.info("Ticket impreso (simulado) num_ticket=%s", meta.get("num_ticket"))
            return

        # modo escpos
        if self.modo_impresion == "escpos":
            if self.esc_renderer is None:
                self.logger.error("Modo 'escpos' solicitado pero EscPosRenderer no está disponible")
                return
            if self.printer_adapter is None:
                self.logger.error("Modo 'escpos' solicitado pero WindowsPrinterAdapter no está disponible")
                return

            # Validar nombre de impresora: NO permitir vacío. Si no se pasó, intentar leer de BD.
            final_printer = None
            if printer_name and str(printer_name).strip():
                final_printer = str(printer_name).strip()
            else:
                if self.db is not None:
                    try:
                        row = self.db.fetch_one(
                            "SELECT valor FROM configuracion WHERE clave = ?",
                            ("printer_name",)
                        )
                        if row and row[0] and str(row[0]).strip():
                            final_printer = str(row[0]).strip()
                    except Exception:
                        self.logger.exception("Error leyendo 'printer_name' desde configuracion en BD")

            if not final_printer:
                self.logger.error(
                    "Modo 'escpos' requiere un 'printer_name' no vacío. Configure 'printer_name' en la tabla configuracion o páselo como argumento al método. No se enviará el trabajo."
                )
                return

            try:
                # Preparar parámetro de logo si está habilitado (usar ruta absoluta)
                logo_path = None
                if getattr(self, 'logo_enabled', False) and getattr(self, 'logo_filename', ''):
                    # Construcción de ruta absoluta desde ubicación del módulo
                    base_dir = Path(__file__).resolve().parents[2]
                    candidate = base_dir / "assets" / "logo" / self.logo_filename

                    self.logger.info(f"Buscando logo en: {candidate}")

                    if candidate.exists():
                        logo_path = candidate
                        self.logger.info("Logo encontrado y cargado")
                    else:
                        self.logger.warning(f"Logo habilitado pero archivo no encontrado en: {candidate}")

                # Preparar QR si está habilitado
                qr_data = None
                try:
                    if self.config.get('qr_enabled', False):
                        qr_url = str(self.config.get('qr_url', '') or '').strip()
                        if qr_url:
                            qr_data = qr_url
                except Exception:
                    qr_data = None

                # Renderizar a bytes ESC/POS (incluye dump si debug activo)
                data = self.esc_renderer.render_text_ticket(texto, cut=True, logo_path=logo_path, qr_data=qr_data)

                # Enviar a impresora (nombre validado)
                self.printer_adapter.send_to_printer(final_printer, data)
                self.logger.info("Ticket enviado a impresora ESC/POS (printer=%s) num_ticket=%s", final_printer, meta.get("num_ticket"))
            except Exception:
                self.logger.exception("Error al renderizar/enviar ticket en modo escpos")
            return

    def imprimir_ticket_nivel(self, nivel_data: dict, printer_name: Optional[str] = None):
        """Genera e imprime un ticket de subida de nivel usando el generador específico.

        Reutiliza la lógica de impresión común para mantener compatibilidad con
        `imprimir_ticket` (simulación, modo texto/escpos, logo, dump).
        """
        # Ensure latest config from DB before generating nivel ticket
        try:
            self.config = self._load_config_from_db()
            self.logger.info('ImpresoraService: recargada configuración desde BD antes de generar ticket nivel')
        except Exception:
            self.logger.exception('ImpresoraService: error recargando config antes de generar ticket nivel')

        texto = self.nivel_ticket_generator.generate(self.config, nivel_data)
        # Usar el cliente o algún identificador como metadato para logs
        meta = {'num_ticket': nivel_data.get('cliente', '')}
        return self._imprimir_texto_generico(texto, meta, printer_name)

    def imprimir(self, ticket_type: 'TicketType', data: dict, items: Optional[list] = None, cliente_data: Optional[dict] = None, printer_name: Optional[str] = None):
        """API unificada para imprimir distintos tipos de tickets.

        Args:
            ticket_type: miembro de `TicketType` indicando el tipo de ticket.
            data: diccionario con datos del ticket (interpretación depende del tipo).
            items: lista de items o tickets (opcional, usada por venta/cierre).
            cliente_data: datos de cliente opcionales (usados por venta).
            printer_name: nombre de impresora opcional.
        """
        # Ensure latest configuration is loaded before generating any ticket
        try:
            self.config = self._load_config_from_db()
            self.logger.info('ImpresoraService: recargada configuración desde BD antes de imprimir')
        except Exception:
            self.logger.exception('ImpresoraService: error recargando config antes de imprimir')

        texto = None
        meta = {}

        if ticket_type == TicketType.VENTA:
            texto = self.ticket_generator.generate(self.config, data, items or [], cliente_data)
            meta = {'num_ticket': data.get('num_ticket', '')}
        elif ticket_type == TicketType.VENTA_FIDELIZACION:
            texto = self.venta_fidelizacion_ticket_generator.generate(self.config, data or {}, items or [], cliente_data)
            meta = {'num_ticket': (data or {}).get('num_ticket', '')}
        elif ticket_type == TicketType.DEVOLUCION:
            texto = self.devolucion_ticket_generator.generate(self.config, data or {}, items or [], cliente_data)
            meta = {'num_ticket': (data or {}).get('num_ticket', '')}
        elif ticket_type == TicketType.CIERRE:
            cierre_data = data or {}
            tickets = items or []
            totals = cierre_data.get('totals') if isinstance(cierre_data, dict) else None
            texto = self.cierre_ticket_generator.generate(self.config, cierre_data, tickets, totals=totals)
            meta = {'num_ticket': cierre_data.get('cierre_id', '')}
        elif ticket_type == TicketType.NIVEL:
            texto = self.nivel_ticket_generator.generate(self.config, data or {})
            meta = {'num_ticket': data.get('cliente', '')}
        elif ticket_type == TicketType.DESCUENTO:
            texto = self.descuento_ticket_generator.generate(self.config, data or {})
            meta = {'num_ticket': (data or {}).get('num_ticket', '')}
        else:
            raise ValueError(f"Unsupported ticket_type: {ticket_type}")

        return self._imprimir_texto_generico(texto, meta, printer_name)
