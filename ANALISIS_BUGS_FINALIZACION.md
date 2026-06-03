# 🐛 Análisis de Bugs en Finalización de Venta

**Fecha:** 1 de junio de 2026  
**Estado:** Problemas identificados - Pendiente de solución

---

## 📋 Problemas Reportados

### Bug 1: Diálogo muestra "TICKET #NONE"
- **Ticket real generado:** `2026-0303` ✅
- **Diálogo muestra:** `VENTA GUARDADA - TICKET #NONE GUARDADO CORRECTAMENTE` ❌

### Bug 2: Cliente no se limpia después de finalizar venta
- **Comportamiento esperado:** Cliente debe limpiarse y mostrar "SELECCIONAR CLIENTE..."
- **Comportamiento actual:** Cliente sigue mostrándose después de finalizar la venta ❌

---

## 🔍 Bug 1: Ticket #None en Diálogo

### Causa Raíz:
Los **processors retornan valores inconsistentes**:

#### VentaProcessor (✅ Correcto)
```python
# kool_tpv/modulos/ticket/venta_processor.py, línea 107
return ticket_id, num_ticket  # ← TUPLA
```

#### VentaFidelizacionProcessor (❌ Incorrecto)
```python
# kool_tpv/modulos/ticket/venta_fidelizacion_processor.py, línea 38
return ticket_id  # ← SOLO ticket_id, NO num_ticket
```

#### DevolucionProcessor (❌ Incorrecto)
```python
# kool_tpv/modulos/ticket/devolucion_processor.py, línea 131
return ticket_id  # ← SOLO ticket_id, NO num_ticket
```

### Flujo del Error:

En [tpv_controller.py](kool_tpv/modulos/tpv/tpv_controller.py#L800-L806):
```python
proc_res = processor.process(**payload)

if isinstance(proc_res, (tuple, list)):
    ticket_id = proc_res[0]
    num_ticket = proc_res[1] if len(proc_res) > 1 else payload.get('num_ticket')
else:
    ticket_id = proc_res
    num_ticket = payload.get('num_ticket')  # ← Problema: puede ser None
```

Luego en línea 814:
```python
show_success(
    self.view.container,
    'Venta guardada',
    f'Ticket #{num_ticket} guardado correctamente'  # ← num_ticket = None
)
```

### ¿Por qué ocurre?

1. Usuario finaliza venta **con cliente** (tipo_ticket = `venta_fidelizacion`)
2. Se usa `VentaFidelizacionProcessor`
3. Processor retorna solo `ticket_id` (no tupla)
4. Código cae en `else` y busca `payload.get('num_ticket')`
5. `payload.get('num_ticket')` retorna `None` porque **num_ticket se genera DENTRO del processor**, no antes
6. Diálogo muestra `#None`

### Evidencia en Logs:
```python
# tpv_controller.py, línea 751-754
num_ticket_val = None
try:
    num_ticket_val = carrito_service.get_num_ticket()
except Exception:
    num_ticket_val = None
logger.info(f"num_ticket={num_ticket_val}")  # ← Seguramente muestra None
```

El `num_ticket` se pasa al payload pero **se genera dentro de la transacción del processor**, no antes.

---

## 🔍 Bug 2: Cliente No Se Limpia

### Causa Raíz:
`TicketCarrito.update_carrito()` **NO actualiza la visualización del cliente**.

### Flujo del Error:

#### En CarritoService ([carrito_service.py](kool_tpv/modulos/tpv/carrito/carrito_service.py#L140-L169)):
```python
def clear(self) -> None:
    self._items.clear()
    # ...
    self._cliente = None  # ← SÍ limpia el cliente ✅
    # ...
    logging.info('Carrito limpiado completamente')
```

#### En TpvController ([tpv_controller.py](kool_tpv/modulos/tpv/tpv_controller.py#L806-L809)):
```python
# Limpiar carrito
carrito_service.clear()  # ← Limpia cliente en el servicio ✅

# Actualizar UI
ticket_carrito = getattr(self.view, 'ticket_carrito', None)
if ticket_carrito:
    ticket_carrito.update_carrito()  # ← Actualiza lista pero NO cliente ❌
```

#### En TicketCarrito ([ticket_carrito.py](kool_tpv/utils/widgets/ticket_carrito.py#L853-L920)):
```python
def update_carrito(self):
    """Actualizar display del carrito manteniendo scroll."""
    # 1. Guarda scroll position
    # 2. Limpia nav_list
    # 3. Añade items del carrito
    # 4. Añade línea visual de tesoro si aplica
    # 5. Restaura scroll position
    # 6. Actualiza resumen financiero
    
    # ❌ FALTA: NO llama a update_cliente()
```

El método `update_cliente()` existe ([línea 616-650](kool_tpv/utils/widgets/ticket_carrito.py#L616)), pero **nunca se llama desde update_carrito()**.

### Consecuencia:
- `CarritoService._cliente = None` ✅
- Visualización en TicketCarrito sigue mostrando el cliente anterior ❌

---

## 💡 Soluciones Propuestas

### Solución Bug 1: Estandarizar retorno de processors

**Todos los processors deben retornar tupla `(ticket_id, num_ticket)`:**

#### Opción A: Modificar VentaFidelizacionProcessor y DevolucionProcessor
```python
# venta_fidelizacion_processor.py
def process(self, **kwargs):
    proc_res = super().process(**kwargs)
    if isinstance(proc_res, (tuple, list)):
        ticket_id = proc_res[0]
        num_ticket = proc_res[1] if len(proc_res) > 1 else None  # ← Extraer num_ticket
    else:
        ticket_id = proc_res
        num_ticket = None
    
    # ... lógica de fidelización ...
    
    return ticket_id, num_ticket  # ← Retornar tupla
```

```python
# devolucion_processor.py
def process(self, *, carrito_items: List[Dict], resumen: Dict, **kwargs) -> tuple:
    # ... dentro de la transacción ...
    num_ticket = config_service.get_next_ticket_number(cur=cur)
    # ...
    return ticket_id, num_ticket  # ← Retornar tupla
```

#### Opción B: Simplificar en tpv_controller.py
```python
# Asumir SIEMPRE tupla (más limpio)
proc_res = processor.process(**payload)
if isinstance(proc_res, (tuple, list)) and len(proc_res) >= 2:
    ticket_id, num_ticket = proc_res[0], proc_res[1]
else:
    ticket_id = proc_res[0] if isinstance(proc_res, (tuple, list)) else proc_res
    num_ticket = None  # ← Fallback seguro
    
    # Recuperar de BD si es necesario
    if num_ticket is None and ticket_id:
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT num_ticket FROM tickets WHERE id = ?", (ticket_id,))
            row = cursor.fetchone()
            num_ticket = row[0] if row else None
        except Exception:
            logger.exception("Error recuperando num_ticket")
```

**Recomendación:** Opción A (estandarizar processors) - Más limpio y coherente.

---

### Solución Bug 2: Actualizar cliente en update_carrito()

**Añadir sincronización de cliente en `TicketCarrito.update_carrito()`:**

```python
# kool_tpv/utils/widgets/ticket_carrito.py, dentro de update_carrito()
def update_carrito(self):
    """Actualizar display del carrito manteniendo scroll."""
    try:
        # ... código existente ...
        
        # Obtener items del servicio
        items = self.carrito_service.get_items() or []
        
        # ... código de añadir items ...
        
        # NUEVO: Sincronizar cliente visual con el servicio
        try:
            cliente_actual = self.carrito_service.get_cliente()
            self.update_cliente(cliente_actual)  # ← Añadir esta línea
        except Exception:
            logger.exception("Error sincronizando cliente en update_carrito")
        
        # ... resto del código ...
```

**Ubicación exacta:** Después de la línea que añade items, antes de actualizar el resumen financiero.

---

## 📝 Archivos a Modificar

### Bug 1 (Opción A):
1. `kool_tpv/modulos/ticket/venta_fidelizacion_processor.py` - Retornar tupla
2. `kool_tpv/modulos/ticket/devolucion_processor.py` - Retornar tupla

### Bug 2:
1. `kool_tpv/utils/widgets/ticket_carrito.py` - Añadir `update_cliente()` en `update_carrito()`

---

## 🎯 Prioridad

**Ambos bugs son de prioridad ALTA:**
- Bug 1: Afecta UX (mensaje confuso al usuario)
- Bug 2: Afecta integridad de datos visualmente (cliente aparece asociado a venta siguiente)

**Tiempo estimado de implementación:** 10-15 minutos

---

## ✅ Testing Recomendado

### Test Bug 1:
1. Añadir producto al carrito
2. Añadir cliente (activa fidelización)
3. Finalizar con Tarjeta/Efectivo/Web
4. Verificar que diálogo muestre número correcto (ej: `TICKET #2026-0304`)

### Test Bug 2:
1. Añadir producto + cliente
2. Finalizar venta
3. Verificar que zona de cliente muestre "SELECCIONAR CLIENTE..." y "0 pts"
4. Añadir nuevo producto (sin cliente)
5. Verificar que NO aparezca el cliente anterior
