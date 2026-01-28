#!/usr/bin/env python3
"""limpiar_proyecto.py

Utilidad para limpiar bytecode y caches en el proyecto KOOL_TPV.
Acciones:
 - Elimina recursivamente directorios `__pycache__` bajo la carpeta del script.
 - Elimina archivos con extensiones `.pyc`, `.pyo`, `.pyd` bajo la carpeta del script.
 - Continúa si encuentra errores y reporta un resumen al final.

Uso:
    python3 limpiar_proyecto.py

Advertencia: el script actúa únicamente dentro de la carpeta donde está ubicado.
"""

from pathlib import Path
import shutil
import sys
import argparse


def main(dry_run: bool = False):
    project_root = Path(__file__).parent.resolve()

    if not project_root.exists():
        print(f"Error: carpeta del script no existe: {project_root}")
        sys.exit(1)

    print(f"Limpiando proyecto en: {project_root}")
    if dry_run:
        print("Modo dry-run: no se eliminará nada, solo se listarán objetivos.")

    removed_dirs = 0
    removed_files = 0
    errors = []

    # 1) Eliminar carpetas __pycache__
    for p in project_root.rglob("__pycache__"):
        try:
            # Protección: asegurarse de que es un subdirectorio del proyecto
            p_resolved = p.resolve()
            if project_root in p_resolved.parents or p_resolved == project_root:
                if dry_run:
                    print(f"[DRY] Dir: {p_resolved}")
                else:
                    shutil.rmtree(p_resolved)
                    print(f"Eliminado directorio: {p_resolved}")
                    removed_dirs += 1
            else:
                print(f"Omitido (fuera del proyecto): {p_resolved}")
        except Exception as e:
            errors.append((str(p), str(e)))
            print(f"WARNING: no se pudo eliminar directorio {p}: {e}")

    # 2) Eliminar archivos compilados
    exts = (".pyc", ".pyo", ".pyd")
    for ext in exts:
        for f in project_root.rglob(f"*{ext}"):
            try:
                f_resolved = f.resolve()
                if project_root in f_resolved.parents or f_resolved == project_root:
                    if dry_run:
                        print(f"[DRY] File: {f_resolved}")
                    else:
                        try:
                            f.unlink()
                            print(f"Eliminado archivo: {f_resolved}")
                            removed_files += 1
                        except IsADirectoryError:
                            # raro caso: si es un directorio, intentar rmtree
                            shutil.rmtree(f_resolved)
                            print(f"Eliminado (dir) por ext improbable: {f_resolved}")
                            removed_dirs += 1
                else:
                    print(f"Omitido (fuera del proyecto): {f_resolved}")
            except Exception as e:
                errors.append((str(f), str(e)))
                print(f"WARNING: no se pudo eliminar archivo {f}: {e}")

    # Resumen
    print("\nResumen de limpieza:")
    print(f"  Directorios __pycache__ eliminados: {removed_dirs}")
    print(f"  Archivos eliminados ({', '.join(exts)}): {removed_files}")
    if errors:
        print(f"\nSe produjeron {len(errors)} errores durante la limpieza:")
        for path, err in errors:
            print(f"  - {path}: {err}")
        print("Si hay errores por permisos, ejecuta con permisos adecuados o revisa procesos que bloqueen archivos.")
    else:
        print("Limpieza completada sin errores.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Limpiar __pycache__ y archivos compilados en el proyecto')
    parser.add_argument('--dry-run', action='store_true', help='Listar objetivos sin eliminar')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
