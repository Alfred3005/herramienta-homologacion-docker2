# -*- coding: utf-8 -*-
"""
CONTEXTUAL VERB VALIDATOR - Validación Inteligente de Verbos con LLM
Sistema de validación con dos modos: HÍBRIDO (rápido) y COMPLETO (detallado)

MODO HÍBRIDO:
- Validación de umbrales (cantidad de verbos débiles)
- 1 llamada LLM global que valida TODO el puesto vs normativa
- Rápido y económico

MODO COMPLETO:
- Validación función por función con contexto normativo
- Validación de herencia jerárquica
- Validación de apropiación de alcance por nivel
- Máxima precisión
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.validators.shared_utilities import (
    APFContext, robust_openai_call, VERB_HIERARCHY, WEAK_VERBS,
    LOGGING_CONFIG
)

# ==========================================
# CONFIGURACIÓN
# ==========================================

VALIDATION_CONFIG = {
    # Modo de validación: "HYBRID" o "COMPLETE"
    "validation_mode": "HYBRID",  # Cambiar a "COMPLETE" para modo detallado

    # Umbrales para modo híbrido
    "weak_verb_threshold": 20,  # Máximo de verbos débiles permitidos
    "completeness_min_threshold": 0.5,  # 50% mínimo de funciones esperadas
    "completeness_max_threshold": 2.0,  # 200% máximo (sobrecarga)

    # Configuración LLM
    "llm_temperature": 0.0,  # Determinístico
    "llm_max_tokens": 1500,
    "use_cache": True
}

# Jerarquía de alcance de verbos (de menor a mayor)
ALCANCE_VERBOS = {
    1: {"nivel": "Operativo", "verbos": ["recopilar", "registrar", "archivar", "transcribir"]},
    2: {"nivel": "Técnico", "verbos": ["elaborar", "preparar", "calcular", "procesar"]},
    3: {"nivel": "Supervisión", "verbos": ["verificar", "revisar", "controlar", "validar"]},
    4: {"nivel": "Analítico", "verbos": ["evaluar", "analizar", "diagnosticar", "investigar"]},
    5: {"nivel": "Asesoría", "verbos": ["proponer", "recomendar", "sugerir", "asesorar"]},
    6: {"nivel": "Coordinación", "verbos": ["coordinar", "gestionar", "organizar", "programar"]},
    7: {"nivel": "Gerencial", "verbos": ["administrar", "supervisar", "dirigir equipos", "implementar"]},
    8: {"nivel": "Decisión", "verbos": ["aprobar", "autorizar", "resolver", "decidir"]},
    9: {"nivel": "Estratégico", "verbos": ["dirigir", "establecer", "definir políticas", "planear"]},
    10: {"nivel": "Normativo", "verbos": ["sancionar", "expedir", "decretar", "legislar"]}
}

# Mapeo de niveles jerárquicos a alcances apropiados
NIVEL_TO_ALCANCE = {
    "G11": (7, 10),  # Secretario: Gerencial-Normativo
    "J31": (5, 8),   # Titular OAD: Asesoría-Decisión
    "M1": (4, 7),    # Director: Analítico-Gerencial
    "P3": (1, 5),    # Jefe Depto: Operativo-Asesoría
}

# ==========================================
# CLASES DE DATOS
# ==========================================

@dataclass
class GlobalValidationResult:
    """Resultado de validación global (modo híbrido)"""
    is_aligned: bool  # ¿Está alineado con normativa?
    alignment_level: str  # "ALIGNED" | "PARTIALLY_ALIGNED" | "NOT_ALIGNED"
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Justificación del LLM

    # Análisis de umbrales
    weak_verbs_count: int
    weak_verbs_threshold_passed: bool
    completeness_rate: Optional[float] = None
    completeness_threshold_passed: bool = True

    # Detección de problemas estructurales
    structural_issues: List[str] = field(default_factory=list)
    normativa_mismatches: List[str] = field(default_factory=list)

    # Validación de referencias institucionales (nuevos campos)
    institutional_references_match: bool = True  # ¿Referencias institucionales coinciden?
    has_hierarchical_backing: bool = False  # ¿Hay herencia jerárquica válida?

    # Metadatos
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class DetailedValidationResult:
    """Resultado de validación detallada (modo completo)"""
    # Campos requeridos (sin valor por defecto)
    function_number: int
    function_text: str
    verb: str
    normative_backed: bool
    backing_type: str  # "DIRECT" | "DERIVED" | "HIERARCHICAL" | "NOT_BACKED"
    appropriate_for_level: bool

    # Campos opcionales (con valor por defecto)
    normative_source: Optional[str] = None
    expected_alcance_range: Tuple[int, int] = (0, 0)
    actual_alcance: int = 0
    severity: str = "MINOR"  # "MINOR" | "MODERATE" | "CRITICAL"
    suggested_alternative: Optional[str] = None
    reasoning: str = ""
    confidence: float = 0.0

# ==========================================
# CLASE PRINCIPAL
# ==========================================

class ContextualVerbValidator:
    """
    Validador contextual de verbos con dos modos de operación
    """

    def __init__(self, normativa_loader=None, context: APFContext = None):
        self.normativa_loader = normativa_loader
        self.context = context or APFContext()
        self.validation_mode = VALIDATION_CONFIG["validation_mode"]

    def set_validation_mode(self, mode: str):
        """Cambia el modo de validación"""
        if mode not in ["HYBRID", "COMPLETE"]:
            raise ValueError(f"Modo inválido: {mode}. Usar 'HYBRID' o 'COMPLETE'")
        self.validation_mode = mode
        VALIDATION_CONFIG["validation_mode"] = mode

    # ==========================================
    # MODO HÍBRIDO (Rápido + LLM Global)
    # ==========================================

    def validate_global(
        self,
        puesto_nombre: str,
        objetivo_general: str,
        funciones: List[Dict[str, Any]],
        nivel_jerarquico: str,
        weak_verbs_detected: List[str]
    ) -> GlobalValidationResult:
        """
        Validación global del puesto completo (modo híbrido)

        Pasos:
        1. Validar umbrales (verbos débiles, completitud)
        2. Llamar LLM para validación semántica global
        3. Retornar resultado consolidado
        """

        # PASO 1: Validación de umbrales
        weak_verbs_count = len(weak_verbs_detected)
        weak_threshold = VALIDATION_CONFIG["weak_verb_threshold"]
        weak_verbs_pass = weak_verbs_count <= weak_threshold

        # Validar completitud de funciones
        completeness_rate = None
        completeness_pass = True

        if self.normativa_loader:
            expected_functions = self._estimate_expected_functions_count()
            if expected_functions > 0:
                completeness_rate = len(funciones) / expected_functions
                min_thresh = VALIDATION_CONFIG["completeness_min_threshold"]
                max_thresh = VALIDATION_CONFIG["completeness_max_threshold"]
                completeness_pass = min_thresh <= completeness_rate <= max_thresh

        # Si falla umbrales, retornar FAIL inmediato
        structural_issues = []
        if not weak_verbs_pass:
            structural_issues.append(
                f"Exceso de verbos débiles: {weak_verbs_count} > {weak_threshold}"
            )
        if not completeness_pass and completeness_rate is not None:
            if completeness_rate < VALIDATION_CONFIG["completeness_min_threshold"]:
                structural_issues.append(
                    f"Funciones insuficientes: {completeness_rate:.1%} < 50%"
                )
            else:
                structural_issues.append(
                    f"Sobrecarga de funciones: {completeness_rate:.1%} > 200%"
                )

        # PASO 2: Validación LLM Global
        llm_result = self._validate_with_llm_global(
            puesto_nombre=puesto_nombre,
            objetivo_general=objetivo_general,
            funciones=funciones,
            nivel_jerarquico=nivel_jerarquico
        )

        # PASO 3: Consolidar resultado con validación estricta

        # Verificar referencias institucionales
        institutional_match = llm_result.get("institutional_references_match", True)
        has_hierarchical_backing = llm_result.get("has_hierarchical_backing", False)

        # Si falla umbrales O LLM dice NOT_ALIGNED → NOT_ALIGNED
        if structural_issues or llm_result["alignment_level"] == "NOT_ALIGNED":
            alignment_level = "NOT_ALIGNED"
            is_aligned = False

        # PARTIALLY_ALIGNED: Solo aprobar si hay respaldo institucional o jerárquico válido
        elif llm_result["alignment_level"] == "PARTIALLY_ALIGNED":
            alignment_level = "PARTIALLY_ALIGNED"

            # Rechazar PARTIALLY_ALIGNED si:
            # 1. Las referencias institucionales NO coinciden (organismos/documentos diferentes)
            # 2. NO hay respaldo jerárquico válido comprobado por LLM
            if not institutional_match and not has_hierarchical_backing:
                alignment_level = "NOT_ALIGNED"
                is_aligned = False
                # Actualizar reasoning para explicar el rechazo
                llm_result["reasoning"] += " [RECHAZADO: Referencias institucionales no coinciden con normativa proporcionada y sin herencia jerárquica válida]"
            else:
                is_aligned = True  # Pasa con observaciones solo si cumple criterios

        else:  # ALIGNED
            alignment_level = "ALIGNED"
            is_aligned = True

        return GlobalValidationResult(
            is_aligned=is_aligned,
            alignment_level=alignment_level,
            confidence=llm_result["confidence"],
            reasoning=llm_result["reasoning"],
            weak_verbs_count=weak_verbs_count,
            weak_verbs_threshold_passed=weak_verbs_pass,
            completeness_rate=completeness_rate,
            completeness_threshold_passed=completeness_pass,
            structural_issues=structural_issues,
            normativa_mismatches=llm_result.get("normativa_mismatches", []),
            institutional_references_match=institutional_match,
            has_hierarchical_backing=has_hierarchical_backing
        )

    def _validate_with_llm_global(
        self,
        puesto_nombre: str,
        objetivo_general: str,
        funciones: List[Dict[str, Any]],
        nivel_jerarquico: str
    ) -> Dict[str, Any]:
        """
        Llamada LLM para validación semántica global del puesto
        """

        # Construir texto de funciones
        funciones_text = "\n".join([
            f"{i}. {f.get('verbo_accion', '')} - {f.get('descripcion_completa', '')[:150]}"
            for i, f in enumerate(funciones, 1)
        ])

        # Crear query de búsqueda con objetivo general + funciones principales
        search_query = f"{objetivo_general} {' '.join([f.get('descripcion_completa', '')[:100] for f in funciones[:5]])}"

        # Obtener contexto normativo relevante con búsqueda semántica
        normativa_context = self._get_normativa_context_summary(search_query=search_query)

        prompt = f"""Eres un experto en análisis de descripciones de puestos de la Administración Pública Federal (APF).

TAREA: Evalúa si este puesto está ALINEADO con la normativa ESPECÍFICA que se te proporciona.

PUESTO A EVALUAR:
- NOMBRE DEL PUESTO: {puesto_nombre}
- Nivel jerárquico: {nivel_jerarquico}
- Objetivo general: {objetivo_general}

FUNCIONES ({len(funciones)} total):
{funciones_text}

NORMATIVA APLICABLE:
{normativa_context}

INSTRUCCIONES - Evalúa con PRAGMATISMO:

PASO 1 - **IDENTIFICACIÓN DEL ORGANISMO DEL PUESTO** (CRÍTICO):
   Analiza el NOMBRE DEL PUESTO para identificar el organismo:

   Ejemplos de identificación correcta:
   - "SECRETARIA(O) ANTICORRUPCION Y BUEN GOBIERNO" → Organismo: SABG (Secretaría de Anticorrupción y Buen Gobierno)
   - "COORDINADOR(A) GENERAL DE BUEN GOBIERNO" → Organismo: SABG (es un cargo dentro de SABG)
   - "TITULAR DE LA UNIDAD DE PARTICIPACION SOCIAL..." → Analiza el contexto, si menciona SABG → Organismo: SABG
   - "COMISIONADO NACIONAL DE ACUACULTURA Y PESCA" → Organismo: CONAPESCA
   - "DIRECTOR EN CONAPESCA" → Organismo: CONAPESCA

   Reglas de identificación:
   a) Si el nombre contiene "ANTICORRUPCION" o "BUEN GOBIERNO" → Organismo: SABG
   b) Si el nombre contiene "CONAPESCA" o "ACUACULTURA Y PESCA" → Organismo: CONAPESCA
   c) Si el nombre contiene "SECRETARIA DE..." → Identifica la secretaría específica
   d) Para cargos medios/bajos (Coordinador, Director, Jefe, Titular): Busca referencias al organismo en objetivo/funciones

PASO 2 - **VALIDACIÓN DE REFERENCIAS INSTITUCIONALES** (CRITERIO PRINCIPAL):
   - Identifica el organismo de la NORMATIVA PROPORCIONADA (busca en título, fragmentos)
   - PREGUNTA CRÍTICA: ¿El organismo del puesto (identificado en PASO 1) coincide con el organismo de la normativa?
   - CRITERIO DE RECHAZO ABSOLUTO: Si son organismos DIFERENTES → NOT_ALIGNED inmediatamente

   Ejemplos correctos:
   - Puesto SABG vs Normativa SABG → ✅ Coinciden, continuar evaluación
   - Puesto CONAPESCA vs Normativa CONAPESCA → ✅ Coinciden, continuar evaluación

   Ejemplos incorrectos:
   - Puesto SABG vs Normativa CONAPESCA → ❌ NO COINCIDEN → NOT_ALIGNED
   - Puesto CONAPESCA vs Normativa SABG → ❌ NO COINCIDEN → NOT_ALIGNED

PASO 3 - **VERIFICACIÓN DE ALINEACIÓN FUNCIONAL** (CRITERIO FLEXIBLE):
   Solo aplica si PASO 2 es exitoso (organismos coinciden):
   - Tienes acceso a FRAGMENTOS RELEVANTES del contenido normativo
   - Las funciones pueden estar:
     * EXPLÍCITAMENTE mencionadas en fragmentos
     * DERIVADAS o RELACIONADAS con atribuciones del organismo
     * En el ÁMBITO DE COMPETENCIA del organismo según la normativa
   - ACEPTA: Funciones razonables para el organismo aunque no sean idénticas al texto normativo
   - ACEPTA: Derivaciones lógicas de atribuciones generales del organismo
   - RECHAZA: Funciones que NO tienen relación con el ámbito del organismo

PASO 4 - **HERENCIA JERÁRQUICA** (CRITERIO ADICIONAL):
   - Para puestos de niveles inferiores: ¿Estas funciones podrían ser delegadas del superior?
   - Para puestos de alto nivel: ¿Estas funciones son coherentes con la dirección del organismo?
   - Documenta si existe herencia jerárquica válida en el campo has_hierarchical_backing

PASO 5 - **Coherencia General**:
   - ¿El alcance de las funciones es razonable para el nivel jerárquico del puesto?
   - ¿Las funciones están en el ámbito de competencia del organismo?

DECISIÓN FINAL - Clasifica el nivel de alineación:

SI organismos NO coinciden (detectado en PASO 1-2) → NOT_ALIGNED AUTOMÁTICAMENTE

SI organismos SÍ coinciden:
- ALIGNED: Funciones están EXPLÍCITAMENTE relacionadas con el ámbito del organismo
- PARTIALLY_ALIGNED: Funciones son DERIVABLES/RAZONABLES aunque no explícitas en normativa
- NOT_ALIGNED: Funciones completamente ajenas al ámbito del organismo

RESPONDE EN JSON:
{{
  "alignment_level": "ALIGNED" | "PARTIALLY_ALIGNED" | "NOT_ALIGNED",
  "confidence": 0.0-1.0,
  "reasoning": "Justificación clara de la evaluación (2-3 oraciones)",
  "institutional_references_match": true/false,
  "references_found_in_puesto": ["organismos, documentos encontrados en descripción del puesto"],
  "references_found_in_normativa": ["organismos, documentos encontrados en normativa proporcionada"],
  "has_hierarchical_backing": true/false,
  "hierarchical_reasoning": "Explicación de si hay herencia jerárquica válida (solo si PARTIALLY_ALIGNED)",
  "normativa_mismatches": ["lista de desalineaciones detectadas"],
  "strengths": ["aspectos bien alineados"],
  "improvement_areas": ["áreas de mejora"]
}}
"""

        try:
            response = robust_openai_call(
                prompt=prompt,
                max_tokens=VALIDATION_CONFIG["llm_max_tokens"],
                temperature=VALIDATION_CONFIG["llm_temperature"],
                context=self.context
            )

            # Verificar respuesta exitosa
            if response.get("status") == "success":
                result = response["data"]
                return result
            else:
                # Error en llamada LLM - RECHAZAR por seguridad
                error_msg = response.get("error", "Error desconocido")
                print(f"⚠️ Error en validación LLM global: {error_msg}")
                return {
                    "alignment_level": "NOT_ALIGNED",
                    "confidence": 0.3,
                    "reasoning": f"Error en validación LLM: {error_msg}. Por seguridad se rechaza el puesto.",
                    "institutional_references_match": False,
                    "references_found_in_puesto": [],
                    "references_found_in_normativa": [],
                    "has_hierarchical_backing": False,
                    "hierarchical_reasoning": "",
                    "normativa_mismatches": ["Error técnico en validación"],
                    "strengths": [],
                    "improvement_areas": []
                }

        except Exception as e:
            print(f"⚠️ Error inesperado en validación LLM global: {e}")
            # Fallback seguro - RECHAZAR por seguridad
            return {
                "alignment_level": "NOT_ALIGNED",
                "confidence": 0.3,
                "reasoning": f"Error inesperado: {str(e)}. Por seguridad se rechaza el puesto.",
                "institutional_references_match": False,
                "references_found_in_puesto": [],
                "references_found_in_normativa": [],
                "has_hierarchical_backing": False,
                "hierarchical_reasoning": "",
                "normativa_mismatches": ["Error técnico en validación"],
                "strengths": [],
                "improvement_areas": []
            }

    # ==========================================
    # MODO COMPLETO (LLM Contextual Detallado)
    # ==========================================

    def validate_detailed(
        self,
        function_text: str,
        verb: str,
        nivel_jerarquico: str,
        function_number: int
    ) -> DetailedValidationResult:
        """
        Validación detallada de una función individual (modo completo)

        Valida:
        1. Respaldo normativo (DIRECTO / DERIVADO / JERÁRQUICO / NO_RESPALDADO)
        2. Apropiación de verbo para el nivel
        3. Alcance apropiado
        """

        # Obtener chunks relevantes de normativa para esta función
        relevant_chunks = self._get_relevant_normativa_chunks(function_text)

        prompt = f"""Eres un experto en análisis de descripciones de puestos de la APF.

FUNCIÓN A EVALUAR:
- Número: {function_number}
- Verbo: "{verb}"
- Descripción completa: "{function_text}"
- Nivel del puesto: {nivel_jerarquico}

NORMATIVA RELEVANTE:
{relevant_chunks}

JERARQUÍA DE VERBOS POR NIVEL:
- G11 (Secretario): dirigir, establecer, autorizar, aprobar, sancionar (alcance 7-10)
- J31 (Titular OAD): coordinar, supervisar, administrar, evaluar (alcance 5-8)
- M1 (Director): administrar, gestionar, implementar, supervisar (alcance 4-7)
- P3 (Jefe Depto): ejecutar, implementar, recopilar, elaborar (alcance 1-5)

ESCALA DE ALCANCE:
1. Operativo: recopilar, registrar
2. Técnico: elaborar, preparar
3. Supervisión: verificar, revisar
4. Analítico: evaluar, analizar
5. Asesoría: proponer, recomendar
6. Coordinación: coordinar, gestionar
7. Gerencial: administrar, supervisar
8. Decisión: aprobar, autorizar
9. Estratégico: dirigir, establecer
10. Normativo: sancionar, expedir

TAREA:
Evalúa si esta función está RESPALDADA por la normativa considerando:

1. RESPALDO DIRECTO: ¿La función está explícitamente en la normativa?
2. RESPALDO DERIVADO: ¿Es una derivación lógica de una función superior?
3. RESPALDO JERÁRQUICO: ¿El verbo es apropiado para el nivel del puesto?

RESPONDE EN JSON:
{{
  "normative_backed": true/false,
  "backing_type": "DIRECT" | "DERIVED" | "HIERARCHICAL" | "NOT_BACKED",
  "normative_source": "cita textual de normativa si aplica",
  "appropriate_for_level": true/false,
  "actual_alcance": 1-10,
  "severity": "MINOR" | "MODERATE" | "CRITICAL",
  "suggested_alternative": "verbo alternativo si aplica",
  "reasoning": "justificación clara (2-3 oraciones)",
  "confidence": 0.0-1.0
}}
"""

        try:
            response = robust_openai_call(
                prompt=prompt,
                max_tokens=VALIDATION_CONFIG["llm_max_tokens"],
                temperature=VALIDATION_CONFIG["llm_temperature"],
                context=self.context
            )

            # Verificar respuesta exitosa
            if response.get("status") != "success":
                error_msg = response.get("error", "Error desconocido")
                print(f"⚠️ Error en validación LLM detallada: {error_msg}")
                # Fallback a resultado de error
                expected_range = NIVEL_TO_ALCANCE.get(nivel_jerarquico, (1, 10))
                return DetailedValidationResult(
                    function_number=function_number,
                    function_text=function_text,
                    verb=verb,
                    normative_backed=False,
                    backing_type="NOT_BACKED",
                    appropriate_for_level=False,
                    expected_alcance_range=expected_range,
                    severity="CRITICAL",
                    reasoning=f"Error en validación: {error_msg}",
                    confidence=0.3
                )

            # Parsear respuesta exitosa
            llm_result = response["data"]

            # Determinar alcance esperado para el nivel
            expected_range = NIVEL_TO_ALCANCE.get(nivel_jerarquico, (1, 10))

            return DetailedValidationResult(
                function_number=function_number,
                function_text=function_text,
                verb=verb,
                normative_backed=llm_result.get("normative_backed", False),
                backing_type=llm_result.get("backing_type", "NOT_BACKED"),
                normative_source=llm_result.get("normative_source"),
                appropriate_for_level=llm_result.get("appropriate_for_level", False),
                expected_alcance_range=expected_range,
                actual_alcance=llm_result.get("actual_alcance", 0),
                severity=llm_result.get("severity", "CRITICAL"),
                suggested_alternative=llm_result.get("suggested_alternative"),
                reasoning=llm_result.get("reasoning", ""),
                confidence=llm_result.get("confidence", 0.5)
            )

        except Exception as e:
            print(f"⚠️ Error inesperado en validación LLM detallada: {e}")
            # Fallback seguro
            return DetailedValidationResult(
                function_number=function_number,
                function_text=function_text,
                verb=verb,
                normative_backed=False,
                backing_type="NOT_BACKED",
                appropriate_for_level=False,
                severity="CRITICAL",
                reasoning=f"Error en validación: {str(e)}",
                confidence=0.3
            )

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    def _get_normativa_context_summary(self, search_query: str = "") -> str:
        """Obtiene resumen del contexto normativo con contenido relevante

        Args:
            search_query: Query para búsqueda semántica de chunks relevantes

        Returns:
            Texto con metadata y chunks de normativa
        """
        if not self.normativa_loader or not hasattr(self.normativa_loader, 'documents'):
            return "No hay normativa cargada"

        summaries = []

        # Primero: metadata de documentos
        for doc_id, doc in self.normativa_loader.documents.items():
            doc_title = getattr(doc, 'title', 'Documento normativo')
            doc_type = getattr(doc, 'document_type', 'Reglamento')
            word_count = getattr(doc, 'word_count', 0)
            summaries.append(f"- {doc_title} ({doc_type}, {word_count} palabras)")

        metadata = "\n".join(summaries[:3])

        # Segundo: contenido relevante mediante búsqueda semántica
        content_chunks = []
        if search_query:
            # Buscar chunks relevantes usando semantic search
            try:
                search_results = self.normativa_loader.semantic_search(
                    query=search_query,
                    max_results=15,  # Traer top 15 chunks más relevantes (más contenido)
                    use_cache=True
                )

                for i, match in enumerate(search_results, 1):
                    # Obtener contenido completo del chunk, no solo snippet
                    doc = self.normativa_loader.documents.get(match.document_id)
                    if doc and hasattr(doc, 'semantic_chunks'):
                        chunk_idx = match.position_info.get('chunk_index', 0)
                        if chunk_idx < len(doc.semantic_chunks):
                            full_chunk = doc.semantic_chunks[chunk_idx]
                            content_chunks.append(
                                f"[Fragmento {i} - Similitud: {match.confidence_score:.2f}]\n{full_chunk[:1500]}"
                            )
            except Exception as e:
                print(f"⚠️ Error en búsqueda semántica de contexto: {e}")
                # Fallback mejorado: tomar múltiples chunks iniciales de cada documento
                for doc_id, doc in list(self.normativa_loader.documents.items())[:2]:
                    if hasattr(doc, 'semantic_chunks') and doc.semantic_chunks:
                        # Tomar los primeros 5 chunks de cada documento
                        for i, chunk in enumerate(doc.semantic_chunks[:5], 1):
                            content_chunks.append(f"[Chunk inicial {i}]\n{chunk[:1200]}")

        # Construir resumen completo
        result = f"DOCUMENTOS NORMATIVOS CARGADOS:\n{metadata}\n\n"

        if content_chunks:
            result += "CONTENIDO NORMATIVO RELEVANTE:\n"
            result += "\n\n".join(content_chunks)
        else:
            result += "No se encontraron fragmentos relevantes específicos."

        return result

    def _get_relevant_normativa_chunks(self, function_text: str, max_chunks: int = 3) -> str:
        """Obtiene chunks de normativa relevantes para una función"""
        if not self.normativa_loader or not hasattr(self.normativa_loader, 'documents'):
            return "No hay normativa cargada"

        # TODO: Implementar búsqueda semántica con embeddings
        # Por ahora, retornar primeros chunks de cada documento
        chunks_text = []
        for doc_id, doc in list(self.normativa_loader.documents.items())[:2]:
            if hasattr(doc, 'chunks') and doc.chunks:
                chunk = doc.chunks[0]
                content = getattr(chunk, 'content', '')
                chunks_text.append(content[:300] + "...")

        return "\n\n".join(chunks_text) if chunks_text else "No hay chunks disponibles"

    def _estimate_expected_functions_count(self) -> int:
        """Estima cantidad esperada de funciones basada en normativa"""
        if not self.normativa_loader or not hasattr(self.normativa_loader, 'documents'):
            return 0

        # Buscar menciones de "función" o "atribución" en la normativa
        # Por ahora, retornar un estimado conservador
        # TODO: Parsear funciones de la normativa de forma estructurada
        return 20  # Placeholder

    def get_validation_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del validador"""
        return {
            "validation_mode": self.validation_mode,
            "weak_verb_threshold": VALIDATION_CONFIG["weak_verb_threshold"],
            "completeness_thresholds": {
                "min": VALIDATION_CONFIG["completeness_min_threshold"],
                "max": VALIDATION_CONFIG["completeness_max_threshold"]
            },
            "normativa_loaded": self.normativa_loader is not None
        }


# ==========================================
# FUNCIÓN FACTORY
# ==========================================

def create_contextual_validator(normativa_loader=None, context: APFContext = None, mode: str = "HYBRID"):
    """Crea un validador contextual con el modo especificado"""
    validator = ContextualVerbValidator(normativa_loader, context)
    validator.set_validation_mode(mode)
    return validator


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("🧪 CONTEXTUAL VERB VALIDATOR - Test")
    print("=" * 60)

    validator = create_contextual_validator(mode="HYBRID")
    print(f"✅ Validador creado en modo: {validator.validation_mode}")
    print(json.dumps(validator.get_validation_summary(), indent=2))
