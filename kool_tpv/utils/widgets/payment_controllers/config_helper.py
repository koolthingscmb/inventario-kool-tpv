"""
ConfigHelper para Payment Controllers.
Centraliza el acceso a configuraciones sin valores hardcodeados.
"""

import logging
from typing import Any, Optional, Dict, Tuple, Union

logger = logging.getLogger(__name__)


class PaymentConfigHelper:
    """
    Helper para manejar configuraciones de payment controllers.
    NO hardcodea ningún valor - todo proviene de archivos JSON.
    """
    
    def __init__(self, config_key: str = "efectivo"):
        """
        Args:
            config_key: Tipo de payment controller ("efectivo", "multi", "tarjeta", "web")
        """
        from . import load_config, norm_color
        
        self.config_key = config_key
        self.norm_color = norm_color
        
        # Cargar configuraciones completas UNA VEZ
        self._colors = load_config("colors_config.json")
        self._fonts = load_config("font_config.json")
        self._layout = load_config("layout_config.json")
        self._button_styles = load_config("button_styles.json")
        
        # Accesos directos a secciones relevantes
        self._pc_colors = self._get_nested(
            self._colors, 
            ["tpv", "payment_controllers", config_key],
            dict_only=True
        )
        
        self._pc_fonts = self._get_nested(
            self._fonts,
            ["modules", "tpv", "payment_controllers"],
            dict_only=True
        )
        
        self._pc_layout = self._get_nested(
            self._layout,
            ["modules", "tpv", "ticket_carrito", "payment_controllers"],
            dict_only=True
        )
        
        self._pc_layout_specific = self._get_nested(
            self._layout,
            ["modules", "tpv", "ticket_carrito", "payment_controllers", config_key],
            dict_only=True
        )
        
        # Acceso a valores default en fonts
        self._default_font = self._fonts.get("default", {})
        
        # Acceso a footer del ticket_carrito (para bg fallback)
        self._footer_colors = self._get_nested(
            self._colors,
            ["tpv", "ticket_carrito", "footer"],
            dict_only=True
        )
    
    def _get_nested(self, data: Dict, keys: list, dict_only: bool = False) -> Any:
        """
        Navega estructura anidada de forma segura.
        
        Args:
            data: Diccionario base
            keys: Lista de claves a navegar
            dict_only: Si True, solo retorna dicts; útil para inicialización
            
        Returns:
            Valor en la posición indicada, o {} si dict_only=True y no existe,
            o None si dict_only=False y no existe
        """
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, {} if dict_only else None)
                if result is None and not dict_only:
                    return None
            else:
                return {} if dict_only else None
        
        if dict_only:
            return result if isinstance(result, dict) else {}
        return result
    
    def get_font(
        self, 
        font_type: str, 
        use_global_default: bool = True
    ) -> Optional[Tuple[str, int, Optional[str]]]:
        """
        Obtener tupla de fuente para el tipo especificado.
        
        Args:
            font_type: Tipo de fuente ("titulo", "label", "entry", "button", "cambio", "error")
            use_global_default: Si es True y no encuentra la fuente específica, usa "default"
            
        Returns:
            Tupla (family, size) o (family, size, weight) si weight existe
            None si no encuentra configuración
        """
        # Buscar en payment_controllers específico
        font_data = self._pc_fonts.get(font_type, {})
        
        # Si no existe, intentar con default global (si se permite)
        if not font_data and use_global_default:
            font_data = self._default_font
            if not font_data:
                logger.warning(
                    f"No se encontró configuración de fuente para '{font_type}' "
                    f"ni 'default' en font_config.json"
                )
                return None
        
        if not font_data:
            logger.warning(
                f"No se encontró configuración de fuente para '{font_type}' "
                f"en payment_controllers"
            )
            return None
        
        family = font_data.get("family")
        size = font_data.get("size")
        weight = font_data.get("weight")
        
        if not family or not size:
            logger.error(
                f"Configuración de fuente '{font_type}' incompleta: "
                f"family={family}, size={size}"
            )
            return None
        
        if weight:
            return (family, size, weight)
        return (family, size)
    
    def get_color(self, color_key: str, context: Optional[str] = None) -> Optional[str]:
        """
        Obtener color normalizado.
        
        Args:
            color_key: Clave del color ("bg", "border", "text_titulo", etc.)
            context: Contexto adicional ("button" para navegar a self._pc_colors["button"][color_key])
            
        Returns:
            Color normalizado o None si no se encuentra
        """
        if context:
            # Navegar a subsección (ej: "button")
            source = self._pc_colors.get(context, {})
        else:
            source = self._pc_colors
        
        raw_value = source.get(color_key)
        
        if raw_value is None:
            logger.warning(
                f"No se encontró color '{color_key}' "
                f"{'en contexto ' + context if context else ''} "
                f"para payment_controller '{self.config_key}'"
            )
            return None
        
        return self.norm_color(raw_value)
    
    def get_layout_value(self, *keys) -> Optional[Any]:
        """
        Obtener valor de layout con navegación flexible.
        
        Args:
            *keys: Secuencia de claves para navegar
            
        Returns:
            Valor encontrado o None
            
        Examples:
            helper.get_layout_value("border_width")  # Busca en payment_controllers general
            helper.get_layout_value("entry_width")   # Busca en payment_controllers.{config_key}
            helper.get_layout_value("button", "width")  # Busca en payment_controllers.button.width
        """
        # Primero intentar en la sección específica del tipo (efectivo, multi, etc.)
        result = self._get_nested(self._pc_layout_specific, list(keys), dict_only=False)
        
        # Si no encontró, buscar en la sección general
        if result is None:
            result = self._get_nested(self._pc_layout, list(keys), dict_only=False)
        
        if result is None:
            logger.warning(
                f"No se encontró valor de layout para {'.'.join(keys)} "
                f"en payment_controller '{self.config_key}'"
            )
            return None
        
        return result
    
    def get_bg_color(self) -> Optional[str]:
        """
        Obtener color de fondo del payment controller.
        Si es transparente, devuelve el bg del footer del ticket_carrito.
        
        Returns:
            Color normalizado o None
        """
        raw_bg = (self._pc_colors.get("bg", "") or "").strip()
        
        # Si es transparente o vacío, usar footer
        if raw_bg.lower() in ("transparent", "none", ""):
            footer_bg = self._footer_colors.get("bg")
            if footer_bg is None:
                logger.warning(
                    f"bg de payment_controller '{self.config_key}' es transparente "
                    f"pero no se encontró bg del footer"
                )
                return None
            return self.norm_color(footer_bg)
        
        return self.norm_color(raw_bg)
    
    def get_button_style(self, button_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtener estilos de botón desde button_styles.json.
        
        Args:
            button_key: Clave específica del botón en button_styles.json
            
        Returns:
            Diccionario con estilos del botón
        """
        if button_key:
            return self._button_styles.get(button_key, {})
        return {}
    
    def get_all_colors(self) -> Dict[str, Any]:
        """
        Obtener diccionario completo de colores del payment controller.
        Útil para debugging.
        """
        return self._pc_colors.copy()
    
    def get_all_layout(self) -> Dict[str, Any]:
        """
        Obtener diccionario completo de layout del payment controller.
        Útil para debugging.
        """
        return {
            "general": self._pc_layout.copy(),
            "specific": self._pc_layout_specific.copy()
        }
