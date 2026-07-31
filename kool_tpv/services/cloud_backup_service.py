import os
import logging
import pickle
from typing import Optional
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

class CloudBackupService:
    """Servicio para gestionar copias de seguridad en Google Drive."""
    
    # Alcance necesario para ver y gestionar archivos creados por esta app y ver el email
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]
    
    def __init__(self, db=None):
        self.db = db
        # Rutas de configuración
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(base_path, 'config', 'cloud')
        self.client_secrets_path = os.path.join(self.config_dir, 'client_secrets.json')
        self.token_path = os.path.join(self.config_dir, 'token.json')
        self.user_info_path = os.path.join(self.config_dir, 'user_info.json') # Para guardar email
        
        # Asegurar que la carpeta existe
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        self.service = None

    def obtener_email_vinculado(self) -> Optional[str]:
        """Devuelve el email de la cuenta vinculada consultando a Google Drive."""
        if not self.service and not self.autenticar():
            return None
            
        try:
            # Usar la API de Drive para obtener info sobre el usuario actual
            about = self.service.about().get(fields="user(emailAddress)").execute()
            email = about.get('user', {}).get('emailAddress')
            if email:
                # Opcionalmente guardar en cache local para rapidez
                import json
                with open(self.user_info_path, 'w') as f:
                    json.dump({'email': email}, f)
                return email
        except Exception:
            # Si falla la red, intentar leer del cache local
            if os.path.exists(self.user_info_path):
                try:
                    import json
                    with open(self.user_info_path, 'r') as f:
                        return json.load(f).get('email')
                except Exception: pass
        return None

    def autenticar(self) -> bool:
        """Realiza el flujo de autenticación OAuth2."""
        creds = None
        
        # 1. Intentar cargar token guardado
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception:
                logger.exception("Error cargando token.json")

        # 2. Si no hay credenciales válidas, pedir login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    logger.exception("Error refrescando token")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.client_secrets_path):
                    logger.error(f"Falta archivo de credenciales: {self.client_secrets_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    # Guardar info del usuario (email)
                    try:
                        import json
                        session = flow.authorized_session()
                        user_info = session.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
                        with open(self.user_info_path, 'w') as f:
                            json.dump(user_info, f)
                    except Exception:
                        logger.warning("No se pudo obtener la info del usuario tras la autenticación")

                except Exception:
                    logger.exception("Error en el flujo de autenticación local")
                    return False

            # 3. Guardar credenciales para la próxima vez
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception:
                logger.exception("Error guardando token.json")

        try:
            self.service = build('drive', 'v3', credentials=creds)
            
            # Si no tenemos el email guardado, intentar obtenerlo ahora que tenemos credenciales válidas
            if not os.path.exists(self.user_info_path):
                self._descargar_user_info(creds)
                
            return True
        except Exception:
            logger.exception("Error construyendo servicio de Google Drive")
            return False

    def _descargar_user_info(self, creds):
        """Descarga la info del usuario (email) usando las credenciales actuales."""
        try:
            import json
            import requests
            response = requests.get(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                headers={'Authorization': f'Bearer {creds.token}'}
            )
            if response.status_code == 200:
                user_info = response.json()
                with open(self.user_info_path, 'w') as f:
                    json.dump(user_info, f)
                logger.info(f"Info de usuario descargada: {user_info.get('email')}")
        except Exception:
            logger.warning("No se pudo descargar la info del usuario")

    def subir_archivo(self, file_path: str, folder_name: str = "KOOL_TPV_Backups") -> bool:
        """Sube un archivo a una carpeta específica en Google Drive con sufijo de fecha."""
        if not self.service and not self.autenticar():
            return False

        try:
            # 1. Buscar o crear la carpeta
            folder_id = self._obtener_o_crear_carpeta(folder_name)
            if not folder_id:
                return False

            # 2. Generar nombre con sufijo DDMMAA_HH
            from datetime import datetime
            ahora = datetime.now()
            sufijo = ahora.strftime("%d%m%y_%H") # Formato: DDMMAA_HH
            
            base_name = os.path.basename(file_path) # kool_bd.db
            name_part, ext = os.path.splitext(base_name) # kool_bd, .db
            new_file_name = f"{name_part}_{sufijo}{ext}" # kool_bd_310726_12.db

            # 3. Preparar metadatos del archivo
            file_metadata = {
                'name': new_file_name,
                'parents': [folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True)

            # 4. Subir
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"Archivo subido como {new_file_name}. ID: {file.get('id')}")
            return True

        except Exception:
            logger.exception(f"Error subiendo archivo {file_path} a Google Drive")
            return False

    def _obtener_o_crear_carpeta(self, folder_name: str) -> Optional[str]:
        """Busca una carpeta por nombre o la crea si no existe."""
        try:
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if items:
                return items[0]['id']
            
            # Crear si no existe
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')

        except Exception:
            logger.exception(f"Error gestionando carpeta {folder_name} en Drive")
            return None
