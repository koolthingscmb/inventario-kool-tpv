
import sys
import os
from pathlib import Path

# 1. Simular entorno PyInstaller (frozen)
sys.frozen = True
# En un EXE real, sys._MEIPASS es una carpeta temporal. 
# Aquí simulamos que es la carpeta donde están los recursos en el repo.
sys._MEIPASS = str(Path(__file__).resolve().parent)

print("=== SIMULACIÓN DE EJECUTABLE (MODO FROZEN) ===")
print(f"sys._MEIPASS simulado en: {sys._MEIPASS}")

try:
    # Importar paths DESPUÉS de setear sys.frozen
    from kool_tpv.paths import CONFIG_DIR, ASSETS_DIR, DB_PATH, get_app_root
    
    print(f"Raíz persistente (fuera del EXE): {get_app_root()}")
    print(f"Config (dentro del EXE): {CONFIG_DIR} -> {'✅ OK' if CONFIG_DIR.exists() else '❌ NO EXISTE'}")
    print(f"Assets (dentro del EXE): {ASSETS_DIR} -> {'✅ OK' if ASSETS_DIR.exists() else '❌ NO EXISTE'}")
    print(f"DB Path (debe estar fuera): {DB_PATH}")

    # Verificar que el recurso crítico de botones existe en la ruta del EXE
    btn_cfg = CONFIG_DIR / "buttons_menu.json"
    print(f"Archivo crítico buttons_menu.json: {btn_cfg} -> {'✅ OK' if btn_cfg.exists() else '❌ NO EXISTE'}")

    if CONFIG_DIR.exists() and ASSETS_DIR.exists() and btn_cfg.exists():
        print("\n🏆 RESULTADO: LA ESTRUCTURA ES 100% COMPATIBLE CON PYINSTALLER.")
    else:
        print("\n⚠️ ERROR: Hay rutas que fallarían en el empaquetado.")

except Exception as e:
    print(f"\n❌ ERROR CRÍTICO EN LA PRUEBA: {e}")
    import traceback
    traceback.print_exc()
