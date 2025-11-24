"""
Módulos core del sistema de homologación APF v5.0

Contiene la lógica de negocio principal:
- file_reader: Lectura de archivos de puestos
- prompt_builder: Construcción de prompts para LLM
- data_validator: Validación de esquemas y datos
- agente_extractor: Extracción de información de puestos
- agente_evaluador: Evaluación de puestos contra normativa
- contextual_validator: Validación contextual inteligente
- verb_analyzer: Análisis semántico de verbos
- llm_evaluator: Evaluación mediante LLM

Todos los módulos siguen el principio de Single Responsibility.
"""

from .file_reader import FileReader, FileContent, FileReadError, UnsupportedFileTypeError
from .prompt_builder import PromptBuilder, ExtractionMode
from .data_validator import (
    DataValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)
from .agente_extractor import APFExtractor, ExtractionError

__version__ = '5.0.0'
__all__ = [
    'FileReader', 'FileContent', 'FileReadError', 'UnsupportedFileTypeError',
    'PromptBuilder', 'ExtractionMode',
    'DataValidator', 'ValidationResult', 'ValidationIssue', 'ValidationSeverity',
    'APFExtractor', 'ExtractionError'
]
