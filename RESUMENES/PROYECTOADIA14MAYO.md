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
- [x] Implementación de `ensure_cents` y tests
- [ ] Fase de migración output
- [ ] Tests de integración `finalize_sale` extremo a extremo
- [ ] Corrección bug IVA combo (`crear_producto_ui.py`)
- [ ] Bugs pendientes en `financial.py` (ver sesión 18/05)

## Apéndices

- Enlaces a archivos clave (presentes en el repo).  
- Logs relevantes y snippets.


---
Fin del informe preliminar.

---

# Sesión de trabajo — 18 de mayo de 2026

## Qué se ha hecho

### 1. Corrección del bug crítico en `_format_currency`
- Eliminada la heurística en `BaseTicketGenerator._format_currency` que causaba que `Decimal('144.00')` se mostrase como `1.44 €`.
- Establecido contrato explícito por tipo: `int` → centavos, `Decimal/str` → euros, `float` → euros con WARNING, `bool` → siempre TypeError.
- Verificado manualmente en la GUI: el usuario confirmó que el bug está corregido.

### 2. Implementación de `ensure_cents` y aliases de tipo
- Añadidos `CentsInt = NewType('CentsInt', int)` y `EurosDecimal = Decimal` en `kool_tpv/utils/money.py`.
- Añadida función `ensure_cents(val)` que centraliza la conversión segura a centavos.

### 3. Flag `STRICT_MONEY_CONTRACT`
- Añadida variable de entorno `STRICT_MONEY_CONTRACT` en `base_ticket_generator.py`.
- Con `STRICT_MONEY_CONTRACT=0` (por defecto): `float` acepta con WARNING.
- Con `STRICT_MONEY_CONTRACT=1` (CI/dev): lanza `TypeError` para tipos incorrectos.

### 4. Tests unitarios (35/35 en verde)
- `tests/test_money.py`: 16 tests cubriendo `from_cents`, `to_cents`, `ensure_cents` con todos los tipos y casos de error.
- `tests/test_format_currency_guard.py`: 9 tests verificando el nuevo contrato (incluye el caso `Decimal('144.00')` que era el bug original).
- `tests/test_financial.py`: 11 tests para `calculate_resumen` (vacío, IVA 0%, IVA 21%, cantidades, devolución, puntos canjeados, IVA mixto, descuento %, descuento directo).

### 5. Bug detectado: IVA combo en `crear_producto_ui.py` (sin corregir aún)
- Al crear un artículo con IVA 4%, el combo solo muestra `21%`.
- **Causa raíz**: el combo se construye con `SELECT DISTINCT tipo_iva FROM productos` — si no existe ningún producto con `tipo_iva=4` en la DB, el 4% no aparece.
- El fallback `[(21,'21'), (4,'4')]` solo se activa cuando no hay conexión a DB, nunca en uso normal.
- **Corrección pendiente**: fusionar los valores de DB con el conjunto canónico `{0, 4, 10, 21}` en el método `_load_db_options` de `crear_producto_ui.py`.

## Bugs conocidos pendientes (sin tocar, requieren permiso)

1. **`financial.py` — `total_bruto_original` incorrecto en path de descuento**: devuelve valor post-descuento en lugar de pre-descuento.
2. **`financial.py` — `gross_by_type` con `tipo_iva=0` + descuento**: el cálculo resulta en cero, haciendo que el total sea 0.00€.
3. **`carrito_service.py` — `get_subtotal()`/`get_iva_desglose()`**: devuelven `Decimal` sin quantizar (legacy, no está en el flujo principal).
4. **`tpv_controller._build_ticket_payload` — `cambio_cents`**: potencial negativo si `efectivo=None`.

## Estado de la fase de pruebas manuales
- En curso: verificación manual de ticket de venta normal (paso a paso).
- Detectado el bug de IVA combo antes de poder completar la prueba manual.
- Siguiente: corregir bug IVA → retomar verificación manual ticket normal → ticket con tesoro → ticket con descuento.

---

# Sesión de trabajo — 19 de mayo de 2026

## Qué se ha hecho

### 1. Bug IVA combo corregido — `crear_producto_ui.py` ✅
- El combo de IVA ahora siempre muestra `{0, 4, 10, 21}` combinado con valores de BD.
- Ya no depende de que existan productos previos con ese tipo de IVA.

### 2. `financial.py` — rounding y cálculos de resumen ✅
- Corregidos cálculos de `calculate_resumen` (subtotal, iva, total).
- 10/10 tests en `test_financial.py` pasan.

### 3. Ruta completa de escritura/lectura de `iva_desglose` (4 archivos) ✅
- `tpv_controller.py` — serializa desglose IVA como JSON en `_build_ticket_payload`
- `venta_processor.py` — propaga `iva_desglose_json` a `repo.insert_ticket()`
- `ticket_repository.py` — `insert_ticket()` escribe `iva_desglose` en la BD (19 columnas)
- `impresora_service.py` — SELECT incluye `subtotal, iva_desglose`; fallback para tickets antiguos sin ese campo
- `tests/test_ticket_print.py` — schema in-memory actualizado con `iva_desglose TEXT DEFAULT '{}'`

### 4. Bug A corregido — cambio negativo en venta con tarjeta ✅
- `tpv_controller.py`: `cambio_cents = max(0, efectivo + tarjeta - total)`
- Antes: si `efectivo=None`, el cálculo podía producir cambio negativo.

### 5. Bug B corregido — venta en efectivo con importe insuficiente ✅ (confirmado en GUI)
Tres capas de defensa en `cash.py` + guardia final en `tpv_controller.py`:

**Capa 1 — `_on_entry_change`:**
- Si `cambio < 0`, se hace `return` ANTES de almacenar `self.efectivo`. Importe insuficiente nunca se persiste. Estado vuelve a `waiting`.

**Capa 2 — `_on_action` (estado `waiting`):**
- Si `cambio < 0`, muestra "Importe insuficiente — faltan X.XX €" y retorna sin transicionar a `calculated`.

**Capa 3 — `_on_action` (estado `calculated`):**
- Eliminado el fallback inseguro `except Exception: total = Decimal('0')` que permitía colar ventas con total=0.
- Si `get_total()` devuelve 0 (error), muestra "Error al leer el total" y retorna (fail-closed).

**Guardia final — `tpv_controller.finalize_sale`:**
- Antes de construir `ticket_data`, verifica `efectivo >= total` para pagos en efectivo.
- Muestra error y retorna si no se cumple.

## Nota de diseño: tabla `precios`
- Los precios históricos se acumulan en `precios` (un registro por cambio de precio).
- El precio vigente es **siempre el último registro** (`MAX(id)`). Diseño intencional.
- Ejemplo: Pepino Azulado tiene 11.84 € (anterior) y 12.00 € (vigente). No es un bug.

## Bugs conocidos pendientes (sin tocar)
1. **Fidelización — `tesoro_total` / `total_compras_euros`**: todos los clientes tienen 0 tras múltiples ventas de test. El flujo de actualización del cliente posiblemente no se ejecuta o falla silenciosamente. Por investigar en la revisión de "venta con cliente".
2. **Ticket carrito visor**: no muestra bien el desglose. Aplazado por el usuario, baja prioridad.

## Revisión en curso: todos los tipos de venta

Objetivo: verificar que cada tipo de venta genera un ticket correcto y actualiza la BD de forma coherente.

| Tipo de venta | Estado |
|---|---|
| Venta con cliente (fidelización) | 🔄 En curso |
| Venta con tarjeta | ⏳ Pendiente |
| Venta mixta (efectivo + tarjeta) | ⏳ Pendiente |
| Venta con descuento (% y directo) | ⏳ Pendiente |
| Devolución | ⏳ Pendiente |
| Venta con canje de tesoro | ⏳ Pendiente |

Para cada tipo se comprueba:
- El ticket impreso / generado es correcto (totales, IVA, forma de pago, cliente)
- La BD refleja el cambio: `tickets`, `ticket_lines`, `payments`, `clientes` (si aplica), `productos` (stock, ventas)

---

# Sesión de trabajo — 20 de mayo de 2026

## Qué se ha hecho

### 1. Fix: módulo Reset de Configuración — CTkScrollableFrame `winfo_exists()` = 0 ✅
- `reset_ui.py`: `CTkScrollableFrame` envuelto en un `CTkFrame` externo; `get_widget()` devuelve el frame externo.
- Solución: el `CTkScrollableFrame` necesita estar dentro del event loop de Tk antes de que `winfo_exists()` devuelva 1. El frame exterior lo garantiza.
- Commit: `bd21eb1`

### 2. Nuevas secciones en Reset de Configuración ✅
- **FIDELIZACIÓN**: botón `Borrar points_movements` → `reset_service.borrar_points_movements()` (`DELETE FROM points_movements`).
- **PRODUCTOS**: botón `Reset stock y ventas` → `reset_service.reset_stock_productos()` (`UPDATE productos SET stock_actual = 0, ventas_totales = 0`).
- Archivos: `reset_ui.py` y `reset_service.py`.
- Commit: `3a2170e`

### 3. Fix: `tesoro_historico` no se decrementaba en devoluciones ✅
- **Problema**: en `DevolucionProcessor.process()`, al revertir tesoro tras una devolución, solo se restaba de `tesoro_total`. El campo `tesoro_historico` (acumulado histórico para calcular nivel de fidelización) nunca bajaba.
- **Fix**: el `UPDATE` ahora decrementa ambos campos simultáneamente:
  ```sql
  SET tesoro_total    = MAX(0, COALESCE(tesoro_total, 0) - ?),
      tesoro_historico = MAX(0, COALESCE(tesoro_historico, 0) - ?)
  ```
- Archivo: `kool_tpv/modulos/ticket/devolucion_processor.py`
- Commit: `2712b57`
- **Nota de diseño**: si `tesoro_historico` baja, el nivel del cliente también puede bajar (usa `tesoro_historico` como base). Si en el futuro se desea que el nivel nunca baje, separar el cálculo de nivel del valor de `tesoro_historico`.

### 4. Fix: columna "Ventas" en subvista Stock mostraba valor incorrecto tras devolución ✅
- **Problema**: `ProductoRepository.listar_con_resumen()` calculaba `ventas` con una subquery:
  ```sql
  COALESCE((SELECT SUM(tl.cantidad) FROM ticket_lines tl WHERE tl.sku = p.sku), 0) AS ventas
  ```
  Esta subquery suma **todas** las líneas de ticket (ventas + devoluciones), ya que ambas se guardan con cantidad positiva en `ticket_lines`. Resultado: tras 1 venta + 1 devolución, la subquery mostraba 2 en lugar de 0.
- **Fix**: sustituida la subquery por `COALESCE(p.ventas_totales, 0) AS ventas`. El campo `productos.ventas_totales` se actualiza correctamente en cada venta (±1) y devolución.
- Archivo: `kool_tpv/modulos/almacen/producto_repository.py`
- Commit: `3a549e0`

### 5. Análisis completo de la vista Tickets (sin cambios — diferido) ⏳
- La vista actual (`TicketsUI`) usa el patrón overlay (`.show()/.hide()`), NO el patrón subvista (`push_subview`).
- Accede a la BD con **SQL raw directamente en la clase UI** — sin service ni repository para lectura.
- `TicketRepository` existe pero solo tiene métodos de **escritura** (INSERT). No hay método de listado.
- **Plan acordado para la sesión siguiente**:
  1. Añadir `listar_tickets(termino)` a `TicketRepository`
  2. Crear `kool_tpv/modulos/tpv/subviews/tickets_subview.py`
  3. Actualizar `button_action_mapper.py`: cambiar `_show_ui(view, '_tickets_ui')` por `push_subview`
  4. Limpiar `tpv_controller.py`: eliminar instanciación de `TicketsUI` al inicio
  5. Eliminar archivos viejos: `actions/tickets/tickets_ui.py`, `tickets_base_ui.py`, `tickets_handler.py`, `__init__.py`

## Bugs conocidos pendientes (sin tocar)
1. **Revisión sistemática de tipos de venta** (19/05): tabla de progreso no completada; pendiente verificar venta con tarjeta, mixta, descuento, canje tesoro.
2. **Ticket carrito visor**: no muestra bien el desglose. Aplazado por el usuario, baja prioridad.
