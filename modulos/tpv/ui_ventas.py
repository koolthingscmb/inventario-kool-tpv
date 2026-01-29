import customtkinter as ctk
import sys
from datetime import datetime, date
from .ui_selector_sin_codigo import SelectorSinCodigo
from tkinter import messagebox, simpledialog
import logging

# Servicios para fidelización y clientes
from modulos.configuracion.config_service import ConfigService
from modulos.clientes.cliente_service import ClienteService
from modulos.clientes.ui_selector_cliente import SelectorCliente
from modulos.configuracion.ui_login_cajero import LoginCajero
try:
    from modulos.tpv.preview_imprimir import preview_ticket
except Exception:
    preview_ticket = None

from modulos.tpv.ticket_service import TicketService
from modulos.impresion.print_service import ImpresionService

# instancia compartida de impresión
impresion_service = ImpresionService()

class CajaVentas(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True)
        # Service instances
        self.ticket_service = TicketService()
        
        # --- CARRITO ---
        self.carrito = [] 
        self._awaiting_final_confirmation = False
        # Cliente actual (dict) asignado a la venta
        self.cliente_actual = None
        # Cajero actualmente identificado (dict) — recuperar si main.py ya lo tiene
        self.cajero_activo = getattr(self.controller, 'usuario_actual', None)
        # puntos a canjear en la venta actual (permitir canje parcial)
        self.puntos_a_canjear = 0.0

        # --- ESTRUCTURA ---
        self.grid_rowconfigure(0, weight=0) 
        self.grid_rowconfigure(1, weight=1) 
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 

        # --- BARRA SUPERIOR ---
        self.top_bar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#333333")
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        self.lbl_reloj = ctk.CTkLabel(self.top_bar, text="00:00:00", font=("Arial", 18, "bold"))
        self.lbl_reloj.pack(side="left", padx=20)
        self.actualizar_reloj()

        self.lbl_cajero = ctk.CTkLabel(self.top_bar, text="👤 Cajero: Sin Identificar", font=("Arial", 14))
        self.lbl_cajero.pack(side="right", padx=20)

        # Si se recuperó un cajero desde el controller, reflejar en la interfaz
        try:
            if getattr(self, 'cajero_activo', None):
                caj = self.cajero_activo or {}
                nombre = ''
                try:
                    nombre = caj.get('nombre') or str(caj.get('id') or '')
                except Exception:
                    nombre = str(caj.get('id') if isinstance(caj, dict) else caj)
                self.lbl_cajero.configure(text=f"👤 Cajero: {nombre}")
        except Exception:
            pass

        # asegurar que la interfaz refleje el usuario actual al terminar init
        try:
            self._actualizar_interfaz_cajero()
        except Exception:
            pass

        self.btn_salir = ctk.CTkButton(self.top_bar, text="❌ Salir", width=60, fg_color="red", 
                                       command=self.controller.mostrar_inicio)
        self.btn_salir.pack(side="right", padx=10)

        # --- ZONA IZQUIERDA ---
        self.frame_visor = ctk.CTkFrame(self)
        self.frame_visor.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.lista_productos = ctk.CTkTextbox(self.frame_visor, font=("Courier", 20))
        self.lista_productos.pack(fill="both", expand=True, padx=5, pady=5)
        self.lista_productos.configure(state="disabled")
        # Habilitar selección por línea y borrar con tecla Supr/Del
        try:
            # tag para línea seleccionada
            self.lista_productos._textbox.tag_configure('selected', foreground='#00A4CC')
            # bind click en el texto para seleccionar la línea
            self.lista_productos._textbox.bind('<Button-1>', self._on_text_click)
            # bind tecla Supr/Delete para eliminar item seleccionado
            self.lista_productos._textbox.bind('<Delete>', self._on_delete_key)
        except Exception:
            pass

        self.frame_totales = ctk.CTkFrame(self.frame_visor, height=100, fg_color="black")
        self.frame_totales.pack(fill="x", side="bottom")

        # Información del cliente (compacta, encima del total)
        self.frame_info_cliente = ctk.CTkFrame(self.frame_totales, fg_color="transparent")
        self.frame_info_cliente.pack(fill="x", pady=(6, 0), padx=6)
        # espacio para nombre cliente, botón quitar y botón canjear
        self.frame_info_cliente.columnconfigure((0, 1, 2), weight=1)

        self.lbl_cliente_nombre = ctk.CTkLabel(self.frame_info_cliente, text="", font=("Arial", 12))
        self.lbl_cliente_nombre.grid(row=0, column=0, sticky="w")

        # Botón para quitar cliente (por defecto deshabilitado)
        self.btn_quitar_cliente = ctk.CTkButton(self.frame_info_cliente, text="X", width=28, height=24, command=self._desvincular_cliente)
        self.btn_quitar_cliente.grid(row=0, column=1, sticky="e", padx=(6,0))
        try:
            self.btn_quitar_cliente.configure(state="disabled")
        except Exception:
            pass

        # Botón para canjear puntos (deshabilitado por defecto)
        try:
            self.btn_canjear = ctk.CTkButton(self.frame_info_cliente, text="🎁 Canjear", width=90, height=24, command=self._canjear_puntos)
            self.btn_canjear.grid(row=0, column=2, sticky="e", padx=(6,0))
            self.btn_canjear.configure(state="disabled")
        except Exception:
            # keep going if customtkinter configuration fails
            pass

        self.lbl_total = ctk.CTkLabel(self.frame_totales, text="TOTAL: 0.00 €", font=("Arial", 48, "bold"), text_color="#00FF00")
        self.lbl_total.pack(pady=6)
        
        self.lbl_iva = ctk.CTkLabel(self.frame_totales, text="Base: 0.00€ | IVA: 0.00€", font=("Arial", 14), text_color="white")
        self.lbl_iva.pack()

        # Elementos para entrada de efectivo (inicialmente ocultos)
        self.lbl_efectivo = ctk.CTkLabel(self.frame_totales, text="Introducir efectivo entregado:", font=("Arial", 14), text_color="red")
        # variable para controlar el entry de efectivo y buffer de teclas
        self.efectivo_var = ctk.StringVar(value="")
        self._cash_buffer = ""
        self.entry_efectivo = ctk.CTkEntry(self.frame_totales, font=("Arial", 14), textvariable=self.efectivo_var)
        self.entry_efectivo.bind("<Return>", self.procesar_efectivo)

        # Captura teclas numéricas globales para rellenar el efectivo cuando la pantalla está activa
        try:
            self.controller.bind_all("<Key>", self._on_global_key)
            # asegurarse de limpiar el binding al destruir la pantalla
            self.bind("<Destroy>", lambda e: self.controller.unbind_all("<Key>"))
        except Exception:
            pass

        # --- ZONA DERECHA ---
        self.frame_botones = ctk.CTkFrame(self)
        self.frame_botones.grid(row=1, column=1, sticky="nsew", padx=(0,10), pady=10)
        self.frame_botones.grid_columnconfigure((0,1), weight=1) 

        # Caja de Búsqueda
        frame_busqueda = ctk.CTkFrame(self.frame_botones, fg_color="transparent")
        frame_busqueda.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.entry_codigo = ctk.CTkEntry(frame_busqueda, placeholder_text="SKU / EAN", height=50, font=("Arial", 16))
        self.entry_codigo.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_codigo.bind("<Return>", self.buscar_producto)
        self.entry_codigo.focus()

        self.btn_buscar = ctk.CTkButton(frame_busqueda, text="🔍", width=50, height=50, command=self.buscar_producto_evento)
        self.btn_buscar.pack(side="right")

        # Botones Varios - reorganizados
        # Parte superior: cuadro de búsqueda ya en row=0
        # Botón SIN CÓDIGO en su propia línea (debajo de la búsqueda)
        ctk.CTkButton(self.frame_botones, text="SIN CÓDIGO", width=140, height=50, fg_color="#FF6B35", command=self.abrir_selector_sin_codigo).grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,10))

        # Zona central: espacio para los botones dinámicos del selector (ocupable)
        self.selector_area = ctk.CTkScrollableFrame(self.frame_botones)
        self.selector_area.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_botones.grid_rowconfigure(2, weight=1)

        # Parte inferior (de arriba a abajo):
        # 6- CLIENTE y CAJERO (misma línea)
        ctk.CTkButton(self.frame_botones, text="👤 CLIENTE", height=40, command=self._abrir_selector_cliente).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="🆔 CAJERO", height=40, command=self._abrir_login_cajero).grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # 5- TICKETS y SELECTOR IMPRIMIR TICKET (misma línea)
        # Tickets button: open tickets view
        try:
            self.btn_tickets = ctk.CTkButton(self.frame_botones, text="📄 TICKETS", height=40, command=self._abrir_tickets)
            self.btn_tickets.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        except Exception:
            ctk.CTkButton(self.frame_botones, text="📄 TICKETS", height=40).grid(row=4, column=0, sticky="ew", padx=5, pady=5)

        # Toggle automatic printing of ticket: visual indicator changes text
        try:
            def _toggle_impr():
                try:
                    # toggle printing flag (default is ON in controller)
                    self.controller.toggle_imprimir_tickets()
                    self._update_impr_button()
                except Exception:
                    pass
                # Show list of tickets included in this cierre so user can verify
                try:
                    # Use TicketService to retrieve tickets for preview instead of direct DB access
                    tickets_rows = []
                    try:
                        # prefer any cached cierre id if available
                        cierre_id = getattr(self, '_last_cierre_id', None)
                    except Exception:
                        cierre_id = None
                    try:
                        if cierre_id:
                            tickets_rows = self.ticket_service.listar_tickets_por_cierre(cierre_id)
                        else:
                            fecha_today = datetime.now().date().isoformat()
                            tickets_rows = self.ticket_service.listar_tickets_por_fecha(fecha_today)
                    except Exception:
                        tickets_rows = []

                    # build modal with Treeview
                    t = ctk.CTkToplevel(self)
                    t.title('Tickets incluidos')
                    t.geometry('600x360')
                    t.transient(self)
                    from tkinter import ttk as _ttk
                    frame = ctk.CTkFrame(t)
                    frame.pack(fill='both', expand=True, padx=8, pady=8)
                    tree = _ttk.Treeview(frame, columns=('no','hora','cajero','total'), show='headings')
                    tree.heading('no', text='Nº')
                    tree.heading('hora', text='Hora')
                    tree.heading('cajero', text='Cajero')
                    tree.heading('total', text='Total')
                    tree.column('no', width=80)
                    tree.column('hora', width=120)
                    tree.column('cajero', width=160)
                    tree.column('total', width=120, anchor='e')
                    tree.pack(fill='both', expand=True, side='left')
                    sb = _ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
                    tree.configure(yscroll=sb.set)
                    sb.pack(side='right', fill='y')
                    for r in tickets_rows:
                        tid, created_at, ticket_no, cajero_t, tot = r
                        hora = ''
                        try:
                            hora = datetime.fromisoformat(created_at).strftime('%H:%M:%S')
                        except Exception:
                            hora = created_at
                        tree.insert('', 'end', iid=str(tid), values=(ticket_no or '', hora, cajero_t or '', f"{(tot or 0):.2f}"))
                    # allow double-click to open ticket detail in main Tickets view
                    def _on_double(e):
                        sel = tree.selection()
                        if not sel:
                            return
                        tid = sel[0]
                        try:
                            t.destroy()
                        except Exception:
                            pass
                        try:
                            # show tickets view focused on the ticket's day and select it
                            self.controller.mostrar_tickets()
                            # rely on the TicketsView to allow user to open details
                        except Exception:
                            pass
                    tree.bind('<Double-1>', _on_double)
                except Exception:
                    pass

            self.btn_impr = ctk.CTkButton(self.frame_botones, text="🖨️ IMPR. TICKET", height=40, command=_toggle_impr)
            self.btn_impr.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
            # set initial visual state
            self._update_impr_button()
        except Exception:
            ctk.CTkButton(self.frame_botones, text="🖨️ IMPR. TICKET", height=40).grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        # 4- DESCUENTO y DEVOLUCIÓN (misma línea)
        ctk.CTkButton(self.frame_botones, text="✂️ DESCUENTO", height=40, fg_color="#E59400", command=self._on_descuento).grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="↩️ DEVOLUCIÓN", height=40, fg_color="#FF4500", command=self._on_devolucion).grid(row=5, column=1, sticky="ew", padx=5, pady=5)

        # 3- TARJETA y WEB (misma línea)
        ctk.CTkButton(self.frame_botones, text="💳 TARJETA", height=60, fg_color="#1E90FF", command=self._cobrar_tarjeta).grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="🌐 WEB", height=60, fg_color="#00A4CC", command=self._cobrar_web).grid(row=6, column=1, sticky="ew", padx=5, pady=5)

        # 2- EFECTIVO (línea completa)
        ctk.CTkButton(self.frame_botones, text="💶 EFECTIVO", height=80, fg_color="#228B22", font=("Arial", 20, "bold"), command=self.abrir_cobro_efectivo).grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # 1- CERRAR DÍA  y CAJÓN (misma línea, al fondo)
        ctk.CTkButton(self.frame_botones, text="🔒 CERRAR DÍA", height=30, fg_color="darkred", command=self._on_cerrar_dia).grid(row=8, column=0, sticky="ew", padx=5, pady=(20,5))
        ctk.CTkButton(self.frame_botones, text="🔓 CAJÓN", height=30, fg_color="#555555").grid(row=8, column=1, sticky="ew", padx=5, pady=(20,5))

    def actualizar_reloj(self):
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_reloj.configure(text=ahora)
        self.after(1000, self.actualizar_reloj)

    def _abrir_login_cajero(self):
        try:
            dlg = LoginCajero(self)
            # modal: wait until closed
            try:
                self.wait_window(dlg)
            except Exception:
                pass
            # check result
            res = getattr(dlg, 'result', None)
            if res:
                # persist session on controller and update UI
                try:
                    self.controller.usuario_actual = res
                except Exception:
                    pass
                try:
                    self._actualizar_interfaz_cajero()
                except Exception:
                    pass
                # no popup on login; UI updated and dialog closed
        except Exception:
            logging.exception('Error abriendo dialogo de login de cajero')

    def _actualizar_interfaz_cajero(self):
        """Actualizar interfaz del TPV según `self.controller.usuario_actual`.

        Si hay usuario, sincroniza `self.cajero_activo` y actualiza `self.lbl_cajero`.
        Si no hay usuario, limpia `self.cajero_activo` y pone texto por defecto.
        """
        try:
            usuario = getattr(self.controller, 'usuario_actual', None)
            if usuario:
                self.cajero_activo = usuario
                try:
                    nombre = usuario.get('nombre') or str(usuario.get('id') or '')
                except Exception:
                    nombre = str(usuario.get('id') if isinstance(usuario, dict) else usuario)
                try:
                    self.lbl_cajero.configure(text=f"👤 Cajero: {nombre}")
                except Exception:
                    pass
            else:
                self.cajero_activo = None
                try:
                    self.lbl_cajero.configure(text="👤 Cajero: Sin Identificar")
                except Exception:
                    pass
        except Exception:
            pass

    def _ensure_cajero_identificado(self) -> bool:
        """Ensure `self.cajero_activo` is set; if not, open `LoginCajero` and wait.

        Returns True if a cajero is identified, False otherwise.
        """
        try:
            if getattr(self, 'cajero_activo', None):
                return True
            dlg = LoginCajero(self)
            try:
                self.wait_window(dlg)
            except Exception:
                pass
            res = getattr(dlg, 'result', None)
            if res:
                self.cajero_activo = res
                try:
                    nombre = res.get('nombre') or str(res.get('id') or '')
                except Exception:
                    nombre = str(res.get('id') if isinstance(res, dict) else res)
                try:
                    self.lbl_cajero.configure(text=f"👤 Cajero: {nombre}")
                except Exception:
                    pass
                return True
            return False
        except Exception:
            return False

    def _on_descuento(self):
        """Handler para el botón DESCUENTO: comprueba permisos antes de permitir la acción."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            caj = self.cajero_activo or {}
            try:
                is_admin = int(caj.get('es_admin') or 0)
            except Exception:
                is_admin = 0
            if is_admin == 1:
                pass  # admin can proceed
            else:
                try:
                    permiso = int(caj.get('permiso_descuento') or 0)
                except Exception:
                    permiso = 0
                if permiso != 1:
                    try:
                        messagebox.showerror('Acceso Denegado', 'No tienes permiso para aplicar descuentos.')
                    except Exception:
                        pass
                    return

            # TODO: implementar lógica real de descuento; por ahora mostramos diálogo simple
            try:
                monto = simpledialog.askfloat('Descuento', 'Introduce importe de descuento (€):', minvalue=0.0)
                if monto is None:
                    return
                # aplicar descuento como línea negativa
                descuento_item = {"id": "MAN_DESC", "nombre": "DESC. MANUAL", "precio": -round(float(monto or 0.0), 2), "cantidad": 1, "iva": 0}
                self.carrito.append(descuento_item)
                try:
                    self.actualizar_visor()
                except Exception:
                    pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error comprobando permiso para descuento')

    def _on_devolucion(self):
        """Handler para el botón DEVOLUCIÓN: comprueba permisos antes de permitir la acción."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            caj = self.cajero_activo or {}
            try:
                is_admin = int(caj.get('es_admin') or 0)
            except Exception:
                is_admin = 0
            if is_admin == 1:
                pass
            else:
                try:
                    permiso = int(caj.get('permiso_devolucion') or 0)
                except Exception:
                    permiso = 0
                if permiso != 1:
                    try:
                        messagebox.showerror('Acceso Denegado', 'No tienes permiso para realizar devoluciones.')
                    except Exception:
                        pass
                    return

            # TODO: Implementar flujo real de devolución. Por ahora, abrir diálogo informativo.
            try:
                messagebox.showinfo('Devolución', 'Funcionalidad de devolución iniciada (pendiente de implementación).')
            except Exception:
                pass
        except Exception:
            logging.exception('Error comprobando permiso para devolución')

    def _abrir_tickets(self):
        """Handler protegido para abrir la pantalla de Tickets."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            caj = self.cajero_activo or {}
            # robust admin check: allow if explicit flag or role == 'admin'
            es_admin = str(caj.get('es_admin', '0')) == '1' or (caj.get('rol') == 'admin')
            if es_admin:
                try:
                    self.controller.mostrar_tickets()
                except Exception:
                    pass
                return

            # non-admin: enforce permiso_tickets
            try:
                permiso = int(caj.get('permiso_tickets') or 0)
            except Exception:
                permiso = 0
            if permiso != 1:
                try:
                    messagebox.showerror('Acceso Denegado', 'No tienes permiso para abrir la pantalla de Tickets.')
                except Exception:
                    pass
                return

            try:
                self.controller.mostrar_tickets()
            except Exception:
                pass
        except Exception:
            logging.exception('Error comprobando permiso para abrir Tickets')

    def _on_cerrar_dia(self):
        """Handler para CERRAR DÍA: comprueba permiso_cierre antes de delegar al controller."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            caj = self.cajero_activo or {}
            try:
                is_admin = int(caj.get('es_admin') or 0)
            except Exception:
                is_admin = 0
            if is_admin == 1:
                pass
            else:
                try:
                    permiso = int(caj.get('permiso_cierre') or 0)
                except Exception:
                    permiso = 0
                if permiso != 1:
                    try:
                        messagebox.showerror('Acceso Denegado', 'No tienes permiso para cerrar el día.')
                    except Exception:
                        pass
                    return

            # delegate to controller to show cierre UI
            try:
                self.controller.mostrar_cierre_caja()
            except Exception:
                try:
                    # fallback to local dialog
                    self.cerrar_dia_dialog()
                except Exception:
                    pass
        except Exception:
            logging.exception('Error comprobando permiso para cerrar día')

    # ------------------ Cálculo de puntos por venta ------------------
    def _calcular_puntos_venta(self) -> float:
        """Calcula los puntos que corresponde dar por la venta actual.

        Orden de prioridad:
          Promoción activa (multiplicador) > fide_puntos_fijos (producto) > porcentaje por tipo > porcentaje por categoría > porcentaje general

        Devuelve puntos totales (int).
        """
        # Delegate to FidelizacionService to avoid DB access here
        try:
            if not hasattr(self, 'fidelizacion_service'):
                from modulos.tpv.fidelizacion_service import FidelizacionService
                self.fidelizacion_service = FidelizacionService()
            return float(self.fidelizacion_service.calcular_puntos(getattr(self, 'carrito', []), getattr(self, 'cliente_actual', None)) or 0.0)
        except Exception:
            logging.exception('Error delegando cálculo de puntos a FidelizacionService')
            return 0.0

    # ------------------ Cliente selector ------------------
    def _abrir_selector_cliente(self):
        try:
            selector = SelectorCliente(self)
            self.wait_window(selector)
            cliente = getattr(selector, 'result', None)
            if cliente:
                self._asignar_cliente(cliente)
        except Exception:
            pass

    def _asignar_cliente(self, cliente: dict):
        try:
            self.cliente_actual = cliente
            nombre = cliente.get('nombre') or ''
            # intentar obtener saldo de puntos actualizado desde servicio si hay id
            try:
                puntos = 0.0
                cid = cliente.get('id')
                if cid:
                    svc = ClienteService()
                    datos = svc.obtener_por_id(cid)
                    try:
                        puntos = float(datos.get('puntos_fidelidad') or 0)
                    except Exception:
                        puntos = float(cliente.get('puntos_fidelidad') or 0)
                else:
                    puntos = float(cliente.get('puntos_fidelidad') or 0)
            except Exception:
                try:
                    puntos = float(cliente.get('puntos_fidelidad') or 0)
                except Exception:
                    puntos = 0.0

            self.lbl_cliente_nombre.configure(text=f"Cliente: {nombre} ({puntos:.2f} pts)")
            try:
                self.btn_quitar_cliente.configure(state="normal")
                try:
                    self.btn_canjear.configure(state="normal")
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    def _desvincular_cliente(self):
        try:
            self.cliente_actual = None
            # volver al estado por defecto (cliente no asignado)
            try:
                self.lbl_cliente_nombre.configure(text="Cliente: Contado")
            except Exception:
                self.lbl_cliente_nombre.configure(text="")
            try:
                self.btn_quitar_cliente.configure(state="disabled")
                try:
                    self.btn_canjear.configure(state="disabled")
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    def _canjear_puntos(self):
        """Permite canjear parcialmente puntos del cliente como descuento en euros.

        Pide al cajero la cantidad de puntos a canjear y valida disponibilidad
        y que el descuento no supere el total del carrito.
        """
        try:
            if not getattr(self, 'cliente_actual', None):
                messagebox.showwarning('Atención', 'No hay ningún cliente seleccionado')
                return

            cfg = ConfigService()
            try:
                puntos_por_euro = float(cfg.get_valor('fide_puntos_valor_euro', '1') or 1)
            except Exception:
                puntos_por_euro = 1.0

            # 1. Obtener saldo real de la BD primero
            cliente_id = self.cliente_actual.get('id')
            data = ClienteService().obtener_por_id(cliente_id)
            saldo = float(data.get('puntos_fidelidad') or 0) if data else 0.0

            # 2. Llamar a nuestra nueva ventana en lugar de simpledialog
            pts = self._mostrar_dialogo_canje(saldo)
            # Si el usuario cerró o canceló, pts será None, salimos
            if pts is None:
                return

            if pts > saldo:
                messagebox.showwarning('Atención', 'El cliente no tiene suficientes puntos')
                return

            # calcular descuento en euros: puntos / puntos_por_euro (puntos por euro)
            try:
                descuento_euros = float(pts) / float(puntos_por_euro) if puntos_por_euro else 0.0
            except Exception:
                descuento_euros = 0.0

            # total actual del carrito
            try:
                total = self._total_carrito()
            except Exception:
                total = 0.0

            if descuento_euros > total:
                messagebox.showwarning('Atención', 'El descuento supera el total de la venta')
                return

            # remove any existing discount line
            try:
                self.carrito = [it for it in self.carrito if it.get('id') != 'DESC']
            except Exception:
                pass

            # aplicar descuento como línea negativa
            try:
                descuento_item = {"id": "DESC", "nombre": "DESC. PUNTOS", "precio": -round(descuento_euros, 2), "cantidad": 1, "iva": 0}
                self.carrito.append(descuento_item)
                self.puntos_a_canjear = pts
            except Exception:
                pass

            # actualizar visor para reflejar descuento
            try:
                self.actualizar_visor()
            except Exception:
                pass
        except Exception:
            logging.exception('Error en canje de puntos')

    def _compute_day_summary(self, fecha_str: str):
        """Return lightweight summary for `fecha_str` (YYYY-MM-DD)."""
        try:
            # Delegate summary computation to TicketService
            try:
                if not hasattr(self, 'ticket_service'):
                    from modulos.tpv.ticket_service import TicketService
                    self.ticket_service = TicketService()
                resumen = self.ticket_service.resumen_dia(fecha_str)
                return resumen
            except Exception:
                return None
        except Exception:
            return None
        finally:
            # TicketService handles its own connection lifecycle
            pass

    def cerrar_dia_dialog(self):
        """Show modal to confirm day closure and perform close_day on confirm."""
        fecha = datetime.now().date().isoformat()
        summary = self._compute_day_summary(fecha)

        win = ctk.CTkToplevel(self)
        win.title(f"Cerrar día {fecha}")
        win.geometry('480x320')
        win.transient(self)

        # Summary labels
        lbl = ctk.CTkLabel(win, text=f"Resumen día {fecha}", font=(None, 16, 'bold'))
        lbl.pack(pady=(12,6))
        if summary:
            txt = f"Tickets: {summary['count']}  Total: {summary['total']:.2f}€\nRango: {summary['from'] or ''} - {summary['to'] or ''}\n"
            for forma, cnt, tot in summary['pagos']:
                txt += f"{forma or 'OTROS'}: {cnt}  {tot:.2f}€\n"
        else:
            txt = "No hay datos para este día."
        lbl2 = ctk.CTkLabel(win, text=txt, anchor='w', justify='left')
        lbl2.pack(fill='both', padx=12)

        # Options
        var_tipo = ctk.StringVar(value='Z')
        frame_tipo = ctk.CTkFrame(win)
        frame_tipo.pack(anchor='w', padx=12, pady=(8,0))
        ctk.CTkLabel(frame_tipo, text='Tipo:').pack(side='left', padx=(0,8))
        ctk.CTkRadioButton(frame_tipo, text='Z - Cierre definitivo (marca tickets)', variable=var_tipo, value='Z').pack(side='left', padx=4)
        ctk.CTkRadioButton(frame_tipo, text='X - Cierre informativo (no marca)', variable=var_tipo, value='X').pack(side='left', padx=4)

        var_cat = ctk.BooleanVar(value=False)
        var_prod = ctk.BooleanVar(value=False)
        var_print = ctk.BooleanVar(value=False)
        cb1 = ctk.CTkCheckBox(win, text="Incluir desglose por categoría", variable=var_cat)
        cb1.pack(anchor='w', padx=12, pady=(8,0))
        cb2 = ctk.CTkCheckBox(win, text="Incluir top productos", variable=var_prod)
        cb2.pack(anchor='w', padx=12)
        cb3 = ctk.CTkCheckBox(win, text="Imprimir cierre (en impresora)", variable=var_print)
        cb3.pack(anchor='w', padx=12, pady=(0,8))

        btns = ctk.CTkFrame(win)
        btns.pack(side='bottom', fill='x', pady=12)

        def _on_confirm():
            try:
                # Delegate close_day to TicketService to avoid direct DB function import in UI
                tipo = var_tipo.get()
                # pass current cashier name to close_day so cierres_caja.cajero is populated
                cajero_name = None
                try:
                    if getattr(self, 'cajero_activo', None):
                        cajero_name = self.cajero_activo.get('nombre')
                except Exception:
                    cajero_name = None

                try:
                    resumen = self.ticket_service.close_day(fecha, tipo=tipo, include_category=var_cat.get(), include_products=var_prod.get(), cajero=cajero_name, notas=None)
                except Exception:
                    resumen = None

                # Build closure text (include numero and tipo)
                lines = []
                lines.append("CIERRE DE CAJA\n")
                lines.append(f"Tipo: {(resumen.get('numero','') if resumen else '')} - {tipo}\n")
                lines.append(f"Día: {fecha}\n")
                lines.append(f"Tickets: {(resumen.get('count_tickets',0) if resumen else 0)}  TOTAL: {(resumen.get('total',0) if resumen else 0):.2f}€\n")
                if resumen:
                    for p in resumen.get('por_forma_pago', []):
                        lines.append(f"{p.get('forma','OTROS')}: {p.get('total',0):.2f}€\n")
                    if resumen.get('por_categoria'):
                        lines.append('\nDesglose por categoría:\n')
                        for c in resumen.get('por_categoria'):
                            lines.append(f"{c.get('categoria')}: {c.get('qty')}  {c.get('total'):.2f}€\n")
                    if resumen.get('top_products'):
                        lines.append('\nTop productos:\n')
                        for tprod in resumen.get('top_products'):
                            lines.append(f"{tprod.get('nombre')}: {tprod.get('qty')}  {tprod.get('total'):.2f}€\n")
                text = ''.join(lines)

                # Inform user immediately about created cierre (so they see something even if preview fails)
                try:
                    from tkinter import messagebox as _mb
                    _mb.showinfo('Cierre creado', f"Tipo: {tipo}  Número: {(resumen.get('numero','') if resumen else '')}\nTickets: {(resumen.get('count_tickets',0) if resumen else 0)}\nTotal: {(resumen.get('total',0) if resumen else 0):.2f}€")
                except Exception:
                    pass

                # Always show a local preview modal for Z closures or when printing requested.
                try:
                    # collect ticket rows via TicketService for the preview
                    try:
                        tickets_rows = []
                        if resumen and resumen.get('cierre_id'):
                            tickets_rows = self.ticket_service.listar_tickets_por_cierre(resumen.get('cierre_id'))
                        else:
                            tickets_rows = self.ticket_service.listar_tickets_por_fecha(fecha)
                    except Exception:
                        tickets_rows = []

                    if tipo == 'Z' or var_print.get():
                        try:
                            self._show_cierre_preview(text, tickets_rows)
                        except Exception:
                            # fallback: ensure at least a simple modal appears
                            t = ctk.CTkToplevel(self)
                            t.title('Previsualizar cierre')
                            tb = ctk.CTkTextbox(t, width=400, height=300)
                            tb.pack(fill='both', expand=True)
                            tb.insert('end', text)
                except Exception:
                    pass

                # if closure already existed, inform user; otherwise proceed to next day
                try:
                    if resumen and resumen.get('already_closed'):
                        try:
                            from tkinter import messagebox
                            messagebox.showinfo('Cierre', f"El día {fecha} ya estaba cerrado (id {resumen.get('cierre_id')}). Se mostrará el resumen.")
                        except Exception:
                            pass
                    # navigate to Tickets view for next day
                    import datetime as _dt
                    next_day = (_dt.date.fromisoformat(fecha) + _dt.timedelta(days=1)).isoformat()
                    self.controller.mostrar_tickets(next_day)
                except Exception:
                    try:
                        self.controller.mostrar_tickets()
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                try:
                    win.destroy()
                except Exception:
                    pass

        def _on_cancel():
            try:
                win.destroy()
            except Exception:
                pass

        ctk.CTkButton(btns, text='Confirmar Cierre', fg_color='darkred', command=_on_confirm).pack(side='left', padx=12)
        ctk.CTkButton(btns, text='Cancelar', command=_on_cancel).pack(side='right', padx=12)

    def _show_cierre_preview(self, cierre_text, tickets_rows=None):
        """Show a modal preview of the cierre text and an optional list of included tickets."""
        try:
            modal = ctk.CTkToplevel(self)
            modal.title('Previsualización cierre')
            modal.geometry('720x520')
            modal.transient(self)

            txt = ctk.CTkTextbox(modal, width=700, height=260)
            txt.pack(padx=10, pady=(10,6), fill='x')
            try:
                txt.insert('0.0', cierre_text)
            except Exception:
                txt.insert('end', str(cierre_text))
            try:
                txt.configure(state='disabled')
            except Exception:
                pass

            if tickets_rows:
                frame = ctk.CTkFrame(modal)
                frame.pack(fill='both', expand=True, padx=10, pady=6)
                from tkinter import ttk as _ttk
                tree = _ttk.Treeview(frame, columns=('num','hora','cajero','total'), show='headings', height=8)
                tree.heading('num', text='Nº')
                tree.heading('hora', text='Hora')
                tree.heading('cajero', text='Cajero')
                tree.heading('total', text='Total')
                tree.column('num', width=80)
                tree.column('hora', width=120)
                tree.column('cajero', width=160)
                tree.column('total', width=120, anchor='e')
                tree.pack(side='left', fill='both', expand=True)
                for r in tickets_rows:
                    tid, created_at, ticket_no, cajero_t, tot = r
                    hora = ''
                    try:
                        hora = datetime.fromisoformat(created_at).strftime('%H:%M:%S')
                    except Exception:
                        hora = created_at
                    tree.insert('', 'end', iid=str(tid), values=(ticket_no or '', hora, cajero_t or '', f"{(tot or 0):.2f}"))
                sb = _ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
                sb.pack(side='right', fill='y')
                tree.configure(yscrollcommand=sb.set)

            btns = ctk.CTkFrame(modal)
            btns.pack(fill='x', padx=10, pady=(6,10))

            def _imprimir():
                try:
                    impresion_service.imprimir_ticket(cierre_text, abrir_cajon=True)
                except Exception:
                    pass

            ctk.CTkButton(btns, text='Imprimir', width=120, command=_imprimir).pack(side='right', padx=6)
            ctk.CTkButton(btns, text='Cerrar', width=120, command=modal.destroy).pack(side='right', padx=6)
        except Exception:
            pass

    def _ask_large_price(self, title, prompt):
        win = ctk.CTkToplevel(self)
        win.title(title)
        try:
            win.geometry("480x220")
        except Exception:
            pass
        win.transient(self)
        win.grab_set()

        lbl = ctk.CTkLabel(win, text=prompt, font=("Arial", 16))
        lbl.pack(pady=(18, 6))

        var = ctk.StringVar()
        entry = ctk.CTkEntry(win, textvariable=var, font=("Arial", 26), justify='center')
        entry.pack(fill='x', padx=24, pady=(0, 12))
        entry.focus_set()
        # accept Enter in the entry as OK and Escape as cancel
        entry.bind("<Return>", lambda e: _on_ok())
        entry.bind("<KP_Enter>", lambda e: _on_ok())
        win.bind("<Escape>", lambda e: _on_cancel())

        result = {'value': None}

        def _on_ok():
            try:
                v = float(var.get().replace(',', '.'))
                result['value'] = v
                win.destroy()
            except Exception:
                messagebox.showerror('Error', 'Introduce un número válido')

        def _on_cancel():
            win.destroy()

        btns = ctk.CTkFrame(win)
        btns.pack(pady=(6, 16))
        ctk.CTkButton(btns, text='Aceptar', width=140, command=_on_ok).pack(side='left', padx=8)
        ctk.CTkButton(btns, text='Cancelar', width=140, command=_on_cancel).pack(side='left', padx=8)

        win.wait_window()
        return result['value']

    def buscar_producto_evento(self):
        self.buscar_producto(None)

    def buscar_producto(self, event):
        # require cashier identification
        try:
            if not getattr(self, 'cajero_activo', None):
                messagebox.showwarning('Atención', 'Debe identificarse como cajero para realizar ventas')
                return
        except Exception:
            pass
        codigo_input = self.entry_codigo.get().strip()
        if not codigo_input:
            return

        # Use ProductoService to avoid direct DB access in the UI
        try:
            if not hasattr(self, 'producto_service'):
                from modulos.almacen.producto_service import ProductoService
                self.producto_service = ProductoService()

            # Exact SKU/EAN lookup via service
            try:
                resultado = self.producto_service.buscar_por_codigo(codigo_input)
            except Exception:
                resultado = None

            if resultado:
                # El ProductoService devuelve un dict; usar claves conocidas
                pvp_variable = resultado.get('pvp_variable', 0)
                # precio real almacenado bajo 'precio'
                precio_base = resultado.get('precio')
                if pvp_variable:
                    try:
                        val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                        if val is None:
                            self.entry_codigo.delete(0, 'end')
                            return
                        precio_base = float(val)
                    except Exception:
                        pass

                # Asegurar tipo numérico en 'precio'
                try:
                    precio_base = float(precio_base) if precio_base is not None else 0.0
                except Exception:
                    precio_base = 0.0

                producto = {
                    "nombre": resultado.get('nombre'),
                    "precio": precio_base,
                    "sku": resultado.get('sku'),
                    "iva": resultado.get('tipo_iva'),
                    "id": resultado.get('id'),
                    "cantidad": 1
                }

                encontrado = False
                for item in self.carrito:
                    if item['id'] == producto['id']:
                        item['cantidad'] += 1
                        encontrado = True
                        break

                if not encontrado:
                    self.carrito.append(producto)

                self.actualizar_visor()
                self.entry_codigo.delete(0, 'end')
                return

            # Fallback: search by name/sku
            try:
                rows = self.producto_service.buscar_por_nombre(codigo_input)
            except Exception:
                rows = []

            # clear and show results in selector area
            try:
                for w in self.selector_area.winfo_children():
                    w.destroy()
            except Exception:
                pass

            if not rows:
                lbl = ctk.CTkLabel(self.selector_area, text="No hay resultados.")
                lbl.pack(pady=6)
                self.entry_codigo.delete(0, 'end')
                return

            for row in rows:
                try:
                    # ProductoService devuelve dicts; leer claves conocidas
                    pid = row.get('id')
                    nombre = row.get('nombre')
                    # preferimos 'precio' como fuente del PVP
                    pvp = row.get('precio') or row.get('pvp') or 0
                    sku = row.get('sku')
                    pvp_variable = row.get('pvp_variable', 0)
                except Exception:
                    continue

                def _make_cmd(pid=pid, pvp=pvp, sku=sku, nombre=nombre, pvp_variable=pvp_variable):
                    def _cmd():
                        precio_base = pvp
                        if pvp_variable:
                            try:
                                val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                                if val is None:
                                    return
                                precio_base = float(val)
                            except Exception:
                                pass
                        # Asegurar precio numérico y usar tipo de IVA si viene
                        try:
                            precio_base = float(precio_base) if precio_base is not None else 0.0
                        except Exception:
                            precio_base = 0.0
                        iva_val = row.get('tipo_iva') if isinstance(row, dict) else None
                        producto = {"nombre": nombre, "precio": precio_base, "sku": sku, "iva": iva_val or 21, "id": pid, "cantidad": 1}
                        encontrado = False
                        for item in self.carrito:
                            if item['id'] == producto['id']:
                                item['cantidad'] += 1
                                encontrado = True
                                break
                        if not encontrado:
                            self.carrito.append(producto)
                        self.actualizar_visor()
                    return _cmd

                btn = ctk.CTkButton(self.selector_area, text=f"{nombre} — {sku} — {float(pvp):.2f}€", command=_make_cmd())
                btn.pack(fill='x', pady=4, padx=6)

            self.entry_codigo.delete(0, 'end')

        except Exception as e:
            print(f"Error búsqueda global: {e}")

    def actualizar_visor(self):
        self.lista_productos.configure(state="normal")
        self.lista_productos.delete("0.0", "end")
        
        total_pagar = 0.0
        total_base = 0.0
        total_iva = 0.0

        self.lista_productos.insert("end", f"{'CANT':<5} {'PRODUCTO':<25} {'PRECIO':>10} {'TOTAL':>10}\n")
        self.lista_productos.insert("end", "-"*55 + "\n")

        for idx, item in enumerate(self.carrito):
            # proteger valores: precio y cantidad pueden ser None o strings
            precio_raw = item.get('precio')
            cantidad_raw = item.get('cantidad', 0)
            if precio_raw is None:
                try:
                    logging.warning('Producto sin precio al renderizar visor: SKU=%s id=%s', item.get('sku'), item.get('id'))
                except Exception:
                    logging.warning('Producto sin precio al renderizar visor: id=%s', item.get('id'))
            try:
                precio = float(precio_raw or 0.0)
            except Exception:
                precio = 0.0
            try:
                cantidad = int(cantidad_raw)
            except Exception:
                try:
                    cantidad = int(float(cantidad_raw))
                except Exception:
                    cantidad = 0

            subtotal = precio * cantidad
            try:
                iva_val = float(item.get('iva') or 0.0)
            except Exception:
                iva_val = 0.0
            divisor = 1 + (iva_val / 100)
            base_item = subtotal / divisor if divisor != 0 else 0.0
            iva_item = subtotal - base_item

            total_pagar += subtotal
            total_base += base_item
            total_iva += iva_item

            linea = f"{cantidad}x    {item.get('nombre','')[:22]:<25} {precio:>8.2f}€ {subtotal:>9.2f}€\n"
            # insertar y etiquetar la línea para selección
            self.lista_productos.insert("end", linea)
            line_no = 3 + idx
            try:
                self.lista_productos._textbox.tag_remove(f"item_{idx}", f"{line_no}.0", f"{line_no}.end")
            except Exception:
                pass
            try:
                self.lista_productos._textbox.tag_add(f"item_{idx}", f"{line_no}.0", f"{line_no}.end")
            except Exception:
                pass

        self.lista_productos.configure(state="disabled")
        self.lbl_total.configure(text=f"TOTAL: {total_pagar:.2f} €")
        self.lbl_iva.configure(text=f"Base Imponible: {total_base:.2f}€ | Total IVA: {total_iva:.2f}€")

    def _update_impr_button(self):
        try:
            enabled = getattr(self.controller, 'imprimir_tickets_enabled', False)
            if enabled:
                try:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET (ON)", fg_color="#2E8B57")
                except Exception:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET (ON)")
            else:
                try:
                    # visual 'off' state: gray
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET", fg_color="#6c6c6c")
                except Exception:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET")
        except Exception:
            pass

    def _total_carrito(self) -> float:
        """Calcula el total del carrito de forma segura, evitando None en precio/cantidad.

        Registra un warning si encuentra un producto sin precio (para identificar SKU/id).
        """
        total = 0.0
        try:
            for it in getattr(self, 'carrito', []) or []:
                precio_raw = it.get('precio')
                cantidad_raw = it.get('cantidad', 0)
                if precio_raw is None:
                    try:
                        logging.warning('Producto sin precio al calcular total: SKU=%s id=%s', it.get('sku'), it.get('id'))
                    except Exception:
                        logging.warning('Producto sin precio al calcular total: id=%s', it.get('id'))
                try:
                    precio = float(precio_raw or 0.0)
                except Exception:
                    precio = 0.0
                try:
                    cantidad = int(cantidad_raw)
                except Exception:
                    try:
                        cantidad = int(float(cantidad_raw))
                    except Exception:
                        cantidad = 0
                total += precio * cantidad
        except Exception:
            logging.exception('Error calculando total seguro del carrito')
            return 0.0
        return total

    def _on_text_click(self, event):
        try:
            # conseguir índice de línea bajo el click
            index = self.lista_productos._textbox.index(f"@{event.x},{event.y}")
            line = int(index.split('.')[0])
            # los items empiezan en la línea 3 (1: header, 2: separador)
            item_idx = line - 3
            if item_idx < 0 or item_idx >= len(self.carrito):
                return
            # quitar selección previa
            try:
                self.lista_productos._textbox.tag_remove('selected', '1.0', 'end')
            except Exception:
                pass
            # añadir tag selected a la línea
            try:
                self.lista_productos._textbox.tag_add('selected', f"{line}.0", f"{line}.end")
            except Exception:
                pass
            self._selected_carrito_index = item_idx
            # asegurar foco para recibir teclas
            try:
                self.lista_productos._textbox.focus_set()
            except Exception:
                pass
        except Exception:
            pass

    def _on_delete_key(self, event):
        try:
            idx = getattr(self, '_selected_carrito_index', None)
            if idx is None:
                return
            if 0 <= idx < len(self.carrito):
                # si hay más de 1 unidad, decrementar en 1; si no, eliminar la línea
                if self.carrito[idx].get('cantidad', 1) > 1:
                    self.carrito[idx]['cantidad'] -= 1
                    # mantener la selección en la misma línea
                else:
                    del self.carrito[idx]
                    # limpiar selección si el item desaparece
                    try:
                        self.lista_productos._textbox.tag_remove('selected', '1.0', 'end')
                    except Exception:
                        pass
                    self._selected_carrito_index = None
                self.actualizar_visor()
        except Exception as e:
            print(f"Error al eliminar item: {e}")

    # --- FUNCIONES DE COBRO ---
    def abrir_cobro_efectivo(self):
        if not getattr(self, 'cajero_activo', None):
            messagebox.showwarning('Atención', 'Debe identificarse como cajero para realizar ventas')
            return

        if not self.carrito:
            print("El carrito está vacío, no se puede cobrar.")
            return

        # Mostrar entrada de efectivo
        self.lbl_efectivo.pack()
        self.entry_efectivo.pack()
        # iniciar buffer vacío cuando se abre el cobro
        self._cash_buffer = ""
        self.efectivo_var.set("")
        self.entry_efectivo.focus()
        self.entry_efectivo.delete(0, 'end')
        self._awaiting_final_confirmation = False

    def _cobrar_tarjeta(self):
        """Procesa un cobro con tarjeta: seguridad, confirmación y finalización."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            if not getattr(self, 'carrito', None):
                messagebox.showwarning('Atención', 'El carrito está vacío')
                return
            # calcular total
            try:
                total = self._total_carrito()
            except Exception:
                total = 0.0

            confirmar = messagebox.askyesno('Confirmar', '¿Finalizar venta con TARJETA?')
            if not confirmar:
                return

            # finalizar venta: pasar total como efectivo para registrar importe, cambio=0
            try:
                self.limpiar_tras_venta(efectivo=total, cambio=0.0, forma_pago='TARJETA')
            except Exception:
                pass
        except Exception:
            logging.exception('Error procesando cobro con tarjeta')

    def _cobrar_web(self):
        """Procesa un cobro via web: seguridad, confirmación y finalización."""
        try:
            ok = self._ensure_cajero_identificado()
            if not ok:
                return
            if not getattr(self, 'carrito', None):
                messagebox.showwarning('Atención', 'El carrito está vacío')
                return
            try:
                total = self._total_carrito()
            except Exception:
                total = 0.0

            confirmar = messagebox.askyesno('Confirmar', '¿Finalizar venta con WEB?')
            if not confirmar:
                return

            try:
                forma = 'WEB'
                # force uppercase and trim spaces
                forma_forzada = (forma or '').strip().upper()
                self.limpiar_tras_venta(efectivo=total, cambio=0.0, forma_pago=forma_forzada)
            except Exception:
                logging.exception('Error finalizando cobro WEB')
        except Exception:
            logging.exception('Error procesando cobro WEB')

    def _on_global_key(self, event):
        """
        Captura teclas numéricas globales para rellenar el campo de efectivo.
        - Ignora si el foco está en otro Entry/Text distinto del entry_efectivo.
        - Digitos y separador decimal se acumulan en _cash_buffer.
        - BackSpace borra y Enter confirma (procesa el cobro).
        """
        try:
            focused = self.controller.focus_get()
            # si el foco está en un entry/text distinto del entry_efectivo, no interferir
            if focused is not None and focused is not self.entry_efectivo:
                cls = focused.winfo_class().lower()
                if 'entry' in cls or 'text' in cls:
                    return

            ch = event.char
            key = event.keysym

            # Enter: si hay buffer, fijar valor y pedir confirmación (doble Enter)
            if key in ("Return", "KP_Enter"):
                if self._cash_buffer:
                    try:
                        val = float(self._cash_buffer.replace(",", "."))
                        # mostrar con 2 decimales
                        self.efectivo_var.set(f"{val:.2f}")
                        # if not already awaiting confirmation, change label and wait for second Enter
                        if not getattr(self, '_awaiting_final_confirmation', False):
                            self._awaiting_final_confirmation = True
                            try:
                                total = self._total_carrito()
                                cambio = val - total
                                self.lbl_efectivo.configure(text=f"Pulsa Enter para confirmar — Efectivo: {val:.2f}€ | Total: {total:.2f}€ | Cambio: {cambio:.2f}€", text_color="yellow")
                            except Exception:
                                pass
                            # clear buffer but keep amount shown
                            self._cash_buffer = ""
                            return
                        else:
                            # second Enter -> process
                            try:
                                self.procesar_efectivo(None)
                            except Exception:
                                pass
                    except Exception:
                        pass
                # limpiar buffer
                self._cash_buffer = ""
                return

            # Backspace
            if key == "BackSpace":
                self._cash_buffer = self._cash_buffer[:-1]
                self.efectivo_var.set(self._cash_buffer)
                return

            # aceptar dígitos y separador decimal
            if ch and (ch.isdigit() or ch in (".", ",")):
                # si el entry no está visible, abrir cobro para que se muestre
                try:
                    if not self.entry_efectivo.winfo_ismapped():
                        self.abrir_cobro_efectivo()
                except Exception:
                    pass
                if ch == ",":
                    ch = "."
                self._cash_buffer += ch
                self.efectivo_var.set(self._cash_buffer)
        except Exception:
            pass

    def procesar_efectivo(self, event):
        try:
            # If not yet confirmed, set awaiting flag and prompt
            if not getattr(self, '_awaiting_final_confirmation', False):
                try:
                    # try to show entered amount and computed change
                    val = 0.0
                    try:
                        val = float(self.entry_efectivo.get().replace(',', '.'))
                    except Exception:
                        pass
                    total = self._total_carrito()
                    cambio = val - total
                    self._awaiting_final_confirmation = True
                    self.lbl_efectivo.configure(text=f"Pulsa Enter para confirmar — Efectivo: {val:.2f}€ | Total: {total:.2f}€ | Cambio: {cambio:.2f}€", text_color="yellow")
                except Exception:
                    pass
                return

            efectivo = float(self.entry_efectivo.get())
            total = self._total_carrito()
            if efectivo >= total:
                cambio = efectivo - total
                # specify payment method as EFECTIVO
                self.limpiar_tras_venta(efectivo, cambio, forma_pago='EFECTIVO')
                # Ocultar entrada
                self.lbl_efectivo.pack_forget()
                self.entry_efectivo.pack_forget()
                self._awaiting_final_confirmation = False
            else:
                self.lbl_efectivo.configure(text="Efectivo insuficiente", text_color="red")
                self.after(2000, lambda: self.lbl_efectivo.configure(text="Introducir efectivo entregado:", text_color="red"))
        except ValueError:
            self.lbl_efectivo.configure(text="Cantidad inválida", text_color="red")
            self.after(2000, lambda: self.lbl_efectivo.configure(text="Introducir efectivo entregado:", text_color="red"))

    def limpiar_tras_venta(self, efectivo, cambio, forma_pago='EFECTIVO'):
        print("¡Venta completada!")
        
        # Generar el texto del ticket
        if self.carrito:
                # First: save ticket and lines using TicketService
            try:
                from datetime import datetime
                now = datetime.now().isoformat()

                total = self._total_carrito()

                # cajero text extraction (same logic as before)
                cajero = getattr(self, 'lbl_cajero', None)
                cajero_txt = ''
                try:
                    if cajero is not None:
                        raw = cajero.cget('text')
                        try:
                            raw = raw.replace('👤', '').strip()
                        except Exception:
                            pass
                        if 'Cajero' in raw:
                            try:
                                name = raw.split('Cajero')[-1]
                                name = name.lstrip(':').strip()
                                if '(' in name:
                                    name = name.split('(')[0].strip()
                                cajero_txt = name
                            except Exception:
                                cajero_txt = raw
                        else:
                            cajero_txt = raw
                except Exception:
                    cajero_txt = ''

                cliente_nombre = None
                try:
                    if getattr(self, 'cliente_actual', None):
                        cliente_nombre = self.cliente_actual.get('nombre')
                except Exception:
                    cliente_nombre = None

                if cliente_nombre:
                    try:
                        if not hasattr(self, 'fidelizacion_service'):
                            from modulos.tpv.fidelizacion_service import FidelizacionService
                            self.fidelizacion_service = FidelizacionService()
                        puntos_ganados = float(self.fidelizacion_service.calcular_puntos(self.carrito, getattr(self, 'cliente_actual', None)) or 0.0)
                    except Exception:
                        puntos_ganados = 0.0
                    try:
                        puntos_canjeados = float(getattr(self, 'puntos_a_canjear', 0.0) or 0.0)
                    except Exception:
                        puntos_canjeados = 0.0
                else:
                    puntos_ganados = 0.0
                    puntos_canjeados = 0.0

                try:
                    puntos_total_momento = None
                    cliente_id = None
                    if getattr(self, 'cliente_actual', None):
                        try:
                            cliente_id = self.cliente_actual.get('id')
                        except Exception:
                            cliente_id = None
                    if cliente_id:
                        try:
                            svc = ClienteService()
                            datos_cli = svc.obtener_por_id(cliente_id) or {}
                            saldo_actual = float(datos_cli.get('puntos_fidelidad') or 0.0)
                            puntos_total_momento = float(saldo_actual) - float(puntos_canjeados) + float(puntos_ganados)
                        except Exception:
                            puntos_total_momento = float(0.0)
                    else:
                        puntos_total_momento = float(0.0)
                except Exception:
                    puntos_total_momento = float(0.0)

                datos_ticket = {
                    'created_at': now,
                    'total': total,
                    'cajero': cajero_txt,
                    'cliente': cliente_nombre,
                    'cliente_id': cliente_id,
                    'forma_pago': forma_pago,
                    'pagado': efectivo,
                    'cambio': cambio,
                    'puntos_ganados': puntos_ganados,
                    'puntos_canjeados': puntos_canjeados,
                    'puntos_total_momento': puntos_total_momento,
                }

                ticket_id = self.ticket_service.guardar_ticket(datos_ticket, self.carrito)

            except Exception:
                ticket_id = None

            except Exception as e:
                print(f"Error guardando ticket en BD: {e}")

                # Then: print/preview only if printing is enabled in controller
            try:
                # Fetch saved ticket and lines via TicketService to avoid SQL in UI
                try:
                    datos = self.ticket_service.obtener_ticket_completo(ticket_id)
                    if datos:
                        meta = datos.get('meta') or {}
                        lines = datos.get('lineas') or []
                    else:
                        meta = None
                        lines = []
                except Exception:
                    meta = None
                    lines = []

                # Build textual ticket (header + lines + totals + pagado/cambio)
                try:
                    if meta:
                        try:
                            created_at = meta.get('created_at')
                        except Exception:
                            created_at = None
                        try:
                            cajero_meta = meta.get('cajero') or ''
                        except Exception:
                            cajero_meta = ''
                        try:
                            total_meta = float(meta.get('total') or 0.0)
                        except Exception:
                            total_meta = total
                        try:
                            ticket_no_meta = meta.get('ticket_no') or meta.get('id') or ticket_id
                        except Exception:
                            ticket_no_meta = ticket_id
                        try:
                            forma_meta = meta.get('forma_pago') or forma_pago
                        except Exception:
                            forma_meta = forma_pago
                        try:
                            pagado_meta = meta.get('pagado')
                        except Exception:
                            pagado_meta = efectivo
                        try:
                            cambio_meta = meta.get('cambio')
                        except Exception:
                            cambio_meta = cambio
                        try:
                            cliente_meta = meta.get('cliente') or ''
                        except Exception:
                            cliente_meta = ''
                    else:
                        created_at = None
                        cajero_meta = ''
                        total_meta = total
                        ticket_no_meta = ticket_id
                        forma_meta = forma_pago
                        pagado_meta = efectivo
                        cambio_meta = cambio
                        cliente_meta = ''
                except Exception:
                    created_at = None
                    cajero_meta = ''
                    total_meta = total
                    ticket_no_meta = ticket_id
                    forma_meta = forma_pago
                    pagado_meta = efectivo
                    cambio_meta = cambio
                    cliente_meta = ''

                header_lines = []
                header_lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
                header_lines.append("-"*30 + "\n")
                header_lines.append(f"FACTURA Nº: {ticket_no_meta}\n")
                try:
                    if created_at:
                        dt_disp = datetime.fromisoformat(created_at).strftime("%d/%m/%Y %H:%M")
                        header_lines.append(f"Fecha: {dt_disp}\n")
                except Exception:
                    header_lines.append(f"Fecha: {created_at or ''}\n")
                header_lines.append(f"Cajero: {cajero_meta}\n")
                header_lines.append(f"Cliente: {cliente_meta or ''}\n")
                header_lines.append("-"*30 + "\n")

                body_lines = []
                for ln in lines:
                    try:
                        sku = ln.get('sku') if isinstance(ln, dict) else (ln[0] if len(ln) > 0 else None)
                        nombre = ln.get('nombre') if isinstance(ln, dict) else (ln[1] if len(ln) > 1 else '')
                        cantidad_l = ln.get('cantidad') if isinstance(ln, dict) else (ln[2] if len(ln) > 2 else 0)
                        precio_l = ln.get('precio') if isinstance(ln, dict) else (ln[3] if len(ln) > 3 else 0)
                        iva_l = ln.get('iva') if isinstance(ln, dict) else (ln[4] if len(ln) > 4 else 0)
                    except Exception:
                        nombre = ''
                        cantidad_l = 0
                        precio_l = 0
                    try:
                        cantidad_show = int(cantidad_l) if isinstance(cantidad_l, float) and float(cantidad_l).is_integer() else cantidad_l
                    except Exception:
                        cantidad_show = cantidad_l
                    try:
                        body_lines.append(f"{cantidad_show}x {nombre}  {float(precio_l):.2f}\n")
                    except Exception:
                        body_lines.append(f"{cantidad_show}x {nombre}  {precio_l}\n")

                totals_lines = []
                totals_lines.append("-"*30 + "\n")
                try:
                    totals_lines.append(f"TOTAL: {total_meta:.2f}\n")
                except Exception:
                    totals_lines.append(f"TOTAL: {total_meta}\n")
                if pagado_meta is not None:
                    try:
                        totals_lines.append(f"{forma_meta}: {pagado_meta:.2f}\n")
                    except Exception:
                        totals_lines.append(f"{forma_meta}: {pagado_meta}\n")
                if cambio_meta is not None:
                    try:
                        totals_lines.append(f"CAMBIO: {cambio_meta:.2f}\n")
                    except Exception:
                        totals_lines.append(f"CAMBIO: {cambio_meta}\n")

                ticket_texto = ''.join(header_lines) + ''.join(body_lines) + ''.join(totals_lines) + "\n¡Gracias por tu compra!\n"

                # Si hay un cliente asignado, procesar canje y puntos, y añadir información al ticket
                try:
                    if self.cliente_actual is not None:
                        # extra info block
                        try:
                            cliente_id = None
                            try:
                                cliente_id = self.cliente_actual.get('id')
                            except Exception:
                                cliente_id = None
                            try:
                                cli_svc = ClienteService()
                            except Exception:
                                cli_svc = None

                            extra = []
                            extra.append('\n' + ('-'*20) + '\n')

                            # 1) Si existe canje de puntos, restarlos primero
                            try:
                                if getattr(self, 'puntos_a_canjear', 0) and float(self.puntos_a_canjear) > 0 and cliente_id and cli_svc:
                                    try:
                                        cli_svc.sumar_puntos(cliente_id, -float(self.puntos_a_canjear))
                                        extra.append(f"Puntos canjeados: -{float(self.puntos_a_canjear):.2f} pts\n")
                                    except Exception:
                                        logging.exception('No se pudieron restar puntos al cliente id=%s', cliente_id)
                            except Exception:
                                pass

                            # 2) Calcular puntos ganados por la compra (solo si hay cliente)
                            try:
                                if not hasattr(self, 'fidelizacion_service'):
                                    from modulos.tpv.fidelizacion_service import FidelizacionService
                                    self.fidelizacion_service = FidelizacionService()
                                puntos = self.fidelizacion_service.calcular_puntos(self.carrito, getattr(self, 'cliente_actual', None))
                            except Exception:
                                puntos = 0.0

                            # 3) Registrar puntos ganados y gasto
                            saldo = None
                            if cliente_id and cli_svc:
                                try:
                                    if puntos and float(puntos) > 0:
                                        try:
                                            cli_svc.sumar_puntos(cliente_id, float(puntos))
                                        except Exception:
                                            logging.exception('No se pudieron sumar puntos al cliente id=%s', cliente_id)
                                    try:
                                        cli_svc.registrar_gasto(cliente_id, float(total_meta or total))
                                    except Exception:
                                        logging.exception('No se pudo registrar gasto para cliente id=%s', cliente_id)
                                    try:
                                        updated = cli_svc.obtener_por_id(cliente_id)
                                        saldo = updated.get('puntos_fidelidad') if updated else None
                                    except Exception:
                                        saldo = None
                                except Exception:
                                    pass

                            # 4) Añadir línea de puntos ganados si aplica
                            try:
                                if puntos and float(puntos) > 0:
                                    extra.append(f"Puntos ganados en esta compra: {float(puntos):.2f}\n")
                            except Exception:
                                try:
                                    extra.append(f"Puntos ganados en esta compra: {puntos}\n")
                                except Exception:
                                    pass

                            # 5) Asegurar que saldo refleje los cambios y añadir línea de saldo
                            try:
                                if saldo is None and cliente_id and cli_svc:
                                    try:
                                        updated = cli_svc.obtener_por_id(cliente_id)
                                        saldo = updated.get('puntos_fidelidad') if updated else None
                                    except Exception:
                                        saldo = None
                            except Exception:
                                pass
                            try:
                                extra.append(f"Saldo total de puntos: {float(saldo):.2f}\n" if saldo is not None else "Saldo total de puntos: \n")
                            except Exception:
                                extra.append(f"Saldo total de puntos: {saldo if saldo is not None else ''}\n")

                            ticket_texto = ticket_texto + ''.join(extra)
                        except Exception:
                            logging.exception('Error proceso fidelización en ticket')
                except Exception:
                    logging.exception('Error proceso fidelización en ticket - envoltura')

                if getattr(self.controller, 'imprimir_tickets_enabled', False):
                    # Prefer preview_ticket on macOS, otherwise try direct print
                    if sys.platform == 'darwin' and preview_ticket is not None:
                        try:
                            preview_ticket(self, ticket_texto, modo='ventana')
                        except Exception:
                            try:
                                preview_ticket(None, ticket_texto, modo='terminal')
                            except Exception:
                                pass
                    else:
                        try:
                            impresion_service.imprimir_ticket(ticket_texto, abrir_cajon=True)
                        except Exception:
                            try:
                                if preview_ticket is not None:
                                    preview_ticket(None, ticket_texto, modo='terminal')
                            except Exception:
                                pass
                else:
                    try:
                        print('Impresión automática desactivada; ticket guardado en BD.')
                    except Exception:
                        pass
            except Exception:
                pass
        
        # Limpiar carrito
        # Reset puntos_a_canjear antes de limpiar carrito y vistas
        try:
            self.puntos_a_canjear = 0
        except Exception:
            pass
        self.carrito = []
        self.actualizar_visor()
        try:
            self._desvincular_cliente()
        except Exception:
            pass

    def abrir_selector_sin_codigo(self):
        """Renderiza el selector de productos sin código dentro del área disponible"""
        try:
            if not getattr(self, 'cajero_activo', None):
                messagebox.showwarning('Atención', 'Debe identificarse como cajero para realizar ventas')
                return
        except Exception:
            pass
        selector = SelectorSinCodigo(self.agregar_producto_sin_codigo)
        selector.render_in_frame(self.selector_area)

    def agregar_producto_sin_codigo(self, producto_id, precio, nombre):
        """Agrega un producto al carrito desde el selector sin código"""
        try:
            # Use ProductoService to fetch product details
            if not hasattr(self, 'producto_service'):
                from modulos.almacen.producto_service import ProductoService
                self.producto_service = ProductoService()
            try:
                resultado = self.producto_service.obtener_por_id(producto_id)
            except Exception:
                resultado = None


            if resultado:
                # ProductoService devuelve un dict con claves estables
                pvp_variable = resultado.get('pvp_variable', 0)
                # El precio real está ahora en la clave 'precio'
                precio_base = resultado.get('precio')
                if pvp_variable:
                    try:
                        val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                        if val is None:
                            return
                        precio_base = float(val)
                    except Exception:
                        pass

                # Asegurar que precio sea numérico
                try:
                    precio_base = float(precio_base) if precio_base is not None else 0.0
                except Exception:
                    precio_base = 0.0

                producto = {
                    "nombre": resultado.get('nombre'),
                    "precio": precio_base,
                    "sku": resultado.get('sku'),
                    "iva": resultado.get('tipo_iva'),
                    "id": resultado.get('id'),
                    "cantidad": 1
                }

                encontrado = False
                for item in self.carrito:
                    if item['id'] == producto['id']:
                        item['cantidad'] += 1
                        encontrado = True
                        break

                if not encontrado:
                    self.carrito.append(producto)

                self.actualizar_visor()
        except Exception as e:
            print(f"Error al agregar producto: {e}")

    def _mostrar_dialogo_canje(self, max_puntos):
        """Crea una ventana flotante grande para introducir los puntos."""
        result = {'value': None}
        # Crear ventana
        win = ctk.CTkToplevel(self)
        win.title('Canjear Puntos')
        win.geometry('450x300')
        win.transient(self) # Se queda encima de la principal
        win.grab_set()      # Bloquea el resto de la app hasta cerrar

        # Títulos
        ctk.CTkLabel(win, text='¿Cuántos puntos canjear?', font=('Arial', 22, 'bold')).pack(pady=(25,5))
        ctk.CTkLabel(win, text=f'Máximo disponible: {max_puntos:.2f} pts', font=('Arial', 14)).pack(pady=(0,20))

        # Caja de texto GIGANTE
        entry_var = ctk.StringVar()
        entry = ctk.CTkEntry(win, textvariable=entry_var, font=('Arial', 32), justify='center', height=60)
        entry.pack(fill='x', padx=50, pady=10)
        entry.focus_set()

        # Etiqueta para errores (roja)
        err_lbl = ctk.CTkLabel(win, text='', text_color='red', font=('Arial', 13))
        err_lbl.pack()

        def _validar_y_cerrar():
            # El truco de la coma: la cambiamos por un punto aquí
            texto = entry_var.get().replace(',', '.')
            try:
                val = float(texto)
                if val < 0: raise ValueError
                if val > max_puntos:
                    err_lbl.configure(text=f'Error: El cliente solo tiene {max_puntos:.2f} pts')
                    return
                result['value'] = val
                win.destroy()
            except ValueError:
                err_lbl.configure(text='Introduce un número válido (ej: 0.50)')

        # Botones de acción
        btn_frame = ctk.CTkFrame(win, fg_color='transparent')
        btn_frame.pack(pady=25)
        ctk.CTkButton(btn_frame, text='ACEPTAR', width=160, height=45, fg_color='#2ecc71', command=_validar_y_cerrar).pack(side='left', padx=10)
        ctk.CTkButton(btn_frame, text='CANCELAR', width=160, height=45, fg_color='#555', command=win.destroy).pack(side='left', padx=10)

        # Hacer que 'Enter' también sirva para aceptar
        entry.bind('<Return>', lambda e: _validar_y_cerrar())
        
        self.wait_window(win)
        return result['value']