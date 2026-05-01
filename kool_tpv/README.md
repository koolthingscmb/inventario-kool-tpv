# kool_tpv

Estructura inicial del proyecto `kool_tpv`.

Nota: Todos los archivos creados contienen solo placeholders y comentarios
que indican su propósito. No se ha añadido lógica o implementación.

Estructura creada:

- `main.py` - Punto de entrada de la aplicación (placeholder).
- `modulos/` - Módulos funcionales (`tpv`, `clientes`, `impresion`, `configuracion`).
- `base_datos/` - Scripts y utilidades para la base de datos.
- `assets/`, `logs/`, `tests/`, `scripts/` - Carpetas auxiliares con `__init__.py`.

## TUTORIAL: cómo modificar tamaños y estilo de las zonas y botones

Esta sección explica de forma directa y práctica dónde tocar para cambiar
las dimensiones y el estilo de la interfaz del `BuscarArticuloPanel` (zona
superior, zona central y botones). Haz una copia de seguridad antes de
editar y reinicia la aplicación para ver los cambios.

- Archivo a editar: `kool_tpv/modulos/tpv/actions/buscar_articulo.py`

- ZONA SUPERIOR (barra con los botones `CATEGORÍAS` y `TIPOS`):
    - Valor por defecto: dentro del dict `cfg` en `__init__`.
        - `top_height`: altura en píxeles de la zona superior. Ejemplo: `72`.
        - `top_left`: padding/offset izquierdo en píxeles (donde empieza la zona).
    - Línea donde se crea el frame superior (usa `self.top_height`):
        - `self.top_buttons = ctk.CTkFrame(self.overlay, fg_color="transparent", height=self.top_height)`
        - `self.top_buttons.pack(side="top", fill="x", pady=(8, 0), padx=(self.top_left, 12))`

- BOTONES (zona superior): cambiar tamaño, fuente y colores
    - Dentro de la misma sección busca la creación de `self.cat_btn` y
        `self.tipos_btn` y modifica estos parámetros:
        - `width`: ancho en píxeles.
        - `height`: alto en píxeles.
        - `fg_color`: color de fondo normal (hex).
        - `hover_color`: color al pasar el cursor (hex).
        - `font`: tuple con la fuente, p. ej. `("Arial", 16, "bold")`.

- ZONA CENTRAL (categorías / tipos): fuente, tamaño y colores de botones
    - Valores por defecto editables en `cfg`:
        - `btn_font`: fuente por defecto de los botones (tuple).
        - `btn_width`: ancho objetivo usado para calcular columnas en el grid.
        - `category_btn_height`: altura (px) de los botones de categorías/tipos.
    - Para cambiar color/ancho de cada botón modifica `_render_categories()`:
        - `fg_color`: color normal.
        - `hover_color`: color hover.
        - `text_color`: color del texto.
        - `width` y `height` en la llamada a `ctk.CTkButton(...)`.

- ZONA INFERIOR (artículos): similar a la central
    - `article_btn_height` controla la altura por defecto de los botones
        de artículos.
    - Cambia `btn_font`, `btn_width` y `article_btn_height` en `cfg`.

- Cambios en tiempo real (sin editar el archivo):
    - Crea el panel en tu REPL o en código y usa `set_ui_config`:

```python
panel.set_ui_config(btn_font=("Verdana",16,"bold"), category_btn_height=60)
panel.cat_btn.configure(width=150, height=50, fg_color="#2E8B57", hover_color="#00A4DF")
for b in panel.categories_grid.winfo_children():
        b.configure(fg_color="#2E8B57", hover_color="#00A4DF", text_color="#000000", width=180, height=60)
```

- Notas y recomendaciones:
    - Guarda siempre antes de reiniciar la aplicación.
    - Si no ves cambios, asegúrate de que el overlay no esté cacheado y
        que llamas a `panel.show()` después de cambiar configuraciones.
    - Usa `app.update_idletasks()` para forzar recálculo de geometría en pruebas.

Si quieres, puedo aplicar un ejemplo concreto (valores) y hacer el commit.

## Plantilla: Instrucciones exactas para colocar el botón `power/close`

Usar esta plantilla cada vez que se implemente una nueva pantalla u overlay.

1) Crear el botón con la utilidad (NO colocar dentro de la utilidad):

```python
from kool_tpv.utils.global_buttons import create_global_close_button

# crear el botón (no hacer place/pack dentro de la función)
close_btn = create_global_close_button(parent_overlay, command=on_close)
```

2) En el método `show()` del overlay, colocar el botón usando las coordenadas
absolutas del `power_button` para conseguir coincidencia pixel-perfect:

```python
# colocar el overlay primero
self.overlay.place(x=0, y=0, relwidth=1, relheight=1)

# forzar cálculo de geometría
self.update_idletasks()
self.overlay.update_idletasks()

# obtener referencia a la app (root) y al power_button
app_root = self.root  # o la referencia a la instancia App
pb = getattr(app_root, 'power_button', None)

if pb is not None:
    rel_x = pb.winfo_rootx() - self.overlay.winfo_rootx()
    rel_y = pb.winfo_rooty() - self.overlay.winfo_rooty()
else:
    # fallback razonable: 12px offset desde nav_frame
    nav = getattr(app_root, 'nav_frame', None)
    if nav is not None:
        rel_x = 12 + (nav.winfo_rootx() - self.overlay.winfo_rootx())
        rel_y = 12 + (nav.winfo_rooty() - self.overlay.winfo_rooty())
    else:
        rel_x, rel_y = 12, 12

self.close_btn.place(x=rel_x, y=rel_y)
self.close_btn.lift()
```

3) Verificación automática (comprobar después de implementar):

```python
print('power_button root coords:', power_button.winfo_rootx(), power_button.winfo_rooty(), power_button.winfo_width(), power_button.winfo_height())
print('close_btn root coords:', close_btn.winfo_rootx(), close_btn.winfo_rooty(), close_btn.winfo_width(), close_btn.winfo_height())
# ambos deben coincidir exactamente
```

4) Reglas a seguir:
- `create_global_close_button` SOLO crea y devuelve el widget; NO hace `place()` ni `pack()`.
- La colocación se hace siempre después de `overlay.place(...)` y `update_idletasks()`.
- Si la `nav_frame` o `power_button` pueden moverse mientras el overlay esté abierto,
  recalcula la posición cada vez que muestres el overlay o escucha eventos de `<Configure>`.

5) Limpieza final:
- Elimina logs diagnósticos temporales y banderas de depuración antes de hacer commit.

Sigue esta plantilla exactamente para evitar discrepancias de posición.
# kool_tpv

Estructura inicial del proyecto `kool_tpv`.

Nota: Todos los archivos creados contienen solo placeholders y comentarios
que indican su propósito. No se ha añadido lógica o implementación.

Estructura creada:

- `main.py` - Punto de entrada de la aplicación (placeholder).
- `modulos/` - Módulos funcionales (`tpv`, `clientes`, `impresion`, `configuracion`).
- `base_datos/` - Scripts y utilidades para la base de datos.
- `assets/`, `logs/`, `tests/`, `scripts/` - Carpetas auxiliares con `__init__.py`.
