#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path('kool_tpv/base_datos/kool_bd.db')

print("═" * 80)
print("VERIFICACIÓN ESTRUCTURA TABLA CLIENTES")
print("═" * 80)

if not db_path.exists():
    print(f"ERROR: base de datos no encontrada en {db_path}")
    raise SystemExit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("\n📋 ESTRUCTURA TABLA clientes:\n")
cursor.execute("PRAGMA table_info(clientes)")
cols = cursor.fetchall()

campos_nuevos = ['fecha_vencimiento_tesoro', 'fecha_ultima_compra', 'total_compras', 'fecha_ultima_comunicacion']

for col in cols:
    cid, name, tipo, notnull, default, pk = col
    marcador = "✅ NUEVO" if name in campos_nuevos else ""
    print(f" {name:30} | {tipo:10} | NotNull:{notnull} | Default:{default} {marcador}")

print("\n📊 CONTANDO CLIENTES...\n")
cursor.execute("SELECT COUNT(*) FROM clientes")
total = cursor.fetchone()[0]
print(f"📊 TOTAL CLIENTES: {total}")

if total > 0:
    cursor.execute("""
    SELECT id, nombre, fecha_vencimiento_tesoro, fecha_ultima_compra,
           total_compras, fecha_ultima_comunicacion
    FROM clientes LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        print(f"\n🔍 CLIENTE DE PRUEBA (ID {row[0]}):")
        print(f" Nombre: {row[1]}")
        print(f" Fecha venc tesoro: {row[2] or 'NULL'}")
        print(f" Última compra: {row[3] or 'NULL'}")
        print(f" Total compras: {row[4] or 0}")
        print(f" Última comunicación: {row[5] or 'NULL'}")
    else:
        print("No se pudo recuperar un cliente de prueba (tabla vacía o error).")
else:
    print("Tabla `clientes` vacía — no hay filas para probar campos.")

conn.close()

print("\n" + "═" * 80)
print("✅ VERIFICACIÓN COMPLETADA - TABLA LISTA PARA MÓDULO CLIENTES")
print("═" * 80)
