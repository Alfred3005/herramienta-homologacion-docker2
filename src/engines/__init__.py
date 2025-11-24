"""
Engines - Motores especializados

Motores para funcionalidades específicas:
- embedding_engine: Generación y búsqueda de embeddings semánticos
- normativa_loader: Carga y gestión de documentos normativos
"""

from .embedding_engine import EmbeddingEngine, EmbeddingEngineError

__version__ = '5.0.0'
__all__ = ['EmbeddingEngine', 'EmbeddingEngineError']
