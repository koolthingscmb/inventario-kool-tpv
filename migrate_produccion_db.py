
import sqlite3
import os

DB_PATH = "/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/base_datos/kool_bd.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Iniciando migración de base de datos...")

        # 1. Añadir columnas a la tabla 'tipos' si no existen
        columnas_nuevas = [
            ("coste_base", "REAL DEFAULT 0"),
            ("requiere_talla", "INTEGER DEFAULT 0"),
            ("requiere_color", "INTEGER DEFAULT 0"),
            ("requiere_genero", "INTEGER DEFAULT 0"),
            ("activo", "INTEGER DEFAULT 1"),
            ("orden", "INTEGER DEFAULT 0"),
            ("color", "TEXT"),
            ("icono", "TEXT")
        ]

        # Obtener columnas actuales de 'tipos'
        cursor.execute("PRAGMA table_info(tipos)")
        cols_existentes = [row[1] for row in cursor.fetchall()]

        for col_name, col_type in columnas_nuevas:
            if col_name not in cols_existentes:
                print(f"Añadiendo columna {col_name} a tabla tipos...")
                cursor.execute(f"ALTER TABLE tipos ADD COLUMN {col_name} {col_type}")

        # 2. Mapear IDs de produccion_tipos a tipos
        cursor.execute("SELECT id, nombre, descripcion, color, icono, coste_base, requiere_talla, requiere_color, activo, orden, requiere_genero FROM produccion_tipos")
        prod_tipos = cursor.fetchall()
        
        id_mapping = {} # old_id -> new_id

        for pt in prod_tipos:
            old_id, nombre, desc, color, icono, coste, req_talla, req_color, activo, orden, req_genero = pt
            
            # Buscar si ya existe en 'tipos' (insensible a mayúsculas)
            cursor.execute("SELECT id FROM tipos WHERE LOWER(nombre) = LOWER(?)", (nombre,))
            row = cursor.fetchone()
            
            if row:
                new_id = row[0]
                print(f"Actualizando tipo existente: {nombre} (ID: {new_id})")
                cursor.execute("""
                    UPDATE tipos SET 
                        coste_base = ?, requiere_talla = ?, requiere_color = ?, 
                        requiere_genero = ?, activo = ?, orden = ?, color = ?, icono = ?
                    WHERE id = ?
                """, (coste, req_talla, req_color, req_genero, activo, orden, color, icono, new_id))
            else:
                print(f"Insertando nuevo tipo desde producción: {nombre}")
                cursor.execute("""
                    INSERT INTO tipos (nombre, descripcion, color, icono, coste_base, requiere_talla, requiere_color, requiere_genero, activo, orden)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nombre.title(), desc, color, icono, coste, req_talla, req_color, req_genero, activo, orden))
                new_id = cursor.lastrowid
            
            id_mapping[old_id] = new_id

        # 3. Actualizar tablas dependientes
        # produccion_tipos_colores
        print("Actualizando produccion_tipos_colores...")
        cursor.execute("SELECT tipo_id, color_id FROM produccion_tipos_colores")
        rel_colores = cursor.fetchall()
        cursor.execute("DELETE FROM produccion_tipos_colores")
        for old_tid, cid in rel_colores:
            if old_tid in id_mapping:
                cursor.execute("INSERT OR IGNORE INTO produccion_tipos_colores (tipo_id, color_id) VALUES (?, ?)", (id_mapping[old_tid], cid))

        # produccion_tipos_generos
        print("Actualizando produccion_tipos_generos...")
        cursor.execute("SELECT tipo_id, genero_id FROM produccion_tipos_generos")
        rel_generos = cursor.fetchall()
        cursor.execute("DELETE FROM produccion_tipos_generos")
        for old_tid, gid in rel_generos:
            if old_tid in id_mapping:
                cursor.execute("INSERT OR IGNORE INTO produccion_tipos_generos (tipo_id, genero_id) VALUES (?, ?)", (id_mapping[old_tid], gid))

        # 4. Crear tabla de stock acumulado para diseños
        print("Creando tabla produccion_disenos_stock...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produccion_disenos_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                diseno_codigo TEXT NOT NULL,
                tipo_id INTEGER NOT NULL,
                color_id INTEGER,
                talla TEXT,
                cantidad INTEGER DEFAULT 0,
                FOREIGN KEY (diseno_codigo) REFERENCES produccion_disenos(codigo),
                FOREIGN KEY (tipo_id) REFERENCES tipos(id),
                FOREIGN KEY (color_id) REFERENCES produccion_colores(id),
                UNIQUE(diseno_codigo, tipo_id, color_id, talla)
            )
        """)

        # 5. Eliminar tabla antigua
        print("Eliminando tabla produccion_tipos...")
        cursor.execute("DROP TABLE produccion_tipos")

        conn.commit()
        print("Migración completada con éxito.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR en la migración: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
