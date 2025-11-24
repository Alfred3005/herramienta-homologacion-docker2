"""
Interface para logging

Implementa el principio de Segregación de Interfaces (ISP):
- Interface pequeña solo para logging
- Los clientes que necesitan logging no dependen de funcionalidades no relacionadas
"""

from typing import Protocol, Any, Dict, Optional
from enum import Enum


class LogLevel(Enum):
    """Niveles de logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ILogger(Protocol):
    """
    Interface para logging.

    Implementaciones pueden usar:
    - Python logging module
    - Loguru
    - Custom file logger
    - Cloud logging (AWS CloudWatch, etc.)
    """

    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log mensaje de debug.

        Args:
            message: Mensaje a registrar
            **kwargs: Contexto adicional
        """
        ...

    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log mensaje informativo.

        Args:
            message: Mensaje a registrar
            **kwargs: Contexto adicional
        """
        ...

    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Log mensaje de advertencia.

        Args:
            message: Mensaje a registrar
            **kwargs: Contexto adicional
        """
        ...

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        Log mensaje de error.

        Args:
            message: Mensaje a registrar
            exception: Excepción opcional
            **kwargs: Contexto adicional
        """
        ...

    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        Log mensaje crítico.

        Args:
            message: Mensaje a registrar
            exception: Excepción opcional
            **kwargs: Contexto adicional
        """
        ...

    def set_level(self, level: LogLevel) -> None:
        """
        Configura el nivel de logging.

        Args:
            level: Nivel de logging a configurar
        """
        ...

    def get_context(self) -> Dict[str, Any]:
        """
        Obtiene el contexto actual de logging.

        Returns:
            Dict con contexto (request_id, user_id, etc.)
        """
        ...
