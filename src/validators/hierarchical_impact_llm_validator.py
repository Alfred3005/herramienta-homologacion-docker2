"""
Validador LLM de Impacto Jerárquico para Criterio 3

Este módulo complementa el ImpactAnalyzer basado en reglas con análisis LLM
para obtener mejor comprensión semántica del impacto y respaldo normativo.

MEJORAS v5.37:
- Prompt con RANGOS DE IMPACTO ACEPTABLES específicos por nivel
- No requiere match exacto con perfil ideal - acepta variedad legítima
- Nivel G: acepta scope=[strategic_national, interinstitutional, institutional]
- Nivel G: acepta consequences=[systemic, strategic, tactical]
- Nivel G: acepta complexity=[transformational, innovative, strategic, analytical]
- LLM informado de rangos válidos para evaluación más precisa

Versión: 5.37 (con rangos de impacto aceptables - filosofía de variedad legítima)
Fecha: 2025-11-11
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.validators.shared_utilities import APFContext, robust_openai_call

logger = logging.getLogger(__name__)


@dataclass
class LLMImpactAnalysis:
    """Resultado del análisis LLM de impacto jerárquico"""
    scope_level: str  # local|institutional|interinstitutional|strategic_national
    consequences_level: str  # operational|tactical|strategic|systemic
    complexity_level: str  # routine|analytical|strategic|transformational|innovative
    is_appropriate_for_level: bool
    confidence: float
    reasoning: str
    detected_issues: List[str]


@dataclass
class LLMNormativeBackingResult:
    """Resultado de búsqueda LLM de respaldo normativo"""
    has_backing: bool
    backing_text: Optional[str]
    relevance_score: float
    reasoning: str


class HierarchicalImpactLLMValidator:
    """
    Validador LLM para análisis de impacto jerárquico (Criterio 3).

    Usa GPT-4o-mini para:
    1. Analizar semánticamente el impacto de funciones
    2. Buscar respaldo normativo de manera inteligente
    3. Evaluar coherencia con nivel jerárquico
    """

    def __init__(self, context: APFContext):
        """
        Inicializa el validador LLM.

        Args:
            context: APFContext con API keys y configuración
        """
        self.context = context
        logger.info("[HierarchicalImpactLLMValidator] Inicializado con GPT-4o-mini")

    def analyze_function_impact(
        self,
        funcion_text: str,
        nivel_salarial: str,
        expected_impact: Dict[str, str]
    ) -> LLMImpactAnalysis:
        """
        Analiza el impacto de una función usando LLM.

        Args:
            funcion_text: Texto completo de la función
            nivel_salarial: Nivel del puesto (ej: "M1", "K12")
            expected_impact: Perfil de impacto esperado para el nivel
                {
                    "decision_scope": "institutional",
                    "error_consequences": "tactical",
                    "complexity_level": "analytical"
                }

        Returns:
            LLMImpactAnalysis con el análisis completo
        """
        prompt = self._build_impact_analysis_prompt(
            funcion_text,
            nivel_salarial,
            expected_impact
        )

        try:
            response = robust_openai_call(
                prompt=prompt,
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=800,
                context=self.context
            )

            if response.get("status") == "success":
                result = response["data"]

                return LLMImpactAnalysis(
                    scope_level=result.get("scope_level", "local"),
                    consequences_level=result.get("consequences_level", "operational"),
                    complexity_level=result.get("complexity_level", "routine"),
                    is_appropriate_for_level=result.get("is_appropriate", False),
                    confidence=result.get("confidence", 0.0),
                    reasoning=result.get("reasoning", ""),
                    detected_issues=result.get("issues", [])
                )
            else:
                logger.error(f"[HierarchicalImpactLLMValidator] Error en LLM: {response.get('error')}")
                return self._create_fallback_analysis()

        except Exception as e:
            logger.error(f"[HierarchicalImpactLLMValidator] Excepción en análisis: {e}")
            return self._create_fallback_analysis()

    def search_normative_backing(
        self,
        funcion_text: str,
        normativa_fragments: List[str],
        discrepancy_description: str
    ) -> LLMNormativeBackingResult:
        """
        Busca respaldo normativo para una función usando LLM.

        Args:
            funcion_text: Texto de la función
            normativa_fragments: Fragmentos de normativa disponibles
            discrepancy_description: Descripción de la discrepancia detectada

        Returns:
            LLMNormativeBackingResult con el respaldo encontrado (si existe)
        """
        if not normativa_fragments:
            return LLMNormativeBackingResult(
                has_backing=False,
                backing_text=None,
                relevance_score=0.0,
                reasoning="No hay fragmentos de normativa disponibles"
            )

        prompt = self._build_normative_search_prompt(
            funcion_text,
            normativa_fragments[:5],  # Limitar a 5 fragmentos más relevantes
            discrepancy_description
        )

        try:
            response = robust_openai_call(
                prompt=prompt,
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=600,
                context=self.context
            )

            if response.get("status") == "success":
                result = response["data"]

                return LLMNormativeBackingResult(
                    has_backing=result.get("has_backing", False),
                    backing_text=result.get("backing_text"),
                    relevance_score=result.get("relevance_score", 0.0),
                    reasoning=result.get("reasoning", "")
                )
            else:
                logger.error(f"[HierarchicalImpactLLMValidator] Error en búsqueda normativa: {response.get('error')}")
                return self._create_fallback_backing()

        except Exception as e:
            logger.error(f"[HierarchicalImpactLLMValidator] Excepción en búsqueda: {e}")
            return self._create_fallback_backing()

    def _build_impact_analysis_prompt(
        self,
        funcion_text: str,
        nivel: str,
        expected_impact: Dict[str, str]
    ) -> str:
        """Construye el prompt para análisis de impacto"""

        # Determinar si es nivel estratégico y obtener rangos aceptables
        from src.config.verb_hierarchy import extract_level_letter, get_acceptable_impact_ranges
        letra = extract_level_letter(nivel)
        acceptable_ranges = get_acceptable_impact_ranges(nivel)

        # Construir guidance con rangos específicos
        ranges_guidance = f"""
**RANGOS DE IMPACTO ACEPTABLES PARA NIVEL {nivel} ({letra}):**

La evaluación debe considerar que para este nivel son APROPIADOS los siguientes valores:

- **Alcance (decision_scope)**: {', '.join(acceptable_ranges['decision_scope'])}
- **Consecuencias (error_consequences)**: {', '.join(acceptable_ranges['error_consequences'])}
- **Complejidad (complexity_level)**: {', '.join(acceptable_ranges['complexity_level'])}

**IMPORTANTE**: Si la función tiene impacto dentro de CUALQUIERA de estos rangos, es APROPIADA.
NO es necesario que coincida exactamente con el perfil ideal - los rangos reflejan la variedad
legítima de funciones que puede tener un puesto de este nivel.
"""

        return f"""Eres un experto en análisis de puestos de la Administración Pública Federal mexicana.

**TAREA:** Analiza el impacto jerárquico de esta función y determina si es apropiada para el nivel del puesto.

**NIVEL DEL PUESTO:** {nivel}

**PERFIL DE IMPACTO IDEAL (referencia):**
- Alcance de decisiones: {expected_impact.get('decision_scope', 'N/A')}
- Consecuencias de errores: {expected_impact.get('error_consequences', 'N/A')}
- Complejidad: {expected_impact.get('complexity_level', 'N/A')}
{ranges_guidance}
**FUNCIÓN A ANALIZAR:**
{funcion_text}

**INSTRUCCIONES:**
1. Analiza el ALCANCE real de esta función:
   - local: afecta solo al departamento/área
   - institutional: afecta a toda la institución
   - interinstitutional: afecta a múltiples instituciones
   - strategic_national: afecta a nivel nacional

2. Analiza las CONSECUENCIAS de errores en esta función:
   - operational: afecta operaciones diarias
   - tactical: compromete metas/proyectos
   - strategic: afecta objetivos estratégicos
   - systemic: afecta sistema nacional

3. Analiza la COMPLEJIDAD de esta función:
   - routine: tareas repetitivas/procedimientos
   - analytical: análisis/evaluación
   - strategic: diseño/planeación estratégica
   - transformational: transformación/reestructuración
   - innovative: creación/innovación

4. Determina si el impacto es APROPIADO para el nivel del puesto

Responde en JSON:
{{
  "scope_level": "local|institutional|interinstitutional|strategic_national",
  "consequences_level": "operational|tactical|strategic|systemic",
  "complexity_level": "routine|analytical|strategic|transformational|innovative",
  "is_appropriate": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Explicación concisa de por qué es/no es apropiado",
  "issues": ["lista", "de", "problemas"] // vacío si is_appropriate=true
}}"""

    def _build_normative_search_prompt(
        self,
        funcion_text: str,
        normativa_fragments: List[str],
        discrepancy: str
    ) -> str:
        """Construye el prompt para búsqueda de respaldo normativo"""

        fragments_text = "\n\n".join([
            f"**Fragmento {i+1}:**\n{frag[:500]}"
            for i, frag in enumerate(normativa_fragments)
        ])

        return f"""Eres un experto en normativa de la Administración Pública Federal mexicana.

**TAREA:** Determina si algún fragmento de normativa respalda la discrepancia detectada en esta función.

**FUNCIÓN:**
{funcion_text}

**DISCREPANCIA DETECTADA:**
{discrepancy}

**FRAGMENTOS DE NORMATIVA DISPONIBLES:**
{fragments_text}

**INSTRUCCIONES:**
Busca si algún fragmento respalda explícitamente que esta función (a pesar de la discrepancia detectada) es legítima según la normativa institucional.

Por ejemplo:
- Si el verbo parece inapropiado pero la normativa lo menciona explícitamente
- Si el alcance parece excesivo pero la normativa lo autoriza
- Si hay herencia jerárquica de atribuciones de niveles superiores

Responde en JSON:
{{
  "has_backing": true/false,
  "backing_text": "texto exacto del fragmento que respalda" o null,
  "relevance_score": 0.0-1.0,
  "reasoning": "Explicación de por qué sí/no hay respaldo"
}}"""

    def _create_fallback_analysis(self) -> LLMImpactAnalysis:
        """Crea un análisis fallback en caso de error"""
        return LLMImpactAnalysis(
            scope_level="local",
            consequences_level="operational",
            complexity_level="routine",
            is_appropriate_for_level=False,
            confidence=0.0,
            reasoning="Error en análisis LLM - usando fallback conservador",
            detected_issues=["Error en llamada LLM"]
        )

    def _create_fallback_backing(self) -> LLMNormativeBackingResult:
        """Crea un resultado fallback en caso de error"""
        return LLMNormativeBackingResult(
            has_backing=False,
            backing_text=None,
            relevance_score=0.0,
            reasoning="Error en búsqueda LLM - asumiendo sin respaldo por seguridad"
        )
