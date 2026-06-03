# 🔍 Análisis del Botón Power (X) en TPV

**Fecha:** 1 de junio de 2026  
**Estado:** Problema identificado - Pendiente de solución

---

## 📋 Resumen del Problema

Cuando estás en una subvista (Stock, Tickets, Cierres, etc.) y pulsas el botón Power (X):
- **Comportamiento esperado:** Volver al grid del TPV
- **Comportamiento actual:** A veces cierra todo el TPV y vuelve al menú principal

---

## 🔍 Causa Raíz Identificada

El sistema de `register_power_handler()` solo permite **UN handler activo a la vez**, creando un conflicto entre el TPV y sus subvistas.

### Flujo Problemático:

```
1. TPV se carga → Registra TpvView._handle_power ✅
2. Usuario abre Stock → StockSubView registra su _handle_power (SOBRESCRIBE el del TPV) ⚠️
3. Usuario pulsa X → Ejecuta StockSubView._handle_power → pop_subview() ✅
4. StockSubView.destroy() → Desregistra handler → _power_handler = None ❌
5. Usuario pulsa X otra vez → No hay handler → Ejecuta close_app() → Sale del TPV ❌❌
```

---

## 🏗️ Arquitectura Actual

### main.py (App)
```python
# Sistema de UN SOLO HANDLER
def register_power_handler(self, handler, owner=None):
    self._power_handler = handler  # ← SOBRESCRIBE el anterior

def _dispatch_power(self):
    if self._power_handler and self._power_handler():
        return 
    self.close_app()  # ← Se ejecuta si no hay handler
```

### tpv_view_new.py (TpvView)
```python
def __init__(...):
    # Registra su handler
    root.register_power_handler(self._handle_power, owner=self)

def _handle_power(self):
    if self._subview_stack:
        self.pop_subview()
        return True
    return False

# ⚠️ PROBLEMA: Nunca re-registra después de cerrar una subvista
```

### stock_subview.py (StockSubView) - y TODAS las subvistas
```python
def __init__(...):
    # Registra su handler (SOBRESCRIBE el del TPV)
    root.register_power_handler(self._handle_power, owner=self)

def _handle_power(self):
    self.view.pop_subview()  # Cierra esta subvista
    return True

def destroy(self):
    # Desregistra, dejando _power_handler = None
    root.unregister_power_handler(owner=self)
    super().destroy()
```

---

## 📊 Flujo Actual por Archivo

| Archivo | Registra Handler | Desregistra | Comportamiento |
|---------|-----------------|-------------|----------------|
| `main.py` | Sistema global (UN handler) | - | Ejecuta `close_app()` si no hay handler |
| `tpv_view_new.py` | ✅ Al iniciar TPV | ❌ Nunca | Handler sobrescrito por subvistas |
| `stock_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |
| `tickets_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |
| `cierres_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |
| `devolucion_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |
| `cliente_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |
| `descuento_subview.py` | ✅ Al abrir | ✅ Al cerrar | Deja `_power_handler = None` |

---

## 🔧 Soluciones Posibles

### Opción 1: Stack de Handlers (Más robusto)
Cambiar de un solo handler a una pila de handlers:

```python
# En main.py
def __init__(self):
    self._power_handler_stack = []  # En lugar de _power_handler

def register_power_handler(self, handler, owner=None):
    self._power_handler_stack.append(handler)

def unregister_power_handler(self, handler=None, owner=None):
    if self._power_handler_stack:
        self._power_handler_stack.pop()

def _dispatch_power(self):
    if self._power_handler_stack:
        handler = self._power_handler_stack[-1]  # El más reciente
        if handler():
            return
    self.close_app()
```

**Pros:** Robusto, mantiene jerarquía automáticamente  
**Contras:** Requiere cambios en main.py

---

### Opción 2: Re-registrar TPV después de pop_subview (Más simple)
```python
# En tpv_view_new.py
def pop_subview(self):
    # ... código actual ...
    
    # AL FINAL, re-registrar handler del TPV
    try:
        root = self.winfo_toplevel()
        if hasattr(root, "register_power_handler"):
            root.register_power_handler(self._handle_power, owner=self)
    except Exception:
        pass
```

**Pros:** Cambio mínimo, fácil de implementar  
**Contras:** Parcheado, no resuelve el problema de raíz

---

### Opción 3: Solo el TPV maneja Power (Más limpio)
Las subvistas NO registran handlers, solo el TPV:

```python
# Eliminar de TODAS las subvistas:
# - root.register_power_handler(self._handle_power, owner=self)
# - root.unregister_power_handler(owner=self)

# El TPV siempre maneja Power a través de su stack
```

**Pros:** Arquitectura más limpia, un solo punto de control  
**Contras:** Requiere eliminar código de 6+ archivos

---

## 🎯 Recomendación

**Opción 2** (re-registrar en pop_subview) es la más rápida y segura para resolver el problema inmediato.

**Opción 3** sería ideal a largo plazo, pero requiere refactorización de múltiples archivos.

**Opción 1** es la más robusta pero implica cambiar el core (main.py).

---

## 📝 Archivos Afectados

### Core:
- `main.py` - Sistema de registro de handlers

### TPV:
- `kool_tpv/modulos/tpv/tpv_view_new.py` - Vista principal TPV
- `kool_tpv/modulos/tpv/button_action_mapper.py` - Mapeo de botones a subvistas

### Subvistas TPV (todas registran/desregistran):
- `kool_tpv/modulos/tpv/subviews/stock_subview.py`
- `kool_tpv/modulos/tpv/subviews/tickets_subview.py`
- `kool_tpv/modulos/tpv/subviews/cierres_subview.py`
- `kool_tpv/modulos/tpv/subviews/devolucion_subview.py`
- `kool_tpv/modulos/tpv/subviews/cliente_subview.py`
- `kool_tpv/modulos/tpv/subviews/descuento_subview.py`

---

## 🧪 Cómo Reproducir

1. Abrir TPV
2. Pulsar botón "STOCK"
3. Pulsar X (cierra Stock correctamente ✅)
4. Pulsar X otra vez → Cierra TODO el TPV ❌

**Mismo comportamiento con:** Tickets, Cierres, Cliente, Descuento, Devolución
