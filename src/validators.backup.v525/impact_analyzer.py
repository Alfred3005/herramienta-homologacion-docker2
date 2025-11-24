"""
Analizador de Impacto Jerárquico

Evalúa si el impacto declarado en las funciones es coherente con el nivel
jerárquico del puesto. Analiza 3 dimensiones principales:
1. Alcance de decisiones (scope)
2. Consecuencias de errores (consequences)
3. Complejidad (complexity)

NOTA: La dimensión de presupuesto (budget) se mantiene en el código por
compatibilidad, pero NO se usa en la lógica de decisión por decisión del
equipo (2025-11-05).

Fecha: 2025-11-05
Versión: 5.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import re


# ==========================================
# INDICADORES DE IMPACTO
# ==========================================

SCOPE_INDICATORS = {
    "local": [
        "del departamento", "de la unidad", "del área", "del equipo",
        "operativo", "operativa", "diario", "diaria", "rutinario",
        "interno", "interna"
    ],
    "institutional": [
        "de la dirección", "de la institución", "del organismo",
        "institucional", "organizacional", "de la dependencia",
        "táctico", "táctica"
    ],
    "interinstitutional": [
        "interinstitucional", "intersectorial", "con otras dependencias",
        "con otros organismos", "coordinación con", "enlace con",
        "estratégico sectorial"
    ],
    "strategic_national": [
        "nacional", "república", "país", "federal", "secretaría",
        "administración pública", "gobierno federal", "política pública",
        "estrategia nacional", "nivel nacional", "a nivel nacional"
    ]
}

CONSEQUENCES_INDICATORS = {
    "operational": [
        "afecta operación diaria", "impacta rutina", "retrasa actividades",
        "interrumpe flujo", "afecta procesos internos"
    ],
    "tactical": [
        "afecta cumplimiento", "impacta resultados", "compromete metas",
        "retrasa proyectos", "afecta calidad", "impacta recursos"
    ],
    "strategic": [
        "afecta objetivos estratégicos", "compromete misión",
        "impacta política pública", "afecta reputación institucional",
        "compromete estrategia sectorial"
    ],
    "systemic": [
        "afecta sistema nacional", "compromete seguridad nacional",
        "impacta economía", "afecta población", "crisis",
        "afecta múltiples sectores", "consecuencias irreversibles"
    ]
}

COMPLEXITY_INDICATORS = {
    "routine": [
        "repetitivo", "procedimiento establecido", "rutinario",
        "siguiendo instrucciones", "tareas simples", "operativo básico"
    ],
    "analytical": [
        "analizar", "evaluar", "diagnosticar", "interpretar",
        "estudiar", "investigar", "comparar", "clasificar"
    ],
    "strategic": [
        "diseñar", "planificar", "formular", "proponer",
        "desarrollar estrategias", "establecer políticas"
    ],
    "transformational": [
        "transformar", "rediseñar", "reestructurar", "innovar",
        "modernizar", "revolucionar"
    ],
    "innovative": [
        "crear", "inventar", "pionero", "vanguardia",
        "disruptivo", "primer", "único"
    ]
}

# NOTA: Budget se mantiene por compatibilidad pero NO se usa en decisiones
BUDGET_INDICATORS = {
    "minimal": ["sin presupuesto", "recursos mínimos", "bajo presupuesto"],
    "operational": ["presupuesto operativo", "gastos corrientes"],
    "tactical": ["presupuesto del área", "recursos del departamento"],
    "strategic": ["presupuesto institucional", "millones"],
    "executive": ["presupuesto federal", "miles de millones"]
}


# ==========================================
# JERARQUÍAS DE NIVELES
# ==========================================

SCOPE_HIERARCHY = {
    "local": 1,
    "institutional": 2,
    "interinstitutional": 3,
    "strategic_national": 4
}

CONSEQUENCES_HIERARCHY = {
    "operational": 1,
    "tactical": 2,
    "strategic": 3,
    "systemic": 4
}

COMPLEXITY_HIERARCHY = {
    "routine": 1,
    "analytical": 2,
    "strategic": 3,
    "transformational": 4,
    "innovative": 5
}

# NOTA: No se usa en decisiones
BUDGET_HIERARCHY = {
    "minimal": 1,
    "operational": 2,
    "tactical": 3,
    "strategic": 4,
    "executive": 5
}


# ==========================================
# DATACLASSES
# ==========================================

@dataclass
class ImpactAnalysisResult:
    """Resultado del análisis de impacto"""
    detected_scope: str = "local"
    scope_confidence: float = 0.0
    scope_matches: List[str] = field(default_factory=list)

    detected_consequences: str = "operational"
    consequences_confidence: float = 0.0
    consequences_matches: List[str] = field(default_factory=list)

    detected_complexity: str = "routine"
    complexity_confidence: float = 0.0
    complexity_matches: List[str] = field(default_factory=list)

    # NOTA: Budget no se usa en decisiones (mantenido por compatibilidad)
    detected_budget: str = "minimal"
    budget_confidence: float = 0.0
    budget_matches: List[str] = field(default_factory=list)


@dataclass
class CoherenceEvaluation:
    """Evaluación de coherencia de una dimensión"""
    is_coherent: bool = True
    detected_level: int = 0
    expected_level: int = 0
    difference: int = 0
    tolerance: int = 1
    reasoning: str = ""


# ==========================================
# ANALIZADOR DE IMPACTO
# ==========================================

class ImpactAnalyzer:
    """
    Analiza el impacto de las funciones en 3 dimensiones:
    - Alcance de decisiones (scope)
    - Consecuencias de errores (consequences)
    - Complejidad (complexity)
    """

    def __init__(self):
        self.scope_indicators = SCOPE_INDICATORS
        self.consequences_indicators = CONSEQUENCES_INDICATORS
        self.complexity_indicators = COMPLEXITY_INDICATORS
        self.budget_indicators = BUDGET_INDICATORS  # No se usa

    def analyze_impact_indicators(self, functions: List[Dict[str, Any]]) -> ImpactAnalysisResult:
        """
        Analiza indicadores de impacto en el texto de las funciones.

        Args:
            functions: Lista de funciones del puesto

        Returns:
            ImpactAnalysisResult con los niveles detectados
        """
        # Combinar todo el texto de las funciones
        combined_text = ""
        for func in functions:
            combined_text += func.get("descripcion_completa", "") + " "
            combined_text += func.get("que_hace", "") + " "
            combined_text += func.get("para_que_lo_hace", "") + " "  # El complemento es clave

        combined_lower = combined_text.lower()

        # Detectar alcance
        detected_scope, scope_matches = self._detect_scope(combined_lower)
        scope_confidence = len(scope_matches) / max(len(functions), 1)

        # Detectar complejidad
        detected_complexity, complexity_matches = self._detect_complexity(combined_lower)
        complexity_confidence = len(complexity_matches) / max(len(functions), 1)

        # Inferir consecuencias basado en complejidad y alcance
        detected_consequences = self._infer_consequences(detected_complexity, detected_scope)
        consequences_matches = []
        consequences_confidence = 0.5  # Confianza moderada por inferencia

        # NOTA: Budget no se usa, pero se mantiene por compatibilidad
        detected_budget = "minimal"
        budget_matches = []
        budget_confidence = 0.0

        return ImpactAnalysisResult(
            detected_scope=detected_scope,
            scope_confidence=scope_confidence,
            scope_matches=scope_matches,
            detected_consequences=detected_consequences,
            consequences_confidence=consequences_confidence,
            consequences_matches=consequences_matches,
            detected_complexity=detected_complexity,
            complexity_confidence=complexity_confidence,
            complexity_matches=complexity_matches,
            detected_budget=detected_budget,
            budget_confidence=budget_confidence,
            budget_matches=budget_matches
        )

    def _detect_scope(self, text: str) -> Tuple[str, List[str]]:
        """Detecta el alcance de las decisiones"""
        matches_by_scope = {}

        for scope, indicators in self.scope_indicators.items():
            matches = []
            for indicator in indicators:
                if indicator.lower() in text:
                    matches.append(indicator)
            matches_by_scope[scope] = matches

        # Priorizar niveles más altos si hay empate
        for scope in ["strategic_national", "interinstitutional", "institutional", "local"]:
            if matches_by_scope[scope]:
                return scope, matches_by_scope[scope]

        return "local", []

    def _detect_complexity(self, text: str) -> Tuple[str, List[str]]:
        """Detecta el nivel de complejidad"""
        matches_by_complexity = {}

        for complexity, indicators in self.complexity_indicators.items():
            matches = []
            for indicator in indicators:
                if indicator.lower() in text:
                    matches.append(indicator)
            matches_by_complexity[complexity] = matches

        # Priorizar niveles más altos
        for complexity in ["innovative", "transformational", "strategic", "analytical", "routine"]:
            if matches_by_complexity[complexity]:
                return complexity, matches_by_complexity[complexity]

        return "routine", []

    def _infer_consequences(self, complexity: str, scope: str) -> str:
        """
        Infiere consecuencias basándose en complejidad y alcance.

        Lógica:
        - Si alcance es strategic_national → systemic
        - Si complejidad es transformational/innovative → strategic
        - Si alcance es interinstitutional → strategic
        - Si complejidad es strategic → tactical
        - Default → operational
        """
        if scope == "strategic_national":
            return "systemic"

        if complexity in ["transformational", "innovative"]:
            return "strategic"

        if scope == "interinstitutional":
            return "strategic"

        if complexity == "strategic":
            return "tactical"

        if scope == "institutional":
            return "tactical"

        return "operational"

    def analyze_single_function(self, function: Dict[str, Any]) -> ImpactAnalysisResult:
        """
        Analiza una sola función.

        Args:
            function: Diccionario con la función

        Returns:
            ImpactAnalysisResult para esa función
        """
        return self.analyze_impact_indicators([function])

    def evaluate_scope_coherence(
        self,
        detected_scope: str,
        expected_scope: str,
        nivel: str,
        tolerance: int = 1
    ) -> CoherenceEvaluation:
        """
        Evalúa si el alcance detectado es coherente con el esperado.

        Args:
            detected_scope: Alcance detectado en la función
            expected_scope: Alcance esperado para el nivel
            nivel: Nivel salarial (para contexto)
            tolerance: Tolerancia en niveles (default 1)

        Returns:
            CoherenceEvaluation
        """
        detected_level = SCOPE_HIERARCHY.get(detected_scope, 1)
        expected_level = SCOPE_HIERARCHY.get(expected_scope, 1)
        difference = abs(detected_level - expected_level)

        is_coherent = difference <= tolerance

        reasoning = f"Alcance detectado '{detected_scope}' (nivel {detected_level}) "
        reasoning += f"vs esperado '{expected_scope}' (nivel {expected_level}). "
        reasoning += f"Diferencia: {difference} niveles. "
        reasoning += f"Tolerancia: {tolerance}. "
        reasoning += f"{'✓ Coherente' if is_coherent else '✗ No coherente'}"

        return CoherenceEvaluation(
            is_coherent=is_coherent,
            detected_level=detected_level,
            expected_level=expected_level,
            difference=difference,
            tolerance=tolerance,
            reasoning=reasoning
        )

    def evaluate_consequences_coherence(
        self,
        detected_consequences: str,
        expected_consequences: str,
        nivel: str,
        tolerance: int = 1
    ) -> CoherenceEvaluation:
        """
        Evalúa si las consecuencias detectadas son coherentes con las esperadas.

        Args:
            detected_consequences: Consecuencias detectadas
            expected_consequences: Consecuencias esperadas para el nivel
            nivel: Nivel salarial (para contexto)
            tolerance: Tolerancia en niveles (default 1)

        Returns:
            CoherenceEvaluation
        """
        detected_level = CONSEQUENCES_HIERARCHY.get(detected_consequences, 1)
        expected_level = CONSEQUENCES_HIERARCHY.get(expected_consequences, 1)
        difference = abs(detected_level - expected_level)

        is_coherent = difference <= tolerance

        reasoning = f"Consecuencias detectadas '{detected_consequences}' (nivel {detected_level}) "
        reasoning += f"vs esperadas '{expected_consequences}' (nivel {expected_level}). "
        reasoning += f"Diferencia: {difference} niveles. "
        reasoning += f"Tolerancia: {tolerance}. "
        reasoning += f"{'✓ Coherente' if is_coherent else '✗ No coherente'}"

        return CoherenceEvaluation(
            is_coherent=is_coherent,
            detected_level=detected_level,
            expected_level=expected_level,
            difference=difference,
            tolerance=tolerance,
            reasoning=reasoning
        )

    def evaluate_complexity_coherence(
        self,
        detected_complexity: str,
        expected_complexity: str,
        nivel: str,
        tolerance: int = 1
    ) -> CoherenceEvaluation:
        """
        Evalúa si la complejidad detectada es coherente con la esperada.

        Args:
            detected_complexity: Complejidad detectada
            expected_complexity: Complejidad esperada para el nivel
            nivel: Nivel salarial (para contexto)
            tolerance: Tolerancia en niveles (default 1)

        Returns:
            CoherenceEvaluation
        """
        detected_level = COMPLEXITY_HIERARCHY.get(detected_complexity, 1)
        expected_level = COMPLEXITY_HIERARCHY.get(expected_complexity, 1)
        difference = abs(detected_level - expected_level)

        is_coherent = difference <= tolerance

        reasoning = f"Complejidad detectada '{detected_complexity}' (nivel {detected_level}) "
        reasoning += f"vs esperada '{expected_complexity}' (nivel {expected_level}). "
        reasoning += f"Diferencia: {difference} niveles. "
        reasoning += f"Tolerancia: {tolerance}. "
        reasoning += f"{'✓ Coherente' if is_coherent else '✗ No coherente'}"

        return CoherenceEvaluation(
            is_coherent=is_coherent,
            detected_level=detected_level,
            expected_level=expected_level,
            difference=difference,
            tolerance=tolerance,
            reasoning=reasoning
        )

    def extract_main_verb(self, que_hace: str) -> str:
        """
        Extrae el verbo principal de la descripción "qué hace".

        Args:
            que_hace: Texto del campo "que_hace"

        Returns:
            Verbo en infinitivo (lowercase)
        """
        # Limpiar texto
        texto = que_hace.lower().strip()

        # Patrones comunes:
        # "Coordinar la elaboración..." → "coordinar"
        # "Supervisar el equipo..." → "supervisar"
        # "Coadyuvar en..." → "coadyuvar"

        # Extraer primera palabra (generalmente el verbo)
        palabras = texto.split()
        if not palabras:
            return ""

        primera_palabra = palabras[0]

        # Limpiar caracteres especiales
        verbo = re.sub(r'[^a-záéíóúñ]', '', primera_palabra)

        return verbo
