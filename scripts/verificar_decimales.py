#!/usr/bin/env python3
"""Script de QA: verifica que ClienteService.sumar_puntos guarda decimales.

Crea un cliente temporal, suma 2.39 puntos, lee el registro y comprueba
si la BD almacena decimales. Finalmente elimina el cliente de prueba.
"""
import os
import sys
import traceback

try:
    # asegurar que el cwd sea la raíz del proyecto (script está en scripts/)
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here)
    os.chdir(project_root)
except Exception:
    pass

from modulos.clientes.cliente_service import ClienteService


def main():
    svc = ClienteService()
    cliente_id = None
    try:
        # Crear cliente temporal
        cliente_id = svc.crear_cliente({"nombre": "Test Decimales"})
        if not cliente_id:
            print("❌ ERROR: No se pudo crear el cliente de prueba.")
            return 1

        # Sumar exactamente 2.39 puntos
        svc.sumar_puntos(cliente_id, 2.39)

        # Recuperar datos del cliente
        data = svc.obtener_por_id(cliente_id)
        puntos_raw = data.get('puntos_fidelidad') if data else None
        try:
            puntos = float(puntos_raw) if puntos_raw is not None else None
        except Exception:
            puntos = None

        # Comparar resultados
        if puntos is None:
            print('❌ ERROR: No se pudo leer el valor de puntos del cliente.')
        elif abs(puntos - 2.39) < 1e-9:
            print('✅ ÉXITO: El sistema guarda decimales correctamente.')
        elif puntos == 2.0 or puntos == 2:
            print('❌ ERROR: El sistema sigue redondeando a enteros.')
        else:
            print(f'⚠️ Resultado inesperado: puntos = {puntos!r}')

    except Exception:
        print('❌ ERROR durante la verificación:')
        traceback.print_exc()
        return 1
    finally:
        # Eliminar cliente temporal para dejar la BD limpia
        try:
            if cliente_id:
                svc.eliminar_cliente(cliente_id)
        except Exception:
            pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
