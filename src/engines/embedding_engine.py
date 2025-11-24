"""
EmbeddingEngine - Motor de embeddings semánticos

Motor para generar embeddings de textos usando sentence-transformers.
Incluye sistema de caché persistente para optimizar rendimiento.
"""

import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingEngineError(Exception):
    """Error en el motor de embeddings"""
    pass


class EmbeddingEngine:
    """
    Motor de embeddings con caché persistente.

    Características:
    - Genera embeddings usando sentence-transformers
    - Cache persistente en disco (pickle)
    - Limpieza automática de cache antiguo
    - Estadísticas de uso de cache
    - Soporte para batch encoding
    """

    def __init__(
        self,
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        cache_file: str = "embeddings_cache.pkl",
        cache_duration_hours: int = 168,  # 7 días
        enable_logging: bool = True
    ):
        """
        Inicializa el motor de embeddings.

        Args:
            model_name: Nombre del modelo de sentence-transformers
            cache_file: Archivo para cache persistente
            cache_duration_hours: Duración del cache en horas
            enable_logging: Habilitar logging
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise EmbeddingEngineError(
                "sentence-transformers no está instalado. "
                "Instalar con: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.cache_file = Path(cache_file)
        self.cache_duration_hours = cache_duration_hours
        self.enable_logging = enable_logging

        self.model: Optional[SentenceTransformer] = None
        self.embeddings_cache: Dict[str, Tuple[np.ndarray, datetime]] = {}

        self.cache_hits = 0
        self.cache_misses = 0
        self.initialized = False

    def initialize(self) -> bool:
        """
        Carga el modelo y el cache.

        Returns:
            True si se inicializa correctamente
        """
        if self.initialized:
            return True

        try:
            if self.enable_logging:
                print(f"[EmbeddingEngine] Cargando modelo {self.model_name}...")

            start = datetime.now()
            self.model = SentenceTransformer(self.model_name)
            duration = (datetime.now() - start).total_seconds()

            if self.enable_logging:
                print(f"[EmbeddingEngine] Modelo cargado en {duration:.2f}s")

            # Cargar cache si existe
            self.load_cache()

            self.initialized = True
            return True

        except Exception as e:
            raise EmbeddingEngineError(f"Error al inicializar motor: {str(e)}")

    def encode_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Codifica un texto a embedding.

        Args:
            text: Texto a codificar
            use_cache: Usar cache si está disponible

        Returns:
            Vector de embedding (numpy array)

        Raises:
            EmbeddingEngineError: Si el motor no está inicializado
        """
        if not self.initialized:
            raise EmbeddingEngineError("Motor no inicializado. Llamar initialize() primero.")

        # Intentar cache
        if use_cache:
            text_hash = self._get_text_hash(text)

            if text_hash in self.embeddings_cache:
                embedding, timestamp = self.embeddings_cache[text_hash]

                # Verificar antigüedad
                age = datetime.now() - timestamp
                if age.total_seconds() < self.cache_duration_hours * 3600:
                    self.cache_hits += 1
                    return embedding

        # Codificar nuevo
        self.cache_misses += 1
        embedding = self.model.encode(text, convert_to_numpy=True)

        # Guardar en cache
        if use_cache:
            text_hash = self._get_text_hash(text)
            self.embeddings_cache[text_hash] = (embedding, datetime.now())

        return embedding

    def encode_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Codifica múltiples textos eficientemente.

        Args:
            texts: Lista de textos
            show_progress: Mostrar barra de progreso
            batch_size: Tamaño de batch para procesamiento

        Returns:
            Array de embeddings

        Raises:
            EmbeddingEngineError: Si el motor no está inicializado
        """
        if not self.initialized:
            raise EmbeddingEngineError("Motor no inicializado")

        # Codificar batch completo (más eficiente)
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
            batch_size=batch_size
        )

        # Guardar en cache
        for text, embedding in zip(texts, embeddings):
            text_hash = self._get_text_hash(text)
            self.embeddings_cache[text_hash] = (embedding, datetime.now())

        return embeddings

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calcula similitud de coseno entre dos embeddings.

        Args:
            emb1: Primer embedding
            emb2: Segundo embedding

        Returns:
            Similitud de coseno [-1, 1]
        """
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def load_cache(self) -> bool:
        """
        Carga cache desde disco.

        Returns:
            True si se carga correctamente
        """
        if not self.cache_file.exists():
            if self.enable_logging:
                print("[EmbeddingEngine] Sin cache previo")
            return False

        try:
            with open(self.cache_file, 'rb') as f:
                self.embeddings_cache = pickle.load(f)

            if self.enable_logging:
                print(f"[EmbeddingEngine] Cache cargado: {len(self.embeddings_cache)} entradas")
            return True

        except Exception as e:
            if self.enable_logging:
                print(f"[EmbeddingEngine] Error cargando cache: {e}")
            return False

    def save_cache(self) -> bool:
        """
        Guarda cache a disco.

        Returns:
            True si se guarda correctamente
        """
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.embeddings_cache, f)

            if self.enable_logging:
                print(f"[EmbeddingEngine] Cache guardado: {len(self.embeddings_cache)} entradas")
            return True

        except Exception as e:
            if self.enable_logging:
                print(f"[EmbeddingEngine] Error guardando cache: {e}")
            return False

    def clear_old_cache(self, max_age_hours: Optional[int] = None):
        """
        Limpia entradas antiguas del cache.

        Args:
            max_age_hours: Edad máxima en horas (usa cache_duration_hours si no se especifica)
        """
        if max_age_hours is None:
            max_age_hours = self.cache_duration_hours

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_keys = []

        for text_hash, (_, timestamp) in self.embeddings_cache.items():
            if timestamp < cutoff_time:
                old_keys.append(text_hash)

        for key in old_keys:
            del self.embeddings_cache[key]

        if old_keys and self.enable_logging:
            print(f"[EmbeddingEngine] Limpiadas {len(old_keys)} entradas antiguas")

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Obtiene estadísticas del cache.

        Returns:
            Dict con estadísticas
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        cache_size_mb = 0
        if self.cache_file.exists():
            cache_size_mb = self.cache_file.stat().st_size / 1024 / 1024

        return {
            "cache_size": len(self.embeddings_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": hit_rate,
            "cache_file_size_mb": cache_size_mb,
            "model_name": self.model_name
        }

    def _get_text_hash(self, text: str) -> str:
        """
        Genera hash único para texto (clave de cache).

        Args:
            text: Texto a hashear

        Returns:
            Hash MD5 del texto
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def is_available(self) -> bool:
        """
        Verifica si el motor está disponible.

        Returns:
            True si está inicializado
        """
        return self.initialized
