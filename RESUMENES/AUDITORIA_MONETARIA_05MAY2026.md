AUDITORÍA MONETARIA — 05/05/2026

Resumen ejecutivo
- Problema: la base de datos contiene valores monetarios en distintas unidades (principalmente céntimos como `INTEGER`), mientras que varios consumidores del TPV esperan euros (floats/Decimals). Esto provoca tickets impresos con cifras infladas (ej.: `500000` almacenado en BD interpretado como `500000.00 €`).
- Impacto: impresión de tickets, informes agregados, widgets UI, y lógica de negocio que calcula totales pueden mostrar valores erróneos.

Evidencia reproducible
- Ticket de ejemplo (staging): `tickets.id = 73` — filas en `ticket_lines.precio` contienen ints como `500000`, `200000`.
- Scripts diagnóstico existentes: `scripts/inspect_ticket_row.py`, `scripts/debug_check_ticket.py` (ambos usan `read_from_db` para comprobar conversión de céntimos → euros).

Causa raíz (hipótesis técnica)
- Convención mixta: algunos escritores guardan en céntimos (INTEGER), otros guardan en unidades (REAL/Decimal). Lectores y renderizadores no normalizan consistentemente usando el adapter (`read_from_db`/`prepare_for_db`).

Archivos críticos identificados (prioridad alta)
- `kool_tpv/modulos/impresion/base_ticket_generator.py` — mitigación aplicada en `_format_currency` para detectar ints/float/Decimal sin fracción y usar `read_from_db`.
  - [kool_tpv/modulos/impresion/base_ticket_generator.py](kool_tpv/modulos/impresion/base_ticket_generator.py#L14-L51)
- `kool_tpv/modulos/impresion/venta_ticket_generator.py` — formatea `subtotal`, `total`, `importe_efectivo`, `importe_tarjeta` y las líneas (pvp/total).
  - [kool_tpv/modulos/impresion/venta_ticket_generator.py](kool_tpv/modulos/impresion/venta_ticket_generator.py#L62)
  - [kool_tpv/modulos/impresion/venta_ticket_generator.py](kool_tpv/modulos/impresion/venta_ticket_generator.py#L337-L355)
- `kool_tpv/utils/widgets/ticket_carrito.py` — UI usa `formatter.format_precio` pero en ramas cae a `float(...)` y f-strings.
  - [kool_tpv/utils/widgets/ticket_carrito.py](kool_tpv/utils/widgets/ticket_carrito.py#L701-L713)
- `kool_tpv/modulos/informes/informes_view.py` — tablas e informes usan `formatter.format_precio` en filas de resultados.
  - [kool_tpv/modulos/informes/informes_view.py](kool_tpv/modulos/informes/informes_view.py#L433-L485)
- `kool_tpv/modulos/clientes/services/clientes_tops_service.py` — agregaciones `SUM(tl.precio * tl.cantidad)` pueden estar usando céntimos sin conversión.
  - [kool_tpv/modulos/clientes/services/clientes_tops_service.py](kool_tpv/modulos/clientes/services/clientes_tops_service.py#L134-L172)
- Tests/fixtures que documentan la convención de céntimos:
  - [tests/test_ticket_print.py](tests/test_ticket_print.py#L55-L62)
  - [tests/test_money.py](tests/test_money.py#L7-L11)
- Scripts de esquema/migración ya presentes:
  - [scripts/fix_precios_and_fks.py](scripts/fix_precios_and_fks.py#L112-L117)
  - [scripts/audit_kool_bd_schema.py](scripts/audit_kool_bd_schema.py#L72)

Recomendaciones (ordenadas, seguras)
1. NO desplegar cambios masivos en producción hasta validar en staging.
2. Entregar este informe a la persona responsable y pedir aprobación para proceder.
3. Pasos técnicos (aplicar en staging primero):
   - Auditar lectores: reemplazar en renderizadores y generators la lectura directa por `read_from_db` (contrato: los lectores siempre reciben céntimos desde la BD y convierten a `Decimal` en euros para mostrar).
   - Auditar escritores: asegurar que los servicios que insertan/actualizan precios/totales usan `prepare_for_db` para persistir en céntimos.
   - Normalizar tests/fixtures a la convención de céntimos.
   - Ejecutar script de migración en staging para convertir columnas `REAL`/`NUMERIC` ambigüas a `INTEGER` (céntimos) usando `scripts/fix_precios_and_fks.py` adaptado si hace falta.
   - Ejecutar suite de tests e integración (especialmente `tests/test_ticket_print.py`) y verificar tickets impresos en staging (ej.: `id=73`).
4. Después de validar en staging, desplegar PRs por área (writes → reads → tests) y ejecutar migración en producción fuera de horas pico.

Adjuntos útiles
- Scripts de diagnóstico: `scripts/inspect_ticket_row.py`, `scripts/debug_check_ticket.py`.
- Reporte preliminar de call-sites (CSV): `reports/money_callsites.csv` (ya generado parcialmente).

Próximos pasos que puedo ejecutar ahora (elige una):
- GENERAR INFORME DETALLADO CSV con todos los call‑sites (archivo en `reports/`), o
- Crear PRs que apliquen `read_from_db` en los 10 lectores más críticos, o
- Preparar script de migración para staging.

Hecho por el agente: informe creado en RESUMENES para compartir con terceros.
