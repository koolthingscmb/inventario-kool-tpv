# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-15, rama `windows-beta` al día.)

## Estado actual
- Shopify SUBIDA separada en NUEVO y EDITAR (`SubidaBaseView` + componentes + builders sin widgets).
  Stock en subidas: `changeFromQuantity: null`.
- METACAMPOS: rejilla empaquetada (campos de 1, 2 o 4 huecos, SÍ/NO en banda); `reglamento`
  (`file_reference`) con ABRIR/NUEVO — el PDF se sube al guardar. "+ AÑADIR METACAMPO" eliminado.
- MASIVA: metacampos (texto/número/SÍ-NO, listas, familia y `list.metaobject_reference` con
  ELEGIR VALORES; nombres en pantalla, GIDs a Shopify). Modos AÑADIR/CAMBIAR/VACIAR (`[]` válido).
- NUEVO/EDITAR: imágenes en rejilla de 3 por fila (tarjeta: miniatura, nombre, alt, ✕).
- SINC lee `on_hand` (no `available`).
- FIX Windows: Colecciones de METACAMPOS ya no abre diálogos desde el hilo (`frame.after`).
  Hecho, PERO probar más en Windows. ELIMINAR esta nota solo cuando el usuario diga.

## Decisiones (y por qué)
- Metacampos en masa con `metafieldsSet` (atómico por bloque de 25); NUNCA `productSet` (borra lo
  omitido). `rich_text`/`file_reference` fuera de la masiva. Un metacampo por pulsación.
- Colecciones con API 2026-07, modelo "fuentes": `collectionUpdate` con
  `selectionsToAdd/Remove` (`collectionAddProducts`/`RemoveProducts` están deprecadas). Shopify
  rechaza el lote si algún producto ya está dentro: filtrar siempre con `inCollection`. Colección
  manual VACÍA = 0 fuentes: no se puede añadir.
- Toda colección de familia nueva lleva el borrador 'PRODUCTO FANTASMA' para tener fuente. Las
  `Family-...` por etiqueta son LEGADO: no se vacían desde la masiva.
- No se añaden exclusiones a colecciones antiguas (parche que esconde estado). Aviso al usuario.
- Familia en masa (`_aplicar_familia`): AÑADIR = solo productos sin familia; CAMBIAR = a todos.
  Orden: entrar en colección nueva -> metacampo -> salir de la antigua. En EDITAR se conservan las
  colecciones del producto para que `productSet` no las borre; el título solo se toca si el usuario
  lo edita.

## Aprendizajes
- No decir sí a todo: dar opinión profesional con pros y contras.
- Escrituras en Shopify: probar con producto en borrador y verificar con lectura antes/después.
- En EDITAR, reabrir METACAMPOS antes de actualizar recarga los valores de Shopify y pierde lo
  preparado (ya pasaba antes).

## Fuentes de datos de manga/cómics (HECHO y probado en vivo)
- Objetivo cumplido: OBTENER por ISBN/EAN exacto trae ORIGINAL (solo si es distinto
  al título, o sea romaji/original), AUTOR, AÑO, GÉNEROS (TAGS), SINOPSIS y LINK.
  NUNCA precios, costes ni PVP. Imágenes: pendiente (decidido: se DESCARGAN, no solo URL).
- **Migración 062** crea `editoriales_fuentes` (id, nombre, plataforma, url, nif,
  usuario, password) y `editoriales` (id, nombre UNIQUE, fuente_id, web_buscar,
  web_dominio); traspasa lo sembrado en `configuracion`. `editoriales.json` BORRADO.
- Capas: `editorial_repository.py` (SQL) <- `fuentes_editorial_service.py` (lógica)
  <- `ui/editoriales_ui.py`. `obtener_datos_service.py` = servicio del botón OBTENER.
  `fuentes/` = zonalibros/planeta/shopify_publico + registro (plataforma -> clase).
- Subvista EDITORIALES: un chip = una EDITORIAL, el formulario muestra SU fuente.
  Misma plataforma+url+usuario -> fuente compartida; otra url -> fuente nueva.
  Fuentes huérfanas se borran solas. PROBAR = ToastWidget, verificado por el usuario.
- EDITORIAL en crear producto = SearchableCombo estricto de la tabla `editoriales`:
  si no existe -> toast error y limpia; al guardar también bloquea (FocusOut no
  salta al pulsar GUARDAR en macOS). `cargar_producto` muestra la guardada aunque
  no esté en la tabla (opción añadida sin id -> inválida al guardar = obliga a limpiar).
- Detalles técnicos: ZonaLibros/SD = login `zonalogin.aspx` + `BuscadorArticulosResto`,
  ficha con ids `ctl00_MainContent_txt*` en Norma y SIN prefijo en SD (regex con
  prefijo opcional; `txtFormatoTapa` = `txtFormato`). Planeta = login `_csrf_token`,
  `/ajax/libros/listado/` petición MÍNIMA (más parámetros dan 500). Shopify público:
  `suggest.json` + `products/<handle>.json`. `anio` de Publicación/published_at.
- Portadas: las `imagen_url` de las 4 fuentes son PÚBLICAS (200 sin sesión); SD usa
  la CDN `imagenes.zonalibros.com`. Decidido con usuario: DESCARGAR a disco, no URL.
- Credenciales NUNCA en repo/JSON: en la fila de `editoriales_fuentes`.

## Próximos pasos (para mañana — REVISAR/CORREGIR)
- SD no da bien las sinopsis de manga -> probar las webs propias de Panini
  (panini.es) e Ivrea (editorialivrea.com) como fuente de esas editoriales.
- Mejorar tags y demografía en el resultado de las fuentes (hoy géneros crudos
  del portal; demografía no la da ninguno — valorar fuentes públicas).
- Imágenes: descargar portada a disco al pulsar OBTENER (carpeta a decidir) y
  enchufarla a la subida de Shopify (SelectorImagenes espera archivos locales).
- Botón IR del formulario: de momento no hace nada útil (abre Google); decidir uso.
- BuscarDataService queda solo en el botón BUSCAR DATA (OBTENER ya no lo usa).
- Pendiente de decidir: tests rotos, `openai` en `requirements.txt`, documentos desactualizados.
