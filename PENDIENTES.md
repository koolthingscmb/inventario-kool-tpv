# PENDIENTES — KOOL TPV

> Última actualización: 2026-09-17 (sesión tarde: Shopify stock por variante + categoría)

## HECHO ✅

- **Edición Masiva en Almacén** (commit `c08a753` en `windows-beta`):
  - Modo NOMBRES + modo PVP, multi-selección, transacciones atómicas, auditoría.
- **Saneamiento y Especialización del Motor de Búsqueda** (Fase 1 + Limpieza Pro):
  - **Fuentes Especializadas**: AniList, Jikan, MangaDex y Google Books ahora solo traen datos técnicos (Autores reales, Títulos Originales/Kanji, Géneros, Demografía). Se ha eliminado la carga de sinopsis redundante de estas APIs.
  - **Búsqueda en Paralelo**: Ahora las fuentes se consultan simultáneamente. La app ya no se congela sumando esperas; el tiempo total es el de la fuente más lenta.
  - **Búsqueda por ISBN**: Google Books prioriza el código de barras para un match de tomo perfecto.
  - **Fix Naming Cruzado**: Se han renombrado los widgets en `crear_producto_ui` para que sean claros (`e_store_title` para la tienda, `e_google_title` para el tag SEO).
  - **OpenAI Pro**: Activado el modo `json_object` y sustitución segura de variables. Ya no se rompe por llaves en el prompt.
  - **Robustez Windows**: Importación "lazy" de DuckDuckGo. Si falta la librería, la ficha de producto abre perfectamente y la búsqueda web simplemente se desactiva.
  - **Limpieza de Basura**: Eliminados prints de debug masivos en la terminal.
- **Fix variables del prompt SEO**:
  - El prompt del usuario con 9 variables ahora funciona al 100% rindiendo datos reales a `{author}`, `{publisher}`, `{isbn}`, `{kanji}`, etc.

## PENDIENTE — El Siguiente Salto 🚀

### 1. Botón "SINOPSIS" (Whakoom Nativo)
- Crear una nueva fuente `WhakoomSource` que lea directamente de Whakoom usando el ISBN.
- Añadir el botón específico en la UI al lado de la descripción.
- Objetivo: Sinopsis 100% oficiales españolas por tomo, sin fallos de IA.

### 2. Gestión de Imágenes (Fase 4)
- Columna `imagen_url` en BD y guardado de portadas de alta resolución de las APIs.

### 3. Push real a Shopify
- El servicio que realmente sube el producto y el stock a la tienda online.

## PENDIENTE — Shopify / Tipos (2026-09-17)

### 4. Validar subida de camiseta con stock real
- Probar en Mac que `Hombre`, `Mujer` e `Infantil` suben con stock por color/talla.
- Confirmar que `Sorpresa` aparece como color con stock `stock_sorpresa` y precio `precio_sorpresa`.
- Confirmar que `taxonomyCategory` se asigna en Shopify cuando el Tipo tiene `categoria_id`.

### 5. Revisar `changeFromQuantity` en actualizaciones
- Ahora se usa `changeFromQuantity: 0` porque son variantes nuevas.
- Si se re-sube un producto ya existente, Shopify podría pedir el stock actual en vez de `0`.
- Decidir si hay que leer el stock actual de Shopify antes de actualizar.

### 6. UI de Tipos / Categorías
- Abrir `Tipos` y probar el `SearchableCombo` de categoría.
- Guardar un tipo con categoría y verificar que `categoria_id` persiste.
- Confirmar que el campo `shopify_taxonomy` ya no se usa y puede quedar obsoleto.

### 7. Windows
- Al hacer `git pull` en Windows, la migración 054 se aplica sola.
- Probar que la UI de Tipos funciona igual en Windows.

## RESUELTO — Producción / Variantes (2026-09-18)

### 8. ~~Chips de variantes posiblemente hardcodeados~~
- Causa: `config_tab_variantes.py` cargaba `obtener_por_tipo(..., solo_activos=False)` — mostraba variantes eliminadas (soft delete, `activo=0`).
- Fix: `solo_activos=True`. Las eliminadas ya no aparecen.

## RESUELTO — Shopify / Subida por tipo (2026-09-20)

### 9. Configuración Shopify reestructurada por tipos
- Pestaña CONFIG → GENERAL: grid de 4 columnas solo con conexión (URL, token, location, API, plantilla, marca, guía, CDN).
- Nueva pestaña CONFIG → TIPOS: añadir tipos a controlar, configurar por variante `sync_web` + `precio_web`, prompts IA por tipo, stock/precio sorpresa para Camiseta.
- Base de datos: migraciones 055 (`web_activo` en tipos, `precio_web` en variantes) y 056 (`shopify_prompts` con `UNIQUE(clave, tipo)` para genéricos + excepciones).
- SUBIDA: usa tipos `web_activo=1`, variantes `sync_web=1`, precio por variante y prompts por tipo.
- Arreglado error `productOptions` con valores vacíos: se respetan `requiere_talla` y `requiere_color`.
- Eliminado el campo único PRECIO WEB de SUBIDA y el recargo de tallas grandes; los precios salen de CONFIG → TIPOS.
- Eliminado el selector **VARIANTES A SUBIR** de SUBIDA: ahora se suben automáticamente todas las variantes activas del tipo.
- **PLANTILLA** movida de SUBIDA a CONFIG → TIPOS (con fallback al config global). Migración 057.

## PENDIENTE — Shopify / Pruebas reales (2026-09-20)

### 10. Validar subida con precios por variante
- Configurar `precio_web` y `template_suffix` en CONFIG → TIPOS para Camiseta (Hombre, Mujer, Infantil) y probar subida real.
- Confirmar que `Sorpresa` solo se añade en Camiseta y que stock/precio sorpresa se leen de CONFIG → TIPOS.
- Verificar que productos sin talla/color (Cuerdas, Mochila, Tote, Láminas) suben sin error.

### 11. Revisar el prompt de tags (GENERAR TAGS)
- El prompt `camiseta_tags` está generando tags de mala calidad.
- Revisar el texto del prompt en IA PROMPTS / CONFIG → TIPOS y afinarlo.
- Posible mejora: pasar la lista de tags existentes en Shopify para que reutilice.

