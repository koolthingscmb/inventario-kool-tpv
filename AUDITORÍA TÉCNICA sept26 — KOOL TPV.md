# AUDITORÍA TÉCNICA — KOOL TPV

> Auditoría técnica completa del proyecto realizada sobre el código fuente,
> la base de datos real y el historial git. Septiembre 2026.
>
> Rama auditada: `windows-beta` — último commit: `8657ac9`.
> Datos verificados mediante inspección de código, esquema SQLite y logs reales.

---

```
==================================================
1. RESUMEN DEL PROYECTO
==================================================
```

**Qué es**: Kool TPV es un TPV (Terminal Punto de Venta) de escritorio completo, construido en Python con interfaz gráfica customtkinter/Tkinter, para la tienda Kool Things / Kool Dreams.

**Problema que resuelve**: La tienda vende dos tipos de mercancía — productos comprados a proveedores (mangas, figuras, merchandising) **y productos fabricados en taller propio** (camisetas, láminas impresas bajo demanda). Un TPV estándar no cubre el segundo caso; este software unifica: venta en tienda, inventario, gestión de producción interna (diseños × tipos × colores × tallas), fidelización de clientes, pedidos de clientes, y sincronización de stock con la tienda online Shopify.

**Usuario objetivo**: Los empleados (cajeros) y el dueño/taller de una tienda física de merchandising/impresión.

**Módulos identificados** (menú principal, verificado en `buttons_config.json` y `main.py`):
`TPV`, `ALMACÉN`, `CLIENTES`, `INFORMES`, `SHOPIFY`, `PRESENCIA`, `CONFIG`, `PRODUCCIÓN`.

**Arquitectura general**: Aplicación monolítica de escritorio con tres capas por módulo: **UI (Tkinter) → Service → Repository → Database wrapper (SQLite)**. Estado global mínimo: `App` (root CTk) posee la conexión DB, `KeyboardManager`, `BarcodeService` y un stack de "power handlers" para navegación.

---

```
==================================================
2. TECNOLOGÍAS
==================================================
```

| Componente | Realidad |
|---|---|
| Lenguaje | Python **3.14.2** (verificado en `.venv`) |
| GUI | **customtkinter 5.2.2** sobre Tkinter estándar; mezcla deliberada de `tk.Frame` y `ctk.CTk*` |
| Base de datos | **SQLite** (fichero `kool_tpv/base_datos/kool_bd.db`, 2.7 MB reales) |
| PDFs | **reportlab 4.4.10** (exportación de albaranes e informes) |
| Códigos de barras | **python-barcode 0.16.1** (generación) + captura por teclado (lector HID) |
| Impresión tickets | **ESC/POS propio** (`escpos_renderer.py`, bytes crudos, codepage cp858) + adaptador **pywin32/win32print** en Windows |
| Imágenes | **Pillow 12.1.0** (logos, badges rasterizados para tickets) |
| Backup nube | **Google Drive API** (`google-api-python-client`, OAuth2 con `google-auth-oauthlib`) |
| IA | **openai 3.11.0** (generación SEO con modo `json_object`) |
| APIs de datos | **requests**: AniList GraphQL, Jikan, MangaDex, Google Books; **duckduckgo-search 8.1.1** (importación lazy — en Windows falla y se desactiva) |
| Shopify | **Admin GraphQL API** (`inventorySetOnHandQuantities`) vía requests |
| WhatsApp | Servicio propio que detecta WhatsApp Desktop y abre conversación (no API oficial) |
| Config | Ficheros **JSON** (`layout_config.json`, `colors_config.json`, `font_config.json`, `buttons_config.json`, `button_styles.json`, `ui_dialogs.json`) + tabla `configuracion` en BD |
| Logs | `logging` estándar → `kool_tpv/logs/application.log` + stdout |
| SO objetivo | **Windows y macOS** (código multiplataforma: `sys._MEIPASS` para PyInstaller, `state('zoomed')` con fallback, win32print condicional) |
| Empaquetado | Preparado para **PyInstaller** (`paths.py` resuelve recursos en `_MEIPASS`) |

**Instaladas pero poco/no usadas**: `coverage` (solo para medir tests), `pywin32` (solo Windows). `duckduckgo-search` está degradada a opcional.

---

```
==================================================
3. ARQUITECTURA DEL SOFTWARE
==================================================
```

**Estructura**:

```
main.py                    → App (CTk root), menú, power-stack, wiring global
kool_tpv/
  paths.py                 → Resolución de rutas (dev + PyInstaller)
  base_datos/              → Database wrapper, db_init (migraciones), money_adapter,
                             servicios de dominio (ticket, cierre, usuario, audit...)
  modulos/<modulo>/        → cada módulo: *_view.py, services/, repositories/, models/, ui/
  utils/                   → KeyboardManager, BarcodeService, ScaleManager,
                             dialogs/, widgets/ (VirtualNavList, ToastWidget, combos),
                             factories/ButtonFactory, templates/ de páginas
  services/                → CloudBackupService, WhatsAppService
  config/                  → loaders de JSON
```

**Separación UI/lógica/datos**: Sí, con calidad **desigual por módulo**. `produccion` es el mejor ejemplo (models/repositories/services/ui separados formalmente). `almacen` y `tpv` mezclan más: hay "services" en `base_datos/` que son en realidad repositorios (p. ej. `ticket_service.py`, `cierre_service.py` ejecutan SQL directo).

**Patrones reconocibles**:
- **Repository pattern** real en produccion, clientes/pedidos, fidelización, ticket.
- **Service facade**: `ProduccionConfigService` agrega 10 repositorios.
- **Strategy**: procesadores de ticket por tipo (`venta`, `devolución`, `cierre`, `descuento`, `subida_nivel`, `fidelización`) y `payment_controllers` por método de pago (efectivo, tarjeta, multi, vale, devolución, resumen) con `PaymentControllerFactory`.
- **Observer/callback**: `BarcodeService.set_handler()` — los módulos se suscriben al escáner central.
- **Stack de handlers LIFO**: sistema "Power" (Esc) donde cada vista registrada tiene prioridad sobre la anterior.
- **Context manager transaccional** en `Database.transaction()` con soporte de **SAVEPOINTs anidados**.

**Concurrencia**: Threads para Shopify sync y búsquedas externas, con callbacks a UI vía `after()`. Punto débil real: **una única conexión SQLite compartida entre threads** (`check_same_thread=False`) — ya produjo `sqlite3.InterfaceError` en producción.

**Gestión de errores**: `try/except` + `logging.exception` casi universal; en UI, `ToastWidget` para feedback. Hay muchos `except Exception: pass` en caminos no críticos (defensivo, a veces excesivo).

**Configuración**: Dual — JSON para layout/visual, tabla `configuracion` para claves operativas (incl. tokens Shopify en claro).

**Puntos fuertes**: separación repository/service en módulos nuevos; wrapper DB con transacciones anidadas; factoría de botones con paletas por módulo; migraciones auto-aplicadas al arrancar.

**Puntos débiles (god objects)**: `importar_albaran.py` (1.655 líneas), `tpv_controller.py` (1.635), `impresora_service.py` (1.088), `crear_producto_ui.py` (1.255). `db_init.py` es un procedimiento monolítico de ~700 líneas con ~40 migraciones embebidas inline. Duplicación menor: `modulos/config` y `modulos/configuracion` coexisten; `_mantenimiento/codigo_obsoleto` contiene código muerto en el repo.

---

```
==================================================
4. PRODUCTOS Y CATÁLOGO
==================================================
```

Tabla `productos` (2.324 registros reales). Relacionadas: `categorias`, `tipos`, `codigos_barras` (multi-EAN por producto), `precios` (historial con flag activo), `proveedores`, `productos_menu`, `favoritos`.

| Función | Estado |
|---|---|
| Alta (formulario completo: nombre, categoría, tipo, PVP, coste, IVA, EAN, SEO) | IMPLEMENTADA |
| Edición individual + carga por diálogo | IMPLEMENTADA |
| **Edición masiva** (multi-selección, modos NOMBRES/PVP, transacción atómica, auditoría) | IMPLEMENTADA |
| Eliminación | IMPLEMENTADA |
| Categorías y Tipos (con color/icono, CRUD propio) | IMPLEMENTADAS |
| Multi-código de barras + escáner global + **alta rápida al escanear código desconocido** | IMPLEMENTADA |
| Precios con historial (`precios` con activo) | IMPLEMENTADO |
| IVA por producto con desglose en ticket (`iva_desglose` JSON en tickets) | IMPLEMENTADO |
| Stock por producto con movimientos auditados | IMPLEMENTADO |
| Proveedores con mapeo de colores/tipos/géneros/tallas (para importar albaranes) | IMPLEMENTADO |
| Búsqueda dinámica, filtros por categoría/tipo | IMPLEMENTADA |
| **Importación de albaranes CSV** con validador, fórmulas y mapeo de columnas | IMPLEMENTADA (uno de los subsistemas más grandes) |
| Exportación albarán CSV/PDF | IMPLEMENTADA |
| Imágenes de producto | PARCIAL — badges/iconos existen para tickets; `imagen_url` listada como pendiente en PENDIENTES.md |
| Campos SEO (title, descripción, metas) + autofill con IA/APIs | IMPLEMENTADO en ficha |

---

```
==================================================
5. VENTAS / TPV
==================================================
```

| Función | Estado |
|---|---|
| Crear venta, añadir/quitar líneas, modificar cantidad | IMPLEMENTADA |
| Escanear producto → añade al carrito; EAN desconocido → alta rápida | IMPLEMENTADA |
| Descuentos (porcentaje, euros, por línea y global; catálogo con auditoría y permiso) | IMPLEMENTADA |
| IVA multi-tasa con desglose | IMPLEMENTADA |
| Métodos de pago: efectivo (con cambio), tarjeta, **mixto**, **vale**, canje de puntos | IMPLEMENTADOS |
| Devoluciones (subvista dedicada, genera vale, restaura stock, permiso requerido) | IMPLEMENTADA |
| Vales (crear, listar, aplicar, vinculados a pedidos) | IMPLEMENTADO |
| Tickets: guardar texto completo, reimprimir, historial con filtros | IMPLEMENTADO |
| Asociar cliente y cajero a venta | IMPLEMENTADO |
| Favoritos (grid configurable de productos rápidos) | IMPLEMENTADO |
| Reposición (cola de productos vendidos pendientes de reponer, fichero persistente) | IMPLEMENTADO — subsistema propio |
| Detección de productos con datos incompletos al entrar al TPV | IMPLEMENTADO |
| Cancelación de venta (vaciar carrito) | IMPLEMENTADA |
| Facturas emitidas al cliente | **NO IMPLEMENTADA** — la tabla `facturas`/`facturas_lines` existe en el esquema pero tiene **0 filas** y no hay INSERT en el código |
| Venta en espera / recuperar carrito | PARCIAL (persistencia de borradores vinculada a reposición) |

Flujo: `CarritoService` (estado en memoria, Decimal) → `financial.calculate_resumen()` (subtotal, IVA por tasa, descuento, puntos, vale) → `TpvController.finalize_sale()` → ticket + pagos + movimientos de stock + puntos de fidelización en transacción.

---

```
==================================================
6. STOCK
==================================================
```

- **Entrada**: albaranes (manual, CSV importado, borrador→confirmado) — IMPLEMENTADO.
- **Salida**: ventas (descuento automático por línea de ticket) y salidas manuales — IMPLEMENTADO.
- **Ajustes manuales** con motivo y usuario — IMPLEMENTADO (`registrar_ajuste_manual`, dentro de transacción).
- **Historial**: `stock_movements` con `usuario_id` (auditoría completa de cada movimiento) — IMPLEMENTADO.
- **Stock de taller** (matriz tipo/color/talla/variante en `produccion_stock_colores_tallas`) separado del stock de productos comprados — IMPLEMENTADO.
- **Devoluciones** reponen stock — IMPLEMENTADO.
- **Pedidos de cliente** se actualizan al llegar stock (`actualizar_pedidos_por_stock`) — IMPLEMENTADO (automatización real).
- Stock mínimo / alertas automáticas de rotura — **NO IMPLEMENTADO**.
- Multi-almacén — NO IMPLEMENTADO (una sola ubicación lógica).
- **Post-venta**: la venta descuenta `productos.stock` y registra el movimiento; en producción, fabricar una prenda **consume stock base y suma stock de diseño**, y puede **incrementar el producto TPV vinculado** automáticamente (verificado en `produccion_ordenes_service._actualizar_stock_tpv_vinculado`).

---

```
==================================================
7. CLIENTES
==================================================
```

53 clientes reales. CRUD completo, búsqueda, historial de tickets, "TOPS" (ranking de clientes), **pedidos de cliente** con estados y líneas, comunicación vía **WhatsApp con plantillas configurables**, asociación de vales, fidelización con puntos y niveles. Todo IMPLEMENTADO. La facturación formal a cliente NO existe (no hay facturas).

---

```
==================================================
8. PROVEEDORES
==================================================
```

IMPLEMENTADO: CRUD de proveedores, **albaranes de entrada** (manual + importación CSV con validador, fórmulas y mapeo de columnas del proveedor), **devoluciones a proveedor** (salida manual), consulta/filtrado, exportación PDF/CSV con plantillas configurables, y mapeos proveedor↔colores/tipos/géneros/tallas para normalizar catálogos de proveedor.

---

```
==================================================
9. CAJA Y PAGOS
==================================================
```

- **Cierre de caja (arqueo)**: IMPLEMENTADO y sólido — `create_cierre_atomic`, numeración secuencial, snapshot de líneas en `cierres_lineas`, desglose por forma de pago, por cajero, por categoría, puntos de fidelización del periodo; reimpresión del ticket de cierre; borrado con permiso. 1.707 tickets reales registrados.
- **Apertura**: no hay apertura formal con fondo de caja — el cierre agrupa "tickets sin cierre".
- **Métodos de pago**: efectivo, tarjeta, mixto, vale, puntos — tabla `payments` soporta multi-pago por ticket.
- **Cajón portamonedas**: apertura ESC/POS con permiso `permiso_cajon` — IMPLEMENTADO.
- Ingresos/retiradas manuales de caja fuera de venta — NO encontrado como movimiento independiente.

---

```
==================================================
10. INFORMES Y ESTADÍSTICAS
==================================================
```

`InformesService` implementa: **resumen de ventas por rango** (nº tickets, total, media), **ventas diarias**, **ventas por cajero**, **ventas por producto**, **por categoría** y **por tipo** (con búsqueda dinámica de filtros), **stock por categoría/tipo**, **informe de presencia** (horas por usuario). Exportadores **CSV y PDF** propios. Producción tiene su propio `produccion_informes_service/repository`. Métricas reales: totales en céntimos, unidades vendidas. Informe de beneficio/margen agregado — **PARCIAL** (hay coste en productos pero no informe de margen consolidado).

---

```
==================================================
11. IMPRESIÓN Y DOCUMENTOS
==================================================
```

- **Tickets térmicos ESC/POS**: renderer propio a bytes (codepage cp858, negrita, doble altura, corte, apertura de cajón), **logo rasterizado**, **QR**, **código EAN-13**, **badge de nivel de fidelización** impreso según cliente.
- Tipos de ticket: venta, devolución, cierre de caja, descuento aplicado, subida de nivel, venta con fidelización — cada uno con su generator.
- Envío: **win32print** (Windows RAW), fallback consola/debug dump a fichero.
- **PDFs**: albaranes e informes vía reportlab. **CSV**: albaranes, informes, importación.
- Etiquetas de producto: generación de EAN existe (`barcode_gen_utils`); impresión de etiquetas dedicada — PARCIAL.
- Plantillas de textos de tickets, albarán, informes y WhatsApp — configurables desde UI — IMPLEMENTADO.

---

```
==================================================
12. USUARIOS Y SEGURIDAD
==================================================
```

- Usuarios con `rol` (Admin/Cajero), contraseña **SHA-256 sin sal** (`hashlib.sha256`), flags granulares: `permiso_cierre`, `permiso_descuento`, `permiso_devolucion`, `permiso_tickets`, `permiso_cajon`, personalización visual por usuario (`ui_color`, `banner_path`). 3 usuarios reales.
- **Sin pantalla de login global** — la autenticación es **por acción**: diálogo de contraseña al entrar a producción, aplicar descuento, cierre, etc. No hay sesiones.
- **Auditoría**: tabla `audit_logs` + `AuditService` (entidad, acción, responsable) — usada en operaciones sensibles (edición masiva, usuarios, fichajes corregidos).
- **Presencia**: fichaje entrada/salida con duración y corrección supervisada — IMPLEMENTADO.
- **Backup**: subida manual a Google Drive (OAuth) de la BD — IMPLEMENTADO; backup local `backups/` existe como directorio. Cifrado de BD: ninguno. Tokens de Shopify en la tabla `configuracion` en claro — punto débil real.

---

```
==================================================
13. BASE DE DATOS
==================================================
```

SQLite, **56 tablas**, ~30 índices deliberados (tickets por fecha/cajero, líneas, pagos, stock por SKU, presencia, audit, pedidos...). FKs declaradas con `ON DELETE CASCADE/SET NULL` y **activadas por conexión** (`PRAGMA foreign_keys=ON` en el wrapper). `journal_mode=delete` (sin WAL). Sistema de migraciones **propio e incremental**: `db_init.py` chequea `PRAGMA table_info`/`sqlite_master` y aplica ~40 migraciones (SQL y Python) al arranque. Money como **INTEGER céntimos** + `money_adapter`/Decimal. Backups: Google Drive + carpeta local.

---

```
==================================================
14. INTEGRACIONES
==================================================
```

| Integración | Estado |
|---|---|
| **Shopify Admin GraphQL** — sync de stock por SKU (manual por categoría/filtros y automática tras producción/albarán), log persistente en `shopify_sync_log` (184 entradas reales) | IMPLEMENTADA y probada en producción |
| **Google Drive** — backup de BD con OAuth | IMPLEMENTADO |
| **OpenAI** — generación de textos SEO (modo json_object, prompt configurable) | IMPLEMENTADO |
| **AniList / Jikan / MangaDex / Google Books** — autofill de ficha de producto (autores, kanji, géneros, ISBN) en **paralelo con ThreadPoolExecutor** | IMPLEMENTADO |
| **DuckDuckGo** — búsqueda web auxiliar | PARCIAL (lazy-import; en Windows se desactiva si falta) |
| **WhatsApp Desktop** — mensajes a clientes con plantillas | IMPLEMENTADO (apertura de conversación, no API oficial) |
| **Impresora térmica** — win32print/RAW + cajón | IMPLEMENTADO en Windows |
| **Lector de códigos** — captura global HID con detección de "estoy escribiendo en un Entry" | IMPLEMENTADO |

---

```
==================================================
15. FUNCIONALIDADES AVANZADAS (no-CRUD)
==================================================
```

1. **Sincronización Shopify asíncrona con trazabilidad**: hilos + cola de callbacks a Tkinter con guardas de ciclo de vida de widgets; log persistente por operación con motivo ("Producción de 2 uds (Diseño: Naruto)...").
2. **Motor de producción 4D**: tipo × variante × color × talla con grupos de tallas (N:M), matriz configurable, métodos de impresión por variante, extras con coste, y **propagación automática**: fabricar descuenta base, suma diseño y actualiza el producto TPV vinculado.
3. **Transacciones anidadas con SAVEPOINT** en el wrapper SQLite — permite atomicidad en operaciones compuestas (cierre de caja, edición masiva) sin romper transacciones externas.
4. **Cierre de caja atómico**: numeración, snapshot inmutable de líneas, desglose por pago/cajero/categoría en una sola transacción.
5. **Búsqueda multi-fuente en paralelo** (ThreadPoolExecutor) con fusión de resultados por prioridad de fuente e ISBN-match.
6. **Sistema de navegación por teclado global**: `KeyboardManager` con Protocol `Navigable` + mixins, ignorando flechas en campos de texto — la app es usable sin ratón.
7. **Fidelización con niveles y badges impresos**: puntos ("tesoro"), canje como método de pago, subida de nivel genera su propio ticket.
8. **Cola de reposición persistente en fichero** (`ReposicionStore`): lo vendido en TPV queda pendiente de reponer hasta que el albarán lo confirma.
9. **Importador CSV de albaranes** con parser, validador, fórmulas y mapeo visual de columnas.
10. **Migraciones auto-reparables al arranque** (incluye saneamiento de datos huérfanos, no solo DDL).

---

```
==================================================
16. CALIDAD DEL CÓDIGO (evaluación honesta)
==================================================
```

| Área | Nota | Justificación |
|---|---|---|
| Arquitectura | **7/10** | Capas reales y consistentes en módulos nuevos; inconsistencias en los antiguos (`base_datos/*_service` que son repos) |
| Legibilidad | **7/10** | Docstrings en la mayoría de clases/métodos, nombres claros en español, comentarios de intención |
| Modularidad | **7/10** | Módulos por dominio; pero vistas monolíticas de >1.000 líneas y acoplamiento al `App` global |
| Mantenibilidad | **6/10** | Config externalizada ayuda; god objects y `db_init.py` monolítico restan |
| Robustez | **7/10** | Transacciones, migraciones defensivas, fallbacks multiplataforma; pero conexión única multi-thread ya falló |
| Gestión de errores | **6/10** | Logging+toast sistemáticos; demasiados `except: pass` silenciosos |
| Seguridad | **4/10** | SHA-256 sin sal, tokens API en claro en BD, sin login de sesión |
| Testabilidad | **6/10** | Servicios desacoplados y tests headless reales; la UI mezclada limita la cobertura |
| Escalabilidad | **5/10** | SQLite monolítico y single-process; correcto para una tienda, no multi-tienda |

---

```
==================================================
17. TESTS
==================================================
```

**35 ficheros de test** con pytest en `tests/` (más `test_frozen_paths.py` en raíz). Cubren: auth, canje de puntos, carrito (integración y UI headless), cierres, devoluciones, descuentos, fidelización (repo+service), financial/money, payment factory, producto repo/service, ticket repo/processor/print, tpv controller/service, validación integral y **robustez de BD**. `coverage` instalado. Estimación honesta: **los servicios financieros y de ticket están bien cubiertos; la capa UI solo parcialmente (headless); producción y shopify apenas tienen tests** → cobertura global estimada ~25-35%.

---

```
==================================================
18. TAMAÑO DEL PROYECTO
==================================================
```

- **402 ficheros `.py`** en `kool_tpv/` (446 contando `_mantenimiento` obsoleto)
- **~94.300 líneas** de código Python activo
- **326 clases**, **~3.200 funciones/métodos**
- **13 módulos** de negocio + utils/config/base_datos
- **56 tablas**, ~30 índices
- BD real: **2,7 MB** — 1.707 tickets, 2.324 productos, 677 órdenes de producción, 370 diseños, 184 logs Shopify
- **670 commits** entre 2026-05-01 y 2026-09-14 (~4,5 meses)
- 13 ficheros de config JSON + assets (fuentes, iconos, badges, diálogos)

---

```
==================================================
19. USO DE IA / AGENTES (lo verificable)
==================================================
```

- **Verificable**: `PENDIENTES.md` documenta sesiones de trabajo iterativas con referencias a commits; los commits recientes llevan co-autoría `devin-ai-integration`. Comentarios tipo "SERVICIO DE ESCÁNER CENTRAL (Senior Architecture)", "(Fix Windows)" sugieren ciclos de diagnóstico-corrección asistidos.
- **Patrones**: la arquitectura es claramente **incremental** — módulos antiguos mezclan capas, los recientes (produccion, shopify, pedidos) siguen repository/service estricto. Consistente con refactorización progresiva.
- **No afirmable**: no se puede determinar qué líneas concretas escribió humano vs IA más allá de los commits firmados.

---

```
==================================================
20. LO MÁS DESTACABLE PARA UN PORTFOLIO
==================================================
```

Para un responsable técnico de videojuegos (donde importan sistemas, estados y robustez):

1. **Motor de producción 4D con propagación de stock** — modelado de un dominio real complejo (tipo×variante×color×talla) con efectos en cascada a tres inventarios distintos. Demuestra diseño de sistemas, no solo CRUD.
2. **Transacciones anidadas con SAVEPOINT en wrapper propio** — conocimiento real de atomicidad SQL; lo mismo que un save-system parcial en un juego.
3. **Cierre de caja atómico con snapshot inmutable** — gestión de estado financiero con integridad; comparable a persistir resultados de partida de forma consistente.
4. **Renderer ESC/POS a bytes propio** — codepages, comandos de impresora, rasterizado de imágenes: programación de bajo nivel aplicada.
5. **Sistema de fidelización completo** — economía de puntos, niveles, canje como forma de pago, badge impreso: literalmente un **sistema de progresión tipo RPG** aplicado a clientes.
6. **Integración Shopify asíncrona con auditoría** — threading, lifecycle de UI, logs persistentes, idempotencia por SKU.
7. **Migraciones autónomas al arranque** — la app se auto-repara y versiona su esquema; tolerancia a despliegues.
8. **KeyboardManager con Protocol + mixins** — abstracción de input global desacoplada (muy "game-like": input system desacoplado de escenas).
9. **Pipeline de importación CSV con validador y mapeo** — parsers, normalización, UX de corrección.
10. **Carrito con motor financiero Decimal** — impuestos multi-tasa, descuentos compuestos, vales, puntos: reglas combinables sin errores de redondeo.

---

```
==================================================
21. PREGUNTAS DIFÍCILES QUE PODRÍAN HACERTE
==================================================
```

1. **"¿Por qué SQLite y no PostgreSQL?"** → App de escritorio monopuesto, cero dependencias, backup = copiar fichero; trade-off: concurrencia limitada (sin WAL activado).
2. **"¿Cómo gestionas la concurrencia con una sola conexión compartida entre threads?"** → Punto débil real (`check_same_thread=False`, ya produjo InterfaceError). Debes conocer el problema y la alternativa (conexión por thread / pool).
3. **"¿Por qué guardas dinero como INTEGER?"** → Céntimos + Decimal evitan errores de float; `money_adapter` centraliza la conversión.
4. **"¿Qué pasa si la app se cierra a mitad de una venta?"** → Transacciones atómicas; el ticket se escribe entero o no se escribe. Vales/reposición usan ficheros JSON con recuperación.
5. **"¿Cómo haces backups y restauración?"** → Google Drive OAuth + carpeta local; restauración manual — admite que no hay restore automático verificado.
6. **"¿Por qué SHA-256 sin sal para contraseñas?"** → Respuesta honesta: suficiente para TPV local de 3 usuarios, pero conoces bcrypt/argon2 y su porqué.
7. **"¿Cómo evitarías corrupción de datos en el cierre de caja?"** → Transacción única + snapshot de líneas + numeración secuencial.
8. **"¿Cómo pruebas la UI de Tkinter?"** → Tests headless reales en `tests/` (carrito_ui_headless, db_render_click) + servicios desacoplados.
9. **"¿Por qué Tkinter y no Qt/Electron?"** → Zero-dependency para un PC de tienda, PyInstaller, táctil con chips grandes; coste: UI menos moderna.
10. **"¿Cómo escalaría esto a 5 tiendas?"** → Requeriría servidor central/BD cliente-servidor, sync de stock distribuida; la arquitectura por capas lo permite pero no está hecho.
11. **"¿Qué ocurre si Shopify está caído durante una producción?"** → Sync asíncrono con log de errores persistente y reintento manual desde la pestaña LOGS.
12. **"¿Por qué hay `modulos/config` y `modulos/configuracion`?"** → Deuda de refactors incrementales — honestidad ante la deuda técnica.

---

```
==================================================
22. RESUMEN FINAL
==================================================
```

**A) En 5 líneas**: Kool TPV es un punto de venta de escritorio en Python/Tkinter para una tienda que vende merchandising comprado **y** productos fabricados en taller propio. Integra ventas multi-pago, inventario dual (producto + matriz de producción), fidelización con niveles, pedidos de cliente, cierres de caja atómicos, impresión térmica ESC/POS y sincronización de stock con Shopify — ~94.000 líneas, 56 tablas, en producción real.

**B) 10 funcionalidades clave**:
1. Venta con pagos mixtos/vales/puntos
2. Motor de producción taller→TPV
3. Sync Shopify en tiempo real con auditoría
4. Cierre de caja atómico
5. Importador CSV de albaranes
6. Fidelización con niveles y badges impresos
7. Devoluciones con vales y reposición de stock
8. Pedidos de cliente con estados
9. Informes con exportación PDF/CSV
10. Escáner global con alta rápida de productos

**C) 5 decisiones técnicas interesantes**: transacciones anidadas con SAVEPOINT; dinero en céntimos con Decimal; migraciones auto-aplicadas con saneamiento; ESC/POS a bytes propio; KeyboardManager por Protocol para uso sin ratón.

**D) 5 debilidades**: contraseñas SHA-256 sin sal y tokens en claro; conexión SQLite única multi-thread (sin WAL); vistas >1.500 líneas (god objects); sin facturación a cliente pese a esquema existente; cobertura de tests desigual (producción/shopify casi sin tests).

**E) 5 cosas a enseñar en portfolio**: el diagrama del flujo producción→stock→Shopify; el código del `transaction()` con SAVEPOINTs; el sistema de fidelización (progresión tipo RPG); el renderer ESC/POS; y el importer CSV con su validador.

**F) Descripción profesional (~130 palabras)**:

> Kool TPV es un sistema de punto de venta de escritorio en producción real, desarrollado en Python 3.14 con customtkinter y SQLite. Además del ciclo de venta completo (pagos mixtos, vales, devoluciones, cierres de caja atómicos), incorpora un motor de producción propio que gestiona la fabricación bajo demanda del taller — variantes, colores, tallas y métodos de impresión — propagando el stock automáticamente entre taller, tienda física y Shopify mediante la API GraphQL. Incluye fidelización con niveles, pedidos de cliente, importación CSV de albaranes de proveedor, impresión térmica ESC/POS a nivel de bytes, backup en Google Drive y un sistema de migraciones autónomas. ~94.000 líneas con arquitectura por capas (UI/servicio/repositorio) y suite de tests con pytest.

---

*Nota: donde algo existe en esquema pero no funciona (facturas), o existe pero es frágil (concurrencia, hashing), se ha marcado explícitamente. El resto está verificado en código y datos reales de la BD.*
