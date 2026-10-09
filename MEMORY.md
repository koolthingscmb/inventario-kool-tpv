# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-09, commit `e85db72` en `windows-beta`.)

## Estado actual
- Shopify SUBIDA separada en NUEVO y EDITAR: `SubidaBaseView` + `SubidaNuevoView` + `SubidaEditarView`,
  con componentes (formulario, editor de contenido IA, selector de imágenes) y builders sin widgets.
- Stock en subidas: `inventorySetQuantities` con `changeFromQuantity: null`; si falla, la pantalla avisa.
- METACAMPOS: casillas para opciones; reenvío de campos sin definición; selector de Colecciones real
  en grid de 3 columnas con buscador y sincronización automática con el campo oficial de colecciones.
- GENERAR CONTENIDO en EDITAR genera para la variante que se edita.

## Decisiones (y por qué)
- Refactors sin cambiar comportamiento, comparando con la versión anterior (`git show HEAD:...`).
- Doble envío de Colecciones: el metacampo `coleccion_de_familia` se sincroniza con `collections` de
  Shopify para que el producto aparezca físicamente en la colección y no solo como una nota.
- Selector general: `ShopifyReferenceSelectDialog` (evolución del de Mecánicas) ahora es genérico,
  usa grid de 3 columnas para aprovechar el ancho y tiene buscador para rapidez.
- En EDITAR se conservan las colecciones existentes del producto para que `productSet` no las borre.
- El título en EDITAR solo se toca si el usuario lo edita.
- Botones del menú: NUEVO y EDITAR (elegidos por el usuario).

## Aprendizajes y errores a evitar
- **NUNCA borrar o deshacer código sin permiso**, aunque creas que has cometido un error de proceso.
- Probar escrituras en Shopify con productos en borrador. La Riñonera Star wars quedó con el título
  cambiado y sin 2 metacampos de Google antes de arreglarlo (el usuario lo dio por bueno).
- Un `Actualizado OK` no significa que el stock se aplicara: mirar `stock_ok`.
- Mis scripts de `/tmp` desaparecen al reiniciar el Mac: recréalos y di que son temporales.
- El usuario pide explicaciones simples y con ejemplos reales; no te quedes en jerga técnica.

## Próximos pasos
- Shopify EDITAR MASIVA: implementar cambio masivo de `coleccion_de_familia`, limpiar UI (quitar
  elementos no usados) y revisar ancho de columnas.
- METACAMPOS: texto enriquecido (`componentes`) sin JSON crudo; archivos (`reglamento`) con nombre en vez
  del identificador; alinear cabecera y columnas del grid y dar fila propia al texto largo; no perder lo
  escrito al pulsar "+ AÑADIR METACAMPO"; limpiar código sobrante.
- NUEVO/EDITAR: zona de imágenes en rejilla (miniatura, nombre, X; 2 por fila) para evitar scroll hasta el SEO.
- Validar subida NUEVO con precios por variante y productos sin talla/color. Revisar el prompt GENERAR
  TAGS (mala calidad); idea: pasarle los tags que ya existen en Shopify para que los reutilice.
- Probar en Windows la UI de Tipos y la migración 054; revisar la UI de Tipos/Categorías
  (`shopify_taxonomy` queda obsoleto: se usa `categoria_id`).
- Botón SINOPSIS junto a la descripción (fuente nueva `WhakoomSource`, por ISBN, sinopsis oficiales en
  español por tomo) y gestión de imágenes de producto (`imagen_url`, portadas en alta, fase 4).
- Pendiente de decidir: tests rotos, `openai` en `requirements.txt` y documentos desactualizados
  (auditoría, README).
- Opcional: pasada 2 del refactor (métodos de los componentes en lugar de acceso directo a widgets).
