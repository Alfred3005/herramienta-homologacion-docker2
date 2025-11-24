# -*- coding: utf-8 -*-
"""
NORMATIVA LOADER v4.0 - Sistema Mejorado de Carga y Validación Normativa SABG
Análisis semántico, caché inteligente, detección automática mejorada
Integración completa con sistema APF v4.0
INCLUYE: Sistema de embeddings semánticos con sentence-transformers
"""

import json
import re
import hashlib
import pickle
import numpy as np  # AGREGADO para embeddings
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

# Importar motor de embeddings
from src.validators.embedding_engine import EmbeddingEngine  # AGREGADO

# Importar utilidades del sistema unificado
from src.validators.shared_utilities import (
    APFAgent, APFContext, clean_text_for_processing,
    robust_openai_call, DEFAULT_PATHS, LOGGING_CONFIG
)

# ==========================================
# CONFIGURACIÓN DE NORMATIVA
# ==========================================

# Jerarquía normativa actualizada para SABG
NORMATIVE_HIERARCHY = {
    "1_cpeum": {
        "document": "Constitución Política de los Estados Unidos Mexicanos",
        "priority": 1,
        "scope": "Principios constitucionales fundamentales",
        "keywords": ["constitución", "cpeum", "constitucional", "república", "estados unidos mexicanos"],
        "file_patterns": ["cpeum", "constitucion", "constitucional", "carta_magna"],
        "semantic_indicators": ["artículo constitucional", "garantías individuales", "división de poderes"]
    },
    "2_reglamento_sabg": {
        "document": "Reglamento Interior SABG 2025",
        "priority": 1,  # Máxima prioridad para SABG
        "scope": "Atribuciones específicas de todas las unidades administrativas SABG",
        "keywords": ["sabg", "secretaría anticorrupción", "buen gobierno", "reglamento interior"],
        "file_patterns": ["sabg", "reglamento_interior_sabg", "secretaria_anticorrupcion", "buen_gobierno"],
        "semantic_indicators": ["atribuciones", "unidad administrativa", "transparencia", "rendición de cuentas"]
    },
    "3_ley_organica": {
        "document": "Ley Orgánica de la Administración Pública Federal",
        "priority": 2,
        "scope": "Estructura y atribuciones generales de dependencias",
        "keywords": ["ley orgánica", "loapf", "administración pública federal"],
        "file_patterns": ["ley_organica", "loapf", "administracion_publica_federal"],
        "semantic_indicators": ["dependencias", "secretarías", "administración centralizada"]
    },
    "4_ley_remuneraciones": {
        "document": "Ley Federal de Remuneraciones",
        "priority": 2,
        "scope": "Marco normativo de remuneraciones",
        "keywords": ["remuneraciones", "salarios", "percepciones"],
        "file_patterns": ["ley_remuneraciones", "remuneraciones", "percepciones"],
        "semantic_indicators": ["tabulador", "nivel salarial", "compensación"]
    },
    "5_lfprh": {
        "document": "Ley Federal de Presupuesto y Responsabilidad Hacendaria",
        "priority": 2,
        "scope": "Gestión presupuestaria y responsabilidad fiscal",
        "keywords": ["presupuesto", "lfprh", "responsabilidad hacendaria"],
        "file_patterns": ["lfprh", "presupuesto", "hacendaria", "fiscal"],
        "semantic_indicators": ["ejercicio presupuestal", "recursos públicos", "eficiencia"]
    },
    "6_pef": {
        "document": "Presupuesto de Egresos de la Federación 2025",
        "priority": 2,
        "scope": "Asignaciones presupuestarias anuales",
        "keywords": ["pef", "presupuesto egresos", "federación 2025"],
        "file_patterns": ["pef", "presupuesto_egresos", "egresos_2025"],
        "semantic_indicators": ["asignación", "programa presupuestario", "recursos autorizados"]
    },
    "7_reglamento_shcp": {
        "document": "Reglamento Interior SHCP",
        "priority": 3,
        "scope": "Coordinación presupuestaria y hacendaria",
        "keywords": ["shcp", "hacienda", "reglamento interior shcp"],
        "file_patterns": ["reglamento_shcp", "shcp", "hacienda"],
        "semantic_indicators": ["coordinación", "hacienda pública", "política fiscal"]
    },
    "8_manual_percepciones": {
        "document": "Manual de Percepciones",
        "priority": 3,
        "scope": "Normativa específica de percepciones adicionales",
        "keywords": ["manual percepciones", "compensaciones", "estímulos"],
        "file_patterns": ["manual_percepciones", "percepciones", "compensaciones"],
        "semantic_indicators": ["prima", "compensación", "estímulo económico"]
    }
}

# Configuración de caché
CACHE_CONFIG = {
    "enable_cache": True,
    "cache_duration_hours": 24,
    "max_cache_entries": 1000,
    "cache_file": "normativa_cache.pkl"
}

# ==========================================
# CLASES DE DATOS
# ==========================================

@dataclass
class SemanticMatch:
    """Resultado de coincidencia semántica"""
    document_id: str
    document_title: str
    priority: int
    content_snippet: str
    confidence_score: float
    match_type: str  # "keyword", "semantic", "contextual", "embedding_chunk", "hybrid"
    position_info: Dict[str, int]
    supporting_evidence: List[str] = field(default_factory=list)

@dataclass
class ComplianceValidation:
    """Resultado de validación de compliance"""
    is_compliant: bool
    confidence_score: float
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    checked_documents: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

@dataclass
class NormativeDocument:
    """Documento normativo con capacidades mejoradas"""
    doc_id: str
    title: str
    file_path: str
    priority: int
    scope: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Campos para análisis semántico (originales)
    semantic_chunks: List[str] = field(default_factory=list)
    keyword_index: Dict[str, List[int]] = field(default_factory=dict)
    article_index: Dict[str, str] = field(default_factory=dict)
    section_index: Dict[str, List[str]] = field(default_factory=dict)
    
    # NUEVOS campos para embeddings
    chunk_embeddings: Optional[np.ndarray] = None  # Shape: (n_chunks, 384)
    embeddings_created: bool = False
    
    word_count: int = 0
    processed_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-procesamiento con análisis semántico"""
        if self.content:
            self.word_count = len(self.content.split())
            self._create_semantic_index()
    
    def _create_semantic_index(self, chunk_size: int = 300):
        """Crea índices semánticos del documento"""
        # Crear chunks semánticos
        sentences = re.split(r'[.!?]+', self.content)
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if current_size + sentence_words > chunk_size and current_chunk:
                self.semantic_chunks.append(current_chunk.strip().lower())
                current_chunk = sentence
                current_size = sentence_words
            else:
                current_chunk += " " + sentence
                current_size += sentence_words
        
        if current_chunk.strip():
            self.semantic_chunks.append(current_chunk.strip().lower())
        
        # Crear índice de palabras clave
        words = self.content.lower().split()
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 3:  # Ignorar palabras muy cortas
                if clean_word not in self.keyword_index:
                    self.keyword_index[clean_word] = []
                self.keyword_index[clean_word].append(i)
        
        # Extraer artículos si es ley/reglamento
        self._extract_articles()
        
        # Crear índice de secciones
        self._create_section_index()
    
    def _extract_articles(self):
        """Extrae artículos numerados del documento"""
        # Patrones para identificar artículos
        patterns = [
            r'Art[íi]culo\s+(\d+)[°º]?\.-?\s*(.*?)(?=Art[íi]culo|\Z)',
            r'ARTICULO\s+(\d+)[°º]?\.-?\s*(.*?)(?=ARTICULO|\Z)',
            r'(\d+)[°º]?\.-\s*(.*?)(?=\d+[°º]?\.-|\Z)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, self.content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                article_num = match.group(1)
                article_content = match.group(2).strip()
                if article_content:
                    self.article_index[f"articulo_{article_num}"] = article_content
    
    def _create_section_index(self):
        """Crea índice de secciones temáticas"""
        # Identificar secciones por títulos o palabras clave
        section_patterns = {
            "atribuciones": r"atribuciones?|competencias?|facultades?",
            "organizacion": r"organizaci[óo]n|estructura|organigrama",
            "procedimientos": r"procedimientos?|tr[áa]mites?|procesos?",
            "responsabilidades": r"responsabilidades?|obligaciones?|deberes?",
            "sanciones": r"sanciones?|infracciones?|multas?"
        }
        
        for section_name, pattern in section_patterns.items():
            paragraphs = []
            lines = self.content.split('\n')
            
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    # Tomar contexto alrededor de la línea coincidente
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 5)
                    context = '\n'.join(lines[context_start:context_end])
                    paragraphs.append(context)
            
            if paragraphs:
                self.section_index[section_name] = paragraphs
    
    def _calculate_article_relevance(self, query: str, article_content: str) -> float:
        """Calcula relevancia específica para artículos"""
        query_words = set(query.split())
        article_words = set(article_content.split())
        
        intersection = query_words.intersection(article_words)
        union = query_words.union(article_words)
        
        # Bonus por términos legales importantes
        legal_terms = ["atribuciones", "facultades", "competencias", "responsabilidades"]
        legal_bonus = sum(1 for term in legal_terms if term in article_content) * 0.1
        
        base_score = len(intersection) / len(union) if union else 0
        return min(1.0, base_score + legal_bonus)
    
    # ==========================================
    # NUEVOS MÉTODOS PARA EMBEDDINGS
    # ==========================================
    
    def create_embeddings(self, embedding_engine: 'EmbeddingEngine') -> bool:
        """Crea embeddings para todos los chunks"""
        if self.embeddings_created or not self.semantic_chunks:
            return True
        
        try:
            # Codificar todos los chunks en batch
            self.chunk_embeddings = embedding_engine.encode_batch(
                self.semantic_chunks,
                show_progress=False
            )
            
            self.embeddings_created = True
            return True
            
        except Exception as e:
            print(f"Error creando embeddings para {self.doc_id}: {e}")
            return False
    
    def semantic_search_embeddings(self,
                                   query: str,
                                   embedding_engine: 'EmbeddingEngine',
                                   max_results: int = 5,
                                   threshold: float = 0.58) -> List[SemanticMatch]:
        """Búsqueda con embeddings (NUEVO)"""
        if not self.embeddings_created or self.chunk_embeddings is None:
            return []
        
        results = []
        
        # Codificar query
        query_emb = embedding_engine.encode_text(query)
        
        # Comparar con cada chunk
        for i, chunk_emb in enumerate(self.chunk_embeddings):
            similarity = embedding_engine.cosine_similarity(query_emb, chunk_emb)
            
            if similarity >= threshold:
                match = SemanticMatch(
                    document_id=self.doc_id,
                    document_title=self.title,
                    priority=self.priority,
                    content_snippet=self.semantic_chunks[i][:200] + "...",
                    confidence_score=similarity,
                    match_type="embedding_chunk",
                    position_info={"chunk_index": i},
                    supporting_evidence=[f"Similitud coseno: {similarity:.3f}"]
                )
                results.append(match)
        
        # Ordenar por similitud
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return results[:max_results]
    
    def semantic_search_jaccard(self, query: str, max_results: int = 5) -> List[SemanticMatch]:
        """Búsqueda con Jaccard (método original renombrado)"""
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        results = []
        
        # Búsqueda en chunks semánticos
        for i, chunk in enumerate(self.semantic_chunks):
            chunk_words = set(re.findall(r'\w+', chunk))
            
            # Calcular similitud
            intersection = query_words.intersection(chunk_words)
            if len(intersection) > 0:
                confidence = len(intersection) / len(query_words.union(chunk_words))
                
                if confidence > 0.1:  # Umbral mínimo
                    match = SemanticMatch(
                        document_id=self.doc_id,
                        document_title=self.title,
                        priority=self.priority,
                        content_snippet=chunk[:200] + "..." if len(chunk) > 200 else chunk,
                        confidence_score=confidence,
                        match_type="semantic",
                        position_info={"chunk_index": i},
                        supporting_evidence=list(intersection)
                    )
                    results.append(match)
        
        # Búsqueda específica en artículos
        for article_id, article_content in self.article_index.items():
            if any(word in article_content.lower() for word in query_words):
                confidence = self._calculate_article_relevance(query_lower, article_content.lower())
                if confidence > 0.2:
                    match = SemanticMatch(
                        document_id=self.doc_id,
                        document_title=self.title,
                        priority=self.priority,
                        content_snippet=article_content[:300] + "...",
                        confidence_score=confidence,
                        match_type="article",
                        position_info={"article": article_id},
                        supporting_evidence=[f"Artículo específico: {article_id}"]
                    )
                    results.append(match)
        
        # Ordenar por confianza y prioridad
        results.sort(key=lambda x: (x.confidence_score, -x.priority), reverse=True)
        
        return results[:max_results]


# ==========================================
# SISTEMA DE CACHÉ INTELIGENTE
# ==========================================

class IntelligentCache:
    """Sistema de caché inteligente para búsquedas normativas"""
    
    def __init__(self, cache_file: str = None):
        self.cache_file = Path(cache_file or CACHE_CONFIG["cache_file"])
        self.cache_data = self._load_cache()
        self.hit_count = 0
        self.miss_count = 0
    
    def _load_cache(self) -> Dict[str, Any]:
        """Carga caché desde archivo"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                # Verificar si el caché es válido
                if self._is_cache_valid(cache_data):
                    return cache_data
            except Exception as e:
                print(f"Warning: Error cargando caché: {e}")
        
        return {"queries": {}, "metadata": {"created_at": datetime.now()}}
    
    def _is_cache_valid(self, cache_data: Dict) -> bool:
        """Verifica si el caché es válido"""
        if "metadata" not in cache_data:
            return False
        
        created_at = cache_data["metadata"].get("created_at")
        if not created_at:
            return False
        
        age = datetime.now() - created_at
        return age.total_seconds() < CACHE_CONFIG["cache_duration_hours"] * 3600
    
    def _save_cache(self) -> None:
        """Guarda caché a archivo"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache_data, f)
        except Exception as e:
            print(f"Warning: Error guardando caché: {e}")
    
    def get_query_hash(self, query: str, documents_hash: str) -> str:
        """Genera hash único para la consulta"""
        combined = f"{query}_{documents_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, query_hash: str) -> Optional[List[SemanticMatch]]:
        """Obtiene resultado del caché"""
        if not CACHE_CONFIG["enable_cache"]:
            return None
        
        if query_hash in self.cache_data["queries"]:
            entry = self.cache_data["queries"][query_hash]
            
            # Verificar si la entrada es válida
            entry_age = datetime.now() - entry["timestamp"]
            if entry_age.total_seconds() < CACHE_CONFIG["cache_duration_hours"] * 3600:
                self.hit_count += 1
                return entry["results"]
        
        self.miss_count += 1
        return None
    
    def set(self, query_hash: str, results: List[SemanticMatch]) -> None:
        """Almacena resultado en caché"""
        if not CACHE_CONFIG["enable_cache"]:
            return
        
        # Limpiar caché si es muy grande
        if len(self.cache_data["queries"]) >= CACHE_CONFIG["max_cache_entries"]:
            self._cleanup_cache()
        
        # Convertir SemanticMatch a dict para serialización
        serializable_results = []
        for match in results:
            serializable_results.append({
                "document_id": match.document_id,
                "document_title": match.document_title,
                "priority": match.priority,
                "content_snippet": match.content_snippet,
                "confidence_score": match.confidence_score,
                "match_type": match.match_type,
                "position_info": match.position_info,
                "supporting_evidence": match.supporting_evidence
            })
        
        self.cache_data["queries"][query_hash] = {
            "results": serializable_results,
            "timestamp": datetime.now()
        }
        
        self._save_cache()
    
    def _cleanup_cache(self) -> None:
        """Limpia entradas antiguas del caché"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=CACHE_CONFIG["cache_duration_hours"])
        
        queries_to_remove = []
        for query_hash, entry in self.cache_data["queries"].items():
            if entry["timestamp"] < cutoff_time:
                queries_to_remove.append(query_hash)
        
        for query_hash in queries_to_remove:
            del self.cache_data["queries"][query_hash]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests) * 100 if total_requests > 0 else 0
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache_data["queries"]),
            "cache_file_size": self.cache_file.stat().st_size if self.cache_file.exists() else 0
        }


# ==========================================
# CLASE PRINCIPAL: NORMATIVA LOADER MEJORADO
# ==========================================

class NormativaLoader(APFAgent):
    """
    Cargador inteligente mejorado con análisis semántico, caché y embeddings
    """
    
    def __init__(self, normativa_directory: str = None, context: APFContext = None):
        super().__init__("NormativaLoader", context)
        
        self.normativa_directory = Path(normativa_directory or DEFAULT_PATHS["normativa_dir"])
        self.documents: Dict[str, NormativeDocument] = {}
        self.hierarchy = NORMATIVE_HIERARCHY.copy()
        self.cache = IntelligentCache()
        
        # Estadísticas mejoradas
        self.load_stats = {
            "documents_processed": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "total_words": 0,
            "processing_time": 0,
            "last_load": None
        }
        
        # Índice global para búsquedas rápidas
        self.global_keyword_index = defaultdict(set)  # palabra -> set de doc_ids
        self.documents_hash = ""
        
        # NUEVOS campos para embeddings (dentro del __init__)
        self.embedding_engine: Optional[EmbeddingEngine] = None
        self.embedding_mode: str = "enabled"  # "disabled" | "enabled" | "hybrid"
        self.embeddings_initialized: bool = False
    
    def initialize(self, use_embeddings: bool = True) -> bool:
        """Inicializa el loader cargando documentos y opcionalmente embeddings"""
        if self.initialized:
            return True
        
        self._log("Inicializando Normativa Loader v4.0")
        
        if not self.normativa_directory.exists():
            error_msg = f"Directorio normativa no existe: {self.normativa_directory}"
            self.context.add_error(error_msg, self.agent_name)
            return False
        
        # 1. Cargar documentos
        load_result = self.load_all_documents()
        
        if load_result["status"] != "success":
            self.context.add_error(f"Error en inicialización: {load_result.get('error')}", self.agent_name)
            return False
        
        # 2. Crear índice Jaccard
        self._create_global_index()
        
        # 3. NUEVO: Inicializar embeddings
        if use_embeddings:
            self._initialize_embeddings()
        else:
            self.embedding_mode = "disabled"
        
        self.initialized = True
        self._log(f"Inicialización exitosa: {len(self.documents)} documentos cargados")
        return True
    
    def load_all_documents(self) -> Dict[str, Any]:
        """Carga todos los documentos normativos con detección automática mejorada"""
        self.context.start_step("load_normative_documents", self.agent_name)
        
        start_time = datetime.now()
        
        # Encontrar archivos
        text_files = list(self.normativa_directory.glob("*.txt"))
        if not text_files:
            error_msg = f"No se encontraron archivos .txt en {self.normativa_directory}"
            self.context.fail_step("load_normative_documents", error_msg)
            return {"status": "error", "error": error_msg}
        
        self._log(f"Encontrados {len(text_files)} archivos para procesar")
        
        # Procesar cada archivo
        for file_path in text_files:
            try:
                self._load_single_document_enhanced(file_path)
                self.load_stats["successful_loads"] += 1
            except Exception as e:
                error_msg = f"Error cargando {file_path.name}: {str(e)}"
                self.context.add_warning(error_msg, self.agent_name)
                self.load_stats["failed_loads"] += 1
        
        # Calcular estadísticas finales
        processing_time = (datetime.now() - start_time).total_seconds()
        self.load_stats["processing_time"] = processing_time
        self.load_stats["last_load"] = datetime.now()
        
        # Crear hash de los documentos para caché
        self.documents_hash = self._create_documents_hash()
        
        self.context.complete_step("load_normative_documents", 
                                 f"Cargados {self.load_stats['successful_loads']} documentos en {processing_time:.2f}s")
        
        return {
            "status": "success" if self.load_stats["successful_loads"] > 0 else "partial",
            "loaded_documents": self.load_stats["successful_loads"],
            "failed_documents": self.load_stats["failed_loads"],
            "total_words": self.load_stats["total_words"],
            "processing_time": processing_time
        }
    
    def _load_single_document_enhanced(self, file_path: Path) -> bool:
        """Carga un documento individual con análisis semántico"""
        try:
            # Leer contenido
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                self._log(f"Archivo vacío omitido: {file_path.name}", "WARNING")
                return False
            
            # Limpiar contenido
            clean_content = clean_text_for_processing(content)
            
            # Detección automática mejorada
            doc_info = self._enhanced_document_detection(file_path, clean_content)
            
            # FIX: Crear doc_id único usando hash del nombre de archivo
            import hashlib
            file_hash = hashlib.md5(file_path.name.encode()).hexdigest()[:8]
            unique_doc_id = f"{doc_info['doc_id']}_{file_hash}"
            
            # Crear documento con análisis semántico
            document = NormativeDocument(
                doc_id=unique_doc_id,  # Ahora es único por archivo
                title=f"{doc_info['title']} [{file_path.stem}]",  # Agregar identificador
                file_path=str(file_path),
                priority=doc_info["priority"],
                scope=doc_info["scope"],
                content=clean_content,
                metadata={
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                    "detection_confidence": doc_info.get("confidence", 0.5),
                    "detection_method": "enhanced_semantic",
                    "original_doc_id": doc_info["doc_id"],
                    "file_hash": file_hash
                }
            )
            
            # Guardar documento (ya no hay sobrescritura)
            self.documents[unique_doc_id] = document
            self.load_stats["total_words"] += document.word_count
            
            self._log(f"Cargado: {document.title} ({document.word_count:,} palabras, "
                    f"{len(document.semantic_chunks)} chunks)")
            
            return True
            
        except Exception as e:
            self._log(f"Error procesando {file_path.name}: {str(e)}", "ERROR")
            raise
        
    def _enhanced_document_detection(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Detección automática mejorada con prioridad en nombre de archivo"""
        file_name_lower = file_path.name.lower()
        content_lower = content.lower()
        
        # ===== DETECCIÓN PRIORITARIA POR NOMBRE DE ARCHIVO =====
        # Patrones específicos para evitar falsos positivos
        priority_patterns = {
            "ley_apf": ["ley organica", "ley orgánica", "apf", "administracion publica federal"],
            "reglamento_shcp": ["reglamento shcp", "reglamento de la shcp", "secretaria de hacienda"],
            "pef": ["pef", "presupuesto de egresos", "presupuesto egresos"],
        }
        
        for doc_id, patterns in priority_patterns.items():
            if doc_id in self.hierarchy:
                for pattern in patterns:
                    if pattern in file_name_lower:
                        doc_info = self.hierarchy[doc_id]
                        self._log(f"Detección directa por nombre de archivo: {doc_info['document']}")
                        return {
                            "doc_id": doc_id,
                            "title": doc_info["document"],
                            "priority": doc_info["priority"],
                            "scope": doc_info["scope"],
                            "confidence": 0.95,
                            "evidence": [f"filename_priority:{pattern}"]
                        }
        
        # ===== DETECCIÓN POR SCORING =====
        best_match = None
        best_score = 0
        best_confidence = 0
        
        for doc_id, doc_info in self.hierarchy.items():
            score = 0
            confidence_factors = []
            
            # Puntuación por patrones de archivo (peso: 6 - AUMENTADO)
            file_pattern_matches = 0
            for pattern in doc_info["file_patterns"]:
                if pattern in file_name_lower:
                    score += 6
                    file_pattern_matches += 1
                    confidence_factors.append(f"file_pattern:{pattern}")
            
            # Bonus por múltiples coincidencias en nombre de archivo
            if file_pattern_matches > 1:
                score += 3
            
            # Puntuación por palabras clave (peso: 1.5 - REDUCIDO)
            # Solo contar si hay coincidencia de archivo o semántica fuerte
            keyword_matches = 0
            for keyword in doc_info["keywords"]:
                occurrences = content_lower.count(keyword.lower())
                if occurrences > 0:
                    keyword_matches += occurrences
                    # Peso reducido para evitar falsos positivos
                    score += min(1.5, occurrences * 0.3)
                    confidence_factors.append(f"keyword:{keyword}({occurrences})")
            
            # Penalizar si solo hay keywords sin otros indicadores
            if keyword_matches > 0 and file_pattern_matches == 0 and len(confidence_factors) == keyword_matches:
                score *= 0.3  # Reducir drásticamente el score
            
            # Puntuación por indicadores semánticos (peso: 4)
            semantic_matches = 0
            for indicator in doc_info["semantic_indicators"]:
                if indicator.lower() in content_lower:
                    semantic_matches += 1
                    score += 4
                    confidence_factors.append(f"semantic:{indicator}")
            
            # Bonus por múltiples coincidencias semánticas
            if semantic_matches > 1:
                score += semantic_matches * 0.5
            
            # Bonus si hay coincidencia de archivo + contenido
            if file_pattern_matches > 0 and (semantic_matches > 0 or keyword_matches > 0):
                score += 2
                confidence_factors.append("multi_source_match")
            
            # Calcular confianza (ajustado para nuevo rango)
            confidence = min(1.0, score / 15.0)  # Normalizar a 0-1
            
            if score > best_score:
                best_score = score
                best_confidence = confidence
                best_match = {
                    "doc_id": doc_id,
                    "title": doc_info["document"],
                    "priority": doc_info["priority"],
                    "scope": doc_info["scope"],
                    "confidence": confidence,
                    "evidence": confidence_factors
                }
        
        # Umbral de confianza ajustado
        if best_score >= 3.0 and best_match:
            self._log(f"Detectado como: {best_match['title']} "
                    f"(score: {best_score:.1f}, confianza: {best_confidence:.2f})")
            return best_match
        
        # Fallback mejorado
        self._log(f"No se pudo detectar automáticamente (best_score: {best_score:.1f})")
        fallback_info = self._create_fallback_document_info(file_path, content)
        return fallback_info
    
    def _create_fallback_document_info(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Crea información de documento cuando no se puede detectar automáticamente"""
        file_stem = file_path.stem.replace('_', ' ').title()
        
        # Intentar inferir prioridad basada en contenido
        priority = 4  # Default: baja prioridad
        
        high_priority_terms = ["constitución", "ley orgánica", "presupuesto", "reglamento interior"]
        medium_priority_terms = ["manual", "acuerdo", "disposiciones"]
        
        content_lower = content.lower()
        
        if any(term in content_lower for term in high_priority_terms):
            priority = 2
        elif any(term in content_lower for term in medium_priority_terms):
            priority = 3
        
        return {
            "doc_id": f"unclassified_{hashlib.md5(file_path.name.encode()).hexdigest()[:8]}",
            "title": f"{file_stem} (No Clasificado)",
            "priority": priority,
            "scope": "Documento normativo no clasificado automáticamente",
            "confidence": 0.3
        }
    
    def _create_global_index(self) -> None:
        """Crea índice global de palabras clave para búsquedas rápidas"""
        self._log("Creando índice global de palabras clave")
        
        self.global_keyword_index.clear()
        
        for doc_id, document in self.documents.items():
            for keyword in document.keyword_index.keys():
                self.global_keyword_index[keyword].add(doc_id)
    
    def _create_documents_hash(self) -> str:
        """Crea hash único para el conjunto de documentos cargados"""
        doc_signatures = []
        for doc_id in sorted(self.documents.keys()):
            doc = self.documents[doc_id]
            signature = f"{doc_id}:{doc.word_count}:{doc.processed_at.isoformat()}"
            doc_signatures.append(signature)
        
        combined_signature = "|".join(doc_signatures)
        return hashlib.sha256(combined_signature.encode()).hexdigest()
    
    # ==========================================
    # NUEVOS MÉTODOS PARA EMBEDDINGS
    # ==========================================
    
    def _initialize_embeddings(self) -> bool:
        """Inicializa embeddings para todos los documentos"""
        try:
            print("[NormativaLoader] Inicializando sistema de embeddings...")
            
            # Crear motor de embeddings
            self.embedding_engine = EmbeddingEngine()
            
            if not self.embedding_engine.initialize():
                print("[NormativaLoader] Fallback: embeddings deshabilitados")
                self.embedding_mode = "disabled"
                return False
            
            # Procesar cada documento
            total_docs = len(self.documents)
            for i, (doc_id, document) in enumerate(self.documents.items(), 1):
                print(f"[NormativaLoader] Procesando {i}/{total_docs}: {document.title[:50]}...")
                document.create_embeddings(self.embedding_engine)
            
            # Guardar caché
            self.embedding_engine.save_cache()
            
            # Mostrar estadísticas
            stats = self.embedding_engine.get_cache_stats()
            print(f"[NormativaLoader] Embeddings listos: {stats['cache_size']} vectores")
            
            self.embeddings_initialized = True
            return True
            
        except Exception as e:
            print(f"[NormativaLoader] Error inicializando embeddings: {e}")
            self.embedding_mode = "disabled"
            return False
    
    def semantic_search(self, query: str, max_results: int = 10, 
                       use_cache: bool = True) -> List[SemanticMatch]:
        """
        Búsqueda semántica inteligente con soporte para embeddings
        """
        if not self.initialized:
            if not self.initialize():
                self.context.add_error("Normativa Loader no inicializado", self.agent_name)
                return []
        
        # Intentar obtener del caché
        query_hash = self.cache.get_query_hash(query, self.documents_hash)
        
        if use_cache:
            cached_results = self.cache.get(query_hash)
            if cached_results:
                # Reconstruir SemanticMatch objects
                results = []
                for result_dict in cached_results:
                    match = SemanticMatch(**result_dict)
                    results.append(match)
                self._log(f"Resultado obtenido del caché para: {query}")
                return results[:max_results]
        
        # Modo disabled: solo Jaccard
        if self.embedding_mode == "disabled" or not self.embeddings_initialized:
            return self._search_jaccard(query, max_results)
        
        # Modo enabled o hybrid: usar embeddings con fallback
        try:
            if self.embedding_mode == "hybrid":
                results = self._search_hybrid(query, max_results)
            else:  # "enabled"
                results = self._search_embeddings_only(query, max_results)
            
            # Guardar en caché
            if use_cache and results:
                self.cache.set(query_hash, results)
            
            self._update_stats(True)
            return results
            
        except Exception as e:
            self._log(f"Error en búsqueda embeddings, fallback a Jaccard: {e}", "WARNING")
            return self._search_jaccard(query, max_results)
    
    def _search_jaccard(self, query: str, max_results: int) -> List[SemanticMatch]:
        """Búsqueda con Jaccard (método original)"""
        self.context.start_step("semantic_search_jaccard", self.agent_name)
        
        # Búsqueda en múltiples etapas
        all_results = []
        
        # Etapa 1: Búsqueda por palabras clave en índice global
        query_words = set(re.findall(r'\w+', query.lower()))
        candidate_docs = set()
        
        for word in query_words:
            if word in self.global_keyword_index:
                candidate_docs.update(self.global_keyword_index[word])
        
        # Etapa 2: Búsqueda semántica en documentos candidatos
        for doc_id in candidate_docs:
            if doc_id in self.documents:
                document = self.documents[doc_id]
                doc_results = document.semantic_search_jaccard(query, max_results=3)
                all_results.extend(doc_results)
        
        # Etapa 3: Si pocos resultados, búsqueda en todos los documentos
        if len(all_results) < max_results // 2:
            remaining_docs = set(self.documents.keys()) - candidate_docs
            for doc_id in list(remaining_docs)[:5]:  # Limitar para performance
                document = self.documents[doc_id]
                doc_results = document.semantic_search_jaccard(query, max_results=2)
                all_results.extend(doc_results)
        
        # Ordenar y deduplicar
        seen_snippets = set()
        unique_results = []
        
        for result in sorted(all_results, key=lambda x: (x.confidence_score, -x.priority), reverse=True):
            snippet_hash = hashlib.md5(result.content_snippet.encode()).hexdigest()
            if snippet_hash not in seen_snippets:
                seen_snippets.add(snippet_hash)
                unique_results.append(result)
        
        final_results = unique_results[:max_results]
        
        self.context.complete_step("semantic_search_jaccard", 
                                 f"Encontrados {len(final_results)} resultados para '{query}'")
        
        return final_results
    
    def _search_embeddings_only(self, query: str, max_results: int) -> List[SemanticMatch]:
        """Búsqueda solo con embeddings"""
        self.context.start_step("semantic_search_embeddings", self.agent_name)
        
        all_results = []
        
        for doc_id, document in self.documents.items():
            doc_results = document.semantic_search_embeddings(
                query, self.embedding_engine, max_results=3, threshold=0.58
            )
            all_results.extend(doc_results)
        
        all_results.sort(key=lambda x: (x.confidence_score, -x.priority), reverse=True)
        
        final_results = all_results[:max_results]
        
        self.context.complete_step("semantic_search_embeddings",
                                 f"Encontrados {len(final_results)} resultados embeddings")
        
        return final_results
    
    def _search_hybrid(self, query: str, max_results: int) -> List[SemanticMatch]:
        """Modo híbrido: Jaccard para filtrar + embeddings para ranking"""
        self.context.start_step("semantic_search_hybrid", self.agent_name)
        
        # Paso 1: Filtrado rápido con Jaccard (threshold bajo, más resultados)
        jaccard_candidates = self._search_jaccard(query, max_results=20)
        
        if not jaccard_candidates:
            self.context.complete_step("semantic_search_hybrid", "Sin resultados")
            return []
        
        # Paso 2: Re-ranking con embeddings solo en candidatos
        query_emb = self.embedding_engine.encode_text(query)
        
        for candidate in jaccard_candidates:
            # Obtener documento del candidato
            doc = self.documents.get(candidate.document_id)
            if not doc or not doc.embeddings_created:
                continue
            
            # Buscar chunk correspondiente
            chunk_idx = candidate.position_info.get("chunk_index", 0)
            if chunk_idx < len(doc.chunk_embeddings):
                chunk_emb = doc.chunk_embeddings[chunk_idx]
                
                # Recalcular score con embeddings
                embedding_score = self.embedding_engine.cosine_similarity(query_emb, chunk_emb)
                
                # Actualizar confidence (ponderación: 70% embeddings, 30% jaccard)
                candidate.confidence_score = (embedding_score * 0.7) + (candidate.confidence_score * 0.3)
                candidate.match_type = "hybrid"
                candidate.supporting_evidence.append(f"Embedding score: {embedding_score:.3f}")
        
        # Paso 3: Re-ordenar por nuevo score
        jaccard_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
        
        final_results = jaccard_candidates[:max_results]
        
        self.context.complete_step("semantic_search_hybrid",
                                 f"Encontrados {len(final_results)} resultados híbridos")
        
        return final_results
    
    # ==========================================
    # MÉTODOS DE VALIDACIÓN (sin cambios)
    # ==========================================
    
    def validate_compliance_advanced(self, 
                                   position_functions: List[str],
                                   administrative_unit: str,
                                   hierarchical_level: str,
                                   position_title: str = None) -> ComplianceValidation:
        """
        Validación avanzada de compliance con análisis semántico
        """
        if not self.initialized:
            if not self.initialize():
                return ComplianceValidation(
                    is_compliant=False,
                    confidence_score=0.0,
                    violations=["Normativa Loader no inicializado"]
                )
        
        self.context.start_step("compliance_validation", self.agent_name)
        
        violations = []
        warnings = []
        supporting_evidence = []
        recommendations = []
        checked_documents = []
        
        # 1. Verificar atribuciones específicas en Reglamento SABG
        sabg_validation = self._validate_against_sabg_regulation(
            position_functions, administrative_unit, position_title
        )
        
        violations.extend(sabg_validation["violations"])
        warnings.extend(sabg_validation["warnings"])
        supporting_evidence.extend(sabg_validation["evidence"])
        checked_documents.extend(sabg_validation["documents"])
        
        # 2. Validar nivel jerárquico contra normativa general
        hierarchy_validation = self._validate_hierarchical_consistency(
            hierarchical_level, position_functions, administrative_unit
        )
        
        violations.extend(hierarchy_validation["violations"])
        warnings.extend(hierarchy_validation["warnings"])
        supporting_evidence.extend(hierarchy_validation["evidence"])
        
        # 3. Verificar contra marco normativo superior
        legal_validation = self._validate_against_superior_framework(
            position_functions, hierarchical_level
        )
        
        violations.extend(legal_validation["violations"])
        warnings.extend(legal_validation["warnings"])
        supporting_evidence.extend(legal_validation["evidence"])
        checked_documents.extend(legal_validation["documents"])
        
        # 4. Generar recomendaciones
        recommendations = self._generate_compliance_recommendations(
            violations, warnings, hierarchical_level
        )
        
        # Calcular score de confianza
        total_checks = len(position_functions) + 3
        violation_weight = len(violations) * 1.0
        warning_weight = len(warnings) * 0.3
        
        confidence_score = max(0.0, 1.0 - (violation_weight + warning_weight) / total_checks)
        
        # Determinar compliance
        is_compliant = len(violations) == 0 and len(warnings) <= len(position_functions) * 0.3
        
        self.context.complete_step("compliance_validation", 
                                 f"Compliance: {'✓' if is_compliant else '✗'} "
                                 f"(confianza: {confidence_score:.2%})")
        
        return ComplianceValidation(
            is_compliant=is_compliant,
            confidence_score=confidence_score,
            violations=violations,
            warnings=warnings,
            supporting_evidence=supporting_evidence,
            checked_documents=list(set(checked_documents)),
            recommendations=recommendations
        )
    
    def _validate_against_sabg_regulation(self, functions: List[str], 
                                         unit: str, title: str = None) -> Dict:
        """Valida específicamente contra Reglamento Interior SABG"""
        results = {
            "violations": [],
            "warnings": [],
            "evidence": [],
            "documents": []
        }
        
        # Buscar reglamento SABG
        sabg_doc = None
        for doc_id, doc in self.documents.items():
            if "sabg" in doc_id or "secretaria_anticorrupcion" in doc_id.lower():
                sabg_doc = doc
                results["documents"].append(doc.title)
                break
        
        if not sabg_doc:
            results["violations"].append(
                "Reglamento Interior SABG no disponible para validación de atribuciones"
            )
            return results
        
        # Buscar atribuciones específicas de la unidad
        unit_searches = [
            unit,
            f"dirección {unit.lower()}",
            f"unidad {unit.lower()}",
            f"coordinación {unit.lower()}"
        ]
        
        unit_attributions_found = False
        
        for search_term in unit_searches:
            search_results = sabg_doc.semantic_search_jaccard(search_term, max_results=3)
            
            if search_results:
                unit_attributions_found = True
                results["evidence"].append(
                    f"Atribuciones encontradas para {unit} en Reglamento SABG"
                )
                
                # Validar cada función contra atribuciones encontradas
                for i, function in enumerate(functions, 1):
                    function_validated = False
                    
                    # Extraer palabras clave de la función
                    function_keywords = set(re.findall(r'\w+', function.lower()))
                    
                    for result in search_results:
                        snippet_words = set(re.findall(r'\w+', result.content_snippet.lower()))
                        overlap = function_keywords.intersection(snippet_words)
                        
                        if len(overlap) >= 2:  # Al menos 2 palabras en común
                            function_validated = True
                            results["evidence"].append(
                                f"Función {i} respaldada por normativa: {', '.join(list(overlap)[:3])}"
                            )
                            break
                    
                    if not function_validated:
                        results["warnings"].append(
                            f"Función {i} no tiene respaldo claro en atribuciones específicas de {unit}"
                        )
                break
        
        if not unit_attributions_found:
            results["violations"].append(
                f"No se encontraron atribuciones específicas para la unidad '{unit}' en Reglamento Interior SABG"
            )
        
        return results
    
    def _validate_hierarchical_consistency(self, level: str, functions: List[str], unit: str) -> Dict:
        """Valida consistencia jerárquica contra normativa"""
        results = {
            "violations": [],
            "warnings": [],
            "evidence": []
        }
        
        if level not in ['G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P']:
            results["violations"].append(f"Nivel jerárquico no reconocido: {level}")
            return results
        
        # Buscar referencias al nivel jerárquico en normativa
        hierarchy_terms = {
            'G': ["secretaría", "titular"],
            'H': ["subsecretaría", "oficialía mayor"],
            'J': ["jefatura de unidad"],
            'K': ["dirección general"],
            'L': ["dirección general adjunta"],
            'M': ["dirección de área", "coordinación"],
            'N': ["subdirección"],
            'O': ["jefatura de departamento"],
            'P': ["enlace"]
        }
        
        expected_terms = hierarchy_terms.get(level, [])
        
        # Buscar en documentos normativos referencias al nivel
        for term in expected_terms:
            search_results = self.semantic_search(f"{term} atribuciones facultades", max_results=2)
            
            if search_results:
                results["evidence"].append(
                    f"Encontradas referencias normativas para nivel {level}: {term}"
                )
                
                # Verificar si las funciones son apropiadas para el nivel
                high_impact_indicators = [
                    "normar", "establecer", "dictar", "representar", "autorizar"
                ]
                low_impact_indicators = [
                    "ejecutar", "realizar", "efectuar", "tramitar", "capturar"
                ]
                
                has_high_impact = any(
                    any(indicator in func.lower() for indicator in high_impact_indicators)
                    for func in functions
                )
                
                has_low_impact = any(
                    any(indicator in func.lower() for indicator in low_impact_indicators)
                    for func in functions
                )
                
                # Validar apropiabilidad según nivel
                if level in ['G', 'H', 'J', 'K'] and has_low_impact:
                    results["warnings"].append(
                        f"Puesto nivel {level} con funciones de bajo impacto detectadas"
                    )
                elif level in ['O', 'P'] and has_high_impact:
                    results["warnings"].append(
                        f"Puesto nivel {level} con funciones de alto impacto detectadas"
                    )
                
                break
        
        return results
    
    def _validate_against_superior_framework(self, functions: List[str], level: str) -> Dict:
        """Valida contra marco normativo superior (CPEUM, Ley Orgánica)"""
        results = {
            "violations": [],
            "warnings": [],
            "evidence": [],
            "documents": []
        }
        
        # Buscar documentos de alta prioridad
        high_priority_docs = [doc for doc in self.documents.values() if doc.priority <= 2]
        
        if not high_priority_docs:
            results["warnings"].append(
                "No se encontraron documentos normativos de alta prioridad para validación"
            )
            return results
        
        # Buscar principios fundamentales que podrían ser violados
        prohibited_functions = [
            "impartir justicia",
            "legislar",
            "ejercer soberanía",
            "representar al estado mexicano"
        ]
        
        for function in functions:
            function_lower = function.lower()
            
            for prohibited in prohibited_functions:
                if prohibited in function_lower:
                    results["violations"].append(
                        f"Función potencialmente fuera del ámbito de competencia: '{function[:100]}...'"
                    )
                    break
        
        # Verificar alineación con principios de administración pública
        admin_principles = self.semantic_search(
            "administración pública federal principios eficiencia eficacia", 
            max_results=3
        )
        
        if admin_principles:
            results["evidence"].append(
                "Marco normativo superior disponible para validación de principios"
            )
            results["documents"].extend([result.document_title for result in admin_principles])
        
        return results
    
    def _generate_compliance_recommendations(self, violations: List[str], 
                                           warnings: List[str], 
                                           level: str) -> List[str]:
        """Genera recomendaciones específicas para mejorar compliance"""
        recommendations = []
        
        if violations:
            recommendations.append(
                "CRÍTICO: Revisar funciones que exceden competencias legales de la unidad"
            )
            recommendations.append(
                "Consultar específicamente el Reglamento Interior SABG para atribuciones exactas"
            )
        
        if warnings:
            recommendations.append(
                "MODERADO: Clarificar funciones ambiguas o con términos vagos"
            )
            if level in ['M', 'N', 'O', 'P']:
                recommendations.append(
                    f"Para nivel {level}, usar verbos más específicos y operativos"
                )
            elif level in ['G', 'H', 'J', 'K']:
                recommendations.append(
                    f"Para nivel {level}, enfocarse en funciones estratégicas y de coordinación"
                )
        
        # Recomendaciones específicas por nivel
        level_recommendations = {
            'M': "Enfocarse en coordinación y supervisión de procesos específicos",
            'N': "Detallar actividades de apoyo técnico especializado", 
            'O': "Especificar actividades operativas y de gestión directa",
            'P': "Detallar actividades de enlace, ejecución y apoyo administrativo"
        }
        
        if level in level_recommendations:
            recommendations.append(level_recommendations[level])
        
        return recommendations
    
    # ==========================================
    # MÉTODOS DE ESTADÍSTICAS Y DEBUGGING
    # ==========================================
    
    def get_loader_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas del loader"""
        cache_stats = self.cache.get_stats()
        
        stats = {
            "agent_info": self.get_agent_summary(),
            "loading_stats": self.load_stats,
            "documents_info": {
                "total_loaded": len(self.documents),
                "by_priority": {
                    str(priority): len([d for d in self.documents.values() if d.priority == priority])
                    for priority in range(1, 5)
                },
                "total_words": sum(doc.word_count for doc in self.documents.values()),
                "total_chunks": sum(len(doc.semantic_chunks) for doc in self.documents.values())
            },
            "cache_stats": cache_stats,
            "index_stats": {
                "global_keywords": len(self.global_keyword_index),
                "documents_hash": self.documents_hash[:16] + "..." if self.documents_hash else None
            }
        }
        
        # Agregar estadísticas de embeddings si están habilitados
        if self.embeddings_initialized and self.embedding_engine:
            embedding_stats = self.embedding_engine.get_cache_stats()
            stats["embedding_stats"] = {
                "mode": self.embedding_mode,
                "initialized": self.embeddings_initialized,
                "cache_stats": embedding_stats
            }
        
        return stats
    
    def export_debug_info(self, output_file: str = "normativa_debug.json") -> str:
        """Exporta información de debugging"""
        debug_data = {
            "export_timestamp": datetime.now().isoformat(),
            "loader_stats": self.get_loader_stats(),
            "documents": {
                doc_id: {
                    "title": doc.title,
                    "priority": doc.priority,
                    "scope": doc.scope,
                    "word_count": doc.word_count,
                    "chunks_count": len(doc.semantic_chunks),
                    "articles_count": len(doc.article_index),
                    "sections": list(doc.section_index.keys()),
                    "metadata": doc.metadata,
                    "embeddings_created": doc.embeddings_created
                }
                for doc_id, doc in self.documents.items()
            },
            "context_summary": self.context.get_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        return f"Debug info exportado a: {output_file}"


# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def create_normativa_loader(directory: str = None, context: APFContext = None) -> NormativaLoader:
    """Factory function para crear loader con configuración por defecto"""
    return NormativaLoader(directory, context)

def quick_compliance_check(loader: NormativaLoader,
                          functions_list: List[str],
                          unit: str = "SABG",
                          level: str = "M",
                          position_title: str = None) -> Dict[str, Any]:
    """Función rápida para validación de compliance"""
    if not loader.initialized:
        loader.initialize()
    
    result = loader.validate_compliance_advanced(
        functions_list, unit, level, position_title
    )
    
    return {
        "is_compliant": result.is_compliant,
        "confidence_score": result.confidence_score,
        "total_violations": len(result.violations),
        "total_warnings": len(result.warnings),
        "summary": f"{'✅ CUMPLE' if result.is_compliant else '❌ NO CUMPLE'} - "
                   f"Confianza: {result.confidence_score:.2%}",
        "top_recommendations": result.recommendations[:3]
    }

def test_normativa_loader_enhanced(directory: str = None) -> bool:
    """Test completo del normativa loader mejorado"""
    print("🧪 TESTING NORMATIVA LOADER v4.0 CON EMBEDDINGS")
    print("=" * 60)
    
    try:
        # Crear loader
        context = APFContext("TEST_NORMATIVA")
        loader = create_normativa_loader(directory, context)
        
        # Test inicialización
        print("\nTest 1: Inicialización con embeddings...")
        if not loader.initialize(use_embeddings=True):
            print("❌ Fallo en inicialización")
            return False
        print(f"✅ Inicialización exitosa (modo: {loader.embedding_mode})")
        
        # Test búsqueda semántica
        print("\nTest 2: Búsqueda semántica...")
        results = loader.semantic_search("atribuciones director transparencia")
        print(f"✅ Encontrados {len(results)} resultados")
        if results:
            print(f"   Top result: [{results[0].match_type}] Score: {results[0].confidence_score:.3f}")
        
        # Test validación de compliance
        print("\nTest 3: Validación de compliance...")
        test_functions = [
            "Coordinar las actividades de transparencia",
            "Supervisar el cumplimiento normativo",
            "Elaborar reportes especializados"
        ]
        
        compliance = loader.validate_compliance_advanced(
            test_functions, "Dirección de Transparencia", "M"
        )
        
        print(f"✅ Compliance: {compliance.is_compliant} "
              f"(confianza: {compliance.confidence_score:.2%})")
        
        # Test estadísticas
        print("\nTest 4: Estadísticas...")
        stats = loader.get_loader_stats()
        print(f"✅ Stats: {stats['documents_info']['total_loaded']} docs, "
              f"{stats['cache_stats']['cache_size']} cache entries")
        
        if 'embedding_stats' in stats:
            print(f"   Embeddings: {stats['embedding_stats']['mode']}, "
                  f"cache: {stats['embedding_stats']['cache_stats']['cache_size']} vectores")
        
        print("\n✅ TODOS LOS TESTS PASARON")
        return True
        
    except Exception as e:
        print(f"❌ Error en testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Ejecutar test si se ejecuta directamente
    test_result = test_normativa_loader_enhanced()
    if test_result:
        print("\n🎯 Normativa Loader v4.0 con embeddings listo para uso")
    else:
        print("\n⚠️ Normativa Loader requiere ajustes")