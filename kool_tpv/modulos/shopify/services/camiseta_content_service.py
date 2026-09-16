import json
import logging
import re
import unicodedata
from typing import Dict, Any, Optional, Tuple

import requests

from .shopify_config_service import ShopifyConfigService
from .camiseta_prompts import (
    PROMPT_SEO_DESCRIPCION, PROMPT_BODY_HTML, PROMPT_TAGS,
    PLANTILLA_HTML, PLANTILLA_SEO_TITLE, BOTON_GENERO, CDN_BASE_BOTONES,
    INSTRUCCIONES_GENERO, CORTE_PRODUCTO, TONO_POR_DEFECTO,
    GENEROS_CAMISETA, LINK_GUIA_TALLAS,
)
from ..shopify_prompts_repository import ShopifyPromptsRepository

logger = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def slugify_diseno(titulo: str) -> str:
    """Slug estilo GAS: minúsculas, sin acentos, sin |, espacios a guiones."""
    texto = unicodedata.normalize("NFKD", titulo.lower().strip())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("|", "")
    texto = re.sub(r"[^a-z0-9\s-]", "", texto).strip()
    return re.sub(r"\s+", "-", texto)


class CamisetaContentService:
    """Genera los textos de la camiseta con OpenAI usando los prompts de la
    tabla shopify_prompts (port exacto del Google Apps Script)."""

    def __init__(self, db):
        self.db = db
        self.config_service = ShopifyConfigService(db)
        self.prompts_repo = ShopifyPromptsRepository(db)

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    def _llamar_ia(self, prompt: str, json_mode: bool = False) -> Tuple[Optional[str], Optional[str]]:
        cfg = self.config_service.get_config()
        api_key, model = cfg.get("ia_api_key"), cfg.get("ia_model") or "gpt-4o-mini"
        if not api_key:
            return None, "Falta la OpenAI API Key en CONFIG > IA"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(
                OPENAI_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
        except Exception as e:
            return None, f"Conexión OpenAI: {e}"

        if resp.status_code != 200:
            return None, f"OpenAI {resp.status_code}: {resp.text[:300]}"

        return resp.json()["choices"][0]["message"]["content"].strip(), None

    def _get_prompt(self, clave: str, default: str) -> str:
        """Prompt desde la tabla; si no existe, el original del script."""
        row = self.prompts_repo.get_prompt(clave)
        return (row or {}).get("texto") or default

    # ------------------------------------------------------------------
    # Generación
    # ------------------------------------------------------------------

    def generar_tags(self, titulo_base: str) -> Tuple[Optional[str], Optional[str]]:
        """Genera la lista de tags (prompt nuevo, editable en IA PROMPTS)."""
        prompt = self._get_prompt("camiseta_tags", PROMPT_TAGS)
        prompt = prompt.replace("{titulo_base}", titulo_base)
        texto, err = self._llamar_ia(prompt)
        if err:
            return None, err
        return texto.strip(), None

    def generar_seo_descripcion(self, titulo_base: str, tags: str, beneficio: str) -> Tuple[Optional[str], Optional[str]]:
        """Meta descripción (máx 155 chars) - port de generarSeoDescription del GAS."""
        prompt = self._get_prompt("camiseta_seo", PROMPT_SEO_DESCRIPCION)
        prompt = (prompt
                  .replace("{titulo_base}", titulo_base)
                  .replace("{tags}", tags)
                  .replace("{beneficio}", beneficio))
        texto, err = self._llamar_ia(prompt)
        if err:
            return None, err
        return texto.strip('"').strip(), None

    def generar_body(self, genero: str, titulo_base: str, tags: str, beneficio: str,
                     tono: str = "") -> Tuple[Optional[Dict], Optional[str]]:
        """JSON de bloques para un género - port de generarBodyHtml del GAS."""
        prompt = self._get_prompt("camiseta_body", PROMPT_BODY_HTML)
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        prompt = (prompt
                  .replace("{genero}", genero)
                  .replace("{titulo_base}", titulo_base)
                  .replace("{tono}", tono or TONO_POR_DEFECTO)
                  .replace("{instrucciones_genero}", INSTRUCCIONES_GENERO.get(genero, ""))
                  .replace("{tags}", tags)
                  .replace("{beneficio}", beneficio)
                  .replace("{tags_top3}", ", ".join(tags_list[:3])))
        texto, err = self._llamar_ia(prompt, json_mode=True)
        if err:
            return None, err
        try:
            if texto.startswith("```"):
                texto = texto.strip("`")
                if texto.startswith("json"):
                    texto = texto[4:]
            return json.loads(texto), None
        except json.JSONDecodeError as e:
            return None, f"JSON inválido de la IA: {e}"

    def generar_todo(self, titulo_base: str, tags: str, beneficio: str,
                     tono: str = "") -> Dict[str, Any]:
        """Genera todo el contenido de golpe: SEO desc + body por género."""
        resultado = {"seo_desc": None, "bodies": {}, "errores": []}

        seo, err = self.generar_seo_descripcion(titulo_base, tags, beneficio)
        if err:
            resultado["errores"].append(f"SEO desc: {err}")
        else:
            resultado["seo_desc"] = seo

        for genero in GENEROS_CAMISETA:
            body, err = self.generar_body(genero, titulo_base, tags, beneficio, tono)
            if err:
                resultado["errores"].append(f"Body {genero}: {err}")
            else:
                resultado["bodies"][genero] = body

        return resultado

    # ------------------------------------------------------------------
    # Montaje del HTML final (plantilla editable + estructura fija)
    # ------------------------------------------------------------------

    def seo_title_for(self, titulo: str, genero: str) -> str:
        """SEO title con el patrón del script: {titulo} | {genero} | {marca}."""
        plantilla = self._get_prompt("camiseta_seo_title", PLANTILLA_SEO_TITLE)
        marca = self.config_service.get_config().get("marca") or "Kool Things"
        return (plantilla
                .replace("{titulo}", titulo)
                .replace("{genero}", genero)
                .replace("{marca}", marca))

    def montar_html(self, body_json: Dict[str, str], genero: str, titulo_base: str) -> str:
        """Ensambla el descriptionHtml final usando la plantilla editable
        'camiseta_html' (port exacto del GAS: strongs, características,
        FANART, botones de género y footer de envíos)."""
        cfg = self.config_service.get_config()
        plantilla = self._get_prompt("camiseta_html", PLANTILLA_HTML)
        cdn = cfg.get("botones_cdn") or CDN_BASE_BOTONES
        link_guia = cfg.get("link_guia") or LINK_GUIA_TALLAS
        slug = slugify_diseno(titulo_base)

        botones = "".join(
            BOTON_GENERO
            .replace("{handle}", f"{slug}-{g.lower()}")
            .replace("{cdn_base}", cdn)
            .replace("{genero}", g)
            .replace("{genero_upper}", g.upper())
            for g in GENEROS_CAMISETA if g != genero
        )

        html = plantilla
        for clave, valor in body_json.items():
            html = html.replace("{" + clave + "}", valor or "")
        return (html
                .replace("{corte}", CORTE_PRODUCTO.get(genero, ""))
                .replace("{link_guia}", link_guia)
                .replace("{botones_html}", botones)
                .strip())
