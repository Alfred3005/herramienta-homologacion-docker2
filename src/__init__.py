"""
Sistema de Homologación APF v5.0

Sistema modular para extracción, evaluación y validación de descripciones
de puestos de la Administración Pública Federal (APF) de México.

Arquitectura basada en principios SOLID:
- Single Responsibility: Cada módulo tiene una responsabilidad clara
- Open/Closed: Extensible mediante configuración y plugins
- Liskov Substitution: Jerarquías bien definidas
- Interface Segregation: Interfaces pequeñas y especializadas
- Dependency Inversion: Dependencias mediante inyección

Módulos principales:
- interfaces: Contratos abstractos (ILLMProvider, ICacheProvider, etc.)
- core: Lógica de negocio (extractores, evaluadores, validadores)
- providers: Implementaciones concretas de interfaces
- engines: Motores especializados (embeddings, normativa)
- utils: Utilidades compartidas
- pipeline: Orquestación del flujo completo
"""

__version__ = '5.0.0'
__author__ = 'Equipo APF'
__license__ = 'MIT'

# Exportar interfaces principales para facilitar imports
from src.interfaces import (
    ILLMProvider,
    ICacheProvider,
    ILogger,
    INormativaSource
)

__all__ = [
    'ILLMProvider',
    'ICacheProvider',
    'ILogger',
    'INormativaSource'
]
