# MIGRATION_CENTS_STEPS

Índice de pasos para arreglar la representación monetaria (céntimos) en kool_tpv.

1. Documentar convención
   - [x] Definir: BD almacena céntimos (INTEGER).
   - [x] Listar tablas y columnas afectadas (ver listado abajo).
   - Añadir nota en `INSTRUCCIONES_IA.md`.

2. Hacer backup de la BD
   - [x] Crear copia con timestamp.
     - Archivo creado: `backups/kool_bd_20260505_093129.db`.
   - [x] Verificar integridad de la copia (checksum/abrir con DB Browser).
      - Verificado: abierto en DB Browser por el usuario el 2026-05-05; checksum opcional.

3. Preparar entorno y branch
    - [x] Crear rama git para los cambios.
       - Rama creada: `migration/cents-conversion`.
    - [x] Preparar BD de staging (usar copia).
       - Archivo creado: `staging/kool_bd_staging.db` (copia de `backups/kool_bd_20260505_093129.db`).

4. Añadir helpers/adapter de money
   - [x] Centralizar `from_cents` y `to_cents` en un adapter/DAO.
     - Archivo creado: `kool_tpv/base_datos/money_adapter.py` (wrapper que reutiliza `kool_tpv/utils/money.py`).
   - [x] Documentar uso del adapter (docstring en el módulo con ejemplos básicos).

5. Corregir escrituras a la BD (prioridad alta)
    - Prioridad 1 (crítico — correcciones que evitan pérdidas/errores visibles):
       - `kool_tpv/base_datos/ticket_service.py` — convertir antes de INSERT/UPDATE: `subtotal`, `total`, `pagado`, `cambio`, `importe_efectivo`, `importe_tarjeta`, `descuento_euros`; usar `money_adapter.prepare_for_db(...)`. Convertir `ticket_lines.precio` al insertar líneas y usar `prepare_for_db` para `payments.importe`.
    - Prioridad 2 (alta — operaciones contables y stock):
       - `kool_tpv/base_datos/albaran_service.py` — convertir `coste`, `descuento`, `importe` en `albaran_lines` y totales (`total_neto`, `total_iva_*`, `total`) antes de insert.
       - `kool_tpv/base_datos/cierre_service.py` — en `insert_cierre` y `create_cierre_atomic` convertir todos los campos monetarios (`total_ingresos`, `total_efectivo`, `total_tarjeta`, `total_web`, `total_devoluciones`, `total_descuentos`, `base_21`, `iva_21`, `base_4`, `iva_4`, `total_base_imponible`, `total_iva`) a céntimos.
    - Prioridad 3 (alta — UI que escribe precios):
       - `kool_tpv/modulos/almacen/ui/crear_producto_ui.py` — al insertar/upsert en `precios` usar `prepare_for_db` para `pvp` y `coste`.
       - `kool_tpv/modulos/almacen/ui/Productos/crear_producto_ui.py` — mismo cambio para la variante del UI.
    - Prioridad 4 (media):
       - `kool_tpv/base_datos/producto_service.py` — revisar lecturas/escrituras relacionadas con `precios` y normalizar (lectura: `read_from_db`, escrituras: `prepare_for_db`).
       - Servicios/scripts que generan `facturas` / `facturas_lines` (buscar en `modulos/` y `scripts/`) — convertir `base_imponible`, `total_iva`, `total_recargo`, `total`, `precio_unitario`, `descuento`, `total_linea`.
    - Prioridad 5 (baja pero necesario):
       - `scripts/test_db_robustness.py` y otros scripts de creación de datos: actualizar inserciones para usar céntimos o adaptador.
       - `tests/test_ticket_print.py` y fixtures/tests que hacen INSERT directo: actualizar valores esperados a céntimos o usar adaptadores en los tests.
    - Nota: marcar cada cambio con un TODO/issue reference y crear PRs por área (writes primero). 

6. Corregir lecturas desde la BD (prioridad alta)
   - Reemplazar `float(...)`/`Decimal(str(...))` por `from_cents` donde corresponda.
   - Ajustar agregaciones (SUM) que devuelven céntimos: convertir al final.
   - Asegurar que servicios devuelvan `Decimal` en euros a la UI.

7. Ajustar UI y formateadores
   - `ticket_carrito.py`: pasar `subtotal`/`total` en euros a `format_precio`.
   - Usar `format_precio_cents` solo si el valor es céntimos.
   - Revisar visores, cierres y exportes.

**Recomendación profesional (ordenada, lista para ejecutar):**

- Auditoría no invasiva (recomendada ahora): buscar y listar todos los call‑sites que leen valores monetarios desde BD y/o llaman a `format_precio`/`format_precio_cents`. Resultado: `archivo:línea:qué espera (céntimos/euros)`. Esto no modifica nada.
- Aplicar un guard (baja invasividad) en la capa de renderizado para evitar más tickets inflados: detectar `float`/`Decimal` sin parte fracc. y tratarlos como céntimos vía `read_from_db` antes de formatear. Esto arregla la mayoría de síntomas rápidamente y es reversible.
- Después del guard, hacer correcciones por sitio (reemplazar usos incorrectos por `format_precio_cents` o `read_from_db`) y ejecutar tests.
- Migración: normalizar legacy rows en staging con el script de migración, verificar, luego desplegar según `MIGRATION_CENTS_STEPS.md`.

Acciones recomendadas (inmediatas):

- 1) Aplicar un guard central y reversible en la capa de renderizado:
   - Modificar `kool_tpv/modulos/impresion/base_ticket_generator.py`:`_format_currency` para:
      - Detectar `float` sin parte fraccional (p.e. `val.is_integer()`), y `Decimal` cuyo valor es integral (`v == v.to_integral_value()`), y tratarlos como céntimos convirtiendo con `read_from_db(int(val))` antes de formatear.
      - Mantener comportamiento actual para `Decimal` con parte fraccional y `str`/`int` ya manejados.
   - Propósito: mitigar rápidamente tickets impresos con 1184 → 1184.00 € sin cambios masivos en la base de código.

- 2) Corregir fuente en impresión (media prioridad):
   - Revisar `kool_tpv/modulos/impresion/impresora_service.py` y evitar `float(precio)` al mapear filas de BD. En su lugar, usar `read_from_db(precio)` o mantener `Decimal` para pasar al generador.
   - Propósito: prevenir que valores de BD (céntimos) sean convertidos a `float` y malinterpretados como euros.

- 3) Auditar puntos de reportes y vistas (media prioridad):
   - Revisar `kool_tpv/modulos/informes/informes_view.py` y cualquier consumidor de `report_data.sections[].money_columns` para garantizar que se pase `format_precio_cents` cuando los datos sean céntimos, o que se conviertan explícitamente con `read_from_db`.

- 4) Añadir pruebas y validación (alta prioridad):
   - Añadir tests unitarios para el guard (`_format_currency`) que comprueben: `1184 (int) → 11.84`, `1184.0 (float) → 11.84`, `Decimal('11.84') → 11.84`.
   - Añadir un test de integración que genere un ticket desde staging DB y verifique la representación impresa.

- 5) Plan de despliegue seguro:
   - Aplicar el guard en branch `migration/cents-conversion`, ejecutar tests, desplegar en staging y validar visualmente (generar tickets). Después, corregir call-sites por área (writes primero), normalizar BD en staging y planificar migración en producción.


8. Tests automatizados
   - Tests para `to_cents` / `from_cents`.
   - Tests unitarios para `ticket_service` (guardar + leer).
   - Tests de integración E2E en BD temporal.
   - Añadir test de regresión (mostrar 5000 vs 50.00).

9. Migración en staging
   - Ejecutar `scripts/migrate_real_to_cents.py` en copia.
   - Verificar checks del script y ejecutar tests en staging.

10. Revisión de PR & CI
    - Crear PRs organizados por categoría (writes, reads, adapter, tests).
    - CI: tests + linter deben pasar.
    - Checklist de revisión completado.

11. Despliegue en producción
    - Backup final.
    - Ejecutar migración en ventana de mantenimiento.
    - Desplegar el commit verificado.

12. Verificaciones post-despliegue
    - Crear 3 tickets de prueba y comprobar BD/UI.
    - Comprobar cierres/informes y exportes.
    - Monitorizar logs 24–48h.

13. Documentación final
    - Actualizar `INSTRUCCIONES_IA.md` y `README.md`.
    - Añadir pasos de rollback y changelog.

---

Listado exacto detectado (tabla: columnas monetarias) — extraído de `scripts/certify_db_state_report.txt`

- `albaran_lines`:
   - `coste`, `descuento`, `importe`
- `albaranes`:
   - `total_neto`, `total_iva_4`, `total_iva_10`, `total_iva_21`, `total`
- `cierres_caja`:
   - `total_ingresos`, `total_efectivo`, `total_tarjeta`, `total_web`, `total_devoluciones`, `total_descuentos`, `tesoro_ganado`, `tesoro_gastado`, `tesoro_total_ganado`, `tesoro_total_gastado`, `total_base_imponible`, `total_iva`, `base_21`, `iva_21`, `base_4`, `iva_4`
- `clientes`:
   - `tesoro_total`, `tesoro_gastado_total`, `tesoro_historico`, `total_compras`, `total_compras_euros`, `total_unidades`
- `facturas`:
   - `base_imponible`, `total_iva`, `total_recargo`, `total`
- `facturas_lines`:
   - `precio_unitario`, `descuento`, `base_imponible`, `iva`, `total_linea`
- `nivel_fidelidad` / `niveles_fidelidad`:
   - `gasto_minimo`
- `payments`:
   - `importe`
- `precios`:
   - `pvp`, `coste`  (confirmado: INTEGER en la BD; ver comprobación en DB Browser)
- `productos`:
   - `fidelizacion_valor` (otros campos como `ventas_totales` o `pvp_variable` no son importes en euros)
- `stock_movements` / `albaran_lines`:
   - `cantidad` / `coste` / `importe` según tabla (anotar que `cantidad` no es importe monetario salvo en migraciones específicas)
- `ticket_lines`:
   - `precio`, `iva` (y `cantidad` como unidades)
- `tickets`:
   - `subtotal`, `total`, `pagado`, `cambio`, `importe_efectivo`, `importe_tarjeta`, `descuento_euros`, `descuento_valor`

- Notas:
- La lista anterior proviene del DDL generado por `scripts/certify_db_state_report.txt` y `scripts/migrate_real_to_cents_output.txt`.
- `precios.pvp` y `precios.coste` fueron revisados en DB Browser por el usuario y están como `INTEGER` (correcto para céntimos).
- Algunos campos con nombres similares aparecen en tests o fixtures (ver `tests/test_ticket_print.py`) y deben considerarse en los tests de regresión.
- Próximo paso: añadir automáticamente en este archivo una tabla:columna por cada columna detectada (CSV o código) y crear un script menor para validar tipos en BD.

Estado: listado exacto detectado e incorporado en el documento. `precios.pvp` / `precios.coste` confirmados como `INTEGER`.

