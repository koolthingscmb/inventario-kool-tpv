Migración: `niveles_fidelidad` y cambios en `clientes`

Fecha: 2026-02-01
Autor: Automatizado por Copilot (tareas de migración)

Resumen
-------
Se ha añadido soporte para niveles de fidelización y se han renombrado columnas
relacionadas con la fidelización para mejorar la claridad del dominio.

Cambios aplicados
-----------------
1. Nueva tabla `niveles_fidelidad` creada con columnas:
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `level` INTEGER NOT NULL UNIQUE
   - `nombre_nivel` TEXT NOT NULL
   - `grafismo_nivel` TEXT NULL
   - `gasto_minimo` REAL NOT NULL DEFAULT 0.0

   Se insertaron filas iniciales:
   (1, 'Errante sombrío', '///', 0.0)
   (2, 'Guardián del Tesoro', '/////', 100.0)
   (3, 'Maestro del Tesoro', '//////', 300.0)
   (4, 'Señor del Oro', '///////', 600.0)

2. Tabla `clientes` reconstruida (clientes_new -> clientes) para incluir:
   - `tesoro_total` (antes `puntos_fidelidad`)
   - `tesoro_gastado_total` (antes `total_gastado`)
   - `fidelidad_activa` (antes `puntos_activados`)
   - `id_nivel` (FK -> `niveles_fidelidad.id`)

   Nota: para minimizar riesgos se creó `clientes_old` con el esquema previo y los
   datos fueron copiados (preservando valores de columnas antiguas cuando existían).

3. Compatibilidad en el código:
   - `modulos/clientes/cliente_service.py` adaptado para usar las nuevas columnas al
     leer y escribir. Se añadieron alias en `_row_to_dict` para devolver también
     las claves legacy (`puntos_fidelidad`, `total_gastado`, `puntos_activados`) en
     los dicts retornados por los servicios para mantener compatibilidad con
     componentes que aún no se han migrado.

4. Tests actualizados:
   - `tests/test_fidelizacion_service.py` y `tests/test_migracion_clientes.py`
     modificados para utilizar las nuevas columnas (`tesoro_total`, `fidelidad_activa`).

Archivos añadidos/modificados
----------------------------
- scripts/migracion_niveles_fidelidad.py  (nuevo)
- modulos/clientes/cliente_service.py      (modificado)
- tests/test_fidelizacion_service.py      (modificado)
- tests/test_migracion_clientes.py        (modificado)
- MIGRATION_NOTES/niveles_fidelidad_migration.md (este archivo)

Pasos recomendados tras la migración
------------------------------------
- Revisar manualmente `clientes_old` (si existe) y verificar que los datos fueron
  copiados correctamente antes de eliminarlo.
- Ejecutar pruebas funcionales del TPV (ventas, cierre de caja, gestión de clientes)
  y validar que la fidelización sigue comportándose como antes.
- Gradualmente eliminar alias legacy del código (tras confirmación en QA), y
  actualizar cualquier script externo que use las columnas antiguas.

Cómo revertir
-------------
- Si necesitas deshacer: restaurar la copia de seguridad del fichero `inventario.db`
  (se recomienda tener un backup previo a la migración).

Notas
-----
La migración intenta ser idempotente y segura para un entorno de desarrollo. En
entornos productivos, realiza una copia de seguridad completa antes de ejecutar
el script `scripts/migracion_niveles_fidelidad.py` y valida en staging.
