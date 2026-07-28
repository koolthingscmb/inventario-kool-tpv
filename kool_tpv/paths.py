"""
Rutas centralizadas del proyecto.
Todas las rutas se calculan desde un único punto para evitar errores
al mover archivos o empaquetar la aplicación.
"""
from pathlib import Path

# Raíz del proyecto = carpeta padre de kool_tpv/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Rutas clave del proyecto
CONFIG_DIR = PROJECT_ROOT / "kool_tpv" / "config"
DB_PATH = PROJECT_ROOT / "kool_tpv" / "base_datos" / "kool_bd.db"
ASSETS_DIR = PROJECT_ROOT / "kool_tpv" / "assets"
LOGS_DIR = PROJECT_ROOT / "logs"

# Rutas alternativas de assets (legacy/compatibilidad)
PROJECT_ROOT_ASSETS = PROJECT_ROOT / "kool_tpv-assets"  # carpeta opcional en raíz
