# AGENTS.md — Kool TPV
TPV de escritorio (Python/Tkinter) para la tienda Kool Things / Kool Dreams (Cambrils). Gestiona ventas,
almacén, producción propia (camisetas, láminas...), clientes y fidelización, informes, impresión de
tickets y sincronización con Shopify. Objetivo: reflejar con fidelidad lo que pasa en la tienda, sin
repetir trabajo a mano y sin acciones destructivas ni sorpresas.

## Stack y estructura
- Python 3.14.2 (`.venv`), customtkinter 5.2.2 sobre Tkinter, SQLite, reportlab, Pillow, python-barcode,
  requests, Google Drive API. `pywin32` solo en Windows (impresora térmica). Se desarrolla y valida en
  macOS y se despliega en Windows.
- Rama de trabajo: `windows-beta` (733 commits por delante de `main`). Remoto: GitHub `koolthingscmb/inventario-kool-tpv`.
- `main.py`: ventana `App`, menú lateral y pila de "power handlers" (Esc / botón power).
- `kool_tpv/paths.py`: todas las rutas (desarrollo y PyInstaller). No construyas rutas a mano.
- `kool_tpv/base_datos/`: wrapper SQLite, `db_init.py` (migraciones al arrancar), `money_adapter.py`.
  Varios `*_service.py` de aquí son en realidad repositorios (deuda conocida).
- `kool_tpv/modulos/<módulo>/`: tpv, almacen, produccion, shopify, clientes, informes, impresion,
  ticket, fidelizacion, presencia, descuento. `config/` y `configuracion/` coexisten (deuda).
- `kool_tpv/utils/`: widgets, diálogos, `ButtonFactory`, `BaseModuleView`, `KeyboardManager`, `BarcodeService`.
- `kool_tpv/config/*.json`: colores, fuentes, layout y menús. `buttons_menu.json` define los botones laterales.
- Shopify (`modulos/shopify`): `services/` (producto, sync, metacampos, IA, fuentes de datos, builders
  sin widgets) y `ui/` (`subida/` con base + NUEVO + EDITAR + componentes, `tabs/` de CONFIG).
- Ignorar: `_mantenimiento/`, `backups/`, `tools/` (scripts puntuales), `.venv/`.

## Comandos
- Ejecutar: `.venv/bin/python main.py`
- Comprobar que un archivo compila: `.venv/bin/python -m py_compile <archivo.py>`
- Tests: `.venv/bin/python -m pytest -q --continue-on-collection-errors`
  Estado de partida (9-oct-2026): 72 pasan, 14 fallan y 6 no se pueden importar. NO está en verde:
  compara contra esa base y no "arregles" tests ajenos sin preguntar.
- No hay linter configurado ni CI. Empaquetado: `kool_tpv.spec` (PyInstaller, no verificado).
- Consultar la BD sin riesgo: `sqlite3` en modo solo lectura (`file:...?mode=ro`, `uri=True`).
- macOS no trae `timeout` ni `grep -P`: no los uses en comandos.

## Convenciones
- Todo en español: textos de interfaz (botones en MAYÚSCULAS), comentarios, docstrings, logs y commits.
- Indentación: 4 espacios, pero ~41 archivos (sobre todo de `produccion`) usan TABULADORES. Respeta la del archivo.
- Capas: UI -> Service -> Repository -> Database. La lógica no va en la UI. Referencias de buen patrón:
  `modulos/produccion/` y `shopify/services/shopify_nuevo_builder.py` / `shopify_edicion_builder.py`
  (preparan datos sin conocer widgets).
- Vistas de módulo heredan `BaseModuleView`. Los botones laterales se enlazan por texto desde
  `buttons_menu.json` a métodos `show_*`. Las subvistas usan `on_volver` y `actualizar_ruta` (migas de pan).
- Colores y fuentes: `load_colors('<módulo>')` y los JSON de `config/`.
- Avisos: toasts con `utils/widgets/notificaciones` (`show_error(parent, mensaje)`) y diálogos modales con
  `utils/dialogs/helpers` (`show_error(parent, titulo, mensaje)`). Firmas distintas: no mezclar.
- Logs con `logging.getLogger(__name__)`; no usar `print`.
- Hilos: el trabajo va en un hilo y la UI se actualiza con `frame.after(0, ...)`. Nunca tocar widgets desde el hilo.
- Dinero: céntimos enteros en BD, `Decimal` en lógica, conversión solo con `prepare_for_db` / `read_from_db`.
  Nunca `float`.
- Commits: `Módulo: frase en español acabada en punto.` + trailer de Devin. Un tema por commit.

## Reglas de dominio / trampas conocidas
- Única BD válida: `kool_tpv/base_datos/kool_bd.db` (datos reales de la tienda, gitignored).
- `requirements.txt` incluye `openai==3.11.0`, que no está instalado en el entorno y el código no importa.
- Migraciones: se aplican solas al arrancar. Las `.sql` llegan a la 041; de la 042 en adelante van dentro
  de `db_init.py`, con comprobación idempotente y log "Migración NNN". Mira la última antes de numerar.
- Stock dual: `productos.stock_actual` (producto del TPV) y `produccion_stock_colores_tallas` (matriz del
  taller: tipo × variante × color × talla). Fabricar consume stock base, suma stock de diseño y puede
  actualizar el producto TPV vinculado. Esos cambios de stock disparan sync a Shopify solo si
  `tipos_variantes.sync_web = 1` y `shopify_sync_active` está activo.
- El teclado es global: `KeyboardManager` captura las flechas y `BarcodeService` el escáner. Los campos
  de texto nuevos deben convivir con ambos.
- Windows: `pywin32` condicional, `duckduckgo` con import perezoso, `state('zoomed')` con alternativa.
- Shopify (aprendido con pruebas reales):
  - `productSet` define el ESTADO COMPLETO de las listas: variantes y metacampos que no se reenvían, se BORRAN.
  - Producto simple (variante única) se envía con opción `Title` / valor `Default Title`, con esa grafía exacta.
  - Stock: mutación `inventorySetQuantities` (`name: on_hand`). En SUBIDA, `changeFromQuantity: null`
    (el TPV es la fuente de verdad); en SINC se envía la cantidad actual leída. `product_set` devuelve
    `stock_ok` y la pantalla debe avisar si el stock falla. `inventorySetOnHandQuantities` está obsoleta.
  - "Sorpresa": color de Camiseta, sin control de inventario (`tracked=False`), nunca se le fija stock.
  - Metacampos: la pantalla solo muestra los de `custom` con definición. El resto (Google `mc-facebook`,
    `mm-google-shopping`, `custom.mecanicas`...) se reenvía tal cual. `global.title_tag/description_tag`
    van por el campo SEO. Un booleano o lista sin valor y sin marcar no se envía.
  - EDITAR no reconstruye el título (`base | variante`) salvo que el usuario lo edite.
  - Variantes: en NUEVO solo las `sync_web = 1`; en EDITAR, todas las activas del tipo.
  - Credenciales en la tabla `configuracion` (`shopify_*`), en claro. Versión de API por defecto 2026-07
    (editable en CONFIG -> GENERAL).
- Contenido de marca y SEO: fuente única `KOOLTHINGSHOP.md`. No inventar datos; los diseños propios son
  Fan Art dibujado a mano, prohibido decir o usar IA en ellos.
- Documentos desactualizados: `PENDIENTES.md` (el punto 5 de `changeFromQuantity` ya está resuelto),
  `AUDITORÍA TÉCNICA sept26` (cita la mutación vieja) y `kool_tpv/README.md` (cita `scripts/` y la rama `main`).

## Forma de trabajar
- Explica el cambio ANTES de hacerlo y espera la aprobación. No tomes decisiones por el usuario.
- Cambios pequeños, uno por vez; espera su prueba antes de seguir.
- Refactor = mismo comportamiento: captura la salida del código actual, mueve la lógica y compara.
- Al terminar di: qué hiciste, cómo lo comprobaste, qué NO pudiste comprobar y qué debe probar el usuario.
- Respuestas en español, cortas y sin jerga; si pide algo "más simple", usa un ejemplo real.
- Scripts de prueba temporales en `/tmp` y di que son temporales. No crees archivos raros en el repo.

## Memoria
- Al empezar, lee `MEMORY.md` para conocer el estado del proyecto y las decisiones tomadas.
- Al terminar una tarea, actualízalo: estado actual, decisiones importantes (con su porqué) y errores a evitar.
- Mantenlo breve (máximo ~50 líneas): resume o elimina lo que ya no aporte.
- Si algo se convierte en una regla permanente, propón moverlo a `AGENTS.md` en lugar de dejarlo en la memoria.
- No guardes nunca datos sensibles (claves, tokens, datos personales).

## Límites
- ✅ Siempre: leer antes de editar, respetar la indentación y los nombres del archivo, compilar lo tocado,
  probar con datos simulados, diagnosticar con consultas de SOLO LECTURA (BD y Shopify).
- ⚠ Pregunta antes: crear archivos, añadir dependencias, migraciones o cambios de esquema, cambiar
  formatos de datos, mover o borrar código, cambiar comportamiento visible, cualquier escritura en Shopify
  (aunque sea un borrador), hacer commit o push.
- 🚫 Nunca: escribir o borrar en la BD real sin permiso explícito, borrados o escrituras masivas en
  Shopify, imprimir o subir tokens y `client_secrets.json`, `git push --force` o reescribir historia,
  tocar `.gitignore` o controles de seguridad para esquivar un fallo, tocar `_mantenimiento/` o `backups/`,
  reintroducir `upload_view.py`.

## Verificación
- `py_compile` de cada archivo tocado y tests relacionados (comparando con la base de arriba).
- Cambios de Shopify: simular `_graphql`, comparar lo que se envía con la versión anterior (`git show HEAD:<ruta>`)
  y, tras la prueba real del usuario, comprobar con una consulta de lectura "antes y después".
- UI Tkinter: no hay tests de UI para Shopify. Se comprueba estructura con un script temporal y se pide la
  prueba al usuario. Di siempre que el aspecto pintado no se ha visto.
