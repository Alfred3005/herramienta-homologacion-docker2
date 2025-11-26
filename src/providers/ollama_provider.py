"""
Ollama Provider - Implementación de ILLMProvider para Ollama Local

Implementa la interface ILLMProvider usando LiteLLM para llamadas a Ollama.
Optimizado para modelos locales pequeños (1B-4B) con soporte para Phi-3.5 Mini.
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


class OllamaProvider:
    """
    Provider para Ollama usando LiteLLM.

    Características:
    - Soporte para modelos locales (Phi-3.5, Llama, Qwen, etc.)
    - Parsing robusto de JSON con fallbacks
    - Limpieza automática de markdown wrappers
    - Logging detallado de llamadas
    - Manejo de errores con reintentos
    - Optimizado para inferencia local en GPU limitada
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "phi3.5",
        timeout: int = 120,  # Mayor timeout para modelos locales
        max_retries: int = 2,  # Menos reintentos (modelo local no tiene rate limits)
        enable_logging: bool = True
    ):
        """
        Inicializa el provider de Ollama.

        Args:
            base_url: URL base de Ollama (default: http://localhost:11434)
            default_model: Modelo por defecto (ej: "phi3.5", "llama3.2", "qwen2.5")
            timeout: Timeout en segundos para llamadas (mayor para modelos locales)
            max_retries: Número máximo de reintentos en caso de error
            enable_logging: Habilitar logging de llamadas
        """
        if not LITELLM_AVAILABLE:
            raise LLMProviderError(
                "LiteLLM no está instalado. Instalar con: pip install litellm"
            )

        self.base_url = base_url
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

        # Formato para Ollama en LiteLLM: "ollama/nombre_modelo"
        if not model.startswith("ollama/"):
            model = f"ollama/{model}"

        if self.enable_logging:
            print(f"[Ollama] Llamada iniciada - Model: {model}, Max tokens: {request.max_tokens}")
            print(f"[Ollama] Base URL: {self.base_url}")

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
            "temperature": request.temperature,
            "api_base": self.base_url,
            "timeout": self.timeout
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
                    raise LLMProviderError("Ollama devolvió respuesta vacía")

                if self.enable_logging:
                    print(f"[Ollama] Respuesta recibida en {duration:.2f}s ({len(content)} chars)")

                # Extraer tokens usados (Ollama provee esto)
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
                        "attempt": attempt + 1,
                        "base_url": self.base_url
                    }
                )

            except Exception as e:
                last_error = self._classify_error(e)

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    if self.enable_logging:
                        print(f"[Ollama] Error en intento {attempt + 1}, reintentando en {wait_time}s...")
                        print(f"[Ollama] Error: {str(e)}")
                    time.sleep(wait_time)
                else:
                    raise last_error

        raise last_error or LLMProviderError("Error desconocido en llamada a Ollama")

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
        # Agregar instrucción explícita para JSON en el prompt
        original_prompt = request.prompt
        if "JSON" not in original_prompt and "json" not in original_prompt:
            enhanced_prompt = (
                f"{original_prompt}\n\n"
                "IMPORTANTE: Responde ÚNICAMENTE con un objeto JSON válido. "
                "No incluyas explicaciones ni texto adicional."
            )
            request = replace(request, prompt=enhanced_prompt)

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
            if self.enable_logging:
                print(f"[Ollama] Error parseando JSON. Contenido: {content_cleaned[:500]}")

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
            "provider": "Ollama (Local)",
            "default_model": self.default_model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "litellm_available": LITELLM_AVAILABLE
        }

    def is_available(self) -> bool:
        """
        Verifica si el proveedor está disponible.

        Returns:
            True si LiteLLM está disponible y Ollama responde
        """
        if not LITELLM_AVAILABLE:
            return False

        # Intentar una llamada simple para verificar conectividad
        try:
            test_request = LLMRequest(
                prompt="test",
                max_tokens=10,
                temperature=0.1
            )
            self.complete(test_request)
            return True
        except:
            return False

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
        Mejorado para manejar JSON truncado por modelos pequeños como Phi-3.5.

        Args:
            content: Contenido donde buscar JSON

        Returns:
            Dict parseado o None si no se encuentra
        """
        # Método 1: Buscar desde primer '{' hasta el último '}' válido
        try:
            first_brace = content.find('{')
            if first_brace != -1:
                # Encontrar el último '}' y trabajar hacia atrás
                for i in range(len(content) - 1, first_brace, -1):
                    if content[i] == '}':
                        candidate = content[first_brace:i+1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            # Intentar reparar JSON truncado
                            repaired = self._repair_truncated_json(candidate)
                            if repaired:
                                try:
                                    return json.loads(repaired)
                                except:
                                    continue
        except:
            pass

        # Método 2: Regex patterns (fallback original)
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

    def _repair_truncated_json(self, json_str: str) -> Optional[str]:
        """
        Intenta reparar JSON truncado/malformado agregando comillas, paréntesis y llaves faltantes.
        Optimizado para manejar errores de Phi-3.5 Mini.

        Args:
            json_str: String de JSON potencialmente truncado

        Returns:
            String de JSON reparado o None si no se puede reparar
        """
        try:
            original = json_str
            lines = json_str.strip().split('\n')

            # Paso 1: Reparar última línea incompleta
            last_line = lines[-1].strip()
            if last_line and not any(last_line.endswith(c) for c in ['}', ']', '"', ',']):
                # Verificar si es un valor de string truncado (ej: "key": "value_incomplete)
                if '": "' in last_line or "': '" in last_line:
                    # Cerrar paréntesis/corchetes abiertos en el string
                    open_parens = last_line.count('(') - last_line.count(')')
                    if open_parens > 0:
                        last_line += ')' * open_parens

                    open_brackets = last_line.count('[') - last_line.count(']')
                    if open_brackets > 0:
                        last_line += ']' * open_brackets

                    # Cerrar comilla del string
                    quote_char = '"' if '": "' in last_line else "'"
                    if not last_line.endswith(quote_char):
                        last_line += quote_char

                    # Actualizar línea
                    lines[-1] = last_line
                    json_str = '\n'.join(lines)
                else:
                    # Remover línea completamente incompleta
                    json_str = '\n'.join(lines[:-1])
                    # Si la línea anterior termina en coma, removerla
                    if json_str.rstrip().endswith(','):
                        json_str = json_str.rstrip()[:-1]

            # Paso 2: Cerrar comillas abiertas globalmente
            quote_count = json_str.count('"') - json_str.count('\\"')
            if quote_count % 2 != 0:  # Comillas impares
                json_str += '"'

            # Paso 3: Balancear llaves
            open_braces = json_str.count('{') - json_str.count('\\{')
            close_braces = json_str.count('}') - json_str.count('\\}')

            if open_braces > close_braces:
                # Agregar comas si el último elemento no la tiene
                if json_str.rstrip()[-1] not in [',', '{', '[']:
                    json_str = json_str.rstrip() + ','

                # Cerrar llaves
                json_str += '\n' + '}' * (open_braces - close_braces)

            # Paso 4: Balancear corchetes (arrays)
            open_brackets = json_str.count('[') - json_str.count('\\[')
            close_brackets = json_str.count(']') - json_str.count('\\]')

            if open_brackets > close_brackets:
                json_str += ']' * (open_brackets - close_brackets)

            return json_str.strip()
        except Exception as e:
            # En caso de error, retornar None
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
            return LLMProviderTimeoutError(
                f"Timeout en llamada a Ollama (¿modelo cargado?): {error}"
            )

        if "connection" in error_str or "refused" in error_str:
            return LLMProviderError(
                f"No se pudo conectar a Ollama en {self.base_url}. "
                f"¿Está Ollama corriendo?: {error}"
            )

        if "not found" in error_str or "404" in error_str:
            return LLMProviderError(
                f"Modelo {self.default_model} no encontrado en Ollama. "
                f"Ejecuta: ollama pull {self.default_model}"
            )

        return LLMProviderError(f"Error en llamada a Ollama: {error}")


# ==========================================
# FUNCIÓN DE CONVENIENCIA
# ==========================================

def create_ollama_provider(
    model_name: str = "phi3.5",
    base_url: str = "http://localhost:11434",
    enable_logging: bool = True
) -> OllamaProvider:
    """
    Factory function para crear un OllamaProvider configurado.

    Args:
        model_name: Nombre del modelo (phi3.5, llama3.2, qwen2.5, etc.)
        base_url: URL de Ollama
        enable_logging: Habilitar logging

    Returns:
        OllamaProvider configurado

    Example:
        >>> provider = create_ollama_provider("phi3.5")
        >>> request = LLMRequest(prompt="Hello", max_tokens=100)
        >>> response = provider.complete(request)
    """
    return OllamaProvider(
        base_url=base_url,
        default_model=model_name,
        enable_logging=enable_logging
    )
