"""
Rutas centralizadas del proyecto.
Todas las rutas se calculan desde un único punto para evitar errores
al mover archivos o empaquetar la aplicación.
"""
import sys
from pathlib import Path

def get_app_root() -> Path:
    """Retorna la raíz persistente de la aplicación.
    - Desarrollo: raíz del repo (padre de kool_tpv/).
    - Empaquetado: carpeta donde reside el .exe.
    Se usa para DB y Logs.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

def get_resource_path(*parts) -> Path:
    """Retorna la ruta a un recurso estático (assets, config, migraciones).
    - Desarrollo: ruta relativa desde la raíz del repo.
    - Empaquetado: ruta dentro de sys._MEIPASS (directorio temporal de PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller desempaqueta recursos en sys._MEIPASS
        base = Path(sys._MEIPASS)
        return base.joinpath(*parts)
    
    # En desarrollo, la raíz es el repo
    return get_app_root().joinpath(*parts)

# Raíz persistente (para archivos que el usuario debe poder ver/tocar)
PROJECT_ROOT = get_app_root()

# Rutas clave (Recursos estáticos empaquetados)
# Usamos get_resource_path para que apunten a _MEIPASS en el EXE
CONFIG_DIR = get_resource_path("kool_tpv", "config")
CLOUD_CONFIG_DIR = CONFIG_DIR / "cloud"
ASSETS_DIR = get_resource_path("kool_tpv", "assets")

# Rutas persistentes (Fuera del paquete en el EXE, en la carpeta del usuario/instalación)
DB_PATH = PROJECT_ROOT / "kool_tpv" / "base_datos" / "kool_bd.db"
LOGS_DIR = PROJECT_ROOT / "logs"
BORRADORES_DIR = PROJECT_ROOT / "kool_tpv" / "borradores"
BACKUP_DIR = PROJECT_ROOT / "kool_tpv" / "config" / "backups"

# Rutas de recursos específicos (Atajos)
MIGRACIONES_DIR = get_resource_path("kool_tpv", "base_datos", "migraciones")
ICONOS_DIR = ASSETS_DIR / "iconos"
BADGES_DIR = ASSETS_DIR / "badges"

# Rutas alternativas de assets (legacy/compatibilidad)
PROJECT_ROOT_ASSETS = PROJECT_ROOT / "kool_tpv-assets"
