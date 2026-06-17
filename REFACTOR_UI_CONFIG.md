# Índice de Refactorización UI Config - Pendiente

## COMPLETADO

- [x] `ui_dialogs.json` - Configuración unificada de dialogs (info, warning, error, success, password, input)
- [x] `ui_config_loader.py` - Loader con cache para ui_dialogs.json
- [x] `config_loader.py` - Modificado para priorizar ui_dialogs.json con fallback a legacy
- [x] Probar dialogs con nuevo config
- [x] Commit y push a windows-beta

---

## PENDIENTE - PRIMERA FASE (Componentes UI)

### 1. ui_toast.json
**Archivo a crear:** `kool_tpv/config/ui_toast.json`
**Qué incluye:**
- Configuración de ToastWidget (success, info, warning, error)
- Colores bg/fg por tipo
- Duración, opacidad, tamaño, posición
- Iconos (tamaño, padding)
- Botón OK opcional (info)

**Qué modificar:**
- `toast_widget.py` - Usar nuevo loader en lugar de `load_notificaciones_config()`
- `notificaciones_config.json` - Eliminar/mantener como fallback
- `notificaciones_config.py` - Eliminar o simplificar

**Archivos involucrados:**
- `kool_tpv/utils/widgets/notificaciones/toast_widget.py`
- `kool_tpv/config/notificaciones_config.py`
- `kool_tpv/config/notificaciones_config.json`

---

### 2. ui_navlist.json
**Archivo a crear:** `kool_tpv/config/ui_navlist.json`
**Qué incluye:**
- Configuración de NavList (row_normal_bg, row_hover_bg, row_selected_bg)
- Colores de texto por estado
- Borde seleccionado
- Fuente header, fuente fila
- Altura fila, altura header

**Qué modificar:**
- `nav_list.py` - Usar `load_ui_navlist()` en lugar de `load_colors()` + `load_layout_config()`
- `searchable_paginated_navlist.py` - Hereda de NavList
- `virtual_nav_list.py` - Hereda de NavList

**Archivos involucrados:**
- `kool_tpv/utils/widgets/nav_list.py`
- `kool_tpv/utils/widgets/virtual_nav_list.py`
- `kool_tpv/utils/widgets/searchable_paginated_navlist.py`
- `kool_tpv/config/colors_config.json` (sección nav_list)
- `kool_tpv/config/layout_config.json` (sección nav_list)

---

### 3. ui_buttons.json
**Archivo a crear:** `kool_tpv/config/ui_buttons.json`
**Qué incluye:**
- Configuración de ButtonFactory por tipo (action_primary, action_cancel, action_danger, dialog_accept, dialog_cancel, etc.)
- Colores (bg, hover, text, border)
- Tamaño (width, height)
- Fuente (family, size, weight)
- Corner radius, border width

**Qué modificar:**
- `button_factory.py` - Usar `load_ui_buttons()` en lugar de `button_styles.json` + `design_tokens.json`

**Archivos involucrados:**
- `kool_tpv/utils/factories/button_factory.py`
- `kool_tpv/config/button_styles.json`
- `kool_tpv/config/design_tokens.json`

---

## PENDIENTE - SEGUNDA FASE (Limpieza Legacy)

### 4. Limpiar colors_config.json
**Quitar:**
- Sección `global.dialogs` (ya está en ui_dialogs.json)
- Sección `global.components.nav_list` (ya estará en ui_navlist.json)

**Mantener:**
- `main_menu` (colores de botones de menú principal)
- `global_buttons` (power_btn, print_btn)
- `global.layout` (colores generales de la app)
- `global.components.action_buttons` (si se migran, quitar)

**Archivo:** `kool_tpv/config/colors_config.json`

---

### 5. Limpiar font_config.json
**Quitar:**
- Sección `components.dialog` (ya está en ui_dialogs.json)
- Sección `components.nav_list` (ya estará en ui_navlist.json)

**Mantener:**
- `global.families`
- `app.base_font`, `app.nav_button`, `app.tpv_large`
- `modules.*` (config, tpv, etc.)

**Archivo:** `kool_tpv/config/font_config.json`

---

### 6. Limpiar layout_config.json
**Quitar:**
- Sección `components.dialog` (ya está en ui_dialogs.json)
- Sección `components.nav_list` (ya estará en ui_navlist.json)

**Mantener:**
- `modules.*` (tpv, almacen, clientes, informes, shopify, config)
- `components.sidebar_layout`
- `components.power_layout`

**Archivo:** `kool_tpv/config/layout_config.json`

---

## PENDIENTE - TERCERA FASE (Módulos específicos)

### 7. ui_visorticket.json
**Qué incluye:**
- Fuente, tamaño, colores del visor de tickets
- Configuración de impresión

**Archivos:**
- `kool_tpv/modulos/tpv/ui/visor_negro.py`

---

### 8. ui_labels.json (opcional)
**Qué incluye:**
- `label_title` (Courier New 22 bold)
- `label_header` (Courier New 16 bold)
- `label_value` (Courier New 30 bold)
- `label_normal` (Courier New 12)

**Archivos que usan fuentes hardcodeadas:**
- `crear_cliente_ui.py` (labels tesoro, level, etc.)
- `clientes_tickets.py`
- `albaranes/exportar_albaran.py`

---

## PENDIENTE - CUARTA FASE (UI de Configuración)

### 9. Crear módulo Configuración UI
**Archivo nuevo:** `kool_tpv/modulos/config/ui_config_editor.py`

**Funcionalidades:**
- Editor visual de cada ui_*.json
- Preview en tiempo real del componente editado
- Botón "Aplicar" (reload sin reiniciar app)
- Botón "Reset a defaults"
- Validación de JSON antes de guardar
- Tabs: Dialogs, Toast, NavList, Buttons

**Estructura UI:**
```
Configuración > Apariencia
├── Tab: Dialogs (info, warning, error, success, password, input)
│   ├── Colores (bg, border, texto)
│   ├── Fuentes (título, mensaje, botón, input)
│   ├── Tamaño ventana, spacing
│   └── Preview del dialog
├── Tab: Toast
│   ├── Colores por tipo
│   ├── Duración, opacidad
│   └── Preview toast
├── Tab: NavList
│   ├── Colores fila (normal, hover, seleccionada)
│   ├── Fuente header, fuente fila
│   └── Preview lista
└── Tab: Buttons
    ├── Colores por tipo
    ├── Tamaño, fuente
    └── Preview botones
```

---

## PENDIENTE - QUINTA FASE (Optimización)

### 10. Unificar loaders
**Crear:** `kool_tpv/config/ui_loader.py`

**Función:**
- Un solo loader para todos los ui_*.json
- Hot-reload global (tecla F5 o botón)
- Cache centralizado para todos los componentes UI

---

## ORDEN RECOMENDADO DE EJECUCIÓN

1. **Toast** (más simple, un solo archivo)
2. **NavList** (2-3 archivos a modificar)
3. **Buttons** (ButtonFactory es central)
4. **Limpiar JSONs legacy** (una vez todo probado 2 semanas)
5. **Visor de tickets**
6. **Labels**
7. **UI de Configuración** (lo más largo)
8. **Unificar loaders**

---

## NOTAS

- Cada fase debe incluir: crear JSON → crear loader → modificar código → probar → commit
- Siempre mantener fallback a JSONs legacy hasta confirmar que todo funciona 100%
- El `FALLBACKS` hardcodeado en `config_loader.py` sirve como último recurso de seguridad
