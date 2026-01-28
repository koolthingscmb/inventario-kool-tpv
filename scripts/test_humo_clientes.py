#!/usr/bin/env python3
"""Smoke test for ClienteService against the real SQLite DB.

Usage:
    python3 scripts/test_humo_clientes.py

The script will:
 - Add project root to sys.path so imports work when run from repo root
 - Create a test client
 - Verify creation, search, update and delete
 - Clean up the created record
"""
import sys
from pathlib import Path
import traceback

# Ensure project root is on sys.path (so `modulos` can be imported)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modulos.clientes.cliente_service import ClienteService


def main():
    service = ClienteService()
    created_id = None
    try:
        # 1) Crear cliente de prueba
        datos = {
            'nombre': 'Cliente de Prueba',
            'telefono': '123456789',
            'email': 'test@mail.com',
            'dni': '99999999X',
            'direccion': 'Calle Test 1',
            'ciudad': 'Pruebaland',
            'cp': '00000',
            'tags': 'test,auto',
            'notas_internas': 'Generado por test humo'
        }
        created_id = service.crear_cliente(datos)
        if created_id is None:
            print('❌ Falló la creación del cliente (id None)')
            return
        print(f'✅ Cliente creado con ID: {created_id}')

        # 2) Buscar cliente por nombre
        encontrados = service.buscar_clientes('Cliente de Prueba')
        if not encontrados:
            print('❌ No se encontró el cliente mediante buscar_clientes')
            return
        # buscar en resultados el id
        if not any((c.get('id') == created_id or c.get('nombre') == 'Cliente de Prueba') for c in encontrados):
            print('❌ El cliente creado no aparece en los resultados de búsqueda')
            return
        print('✅ Búsqueda: cliente encontrado en resultados')

        # 3) Obtener por id
        cliente = service.obtener_por_id(created_id)
        if not cliente:
            print('❌ obtener_por_id devolvió None')
            return
        print('✅ obtener_por_id retornó datos')

        # 4) Actualizar cliente
        actualizado = service.actualizar_cliente(created_id, {'nombre': 'Cliente de Prueba Editado'})
        if not actualizado:
            print('❌ actualización fallida')
            return
        cliente_editado = service.obtener_por_id(created_id)
        if cliente_editado.get('nombre') != 'Cliente de Prueba Editado':
            print('❌ El nombre no fue actualizado correctamente')
            return
        print('✅ Actualización: nombre actualizado correctamente')

        # 5) Sumar puntos y registrar gasto (comprobación rápida)
        ok_pts = service.sumar_puntos(created_id, 10)
        ok_gasto = service.registrar_gasto(created_id, 12.5)
        if not ok_pts or not ok_gasto:
            print('⚠️ Advertencia: sumar_puntos o registrar_gasto devolvió False')
        else:
            print('✅ Puntos y gasto registrados correctamente')

        print('\n🎉 Resumen: CRUD básico de clientes pasado con éxito.')

    except Exception:
        print('❌ Excepción no esperada durante las pruebas:')
        traceback.print_exc()
    finally:
        # Limpieza: eliminar el cliente creado
        try:
            if created_id:
                deleted = service.eliminar_cliente(created_id)
                if deleted:
                    print(f'🧹 Cliente de prueba (id={created_id}) eliminado correctamente')
                else:
                    print(f'⚠️ No se pudo eliminar cliente de prueba (id={created_id})')
        except Exception:
            print('⚠️ Excepción durante la limpieza:')
            traceback.print_exc()


if __name__ == '__main__':
    main()
