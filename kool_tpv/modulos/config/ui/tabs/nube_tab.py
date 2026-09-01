import tkinter as tk
import customtkinter as ctk
import logging
import os
from typing import Optional
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.services.cloud_backup_service import CloudBackupService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL
from kool_tpv.paths import DB_PATH
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)

class NubeTab(ctk.CTkFrame):
    """Panel de configuración de Backup en la Nube (Google Drive)."""

    def __init__(self, parent, db=None, **kwargs):
        self.module_name = 'config'
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {}
        
        bg = self.colors.get('background', COLOR_BG_TERMINAL)
        super().__init__(parent, fg_color=bg, **kwargs)
        
        self.parent = parent
        
        # Inicializar servicios de base de datos
        if db:
            self.db = db
            self._db_shared = True
        else:
            # Si no nos pasan la DB, usamos la ruta centralizada
            self.db = Database(str(DB_PATH))
            self.db.connect()
            self._db_shared = False

        self.config_repo = ConfiguracionRepository(self.db)
        
        # Servicio de Backup
        self.backup_service = CloudBackupService(self.db)
        
        # Variables de UI
        self._backup_enabled = tk.BooleanVar()
        self._folder_name = tk.StringVar()
        self._linked_email = tk.StringVar(value=self.backup_service.obtener_email_vinculado() or "No vinculada")
        self._account_linked = tk.BooleanVar(value=os.path.exists(self.backup_service.token_path))
        
        self._load_settings()
        self._build()

    def _load_settings(self):
        """Carga los ajustes desde la base de datos."""
        try:
            settings = self.config_repo.obtener_multiples(['backup_drive_enabled', 'backup_drive_folder_name'])
            self._backup_enabled.set(settings.get('backup_drive_enabled', '0') == '1')
            self._folder_name.set(settings.get('backup_drive_folder_name', 'KOOL_TPV_Backups'))
        except Exception:
            logger.exception("Error cargando ajustes de nube")

    def _save_settings(self, *_):
        """Guarda los ajustes en la base de datos."""
        try:
            self.config_repo.guardar_multiples({
                'backup_drive_enabled': '1' if self._backup_enabled.get() else '0',
                'backup_drive_folder_name': self._folder_name.get()
            })
            ToastWidget.show(self.parent, 'Ajustes guardados', tipo='success')
        except Exception:
            logger.exception("Error guardando ajustes de nube")
            ToastWidget.show(self.parent, 'Error al guardar', tipo='error')

    def _build(self):
        bg = self.colors.get('background', COLOR_BG_TERMINAL)
        lbl_font = get_font('label', module=self.module_name)
        title_font = get_font('label', module=self.module_name)
        entry_kwargs = {
            "fg_color": bg,
            "text_color": self.colors.get('text', '#FFFFFF'),
            "border_width": 2,
            "border_color": self.colors.get('border', self.colors.get('primary', '#3498db')),
            "corner_radius": 4,
            "font": get_font('entry', module=self.module_name),
        }

        scroll = ctk.CTkScrollableFrame(self, fg_color=bg, corner_radius=0)
        scroll.pack(fill=tk.BOTH, expand=True)

        # --- SECCIÓN CUENTA ---
        acc_frame = ctk.CTkFrame(scroll, fg_color=bg)
        acc_frame.pack(fill='x', padx=12, pady=12)
        
        ctk.CTkLabel(acc_frame, text='GESTIÓN DE CUENTA GOOGLE', 
                     font=title_font, text_color=self.colors.get('secondary', '#FFB74D')).pack(anchor='w', padx=6, pady=(0, 10))

        info_row = ctk.CTkFrame(acc_frame, fg_color='transparent')
        info_row.pack(fill='x', padx=6)

        ctk.CTkLabel(info_row, text='Cuenta vinculada:', font=lbl_font, text_color=self.colors.get('text')).pack(side='left')
        
        self.email_lbl = ctk.CTkLabel(info_row, textvariable=self._linked_email, 
                                     font=get_font('entry', module=self.module_name), 
                                     text_color=self.colors.get('primary'))
        self.email_lbl.pack(side='left', padx=10)

        btn_row = ctk.CTkFrame(acc_frame, fg_color='transparent')
        btn_row.pack(fill='x', padx=6, pady=(15, 5))

        self.btn_link = ButtonFactory.create_button(
            btn_row,
            text='VINCULAR CUENTA',
            command=self._vincular_cuenta,
            module="config",
            palette_key="primary",
            style_key="action_success"
        )
        self.btn_link.pack(side='left', padx=(0, 10))

        self.btn_unlink = ButtonFactory.create_button(
            btn_row,
            text='DESVINCULAR / CAMBIAR',
            command=self._desvincular_cuenta,
            module="config",
            palette_key="accent",
            style_key="action_success"
        )
        self.btn_unlink.pack(side='left')

        # --- SECCIÓN CONFIGURACIÓN ---
        cfg_frame = ctk.CTkFrame(scroll, fg_color=bg)
        cfg_frame.pack(fill='x', padx=12, pady=12)

        ctk.CTkLabel(cfg_frame, text='CONFIGURACIÓN DE BACKUP', 
                     font=title_font, text_color=self.colors.get('secondary', '#FFB74D')).pack(anchor='w', padx=6, pady=(0, 10))

        # Checkbox habilitar
        sw_row = ctk.CTkFrame(cfg_frame, fg_color='transparent')
        sw_row.pack(fill='x', padx=6, pady=5)
        
        self.sw_backup = ctk.CTkCheckBox(
            sw_row, text="Activar copia de seguridad automática al cerrar",
            variable=self._backup_enabled,
            command=self._save_settings,
            fg_color=self.colors.get('primary', '#FF9800'),
            hover_color=self.colors.get('secondary', '#F57C00'),
            font=lbl_font,
            text_color=self.colors.get('text')
        )
        self.sw_backup.pack(side='left')

        # Carpeta
        folder_row = ctk.CTkFrame(cfg_frame, fg_color='transparent')
        folder_row.pack(fill='x', padx=6, pady=15)
        
        ctk.CTkLabel(folder_row, text='Nombre de la carpeta en Drive:', font=lbl_font, text_color=self.colors.get('text')).pack(side='left', padx=(0, 15))
        
        self.e_folder = ctk.CTkEntry(folder_row, textvariable=self._folder_name, width=300, **entry_kwargs)
        self.e_folder.pack(side='left')
        self.e_folder.bind("<FocusOut>", self._save_settings)
        self.e_folder.bind("<Return>", self._save_settings)

        # --- SECCIÓN ACCIONES ---
        act_frame = ctk.CTkFrame(scroll, fg_color=bg)
        act_frame.pack(fill='x', padx=12, pady=12)

        ctk.CTkLabel(act_frame, text='ACCIONES MANUALES', 
                     font=title_font, text_color=self.colors.get('secondary', '#FFB74D')).pack(anchor='w', padx=6, pady=(0, 10))

        self.btn_test = ButtonFactory.create_button(
            act_frame,
            text='PROBAR SUBIDA AHORA',
            command=self._probar_subida,
            module="config",
            palette_key="secondary",
            style_key="action_success"
        )
        self.btn_test.pack(side='left', padx=6, pady=5)

    def _vincular_cuenta(self):
        """Dispara el flujo de autenticación de Google."""
        ToastWidget.show(self.parent, "Iniciando autenticación...", tipo='info')
        self.update()
        
        success = self.backup_service.autenticar()
        if success:
            self._account_linked.set(True)
            email = self.backup_service.obtener_email_vinculado() or "Cuenta vinculada"
            self._linked_email.set(email)
            ToastWidget.show(self.parent, "Cuenta vinculada con éxito", tipo='success')
        else:
            ToastWidget.show(self.parent, "Error al vincular cuenta", tipo='error')

    def _desvincular_cuenta(self):
        """Elimina la vinculación de la cuenta actual."""
        if self.backup_service.desvincular_cuenta():
            self._account_linked.set(False)
            self._linked_email.set("No vinculada")
            ToastWidget.show(self.parent, "Cuenta desvinculada", tipo='info')
        else:
            ToastWidget.show(self.parent, "Error al desvincular", tipo='error')

    def _probar_subida(self):
        """Realiza una subida de prueba de la base de datos actual."""
        if not self._account_linked.get():
            ToastWidget.show(self.parent, "Primero vincula tu cuenta", tipo='warning')
            return

        ToastWidget.show(self.parent, "Subiendo base de datos...", tipo='info')
        self.update()
        
        db_path = "/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/base_datos/kool_bd.db"
        
        if not os.path.exists(db_path):
            ToastWidget.show(self.parent, "Base de datos no encontrada", tipo='error')
            return

        success = self.backup_service.subir_archivo(db_path, self._folder_name.get())
        if success:
            ToastWidget.show(self.parent, "Prueba correcta", tipo='success')
        else:
            ToastWidget.show(self.parent, "Error en la subida", tipo='error')

    def destroy(self):
        """Cerrar la conexión a la DB solo si la creamos nosotros."""
        try:
            if hasattr(self, 'db') and not getattr(self, '_db_shared', False):
                self.db.close_connection()
        except Exception:
            pass
        super().destroy()
