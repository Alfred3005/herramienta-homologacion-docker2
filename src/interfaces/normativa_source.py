"""
Interface para fuentes de normativa

Permite diferentes implementaciones:
- Archivos de texto
- Base de datos
- APIs externas
"""

from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class NormativaFragment:
    """Fragmento de normativa con metadata"""
    content: str
    source_document: str
    article_number: Optional[str] = None
    section: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class NormativaDocument:
    """Documento completo de normativa"""
    name: str
    content: str
    document_type: str  # "reglamento", "ley", "acuerdo", etc.
    year: Optional[int] = None
    organization: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class INormativaSource(Protocol):
    """
    Interface para fuentes de normativa.

    Implementaciones pueden cargar normativa desde:
    - Archivos de texto locales
    - Base de datos
    - APIs de gobierno
    """

    def load_document(self, document_name: str) -> NormativaDocument:
        """
        Carga un documento completo de normativa.

        Args:
            document_name: Nombre del documento a cargar

        Returns:
            NormativaDocument con el contenido completo

        Raises:
            NormativaNotFoundError: Si el documento no existe
        """
        ...

    def search_fragments(
        self,
        query: str,
        document_names: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[NormativaFragment]:
        """
        Busca fragmentos relevantes de normativa.

        Args:
            query: Texto de búsqueda
            document_names: Lista opcional de documentos donde buscar
            top_k: Número de fragmentos a retornar

        Returns:
            Lista de fragmentos ordenados por relevancia
        """
        ...

    def get_available_documents(self) -> List[str]:
        """
        Lista los documentos de normativa disponibles.

        Returns:
            Lista de nombres de documentos
        """
        ...

    def reload(self) -> None:
        """
        Recarga todos los documentos de normativa.
        Útil si los archivos cambian en disco.
        """
        ...


class NormativaNotFoundError(Exception):
    """Error cuando no se encuentra un documento de normativa"""
    pass


class NormativaLoadError(Exception):
    """Error al cargar normativa"""
    pass
