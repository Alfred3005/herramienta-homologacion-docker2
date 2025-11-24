"""
Motor de embeddings semánticos para normativa_loader.py
Encapsula sentence-transformers con sistema de caché
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

class EmbeddingEngine:
    """Motor de embeddings con caché persistente"""
    
    def __init__(self, 
                 model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                 cache_file: str = "embeddings_cache.pkl",
                 cache_duration_hours: int = 168):
        self.model_name = model_name
        self.cache_file = Path(cache_file)
        self.cache_duration_hours = cache_duration_hours
        
        self.model: Optional[SentenceTransformer] = None
        self.embeddings_cache: Dict[str, Tuple[np.ndarray, datetime]] = {}
        
        self.cache_hits = 0
        self.cache_misses = 0
        self.initialized = False
    
    def initialize(self) -> bool:
        """Carga modelo y caché"""
        if self.initialized:
            return True
        
        try:
            print(f"[EmbeddingEngine] Cargando modelo {self.model_name}...")
            start = datetime.now()
            
            self.model = SentenceTransformer(self.model_name)
            
            duration = (datetime.now() - start).total_seconds()
            print(f"[EmbeddingEngine] Modelo cargado en {duration:.2f}s")
            
            # Cargar caché si existe
            self.load_cache()
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"[EmbeddingEngine] ERROR inicializando: {e}")
            return False
    
    def _get_text_hash(self, text: str) -> str:
        """Hash único para texto (clave de caché)"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def encode_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Codifica texto a embedding (384D)"""
        if not self.initialized:
            raise RuntimeError("EmbeddingEngine no inicializado")
        
        # Intentar caché
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
        
        # Guardar en caché
        if use_cache:
            text_hash = self._get_text_hash(text)
            self.embeddings_cache[text_hash] = (embedding, datetime.now())
        
        return embedding
    
    def encode_batch(self, texts: List[str], 
                    show_progress: bool = False) -> np.ndarray:
        """Codifica múltiples textos eficientemente"""
        if not self.initialized:
            raise RuntimeError("EmbeddingEngine no inicializado")
        
        # Codificar batch completo (más eficiente que uno por uno)
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
            batch_size=32
        )
        
        # Guardar en caché
        for text, embedding in zip(texts, embeddings):
            text_hash = self._get_text_hash(text)
            self.embeddings_cache[text_hash] = (embedding, datetime.now())
        
        return embeddings
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Similitud de coseno [-1, 1]"""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def load_cache(self) -> bool:
        """Carga caché desde disco"""
        if not self.cache_file.exists():
            print("[EmbeddingEngine] Sin caché previo")
            return False
        
        try:
            with open(self.cache_file, 'rb') as f:
                self.embeddings_cache = pickle.load(f)
            
            print(f"[EmbeddingEngine] Caché cargado: {len(self.embeddings_cache)} entradas")
            return True
            
        except Exception as e:
            print(f"[EmbeddingEngine] Error cargando caché: {e}")
            return False
    
    def save_cache(self) -> bool:
        """Guarda caché a disco"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.embeddings_cache, f)
            
            return True
            
        except Exception as e:
            print(f"[EmbeddingEngine] Error guardando caché: {e}")
            return False
    
    def clear_old_cache(self, max_age_hours: int = None):
        """Limpia entradas antiguas"""
        if max_age_hours is None:
            max_age_hours = self.cache_duration_hours
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_keys = []
        
        for text_hash, (_, timestamp) in self.embeddings_cache.items():
            if timestamp < cutoff_time:
                old_keys.append(text_hash)
        
        for key in old_keys:
            del self.embeddings_cache[key]
        
        if old_keys:
            print(f"[EmbeddingEngine] Limpiadas {len(old_keys)} entradas antiguas")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Estadísticas de caché"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.embeddings_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": hit_rate,
            "cache_file_size_mb": self.cache_file.stat().st_size / 1024 / 1024 if self.cache_file.exists() else 0
        }