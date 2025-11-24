"""
PipelineFactory - Factory para crear pipelines con Dependency Injection

Implementa Factory Pattern para facilitar la creación de pipelines configurados.
Permite crear extractores y evaluadores con todas sus dependencias inyectadas.
"""

from typing import Optional, Dict, Any
import os

from ..interfaces.llm_provider import ILLMProvider
from ..providers.openai_provider import OpenAIProvider
from ..core import (
    APFExtractor,
    FileReader,
    PromptBuilder,
    DataValidator
)
from ..engines import EmbeddingEngine


class PipelineFactory:
    """
    Factory para crear componentes del pipeline con DI.

    Simplifica la creación de extractores y evaluadores configurados
    con todas sus dependencias correctamente inyectadas.
    """

    @staticmethod
    def create_openai_provider(
        api_key: Optional[str] = None,
        model: str = "openai/gpt-4o",
        timeout: int = 60,
        max_retries: int = 3,
        enable_logging: bool = True
    ) -> OpenAIProvider:
        """
        Crea un provider de OpenAI configurado.

        Args:
            api_key: API key de OpenAI (si None, usa variable de entorno)
            model: Modelo a usar
            timeout: Timeout en segundos
            max_retries: Número de reintentos
            enable_logging: Habilitar logging

        Returns:
            OpenAIProvider configurado
        """
        # Usar variable de entorno si no se provee API key
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "API key no proporcionada. Especificar api_key o "
                    "configurar variable de entorno OPENAI_API_KEY"
                )

        return OpenAIProvider(
            api_key=api_key,
            default_model=model,
            timeout=timeout,
            max_retries=max_retries,
            enable_logging=enable_logging
        )

    @staticmethod
    def create_extractor(
        llm_provider: Optional[ILLMProvider] = None,
        config: Optional[Dict[str, Any]] = None,
        enable_logging: bool = True
    ) -> APFExtractor:
        """
        Crea un extractor completo con todas sus dependencias.

        Args:
            llm_provider: Provider de LLM (si None, crea uno con OpenAI)
            config: Configuración adicional
            enable_logging: Habilitar logging

        Returns:
            APFExtractor configurado y listo para usar
        """
        config = config or {}

        # Crear provider si no se provee
        if llm_provider is None:
            llm_provider = PipelineFactory.create_openai_provider(
                api_key=config.get('openai_api_key'),
                model=config.get('model', 'openai/gpt-4o'),
                enable_logging=enable_logging
            )

        # Crear componentes
        file_reader = FileReader(
            encoding=config.get('encoding', 'utf-8')
        )

        prompt_builder = PromptBuilder()

        data_validator = DataValidator(
            strict_mode=config.get('strict_validation', False)
        )

        # Crear extractor con DI
        extractor = APFExtractor(
            llm_provider=llm_provider,
            file_reader=file_reader,
            prompt_builder=prompt_builder,
            data_validator=data_validator,
            enable_logging=enable_logging
        )

        return extractor

    @staticmethod
    def create_embedding_engine(
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        cache_file: str = "embeddings_cache.pkl",
        cache_duration_hours: int = 168,
        enable_logging: bool = True,
        auto_initialize: bool = True
    ) -> EmbeddingEngine:
        """
        Crea un motor de embeddings configurado.

        Args:
            model_name: Nombre del modelo de sentence-transformers
            cache_file: Archivo para cache
            cache_duration_hours: Duración del cache
            enable_logging: Habilitar logging
            auto_initialize: Inicializar automáticamente

        Returns:
            EmbeddingEngine configurado
        """
        engine = EmbeddingEngine(
            model_name=model_name,
            cache_file=cache_file,
            cache_duration_hours=cache_duration_hours,
            enable_logging=enable_logging
        )

        if auto_initialize:
            engine.initialize()

        return engine

    @staticmethod
    def create_simple_pipeline(
        api_key: Optional[str] = None,
        model: str = "openai/gpt-4o",
        enable_logging: bool = True
    ) -> APFExtractor:
        """
        Crea un pipeline simple listo para usar (configuración mínima).

        Args:
            api_key: API key de OpenAI (opcional si está en variable de entorno)
            model: Modelo a usar
            enable_logging: Habilitar logging

        Returns:
            APFExtractor configurado y listo

        Example:
            >>> extractor = PipelineFactory.create_simple_pipeline()
            >>> result = extractor.extract_from_file("puesto.pdf")
        """
        llm_provider = PipelineFactory.create_openai_provider(
            api_key=api_key,
            model=model,
            enable_logging=enable_logging
        )

        return PipelineFactory.create_extractor(
            llm_provider=llm_provider,
            enable_logging=enable_logging
        )

    @staticmethod
    def create_advanced_pipeline(
        api_key: Optional[str] = None,
        model: str = "openai/gpt-4o",
        strict_validation: bool = False,
        enable_embeddings: bool = False,
        embedding_model: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        enable_logging: bool = True
    ) -> Dict[str, Any]:
        """
        Crea un pipeline avanzado con todas las capacidades.

        Args:
            api_key: API key de OpenAI
            model: Modelo LLM a usar
            strict_validation: Validación estricta
            enable_embeddings: Habilitar motor de embeddings
            embedding_model: Modelo de embeddings
            enable_logging: Habilitar logging

        Returns:
            Dict con extractor y opcionalmente embedding_engine

        Example:
            >>> pipeline = PipelineFactory.create_advanced_pipeline(
            ...     enable_embeddings=True
            ... )
            >>> extractor = pipeline['extractor']
            >>> embedding_engine = pipeline['embedding_engine']
        """
        # Crear provider LLM
        llm_provider = PipelineFactory.create_openai_provider(
            api_key=api_key,
            model=model,
            enable_logging=enable_logging
        )

        # Crear extractor
        extractor = PipelineFactory.create_extractor(
            llm_provider=llm_provider,
            config={'strict_validation': strict_validation},
            enable_logging=enable_logging
        )

        result = {
            'extractor': extractor,
            'llm_provider': llm_provider
        }

        # Agregar embedding engine si se solicita
        if enable_embeddings:
            embedding_engine = PipelineFactory.create_embedding_engine(
                model_name=embedding_model,
                enable_logging=enable_logging,
                auto_initialize=True
            )
            result['embedding_engine'] = embedding_engine

        return result
