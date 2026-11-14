# MEMORY.md — Kool TPV
Memoria entre sesiones. Actualización: 2026-11-14, rama `windows-beta`. Máximo ~50 líneas.

## Editoriales y fuentes
- UI 50/50 (editorial arriba, fuente abajo); WEB de editorial = botón IR, URL de fuente = OBTENER.
- PLATAFORMA elige el adaptador de `TIPOS_FUENTE`: fuente = config en BD, adaptador = código.
- Mac y Windows tienen fuentes/accesos propios en BD: `git pull` no los copia.

## Shopify
- SUBIDA NUEVO/EDITAR con builders sin widgets. Stock: subida `changeFromQuantity: null`; SINC `on_hand`.
- Masiva: `metafieldsSet` en bloques de 25, nunca `productSet` (borra omitidos); excluye
  rich_text/file_reference; modos AÑADIR/CAMBIAR/QUITAR. Varios metacampos por producto
  (`_mf_lista`, repetir uno lo reemplaza) y franja CAMBIOS PREPARADOS con ✕ por cambio.
  QUITAR en valor único/escalar = `metafieldsDelete` (lee antes; sin valor = omitido); en listas
  sigue escribiendo `[]`; familia no tiene QUITAR. Columna VALOR ACTUAL (solo lectura, hilo con
  token anti-resultados antiguos): `leer_valores_metacampo`; '—' sin valor, '?' no leído;
  `VirtualNavList.refresh()` repinta sin perder selección.
- Colecciones API 2026-07: `collectionUpdate` selectionsToAdd/Remove + `inCollection`.
  Familia masiva: entrar nueva -> metacampo -> salir antigua; AÑADIR solo si no tenía.
- Rebaja ficha (migr. 069): % en centésimas, NULL = sin configurar; `price` = final,
  `compareAtPrice` = base; UPDATE con COALESCE (otros flujos no pisan).
- Espejo cómic en EDICIÓN MASIVA almacén: 4 claves de GRUPOS, ausente = borrar, ajenas conservadas.
- Label estado web: EN LA WEB/NO SUBIDO/CAMBIOS PENDIENTES, solo lectura de BD.
- IA: OpenAIService sirve OpenAI y Gemini (endpoint compatible); chips CONFIG IA por proveedor,
  claves Gemini A-E en `shopify_ia_gemini_api_keys` con rotación y fallback; modelo por defecto
  gemini-3.6-flash; fallos SEO en shopify_sync_log (acción SEO_IA).

## Metaobjetos (`kool_tpv/METAOBJETOS-API.md`)
- METACAMPOS y masiva admiten metaobject_reference único además de listas; secciones en 2 columnas.
- Stock sync genérico por `productos`+`shopify_product_mapping` (lo crea la ficha; NUEVO producción no).
- `ficha_juego` HECHO: crear/actualizar metaobjeto por producto + formulario vivo desde
  fieldDefinitions (`ficha_juego_dialog.py`). OBTENER autorellena jugadores/edad/tiempo en 'juego'.
- `metacampos_grupo` por tipo (migr. 070-071, una sola vez): 'comic'/'juego'/NULL en `tipos`,
  selector en CONFIG->TIPOS. Ficha muestra los 4 campos del grupo; METACAMPOS_PROPIOS cubre las 8.
- `familia` (único, `81dd8ca`): botón FAMILIA en la ficha (todos los tipos); en METACAMPOS_PROPIOS
  -> subir sin familia BORRA la de Shopify. Colecciones de familia automáticas.
- Fuentes juegos: `sdgames_web` (pública por nombre), `devir_web` (login Magento, por EAN).
  Asmodee pendiente (Akamai 403; b2b.asmodee.es o navegador real).

## Reglas y fuentes OBTENER
- Mac = pruebas, Windows = tienda; enlaces Shopify son locales por BD.
- Stock por `StockMovementService.aplicar_movimiento` en transacción; cola durable tras confirmar.
- Vales = pago; OBTENER: géneros a METACAMPOS (no TAGS), nunca PVP.
  LINK multi `url (etiqueta); ...`; avance_comic solo con etiqueta Avance.
- `shopify_publico` (Milky Way): suggest.json trae la ficha; página extra tolerante a 429.
  Pendiente evaluar Azeta como principal de Milky Way (reserva hoy solo si falla).
- Astiberri por EAN (/search XHR aprobado pese a Disallow); sin adaptador propio -> Azeta.
- La Cúpula (`lacupula_web`, `102fe87`): web pública WooCommerce por nombre (ISBN no indexado);
  API store para ficha, HTML para autor (/autores/) y avance calameo. Verifica EAN por el SKU.
- Planeta (`758b158`): sinopsis completa del script `#full-synopsis`, no del div resumen.
  UI EQUIVALENCIAS = nombre oficial -> palabras por comas (ej. `manga shonen` bajo Shonen).
- Fragilidad: Panini Queue-it, Azeta reCAPTCHA, Ivrea AJAX (usa sitemap). Credenciales nunca en logs.

## Deuda conocida
- crear_producto_ui grande; tests de base no verdes; openai sin usar; docs antiguos. No tocar sin permiso.
