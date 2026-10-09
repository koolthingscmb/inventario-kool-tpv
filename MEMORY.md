# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-09, commit `ea41a72` en `windows-beta`.)

## Estado actual
- Shopify SUBIDA separada en NUEVO y EDITAR: `SubidaBaseView` + `SubidaNuevoView` + `SubidaEditarView`,
  con componentes (formulario, editor de contenido IA, selector de imágenes) y builders sin widgets.
  `upload_view.py` ya no existe. Menú: SINC, NUEVO, EDITAR, MASIVA, CONFIG.
- Stock en subidas: `inventorySetQuantities` con `changeFromQuantity: null`; si falla, la pantalla avisa.
  SINC también migrado a la mutación nueva. Probado con un producto real.
- EDITAR admite productos simples (Title / Default Title) y no cambia el título si no se edita.
- METACAMPOS: casillas para listas con opciones (`ventajas`, `tutoriales`); se reenvían los metacampos
  sin definición; no se crean booleanos `false` que no existían. Probado con Clutch y una riñonera.
- GENERAR CONTENIDO en EDITAR genera para la variante que se edita.
- Tests: 72 pasan, 14 fallan, 6 no se importan (estado heredado, no causado por Shopify).

## Decisiones (y por qué)
- Refactors sin cambiar comportamiento, comparando con la versión anterior (`git show HEAD:...`):
  el usuario no tolera regresiones ni cambios sin avisar.
- Stock de subida con `changeFromQuantity: null`: el TPV es la fuente de verdad del stock.
- Reenviar los metacampos sin definición: `productSet` borra lo que no se reenvía (comprobado).
- El título en EDITAR solo se toca si el usuario lo edita: productos antiguos no llevan el sufijo `| variante`.
- Botones del menú: NUEVO y EDITAR (elegidos por el usuario). Se quitaron los campos que no aplican en cada vista.
- En EDITAR el combo de variantes lista todas las activas; en NUEVO solo las `sync_web = 1`.

## Aprendizajes y errores a evitar
- Probar escrituras en Shopify con productos en borrador. La Riñonera Star wars quedó con el título
  cambiado y sin 2 metacampos de Google antes de arreglarlo (el usuario lo dio por bueno).
- Un `Actualizado OK` no significa que el stock se aplicara: mirar `stock_ok`.
- Mis scripts de `/tmp` desaparecen al reiniciar el Mac: recréalos y di que son temporales.
- El usuario pide explicaciones simples y con ejemplos reales; no te quedes en jerga técnica.

## Próximos pasos
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
