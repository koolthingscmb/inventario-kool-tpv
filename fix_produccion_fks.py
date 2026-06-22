import sqlite3

DB_PATH = "/Volumes/ALMACEN/KOOL_THINGS/KOOL_TPV_V2/kool_tpv/base_datos/kool_bd.db"

def fix_foreign_keys():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Corrigiendo claves foráneas en la base de datos...")
        
        # Desactivar claves foráneas temporalmente para poder reconstruir tablas
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        tables_to_fix = [
            {
                "name": "produccion_disenos_tipos",
                "schema": """
                    CREATE TABLE IF NOT EXISTS produccion_disenos_tipos (
                        diseno_codigo TEXT NOT NULL,
                        tipo_id INTEGER NOT NULL,
                        PRIMARY KEY (diseno_codigo, tipo_id),
                        FOREIGN KEY (diseno_codigo) REFERENCES produccion_disenos(codigo) ON DELETE CASCADE,
                        FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE CASCADE
                    )
                """
            },
            {
                "name": "produccion_tipos_colores",
                "schema": """
                    CREATE TABLE IF NOT EXISTS produccion_tipos_colores (
                        tipo_id INTEGER NOT NULL,
                        color_id INTEGER NOT NULL,
                        PRIMARY KEY (tipo_id, color_id),
                        FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE CASCADE,
                        FOREIGN KEY (color_id) REFERENCES produccion_colores(id) ON DELETE CASCADE
                    )
                """
            },
            {
                "name": "produccion_tipos_generos",
                "schema": """
                    CREATE TABLE IF NOT EXISTS produccion_tipos_generos (
                        tipo_id INTEGER NOT NULL,
                        genero_id INTEGER NOT NULL,
                        PRIMARY KEY (tipo_id, genero_id),
                        FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE CASCADE,
                        FOREIGN KEY (genero_id) REFERENCES produccion_generos(id) ON DELETE CASCADE
                    )
                """
            }
        ]
        
        for table in tables_to_fix:
            name = table["name"]
            print(f"Reconstruyendo tabla {name}...")
            
            # 1. Copiar datos actuales
            cursor.execute(f"SELECT * FROM {name}")
            data = cursor.fetchall()
            
            # 2. Obtener nombres de columnas
            cursor.execute(f"PRAGMA table_info({name})")
            cols = [row[1] for row in cursor.fetchall()]
            cols_str = ", ".join(cols)
            placeholders = ", ".join(["?"] * len(cols))
            
            # 3. Borrar tabla vieja
            cursor.execute(f"DROP TABLE {name}")
            
            # 4. Crear tabla nueva con FK correcta
            cursor.execute(table["schema"])
            
            # 5. Insertar datos
            if data:
                cursor.executemany(f"INSERT INTO {name} ({cols_str}) VALUES ({placeholders})", data)
        
        conn.commit()
        print("Tablas reconstruidas con éxito.")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_foreign_keys()
