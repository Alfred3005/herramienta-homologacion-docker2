"""
Módulo de filtros para procesamiento en lote de puestos.
Implementa patrón Strategy para filtrado modular y extensible.
"""

from .base_filter import PuestoFilter
from .nivel_filter import NivelSalarialFilter
from .ur_filter import URFilter
from .codigo_filter import CodigoPuestoFilter
from .composite_filter import CompositeFilter

__all__ = [
    'PuestoFilter',
    'NivelSalarialFilter',
    'URFilter',
    'CodigoPuestoFilter',
    'CompositeFilter'
]
