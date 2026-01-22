KOOL_TPV — Conexión a la base de datos

Propósito
- Centralizar el acceso a la base de datos para evitar usos de rutas relativas y copias accidentales del fichero SQLite.

Archivo principal
- `database.py` expone:
  - `DB_PATH`: ruta absoluta por defecto a `inventario.db`.
  - `connect(db_path: Optional[str] = None) -> sqlite3.Connection`: devuelve una conexión a la BD; si `db_path` no se da, usa `DB_PATH`.

Convenciones (recomendadas)
- Importar y usar siempre la función centralizada:

```python
from database import connect, DB_PATH

# obtener conexión (usa DB_PATH por defecto)
conn = connect()
cur = conn.cursor()
# ejecutar consultas
cur.execute("SELECT ...")
# commit si hay cambios
conn.commit()
# cerrar
conn.close()
```

- Variable para la conexión: usar `conn` (corta y clara).
- Usar `cur`/`cursor` para el cursor.
- Evitar `sqlite3.connect('inventario.db')` en módulos: puede crear confusión por cwd.
- Para scripts o tests que necesiten apuntar a otra BD, pasar la ruta a `connect()`:

```python
conn = connect('/ruta/a/otro/inventario.db')
```

Buenas prácticas
- Preferir el uso de `try/finally` o `with` cuando sea conveniente:

```python
try:
    conn = connect()
    cur = conn.cursor()
    cur.execute(...)
    conn.commit()
finally:
    try:
        conn.close()
    except Exception:
        pass
```

- Documentar en el código cuándo se abre una conexión que queda viva (por ejemplo en singletons o pools).

Notas
- Si quieres, puedo:
  - Renombrar más variables de conexión a `conn` en todo el repo para consistencia.
  - Añadir un ejemplo de migración (WAL, PRAGMA) en `README.md`.

Archivo creado: README.md
