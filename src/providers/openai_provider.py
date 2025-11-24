"""
OpenAI Provider - Implementación de ILLMProvider para OpenAI

Implementa la interface ILLMProvider usando LiteLLM para llamadas a OpenAI.
Incluye manejo robusto de errores, parsing de JSON y reintentos.
"""

import json
import re
import time
from typing import Dict, Any, Optional
from dataclasses import replace

from ..interfaces.llm_provider import (
    ILLMProvider,
    LLMRequest,
    LLMResponse,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderAuthError,
    LLMProviderRateLimitError
)

try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class OpenAIProvider:
    """
    Provider para OpenAI usando LiteLLM.

    Características:
    - Soporte para GPT-4, GPT-3.5 y otros modelos OpenAI
    - Parsing robusto de JSON con fallbacks
    - Limpieza automática de markdown wrappers
    - Logging detallado de llamadas
    - Manejo de errores con reintentos
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "openai/gpt-4o",
        timeout: int = 60,
        max_retries: int = 3,
        enable_logging: bool = True
    ):
        """
        Inicializa el provider de OpenAI.

        Args:
            api_key: API key de OpenAI (si no se provee, usa variable de entorno)
            default_model: Modelo por defecto (ej: "openai/gpt-4o", "openai/gpt-3.5-turbo")
            timeout: Timeout en segundos para llamadas
            max_retries: Número máximo de reintentos en caso de error
            enable_logging: Habilitar logging de llamadas
        """
        if not LITELLM_AVAILABLE:
            raise LLMProviderError(
                "LiteLLM no está instalado. Instalar con: pip install litellm"
            )

        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_logging = enable_logging

    def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Genera una completion dado un request.

        Args:
            request: Objeto LLMRequest con prompt y parámetros

        Returns:
            LLMResponse con el contenido generado

        Raises:
            LLMProviderError: Si hay error en la llamada
        """
        model = request.model or self.default_model

        if self.enable_logging:
            print(f"[OpenAI] Llamada iniciada - Model: {model}, Max tokens: {request.max_tokens}")

        start_time = time.time()

        # Construir mensajes
        messages = []
        if request.system_message:
            messages.append({"role": "system", "content": request.system_message})
        messages.append({"role": "user", "content": request.prompt})

        # Parámetros de llamada
        call_params = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }

        if request.stop_sequences:
            call_params["stop"] = request.stop_sequences

        # Intentar llamada con reintentos
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = completion(**call_params)
                duration = time.time() - start_time

                content = response.choices[0].message.content
                if not content:
                    raise LLMProviderError("OpenAI devolvió respuesta vacía")

                if self.enable_logging:
                    print(f"[OpenAI] Respuesta recibida en {duration:.2f}s ({len(content)} chars)")

                # Extraer tokens usados
                usage = response.get('usage', {})
                tokens_used = {
                    "prompt": usage.get('prompt_tokens', 0),
                    "completion": usage.get('completion_tokens', 0),
                    "total": usage.get('total_tokens', 0)
                }

                return LLMResponse(
                    content=content,
                    model=model,
                    tokens_used=tokens_used,
                    finish_reason=response.choices[0].finish_reason,
                    metadata={
                        "duration": duration,
                        "attempt": attempt + 1
                    }
                )

            except Exception as e:
                last_error = self._classify_error(e)

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    if self.enable_logging:
                        print(f"[OpenAI] Error en intento {attempt + 1}, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise last_error

        raise last_error or LLMProviderError("Error desconocido en llamada a OpenAI")

    def complete_json(self, request: LLMRequest) -> Dict[str, Any]:
        """
        Genera una completion en formato JSON con parsing robusto.

        Args:
            request: Objeto LLMRequest con prompt y parámetros

        Returns:
            Dict parseado del JSON generado

        Raises:
            LLMProviderError: Si hay error en la llamada o parsing
        """
        response = self.complete(request)
        content = response.content.strip()

        # Limpiar markdown wrapper si existe
        content_cleaned = self._clean_markdown_wrapper(content)

        # Intentar parsear JSON directamente
        try:
            return json.loads(content_cleaned)
        except json.JSONDecodeError as e:
            # Fallback: buscar JSON con regex
            parsed_json = self._extract_json_with_regex(content_cleaned)
            if parsed_json is not None:
                return parsed_json

            # Si todo falla, lanzar error con contenido original
            raise LLMProviderError(
                f"No se pudo parsear JSON: {str(e)}\n"
                f"Contenido: {content_cleaned[:200]}..."
            )

    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna información del modelo configurado.

        Returns:
            Dict con información del modelo
        """
        return {
            "provider": "OpenAI",
            "default_model": self.default_model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "litellm_available": LITELLM_AVAILABLE
        }

    def is_available(self) -> bool:
        """
        Verifica si el proveedor está disponible.

        Returns:
            True si LiteLLM está disponible
        """
        return LITELLM_AVAILABLE

    # ==========================================
    # MÉTODOS PRIVADOS
    # ==========================================

    def _clean_markdown_wrapper(self, content: str) -> str:
        """
        Limpia markdown code blocks que envuelven JSON.

        Args:
            content: Contenido a limpiar

        Returns:
            Contenido sin markdown wrapper
        """
        content = content.strip()

        # Caso 1: ```json ... ```
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
            if content.endswith('```'):
                content = content[:-3]  # Remove ```
            return content.strip()

        # Caso 2: ``` ... ```
        if content.startswith('```'):
            lines = content.split('\n')
            if len(lines) > 2 and lines[-1].strip() == '```':
                return '\n'.join(lines[1:-1]).strip()

        return content

    def _extract_json_with_regex(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Intenta extraer JSON usando regex como fallback.

        Args:
            content: Contenido donde buscar JSON

        Returns:
            Dict parseado o None si no se encuentra
        """
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Objetos anidados
            r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'  # Arrays anidados
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue

        return None

    def _classify_error(self, error: Exception) -> LLMProviderError:
        """
        Clasifica un error genérico en el tipo específico de LLMProviderError.

        Args:
            error: Excepción original

        Returns:
            LLMProviderError apropiado
        """
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return LLMProviderTimeoutError(f"Timeout en llamada a OpenAI: {error}")

        if "auth" in error_str or "api key" in error_str or "unauthorized" in error_str:
            return LLMProviderAuthError(f"Error de autenticación con OpenAI: {error}")

        if "rate limit" in error_str or "429" in error_str:
            return LLMProviderRateLimitError(f"Rate limit excedido en OpenAI: {error}")

        return LLMProviderError(f"Error en llamada a OpenAI: {error}")
