"""
Pipeline - Orquestación del flujo completo

Orquesta la ejecución de todas las etapas:
1. Extracción de información del puesto
2. Evaluación contra normativa
3. Validación contextual
4. Generación de reportes

Utiliza Dependency Injection para máxima flexibilidad y testabilidad.
"""

from .pipeline_factory import PipelineFactory

__version__ = '5.0.0'
__all__ = ['PipelineFactory']
