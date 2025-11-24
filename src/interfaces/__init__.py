"""
Interfaces abstractas del sistema de homologación APF v5.0

Este módulo define los contratos (interfaces) que deben cumplir
las implementaciones concretas. Siguiendo el principio de Inversión
de Dependencias (DIP), los módulos de alto nivel dependen de estas
abstracciones, no de implementaciones concretas.
"""

from .llm_provider import ILLMProvider
from .cache_provider import ICacheProvider
from .logger import ILogger
from .normativa_source import INormativaSource

__all__ = [
    'ILLMProvider',
    'ICacheProvider',
    'ILogger',
    'INormativaSource'
]

__version__ = '5.0.0'
