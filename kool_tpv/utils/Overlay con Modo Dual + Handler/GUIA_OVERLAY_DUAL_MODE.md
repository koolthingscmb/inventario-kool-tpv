Guía: Overlay con Modo Dual + Handler

¿Qué es esto?

Un overlay que tiene 2 modos visuales diferentes dentro de la misma ventana:

    Modo 1: Vista inicial (ej: lista de tickets pendientes)
    Modo 2: Vista alternativa (ej: histórico de cierres)

Al cambiar de modo:

    Cambia el título
    Cambia las columnas del tree
    Oculta/muestra botones diferentes
    Crea y muestra el VisorNegro automáticamente
    Al pulsar ESC en Modo 2 → vuelve a Modo 1 (NO cierra)

¿Cuándo usarlo?

Cuando un botón necesita mostrar dos vistas relacionadas sin abrir ventanas separadas.

Ejemplos:

    Stock → Consulta de ventas de un producto
    Cierres → Histórico de cierres
    Clientes → Historial de compras de un cliente
    Productos → Movimientos de stock de un producto

Arquitectura

MiUI (hereda de BaseUI)
├── self.modo = 'modo1' o 'modo2'
├── self.columns_config_modo1 = [...]
├── self.columns_config_modo2 = [...]
├── self._mi_handler = MiHandler(self)
│
├── _cambiar_modo(nuevo_modo)
│   ├── if modo1: _configurar_modo1()
│   └── if modo2: _mi_handler.configurar_modo2()
│
├── hide() override
│   ├── if modo2: _cambiar_modo('modo1')  # NO cierra
│   └── else: super().hide()              # Cierra
│
└── Botón que llama a _cambiar_modo('modo2')


MiHandler (clase separada)
├── __init__(parent)
├── load_modo2(termino)
├── render_modo2(items)
├── configurar_modo2()  ← CREA Y MUESTRA VisorNegro aquí
└── on_accion_especial()

Plain text
Archivos necesarios

    mi_base_ui.py - Hereda de SelectionOverlayTemplate
    mi_ui.py - Clase principal con los dos modos
    mi_handler.py - Handler del modo secundario

Ver ejemplos completos

    stock_ui.py + consulta_stock_ui.py (ConsultaStockHandler)
    cierre_ui.py + cierre_historico_ui.py (HistoricoHandler)
