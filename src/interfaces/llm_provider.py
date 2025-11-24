"""
Interface para proveedores de LLM (Large Language Models)

Implementa el principio de Inversión de Dependencias (DIP):
- Los módulos de alto nivel (extractor, evaluador) dependen de esta interfaz
- Las implementaciones concretas (OpenAI, Anthropic) implementan esta interfaz
- Permite intercambiar proveedores sin modificar código core
"""

from typing import Protocol, Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Respuesta estandarizada de un LLM"""
    content: str
    model: str
    tokens_used: Dict[str, int]  # {"prompt": X, "completion": Y, "total": Z}
    finish_reason: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMRequest:
    """Request estandarizado para un LLM"""
    prompt: str
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4000
    system_message: Optional[str] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ILLMProvider(Protocol):
    """
    Interface para proveedores de LLM.

    Cualquier implementación debe cumplir con estos métodos.
    Ejemplos de implementaciones:
    - OpenAIProvider (GPT-4, GPT-3.5)
    - AnthropicProvider (Claude)
    - LocalLLMProvider (Llama, Mistral)
    """

    def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Genera una completion dado un request.

        Args:
            request: Objeto LLMRequest con prompt y parámetros

        Returns:
            LLMResponse con el contenido generado y metadatos

        Raises:
            LLMProviderError: Si hay error en la llamada al LLM
        """
        ...

    def complete_json(self, request: LLMRequest) -> Dict[str, Any]:
        """
        Genera una completion en formato JSON.

        Args:
            request: Objeto LLMRequest con prompt y parámetros

        Returns:
            Dict parseado del JSON generado

        Raises:
            LLMProviderError: Si hay error en la llamada o parsing JSON
        """
        ...

    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna información del modelo configurado.

        Returns:
            Dict con información del modelo (name, max_tokens, etc.)
        """
        ...

    def is_available(self) -> bool:
        """
        Verifica si el proveedor está disponible.

        Returns:
            True si el proveedor está disponible, False en caso contrario
        """
        ...


class LLMProviderError(Exception):
    """Excepción base para errores de proveedores LLM"""
    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Error de timeout en llamada a LLM"""
    pass


class LLMProviderAuthError(LLMProviderError):
    """Error de autenticación con el proveedor"""
    pass


class LLMProviderRateLimitError(LLMProviderError):
    """Error de rate limit del proveedor"""
    pass
