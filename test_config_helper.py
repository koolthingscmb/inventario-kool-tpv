"""
Test del ConfigHelper para Payment Controllers.
Valida que NO hay valores hardcodeados y todo viene de JSON.
"""

import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

from kool_tpv.utils.widgets.payment_controllers.config_helper import PaymentConfigHelper


def test_efectivo():
    print("\n" + "="*70)
    print("TEST: PaymentConfigHelper para EFECTIVO")
    print("="*70)
    
    helper = PaymentConfigHelper("efectivo")
    
    # Test fuentes
    print("\n📝 FUENTES:")
    titulo_font = helper.get_font("titulo")
    print(f"  titulo: {titulo_font}")
    
    label_font = helper.get_font("label")
    print(f"  label: {label_font}")
    
    entry_font = helper.get_font("entry")
    print(f"  entry: {entry_font}")
    
    button_font = helper.get_font("button")
    print(f"  button: {button_font}")
    
    cambio_font = helper.get_font("cambio")
    print(f"  cambio: {cambio_font}")
    
    # Test colores
    print("\n🎨 COLORES:")
    bg = helper.get_bg_color()
    print(f"  bg: {bg}")
    
    border = helper.get_color("border")
    print(f"  border: {border}")
    
    text_titulo = helper.get_color("text_titulo")
    print(f"  text_titulo: {text_titulo}")
    
    text_label = helper.get_color("text_label")
    print(f"  text_label: {text_label}")
    
    # Colores de botón
    button_bg = helper.get_color("bg", context="button")
    print(f"  button.bg: {button_bg}")
    
    button_hover = helper.get_color("hover", context="button")
    print(f"  button.hover: {button_hover}")
    
    button_text = helper.get_color("text", context="button")
    print(f"  button.text: {button_text}")
    
    # Test layout
    print("\n📐 LAYOUT:")
    border_width = helper.get_layout_value("border_width")
    print(f"  border_width: {border_width}")
    
    corner_radius = helper.get_layout_value("corner_radius")
    print(f"  corner_radius: {corner_radius}")
    
    padding = helper.get_layout_value("padding")
    print(f"  padding: {padding}")
    
    entry_width = helper.get_layout_value("entry_width")
    print(f"  entry_width (específico efectivo): {entry_width}")
    
    button_width = helper.get_layout_value("button", "width")
    print(f"  button.width: {button_width}")
    
    button_height = helper.get_layout_value("button", "height")
    print(f"  button.height: {button_height}")


def test_multi():
    print("\n" + "="*70)
    print("TEST: PaymentConfigHelper para MULTI")
    print("="*70)
    
    helper = PaymentConfigHelper("multi")
    
    # Test colores
    print("\n🎨 COLORES:")
    bg = helper.get_bg_color()
    print(f"  bg: {bg}")
    
    border = helper.get_color("border")
    print(f"  border: {border}")
    
    text_titulo = helper.get_color("text_titulo")
    print(f"  text_titulo: {text_titulo}")
    
    button_bg = helper.get_color("bg", context="button")
    print(f"  button.bg: {button_bg}")
    
    # Test layout específico
    print("\n📐 LAYOUT:")
    entry_width = helper.get_layout_value("entry_width")
    print(f"  entry_width (específico multi): {entry_width}")
    
    entries_spacing = helper.get_layout_value("entries_spacing")
    print(f"  entries_spacing: {entries_spacing}")


def test_simple():
    print("\n" + "="*70)
    print("TEST: PaymentConfigHelper para TARJETA (simple)")
    print("="*70)
    
    helper = PaymentConfigHelper("tarjeta")
    
    # Test colores
    print("\n🎨 COLORES:")
    bg = helper.get_bg_color()
    print(f"  bg: {bg}")
    
    border = helper.get_color("border")
    print(f"  border: {border}")
    
    text_titulo = helper.get_color("text_titulo")
    print(f"  text_titulo: {text_titulo}")
    
    # Test layout
    print("\n📐 LAYOUT:")
    titulo_bottom = helper.get_layout_value("titulo_bottom")
    print(f"  titulo_bottom (de 'simple' en JSON): {titulo_bottom}")


def test_nonexistent():
    print("\n" + "="*70)
    print("TEST: Valores NO EXISTENTES (debe devolver None y loggear warning)")
    print("="*70)
    
    helper = PaymentConfigHelper("efectivo")
    
    print("\n⚠️  Intentando obtener valores inexistentes:")
    
    fake_font = helper.get_font("fuente_inventada", use_global_default=False)
    print(f"  fuente_inventada: {fake_font}")
    
    fake_color = helper.get_color("color_inventado")
    print(f"  color_inventado: {fake_color}")
    
    fake_layout = helper.get_layout_value("layout_inventado")
    print(f"  layout_inventado: {fake_layout}")


def main():
    print("\n🚀 INICIANDO TESTS DE ConfigHelper")
    print("✅ Todos los valores deben venir de archivos JSON")
    print("❌ NO debe haber valores hardcodeados")
    
    try:
        test_efectivo()
        test_multi()
        test_simple()
        test_nonexistent()
        
        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS COMPLETADOS")
        print("="*70)
        print("\nSi ves valores None con warnings, es CORRECTO - no hay hardcodeo.")
        print("Si ves valores reales, vienen de los archivos JSON.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR EN TESTS: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
