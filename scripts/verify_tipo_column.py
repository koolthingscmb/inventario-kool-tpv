import sqlite3
from pathlib import Path

db_path = Path('kool_tpv/base_datos/kool_bd.db')

print("═" * 70)
print("VERIFICACIÓN COLUMNA tipo EN albaranes")
print("═" * 70)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
# 1. Verificar estructura
print("\n1. ESTRUCTURA TABLA albaranes:")
cursor.execute("PRAGMA table_info(albaranes)")
cols = cursor.fetchall()
for col in cols:
    print(f" {col[1]:20} | {col[2]:10} | NotNull:{col[3]} | Default:{col[4]}")

# 2. Contar registros totales
cursor.execute("SELECT COUNT(*) FROM albaranes")
total = cursor.fetchone()[0]
print(f"\n2. TOTAL ALBARANES: {total}")

# 3. Contar por tipo
cursor.execute("SELECT tipo, COUNT(*) FROM albaranes GROUP BY tipo")
tipos = cursor.fetchall()
print(f"\n3. DISTRIBUCIÓN POR TIPO:")
for tipo, count in tipos:
    print(f" {tipo:15} : {count}")

# 4. Mostrar primeros 3 registros
cursor.execute("SELECT id, num_albaran, proveedor_id, fecha, tipo FROM albaranes LIMIT 3")
registros = cursor.fetchall()
print(f"\n4. PRIMEROS 3 ALBARANES (con tipo):")
for r in registros:
    print(f" ID:{r[0]} | Num:{r[1]} | Prov:{r[2]} | Fecha:{r[3]} | Tipo:{r[4]}")

conn.close()

print("\n" + "═" * 70)
print("✅ VERIFICACIÓN COMPLETADA")
print("═" * 70)
