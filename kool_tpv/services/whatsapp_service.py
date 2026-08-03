import logging
import re
import urllib.parse
import webbrowser
import platform
import os
import glob
from typing import Optional, Dict, Any, List

from kool_tpv.base_datos.configuracion_repository import ConfiguracionRepository
from kool_tpv.utils.widgets.notificaciones import ToastWidget

logger = logging.getLogger(__name__)

class WhatsAppService:
    @staticmethod
    def normalizar_telefono(telefono: str) -> str:
        """
        Normaliza el teléfono para WhatsApp.
        Si empieza por +, se asume prefijo internacional.
        Si tiene 9 cifras y empieza por 6/7, se añade 34 (España).
        """
        if not telefono:
            return ""
        
        # Guardar si empezaba por +
        empezaba_por_mas = telefono.strip().startswith('+')
        
        # Eliminar todo lo que no sea número
        solo_numeros = re.sub(r'\D', '', telefono)
        
        if empezaba_por_mas:
            return solo_numeros
            
        # Si tiene 9 cifras y empieza por 6 o 7, es España
        if len(solo_numeros) == 9 and solo_numeros[0] in ('6', '7'):
            return '34' + solo_numeros
            
        return solo_numeros

    @staticmethod
    def detectar_desktop() -> bool:
        """Detecta si WhatsApp Desktop está instalado en el sistema."""
        system = platform.system()
        if system == 'Windows':
            try:
                import winreg
                # Buscar en el registro el handler del protocolo whatsapp://
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'whatsapp', 0, winreg.KEY_READ) as key:
                    # Si existe la clave, el protocolo está registrado
                    return True
            except Exception:
                pass
            
            # Fallback: buscar en rutas comunes
            possible_paths = [
                os.path.expandvars(r'%LOCALAPPDATA%\WhatsApp\WhatsApp.exe'),
                os.path.expandvars(r'%PROGRAMFILES%\WhatsApp\WhatsApp.exe'),
                os.path.expandvars(r'%PROGRAMFILES(X86)%\WhatsApp\WhatsApp.exe'),
            ]
            # También buscar en WindowsApps con glob
            windows_apps = os.path.expandvars(r'%PROGRAMFILES%\WindowsApps')
            if os.path.exists(windows_apps):
                try:
                    matches = glob.glob(os.path.join(windows_apps, '5319275A.WhatsAppDesktop_*', 'WhatsApp.exe'))
                    if matches:
                        return True
                except Exception:
                    pass
            
            for path in possible_paths:
                if os.path.exists(path):
                    return True
                    
        elif system == 'Darwin':  # macOS
            if os.path.exists('/Applications/WhatsApp.app'):
                return True
        return False

    @staticmethod
    def enviar_mensaje(parent, db, telefono: str, cliente_data: Dict[str, Any]):
        """
        Orquesta todo el proceso de envío de WhatsApp:
        1. Carga plantillas
        2. Muestra diálogo de selección
        3. Normaliza teléfono
        4. Abre WhatsApp (App o Web)
        """
        try:
            if not telefono or not telefono.strip():
                ToastWidget.show(parent, 'EL CLIENTE NO TIENE TELÉFONO', tipo='warning')
                return

            # 1. Cargar plantillas desde la base de datos
            config_repo = ConfiguracionRepository(db)
            plantillas_json = config_repo.obtener_multiples(['whatsapp_plantillas']).get('whatsapp_plantillas')
            import json
            try:
                plantillas = json.loads(plantillas_json) if plantillas_json else []
            except Exception:
                plantillas = []

            # 2. Mostrar diálogo de selección de plantillas
            from kool_tpv.utils.dialogs.whatsapp_select_dialog import show_whatsapp_select_dialog
            mensaje = show_whatsapp_select_dialog(parent.winfo_toplevel(), plantillas, cliente_data)

            if mensaje is None:  # Canceló
                return

            # 3. Preparar envío
            solo_numeros = WhatsAppService.normalizar_telefono(telefono)
            mensaje_enc = urllib.parse.quote(mensaje)
            
            url_web = f"https://wa.me/{solo_numeros}?text={mensaje_enc}"
            url_app = f"whatsapp://send?phone={solo_numeros}&text={mensaje_enc}"

            # 4. Abrir WhatsApp
            if WhatsAppService.detectar_desktop():
                webbrowser.open(url_app)
            else:
                webbrowser.open(url_web)

        except Exception:
            logger.exception('Error en WhatsAppService.enviar_mensaje')
            ToastWidget.show(parent, 'ERROR AL ABRIR WHATSAPP', tipo='error')
