# Archivo que permite ejecutar la aplicación desde el editor cuando
# se ejecuta el archivo activo `kool_tpv/main.py`.
import sys
import runpy
import logging
from pathlib import Path

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    main_file = project_root / "main.py"
    if main_file.exists():
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        runpy.run_path(str(main_file), run_name="__main__")
    else:
        logging.warning(f"No se encontró {main_file}. Ejecuta la app desde la raíz con: python3 main.py")
