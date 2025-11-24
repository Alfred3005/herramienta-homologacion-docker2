"""
Adaptador InMemory para NormativaLoader de v4

Este módulo proporciona un adaptador que permite usar el NormativaLoader de v4
con fragmentos de texto en memoria (sin archivos físicos).

Autor: Claude Code v5.18
Fecha: 2025-11-06
"""

import hashlib
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from src.validators.normativa_loader import (
    NormativaLoader,
    NormativeDocument,
    APFContext
)


class InMemoryNormativaAdapter:
    """
    Adaptador que crea un NormativaLoader funcional a partir de fragmentos de texto.

    En lugar de cargar archivos desde disco, este adaptador crea documentos
    NormativeDocument en memoria y los inyecta directamente en el loader.
    """

    def __init__(
        self,
        text_fragments: List[str],
        document_title: str = "Reglamento Interior",
        context: Optional[APFContext] = None
    ):
        """
        Inicializa el adaptador con fragmentos de texto.

        Args:
            text_fragments: Lista de fragmentos de normativa (párrafos/secciones)
            document_title: Título del documento normativo
            context: Contexto APF (opcional)
        """
        self.text_fragments = text_fragments
        self.document_title = document_title
        self.context = context or APFContext()

        # Crear loader sin inicializar (sin cargar archivos)
        self.loader = NormativaLoader(
            normativa_directory=None,  # No usaremos directorio
            context=self.context
        )

        # Crear documento en memoria
        self._create_in_memory_document()

    def _create_in_memory_document(self) -> None:
        """
        Crea un NormativeDocument en memoria a partir de los fragmentos.
        """
        # Unir todos los fragmentos
        full_content = "\n\n".join(self.text_fragments)

        # Generar ID único basado en contenido
        content_hash = hashlib.md5(full_content.encode()).hexdigest()[:8]
        doc_id = f"inmemory_{content_hash}"

        # Crear documento normativo
        document = NormativeDocument(
            doc_id=doc_id,
            title=f"{self.document_title} [InMemory]",
            file_path="<in-memory>",
            priority=1,  # Alta prioridad
            scope="Reglamento interior cargado desde memoria",
            content=full_content,
            metadata={
                "source": "in_memory",
                "fragments_count": len(self.text_fragments),
                "created_at": datetime.now().isoformat(),
                "content_hash": content_hash
            }
        )

        # Inyectar documento en el loader
        self.loader.documents[doc_id] = document

        # Actualizar estadísticas del loader
        self.loader.load_stats["documents_processed"] = 1
        self.loader.load_stats["successful_loads"] = 1
        self.loader.load_stats["total_words"] = document.word_count
        self.loader.load_stats["last_load"] = datetime.now()

        # Crear índice global
        self.loader._create_global_index()

        # Crear hash de documentos para caché
        self.loader.documents_hash = self.loader._create_documents_hash()

        # Marcar como inicializado
        self.loader.initialized = True

    def get_loader(self) -> NormativaLoader:
        """
        Retorna el NormativaLoader configurado y listo para usar.

        Returns:
            NormativaLoader con documento en memoria cargado
        """
        return self.loader

    def initialize_with_embeddings(self, use_embeddings: bool = False) -> bool:
        """
        Inicializa embeddings para el documento en memoria.

        Args:
            use_embeddings: Si True, intenta inicializar sistema de embeddings

        Returns:
            True si la inicialización fue exitosa
        """
        if not use_embeddings:
            self.loader.embedding_mode = "disabled"
            return True

        try:
            # Intentar inicializar embeddings
            return self.loader._initialize_embeddings()
        except Exception as e:
            print(f"[InMemoryAdapter] Embeddings deshabilitados: {e}")
            self.loader.embedding_mode = "disabled"
            return False


def create_loader_from_fragments(
    text_fragments: List[str],
    document_title: str = "Reglamento Interior",
    use_embeddings: bool = False,
    context: Optional[APFContext] = None
) -> NormativaLoader:
    """
    Factory function para crear un NormativaLoader desde fragmentos de texto.

    Args:
        text_fragments: Lista de fragmentos de normativa
        document_title: Título del documento
        use_embeddings: Si True, inicializa sistema de embeddings
        context: Contexto APF opcional

    Returns:
        NormativaLoader configurado y listo para usar

    Example:
        >>> fragments = ["Artículo 1. ...", "Artículo 2. ..."]
        >>> loader = create_loader_from_fragments(fragments, "Reglamento SABG")
        >>> results = loader.semantic_search("atribuciones director")
    """
    adapter = InMemoryNormativaAdapter(
        text_fragments=text_fragments,
        document_title=document_title,
        context=context
    )

    # Inicializar embeddings (siempre, para configurar embedding_mode correctamente)
    adapter.initialize_with_embeddings(use_embeddings=use_embeddings)

    return adapter.get_loader()
