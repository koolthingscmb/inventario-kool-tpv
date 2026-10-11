# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-11, commits `6521ccd`..`15eb7a4` en `windows-beta`.)

## Estado actual
- Shopify SUBIDA separada en NUEVO y EDITAR: `SubidaBaseView` + `SubidaNuevoView` + `SubidaEditarView`,
  con componentes (formulario, editor de contenido IA, selector de imágenes) y builders sin widgets.
- Stock en subidas: `inventorySetQuantities` con `changeFromQuantity: null`; si falla, la pantalla avisa.
- METACAMPOS: casillas para opciones; reenvío de campos sin definición; selector de Colecciones real
  en grid de 3 columnas con buscador y sincronización automática con el campo oficial de colecciones.
- GENERAR CONTENIDO en EDITAR genera para la variante que se edita.
- SINC (`6521ccd`): `sync_stock_by_sku_prefix` lee `on_hand` (antes `available`); los pedidos web
  sin enviar rompían la comprobación (`shopify_sync_service.py`). Probado con camisetas Marino.
- MASIVA UI (`0d65c31`): imports muertos fuera, TÍTULO elástico, botón único APLICAR (PVP y/o
  plantilla según lo rellenado), sin redondeo, filtros y acciones en 2 filas sobre fondo gris.
- METACAMPOS `rich_text` (`a3cd0ad`): muestra texto legible y reenvuelve a JSON solo si se edita
  (`_rich_to_text`/`_text_to_rich`). Probado editando `componentes` de Clutch en Shopify.
- MASIVA METACAMPOS (`15eb7a4`), pasos 1-3 del plan: fila 3 con combo de metacampos `custom`, valor por
  tipo (texto, número, URL, SÍ/NO; `TIPOS_MASIVOS` y `validar_valor_masivo` en el servicio de
  metacampos), columna META, envío con `metafieldsSet` en bloques de 25 dentro de
  `actualizar_productos_lote`. Confirmación con `show_warning(confirm=True)` listando los cambios.
  Probado por el usuario con una escritura real. NO visto aún: el texto ampliado del diálogo.

## Decisiones (y por qué)
- Refactors sin cambiar comportamiento, comparando con la versión anterior (`git show HEAD:...`).
- Doble envío de Colecciones: el metacampo `coleccion_de_familia` se sincroniza con `collections` de
  Shopify para que el producto aparezca físicamente en la colección y no solo como una nota.
- En EDITAR se conservan las colecciones existentes del producto para que `productSet` no las borre.
- Edición masiva de metacampos: `metafieldsSet` (atómico por bloque; NO `productSet`, que borra lo
  omitido). `rich_text`/`file_reference` fuera. Solo un metacampo por pulsación de APLICAR.
- Listas con opciones (`ventajas`...): selector AÑADIR/SUSTITUIR, por defecto AÑADIR (conserva lo que
  tenga cada producto; hay que traer los metacampos en la búsqueda de MASIVA). Aprobado por el usuario.
- El título en EDITAR solo se toca si el usuario lo edita.
- `rich_text` sin negritas/listas: si el usuario lo edita en el TPV se guarda como texto plano.

## Aprendizajes y errores a evitar
- **NUNCA borrar o deshacer código sin permiso**, aunque creas que has cometido un error de proceso.
- **NUNCA editar código sin un "aplica" explícito**: explicar y responder preguntas NO es permiso.
- **Leer MEMORY.md y AGENTS.md al empezar CADA sesión**, aunque la conversación venga de ayer.
- En Shopify, `on_hand` = stock físico y `available` = on_hand − pedidos sin enviar (committed).
  `changeFromQuantity` compara contra `on_hand`. Un fallo en un item NO anula el lote: el resto se aplica.
- Probar escrituras en Shopify con productos en borrador.
- Un `Actualizado OK` no significa que el stock se aplicara: mirar `stock_ok`.
- Mis scripts de `/tmp` desaparecen al reiniciar el Mac: recréalos y di que son temporales.
- El usuario pide explicaciones simples y con ejemplos reales; no te quedes en jerga técnica.

## Próximos pasos
- MASIVA metacampos: paso 4 (selectores: listas con opciones, colecciones, metaobjetos), paso 5
  (`coleccion_de_familia` con `collectionAddProducts`, conservando colecciones) y prueba real en borrador.
- METACAMPOS resto: archivos (`reglamento`) con nombre en vez del identificador; alinear cabecera y
  columnas del grid y dar fila propia al texto largo; no perder lo escrito al pulsar "+ AÑADIR
  METACAMPO"; limpiar código sobrante.
- NUEVO/EDITAR: zona de imágenes en rejilla (miniatura, nombre, X; 2 por fila).
- Validar subida NUEVO con precios por variante y productos sin talla/color. Revisar el prompt GENERAR
  TAGS (idea: pasarle los tags que ya existen en Shopify).
- Probar en Windows la UI de Tipos y la migración 054; revisar UI Tipos/Categorías
  (`shopify_taxonomy` obsoleto: se usa `categoria_id`).
- Botón SINOPSIS (`WhakoomSource`, por ISBN) y gestión de imágenes de producto (`imagen_url`, fase 4).
- Pendiente de decidir: tests rotos, `openai` en `requirements.txt`, documentos desactualizados.
- Opcional: pasada 2 del refactor (métodos de los componentes en lugar de acceso directo a widgets).
