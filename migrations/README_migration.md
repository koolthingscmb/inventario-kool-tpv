Migration plan and instructions
================================

Pasos propuestos (resumen):

1) Hacer backup completo de la BD (copiar el fichero `kool_tpv/base_datos/kool_bd.db`).

2) En staging aplicar la migración para añadir `importe_web`:
   - `migrations/001_add_importe_web.sql`

   Nota: La tabla `payments` ya existe en tu esquema, por tanto NO ejecutar ninguna
   migración que intente crearla. Si tu entorno no tuviera `payments`, contacta
   antes de aplicar cambios.

3) Cambiar la lógica de persistencia (aplicar en la rama de feature):
   - Al crear un ticket, insertar/actualizar una fila en `payments` por cada forma de pago usada.
   - Para compatibilidad inmediata, rellenar `tickets.importe_web` cuando `forma_pago='web'`.

4) No actualizar tickets existentes (tal y como solicitaste). Si quieres vaciarlos, usar:
   - `tools/delete_all_tickets.sql` (ejecutable si confirmas borrar todo).

5) Si quieres arreglar datos existentes sin borrarlos, revisa `tools/move_tarjeta_to_web.sql`:
   - Este script INSERTA filas en `payments` desde `tickets.importe_tarjeta` cuando `forma_pago='web'`.
   - NO ejecuta UPDATE sobre `tickets` a menos que descomentes la sección indicada.

6) Ajustar cierres/reports para sumar desde `payments` y añadir tests.

Precauciones:
- Asegúrate de backups antes de correr cualquier script.
- Probar primero en staging con datos de ejemplo.
- Mantén compatibilidad de lectura mientras verificas resultados.
