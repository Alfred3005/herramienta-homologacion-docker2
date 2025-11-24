"""
Modelos de Datos para Sistema de Validación v5.0

Define dataclasses para resultados de validación de los 3 criterios.

Fecha: 2025-11-05
Versión: 5.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class ValidationSeverity(str, Enum):
    """Severidad de un problema detectado"""
    NONE = "NONE"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"


class ValidationResult(str, Enum):
    """Resultado de un criterio"""
    PASS = "PASS"
    FAIL = "FAIL"


class DecisionClassification(str, Enum):
    """Clasificación final del puesto"""
    EXCELENTE = "EXCELENTE"
    ACEPTABLE = "ACEPTABLE"
    DEFICIENTE = "DEFICIENTE"
    CRITICO = "CRITICO"


# ==========================================
# FLAGS Y EVIDENCIAS
# ==========================================

@dataclass
class EvaluationFlag:
    """Representa un problema detectado en la validación"""
    flag_id: str
    severity: ValidationSeverity
    criterion_affected: str  # "CRITERIO_1", "CRITERIO_2", "CRITERIO_3"
    title: str
    description: str
    legal_risk: Optional[str] = None  # "ALTO", "MEDIO", "BAJO"
    suggested_fix: Optional[str] = None
    normative_reference: Optional[str] = None


@dataclass
class Evidence:
    """Evidencia de respaldo normativo"""
    source: str  # "normativa", "reglamento", "manual"
    content_snippet: str
    similarity_score: float
    article_reference: Optional[str] = None


# ==========================================
# CRITERIO 1: CONGRUENCIA DE VERBOS
# ==========================================

@dataclass
class WeakVerbAnalysis:
    """Análisis de un verbo débil detectado"""
    funcion_id: str
    verbo: str
    contexto: str
    tiene_respaldo_normativo: bool
    fragmento_normativo: Optional[str] = None
    similarity_score: float = 0.0
    clasificacion: ValidationSeverity = ValidationSeverity.MODERATE


@dataclass
class Criterion1Result:
    """Resultado de Criterio 1: Congruencia de Verbos Débiles / Análisis Semántico (v5.20+)"""
    criterion_name: str = "CONGRUENCIA_VERBOS"
    result: ValidationResult = ValidationResult.PASS

    total_functions: int = 0
    functions_with_weak_verbs: int = 0
    functions_critical: int = 0  # Sin respaldo / RECHAZADAS
    functions_moderate: int = 0  # Con respaldo / OBSERVACIONES
    functions_approved: int = 0  # APROBADAS (v5.20+)

    critical_rate: float = 0.0
    approval_rate: float = 0.0  # Tasa de aprobación (v5.20+)
    threshold: float = 0.50

    weak_verb_analyses: List[WeakVerbAnalysis] = field(default_factory=list)
    flags_detected: List[EvaluationFlag] = field(default_factory=list)
    evidence_found: List[Evidence] = field(default_factory=list)

    confidence: float = 0.0
    reasoning: str = ""
    details: Optional[Dict[str, Any]] = None  # Detalles adicionales (evaluaciones LLM, etc.)


# ==========================================
# CRITERIO 2: VALIDACIÓN CONTEXTUAL (existente)
# ==========================================

@dataclass
class Criterion2Result:
    """
    Resultado de Criterio 2: Validación Contextual
    (Referencias institucionales + herencia jerárquica)
    """
    criterion_name: str = "VALIDACION_CONTEXTUAL"
    result: ValidationResult = ValidationResult.PASS

    institutional_references_match: bool = True
    has_hierarchical_backing: bool = False

    alignment_classification: str = "ALIGNED"  # ALIGNED, PARTIALLY_ALIGNED, NOT_ALIGNED
    alignment_confidence: float = 0.0

    flags_detected: List[EvaluationFlag] = field(default_factory=list)
    evidence_found: List[Evidence] = field(default_factory=list)

    reasoning: str = ""


# ==========================================
# CRITERIO 3: APROPIACIÓN DE IMPACTO JERÁRQUICO
# ==========================================

@dataclass
class FunctionImpactAnalysis:
    """Análisis de impacto de una función individual"""
    funcion_id: str
    descripcion: str
    que_hace: str
    para_que_lo_hace: str  # ← COMPLEMENTO

    # Análisis de verbos
    verbo_principal: str
    es_verbo_apropiado: bool
    es_verbo_prohibido: bool

    # Análisis de impacto
    detected_scope: str  # local, institutional, interinstitutional, strategic_national
    detected_consequences: str  # operational, tactical, strategic, systemic
    detected_complexity: str  # routine, analytical, strategic, transformational

    # Coherencia vs perfil esperado
    scope_coherent: bool = True
    consequences_coherent: bool = True
    complexity_coherent: bool = True

    # Respaldo normativo
    normative_backing: Optional[str] = None
    normative_confidence: float = 0.0

    # Flags
    severity: ValidationSeverity = ValidationSeverity.NONE
    issue_detected: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class Criterion3Result:
    """Resultado de Criterio 3: Apropiación de Impacto Jerárquico"""
    criterion_name: str = "APROPIACION_IMPACTO_JERARQUICO"
    result: ValidationResult = ValidationResult.PASS

    # Métricas
    total_functions: int = 0
    functions_with_inappropriate_verbs: int = 0
    functions_with_forbidden_verbs: int = 0
    functions_with_scope_discrepancy: int = 0
    functions_with_consequences_discrepancy: int = 0
    functions_critical: int = 0  # Sin respaldo normativo
    functions_moderate: int = 0  # Con respaldo (anotación)

    # Threshold
    critical_rate: float = 0.0
    threshold: float = 0.50

    # Detalles
    function_analyses: List[FunctionImpactAnalysis] = field(default_factory=list)
    flags_detected: List[EvaluationFlag] = field(default_factory=list)
    evidence_found: List[Evidence] = field(default_factory=list)

    # Confianza
    confidence: float = 0.0

    # Evidencia
    normative_fragments_used: List[str] = field(default_factory=list)
    reasoning: str = ""


# ==========================================
# DECISIÓN FINAL (Matriz 2-of-3)
# ==========================================

@dataclass
class FinalDecision:
    """Decisión final basada en matriz 2-of-3"""
    resultado: str  # "APROBADO", "APROBADO_CON_OBSERVACIONES", "RECHAZADO"
    clasificacion: DecisionClassification

    criteria_passed: int  # 0, 1, 2, 3
    criteria_results: Dict[str, ValidationResult] = field(default_factory=dict)

    accion_requerida: str = ""
    confidence_global: float = 0.0

    # Agregación de flags
    all_flags: List[EvaluationFlag] = field(default_factory=list)
    all_evidence: List[Evidence] = field(default_factory=list)

    # Resumen por criterio
    criterion_1: Optional[Criterion1Result] = None
    criterion_2: Optional[Criterion2Result] = None
    criterion_3: Optional[Criterion3Result] = None

    reasoning: str = ""


# ==========================================
# MATRIZ DE DECISIÓN
# ==========================================

DECISION_MATRIX: Dict[int, Dict[str, str]] = {
    3: {
        "resultado": "APROBADO",
        "clasificacion": "EXCELENTE",
        "accion": "Sin modificaciones necesarias. Puesto cumple con todos los criterios de validación."
    },
    2: {
        "resultado": "APROBADO_CON_OBSERVACIONES",
        "clasificacion": "ACEPTABLE",
        "accion": "Implementar mejoras menores en el criterio fallido. Puesto aprobado con observaciones."
    },
    1: {
        "resultado": "RECHAZADO",
        "clasificacion": "DEFICIENTE",
        "accion": "Revisión sustancial requerida - fallan 2 de 3 criterios. Requiere rediseño significativo."
    },
    0: {
        "resultado": "RECHAZADO",
        "clasificacion": "CRITICO",
        "accion": "Reescritura completa necesaria. Ningún criterio cumplido. Puesto no viable en su forma actual."
    }
}


# ==========================================
# FUNCIONES HELPER
# ==========================================

def create_flag(
    flag_id: str,
    severity: ValidationSeverity,
    criterion: str,
    title: str,
    description: str,
    **kwargs
) -> EvaluationFlag:
    """Helper para crear flags de manera consistente"""
    return EvaluationFlag(
        flag_id=flag_id,
        severity=severity,
        criterion_affected=criterion,
        title=title,
        description=description,
        **kwargs
    )


def create_evidence(
    source: str,
    snippet: str,
    score: float,
    **kwargs
) -> Evidence:
    """Helper para crear evidencias"""
    return Evidence(
        source=source,
        content_snippet=snippet,
        similarity_score=score,
        **kwargs
    )


def calculate_final_decision(
    criterion_1: Criterion1Result,
    criterion_2: Criterion2Result,
    criterion_3: Criterion3Result
) -> FinalDecision:
    """
    Calcula la decisión final usando la matriz 2-of-3.

    Args:
        criterion_1: Resultado de Criterio 1
        criterion_2: Resultado de Criterio 2
        criterion_3: Resultado de Criterio 3

    Returns:
        FinalDecision con resultado agregado
    """
    # Contar criterios PASS
    criteria_passed = sum([
        criterion_1.result == ValidationResult.PASS,
        criterion_2.result == ValidationResult.PASS,
        criterion_3.result == ValidationResult.PASS
    ])

    # Obtener decisión de matriz
    decision_data = DECISION_MATRIX[criteria_passed]

    # Clasificación
    classification_map = {
        "EXCELENTE": DecisionClassification.EXCELENTE,
        "ACEPTABLE": DecisionClassification.ACEPTABLE,
        "DEFICIENTE": DecisionClassification.DEFICIENTE,
        "CRITICO": DecisionClassification.CRITICO
    }

    # Agregar flags
    all_flags = []
    all_flags.extend(criterion_1.flags_detected)
    all_flags.extend(criterion_2.flags_detected)
    all_flags.extend(criterion_3.flags_detected)

    # Agregar evidencias
    all_evidence = []
    all_evidence.extend(criterion_1.evidence_found)
    all_evidence.extend(criterion_2.evidence_found)
    all_evidence.extend(criterion_3.evidence_found)

    # Confianza global (promedio)
    confidence_global = (
        criterion_1.confidence +
        criterion_2.alignment_confidence +
        criterion_3.confidence
    ) / 3

    # Generar reasoning
    reasoning_parts = []
    reasoning_parts.append(f"Criterios aprobados: {criteria_passed}/3")
    reasoning_parts.append(f"Criterio 1 (Verbos): {criterion_1.result.value}")
    reasoning_parts.append(f"Criterio 2 (Contextual): {criterion_2.result.value}")
    reasoning_parts.append(f"Criterio 3 (Impacto): {criterion_3.result.value}")

    if criteria_passed >= 2:
        reasoning_parts.append("✅ Puesto APROBADO según matriz 2-of-3")
    else:
        reasoning_parts.append("❌ Puesto RECHAZADO - fallan 2 o más criterios")

    return FinalDecision(
        resultado=decision_data["resultado"],
        clasificacion=classification_map[decision_data["clasificacion"]],
        criteria_passed=criteria_passed,
        criteria_results={
            "CRITERIO_1": criterion_1.result,
            "CRITERIO_2": criterion_2.result,
            "CRITERIO_3": criterion_3.result
        },
        accion_requerida=decision_data["accion"],
        confidence_global=confidence_global,
        all_flags=all_flags,
        all_evidence=all_evidence,
        criterion_1=criterion_1,
        criterion_2=criterion_2,
        criterion_3=criterion_3,
        reasoning="\n".join(reasoning_parts)
    )
