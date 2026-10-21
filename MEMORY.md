# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-20, rama `windows-beta`.)

## Estado actual (Shopify)
- SUBIDA separada en NUEVO y EDITAR (`SubidaBaseView` + componentes + builders sin widgets).
  Stock en subidas: `changeFromQuantity: null`. SINC lee `on_hand` (no `available`).
- METACAMPOS: rejilla empaquetada; `reglamento` (`file_reference`) con ABRIR/NUEVO (el PDF
  se sube al guardar). MASIVA: texto/número/SÍ-NO, listas, familia y `list.metaobject_reference`
  con ELEGIR VALORES; modos AÑADIR/CAMBIAR/VACIAR (`[]` válido).
- NUEVO/EDITAR: imágenes en rejilla de 3 por fila.
- FIX Windows: Colecciones de METACAMPOS ya no abre diálogos desde el hilo (`frame.after`).
  Hecho, PERO probar más en Windows. ELIMINAR esta nota solo cuando el usuario diga.

## Decisiones Shopify (y por qué)
- Metacampos en masa con `metafieldsSet` (bloques de 25); NUNCA `productSet` (borra lo omitido).
  `rich_text`/`file_reference` fuera de la masiva.
- Colecciones (API 2026-07): `collectionUpdate` con `selectionsToAdd/Remove`; filtrar siempre con
  `inCollection`. Colección manual VACÍA = 0 fuentes. Toda colección de familia nueva lleva el
  borrador 'PRODUCTO FANTASMA'; las `Family-...` por etiqueta son LEGADO. Sin exclusiones parche.
- Familia en masa: AÑADIR = solo productos sin familia; CAMBIAR = a todos. Orden: entrar en la nueva
  -> metacampo -> salir de la antigua. En EDITAR se conservan las colecciones del producto.

## Aprendizajes
- No decir sí a todo: opinión profesional con pros y contras. Preguntar antes de cambiar nada.
- Escrituras en Shopify: probar con borrador y verificar con lectura antes/después.
- En EDITAR, reabrir METACAMPOS antes de actualizar recarga y pierde lo preparado.
- Un dato mal configurado se corrige en su sitio, nunca con parche en el código (sin hardcodeo).
- Con el usuario enfadado: frases cortas, sin nombres de tablas; reproducir antes de explicar.

## Fuentes de datos de producto (OBTENER) — CERRADO el 2026-10-20
- Capas: `editorial_repository` (SQL) <- `fuentes_editorial_service` <- `ui/editoriales_ui`;
  `obtener_datos_service` (botón OBTENER) + `fuentes/registro.py` (plataforma -> clase) +
  `PortadasService` (`assets/portadas/<ean>.jpg`, `_2`...; carpeta se crea sola; no va en git).
- Tablas: `editoriales_fuentes` (plataforma, url, nif, usuario, password) y `editoriales`
  (fuente_id, `fuente_reserva_id` [mig. 063], `web_buscar`, `web_dominio`). OBTENER prueba la
  fuente principal y luego la RESERVA. Con plataforma `web` la URL va a `web_buscar` y IR la abre.
- Reglas: nunca precios/PVP; TAGS vacíos; LINK multi `url (etiqueta); url2 (etiqueta2)` (IR elige);
  credenciales solo en `editoriales_fuentes`, NUNCA en repo, chat ni logs.
- Plataformas: zonalibros (Norma, demografía de 'Materia'), planeta, shopify (Milky Way: autor y
  demografía de tags, avance), panini_web, ivrea_web (sitemap), udl_web (La Cúpula), astiberri_web
  (slug+EAN, imágenes `blobs`), arechi_web (sitemap+API, ceros a la izquierda ignorados),
  azeta_web (portal de cliente, por EAN). `azeta_web` será la RESERVA de casi todo.
- Sin fuente propia, van con `azeta_web` (config, sin código): Penguin/Distrito Manga, Kibook,
  Mangaline, Devir, Yermo, Nuevo Nueve, Dolmen, Grafito y los manga menores. No volver a investigar.
- Portadas máximas: Astiberri ~2400 px, Milky Way ~1030, Panini ~856, UDL ~800, Azeta ~650, Arechi
  ~624, Ivrea 400, Planeta 300, Norma 229. Google recomienda ~800: ampliar a mano en los más vendidos.
- Frágil: panini.es solo deja pasar con UA Googlebot (Queue-it); Azeta acepta el login sin token
  reCAPTCHA hoy; Ivrea limita su buscador AJAX por IP (por eso usa el sitemap).

## Pendiente
- Prueba del usuario en la app: `azeta_web`, `arechi_web` y EDITORIALES (RESERVA y URL con `web`).
- Idea NO pedida: avisar cuando la portada descargada sea pequeña (<800 px).
- HECHO y probado: ◀ ANTERIOR / SIGUIENTE ▶ en la ficha (recorren la lista de la búsqueda; con
  cambios preguntan "¿Guardar y pasar?"). `_busqueda_ids` + `show_crear(apilar=False)`; sin atajos
  de teclado (las flechas son globales).
- DEUDA (no urgente): `crear_producto_ui.py` (1586 líneas) hace SQL directo en
  `_load_db_options` (categorias, tipos, proveedores, tipo_iva) saltándose los repositorios;
  `__init__` 419 líneas y `_on_save` 225. Refactor = mismo comportamiento, por partes,
  empezando por mover esas 4 consultas a repositorios. No hacerlo junto a otra función.
- Botón IR del formulario: decidir uso. `web_dominio` ya no se edita desde la pantalla.
- Decidir: tests rotos, `openai` en `requirements.txt`, documentos desactualizados.
- HECHO y probado: METACAMPOS de cómic. Columna `productos.metacampos` (JSON, mig. 064) guarda
  NOMBRES (no GIDs). UN botón METACAMPOS baja las 4 listas en vivo (`MetacamposComicService`,
  delega en `ShopifyMetafieldsService`) y abre UN diálogo agrupado (`show_metacampos_agrupados_
  dialog`; demografía una sola vía `familias_unicas`). El diálogo compartido quedó sin buscador y
  con 4 columnas para TODOS los usos (mecánicas, colecciones igual). El sistema reparte lo elegido
  a 4 campos readonly. DEMOG viejo fuera; su valor se rescata de `datos_tecnicos` al cargar.
  Shopify es el amo de las listas. Zona Shopify rediseñada (rejilla 15 cols + fila metacampos con
  pack), color del módulo en campos/botones/cabecera con línea, SHOPIFY TIPO, SEO_DESC+DESC en una
  fila. Tras GUARDAR el producto se queda cargado (antes se vaciaba); no duplica.
- EN CURSO: OBTENER autorrellena metacampos. `ComparadorMetacamposService` (almacen) coteja
  `candidatos_meta` de cada fuente (categorías/tags/materia, NUNCA la sinopsis) contra las
  listas de Shopify + `config/metacampos_alias.json` (variante editorial -> valor oficial).
  Hecho: comparador + alias + candidatos en las 9 fuentes. Falta: enganchar en OBTENER
  (rellenar solo metacampos vacíos) y probar. PETICIÓN: UI pequeña en Shopify CONFIG para
  editar `metacampos_alias.json` (añadir/modificar equivalencias).
- PRÓXIMOS PASOS (orden acordado 2026-10-20, uno por vez, con aprobación):
  1.5) PENDIENTE DECISIÓN: géneros de OBTENER -> GÉNERO por nombre (hoy siguen yendo a TAGS).
  2) GENERAR SEO sustituye a BUSCAR DATA (rellena título web, SEO y descripción; no guarda). Hoy NO
     se genera SEO: el prompt `manga_seo` (tabla `shopify_prompts`) pide 9 variables y
     `OpenAIService.generate_seo` solo da 2 -> KeyError; `SEO_RULES.md` no existe (la fuente única es
     `KOOLTHINGSHOP.md`); el prompt contradice KOOLTHINGSHOP (título SEO, orden del HTML, cierre,
     tag "Manga"); deja a la IA inventar género/demografía; `web_search_service` usa `print`.
  3) SUBIR / ACTUALIZAR EN SHOPIFY desde la ficha (un botón que sustituye a SINCRONIZAR, hoy vacío).
     `shopify_product_mapping` está VACÍA: antes de crear, buscar por SKU/código de barras para no
     duplicar. Toda escritura en Shopify (aunque sea borrador) se pregunta antes.
  4) Limpieza: `BuscarDataService` y fuentes viejas, `_auto_fill_shopify_data` (código muerto).
