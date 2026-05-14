# Auditoría técnica — PROYECTO A DIA 14 MAYO 2026

> Resumen completo del código, arquitectura, problemas detectados, y plan de remediación.

Fecha: 2026-05-14
Autor: Informe automatizado (revisión de repo local)
Alcance: Análisis estático y dinámico ligero del repositorio `KOOL_TPV_V2` en workspace.

## Resumen Ejecutivo

- Estado: Proyecto TPV de Python con UI (CustomTkinter), servicios modulares (TPV, impresión, fidelización), y persistencia SQLite/DB.
- Hallazgo crítico: manejo de dinero mezclado entre `int` (céntimos) y `Decimal` (euros) en distintas capas; heurística frágil en `BaseTicketGenerator._format_currency` causa visualizaciones incorrectas (p. ej. `144.00 €` mostrado como `1.44 €`).
- Recomendación principal: normalizar contrato monetario y plan de migración controlado; implementar `ensure_cents` y flag `STRICT_MONEY_CONTRACT`, migrar a uso consistente de `int` en persistencia y `Decimal` o `Money VO` en lógica según la estrategia elegida.

## Metodología

- Exploración del repo: búsqueda de patrones (`prepare_for_db`, `read_from_db`, `to_cents`, `from_cents`, `generar_ticket_desde_id`, `VentaProcessor`, `TpvController`).
- Lectura manual de archivos clave (carpeta `kool_tpv/modulos`, `kool_tpv/base_datos`, `kool_tpv/utils`).
- Reproducción mínima vía snippets sugeridos (no ejecutados automáticamente aquí).

## Visión general del repositorio (top-level)

- `kool_tpv/` — código principal del proyecto (módulos, utils, base_datos, modulos).
- `scripts/` — scripts auxiliares y de diagnóstico.
- `tests/` — pruebas unitarias y de integración.
- `RESUMENES/` — documentación y notas de migración.
- `assets/`, `logs/`, `reports/` — recursos y logs.

## Arquitectura general

Componentes principales:
- UI: `main.py`, `kool_tpv/modulos/tpv/*` (vistas y controladores).  
- Lógica de negocio: `TpvService`, `CarritoService`, `financial` (carrito/financial.py).  
- Persistencia: `kool_tpv/base_datos/*` (ticket_service, repositories, money_adapter).  
- Impresión: `kool_tpv/modulos/impresion/Imp...` (`ImpresoraService`, `BaseTicketGenerator`, generadores concretos).  
- Helpers: `kool_tpv/utils/*` (money, formatter_service, keyboard_manager, etc.).

Separación: razonable en capas (UI -> servicios -> repositorio), pero con puntos de mezcla de responsabilidades (ej.: formateo y heurísticas en generadores, logging/formatting intercalado en servicios).

## Inventario módulo por módulo (resumen)

### `kool_tpv/modulos/tpv`
- Propósito: lógica del TPV, UI y controladores. Archivos clave:
  - `tpv_controller.py`: orquestación de flujo de venta (finalize_sale), construye payloads y llama a `TpvService`.
  - `tpv_service.py`: servicio que llama a `save_ticket` y a impresión.
  - `carrito/carrito_service.py`: gestión del carrito, devuelve `Decimal` en sus getters.
  - `carrito/financial.py`: cálculos financieros por línea (usa `Decimal`).
- Lo bueno: estructura modular, separación UI/servicio.
- Riesgos: `carrito` usa `Decimal` en memoria mientras `ticket_service`/DB usan céntimos; falta contrato explícito.
- Recomendación: documentar contrato y adaptar `carrito` para expedir datos ya convertidos al boundary (o cambiar formateador).

### `kool_tpv/modulos/ticket` (processors)
- Archivos clave:
  - `venta_processor.py`: inserta ticket y líneas; llama a `prepare_for_db` para convertir precios de línea y totales.
- Lo bueno: processors encapsulan la persistencia.
- Riesgo: callers asumen payload con claves `_cents`; no está completamente explícito en tipos.
- Recomendación: tipar `process()` y documentar payload.

### `kool_tpv/base_datos`
- Archivos clave: `ticket_service.py` (shim), `money_adapter.py`, repositorios.
- Observaciones: Adapter `prepare_for_db/read_from_db` está correcto; centraliza conversiones.
- Recomendación: agregar `NewType`/aliases en `money.py` y `ensure_cents` helper.

### `kool_tpv/modulos/impresion`
- Archivos clave: `impresora_service.py`, `base_ticket_generator.py`, `venta_ticket_generator.py`.
- Problema detectado: `BaseTicketGenerator._format_currency` contiene heurística que intenta detectar céntimos por valor (>=100) y produce bug. Debe recibir valor con unidad explícita.
- Recomendación: forzar contrato, usar `ensure_cents` o `STRICT` flag, y añadir tests.

### `kool_tpv/utils`
- Archivos clave: `money.py` (to_cents/from_cents), `formatter_service.py`.
- Lo bueno: helpers concentrados.
- Recomendación: añadir `CentsInt = NewType('CentsInt', int)` y `EurosDecimal = Decimal` y `ensure_cents` helper.

## Análisis del flujo crítico: generación de ticket

1. UI llama a `TpvController.finalize_sale()` → obtiene `resumen = carrito_service.get_resumen_financiero()` (Decimal euros).  
2. `TpvController._build_ticket_payload()` usa `prepare_for_db(_dec(resumen.get('total')))` para crear `total_cents` (convertir a int).  
3. El `processor` (`VentaProcessor.process`) inserta ticket y líneas usando `precio_cents = prepare_for_db(pvp_euros)` (céntimos).  
4. Tras persistir, `TpvService._print_ticket()` intenta generar/imprimir ticket: lee `ticket_text` snapshot; si no existe, llama `ImpresoraService.generar_ticket_desde_id(ticket_id)` que reconstruye ticket desde DB y llama al generador.  
5. `BaseTicketGenerator._format_currency` recibe valores y aplica heurística `if Decimal and val == val.to_integral() and abs(val) >= 100: treat as cents` → provoca la interpretación errónea de `Decimal('144.00')`.

Líneas exactas (ejemplos):
- `TpvController._build_ticket_payload` -> `'total_cents': prepare_for_db(_dec(resumen.get('total', '0')))` ([kool_tpv/modulos/tpv/tpv_controller.py#L256])
- `money_adapter.prepare_for_db` -> en [kool_tpv/base_datos/money_adapter.py] (usa `to_cents`)
- `BaseTicketGenerator._format_currency` -> [kool_tpv/modulos/impresion/base_ticket_generator.py] (heurística en `if isinstance(val, Decimal) and val == val.to_integral() and abs(val) >= 100`)

## Base de datos (esquema relevante)

Tablas principales (observadas por código/tests):
- `tickets` — campos: `id`, `num_ticket`, `created_at`, `cajero`, `total` (almacenado como céntimos int), `subtotal`, `pagado`, `cambio`, `forma_pago`, `ticket_text` (snapshot) ...
- `ticket_lines` — campos: `id`, `ticket_id`, `sku`, `nombre`, `cantidad`, `precio` (céntimos int), `tipo_iva`, `line_tipo`, `producto_id` ...
- `payments` — `ticket_id`, `metodo`, `importe` (céntimos) ...

Observación: el esquema usa céntimos en persistencia, lo que es correcto y consistente con `money_adapter`.

## Money handling: adapters y servicios

- `kool_tpv/utils/money.py`: `to_cents(from Decimal)` y `from_cents` están implementados — correcto.
- `kool_tpv/base_datos/money_adapter.py`: `prepare_for_db` y `read_from_db` usan `to_cents`/`from_cents` — correcto.
- Problema: `CarritoService` y `financial` usan `Decimal` en memoria; impresora genera strings asumiento heurística o int. Falta contrato explícito y migración controlada.

## Calidad de código y pruebas

- Hay tests en `tests/` cubriendo repositorios y generación de ticket (`tests/test_ticket_print.py`).  
- Faltan tests que validen contratos monetarios end-to-end; es necesario añadir tests de integración que simulen finalize_sale.
- Logging: buena práctica general, pero ciertos errores se registran y se silencian; preferir fallos detectables en CI.

## Seguridad y Operaciones

- Uso de transacciones en `ticket_service`/processors: indicios de transacción pero revisar integridad para rollback en fallos.
- Logs y trazabilidad razonables.

## Estado actual y problema raíz

- Problema raíz: mezcla de representaciones monetarias y heurística en `BaseTicketGenerator._format_currency` produce errores de visualización.
- Punto exacto de fallo: la heurística que interpreta `Decimal('144.00')` como entero y lo convierte a céntimos.

## Solución profesional (priorizada)

1. Implementar `ensure_cents` en `kool_tpv/utils/money.py` y aliases `CentsInt = NewType(...)`.  
2. Añadir `STRICT_MONEY_CONTRACT` flag (config/env) y `ensure_cents(..., allow_convert=not STRICT)`.  
3. Actualizar `BaseTicketGenerator._format_currency` para usar `ensure_cents` y dejar de usar heurística.  
4. Añadir tests unitarios y de integración (simulate finalize_sale).  
5. Migración por fases: auto-convert + warnings → CI strict → producción.

## Plan de trabajo y estimación (rápido)

- Fase 0 (2–4h): Implementar `ensure_cents`, tests unitarios básicos.  
- Fase 1 (4–8h): Actualizar `BaseTicketGenerator` y `ImpresoraService` para usar ensure, ejecutar tests, arreglar fallos.  
- Fase 2 (1–2 días): Revisar callers, actualizar `financial.py`/`carrito` si se opta por usar ints en memoria.  

## Pruebas y comandos recomendados

- REPL reproducer (usar snippet proporcionado en el informe).  
- `pytest -q tests/test_ticket_print.py::test_generate_ticket_from_cents`  

## Checklist de entrega

- [x] Localización del bug
- [x] Plan profesional propuesto
- [ ] Implementación de `ensure_cents` y tests
- [ ] Fase de migración output

## Apéndices

- Enlaces a archivos clave (presentes en el repo).  
- Logs relevantes y snippets.


---
Fin del informe preliminar.
