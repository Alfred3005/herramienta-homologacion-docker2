"""
Adaptadores para integración con fuentes de datos externas.
"""

from .sidegor_adapter import SidegorAdapter, SidegorExtractor
from .rhnet_document_generator import RHNetDocumentGenerator
from .sidegor_batch_processor import SidegorBatchProcessor, BatchProcessingResult

__all__ = [
    'SidegorAdapter',
    'SidegorExtractor',
    'RHNetDocumentGenerator',
    'SidegorBatchProcessor',
    'BatchProcessingResult'
]
