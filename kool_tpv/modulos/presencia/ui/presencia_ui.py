"""PresenciaUI: Interfaz para control de fichajes (entrada/salida)."""
import logging
from datetime import datetime, timezone, timedelta
import customtkinter as ctk
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.dialogs import show_password_dialog
from kool_tpv.utils.dialogs.input_dialog import InputDialog
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.modulos.presencia.presencia_service import PresenciaService
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.time_utils import format_ddmmyyyy, utc_str_to_local_str
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

logger = logging.getLogger(__name__)

class PresenciaUI(ctk.CTkFrame):
    def __init__(self, parent, db, view=None):
        super().__init__(parent)
        self.db = db
        self.view = view
        
        # Servicios
        self.usuario_service = UsuarioService(db)
        self.auth_service = AuthService(db)
        self.presencia_service = PresenciaService(db)
        
        # Estado local
        self.selected_user = None
        
        self._setup_ui()

    def _format_duracion(self, minutos: int | None) -> str:
        """Convierte minutos a formato legible (Xh Ym o X min)."""
        if minutos is None:
            return "..."
        if minutos < 0: return "0 min"
        if minutos < 60:
            return f"{minutos} min"
        h = minutos // 60
        m = minutos % 60
        if m == 0:
            return f"{h}h"
        return f"{h}h {m}m"

    def _setup_ui(self):
        # Título
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="CONTROL DE PRESENCIA", 
            font=get_font("title"),
            text_color="#00FF00"
        )
        lbl_titulo.pack(pady=20)

        # Split Container: Izquierda (Chips) | Derecha (Acciones)
        self.split_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Panel Izquierdo: Lista de Usuarios (Chips)
        self.left_panel = ctk.CTkFrame(self.split_frame, fg_color="#1a1a1a", width=500)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.chips_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.chips_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self._create_user_chips()

        # Panel Derecho: Ficha del Usuario Seleccionado
        self.right_panel = ctk.CTkFrame(self.split_frame, fg_color="#1a1a1a", width=400)
        self.right_panel.pack(side="right", fill="both", expand=True)
        
        self.detail_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.detail_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Mensaje inicial en panel derecho
        self.lbl_placeholder = ctk.CTkLabel(
            self.detail_container, 
            text="SELECCIONA UN USUARIO\nPARA FICHAR",
            font=get_font("placeholder", module="presencia"),
            text_color="#666666"
        )
        self.lbl_placeholder.pack(expand=True)

    def _create_user_chips(self):
        """Crea los chips de usuarios con indicador visual de estado (●/○).
        El punto tiene color propio (verde=trabajando, rojo=no trabajando).
        El nombre usa el color definido por el estilo 'cajero_chip'.
        """
        for w in self.chips_scroll.winfo_children():
            w.destroy()

        usuarios = self.usuario_service.get_all_usuarios() or []

        for i, user in enumerate(usuarios):
            row = i // 2
            col = i % 2
            user_id = user.get("id")
            nombre = user.get("nombre")

            estado = self.presencia_service.get_estado_usuario(user_id)
            trabajando = estado.get("trabajando", False)

            # Contenedor de celda para combinar dot + botón
            cell = ctk.CTkFrame(self.chips_scroll, fg_color="transparent")
            cell.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            # Indicador de estado con color diferenciado
            dot_color = "#00FF00" if trabajando else "#FF0000"
            dot = ctk.CTkLabel(
                cell,
                text="●" if trabajando else "○",
                text_color=dot_color,
                font=("Segoe UI Emoji", 42)
            )
            dot.pack(side="left", padx=(0, 10), anchor="center")

            # Botón con solo el nombre (color del estilo)
            btn = ButtonFactory.create_button(
                parent=cell,
                text=nombre,
                style_key="cajero_chip",
                command=lambda uid=user_id, n=nombre: self._on_user_click(uid, n)
            )
            btn.pack(side="left", fill="both", expand=True)

        for c in range(2):
            self.chips_scroll.grid_columnconfigure(c, weight=1)

    def _refresh_user_chips(self):
        """Recarga los chips para reflejar cambios de estado en tiempo real."""
        self._create_user_chips()

    def _on_user_click(self, user_id, nombre):
        """Al pulsar un usuario, pedir contraseña. Si es válida, dispara automáticamente
        el fichaje (entrada o salida según estado actual) y muestra toda la información.
        No se requiere pulsar ningún botón adicional de 'Fichar'.
        """
        password = show_password_dialog(
            self.winfo_toplevel(),
            titulo="Autenticar",
            mensaje=f"Introduce la contraseña de {nombre}:"
        )

        if not password:
            self._show_placeholder()
            return

        if self.auth_service.validate_user_password(user_id, password):
            self.selected_user = {"id": user_id, "nombre": nombre}
            
            # Chequeo de seguridad: ¿Es un olvido de ayer o antes?
            estado = self.presencia_service.get_estado_usuario(user_id)
            es_olvido = False
            if estado["trabajando"] and estado["desde"]:
                try:
                    local_desde_chk = utc_str_to_local_str(estado["desde"]) if estado["desde"] else ''
                    dt_entrada = datetime.strptime(local_desde_chk, '%Y-%m-%d %H:%M:%S')
                    horas = (datetime.now() - dt_entrada).total_seconds() / 3600
                    if horas > 20:
                        es_olvido = True
                except Exception:
                    pass

            if not es_olvido:
                # Password dispara la acción directamente (comportamiento normal)
                res = self.presencia_service.fichar(user_id)
                self._refresh_user_chips()
                if res.get("success"):
                    tipo = "ENTRADA" if res.get("tipo") == "entrada" else "SALIDA"
                    ToastWidget.show(self.winfo_toplevel(), f"{tipo} REGISTRADA CORRECTAMENTE", tipo="success")
                else:
                    ToastWidget.show(self.winfo_toplevel(), f"ERROR AL FICHAR: {res.get('error')}", tipo="error")
                self._show_user_detail(last_action=res if res.get("success") else None)
            else:
                # Si es un olvido, NO fichamos. Mostramos el detalle para que use el botón CORREGIR.
                self._refresh_user_chips()
                self._show_user_detail()
        else:
            ToastWidget.show(self.winfo_toplevel(), 'CONTRASEÑA INCORRECTA', tipo='error')
            self._show_placeholder()

    def _on_corregir_click(self, sesion_id):
        """Maneja el clic en corregir olvido. Pide hora de salida y nota."""
        # 1. Pedir Hora
        dialog_hora = InputDialog(
            self.winfo_toplevel(),
            titulo="CORREGIR OLVIDO",
            mensaje="¿A qué hora saliste ayer? (HH:MM)",
            valor_defecto="18:00"
        )
        hora = dialog_hora.get_input()
        if not hora: return

        # Validar formato básico HH:MM
        if ":" not in hora or len(hora.split(":")[0]) > 2:
            ToastWidget.show(self.winfo_toplevel(), 'FORMATO DE HORA INVÁLIDO (USA HH:MM)', tipo='error')
            return

        # 2. Pedir Nota
        dialog_nota = InputDialog(
            self.winfo_toplevel(),
            titulo="MOTIVO",
            mensaje="Escribe una breve nota del olvido:",
            valor_defecto="Olvido de fichaje"
        )
        nota = dialog_nota.get_input() or "Corrección manual"

        # 3. Procesar
        estado = self.presencia_service.get_estado_usuario(self.selected_user["id"])
        local_desde_corr = utc_str_to_local_str(estado["desde"]) if estado["desde"] else ''
        partes = local_desde_corr.split()
        fecha_solo = partes[0]  # YYYY-MM-DD
        hora_entrada = partes[1][:5] if len(partes) > 1 else ''

        # Si la hora de salida es menor que la de entrada, cruzó medianoche
        if hora_entrada and hora < hora_entrada:
            dt_fecha = datetime.strptime(fecha_solo, '%Y-%m-%d')
            fecha_solo = (dt_fecha + timedelta(days=1)).strftime('%Y-%m-%d')

        timestamp_salida_local = f"{fecha_solo} {hora}:00"

        # Convertir a UTC para almacenamiento (la entrada se guardó en UTC)
        dt_local = datetime.strptime(timestamp_salida_local, '%Y-%m-%d %H:%M:%S')
        dt_utc = dt_local.astimezone(timezone.utc)
        timestamp_salida_utc = dt_utc.strftime('%Y-%m-%d %H:%M:%S')

        res = self.presencia_service.corregir_fichaje(sesion_id, timestamp_salida_utc, nota)
        
        if res.get("success"):
            ToastWidget.show(self.winfo_toplevel(), "SESIÓN CORREGIDA. YA PUEDES FICHAR HOY.", tipo="success")
            self._refresh_user_chips()
            self._show_user_detail() # Refrescar detalle para que salga el botón de entrada normal
        else:
            ToastWidget.show(self.winfo_toplevel(), f'NO SE PUDO CORREGIR: {res.get("error")}', tipo='error')

    def _show_placeholder(self):
        for w in self.detail_container.winfo_children():
            w.destroy()
        self.lbl_placeholder = ctk.CTkLabel(
            self.detail_container, 
            text="SELECCIONA UN USUARIO\nPARA FICHAR",
            font=get_font("placeholder", module="presencia"),
            text_color="#666666"
        )
        self.lbl_placeholder.pack(expand=True)

    def _show_user_detail(self, last_action: dict | None = None):
        """Muestra toda la información tras el fichaje automático disparado por password.
        No hay botón de fichar: el password ya ejecutó la acción.
        """
        # Limpiar panel antes de mostrar nuevo contenido
        for w in self.detail_container.winfo_children():
            w.destroy()

        uid = self.selected_user["id"]
        nombre = self.selected_user["nombre"]

        estado = self.presencia_service.get_estado_usuario(uid)

        # Nombre Usuario
        ctk.CTkLabel(self.detail_container, text=nombre, font=get_font("nombre", module="presencia")).pack(pady=(0, 10))

        # Confirmación de la acción que acaba de ocurrir (si viene de password)
        if last_action and last_action.get("success"):
            tipo = "ENTRADA" if last_action.get("tipo") == "entrada" else "SALIDA"
            ctk.CTkLabel(
                self.detail_container,
                text=f"ACCIÓN: {tipo} REGISTRADA",
                font=get_font("accion", module="presencia"),
                text_color="#00FF00"
            ).pack(pady=(0, 8))

        # Estado Actual
        color_estado = "#00FF00" if estado["trabajando"] else "#FF0000"
        ctk.CTkLabel(
            self.detail_container,
            text=f"ESTADO: {estado['texto']}",
            font=get_font("estado", module="presencia"),
            text_color=color_estado
        ).pack(pady=5)

        if estado["desde"]:
            # Detectar si la sesión es de un día anterior (olvido)
            es_antigua = False
            try:
                local_desde_ant = utc_str_to_local_str(estado["desde"]) if estado["desde"] else ''
                dt_entrada = datetime.strptime(local_desde_ant, '%Y-%m-%d %H:%M:%S')
                horas = (datetime.now() - dt_entrada).total_seconds() / 3600
                if horas > 20:
                    es_antigua = True
            except Exception:
                pass

            local_desde = utc_str_to_local_str(estado['desde']) if estado['desde'] else ''
            ctk.CTkLabel(
                self.detail_container,
                text=f"Desde: {format_ddmmyyyy(local_desde, include_time=True)}",
                font=get_font("desde", module="presencia"),
                text_color="#AAAAAA"
            ).pack(pady=2)

            if es_antigua:
                ctk.CTkLabel(
                    self.detail_container,
                    text="¡SESIÓN OLVIDADA DE AYER!",
                    font=get_font("estado", module="presencia"),
                    text_color="#FF0000"
                ).pack(pady=(10, 0))

                btn_corregir = ButtonFactory.create_button(
                    parent=self.detail_container,
                    text="CORREGIR OLVIDO",
                    style_key="action_warning",
                    command=lambda sid=estado["sesion_id"]: self._on_corregir_click(sid)
                )
                btn_corregir.pack(pady=10, padx=40, fill="x")

        # Historial Reciente (Tabla)
        ctk.CTkLabel(self.detail_container, text="ÚLTIMOS MOVIMIENTOS", font=get_font("historial_header", module="presencia"), text_color="#666666").pack(pady=(20, 5))
        
        hist_list = VirtualNavList(
            self.detail_container,
            columns=[
                ('fecha', 90, 'FECHA'),
                ('entrada', 80, 'ENTRADA'),
                ('salida', 80, 'SALIDA'),
                ('duracion', 75, 'TIEMPO'),
                ('estado', 85, 'ESTADO'),
                ('notas', 150, 'NOTAS')
            ],
            module_name="presencia",
            height=200
        )
        hist_list.pack(fill="both", expand=True, padx=5)
        
        historial = self.presencia_service.get_historial(uid)
        mapped = []
        for h in historial:
            raw_in = h.get('entrada', '')
            raw_out = h.get('salida', '')
            status = h.get('estado', '').upper()
            notas = h.get('notas', '') or ''
            
            # Convertir UTC -> local
            local_in = utc_str_to_local_str(raw_in) if raw_in else ''
            local_out = utc_str_to_local_str(raw_out) if raw_out else ''
            
            # Fecha (DD-MM-YYYY)
            fecha = format_ddmmyyyy(local_in, include_time=False)
            
            # Horas (HH:MM)
            t_in = local_in.split()[1][:5] if ' ' in local_in else local_in
            t_out = "..."
            if local_out and ' ' in local_out:
                t_out = local_out.split()[1][:5]
            elif status != 'ACTIVA':
                t_out = "??:??"

            mapped.append({
                'fecha': fecha,
                'entrada': t_in,
                'salida': t_out,
                'duracion': self._format_duracion(h.get('duracion_minutos')),
                'estado': status,
                'notas': notas
            })
        
        hist_list.set_items(mapped)
