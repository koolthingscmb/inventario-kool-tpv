
import sys
from pathlib import Path

# Agregar el directorio actual al path para poder importar kool_tpv
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from kool_tpv.paths import CONFIG_DIR, ASSETS_DIR, DB_PATH, LOGS_DIR, get_app_root
    
    print("\n=== VERIFICACIÓN DE RUTAS (MODO DESARROLLO) ===")
    print(f"Raíz detectada: {get_app_root()}")
    print(f"Config: {CONFIG_DIR} -> {'✅ OK' if CONFIG_DIR.exists() else '❌ NO EXISTE'}")
    print(f"Assets: {ASSETS_DIR} -> {'✅ OK' if ASSETS_DIR.exists() else '❌ NO EXISTE'}")
    print(f"DB Path: {DB_PATH}")
    print(f"Logs: {LOGS_DIR}")
    
    # Verificar subcarpetas críticas
    iconos = ASSETS_DIR / "iconos"
    print(f"Carpeta Iconos: {iconos} -> {'✅ OK' if iconos.exists() else '❌ NO EXISTE'}")
    
    migraciones = get_app_root() / "kool_tpv" / "base_datos" / "migraciones"
    print(f"Migraciones: {migraciones} -> {'✅ OK' if migraciones.exists() else '❌ NO EXISTE'}")

    print("\nSi todo sale con ✅, la estructura es correcta para desarrollo.")
    print("El siguiente paso es la simulación de empaquetado.")

except Exception as e:
    print(f"\n❌ ERROR AL IMPORTAR RUTAS: {e}")
