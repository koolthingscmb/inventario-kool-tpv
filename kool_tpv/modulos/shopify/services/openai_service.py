import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class OpenAIService:
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
