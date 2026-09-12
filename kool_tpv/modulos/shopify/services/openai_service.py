import json
import logging
import requests
from typing import Optional, Tuple, Dict, Any
from .base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

class OpenAIService(BaseAIService):
    """Servicio para interactuar con la API de OpenAI."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba la conexión con OpenAI enviando un mensaje simple.
        
        Returns:
            Tuple[bool, str]: (Éxito, Mensaje de respuesta o error)
        """
        if not self.api_key:
            return False, "API Key no proporcionada"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Responde solo con la palabra 'Hola'"}
            ],
            "max_tokens": 5
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                return True, content
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("message", error_msg)
                except:
                    pass
                logger.error(f"Error en test de conexión OpenAI: {error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            return False, "Tiempo de espera agotado al conectar con OpenAI"
        except Exception as e:
            logger.exception("Error inesperado en test de conexión OpenAI")
            return False, str(e)

    def generate_seo(self, source_data: Dict[str, Any], product_name: str, prompt_template: str, seo_rules: str = "", web_data: str = "") -> Optional[Dict[str, str]]:
        """Genera campos SEO optimizados para Shopify usando OpenAI."""
        if not self.api_key or not prompt_template:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Aplicar los datos a la plantilla del prompt
        try:
            prompt = prompt_template.format(
                product_name=product_name,
                source_data=json.dumps(source_data, ensure_ascii=False)
            )
        except Exception:
            logger.exception("Error formateando el prompt template")
            return None

        system_content = "Eres un asistente experto en SEO para Shopify que solo responde en formato JSON válido."
        
        if seo_rules:
            system_content += f"\n\nDebes seguir estrictamente estas REGLAS DE LA TIENDA:\n{seo_rules}"
            
        if web_data:
            system_content += f"\n\nDATOS VERIFICADOS DE INTERNET (Prioridad para veracidad):\n{web_data}"

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Intentar limpiar posibles bloques de código markdown
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                
                return json.loads(content)
            else:
                logger.error(f"Error OpenAI generate_seo: {response.status_code} - {response.text}")
                return None

        except Exception:
            logger.exception("Error generado SEO con OpenAI")
            return None
