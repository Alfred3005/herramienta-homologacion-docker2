# -*- coding: utf-8 -*-
"""
VERB SEMANTIC ANALYZER - Sistema Inteligente de Análisis de Verbos APF v4.0
Expansión semántica de VERB_HIERARCHY con detección de sinónimos
Sistema flexible que permite adaptación a diferentes normativas
"""

import json
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
import pickle
from pathlib import Path
from datetime import datetime

from src.validators.shared_utilities import (
    APFContext, robust_openai_call, VERB_HIERARCHY, WEAK_VERBS,
    LOGGING_CONFIG
)

# ==========================================
# CONFIGURACIÓN
# ==========================================

VERB_ANALYSIS_CONFIG = {
    "enable_semantic_expansion": True,
    "cache_synonyms": True,
    "synonym_cache_file": "verb_synonyms_cache.pkl",
    "use_llm_for_ambiguity": True,
    "normativa_priority_over_guide": True,  # Normativa tiene prioridad sobre guía
    "similarity_threshold": 0.75
}

# ==========================================
# CLASES DE DATOS
# ==========================================

@dataclass
class VerbAnalysisResult:
    """Resultado de análisis de un verbo"""
    verb: str
    is_appropriate: bool
    is_weak: bool
    confidence: float
    level_category: str  # "appropriate", "forbidden", "weak", "normativa_approved", "unknown"
    reasoning: str
    source: str  # "guide", "normativa", "semantic_expansion", "llm"
    alternative_suggestions: List[str] = None

@dataclass
class VerbConflictResolution:
    """Resolución de conflicto entre guía y normativa"""
    verb: str
    guide_says: str  # "appropriate", "forbidden", "weak"
    normativa_says: str
    resolution: str  # "use_normativa", "use_guide", "flag_for_review"
    reasoning: str

# ==========================================
# CLASE PRINCIPAL
# ==========================================

class VerbSemanticAnalyzer:
    """
    Analizador semántico de verbos con expansión inteligente
    Maneja VERB_HIERARCHY como guía base pero permite adaptación
    """

    def __init__(self, context: APFContext = None, normativa_loader = None):
        self.context = context or APFContext()
        self.verb_hierarchy = VERB_HIERARCHY.copy()
        self.weak_verbs_base = WEAK_VERBS.copy()

        # Caché de sinónimos expandidos
        self.synonym_cache: Dict[str, List[str]] = {}
        self.weak_verbs_expanded: Set[str] = set(WEAK_VERBS)

        # Verbos aprobados por normativa (tiene prioridad)
        self.normativa_approved_verbs: Dict[str, Set[str]] = {}  # {nivel: {verbos}}

        # Normativa loader para búsqueda de verbos en documentos normativos
        self.normativa_loader = normativa_loader

        self.initialized = False
        self._load_synonym_cache()

    def _load_synonym_cache(self):
        """Carga caché de sinónimos si existe"""
        cache_file = Path(VERB_ANALYSIS_CONFIG["synonym_cache_file"])
        if cache_file.exists() and VERB_ANALYSIS_CONFIG["cache_synonyms"]:
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.synonym_cache = cache_data.get("synonyms", {})
                    self.weak_verbs_expanded = set(cache_data.get("weak_expanded", WEAK_VERBS))
                if LOGGING_CONFIG["enable_detailed_logging"]:
                    print(f"[VerbAnalyzer] Caché cargado: {len(self.synonym_cache)} verbos")
            except Exception as e:
                print(f"[VerbAnalyzer] No se pudo cargar caché: {e}")

    def _save_synonym_cache(self):
        """Guarda caché de sinónimos"""
        if not VERB_ANALYSIS_CONFIG["cache_synonyms"]:
            return

        cache_file = Path(VERB_ANALYSIS_CONFIG["synonym_cache_file"])
        try:
            cache_data = {
                "synonyms": self.synonym_cache,
                "weak_expanded": list(self.weak_verbs_expanded),
                "timestamp": datetime.now().isoformat()
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            print(f"[VerbAnalyzer] Error guardando caché: {e}")

    def load_normativa_verbs(self, normativa_verb_mapping: Dict[str, List[str]]):
        """
        Carga verbos extraídos de la normativa oficial

        Args:
            normativa_verb_mapping: {nivel_jerarquico: [lista_verbos_aprobados]}
        """
        self.normativa_approved_verbs = {
            nivel: set(verbos) for nivel, verbos in normativa_verb_mapping.items()
        }

        if LOGGING_CONFIG["enable_detailed_logging"]:
            total_verbs = sum(len(v) for v in self.normativa_approved_verbs.values())
            print(f"[VerbAnalyzer] Cargados {total_verbs} verbos de normativa para {len(self.normativa_approved_verbs)} niveles")

    def get_verb_synonyms(self, verb: str, use_llm: bool = True) -> List[str]:
        """
        Obtiene sinónimos de un verbo usando LLM

        Args:
            verb: Verbo a analizar
            use_llm: Si usar LLM para expansión (caché primero)

        Returns:
            Lista de sinónimos
        """
        # Verificar caché primero
        if verb in self.synonym_cache:
            return self.synonym_cache[verb]

        if not use_llm or not VERB_ANALYSIS_CONFIG["enable_semantic_expansion"]:
            return [verb]

        # Usar LLM para generar sinónimos
        prompt = f"""Analiza el verbo "{verb}" en el contexto de la Administración Pública Federal de México.

Proporciona una lista de sinónimos y verbos relacionados que tengan el MISMO nivel de jerarquía y responsabilidad.

IMPORTANTE: Solo incluir verbos que impliquen el mismo tipo de responsabilidad (estratégica, táctica u operativa).

Responde en formato JSON:
{{
    "synonyms": ["verbo1", "verbo2", "verbo3"],
    "category": "estratégico/táctico/operativo",
    "reasoning": "breve explicación"
}}"""

        llm_result = robust_openai_call(
            prompt=prompt,
            max_tokens=300,
            temperature=0.1,
            context=self.context
        )

        if llm_result["status"] == "success":
            data = llm_result.get("data", {})
            synonyms = data.get("synonyms", [verb])

            # Agregar el verbo original
            if verb not in synonyms:
                synonyms.insert(0, verb)

            # Guardar en caché
            self.synonym_cache[verb] = synonyms
            self._save_synonym_cache()

            return synonyms

        # Fallback: solo el verbo original
        return [verb]

    def is_verb_weak_or_ambiguous(self, verb: str, check_synonyms: bool = True) -> Tuple[bool, str]:
        """
        Verifica si un verbo es débil o ambiguo

        Args:
            verb: Verbo a verificar
            check_synonyms: Si verificar también sinónimos

        Returns:
            (is_weak, reasoning)
        """
        verb_lower = verb.lower().strip()

        # Verificar lista base
        if verb_lower in self.weak_verbs_base:
            return True, f"'{verb}' está en la lista de verbos no recomendados (demasiado ambiguo)"

        # Verificar expansión de sinónimos
        if check_synonyms and verb_lower in self.weak_verbs_expanded:
            return True, f"'{verb}' es sinónimo de un verbo no recomendado"

        # Usar LLM para análisis de ambigüedad si está habilitado
        if VERB_ANALYSIS_CONFIG["use_llm_for_ambiguity"]:
            return self._check_ambiguity_with_llm(verb)

        return False, ""

    def _check_ambiguity_with_llm(self, verb: str) -> Tuple[bool, str]:
        """Verifica ambigüedad de verbo usando LLM"""

        # Crear lista de verbos débiles conocidos para contexto
        weak_examples = ", ".join(self.weak_verbs_base[:5])

        prompt = f"""Analiza si el verbo "{verb}" es DEMASIADO AMBIGUO o GENÉRICO para una descripción de puesto de la Administración Pública Federal.

Verbos considerados débiles/ambiguos incluyen: {weak_examples}, etc.

Un verbo es débil si:
- Es demasiado genérico (ej: "apoyar", "ayudar")
- No define claramente la responsabilidad
- Puede interpretarse de muchas formas diferentes

Responde en formato JSON:
{{
    "is_weak": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explicación breve"
}}"""

        llm_result = robust_openai_call(
            prompt=prompt,
            max_tokens=200,
            temperature=0.1,
            context=self.context
        )

        if llm_result["status"] == "success":
            data = llm_result.get("data", {})
            is_weak = data.get("is_weak", False)
            reasoning = data.get("reasoning", "Análisis LLM")
            confidence = data.get("confidence", 0.5)

            # Expandir lista si confianza es alta
            if is_weak and confidence > 0.75:
                self.weak_verbs_expanded.add(verb.lower())
                self._save_synonym_cache()

            return is_weak, reasoning

        return False, ""

    def analyze_verb_for_level(self, verb: str, nivel_jerarquico: str,
                               normativa_context: Optional[str] = None) -> VerbAnalysisResult:
        """
        Analiza si un verbo es apropiado para un nivel jerárquico

        Args:
            verb: Verbo a analizar
            nivel_jerarquico: Nivel jerárquico (G, H, J, K, L, M, N, O, P)
            normativa_context: Contexto adicional de normativa

        Returns:
            VerbAnalysisResult con análisis completo
        """
        verb_lower = verb.lower().strip()

        # 1. Verificar si es verbo débil (prioridad máxima)
        is_weak, weak_reason = self.is_verb_weak_or_ambiguous(verb)
        if is_weak:
            return VerbAnalysisResult(
                verb=verb,
                is_appropriate=False,
                is_weak=True,
                confidence=0.9,
                level_category="weak",
                reasoning=weak_reason,
                source="guide",
                alternative_suggestions=self._get_strong_alternatives(verb, nivel_jerarquico)
            )

        # 2. Verificar en normativa (segunda prioridad)
        if VERB_ANALYSIS_CONFIG["normativa_priority_over_guide"]:
            if nivel_jerarquico in self.normativa_approved_verbs:
                if verb_lower in self.normativa_approved_verbs[nivel_jerarquico]:
                    return VerbAnalysisResult(
                        verb=verb,
                        is_appropriate=True,
                        is_weak=False,
                        confidence=1.0,
                        level_category="normativa_approved",
                        reasoning=f"Verbo aprobado explícitamente en normativa para nivel {nivel_jerarquico}",
                        source="normativa"
                    )

        # 3. Verificar en guía VERB_HIERARCHY
        if nivel_jerarquico not in self.verb_hierarchy:
            return VerbAnalysisResult(
                verb=verb,
                is_appropriate=False,
                is_weak=False,
                confidence=0.3,
                level_category="unknown",
                reasoning=f"Nivel jerárquico '{nivel_jerarquico}' no reconocido",
                source="guide"
            )

        level_info = self.verb_hierarchy[nivel_jerarquico]
        appropriate_verbs = [v.lower() for v in level_info.get("appropriate_verbs", [])]
        forbidden_verbs = [v.lower() for v in level_info.get("forbidden_verbs", [])]

        # Verificar directamente
        if verb_lower in appropriate_verbs:
            return VerbAnalysisResult(
                verb=verb,
                is_appropriate=True,
                is_weak=False,
                confidence=0.95,
                level_category="appropriate",
                reasoning=f"Verbo apropiado según guía para nivel {nivel_jerarquico} ({level_info['level_name']})",
                source="guide"
            )

        if verb_lower in forbidden_verbs:
            return VerbAnalysisResult(
                verb=verb,
                is_appropriate=False,
                is_weak=False,
                confidence=0.9,
                level_category="forbidden",
                reasoning=f"Verbo no apropiado para nivel {nivel_jerarquico} según guía",
                source="guide",
                alternative_suggestions=appropriate_verbs[:5]
            )

        # 4. Expansión semántica - verificar sinónimos
        if VERB_ANALYSIS_CONFIG["enable_semantic_expansion"]:
            synonyms = self.get_verb_synonyms(verb, use_llm=True)

            for syn in synonyms:
                syn_lower = syn.lower()
                if syn_lower in appropriate_verbs:
                    return VerbAnalysisResult(
                        verb=verb,
                        is_appropriate=True,
                        is_weak=False,
                        confidence=0.75,
                        level_category="appropriate",
                        reasoning=f"Verbo aceptado como sinónimo de '{syn}' (apropiado para nivel {nivel_jerarquico})",
                        source="semantic_expansion"
                    )

                if syn_lower in forbidden_verbs:
                    return VerbAnalysisResult(
                        verb=verb,
                        is_appropriate=False,
                        is_weak=False,
                        confidence=0.7,
                        level_category="forbidden",
                        reasoning=f"Verbo relacionado con '{syn}' (no apropiado para nivel {nivel_jerarquico})",
                        source="semantic_expansion",
                        alternative_suggestions=appropriate_verbs[:5]
                    )

        # 5. Análisis con LLM como último recurso
        if normativa_context:
            return self._analyze_with_llm_and_context(verb, nivel_jerarquico, normativa_context, level_info)

        # 6. Verbo no categorizado - generar flag de revisión
        return VerbAnalysisResult(
            verb=verb,
            is_appropriate=None,  # Desconocido
            is_weak=False,
            confidence=0.4,
            level_category="unknown",
            reasoning=f"Verbo no encontrado en guías para nivel {nivel_jerarquico}. Requiere revisión con normativa específica.",
            source="guide",
            alternative_suggestions=appropriate_verbs[:5]
        )

    def _analyze_with_llm_and_context(self, verb: str, nivel_jerarquico: str,
                                     normativa_context: str, level_info: Dict) -> VerbAnalysisResult:
        """Análisis contextual con LLM usando normativa"""

        appropriate_examples = ", ".join(level_info.get("appropriate_verbs", [])[:5])

        prompt = f"""Analiza si el verbo "{verb}" es apropiado para un puesto de nivel {nivel_jerarquico} ({level_info['level_name']}) en la Administración Pública Federal.

CONTEXTO DE LA NORMATIVA:
{normativa_context[:1000]}

VERBOS TÍPICAMENTE APROPIADOS PARA ESTE NIVEL:
{appropriate_examples}

PERFIL DE IMPACTO ESPERADO:
- Alcance de decisión: {level_info['impact_profile'].get('decision_scope', 'N/A')}
- Consecuencias de error: {level_info['impact_profile'].get('error_consequences', 'N/A')}

¿El verbo "{verb}" corresponde a este nivel de responsabilidad?

Responde en formato JSON:
{{
    "is_appropriate": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explicación basada en normativa y perfil",
    "alternative_if_inappropriate": ["verbo1", "verbo2"]
}}"""

        llm_result = robust_openai_call(
            prompt=prompt,
            max_tokens=400,
            temperature=0.1,
            context=self.context
        )

        if llm_result["status"] == "success":
            data = llm_result.get("data", {})
            is_appropriate = data.get("is_appropriate", False)
            confidence = data.get("confidence", 0.5)
            reasoning = data.get("reasoning", "Análisis LLM con contexto normativo")
            alternatives = data.get("alternative_if_inappropriate", [])

            return VerbAnalysisResult(
                verb=verb,
                is_appropriate=is_appropriate,
                is_weak=False,
                confidence=confidence,
                level_category="normativa_approved" if is_appropriate else "forbidden",
                reasoning=reasoning,
                source="llm",
                alternative_suggestions=alternatives
            )

        # Fallback
        return VerbAnalysisResult(
            verb=verb,
            is_appropriate=False,
            is_weak=False,
            confidence=0.3,
            level_category="unknown",
            reasoning="No se pudo analizar con LLM",
            source="guide"
        )

    def _get_strong_alternatives(self, weak_verb: str, nivel_jerarquico: str) -> List[str]:
        """Obtiene alternativas fuertes para un verbo débil"""
        if nivel_jerarquico not in self.verb_hierarchy:
            return []

        appropriate = self.verb_hierarchy[nivel_jerarquico].get("appropriate_verbs", [])
        return appropriate[:5]  # Top 5 sugerencias

    def resolve_verb_conflict(self, verb: str, nivel_jerarquico: str,
                             guide_result: VerbAnalysisResult,
                             normativa_says_appropriate: bool) -> VerbConflictResolution:
        """
        Resuelve conflicto cuando guía y normativa difieren

        Args:
            verb: Verbo en cuestión
            nivel_jerarquico: Nivel jerárquico
            guide_result: Resultado según guía
            normativa_says_appropriate: Lo que dice normativa

        Returns:
            Resolución del conflicto
        """

        # REGLA: Normativa tiene prioridad si está configurado así
        if VERB_ANALYSIS_CONFIG["normativa_priority_over_guide"]:
            if normativa_says_appropriate and not guide_result.is_appropriate:
                return VerbConflictResolution(
                    verb=verb,
                    guide_says="inappropriate" if not guide_result.is_appropriate else "appropriate",
                    normativa_says="appropriate",
                    resolution="use_normativa",
                    reasoning=f"Normativa explícita tiene prioridad. Verbo aprobado para nivel {nivel_jerarquico} aunque no esté en guía de buenas prácticas. Se levanta anotación."
                )

            if not normativa_says_appropriate and guide_result.is_appropriate:
                return VerbConflictResolution(
                    verb=verb,
                    guide_says="appropriate",
                    normativa_says="not_found_or_inappropriate",
                    resolution="flag_for_review",
                    reasoning=f"Verbo apropiado según guía pero no validado en normativa específica. Requiere revisión."
                )

        # Sin conflicto
        return VerbConflictResolution(
            verb=verb,
            guide_says="appropriate" if guide_result.is_appropriate else "inappropriate",
            normativa_says="appropriate" if normativa_says_appropriate else "inappropriate",
            resolution="no_conflict",
            reasoning="Guía y normativa están alineadas"
        )

    def is_verb_in_normativa(self, verb: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica si un verbo aparece en los documentos normativos cargados

        Args:
            verb: Verbo a buscar (en infinitivo)

        Returns:
            (found, evidence): True si se encuentra en normativa, con evidencia opcional
        """
        if not self.normativa_loader:
            return False, None

        # Verificar que la normativa esté cargada
        if not hasattr(self.normativa_loader, 'documents') or not self.normativa_loader.documents:
            return False, None

        verb_lower = verb.lower().strip()

        # Buscar el verbo en los documentos normativos
        # self.normativa_loader.documents es un Dict[str, NormativeDocument]
        for doc_id, doc in self.normativa_loader.documents.items():
            # Acceder al contenido del documento (NormativeDocument es un dataclass)
            doc_text = getattr(doc, 'content', '') if hasattr(doc, 'content') else ''

            if not doc_text:
                continue

            doc_text_lower = doc_text.lower()
            doc_name = getattr(doc, 'title', '') or getattr(doc, 'file_path', 'normativa')

            # Buscar el verbo (con diferentes conjugaciones posibles)
            # Buscamos el infinitivo y formas conjugadas comunes
            conjugations = [
                verb_lower,  # infinitivo
                verb_lower + 'r',  # por si falta la 'r'
                verb_lower[:-1] if verb_lower.endswith('r') else verb_lower,  # raíz
            ]

            for conjugation in conjugations:
                if conjugation in doc_text_lower:
                    # Encontrado - extraer contexto
                    idx = doc_text_lower.find(conjugation)
                    context_start = max(0, idx - 50)
                    context_end = min(len(doc_text), idx + 100)
                    context = doc_text[context_start:context_end].replace('\n', ' ')

                    evidence = f"Encontrado en {doc_name[:30]}: ...{context}..."
                    return True, evidence

        return False, None

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del analizador"""
        return {
            "cached_synonyms": len(self.synonym_cache),
            "weak_verbs_base": len(self.weak_verbs_base),
            "weak_verbs_expanded": len(self.weak_verbs_expanded),
            "normativa_levels_loaded": len(self.normativa_approved_verbs),
            "total_normativa_verbs": sum(len(v) for v in self.normativa_approved_verbs.values()),
            "semantic_expansion_enabled": VERB_ANALYSIS_CONFIG["enable_semantic_expansion"],
            "normativa_priority": VERB_ANALYSIS_CONFIG["normativa_priority_over_guide"]
        }

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def create_verb_analyzer(context: APFContext = None, normativa_loader = None) -> VerbSemanticAnalyzer:
    """Factory function para crear analizador"""
    return VerbSemanticAnalyzer(context, normativa_loader)

def test_verb_analyzer():
    """Test básico del analizador"""
    print("🧪 TESTING VERB SEMANTIC ANALYZER")
    print("=" * 50)

    analyzer = create_verb_analyzer()

    # Test 1: Verbo apropiado
    result = analyzer.analyze_verb_for_level("coordinar", "M")
    print(f"\n✅ Test 'coordinar' para nivel M:")
    print(f"   Apropiado: {result.is_appropriate}")
    print(f"   Confianza: {result.confidence}")
    print(f"   Razón: {result.reasoning}")

    # Test 2: Verbo débil
    result = analyzer.analyze_verb_for_level("apoyar", "M")
    print(f"\n⚠️ Test 'apoyar' para nivel M:")
    print(f"   Es débil: {result.is_weak}")
    print(f"   Razón: {result.reasoning}")

    # Test 3: Resumen
    summary = analyzer.get_analysis_summary()
    print(f"\n📊 Resumen del analizador:")
    for key, value in summary.items():
        print(f"   {key}: {value}")

    print("\n✅ Tests completados")

if __name__ == "__main__":
    test_verb_analyzer()
