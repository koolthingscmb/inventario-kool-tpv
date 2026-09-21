"""Prompts de generación de contenido para productos de Shopify.

Contiene:
- Los prompts GENÉRICOS (sirven para cualquier tipo de producto).
- Los prompts específicos de CAMISETA (se siembran como excepción del tipo
  Camiseta; son el port exacto del Google Apps Script original).

Las interpolaciones usan placeholders Python ({...}) que se rellenan con
str.replace para no interferir con las llaves {} del ejemplo JSON del body.
"""

# =====================================================================
# PROMPTS GENÉRICOS (tipo IS NULL en shopify_prompts)
# =====================================================================

# Marcadores disponibles en PROMPT_SEO_DESCRIPCION:
#   {tipo_producto}  {titulo_base}  {tags}  {beneficio}
PROMPT_SEO_DESCRIPCION = """Actúa como un copywriter experto en SEO para "Kool Things".
PRODUCTO: {tipo_producto} sobre "{titulo_base}"
TAGS: {tags}
BENEFICIO PRINCIPAL: "{beneficio}"
TAREA: Escribe una meta descripción SEO (máximo 155 caracteres) siguiendo esta estructura de 4 partes, combinando las frases de forma natural:
1. Hook Emocional (1 frase): Crea una pregunta o llamada a la acción potente que conecte con un fan del tema "{titulo_base}". Extrae solo el tema principal del título (ej: si es "Producto X | Banda Y", usa solo "Banda Y") y no uses el símbolo "|".
2. Descripción Atractiva (1 frase): Redacta una frase que evoque la esencia del producto, evitando repetir palabras del título.
3. Diferenciador Clave (ELIGE UNO): Selecciona solo UNA de las siguientes frases y úsala: Diseño 100% original., ¡No lo encontrarás en otro sitio!, Calidad premium., Fanart exclusivo., Pieza de culto., Edición para verdaderos fans..
4. Beneficio Final (1 frase): Termina con una frase como "El regalo perfecto para fans" o "Luce tu pasión con estilo".
REGLAS ESTRICTAS: La respuesta debe ser un único párrafo de texto, sin superar los 155 caracteres, sin hashtags, emojis, o comillas dobles. Texto en español.
REGLA GRAMATICAL: Si el texto incluye nombres de bandas, películas o referencias culturales, usa artículos apropiados (el, la, del, de la) de forma natural en español.
REGLA CRÍTICA: La meta descripción DEBE incluir las palabras clave principales de "{titulo_base}" de forma natural."""

# Marcadores disponibles en PROMPT_BODY_HTML:
#   {variante}  {tipo_producto}  {titulo_base}  {tono}  {instrucciones_variante}
#   {tags}  {beneficio}  {tags_top3}
PROMPT_BODY_HTML = """Actúa como un copywriter experto en SEO, posicionamiento en Google, un fanático de la cultura pop, un auténtico friki y otaku, un pro gamer y un experto de baloncesto para la tienda "Kool Things".
TAREA:
Genera un objeto JSON con 7 claves para escribir el Body HTML de un producto de tipo {tipo_producto} ({variante}) sobre "{titulo_base}". El tono general debe ser: **{tono}**. {instrucciones_variante}
DATOS DEL PRODUCTO:
- Título: "{titulo_base}"
- Tags: {tags}
- Beneficio Principal: "{beneficio}"
ESTRUCTURA DEL JSON A DEVOLVER:
{
  "titulo_introductorio": "[Crea un título H2 creativo de entre 8-12 palabras que incluya el tema principal de '{titulo_base}' (extrae solo el tema, NO uses el nombre del tipo de producto ni el símbolo '|'). El título debe incorporar la idea principal de '{beneficio}' y ser descriptivo y atractivo.]",
  "parrafo_introductorio": "[Escribe un texto plano para un párrafo <p> como gancho emocional (2-3 frases). Debe usar alguna de las palabras clave de los Tags y hablar sobre por qué este diseño es único, exclusivo de Kool Things y una pieza de arte para fans.]",
  "titulo_seccion_calidad": "[Crea un título H3 creativo y corto relacionado con '{titulo_base}' que hable de la calidad premium del producto. Debe ser pegadizo y usar lenguaje del universo del tema. Máximo 5-6 palabras.]",
  "bloque_calidad_impresion": "[Describe el beneficio de la calidad de impresión del diseño con una metáfora del mundo de '{titulo_base}'.]",
  "bloque_calidad_material": "[Describe la calidad y el tacto del material del producto.]",
  "bloque_calidad_durabilidad": "[Describe la durabilidad del producto con una comparación divertida del mundo de '{titulo_base}'.]",
  "bloque_porque_elegirnos": "[Escribe 4-5 frases convincentes explicando por qué Kool Things es la mejor opción para fans de '{titulo_base}'. Menciona: diseños exclusivos y originales, ÚNICOS EN EL MUNDO ya que son dibujados por Kool Things, calidad premium que perdura, atención al detalle, pasión por la cultura friki/pop, y que cada producto es una pieza única para verdaderos fans. Hazlo persuasivo.]"
}
REGLA CRÍTICA SEO: El texto DEBE incluir de forma natural estas palabras clave: "{titulo_base}" y los tags principales ({tags_top3}).
REGLAS ESTRICTAS:
- La respuesta debe ser únicamente un objeto JSON válido, sin texto antes ni después.
- Todo el texto generado para las claves debe ser TEXTO PLANO, sin etiquetas HTML.
- Todo el texto debe estar en español.
- NO repitas el nombre del tipo de producto en los textos generados.
- Extrae solo el tema principal del título (ej: si es "Producto X | Banda Y", usa solo "Banda Y").
- NO uses el título completo del producto en ningún texto generado.
- NO uses el símbolo "|" en ningún caso."""

# Prompt de tags genérico.
# Marcadores: {titulo_base}  {tipo_producto}
PROMPT_TAGS = """Genera una lista de 8-12 tags para Shopify, en español, separados por comas, para un producto de tipo {tipo_producto} sobre "{titulo_base}".
Incluye el tema principal, el tipo de producto, palabras relacionadas y términos de búsqueda habituales.
Responde solo con la lista de tags, sin explicaciones ni comillas."""

# Plantilla HTML genérica del body (estructura neutra para cualquier producto).
# Marcadores: {titulo_introductorio} {parrafo_introductorio} {titulo_seccion_calidad}
# {bloque_calidad_impresion} {bloque_calidad_material} {bloque_calidad_durabilidad}
# {bloque_porque_elegirnos} {botones_html}
PLANTILLA_HTML = """<h2>{titulo_introductorio}</h2>
<p>{parrafo_introductorio}</p>
<h3>{titulo_seccion_calidad}</h3>
<ul>
  <li><strong>Impresión de Alta Definición:</strong> {bloque_calidad_impresion}</li>
  <li><strong>Materiales Premium:</strong> {bloque_calidad_material}</li>
  <li><strong>Hecho para Durar:</strong> {bloque_calidad_durabilidad}</li>
</ul>
<h3>¿Por Qué Elegir Kool Things?</h3>
<p>{bloque_porque_elegirnos}</p>
    <h6><span>Este diseño es un FANART. No pretende ser ninguna copia de algún signo distintivo o marca.</span></h6>
    <br>
    {botones_html}
    <br><br>
    <div style="border-top: 1px solid #ddd; padding-top: 15px; margin-top: 15px;">
      <p>Antes de realizar tu pedido, te recomendamos revisar nuestras <a href="/pages/nuestros-envios" style="font-weight: bold;">condiciones de envío</a> y <a href="/policies/refund-policy" style="font-weight: bold;">política de reembolso</a> para asegurarte de que se ajustan a tus necesidades.</p>
    </div>"""

# Patrón del SEO title genérico.
# Marcadores: {titulo} {variante} {marca}
PLANTILLA_SEO_TITLE = "{titulo} | {variante} | {marca}"

# =====================================================================
# PROMPTS ESPECÍFICOS DE CAMISETA (excepción del tipo Camiseta)
# =====================================================================

PROMPT_SEO_DESCRIPCION_CAMISETA = """Actúa como un copywriter experto en SEO para "Kool Things".
PRODUCTO: Camiseta sobre "{titulo_base}"
TAGS: {tags}
BENEFICIO PRINCIPAL: "{beneficio}"
TAREA: Escribe una meta descripción SEO (máximo 155 caracteres) siguiendo esta estructura de 4 partes, combinando las frases de forma natural:
1. Hook Emocional (1 frase): Crea una pregunta o llamada a la acción potente que conecte con un fan del tema "{titulo_base}". NO repitas la palabra "camiseta" ni uses el símbolo "|". Extrae solo el tema principal (ej: si es "Camiseta X | Banda Y", usa solo "Banda Y").
2. Descripción Atractiva (1 frase): Redacta una frase que evoque la esencia del producto, evitando repetir palabras del título.
3. Diferenciador Clave (ELIGE UNO): Selecciona solo UNA de las siguientes frases y úsala: Diseño 100% original., ¡No lo encontrarás en otro sitio!, Impresión DTG de alta definición., 100% algodón premium., Comodidad legendaria., Fanart exclusivo., Pieza de culto..
4. Beneficio Final (1 frase): Termina con una frase como "El regalo perfecto para fans" o "Luce tu pasión con estilo".
REGLAS ESTRICTAS: La respuesta debe ser un único párrafo de texto, sin superar los 155 caracteres, sin hashtags, emojis, o comillas dobles. Texto en español.
REGLA GRAMATICAL: Si el texto incluye nombres de bandas, películas o referencias culturales, usa artículos apropiados (el, la, del, de la) de forma natural en español.
REGLA CRÍTICA: La meta descripción DEBE incluir las palabras clave principales de "{titulo_base}" de forma natural."""

PROMPT_BODY_HTML_CAMISETA = """Actúa como un copywriter experto en SEO, posicionamiento en Google, un fanático de la cultura pop, un auténtico friki y otaku, un pro gamer y un experto de baloncesto para la tienda "Kool Things".
TAREA:
Genera un objeto JSON con 5 claves para escribir el Body HTML de una camiseta de {genero} sobre "{titulo_base}". El tono general debe ser: **{tono}**. {instrucciones_genero}
DATOS DEL PRODUCTO:
- Título: "{titulo_base}"
- Tags: {tags}
- Beneficio Principal: "{beneficio}"
ESTRUCTURA DEL JSON A DEVOLVER:
{
  "titulo_introductorio": "[Crea un título H2 creativo de entre 8-12 palabras que incluya el tema principal de '{titulo_base}' (extrae solo el tema, NO uses la palabra 'camiseta' ni el símbolo '|'). El título debe incorporar la idea principal de '{beneficio}' y ser descriptivo y atractivo.]",
  "parrafo_introductorio": "[Escribe un texto plano para un párrafo <p> como gancho emocional (2-3 frases). Debe usar alguna de las palabras clave de los Tags y hablar sobre por qué este diseño es único, exclusivo de Kool Things y una pieza de arte para fans.]",
  "titulo_seccion_calidad": "[Crea un título H3 creativo y corto relacionado con '{titulo_base}' que hable de la calidad premium de las camisetas. Debe ser pegadizo y usar lenguaje del universo del tema. Máximo 5-6 palabras.]",
  "bloque_calidad_impresion": "[Describe el beneficio de la impresión DTG con una metáfora del mundo de '{titulo_base}'.]",
  "bloque_calidad_material": "[Describe la sensación de suavidad del algodón premium.]",
  "bloque_calidad_durabilidad": "[Describe la durabilidad con una comparación divertida del mundo de '{titulo_base}'.]",
  "bloque_porque_elegirnos": "[Escribe 4-5 frases convincentes explicando por qué Kool Things es la mejor opción para fans de '{titulo_base}'. Menciona: diseños exclusivos y originales, ÚNICOS EN EL MUNDO ya que son dibujados por Kool Things, calidad premium en las camisetas e impresiones que perdura, atención al detalle, pasión por la cultura friki/pop, y que cada camiseta es una pieza única para verdaderos fans. Hazlo persuasivo.]"
}
REGLA CRÍTICA SEO: El texto DEBE incluir de forma natural estas palabras clave: "{titulo_base}" y los tags principales ({tags_top3}).
REGLAS ESTRICTAS:
- La respuesta debe ser únicamente un objeto JSON válido, sin texto antes ni después.
- Todo el texto generado para las claves debe ser TEXTO PLANO, sin etiquetas HTML.
- Todo el texto debe estar en español.
- NO uses la palabra "camiseta" en los textos generados.
- Extrae solo el tema principal del título (ej: si es "Camiseta X | Banda Y", usa solo "Banda Y").
- NO uses el título completo del producto en ningún texto generado.
- NO uses el símbolo "|" en ningún caso."""

PROMPT_TAGS_CAMISETA = """Genera una lista de 8-12 tags para Shopify, en español, separados por comas, para una camiseta sobre "{titulo_base}".
Incluye el tema principal, palabras relacionadas y términos de búsqueda habituales.
Responde solo con la lista de tags, sin explicaciones ni comillas."""

# Plantilla HTML de la ficha de camiseta — transcripción EXACTA del GAS
# (incluye el </ul> duplicado original; Shopify lo normaliza igual que hacía
# con el script).
PLANTILLA_HTML_CAMISETA = """<h2>{titulo_introductorio}</h2>
<p>{parrafo_introductorio}</p>
<h3>{titulo_seccion_calidad}</h3>
<ul>
  <li><strong>Impresión DTG de Alta Definición:</strong> {bloque_calidad_impresion}</li>
  <li><strong>Algodón Premium 100%:</strong> {bloque_calidad_material}</li>
  <li><strong>Confección Duradera:</strong> {bloque_calidad_durabilidad}</li>
</ul>
</ul>
<h3>¿Por Qué Elegir Kool Things?</h3>
<p>{bloque_porque_elegirnos}</p>

<h3>Características del Producto</h3>
<p>
  Material: 100% Algodón Premium...<br>
  Gramaje: 165 g/m².<br>
  Corte: {corte}.<br>
  Cuidados: Lavar en frío (máximo 30 grados), del revés. No planchar el dibujo. ¡Secadora prohibida!.<br>
  ¿Dudas? Consulta nuestra <a href="{link_guia}">Guía de Tallas Completa</a>.
</p>
    <h6><span>Esta camiseta es un FANART. No pretende ser ninguna copia de algún signo distintivo o marca.</span></h6>
    <br>
    <div style="padding-bottom:5px;">¿Buscas esta misma camiseta para...?</div>
    {botones_html}
    <br><br>
    <div style="border-top: 1px solid #ddd; padding-top: 15px; margin-top: 15px;">
      <p>Antes de realizar tu pedido, te recomendamos revisar nuestras <a href="/pages/nuestros-envios" style="font-weight: bold;">condiciones de envío</a> y <a href="/policies/refund-policy" style="font-weight: bold;">política de reembolso</a> para asegurarte de que se ajustan a tus necesidades.</p>
    </div>"""

# =====================================================================
# DATOS COMPARTIDOS
# =====================================================================

# Instrucciones por género/variante (se inyecta en {instrucciones_genero}
# y {instrucciones_variante})
INSTRUCCIONES_GENERO = {
    "Hombre": "Usa un lenguaje masculino (ej. 'un verdadero fan', 'diseñado para ti').",
    "Mujer": "Adapta todo el texto a un género femenino e inclusivo (ej. 'una verdadera fan', 'diseñada para ti').",
    "Infantil": """CRÍTICO: Dirígete SIEMPRE a los padres/madres en segunda persona (tú/usted), NUNCA a los niños.
Usa frases como: 'Tu hijo/a lucirá increíble', 'Regala a tu pequeño/a', 'El producto perfecto para que tu hijo/a muestre su pasión'.
Enfócate en: comodidad para los niños, calidad que los padres valoran, y el orgullo de vestir a sus hijos con diseños únicos.
Tono: Cercano y persuasivo para padres que buscan productos de calidad para sus hijos.""",
}

# Corte del producto por género (se usa en el bloque HTML fijo, no en el prompt)
CORTE_PRODUCTO = {
    "Hombre": "Corte relajado (Relaxed Fit)",
    "Mujer": "Corte femenino entallado",
    "Infantil": "Corte relajado (Relaxed Fit) infantil",
}

TONO_POR_DEFECTO = "apasionado y para fans"

GENEROS_CAMISETA = ["Hombre", "Mujer", "Infantil"]

LINK_GUIA_TALLAS = "https://koolthingshop.com/pages/nuestras-camisetas"

# Botón de enlace a otra variante.
# Marcadores: {handle} {cdn_base} {genero} {genero_upper}
BOTON_GENERO = "<a href='/products/{handle}' style='margin-right:10px;'><img src='{cdn_base}BOTON-CAMI-{genero_upper}.png' alt='{genero}' width='150'></a>"

CDN_BASE_BOTONES = "https://cdn.shopify.com/s/files/1/0269/4814/1167/files/"

# Prompt por defecto del flujo manga (BUSCAR DATA).
# Marcadores: {product_name} {source_data}
PROMPT_MANGA_SEO = """Actúa como un experto en SEO para Shopify. A partir de los siguientes datos de un producto (fuente externa y nombre local), genera los campos SEO necesarios en formato JSON.

NOMBRE LOCAL: {product_name}
DATOS FUENTE: {source_data}

Debes devolver estrictamente un objeto JSON con las siguientes claves:
- seo_title: Título optimizado para buscadores (máx 70 caracteres).
- seo_short: Título corto y atractivo.
- seo_description: Meta-descripción optimizada (máx 160 caracteres).
- description: Descripción detallada en HTML profesional para la ficha de producto.
- tags: Lista de etiquetas separadas por comas.
- tipo_shop: Categoría o tipo de producto para la tienda.

No incluyas explicaciones, solo el JSON."""
