import json
import logging
import re
import requests
from typing import Any, Dict, List, Optional, Tuple
from .base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

class OpenAIService(BaseAIService):
    """Adaptador de chat para OpenAI y Gemini (endpoint compatible OpenAI).

    Gemini habla el mismo protocolo que OpenAI
    (generativelanguage.googleapis.com/v1beta/openai/), así que el proveedor
    solo cambia la dirección, la llave y el modelo. Admite varias llaves de
    Gemini: si una se queda sin cuota o falla, prueba la siguiente. Nunca se
    registran las llaves en los logs, solo su posición.
    """

    API_URL_OPENAI = "https://api.openai.com/v1/chat/completions"
    API_URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

    # Modelos por proveedor para el desplegable de CONFIG (la elección va a BD)
    MODELOS = {
        "openai": ["gpt-4o-mini", "gpt-4o"],
        "gemini": ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"],
    }
    MODELO_DEFECTO = {"openai": "gpt-4o-mini", "gemini": "gemini-3.6-flash"}

    # Puntero en memoria para rotación equitativa (round-robin) entre llamadas
    _turno_gemini: int = 0
    LETRAS_CLAVES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    @classmethod
    def get_proxima_letra_gemini(cls, num_claves: int) -> str:
        """Devuelve la letra de la clave que se usará en la siguiente llamada."""
        if num_claves <= 0:
            return "A"
        idx = cls._turno_gemini % num_claves
        return cls.LETRAS_CLAVES[idx] if idx < len(cls.LETRAS_CLAVES) else str(idx + 1)

    @classmethod
    def desde_config(cls, cfg: Dict[str, Any]) -> Tuple[Optional["OpenAIService"], Optional[str]]:
        """Construye el servicio con proveedor, llave(s) y modelo de CONFIG.

        Devuelve (servicio, None) o (None, mensaje de error).
        """
        proveedor = str(cfg.get("ia_proveedor") or "openai").strip().lower() or "openai"
        if proveedor not in cls.MODELOS:
            proveedor = "openai"
        modelo = (cfg.get("ia_model") or "").strip() or cls.MODELO_DEFECTO[proveedor]
        if proveedor == "gemini":
            claves = cls.claves_gemini_desde_texto(cfg.get("ia_gemini_api_keys") or "")
            if not claves:
                return None, "Falta la API key de Gemini en Shopify CONFIG > IA."
            return cls(claves[0], modelo, proveedor="gemini", claves_extra=claves[1:]), None
        api_key = (cfg.get("ia_api_key") or "").strip()
        if not api_key:
            return None, "Falta la OpenAI API Key en Shopify CONFIG > IA."
        return cls(api_key, modelo), None

    @staticmethod
    def claves_gemini_desde_texto(texto: str) -> List[str]:
        """Llaves separadas por líneas, comas o punto y coma; sin vacías ni
        duplicadas. Orden estable: la primera es la preferente."""
        vistos: List[str] = []
        for trozo in re.split(r"[\n,;]+", texto or ""):
            k = trozo.strip()
            if k and k not in vistos:
                vistos.append(k)
        return vistos

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 proveedor: str = "openai", claves_extra: Optional[List[str]] = None):
        self.api_key = api_key
        self.model = model
        self.proveedor = (proveedor or "openai").strip().lower()
        self.claves = [api_key] + [k for k in (claves_extra or []) if k and k != api_key]

    @property
    def API_URL(self) -> str:
        return self.API_URL_GEMINI if self.proveedor == "gemini" else self.API_URL_OPENAI

    # ---------- llamada con rotación de llaves ----------

    def _traducir_error(self, respuesta) -> str:
        """Errores frecuentes con mensaje claro; el resto, tal cual (recortado)."""
        cuerpo = respuesta.text or ""
        if self.proveedor == "openai" and ("insufficient_quota" in cuerpo or "credit_balance_exhausted" in cuerpo):
            return ("La IA no tiene saldo: añade créditos en tu cuenta de OpenAI "
                    "(platform.openai.com > Settings > Billing)")
        if self.proveedor == "gemini":
            if respuesta.status_code == 429 or "RESOURCE_EXHAUSTED" in cuerpo:
                return ("Gemini llegó a su límite (plan gratis): espera un rato "
                        "o añade otra llave en CONFIG > IA")
            if respuesta.status_code == 401 or "API_KEY_INVALID" in cuerpo:
                return "Llave de Gemini no válida: revísala en CONFIG > IA"
        return f"{self.proveedor} {respuesta.status_code}: {cuerpo[:300]}"

    def _post(self, data: Dict[str, Any], timeout: int) -> Tuple[Optional[requests.Response], Optional[str], Optional[str]]:
        """POST con rotación de llaves: rota equitativamente (round-robin) en Gemini
        y si una falla, prueba inmediatamente la siguiente de la lista.
        Devuelve (respuesta_200, None, letra_usada) o (None, error_traducido, None)."""
        if not self.claves:
            return None, "API Key no proporcionada", None

        num_claves = len(self.claves)
        if self.proveedor == "gemini" and num_claves > 1:
            inicio = OpenAIService._turno_gemini % num_claves
            OpenAIService._turno_gemini = (inicio + 1) % num_claves
            orden_claves = []
            for i in range(num_claves):
                idx = (inicio + i) % num_claves
                letra = self.LETRAS_CLAVES[idx] if idx < len(self.LETRAS_CLAVES) else str(idx + 1)
                orden_claves.append((idx + 1, self.claves[idx], letra))
        else:
            orden_claves = [(i + 1, clave, self.LETRAS_CLAVES[i] if self.proveedor == "gemini" and i < len(self.LETRAS_CLAVES) else "") for i, clave in enumerate(self.claves)]

        ultimo_error = "Sin llaves configuradas"
        for orden, (indice, clave, letra_clave) in enumerate(orden_claves, start=1):
            headers = {"Authorization": f"Bearer {clave}", "Content-Type": "application/json"}
            try:
                respuesta = requests.post(self.API_URL, headers=headers, json=data, timeout=timeout)
            except requests.exceptions.Timeout:
                logger.warning("IA: timeout llamando a %s (llave %s, intento %d de %d, %ss)",
                               self.API_URL, letra_clave or f"#{indice}", orden, len(self.claves), timeout)
                ultimo_error = "Tiempo de espera agotado al conectar con la IA"
                continue
            except Exception as e:
                ultimo_error = f"Conexión con la IA: {e}"
                logger.exception("Error llamando a la IA (llave %s, intento %d de %d)", letra_clave or f"#{indice}", orden, len(self.claves))
                continue
            if respuesta.status_code == 200:
                return respuesta, None, letra_clave
            ultimo_error = self._traducir_error(respuesta)
            logger.warning("IA: llave %s (intento %d de %d) falló (%s)", letra_clave or f"#{indice}", orden, len(self.claves), ultimo_error)
        return None, ultimo_error, None

    def _payload(self, messages: List[Dict[str, str]], json_mode: bool = False,
                 max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Cuerpo común. temperature está deprecada en los Gemini 3.x: se omite."""
        data: Dict[str, Any] = {"model": self.model, "messages": messages}
        if self.proveedor != "gemini":
            data["temperature"] = 0.7
        if json_mode:
            data["response_format"] = {"type": "json_object"}
        if max_tokens:
            data["max_tokens"] = max_tokens
        return data

    # ---------- API pública ----------

    def test_connection(self) -> Tuple[bool, str]:
        """Prueba la conexión con el proveedor configurado."""
        data = self._payload(
            [{"role": "user", "content": "Responde solo con la palabra 'Hola'"}],
            max_tokens=100)
        respuesta, err, _ = self._post(data, timeout=30)
        if err:
            return False, err
        try:
            return True, respuesta.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.exception("Respuesta inesperada en el test de conexión de IA")
            return False, str(e)

    def generate_json(self, user_prompt: str, system_content: str = "") -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """Llamada genérica al chat que espera un JSON como respuesta.

        Devuelve (dict, None, letra_clave) o (None, mensaje de error, None).
        """
        if not self.claves:
            return None, "API Key no proporcionada", None
        messages: List[Dict[str, str]] = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_prompt})
        respuesta, err, letra = self._post(self._payload(messages, json_mode=True), timeout=60)
        if err:
            return None, err, None
        try:
            content = respuesta.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?", "", content).strip()
                content = re.sub(r"```$", "", content).strip()
            return json.loads(content), None, letra
        except json.JSONDecodeError as e:
            logger.error("JSON inválido devuelto por la IA: %s", e)
            return None, f"JSON inválido de la IA: {e}", None
        except Exception as e:
            logger.exception("Error procesando la respuesta de la IA")
            return None, str(e), None

    def generate_text(self, user_prompt: str, json_mode: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Llamada al chat que devuelve el texto de la respuesta."""
        data = self._payload([{"role": "user", "content": user_prompt}], json_mode=json_mode)
        respuesta, err, _ = self._post(data, timeout=60)
        if err:
            return None, err
        try:
            return respuesta.json()["choices"][0]["message"]["content"].strip(), None
        except Exception as e:
            logger.exception("Error procesando la respuesta de la IA")
            return None, str(e)

    def generate_seo(self, source_data: Dict[str, Any], product_name: str, prompt_template: str, seo_rules: str = "", web_data: str = "") -> Optional[Dict[str, str]]:
        """Genera campos SEO optimizados para Shopify usando la IA configurada."""
        if not self.claves or not prompt_template:
            return None

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

        respuesta, err, _ = self._post(self._payload([
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ], json_mode=True), timeout=30)
        if err or respuesta is None:
            return None
        try:
            content = respuesta.json()["choices"][0]["message"]["content"].strip()
            # Intentar limpiar posibles bloques de código markdown
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return json.loads(content)
        except Exception:
            logger.exception("Error generando SEO con la IA")
            return None
