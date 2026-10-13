# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-13, commits `6521ccd`..`88e0b3a` en `windows-beta`.)

## Estado actual
- Shopify SUBIDA separada en NUEVO y EDITAR (`SubidaBaseView` + `SubidaNuevoView` + `SubidaEditarView`,
  con componentes y builders sin widgets). Stock en subidas: `changeFromQuantity: null`.
- METACAMPOS: casillas para opciones; reenvío de campos sin definición; selector de Colecciones real
  con buscador; `rich_text` se muestra como texto y solo se reenvuelve a JSON si se edita.
- METACAMPOS archivo (`133d9a8`): `reglamento` (`file_reference`) muestra nombre, tipo y tamaño
  (`describir_archivo`) con botones ABRIR y NUEVO (se quitaron QUITAR/DESHACER: molestaban en el grid).
  NUEVO guarda la ruta (`archivo_local`); `product_set` sube el PDF al guardar el producto
  (`subir_archivo`: stagedUploadsCreate FILE + fileCreate APPEND_UUID + espera READY) y lo sustituye por
  su GID; una sola subida por lote (se actualiza el mismo dict). Probado por el usuario: la pantalla y
  la subida real en NUEVO (3 productos, OK). Sin probar: cambiar el PDF en EDITAR. Quitar un PDF: desde
  el admin; deshacer una elección: VOLVER sin aceptar. Botón "+ AÑADIR METACAMPO" ELIMINADO.
- METACAMPOS grid (`88e0b3a`): secciones unidas en mayúsculas (`GENERAL` + `General`); cada campo ocupa
  1, 2 o 4 huecos (texto/número, texto largo, listas-archivo-referencias), empaquetados sin huecos
  vacíos; SÍ/NO en una banda al final de su sección; textos largos con altura de una línea que crece
  sola (~22% menos de alto). Guardar envía lo mismo que antes (comprobado con Tk).
- SINC (`6521ccd`): `sync_stock_by_sku_prefix` lee `on_hand` (antes `available`).
- FIX Windows (`60136a6`): el selector de Colecciones de METACAMPOS abría el diálogo desde un hilo
  secundario y colgaba la app. Ahora el hilo trae datos y el diálogo se abre con `frame.after`.
  Fixeado, PERO hay que probarlo más veces en Windows. ELIMINAR esta nota solo cuando el usuario diga.
- MASIVA (`0d65c31`, `15eb7a4`, `b99e6a0`, `a68c643`, `d83923e`): filtros y acciones en 3 filas (PVP,
  plantilla, metacampo), confirmación que lista los cambios. Columnas: ID, TÍTULO (elástica), TIPO,
  PLANTILLA 102, ◉ 20 (estado con iconos ● activo, ○ borrador, ✕ archivado), €€ 60 y RESULTADO 380 (une
  precio nuevo, plantilla y metacampo; "OK" tras guardar). Dos pasos visibles: botón
  "1) PULSAR PARA PREPARAR LOS CAMBIOS" (color Accent) y "2) ACTUALIZAR EN SHOPIFY", que está en gris
  hasta que hay cambios preparados (`_actualizar_estado_guardar`).
  Metacampos: texto/número/URL/SÍ-NO; listas con opciones; familia (`coleccion_de_familia`).
  Modos AÑADIR/CAMBIAR/VACIAR como botones de opción (grises si el tipo no los usa; VACIAR solo en
  listas, `6c75d4f`: escribe `[]`, Shopify lo acepta y deja el metacampo con lista vacía; salta los que ya
  estaban vacíos). Probado con escritura real en los Clutch.
- Familia en masa (`_aplicar_familia`): AÑADIR = solo productos sin familia; CAMBIAR = a todos.
  Orden: entrar en colección nueva -> metacampo -> salir de la antigua. Probado con Trinidad y colecciones
  `PRUEBA_*`. La tabla (`VirtualNavList`, compartida) solo colorea por FILA, no por columna.

## Decisiones (y por qué)
- Metacampos en masa con `metafieldsSet` (atómico por bloque de 25); NUNCA `productSet` (borra lo omitido).
  `rich_text`/`file_reference` fuera. Un metacampo por pulsación. Listas vacías NO permitidas.
- Colecciones con API 2026-07: modelo de "fuentes". Añadir/quitar = `collectionUpdate` con
  `sourcesToUpdate[].condition.inclusion.selectionsToAdd/Remove` (las órdenes `collectionAddProducts`/
  `RemoveProducts` están deprecadas). Shopify rechaza el lote entero si algún producto ya está dentro:
  siempre filtrar con `inCollection`. Colección manual VACÍA = 0 fuentes: no se puede añadir.
- Convención del usuario: toda colección de familia nueva lleva siempre el producto en borrador
  'PRODUCTO FANTASMA' para que tenga fuente. Las colecciones `Family-...` por etiqueta son LEGADO
  (migrando al metacampo): no se pueden vaciar desde la masiva; la limpieza se hace aparte en Shopify.
- No se añaden exclusiones a colecciones antiguas (parche que esconde estado). Aviso al usuario.
- Doble envío en EDITAR: `coleccion_de_familia` también mete el producto en la colección. Se conservan
  las colecciones existentes del producto para que `productSet` no las borre.
- El título en EDITAR solo se toca si el usuario lo edita.

## Aprendizajes y errores a evitar
- **NUNCA borrar/deshacer código ni editar sin un "aplica" explícito**; explicar no es permiso.
- **Leer MEMORY.md y AGENTS.md al empezar CADA sesión.**
- **Respuestas CORTAS, una cosa cada vez, sin jerga.** El usuario se pierde con mensajes largos.
- **No decir sí a todo:** dar opinión profesional con pros y contras; el usuario lo pidió.
- Tkinter: nunca abrir diálogos ni tocar widgets desde un hilo; usar `frame.after(0, ...)`.
- Shopify: `on_hand` = físico; `available` = on_hand − comprometido. Un fallo no anula el lote.
- Probar escrituras con productos en borrador y verificar con lectura "antes y después" (solo lectura:
  BD abierta `mode=ro` y `execute_query` anulado, para no escribir ni el token temporal).
- Mis scripts de `/tmp` desaparecen al reiniciar: recréalos y di que son temporales.

## Próximos pasos
- MASIVA: referencias a metaobjetos (`mecanicas_...`). Mirar pintado en Windows: filas 2 y 3 enteras
  (ahora con 3 botones de opción) e iconos de estado (●, ○, ✕).
- METACAMPOS resto: limpiar código sobrante. En EDITAR,
  reabrir METACAMPOS antes de actualizar recarga los valores de Shopify (pierde lo preparado: ya pasaba).
  Los metacampos nuevos se crean como definición en el admin de Shopify.
- NUEVO/EDITAR: imágenes en rejilla (2 por fila); validar NUEVO con precios por variante y sin talla/color;
  prompt GENERAR TAGS con los tags existentes. Comprobar si el doble envío de EDITAR funciona con
  colecciones por regla.
- Probar en Windows la UI de Tipos y la migración 054; revisar Tipos/Categorías (`shopify_taxonomy`
  obsoleto: se usa `categoria_id`). Botón SINOPSIS (`WhakoomSource`) e imágenes de producto.
- Pendiente de decidir: tests rotos, `openai` en `requirements.txt`, documentos desactualizados.
